import os
import json
import logging
from typing import Optional, Dict, Any
from fastapi import HTTPException, Request, WebSocket, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.authentication import (
    AuthenticationBackend, 
    AuthCredentials, 
    SimpleUser,
    UnauthenticatedUser
)
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.requests import HTTPConnection

logger = logging.getLogger(__name__)


class BearerTokenAuth(HTTPBearer):
    """Bearer token authentication for HTTP endpoints"""
    
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
        self.auth_token = os.getenv("AUTH_TOKEN", "insecure-token-change-me")
        
    async def __call__(self, request: Request) -> Optional[HTTPAuthorizationCredentials]:
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


class WebSocketAuth:
    """Authentication handler for WebSocket connections"""
    
    def __init__(self):
        self.auth_token = os.getenv("AUTH_TOKEN", "insecure-token-change-me")
        self.admin_secret = os.getenv("ADMIN_SECRET", "change-me-admin-secret")
        # Import JWT auth here to avoid circular dependency
        from app.jwt_auth import jwt_auth as jwt
        self.jwt_auth = jwt
        
    def validate_payload(self, payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate WebSocket connection payload for authentication
        Returns validated auth info or raises exception
        """
        auth_info = {
            "authenticated": False,
            "is_admin": False,
            "user_id": None,
            "workspace_id": None,
            "workspaces": []
        }
        
        if not payload:
            logger.info("No authentication payload provided for WebSocket connection")
            return auth_info
            
        # First check for JWT token (preferred)
        jwt_token = payload.get("jwtToken") or payload.get("jwt")
        if jwt_token:
            try:
                # Verify JWT token
                token_payload = self.jwt_auth.verify_access_token(jwt_token)
                auth_info["authenticated"] = True
                auth_info["user_id"] = token_payload["sub"]
                auth_info["workspaces"] = token_payload.get("workspaces", [])
                
                # Extract workspace_id from payload or use first available
                workspace_id = payload.get("workspaceId")
                if workspace_id:
                    # Check if user has access to this workspace
                    workspace_access = next(
                        (w for w in auth_info["workspaces"] if w["id"] == workspace_id), 
                        None
                    )
                    if workspace_access:
                        auth_info["workspace_id"] = workspace_id
                        auth_info["is_admin"] = workspace_access.get("role") == "admin"
                    else:
                        logger.warning(f"User {auth_info['user_id']} tried to access unauthorized workspace {workspace_id}")
                        raise ValueError("No access to specified workspace")
                elif auth_info["workspaces"]:
                    # Use first workspace if not specified
                    auth_info["workspace_id"] = auth_info["workspaces"][0]["id"]
                    auth_info["is_admin"] = auth_info["workspaces"][0].get("role") == "admin"
                
                logger.info(f"WebSocket JWT authenticated for user: {auth_info['user_id']}, workspace: {auth_info['workspace_id']}")
                return auth_info
                
            except Exception as e:
                logger.warning(f"JWT validation failed: {e}")
                # Fall through to legacy auth methods
        
        # Legacy auth token support (backwards compatibility)
        auth_token = payload.get("authToken") or payload.get("auth")
        
        if auth_token:
            if auth_token == self.auth_token:
                auth_info["authenticated"] = True
                auth_info["user_id"] = payload.get("userId", "anonymous")
                logger.info(f"WebSocket authenticated successfully for user: {auth_info['user_id']} (legacy auth)")
            else:
                logger.warning("Invalid auth token provided in WebSocket payload")
                raise ValueError("Invalid authentication token")
                
        # Check for admin secret
        admin_secret = payload.get("adminSecret")
        if admin_secret:
            if admin_secret == self.admin_secret:
                auth_info["is_admin"] = True
                auth_info["authenticated"] = True
                logger.info("Admin authenticated via WebSocket")
            else:
                logger.warning("Invalid admin secret provided in WebSocket payload")
                raise ValueError("Invalid admin secret")
                
        return auth_info


class CustomAuthBackend(AuthenticationBackend):
    """
    Custom authentication backend for Starlette/FastAPI
    Handles both HTTP and WebSocket authentication
    """
    
    def __init__(self):
        self.auth_token = os.getenv("AUTH_TOKEN", "insecure-token-change-me")
        self.admin_secret = os.getenv("ADMIN_SECRET", "change-me-admin-secret")
        
    async def authenticate(self, conn: HTTPConnection):
        """
        Authenticate incoming connection (HTTP or WebSocket)
        """
        # For WebSocket connections, check query parameters
        if isinstance(conn, WebSocket):
            # WebSocket authentication is handled separately in the endpoint
            # We'll mark it as unauthenticated here and handle it in the WebSocket handler
            return AuthCredentials(), UnauthenticatedUser()
            
        # For HTTP connections, check Authorization header
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
    """
    Create and return authentication middleware for the FastAPI app
    """
    return AuthenticationMiddleware(
        app,
        backend=CustomAuthBackend(),
        on_error=lambda conn, exc: HTTPException(
            status_code=401,
            detail="Authentication failed"
        )
    )