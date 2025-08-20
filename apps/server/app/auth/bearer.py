from typing import Optional
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class BearerTokenAuth(HTTPBearer):
    
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
        self.auth_token = settings.auth_token
    
    async def __call__(
        self, 
        request: Request
    ) -> Optional[HTTPAuthorizationCredentials]:
        credentials = await super().__call__(request)
        if credentials:
            if credentials.credentials != self.auth_token:
                logger.warning(f"Invalid bearer token attempted from {request.client.host}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid authentication token"
                )
            return credentials
        return None