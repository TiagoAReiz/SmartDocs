import asyncio
import sys
from loguru import logger

from app.services.worker_service import worker_service
from app.database import engine


async def main():
    logger.info("Initializing SmartDocs Background Worker...")
    try:
        # Check DB connection
        async with engine.begin() as conn:
            pass
        logger.info("Database connection established.")
        
        # Start the graceful infinite loop
        await worker_service.start()
    except Exception as e:
        logger.error(f"Worker startup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker stopped by KeyboardInterrupt.")
        worker_service.stop()
