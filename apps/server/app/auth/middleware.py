from fastapi import HTTPException, WebSocket
from starlette.authentication import (
    AuthenticationBackend,
    AuthCredentials,
    SimpleUser,
    UnauthenticatedUser
)
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.requests import HTTPConnection

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class CustomAuthBackend(AuthenticationBackend):
    
    def __init__(self):
        self.auth_token = settings.auth_token
        self.admin_secret = settings.admin_secret
    
    async def authenticate(self, conn: HTTPConnection):
        if isinstance(conn, WebSocket):
            return AuthCredentials(), UnauthenticatedUser()
        
        if "Authorization" not in conn.headers:
            return AuthCredentials(), UnauthenticatedUser()
        
        auth_header = conn.headers["Authorization"]
        
        try:
            scheme, token = auth_header.split()
            if scheme.lower() != "bearer":
                logger.warning(f"Invalid authentication scheme: {scheme}")
                return AuthCredentials(), UnauthenticatedUser()
            
            if token == self.auth_token:
                logger.debug("Valid token authentication for HTTP request")
                return AuthCredentials(["authenticated"]), SimpleUser("user")
            elif token == self.admin_secret:
                logger.debug("Admin authentication for HTTP request")
                return AuthCredentials(["authenticated", "admin"]), SimpleUser("admin")
            else:
                logger.warning("Invalid token provided in Authorization header")
                return AuthCredentials(), UnauthenticatedUser()
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return AuthCredentials(), UnauthenticatedUser()


def create_auth_middleware(app):
    return AuthenticationMiddleware(
        app,
        backend=CustomAuthBackend(),
        on_error=lambda conn, exc: HTTPException(
            status_code=401,
            detail="Authentication failed"
        )
    )