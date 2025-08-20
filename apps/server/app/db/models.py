"""
Database models for authentication and workspace management
"""
from datetime import datetime
from typing import Optional, List
from enum import Enum
import uuid


class UserRole(str, Enum):
    ADMIN = "admin"
    MEMBER = "member"


class User:
    """User model"""
    def __init__(
        self,
        id: str,
        email: str,
        password_hash: str,
        created_at: datetime,
        updated_at: datetime,
        is_active: bool = True,
        is_admin: bool = False
    ):
        self.id = id
        self.email = email
        self.password_hash = password_hash
        self.created_at = created_at
        self.updated_at = updated_at
        self.is_active = is_active
        self.is_admin = is_admin

    @staticmethod
    def generate_id() -> str:
        return str(uuid.uuid4())

    def to_dict(self, include_password=False) -> dict:
        data = {
            "id": self.id,
            "email": self.email,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_active": self.is_active,
            "is_admin": self.is_admin
        }
        if include_password:
            data["password_hash"] = self.password_hash
        return data


class Workspace:
    """Workspace model"""
    def __init__(
        self,
        id: str,
        name: str,
        owner_id: str,
        database_name: str,
        created_at: datetime
    ):
        self.id = id
        self.name = name
        self.owner_id = owner_id
        self.database_name = database_name
        self.created_at = created_at

    @staticmethod
    def generate_id() -> str:
        return str(uuid.uuid4())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "owner_id": self.owner_id,
            "database_name": self.database_name,
            "created_at": self.created_at.isoformat()
        }


class WorkspaceMember:
    """Workspace member model"""
    def __init__(
        self,
        workspace_id: str,
        user_id: str,
        role: UserRole,
        joined_at: datetime
    ):
        self.workspace_id = workspace_id
        self.user_id = user_id
        self.role = role
        self.joined_at = joined_at

    def to_dict(self) -> dict:
        return {
            "workspace_id": self.workspace_id,
            "user_id": self.user_id,
            "role": self.role,
            "joined_at": self.joined_at.isoformat()
        }