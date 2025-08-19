"""
User and workspace database operations
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
import asyncpg
import bcrypt
from app.models import User, Workspace, WorkspaceMember, UserRole

logger = logging.getLogger(__name__)


class UserDatabase:
    """Handles user, workspace and membership database operations"""
    
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
        self.lock = asyncio.Lock()

    async def create_tables(self):
        """Create user-related tables if they don't exist"""
        logger.info("Creating user database tables...")
        
        async with self.pool.acquire() as conn:
            # Users table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id UUID PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    is_active BOOLEAN DEFAULT TRUE,
                    is_admin BOOLEAN DEFAULT FALSE
                );
                
                CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
            """)
            
            # Add is_admin column to existing users table if it doesn't exist
            await conn.execute("""
                DO $$ 
                BEGIN 
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'users' AND column_name = 'is_admin'
                    ) THEN
                        ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE;
                    END IF;
                END $$;
            """)
            
            # Workspaces table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS workspaces (
                    id UUID PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    database_name VARCHAR(255) UNIQUE NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                
                CREATE INDEX IF NOT EXISTS idx_workspaces_owner ON workspaces(owner_id);
            """)
            
            # Workspace members table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS workspace_members (
                    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    role VARCHAR(50) NOT NULL CHECK (role IN ('admin', 'member')),
                    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (workspace_id, user_id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_members_user ON workspace_members(user_id);
            """)
            
            logger.info("✅ User database tables created successfully")

    async def create_user(self, email: str, password: str) -> User:
        """Create a new user"""
        user_id = User.generate_id()
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        now = datetime.utcnow()
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO users (id, email, password_hash, created_at, updated_at, is_admin)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, user_id, email.lower(), password_hash, now, now, False)
                
                user = User(
                    id=user_id,
                    email=email.lower(),
                    password_hash=password_hash,
                    created_at=now,
                    updated_at=now,
                    is_active=True,
                    is_admin=False
                )
                
                logger.info(f"✅ User created: {email}")
                return user
                
        except asyncpg.UniqueViolationError:
            logger.warning(f"User with email {email} already exists")
            raise ValueError(f"User with email {email} already exists")

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT id, email, password_hash, created_at, updated_at, is_active, is_admin
                FROM users
                WHERE email = $1
            """, email.lower())
            
            if row:
                return User(
                    id=str(row['id']),
                    email=row['email'],
                    password_hash=row['password_hash'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at'],
                    is_active=row['is_active'],
                    is_admin=row['is_admin']
                )
            return None

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT id, email, password_hash, created_at, updated_at, is_active, is_admin
                FROM users
                WHERE id = $1
            """, user_id)
            
            if row:
                return User(
                    id=str(row['id']),
                    email=row['email'],
                    password_hash=row['password_hash'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at'],
                    is_active=row['is_active'],
                    is_admin=row['is_admin']
                )
            return None

    async def verify_password(self, user: User, password: str) -> bool:
        """Verify user password"""
        return bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8'))

    async def create_workspace(self, name: str, owner_id: str) -> Workspace:
        """Create a new workspace"""
        workspace_id = Workspace.generate_id()
        database_name = f"ws_{workspace_id.replace('-', '_')}"
        now = datetime.utcnow()
        
        try:
            async with self.pool.acquire() as conn:
                # Create workspace
                await conn.execute("""
                    INSERT INTO workspaces (id, name, owner_id, database_name, created_at)
                    VALUES ($1, $2, $3, $4, $5)
                """, workspace_id, name, owner_id, database_name, now)
                
                # Add owner as admin member
                await conn.execute("""
                    INSERT INTO workspace_members (workspace_id, user_id, role, joined_at)
                    VALUES ($1, $2, $3, $4)
                """, workspace_id, owner_id, UserRole.ADMIN.value, now)
                
                workspace = Workspace(
                    id=workspace_id,
                    name=name,
                    owner_id=owner_id,
                    database_name=database_name,
                    created_at=now
                )
                
                logger.info(f"✅ Workspace created: {name} (ID: {workspace_id})")
                return workspace
                
        except Exception as e:
            logger.error(f"Failed to create workspace: {e}")
            raise

    async def get_user_workspaces(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all workspaces for a user"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT w.*, wm.role, wm.joined_at as member_joined_at
                FROM workspaces w
                JOIN workspace_members wm ON w.id = wm.workspace_id
                WHERE wm.user_id = $1
                ORDER BY w.created_at DESC
            """, user_id)
            
            workspaces = []
            for row in rows:
                workspaces.append({
                    "id": str(row['id']),
                    "name": row['name'],
                    "owner_id": str(row['owner_id']),
                    "database_name": row['database_name'],
                    "created_at": row['created_at'].isoformat(),
                    "role": row['role'],
                    "joined_at": row['member_joined_at'].isoformat()
                })
            
            return workspaces

    async def get_workspace_by_id(self, workspace_id: str) -> Optional[Workspace]:
        """Get workspace by ID"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT id, name, owner_id, database_name, created_at
                FROM workspaces
                WHERE id = $1
            """, workspace_id)
            
            if row:
                return Workspace(
                    id=str(row['id']),
                    name=row['name'],
                    owner_id=str(row['owner_id']),
                    database_name=row['database_name'],
                    created_at=row['created_at']
                )
            return None

    async def add_workspace_member(self, workspace_id: str, user_id: str, role: UserRole = UserRole.MEMBER):
        """Add a member to a workspace"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO workspace_members (workspace_id, user_id, role, joined_at)
                    VALUES ($1, $2, $3, $4)
                """, workspace_id, user_id, role.value, datetime.utcnow())
                
                logger.info(f"✅ User {user_id} added to workspace {workspace_id} as {role.value}")
                
        except asyncpg.UniqueViolationError:
            logger.warning(f"User {user_id} is already a member of workspace {workspace_id}")
            raise ValueError("User is already a member of this workspace")

    async def get_workspace_members(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Get all members of a workspace"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT u.id, u.email, u.is_active, wm.role, wm.joined_at
                FROM users u
                JOIN workspace_members wm ON u.id = wm.user_id
                WHERE wm.workspace_id = $1
                ORDER BY wm.joined_at ASC
            """, workspace_id)
            
            members = []
            for row in rows:
                members.append({
                    "user_id": str(row['id']),
                    "email": row['email'],
                    "is_active": row['is_active'],
                    "role": row['role'],
                    "joined_at": row['joined_at'].isoformat()
                })
            
            return members

    async def check_workspace_access(self, user_id: str, workspace_id: str) -> Optional[str]:
        """Check if user has access to workspace and return their role"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT role FROM workspace_members
                WHERE user_id = $1 AND workspace_id = $2
            """, user_id, workspace_id)
            
            return row['role'] if row else None

    async def get_all_users(self) -> List[User]:
        """Get all users (admin only)"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, email, password_hash, created_at, updated_at, is_active, is_admin
                FROM users
                ORDER BY created_at DESC
            """)
            
            users = []
            for row in rows:
                users.append(User(
                    id=str(row['id']),
                    email=row['email'],
                    password_hash=row['password_hash'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at'],
                    is_active=row['is_active'],
                    is_admin=row['is_admin']
                ))
            
            return users

    async def get_all_workspaces(self) -> List[Workspace]:
        """Get all workspaces (admin only)"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, name, owner_id, database_name, created_at
                FROM workspaces
                ORDER BY created_at DESC
            """)
            
            workspaces = []
            for row in rows:
                workspaces.append(Workspace(
                    id=str(row['id']),
                    name=row['name'],
                    owner_id=str(row['owner_id']),
                    database_name=row['database_name'],
                    created_at=row['created_at']
                ))
            
            return workspaces

    async def create_admin_user(self, email: str, password: str) -> User:
        """Create a new admin user"""
        user_id = User.generate_id()
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        now = datetime.utcnow()
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO users (id, email, password_hash, created_at, updated_at, is_active, is_admin)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, user_id, email.lower(), password_hash, now, now, True, True)
                
                user = User(
                    id=user_id,
                    email=email.lower(),
                    password_hash=password_hash,
                    created_at=now,
                    updated_at=now,
                    is_active=True,
                    is_admin=True
                )
                
                logger.info(f"✅ Admin user created: {email}")
                return user
                
        except asyncpg.UniqueViolationError:
            logger.warning(f"Admin user with email {email} already exists")
            raise ValueError(f"User with email {email} already exists")

    async def ensure_admin_user(self, email: str, password: str) -> User:
        """Ensure admin user exists, create if not exists, update if exists"""
        existing_user = await self.get_user_by_email(email)
        
        if existing_user:
            # User exists, make sure they are admin
            if not existing_user.is_admin:
                async with self.pool.acquire() as conn:
                    await conn.execute("""
                        UPDATE users SET is_admin = TRUE, updated_at = NOW()
                        WHERE id = $1
                    """, existing_user.id)
                    
                existing_user.is_admin = True
                logger.info(f"✅ User {email} promoted to admin")
            else:
                logger.info(f"✅ Admin user {email} already exists")
            
            return existing_user
        else:
            # Create new admin user
            return await self.create_admin_user(email, password)