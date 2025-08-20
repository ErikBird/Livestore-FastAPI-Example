# LiveStore Sync Server - Python/FastAPI Implementation

Eine Python/FastAPI-Implementierung des @livestore/sync-cf WebSocket-Protokolls, die PostgreSQL als Datenbank verwendet und 100% kompatibel mit dem Cloudflare Workers sync-cf Client ist.

## Features

✅ **Vollständige Protokoll-Kompatibilität** mit @livestore/sync-cf Client  
✅ **PostgreSQL** als Datenbank statt Cloudflare D1  
✅ **FastAPI** mit nativem WebSocket-Support  
✅ **Docker Compose** Setup für einfaches Deployment  
✅ **Horizontal skalierbar** (mit Redis Pub/Sub Erweiterung möglich)  

## Protokoll-Implementierung

Diese Implementierung unterstützt alle WebSocket-Nachrichten des sync-cf Protokolls:

### Client → Server
- `PullReq` - Events ab Cursor abrufen
- `PushReq` - Neue Events senden
- `Ping` - Healthcheck
- `AdminResetRoomReq` - Store zurücksetzen (Admin)
- `AdminInfoReq` - Store-Informationen (Admin)

### Server → Client  
- `PullRes` - Event-Batch Response
- `PushAck` - Push-Bestätigung
- `Pong` - Healthcheck Response
- `AdminResetRoomRes` - Reset-Bestätigung
- `AdminInfoRes` - Store-Informationen
- `Error` - Fehler-Response

## Quick Start

### Mit Docker Compose

```bash
# 1. Environment Variables setzen
cp .env.example .env
# Edit .env mit deinen Werten

# 2. Services starten
docker-compose up -d

# 3. Logs anzeigen
docker-compose logs -f
```

### Lokale Entwicklung

#### Mit uv (Empfohlen)
```bash
# 1. uv installieren (falls nicht vorhanden)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Dependencies installieren
uv pip install -r requirements.txt

# 3. PostgreSQL starten
docker run -d \
  --name postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=livestore \
  -p 5432:5432 \
  postgres:16-alpine

# 4. Development Server starten
./run_dev.sh

# Oder manuell:
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Mit Admin User initialisieren
```bash
# Environment Variables setzen
export ADMIN_EMAIL="admin@example.com"
export ADMIN_PASSWORD="secure-password"

# Dann Server starten
./run_dev.sh
```

#### Automatisches Setup (Legacy)
```bash
# 1. Setup Script ausführen
python setup_dev.py

# Das Script erstellt automatisch:
# - Virtual Environment (venv/)
# - Installiert alle Dependencies
# - Startet PostgreSQL Container
```

#### Manuelles Setup mit pip (Legacy)
```bash
# 1. PostgreSQL starten (z.B. mit Docker)
docker run -d \
  --name postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=livestore \
  -p 5432:5432 \
  postgres:16-alpine

# 2. Virtual Environment erstellen
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# oder: venv\Scripts\activate  # Windows

# 3. Python Dependencies installieren
pip install -r requirements.txt

# 4. Environment Variables setzen (oder .env Datei verwenden)
export DATABASE_URL="postgresql://postgres:password@localhost:5432/livestore"
export AUTH_TOKEN="insecure-token-change-me"
export ADMIN_SECRET="change-me-admin-secret"

# 5. Server starten
python -m uvicorn app.main:app --reload --port 8000
```

## Client-Konfiguration

Um den sync-cf Client mit diesem Server zu verbinden:

```typescript
import { makeCfSync } from '@livestore/sync-cf'

const sync = makeCfSync({
  // Statt Cloudflare Worker URL:
  url: 'ws://localhost:8000'  // oder wss://your-domain.com für Production
})

// Verwendung wie gewohnt
const backend = sync({ 
  storeId: 'my-store',
  payload: { authToken: 'insecure-token-change-me' }
})
```

## API Endpoints

- `GET /` - Info-Endpoint
- `GET /health` - Health Check
- `WS /websocket?storeId={id}&payload={encoded}` - WebSocket-Verbindung

## Umgebungsvariablen

| Variable | Beschreibung | Default |
|----------|--------------|---------|
| `DATABASE_URL` | PostgreSQL Connection String | `postgresql://postgres:password@localhost:5432/livestore` |
| `AUTH_TOKEN` | Token für Client-Authentifizierung | `insecure-token-change-me` |
| `ADMIN_SECRET` | Secret für Admin-Operationen | `change-me-admin-secret` |
| `PORT` | Server Port | `8000` |
| `HOST` | Server Host | `0.0.0.0` |

## Datenbank-Schema

Die Implementierung erstellt automatisch Tabellen im Format:

```sql
eventlog_{version}_{store_id} (
    seq_num BIGINT PRIMARY KEY,
    parent_seq_num BIGINT NOT NULL,
    name TEXT NOT NULL,
    args JSONB,
    created_at TIMESTAMPTZ NOT NULL,
    client_id TEXT NOT NULL,
    session_id TEXT NOT NULL
)
```

## Architektur

```
┌─────────────┐     WebSocket      ┌──────────────┐
│   Client    │◄──────────────────►│   FastAPI    │
│  sync-cf    │                    │    Server    │
└─────────────┘                    └──────┬───────┘
                                          │
                                          ▼
                                   ┌──────────────┐
                                   │  PostgreSQL  │
                                   │   Database   │
                                   └──────────────┘
```

## Performance

- Connection Pooling mit asyncpg (5-20 connections)
- Chunked Event Transfer (100 Events pro Batch)
- Async/Await für non-blocking I/O
- WebSocket Broadcasting für Echtzeit-Updates

## Skalierung

Für horizontale Skalierung kann Redis als Pub/Sub Layer hinzugefügt werden:

1. Redis zu docker-compose.yml hinzufügen
2. Redis Pub/Sub in websocket_handler.py implementieren
3. Load Balancer mit sticky sessions konfigurieren

## Testing

```bash
# Unit Tests (TODO)
pytest tests/

# Integration Test mit echtem Client
npm install @livestore/sync-cf
node test-client.js
```

## Production Deployment

1. **SSL/TLS aktivieren** - Nutze einen Reverse Proxy (nginx/Caddy)
2. **Environment Variables** - Sichere Tokens verwenden
3. **Database Backups** - Regelmäßige PostgreSQL Backups
4. **Monitoring** - Prometheus/Grafana Integration
5. **Rate Limiting** - Zum Schutz vor Abuse

## Unterschiede zur Cloudflare Implementation

| Feature | Cloudflare | Python/FastAPI |
|---------|------------|----------------|
| Database | D1 (SQLite) | PostgreSQL |
| Runtime | Workers/Durable Objects | Python asyncio |
| Hosting | Edge Network | Self-hosted/Cloud |
| State Management | Durable Object Memory | Application Memory |
| Scaling | Automatic | Manual/Kubernetes |

## Lizenz

Apache-2.0