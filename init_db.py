import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from bd.models.main import Base

async def init_database():
    """Initialize the database with all tables"""
    engine = create_async_engine("sqlite+aiosqlite:///database.db")
    
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    
    logger.debug("✅ Database tables created successfully!")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(init_database())