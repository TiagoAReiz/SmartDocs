import asyncio
import traceback
from datetime import datetime
from loguru import logger

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.database import async_session
from app.models.document_processing_job import DocumentProcessingJob, JobStatus
from app.models.document import Document, DocumentStatus
from app.models.document_log import DocumentLog
from app.services.document_service import process_document


class WorkerService:
    def __init__(self, max_retries: int = 3, poll_interval: int = 5):
        self.max_retries = max_retries
        self.poll_interval = poll_interval
        self._running = False

    async def start(self):
        """Starts the worker polling loop."""
        self._running = True
        logger.info(f"Worker started. Polling every {self.poll_interval} seconds...")
        while self._running:
            try:
                await self._process_next_job()
            except Exception as e:
                logger.error(f"Worker iteration error: {e}")
            
            await asyncio.sleep(self.poll_interval)

    def stop(self):
        """Stops the worker polling loop."""
        self._running = False
        logger.info("Worker gracefully stopping...")

    async def _process_next_job(self):
        """Fetches and processes the next pending job."""
        
        async with async_session() as db:
            # 1. Fetch the next pending job with FOR UPDATE SKIP LOCKED
            stmt = (
                select(DocumentProcessingJob)
                .where(DocumentProcessingJob.status == JobStatus.PENDING)
                .order_by(DocumentProcessingJob.created_at.asc())
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            
            result = await db.execute(stmt)
            job = result.scalar_one_or_none()
            
            if not job:
                return  # No jobs pending
                
            logger.info(f"[Worker] Picked up job {job.id} for document {job.document_id}")
            
            # 2. Mark as processing and commit to release the lock quickly
            job.status = JobStatus.PROCESSING
            job.started_at = datetime.utcnow()
            doc_id = job.document_id
            job_id = job.id
            
            await db.execute(
                update(Document).where(Document.id == doc_id).values(status=DocumentStatus.PROCESSING)
            )
            await db.commit()
            
        # 3. Process the document OUTSIDE the transaction lock!
        # This prevents holding DB locks while Azure AI takes 10+ seconds
        success = False
        error_msg = None
        
        try:
            # Reusing the existing heavy extraction logic
            async with async_session() as processing_db:
                await process_document(doc_id, processing_db)
            success = True
        except Exception as e:
            error_msg = str(e) + "\n" + traceback.format_exc()
            logger.error(f"[Worker] Failed to process job {job_id}: {error_msg}")
            
        # 4. Finalize the job status
        async with async_session() as db:
            result = await db.execute(select(DocumentProcessingJob).where(DocumentProcessingJob.id == job_id))
            job = result.scalar_one()
            
            if success:
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.utcnow()
                logger.info(f"[Worker] Job {job_id} COMPLETED successfully.")
            else:
                job.attempts += 1
                job.error_log = error_msg
                
                if job.attempts >= self.max_retries:
                    job.status = JobStatus.FAILED
                    job.completed_at = datetime.utcnow()
                    logger.error(f"[Worker] Job {job_id} FAILED permanently after {job.attempts} attempts.")
                    await db.execute(
                        update(Document).where(Document.id == doc_id).values(status=DocumentStatus.FAILED, error_message="Extração abortada após múltiplas tentativas.")
                    )
                else:
                    job.status = JobStatus.PENDING  # Queue for retry
                    logger.warning(f"[Worker] Job {job_id} failed. Retrying... (Attempt {job.attempts}/{self.max_retries})")
            
            await db.commit()

worker_service = WorkerService()
