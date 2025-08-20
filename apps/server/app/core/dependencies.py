from typing import AsyncGenerator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import asyncpg

from .config import settings
from .logging import get_logger

logger = get_logger(__name__)

_db_pool: Optional[asyncpg.Pool] = None


async def get_db_pool() -> asyncpg.Pool:
    global _db_pool
    if not _db_pool:
        raise RuntimeError("Database pool not initialized")
    return _db_pool


async def init_db_pool() -> asyncpg.Pool:
    global _db_pool
    if _db_pool:
        return _db_pool
    
    logger.info(f"Creating database connection pool: {settings.safe_database_url}")
    _db_pool = await asyncpg.create_pool(
        str(settings.database_url),
        min_size=settings.db_pool_min_size,
        max_size=settings.db_pool_max_size,
        command_timeout=settings.db_command_timeout
    )
    
    async with _db_pool.acquire() as conn:
        result = await conn.fetchval("SELECT 1")
        logger.info(f"Database connection test successful: {result}")
    
    return _db_pool


async def close_db_pool() -> None:
    global _db_pool
    if _db_pool:
        await _db_pool.close()
        _db_pool = None
        logger.info("Database connection pool closed")


security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[dict]:
    if not credentials:
        return None
    
    if credentials.credentials == settings.auth_token:
        return {"authenticated": True, "is_admin": False}
    elif credentials.credentials == settings.admin_secret:
        return {"authenticated": True, "is_admin": True}
    
    return None


async def require_auth(
    user: Optional[dict] = Depends(get_current_user)
) -> dict:
    if not user or not user.get("authenticated"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return user


async def require_admin(
    user: Optional[dict] = Depends(get_current_user)
) -> dict:
    if not user or not user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return user