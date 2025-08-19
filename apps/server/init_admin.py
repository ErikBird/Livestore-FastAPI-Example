#!/usr/bin/env python3
"""
Admin User Initialization Script

This script creates or ensures the existence of an admin user based on environment variables.
It can be run as a standalone script or imported and called from other modules.

Environment Variables:
- ADMIN_EMAIL: Email address for the admin user
- ADMIN_PASSWORD: Password for the admin user
- DATABASE_URL: PostgreSQL connection string

Usage:
    python init_admin.py
    
Or programmatically:
    from init_admin import init_admin_user
    await init_admin_user()
"""
import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import Database
from app.user_database import UserDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def init_admin_user(
    email: str = None,
    password: str = None,
    database_url: str = None
) -> bool:
    """
    Initialize admin user from environment variables or parameters.
    
    Args:
        email: Admin email (overrides ADMIN_EMAIL env var)
        password: Admin password (overrides ADMIN_PASSWORD env var)
        database_url: Database URL (overrides DATABASE_URL env var)
    
    Returns:
        bool: True if admin user was created/ensured, False otherwise
    """
    # Get configuration from environment or parameters
    admin_email = email or os.getenv('ADMIN_EMAIL')
    admin_password = password or os.getenv('ADMIN_PASSWORD')
    db_url = database_url or os.getenv('DATABASE_URL')
    
    # Validate required parameters
    if not admin_email:
        logger.error("❌ ADMIN_EMAIL environment variable or email parameter is required")
        return False
    
    if not admin_password:
        logger.error("❌ ADMIN_PASSWORD environment variable or password parameter is required")
        return False
    
    if not db_url:
        logger.error("❌ DATABASE_URL environment variable or database_url parameter is required")
        return False
    
    logger.info(f"🔧 Initializing admin user: {admin_email}")
    
    # Set the DATABASE_URL environment variable if provided
    if database_url:
        os.environ['DATABASE_URL'] = db_url
    
    # Initialize database connection
    db = Database()
    try:
        await db.connect()
        logger.info("✅ Database connection established")
        
        # Initialize user database
        user_db = UserDatabase(db.pool)
        
        # Ensure database tables exist
        await user_db.create_tables()
        
        # Create or ensure admin user
        try:
            admin_user = await user_db.ensure_admin_user(admin_email, admin_password)
            logger.info(f"✅ Admin user ready: {admin_user.email} (ID: {admin_user.id})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create/ensure admin user: {e}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False
        
    finally:
        if db.pool:
            await db.pool.close()
            logger.info("🔐 Database connection closed")


async def main():
    """Main entry point when run as a script"""
    logger.info("🚀 Starting admin user initialization")
    
    success = await init_admin_user()
    
    if success:
        logger.info("✅ Admin user initialization completed successfully")
        sys.exit(0)
    else:
        logger.error("❌ Admin user initialization failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())