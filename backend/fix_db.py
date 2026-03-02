import asyncio
from sqlalchemy import text
from app.database import async_session

async def fix():
    async with async_session() as session:
        await session.execute(text("UPDATE alembic_version SET version_num='73e1a354b074' WHERE version_num='be4b47989cfe'"))
        await session.commit()
        print('Fixed Alembic version')

asyncio.run(fix())
