"""
Admin API endpoints for user and workspace management
"""
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr
import asyncpg

from app.core.dependencies import get_db_pool
from app.db.user_db import UserRepository
from app.db.models import UserRole
from app.auth.jwt import JWTBearer
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


async def verify_admin(
    token_payload: Dict[str, Any] = Depends(JWTBearer()),
    pool: asyncpg.Pool = Depends(get_db_pool)
) -> str:
    """Verify that the current user is an admin"""
    user_id = token_payload["sub"]
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication required"
        )
    
    user_db = UserRepository(pool)
    user = await user_db.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not user.is_admin:
        logger.warning(f"Non-admin user {user_id} ({user.email}) attempted to access admin endpoint")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    logger.debug(f"Admin access verified for user {user_id} ({user.email})")
    return user_id


class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str
    workspace_name: Optional[str] = None


class CreateWorkspaceRequest(BaseModel):
    name: str
    owner_email: EmailStr


class AddMemberRequest(BaseModel):
    user_email: EmailStr
    role: UserRole = UserRole.MEMBER


class UserListResponse(BaseModel):
    users: List[dict]
    total: int


class WorkspaceListResponse(BaseModel):
    workspaces: List[dict]
    total: int


class WorkspaceDetailsResponse(BaseModel):
    workspace: dict
    members: List[dict]


@router.post("/users")
async def create_user(
    request: CreateUserRequest,
    pool: asyncpg.Pool = Depends(get_db_pool),
    admin_id: str = Depends(verify_admin)
):
    """Create a new user (admin only)"""
    user_db = UserRepository(pool)
    
    existing_user = await user_db.get_user_by_email(request.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists"
        )
    
    try:
        user = await user_db.create_user(request.email, request.password)
        
        workspace = None
        if request.workspace_name:
            workspace = await user_db.create_workspace(request.workspace_name, user.id)
        
        logger.info(f"Admin {admin_id} created user {user.id} ({user.email})")
        if workspace:
            logger.info(f"Admin {admin_id} created workspace {workspace.id} for user {user.id}")
        
        result = {
            "message": "User created successfully",
            "user": user.to_dict()
        }
        
        if workspace:
            result["workspace"] = workspace.to_dict()
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )


@router.get("/users", response_model=UserListResponse)
async def list_users(
    pool: asyncpg.Pool = Depends(get_db_pool),
    admin_id: str = Depends(verify_admin)
):
    """List all users (admin only)"""
    user_db = UserRepository(pool)
    
    try:
        users = await user_db.get_all_users()
        user_list = [u.to_dict() for u in users]
        
        logger.info(f"Admin {admin_id} listed {len(users)} users")
        
        return UserListResponse(
            users=user_list,
            total=len(user_list)
        )
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list users"
        )


@router.get("/workspaces", response_model=WorkspaceListResponse)
async def list_workspaces(
    pool: asyncpg.Pool = Depends(get_db_pool),
    admin_id: str = Depends(verify_admin)
):
    """List all workspaces (admin only)"""
    user_db = UserRepository(pool)
    
    try:
        workspaces = await user_db.get_all_workspaces()
        workspace_list = [w.to_dict() for w in workspaces]
        
        logger.info(f"Admin {admin_id} listed {len(workspaces)} workspaces")
        
        return WorkspaceListResponse(
            workspaces=workspace_list,
            total=len(workspace_list)
        )
    except Exception as e:
        logger.error(f"Error listing workspaces: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list workspaces"
        )


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceDetailsResponse)
async def get_workspace_details(
    workspace_id: str,
    pool: asyncpg.Pool = Depends(get_db_pool),
    admin_id: str = Depends(verify_admin)
):
    """Get workspace details with members (admin only)"""
    user_db = UserRepository(pool)
    
    try:
        workspace = await user_db.get_workspace_by_id(workspace_id)
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
        
        members = await user_db.get_workspace_members(workspace_id)
        
        logger.info(f"Admin {admin_id} viewed workspace details for {workspace_id}")
        
        return WorkspaceDetailsResponse(
            workspace=workspace.to_dict(),
            members=members
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workspace details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get workspace details"
        )


@router.delete("/workspaces/{workspace_id}")
async def delete_workspace(
    workspace_id: str,
    pool: asyncpg.Pool = Depends(get_db_pool),
    admin_id: str = Depends(verify_admin)
):
    """Delete a workspace and all its data (admin only)"""
    user_db = UserRepository(pool)
    
    try:
        workspace = await user_db.get_workspace_by_id(workspace_id)
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
        
        # Delete workspace and all related data (cascade delete handles members)
        async with pool.acquire() as conn:
            # Delete all event tables for this workspace
            tables = await conn.fetch("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public' 
                AND tablename LIKE $1
            """, f"eventlog_%_{workspace_id.replace('-', '_')}%")
            
            for table in tables:
                await conn.execute(f"DROP TABLE IF EXISTS {table['tablename']} CASCADE")
                logger.info(f"Dropped table {table['tablename']}")
            
            # Delete the workspace (cascade will handle workspace_members)
            await conn.execute("""
                DELETE FROM workspaces WHERE id = $1
            """, workspace_id)
        
        logger.info(f"Admin {admin_id} deleted workspace {workspace_id}")
        
        return {
            "message": "Workspace deleted successfully",
            "workspace_id": workspace_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting workspace: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete workspace"
        )


@router.post("/workspaces")
async def create_workspace(
    request: CreateWorkspaceRequest,
    pool: asyncpg.Pool = Depends(get_db_pool),
    admin_id: str = Depends(verify_admin)
):
    """Create a new workspace (admin only)"""
    user_db = UserRepository(pool)
    
    # Get owner user by email
    owner = await user_db.get_user_by_email(request.owner_email)
    if not owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Owner user not found"
        )
    
    try:
        workspace = await user_db.create_workspace(request.name, owner.id)
        logger.info(f"Admin {admin_id} created workspace {workspace.id} for owner {owner.id}")
        
        return {
            "message": "Workspace created successfully",
            "workspace": workspace.to_dict()
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating workspace: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create workspace"
        )


@router.post("/workspaces/{workspace_id}/members")
async def add_workspace_member(
    workspace_id: str,
    request: AddMemberRequest,
    pool: asyncpg.Pool = Depends(get_db_pool),
    admin_id: str = Depends(verify_admin)
):
    """Add a member to a workspace (admin only)"""
    user_db = UserRepository(pool)
    
    # Check if workspace exists
    workspace = await user_db.get_workspace_by_id(workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    # Get user by email
    user = await user_db.get_user_by_email(request.user_email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    try:
        # Add member to workspace
        await user_db.add_workspace_member(workspace_id, user.id, request.role)
        logger.info(f"Admin {admin_id} added user {user.id} to workspace {workspace_id} with role {request.role}")
        
        return {
            "message": "Member added successfully",
            "workspace_id": workspace_id,
            "user_id": user.id,
            "role": request.role.value
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error adding workspace member: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add workspace member"
        )


@router.delete("/workspaces/{workspace_id}/members/{user_id}")
async def remove_workspace_member(
    workspace_id: str,
    user_id: str,
    pool: asyncpg.Pool = Depends(get_db_pool),
    admin_id: str = Depends(verify_admin)
):
    """Remove a member from a workspace (admin only)"""
    user_db = UserRepository(pool)
    
    try:
        # Check if workspace exists
        workspace = await user_db.get_workspace_by_id(workspace_id)
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
        
        # Remove member from workspace
        async with pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM workspace_members 
                WHERE workspace_id = $1 AND user_id = $2
            """, workspace_id, user_id)
            
            if result.split()[-1] == '0':
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Member not found in workspace"
                )
        
        logger.info(f"Admin {admin_id} removed user {user_id} from workspace {workspace_id}")
        
        return {
            "message": "Member removed successfully",
            "workspace_id": workspace_id,
            "user_id": user_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing workspace member: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove workspace member"
        )


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    pool: asyncpg.Pool = Depends(get_db_pool),
    admin_id: str = Depends(verify_admin)
):
    """Delete a user and all associated data (admin only)"""
    user_db = UserRepository(pool)
    
    try:
        # Check if user exists
        user = await user_db.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Prevent deleting yourself
        if user_id == admin_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own admin account"
            )
        
        # Delete user (cascade will handle workspace memberships and owned workspaces)
        async with pool.acquire() as conn:
            # First get all workspaces owned by this user
            owned_workspaces = await conn.fetch("""
                SELECT id FROM workspaces WHERE owner_id = $1
            """, user_id)
            
            # Delete event tables for owned workspaces
            for ws in owned_workspaces:
                ws_id = ws['id'].replace('-', '_')
                tables = await conn.fetch("""
                    SELECT tablename FROM pg_tables 
                    WHERE schemaname = 'public' 
                    AND tablename LIKE $1
                """, f"eventlog_%%_{ws_id}%%")
                
                for table in tables:
                    await conn.execute(f"DROP TABLE IF EXISTS {table['tablename']} CASCADE")
                    logger.info(f"Dropped table {table['tablename']}")
            
            # Delete the user (cascade will handle workspace_members and owned workspaces)
            await conn.execute("""
                DELETE FROM users WHERE id = $1
            """, user_id)
        
        logger.info(f"Admin {admin_id} deleted user {user_id} ({user.email})")
        
        return {
            "message": "User deleted successfully",
            "user_id": user_id,
            "email": user.email
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        )


@router.get("/stats")
async def get_system_stats(
    pool: asyncpg.Pool = Depends(get_db_pool),
    admin_id: str = Depends(verify_admin)
):
    """Get system statistics (admin only)"""
    user_db = UserRepository(pool)
    
    try:
        async with pool.acquire() as conn:
            total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
            active_users = await conn.fetchval("SELECT COUNT(*) FROM users WHERE is_active = TRUE")
            total_workspaces = await conn.fetchval("SELECT COUNT(*) FROM workspaces")
        
        logger.info(f"Admin {admin_id} requested system stats")
        
        return {
            "total_users": total_users or 0,
            "active_users": active_users or 0,
            "total_workspaces": total_workspaces or 0,
            "database_status": "healthy"
        }
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        return {
            "total_users": 0,
            "active_users": 0,
            "total_workspaces": 0,
            "database_status": f"error: {str(e)}"
        }