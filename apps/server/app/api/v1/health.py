from datetime import datetime, timezone
from fastapi import APIRouter, Request, Depends
import asyncpg

from app.core.dependencies import get_db_pool
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/health")
async def health_check(request: Request, pool: asyncpg.Pool = Depends(get_db_pool)):
    logger.debug("Health check endpoint accessed")
    
    if hasattr(request, 'user'):
        is_authenticated = request.user.is_authenticated
        logger.debug(f"Health check called by {'authenticated' if is_authenticated else 'unauthenticated'} user")
    else:
        logger.debug("Health check called without auth context")
    
    db_status = "unknown"
    try:
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        db_status = "healthy"
        logger.debug("Database health check passed")
    except Exception as e:
        db_status = f"error: {str(e)}"
        logger.error(f"Database health check failed: {e}")
    
    return {
        "status": "healthy",
        "implementation": "python-fastapi",
        "compatible_with": "@livestore/sync-cf",
        "database_status": db_status,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }