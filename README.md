# LiveStore Test - Monorepo

Ein Monorepo für eine LiveStore-basierte Anwendung mit Vue.js Frontend und FastAPI Backend.

## Struktur

```
LivestoreTest/
├── apps/
│   ├── client/          # Vue.js Frontend Application
│   └── server/          # FastAPI Backend Server
└── docker-compose.yml   # Orchestrierung für lokale Entwicklung
```

## Quick Start

### Komplettes System mit Docker

```bash
# Starte alle Services (PostgreSQL, FastAPI Server)
docker-compose up -d

# Logs anzeigen
docker-compose logs -f
```

### Frontend Development

```bash
cd apps/client
npm install
npm run dev
```

Die Vue-App läuft dann auf http://localhost:5173

### Backend Development

```bash
cd apps/server
python setup_dev.py  # Automatisches Setup
# oder manuell:
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Der FastAPI Server läuft auf http://localhost:8000

## Services

- **Frontend (Vue.js)**: Moderne Single-Page Application mit LiveStore Integration
- **Backend (FastAPI)**: WebSocket-basierter Sync-Server für LiveStore
- **PostgreSQL**: Datenbankserver für persistente Datenspeicherung

## Entwicklung

### Frontend (apps/client)
- Vue 3 mit Composition API
- TypeScript
- Vite als Build-Tool
- Tailwind CSS für Styling
- LiveStore für Echtzeit-Synchronisation

### Backend (apps/server)
- FastAPI mit WebSocket-Support
- PostgreSQL für Datenpersistenz
- Vollständig kompatibel mit @livestore/sync-cf Protokoll
- Docker-ready für einfaches Deployment

## Umgebungsvariablen

Backend-Konfiguration (apps/server):
- `DATABASE_URL`: PostgreSQL Connection String
- `AUTH_TOKEN`: Token für Client-Authentifizierung
- `ADMIN_SECRET`: Secret für Admin-Operationen

## Lizenz

MIT