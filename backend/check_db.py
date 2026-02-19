import asyncio
import sys
from app.database import async_session
from sqlalchemy import select
from app.models.document_chunk import DocumentChunk
from app.models.document import Document

async def main():
    keyword = sys.argv[1] if len(sys.argv) > 1 else "Alvorada"
    async with async_session() as db:
        print(f"Searching for '{keyword}'...")
        res = await db.execute(select(DocumentChunk, Document).join(Document).where(DocumentChunk.content.ilike(f"%{keyword}%")))
        found = res.all()
        print(f"Found {len(found)} chunks.")
        for chunk, doc in found:
             print(f"[Doc {doc.id} | Status: {doc.status}]")
             vec = chunk.embedding
             if vec:
                 print(f"Embedding: Yes ({len(vec)} dims) First 5: {vec[:5]}")
             else:
                 print("Embedding: None")

if __name__ == "__main__":
    asyncio.run(main())
