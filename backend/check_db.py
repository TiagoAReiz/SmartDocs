import asyncio
import sys
from app.database import async_session
from sqlalchemy import select, func, text
from app.models.document_chunk import DocumentChunk
from app.models.document import Document

async def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    
    async with async_session() as db:
        if arg and arg.isdigit():
            doc_id = int(arg)
            print(f"Checking Document ID: {doc_id}...")
            
            # Check Document
            res_doc = await db.execute(select(Document).where(Document.id == doc_id))
            doc = res_doc.scalar_one_or_none()
            
            if not doc:
                print(f"Document {doc_id} NOT FOUND.")
                return

            print(f"Document Found: {doc.filename}")
            print(f"Status: {doc.status}")
            print(f"Type: {doc.type}")
            print(f"User ID: {doc.user_id}")
            
            # Check Chunks
            res_chunks = await db.execute(select(DocumentChunk).where(DocumentChunk.document_id == doc_id))
            chunks = res_chunks.scalars().all()
            
            print(f"Total Chunks: {len(chunks)}")
            
            if chunks:
                print("\n--- First 3 Chunks ---")
                for i, chunk in enumerate(chunks[:3]):
                    print(f"Chunk {i+1} (Index: {chunk.chunk_index}):")
                    print(f"Content Preview: {chunk.content[:100]}...")
                    if chunk.embedding:
                        print(f"Embedding: Present ({len(chunk.embedding)} dims)")
                        # Check vector norm/magnitude just in case
                        # But vector is list usually in sqlalchemy model if using pgvector
                    else:
                        print("Embedding: MISSING")
                    print("-" * 20)
            else:
                print("NO CHUNKS FOUND for this document.")

        else:
            keyword = arg or "Azure"
            print(f"Searching for chunks containing '{keyword}'...")
            stmt = select(DocumentChunk, Document).join(Document).where(DocumentChunk.content.ilike(f"%{keyword}%")).limit(5)
            res = await db.execute(stmt)
            found = res.all()
            print(f"Found {len(found)} sample chunks.")
            for chunk, doc in found:
                 print(f"[Doc {doc.id} | {doc.filename} | Status: {doc.status}]")
                 print(f"Content: {chunk.content[:100]}...")

if __name__ == "__main__":
    asyncio.run(main())
