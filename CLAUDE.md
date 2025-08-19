# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a monorepo for a LiveStore-based real-time application with a Vue.js frontend and FastAPI backend. The system uses WebSocket communication for real-time synchronization between clients through the @livestore/sync-cf protocol.

## Architecture

- **Frontend** (`apps/client/`): Vue 3 SPA with LiveStore integration for real-time state synchronization
- **Backend** (`apps/server/`): Python/FastAPI WebSocket server implementing @livestore/sync-cf protocol with PostgreSQL persistence
- **Database**: PostgreSQL for event storage and persistence

## Development Commands

### Full System (Docker Compose)
```bash
# Start all services (PostgreSQL + FastAPI + Caddy)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Frontend Development
```bash
cd apps/client
npm install
npm run dev        # Start dev server on http://localhost:5173
npm run build      # Build for production
vue-tsc -b         # Type checking
```

### Backend Development
```bash
cd apps/server

# Automatic setup (recommended)
python setup_dev.py

# Manual setup
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# Start server
uvicorn app.main:app --reload --port 8000

# Code quality
black app/          # Format code
mypy app/           # Type checking
pylint app/         # Linting
```

## Key Technical Details

### Frontend Architecture
- **State Management**: LiveStore with SQLite-based state tables
- **Schema**: Defined in `src/livestore/schema.ts` with todos example implementation
- **Styling**: Tailwind CSS (always use Tailwind for styling HTML)
- **WebSocket Sync**: Connects to backend via @livestore/sync-cf protocol

### Backend Architecture
- **WebSocket Protocol**: Full compatibility with @livestore/sync-cf message types
- **Database Tables**: Dynamic creation of `eventlog_{version}_{store_id}` tables
- **Authentication**: Token-based via payload parameter, admin operations via ADMIN_SECRET
- **Connection Management**: WebSocket broadcasting for real-time updates across clients

### Environment Variables

Backend requires:
- `DATABASE_URL`: PostgreSQL connection string (default: `postgresql://postgres:password@localhost:5432/livestore`)
- `AUTH_TOKEN`: Client authentication token
- `ADMIN_SECRET`: Admin operations secret

## Important Implementation Notes

### WebSocket Protocol Messages
The backend implements these message types from @livestore/sync-cf:
- Client→Server: `PullReq`, `PushReq`, `Ping`, `AdminResetRoomReq`, `AdminInfoReq`
- Server→Client: `PullRes`, `PushAck`, `Pong`, `AdminResetRoomRes`, `AdminInfoRes`, `Error`

### LiveStore Schema Pattern
Events and state are defined in `apps/client/src/livestore/schema.ts`:
- State tables use SQLite syntax
- Events are synced across clients
- Materializers map events to state changes

### Database Event Storage
Events are stored with:
- `seq_num`: Primary key sequence number
- `parent_seq_num`: For event ordering
- `name`: Event name (e.g., "v1.TodoCreated")
- `args`: JSON event arguments
- `client_id`, `session_id`: Client tracking