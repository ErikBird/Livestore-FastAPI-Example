# LiveStore Real-time Application with Authentication

A comprehensive real-time application built with LiveStore, featuring JWT authentication, user management, and multi-tenant workspaces.

## Architecture

- **Frontend Client** (`apps/client/`): Vue 3 SPA with JWT authentication and LiveStore real-time sync
- **Admin Client** (`apps/admin-client/`): Vue 3 admin dashboard for user and workspace management  
- **Backend API** (`apps/server/`): Python/FastAPI with JWT auth, WebSocket sync, and PostgreSQL
- **Database**: PostgreSQL with user management and workspace-based multi-tenancy

## Features

### Authentication System
- ✅ **JWT-based authentication** with access and refresh tokens
- ✅ **Stateless authentication** - no server-side session storage
- ✅ **Auto-refresh tokens** - seamless token renewal
- ✅ **Secure password hashing** with bcrypt
- ✅ **Multi-workspace support** per user

### Client Application
- ✅ **Login/Register forms** with Vue 3 + Tailwind CSS
- ✅ **Auth Composables** - modern Vue 3 reactive state management
- ✅ **JWT integration** with LiveStore sync payload
- ✅ **Workspace-based data isolation**
- ✅ **Real-time todo synchronization** across clients

### Admin Dashboard
- ✅ **User management** - view all users and their status
- ✅ **Workspace management** - create workspaces and manage members
- ✅ **Member management** - add/remove users from workspaces
- ✅ **System statistics** - monitor platform health
- ✅ **Admin authentication** - separate admin login

### Backend API
- ✅ **REST API endpoints** for auth and admin operations
- ✅ **WebSocket protocol** compatible with @livestore/sync-cf
- ✅ **Multi-tenant data storage** with workspace isolation
- ✅ **Database migrations** and schema management
- ✅ **Environment-based configuration**

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js 20+ (for local development)
- Python 3.11+ (for local development)

### 1. Environment Setup
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration (especially JWT secrets in production!)
```

### 2. Start with Docker Compose
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

### 3. Access Applications
- **Client App**: http://localhost:3000
- **Admin Dashboard**: http://localhost:3001  
- **API Documentation**: http://localhost:8000/docs
- **Direct API**: http://localhost:8000

### 4. Admin User Access
The admin user is automatically created based on environment variables:
- **Default Admin**: admin@localhost / admin123 (from .env)
- **Admin Dashboard**: http://localhost:3001

For production, update the environment variables:
```bash
ADMIN_EMAIL=your-admin@example.com
ADMIN_PASSWORD=your-secure-password
```

## Development

### Local Development Setup

#### Backend
```bash
cd apps/server
python setup_dev.py  # Automatic setup
# OR manual setup:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

#### Client
```bash
cd apps/client
npm install
npm run dev  # http://localhost:5173
```

#### Admin Client  
```bash
cd apps/admin-client
npm install
npm run dev  # http://localhost:5174
```

#### Database
```bash
# Start PostgreSQL only
docker-compose up postgres -d
```

## API Documentation

### Authentication Endpoints
- `POST /api/auth/register` - Register new user with workspace
- `POST /api/auth/login` - Login with email/password  
- `POST /api/auth/refresh` - Refresh access token
- `GET /api/auth/me` - Get current user info
- `POST /api/auth/logout` - Logout (client-side token removal)

### Admin Endpoints (Requires Admin Role)
- `GET /api/admin/users` - List all users
- `GET /api/admin/workspaces` - List all workspaces
- `POST /api/admin/workspaces` - Create workspace
- `GET /api/admin/workspaces/{id}` - Get workspace details
- `POST /api/admin/workspaces/{id}/members` - Add workspace member
- `DELETE /api/admin/workspaces/{id}/members/{user_id}` - Remove member
- `GET /api/admin/stats` - System statistics

### WebSocket Sync
- `ws://localhost:8000/websocket?storeId={workspace_db}&payload={jwt_payload}`
- Compatible with @livestore/sync-cf protocol
- JWT token required in payload for authentication

## Configuration

### Environment Variables

#### Required for Production
```bash
JWT_SECRET=your-256-bit-secret-key
JWT_REFRESH_SECRET=your-256-bit-refresh-secret  
DATABASE_URL=postgresql://user:pass@host:port/db
```

#### Admin User Configuration
```bash
ADMIN_EMAIL=admin@example.com    # Admin user email
ADMIN_PASSWORD=secure-password   # Admin user password
```

#### Optional Configuration
```bash
JWT_ACCESS_EXPIRY=15          # Minutes
JWT_REFRESH_EXPIRY=7          # Days
AUTH_TOKEN=legacy-token       # Legacy auth support
ADMIN_SECRET=admin-secret     # Admin operations
```

### Security Notes
- 🔒 **Change JWT secrets** in production - use 256-bit random keys
- 🔒 **Use HTTPS** in production for all endpoints
- 🔒 **Configure CORS** appropriately for your domain
- 🔒 **Secure PostgreSQL** with proper credentials and network isolation

## Architecture Deep Dive

### Multi-Tenancy
- Each workspace gets its own database tables (`eventlog_{version}_{workspace_id}`)
- JWT tokens contain workspace permissions and roles
- WebSocket connections are workspace-scoped
- Data isolation at the database level

### JWT Token Structure
```json
{
  "sub": "user_id",
  "email": "user@example.com", 
  "workspaces": [
    {
      "id": "workspace_id",
      "name": "Workspace Name",
      "database_name": "ws_abc123",
      "role": "admin"
    }
  ],
  "exp": 1234567890,
  "iat": 1234567890
}
```

### LiveStore Integration
- JWT token passed in `syncPayload.jwtToken`
- Workspace ID passed in `syncPayload.workspaceId`  
- Server validates JWT and workspace access
- Events scoped to workspace database tables

## Tech Stack

- **Frontend**: Vue 3, TypeScript, Tailwind CSS, Vite
- **Backend**: Python, FastAPI, asyncpg, bcrypt, PyJWT
- **Database**: PostgreSQL 16
- **Real-time**: WebSocket with @livestore/sync-cf protocol
- **DevOps**: Docker, Docker Compose, Nginx
- **Authentication**: JWT with HS256, stateless

## Documentation

### Additional Documentation
- **[Admin System Documentation](./ADMIN_SYSTEM.md)** - Detailed documentation of the admin system architecture, setup, and security features

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Follow the development setup above
4. Make changes and test thoroughly
5. Commit changes (`git commit -m 'Add amazing feature'`)
6. Push to branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

This project is for demonstration purposes. Please ensure proper security review before production use.