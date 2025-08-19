# Changelog

All notable changes to this project will be documented in this file.

## [2.0.0] - 2025-08-19

### Major Changes - Admin System Overhaul

#### 🚀 Added
- **System Administrator Role**: Implemented dedicated `is_admin` flag for true system administrators
- **Automatic Admin User Creation**: Admin users are now automatically created based on environment variables
- **Admin Initialization Script**: `init_admin.py` for standalone admin user creation
- **Docker Startup Integration**: `startup.sh` script handles admin initialization during container startup
- **Environment-based Configuration**: `ADMIN_EMAIL` and `ADMIN_PASSWORD` environment variables

#### 🔒 Security Improvements
- **Enhanced Admin API Security**: Admin endpoints now verify true admin role instead of workspace-based permissions
- **Strict Permission Separation**: Clear distinction between workspace administrators and system administrators
- **Database-level Admin Verification**: All admin operations now check `is_admin` flag in database

#### 🗄️ Database Changes
- **User Schema Extension**: Added `is_admin BOOLEAN DEFAULT FALSE` column to users table
- **Automatic Migration**: System automatically adds `is_admin` column to existing databases
- **Backward Compatibility**: Existing users remain unchanged (not admin by default)

#### 🖥️ Frontend Changes
- **Admin Interface Security**: Admin dashboard now checks `is_admin` flag instead of workspace roles
- **User Model Update**: Extended user interface to include `is_admin` property
- **Authentication Flow**: Updated admin login to verify system admin permissions

#### 📦 Infrastructure Changes
- **Docker Configuration**: Updated Dockerfile to include admin scripts
- **Docker Compose**: Added admin environment variables to service configuration
- **Startup Process**: Modified container startup to run admin initialization

#### 📝 Configuration Changes
- **Environment Files**: Updated `.env` and `.env.example` with admin configuration
- **Default Credentials**: Added default admin user (admin@localhost / admin123) for development

### Technical Details

#### Modified Files
- `apps/server/app/models.py` - Extended User model with is_admin flag
- `apps/server/app/user_database.py` - Added admin user management methods
- `apps/server/app/api/admin.py` - Enhanced admin endpoint security
- `apps/server/app/api/auth.py` - Added is_admin to user response
- `apps/admin-client/src/composables/useAdminAuth.ts` - Updated admin verification logic
- `apps/server/Dockerfile` - Added admin scripts and startup process
- `docker-compose.yml` - Added admin environment variables
- `.env` / `.env.example` - Added admin configuration variables

#### New Files
- `apps/server/init_admin.py` - Admin user initialization script
- `apps/server/startup.sh` - Docker container startup script
- `ADMIN_SYSTEM.md` - Comprehensive admin system documentation
- `CHANGELOG.md` - This changelog file

### Migration Guide

#### For New Installations
1. Set `ADMIN_EMAIL` and `ADMIN_PASSWORD` in `.env`
2. Run `docker-compose up -d`
3. Admin user will be created automatically
4. Access admin dashboard at http://localhost:3001

#### For Existing Installations
1. Database migration happens automatically
2. Set admin credentials in `.env`
3. Rebuild containers: `docker-compose up -d --build`
4. Existing users need manual admin promotion or use admin credentials

#### Breaking Changes
- Admin API endpoints now require `is_admin=true` in database
- Workspace-based admin access to system admin endpoints no longer works
- Admin frontend requires system admin role instead of workspace admin role

### Default Configuration

#### Development
- Admin Email: `admin@localhost`
- Admin Password: `admin123`
- Admin Dashboard: http://localhost:3001

#### Production
- Set secure values for `ADMIN_EMAIL` and `ADMIN_PASSWORD`
- Use HTTPS for all admin endpoints
- Change default JWT secrets

### Security Notes
- 🔒 Admin users have full system access - limit admin roles
- 🔒 Change default admin credentials in production
- 🔒 Use strong passwords for admin accounts
- 🔒 Monitor admin access logs
- 🔒 Regular admin user audits recommended

### Performance Impact
- Minimal: Admin verification adds one database query per admin API call
- Container startup: +1-2 seconds for admin initialization
- No impact on regular user operations

---

## [1.0.0] - 2025-08-19

### Initial Release
- Vue.js frontend with real-time synchronization
- FastAPI backend with WebSocket support
- PostgreSQL database with event storage
- JWT authentication system
- Workspace-based multi-tenancy
- Docker containerization
- Basic admin interface