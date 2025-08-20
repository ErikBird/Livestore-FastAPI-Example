from typing import List, Optional, Dict, Any
from datetime import datetime

from app.core.logging import get_logger
from app.db.user_db import UserRepository
from app.db.models import User, Workspace, WorkspaceMember, UserRole

logger = get_logger(__name__)


class WorkspaceService:
    
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository
    
    async def create_workspace(
        self,
        name: str,
        owner_id: str
    ) -> Workspace:
        workspace = await self.user_repository.create_workspace(name, owner_id)
        logger.info(f"Created workspace {workspace.id} for user {owner_id}")
        return workspace
    
    async def get_user_workspaces(self, user_id: str) -> List[Dict[str, Any]]:
        workspaces = await self.user_repository.get_user_workspaces(user_id)
        return [w.to_dict() for w in workspaces]
    
    async def add_member(
        self,
        workspace_id: str,
        user_id: str,
        role: UserRole = UserRole.MEMBER
    ) -> WorkspaceMember:
        member = await self.user_repository.add_workspace_member(
            workspace_id, 
            user_id, 
            role
        )
        logger.info(f"Added user {user_id} to workspace {workspace_id} with role {role}")
        return member
    
    async def remove_member(
        self,
        workspace_id: str,
        user_id: str
    ) -> bool:
        result = await self.user_repository.remove_workspace_member(
            workspace_id,
            user_id
        )
        if result:
            logger.info(f"Removed user {user_id} from workspace {workspace_id}")
        return result
    
    async def get_workspace_members(
        self,
        workspace_id: str
    ) -> List[Dict[str, Any]]:
        members = await self.user_repository.get_workspace_members(workspace_id)
        return [m.to_dict() for m in members]
    
    async def update_member_role(
        self,
        workspace_id: str,
        user_id: str,
        role: UserRole
    ) -> bool:
        result = await self.user_repository.update_workspace_member_role(
            workspace_id,
            user_id,
            role
        )
        if result:
            logger.info(f"Updated user {user_id} role in workspace {workspace_id} to {role}")
        return result