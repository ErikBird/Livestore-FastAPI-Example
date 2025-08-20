"""
Authentication API endpoints
"""
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr
import asyncpg

from app.core.dependencies import get_db_pool
from app.db.user_db import UserRepository
from app.auth.jwt import JWTAuth, JWTBearer

logger = logging.getLogger(__name__)

router = APIRouter()


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    workspace_name: Optional[str] = "My Workspace"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: str
    email: str
    workspaces: list
    is_admin: bool


@router.post("/register", response_model=TokenResponse)
async def register(request: RegisterRequest):
    """Registration is disabled. Users can only be created by admins."""
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Registration is disabled. Please contact an administrator to create your account."
    )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, pool: asyncpg.Pool = Depends(get_db_pool)):
    """Login with email and password"""
    jwt_auth = JWTAuth()
    user_db = UserRepository(pool)
    
    # Get user by email
    user = await user_db.get_user_by_email(request.email)
    if not user:
        logger.warning(f"Login attempt for non-existent user: {request.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not await user_db.verify_password(user, request.password):
        logger.warning(f"Invalid password attempt for user: {request.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check if user is active
    if not user.is_active:
        logger.warning(f"Login attempt for inactive user: {request.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Get user's workspaces
    workspaces = await user_db.get_user_workspaces(user.id)
    
    # Create tokens
    access_token = jwt_auth.create_access_token(user.id, user.email, workspaces)
    refresh_token = jwt_auth.create_refresh_token(user.id, user.email)
    
    logger.info(f"✅ User logged in successfully: {user.email}")
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=jwt_auth.access_token_expire_minutes * 60
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest, pool: asyncpg.Pool = Depends(get_db_pool)):
    """Refresh access token using refresh token"""
    jwt_auth = JWTAuth()
    try:
        # Verify refresh token
        payload = jwt_auth.verify_refresh_token(request.refresh_token)
        user_id = payload["sub"]
        email = payload["email"]
        
        # Get updated user data
        user_db = UserRepository(pool)
        user = await user_db.get_user_by_id(user_id)
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Get user's current workspaces
        workspaces = await user_db.get_user_workspaces(user_id)
        
        # Create new access token (refresh token stays the same)
        access_token = jwt_auth.create_access_token(user_id, email, workspaces)
        
        logger.info(f"✅ Token refreshed for user: {email}")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=request.refresh_token,  # Return same refresh token
            expires_in=jwt_auth.access_token_expire_minutes * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    token_payload: Dict[str, Any] = Depends(JWTBearer()),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """Get current user information"""
    user_id = token_payload["sub"]
    email = token_payload["email"]
    user_db = UserRepository(pool)
    
    # Get user info
    user = await user_db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get user's workspaces
    workspaces = await user_db.get_user_workspaces(user_id)
    
    logger.debug(f"User info requested for: {email}")
    
    return UserResponse(
        id=user_id,
        email=email,
        workspaces=workspaces,
        is_admin=user.is_admin
    )


@router.post("/logout")
async def logout():
    """
    Logout endpoint (client-side token removal).
    Since we're using stateless JWT, the server doesn't need to do anything.
    The client should remove tokens from storage.
    """
    logger.info("Logout endpoint called (client should remove tokens)")
    return {"message": "Logout successful. Please remove tokens from client storage."}