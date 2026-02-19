import asyncio
from app.services.embedding_service import generate_single_embedding
from app.database import async_session
from sqlalchemy import text as sql_text

async def main():
    query = "empresa Alvorada"
    print(f"Generating embedding for '{query}'...")
    try:
        embedding = await generate_single_embedding(query)
        print(f"Embedding generated: {len(embedding)} dims")
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return

    async with async_session() as db:
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
        sql = sql_text("""
            SELECT content, (embedding <=> :embedding) as distance
            FROM document_chunks
            ORDER BY distance ASC
            LIMIT 5
        """)
        
        print("Executing query...")
        res = await db.execute(sql, {"embedding": embedding_str})
        rows = res.fetchall()
        
        print(f"Top 5 results:")
        for r in rows:
            print(f"Distance: {r.distance:.4f} | Content: {r.content[:50]}...")

if __name__ == "__main__":
    asyncio.run(main())
