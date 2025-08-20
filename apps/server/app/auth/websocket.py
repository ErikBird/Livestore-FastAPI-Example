from typing import Optional, Dict, Any

from app.core.config import settings
from app.core.logging import get_logger
from .jwt import JWTAuth

logger = get_logger(__name__)


class WebSocketAuth:
    
    def __init__(self):
        self.auth_token = settings.auth_token
        self.admin_secret = settings.admin_secret
        self.jwt_auth = JWTAuth()
    
    def validate_payload(self, payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
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
        
        jwt_token = payload.get("jwtToken") or payload.get("jwt")
        if jwt_token:
            try:
                token_payload = self.jwt_auth.verify_access_token(jwt_token)
                auth_info["authenticated"] = True
                auth_info["user_id"] = token_payload["sub"]
                auth_info["workspaces"] = token_payload.get("workspaces", [])
                
                workspace_id = payload.get("workspaceId")
                if workspace_id:
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
                    auth_info["workspace_id"] = auth_info["workspaces"][0]["id"]
                    auth_info["is_admin"] = auth_info["workspaces"][0].get("role") == "admin"
                
                logger.info(f"WebSocket JWT authenticated for user: {auth_info['user_id']}, workspace: {auth_info['workspace_id']}")
                return auth_info
                
            except Exception as e:
                logger.warning(f"JWT validation failed: {e}")
        
        auth_token = payload.get("authToken") or payload.get("auth")
        
        if auth_token:
            if auth_token == self.auth_token:
                auth_info["authenticated"] = True
                auth_info["user_id"] = payload.get("userId", "anonymous")
                logger.info(f"WebSocket authenticated successfully for user: {auth_info['user_id']} (legacy auth)")
            else:
                logger.warning("Invalid auth token provided in WebSocket payload")
                raise ValueError("Invalid authentication token")
        
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