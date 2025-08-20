"""
JWT Authentication module for stateless authentication
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
import jwt
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings

logger = logging.getLogger(__name__)


class JWTAuth:
    """JWT authentication handler"""
    
    def __init__(self):
        self.jwt_secret = settings.jwt_secret
        self.jwt_refresh_secret = settings.jwt_secret + "-refresh"
        self.jwt_algorithm = settings.jwt_algorithm
        self.access_token_expire_minutes = settings.jwt_expiry_minutes
        self.refresh_token_expire_days = 7

    def create_access_token(
        self, 
        user_id: str, 
        email: str,
        workspaces: List[Dict[str, Any]] = None
    ) -> str:
        """Create JWT access token"""
        expire = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)
        
        payload = {
            "sub": user_id,  # Subject (user ID)
            "email": email,
            "type": "access",
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "workspaces": workspaces or []  # List of workspace IDs and roles
        }
        
        token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        logger.debug(f"Access token created for user {user_id}, expires at {expire}")
        return token

    def create_refresh_token(self, user_id: str, email: str) -> str:
        """Create JWT refresh token"""
        expire = datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expire_days)
        
        payload = {
            "sub": user_id,
            "email": email,
            "type": "refresh",
            "exp": expire,
            "iat": datetime.now(timezone.utc)
        }
        
        token = jwt.encode(payload, self.jwt_refresh_secret, algorithm=self.jwt_algorithm)
        logger.debug(f"Refresh token created for user {user_id}, expires at {expire}")
        return token

    def verify_access_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT access token"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            
            if payload.get("type") != "access":
                raise jwt.InvalidTokenError("Invalid token type")
            
            logger.debug(f"Access token verified for user {payload.get('sub')}")
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Access token has expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Access token has expired"
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid access token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid access token"
            )

    def verify_refresh_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT refresh token"""
        try:
            payload = jwt.decode(token, self.jwt_refresh_secret, algorithms=[self.jwt_algorithm])
            
            if payload.get("type") != "refresh":
                raise jwt.InvalidTokenError("Invalid token type")
            
            logger.debug(f"Refresh token verified for user {payload.get('sub')}")
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Refresh token has expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired"
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid refresh token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

    def decode_token_no_verify(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode token without verification (for debugging)"""
        try:
            return jwt.decode(token, options={"verify_signature": False})
        except:
            return None


class JWTBearer(HTTPBearer):
    """JWT Bearer token dependency for FastAPI"""
    
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
        self.jwt_auth = JWTAuth()

    async def __call__(self, request: Request) -> Optional[Dict[str, Any]]:
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        
        if credentials:
            if not credentials.scheme == "Bearer":
                if self.auto_error:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Invalid authentication scheme"
                    )
                return None
            
            # Verify the token and return the payload
            payload = self.jwt_auth.verify_access_token(credentials.credentials)
            return payload
        
        if self.auto_error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid authorization code"
            )
        return None




