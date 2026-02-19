import asyncio
import os
import sys

# Add app to path
sys.path.append(os.getcwd())

from app.database import async_session
from app.services import chat_service
from app.models.user import User
from sqlalchemy import select

async def main():
    async with async_session() as db:
        # Get an admin user for context
        result = await db.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        if not user:
            print("No user found to run test")
            return

        print(f"Running test with user: {user.email}")
        
        # Test query that should return data
        question = "Listar todos os documentos do sistema"
        
        print(f"Question: {question}")
        response = await chat_service.chat(
            question=question,
            user_id=user.id,
            is_admin=True,
            db=db
        )
        
        print("\n--- Response ---")
        print(f"Answer: {response['answer'][:100]}...")
        print(f"SQL Used: {response['sql_used']}")
        print(f"Row Count: {response['row_count']}")
        
        if response['data']:
            print(f"Data captured: {len(response['data'])} rows")
            print(f"Sample row: {response['data'][0]}")
            print("✅ SUCCESS: Structured data returned")
        else:
            print("❌ FAILURE: No data returned")

if __name__ == "__main__":
    asyncio.run(main())
