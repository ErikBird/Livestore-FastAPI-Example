"""
Admin API endpoints for user and workspace management
"""
import logging
import os
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr

from app.database import db
from app.user_database import UserDatabase
from app.models import UserRole
from app.jwt_auth import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["Admin"])

# Admin secret for admin-only endpoints
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "change-me-admin-secret")


async def verify_admin(user_id: str = Depends(get_current_user_id)) -> str:
    """Verify that the current user is an admin"""
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication required"
        )
    
    # Check if user has admin role in database
    user_db = UserDatabase(db.pool)
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


class UserListResponse(BaseModel):
    users: List[dict]
    total: int


class WorkspaceListResponse(BaseModel):
    workspaces: List[dict]
    total: int


class CreateWorkspaceRequest(BaseModel):
    name: str
    owner_email: EmailStr


class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str
    workspace_name: Optional[str] = None


class AddMemberRequest(BaseModel):
    user_email: EmailStr
    role: str = "member"


class WorkspaceDetailsResponse(BaseModel):
    workspace: dict
    members: List[dict]


@router.post("/users")
async def create_user(
    request: CreateUserRequest,
    admin_id: str = Depends(verify_admin)
):
    """Create a new user (admin only)"""
    user_db = UserDatabase(db.pool)
    
    # Check if user already exists
    existing_user = await user_db.get_user_by_email(request.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists"
        )
    
    try:
        # Create user
        user = await user_db.create_user(request.email, request.password)
        
        # Create workspace if requested
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
async def list_users(admin_id: str = Depends(verify_admin)):
    """List all users (admin only)"""
    user_db = UserDatabase(db.pool)
    
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
async def list_workspaces(admin_id: str = Depends(verify_admin)):
    """List all workspaces (admin only)"""
    user_db = UserDatabase(db.pool)
    
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


@router.post("/workspaces")
async def create_workspace(
    request: CreateWorkspaceRequest,
    admin_id: str = Depends(verify_admin)
):
    """Create a new workspace for a user (admin only)"""
    user_db = UserDatabase(db.pool)
    
    # Find the owner user
    owner = await user_db.get_user_by_email(request.owner_email)
    if not owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {request.owner_email} not found"
        )
    
    try:
        workspace = await user_db.create_workspace(request.name, owner.id)
        
        logger.info(f"Admin {admin_id} created workspace {workspace.id} for user {owner.id}")
        
        return {
            "message": "Workspace created successfully",
            "workspace": workspace.to_dict()
        }
    except Exception as e:
        logger.error(f"Error creating workspace: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create workspace"
        )


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceDetailsResponse)
async def get_workspace_details(
    workspace_id: str,
    admin_id: str = Depends(verify_admin)
):
    """Get workspace details including members (admin only)"""
    user_db = UserDatabase(db.pool)
    
    workspace = await user_db.get_workspace_by_id(workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    members = await user_db.get_workspace_members(workspace_id)
    
    logger.info(f"Admin {admin_id} viewed workspace {workspace_id} details")
    
    return WorkspaceDetailsResponse(
        workspace=workspace.to_dict(),
        members=members
    )


@router.post("/workspaces/{workspace_id}/members")
async def add_workspace_member(
    workspace_id: str,
    request: AddMemberRequest,
    admin_id: str = Depends(verify_admin)
):
    """Add a member to a workspace (admin only)"""
    user_db = UserDatabase(db.pool)
    
    # Check workspace exists
    workspace = await user_db.get_workspace_by_id(workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    # Find the user to add
    user = await user_db.get_user_by_email(request.user_email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {request.user_email} not found"
        )
    
    # Validate role
    try:
        role = UserRole(request.role.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role: {request.role}. Must be 'admin' or 'member'"
        )
    
    try:
        await user_db.add_workspace_member(workspace_id, user.id, role)
        
        logger.info(f"Admin {admin_id} added user {user.id} to workspace {workspace_id} as {role.value}")
        
        return {
            "message": "Member added successfully",
            "workspace_id": workspace_id,
            "user_id": user.id,
            "role": role.value
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error adding member to workspace: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add member"
        )


@router.delete("/workspaces/{workspace_id}/members/{user_id}")
async def remove_workspace_member(
    workspace_id: str,
    user_id: str,
    admin_id: str = Depends(verify_admin)
):
    """Remove a member from a workspace (admin only)"""
    user_db = UserDatabase(db.pool)
    
    # Check workspace exists
    workspace = await user_db.get_workspace_by_id(workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    # Don't allow removing the owner
    if workspace.owner_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove workspace owner"
        )
    
    try:
        async with db.pool.acquire() as conn:
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
        logger.error(f"Error removing member from workspace: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove member"
        )


@router.delete("/workspaces/{workspace_id}")
async def delete_workspace(
    workspace_id: str,
    admin_id: str = Depends(verify_admin)
):
    """Delete a workspace (admin only)"""
    user_db = UserDatabase(db.pool)
    
    # Check workspace exists
    workspace = await user_db.get_workspace_by_id(workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    try:
        async with db.pool.acquire() as conn:
            # Start transaction
            async with conn.transaction():
                # Remove all workspace members first
                await conn.execute("""
                    DELETE FROM workspace_members
                    WHERE workspace_id = $1
                """, workspace_id)
                
                # Delete the workspace
                await conn.execute("""
                    DELETE FROM workspaces
                    WHERE id = $1
                """, workspace_id)
        
        logger.info(f"Admin {admin_id} deleted workspace {workspace_id} ({workspace.name})")
        
        return {
            "message": "Workspace deleted successfully",
            "workspace_id": workspace_id
        }
    except Exception as e:
        logger.error(f"Error deleting workspace: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete workspace"
        )


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    admin_id: str = Depends(verify_admin)
):
    """Delete a user (admin only)"""
    user_db = UserDatabase(db.pool)
    
    # Check user exists
    user = await user_db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Don't allow deleting admin users (safety check)
    if user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete admin users"
        )
    
    try:
        async with db.pool.acquire() as conn:
            # Start transaction
            async with conn.transaction():
                # Remove user from all workspace memberships
                await conn.execute("""
                    DELETE FROM workspace_members
                    WHERE user_id = $1
                """, user_id)
                
                # Delete workspaces owned by this user (and their members)
                owned_workspaces = await conn.fetch("""
                    SELECT id FROM workspaces WHERE owner_id = $1
                """, user_id)
                
                for workspace in owned_workspaces:
                    await conn.execute("""
                        DELETE FROM workspace_members
                        WHERE workspace_id = $1
                    """, workspace['id'])
                
                await conn.execute("""
                    DELETE FROM workspaces
                    WHERE owner_id = $1
                """, user_id)
                
                # Finally delete the user
                await conn.execute("""
                    DELETE FROM users
                    WHERE id = $1
                """, user_id)
        
        logger.info(f"Admin {admin_id} deleted user {user_id} ({user.email})")
        
        return {
            "message": "User deleted successfully",
            "user_id": user_id
        }
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        )


@router.get("/stats")
async def get_system_stats(admin_id: str = Depends(verify_admin)):
    """Get system statistics (admin only)"""
    user_db = UserDatabase(db.pool)
    
    try:
        users = await user_db.get_all_users()
        workspaces = await user_db.get_all_workspaces()
        
        # Get active users (logged in within last 30 days)
        active_users = [u for u in users if u.is_active]
        
        stats = {
            "total_users": len(users),
            "active_users": len(active_users),
            "total_workspaces": len(workspaces),
            "database_status": "healthy" if db.pool else "disconnected"
        }
        
        logger.info(f"Admin {admin_id} retrieved system stats")
        
        return stats
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get system stats"
        )