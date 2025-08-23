import os
import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from contextlib import asynccontextmanager
from models import Base
from config import settings
import logging
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

logger = logging.getLogger(__name__)

def clean_database_url_for_asyncpg(url: str) -> str:
    """Clean database URL to remove parameters incompatible with asyncpg"""
    parsed = urlparse(url)
    
    # Parse query parameters
    query_dict = parse_qs(parsed.query)
    
    # Remove problematic parameters for asyncpg
    asyncpg_incompatible = ['sslmode', 'sslcert', 'sslkey', 'sslrootcert']
    for param in asyncpg_incompatible:
        query_dict.pop(param, None)
    
    # Add SSL context for asyncpg if needed
    if not query_dict.get('sslmode') or query_dict.get('sslmode')[0] != 'disable':
        query_dict['ssl'] = ['require']
    
    # Rebuild URL
    new_query = urlencode(query_dict, doseq=True)
    cleaned_url = urlunparse((
        parsed.scheme,
        parsed.netloc, 
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment
    ))
    
    return cleaned_url

# Clean the database URL for asyncpg compatibility
cleaned_db_url = clean_database_url_for_asyncpg(settings.database_url)

# Create async engine
engine = create_async_engine(
    cleaned_db_url.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.debug,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    pool_pre_ping=True
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def init_db():
    """Initialize database and create tables"""
    try:
        # Create pgvector extension
        conn = await asyncpg.connect(settings.database_url)
        try:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            logger.info("pgvector extension created/verified")
        finally:
            await conn.close()
        
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created/verified")
            
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


@asynccontextmanager
async def get_db():
    """Get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_db_session():
    """Get database session for dependency injection"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def test_connection():
    """Test database connection"""
    try:
        async with get_db() as session:
            result = await session.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False
