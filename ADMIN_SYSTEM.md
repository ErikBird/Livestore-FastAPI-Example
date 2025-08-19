# Admin System Documentation

## Übersicht

Das Admin-System wurde komplett überarbeitet, um eine echte System-Administrator-Rolle zu implementieren. Vorher basierte der Admin-Zugang auf Workspace-Rollen, jetzt gibt es eine dedizierte `is_admin` Flag für System-Administratoren.

## Architekturänderungen

### 1. Datenbank-Schema

#### User-Tabelle Erweiterung
```sql
-- Neue Spalte hinzugefügt
ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE;
```

**Automatische Migration**: Das System fügt die `is_admin` Spalte automatisch bei Startup hinzu, falls sie nicht existiert.

### 2. User Model Erweiterung

**Datei**: `apps/server/app/models.py`

```python
class User:
    def __init__(
        self,
        id: str,
        email: str,
        password_hash: str,
        created_at: datetime,
        updated_at: datetime,
        is_active: bool = True,
        is_admin: bool = False  # ← NEU
    ):
```

**Änderungen**:
- `is_admin` Parameter hinzugefügt
- `to_dict()` Methode um `is_admin` erweitert

### 3. UserDatabase Erweiterung

**Datei**: `apps/server/app/user_database.py`

**Neue Methoden**:
```python
async def create_admin_user(self, email: str, password: str) -> User:
    """Erstellt einen neuen Admin-Benutzer"""

async def ensure_admin_user(self, email: str, password: str) -> User:
    """Stellt sicher dass Admin existiert, erstellt ihn falls nicht"""
```

**Geänderte Methoden**:
- `create_user()` - Setzt `is_admin=False` standardmäßig
- `get_user_by_email()` - Lädt `is_admin` Flag
- `get_user_by_id()` - Lädt `is_admin` Flag
- `get_all_users()` - Lädt `is_admin` Flag

### 4. Admin-API Sicherheit

**Datei**: `apps/server/app/api/admin.py`

**Vorher**:
```python
def verify_admin(user_id: str = Depends(get_current_user_id)) -> str:
    # Vereinfachte Prüfung ohne echte Admin-Rolle
```

**Nachher**:
```python
async def verify_admin(user_id: str = Depends(get_current_user_id)) -> str:
    # Lädt User aus Datenbank und prüft is_admin Flag
    user = await user_db.get_user_by_id(user_id)
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
```

### 5. Auth-API Erweiterung

**Datei**: `apps/server/app/api/auth.py`

```python
class UserResponse(BaseModel):
    id: str
    email: str
    workspaces: list
    is_admin: bool  # ← NEU
```

Die `/api/auth/me` Route gibt jetzt das `is_admin` Flag zurück.

### 6. Frontend Admin-Authentifizierung

**Datei**: `apps/admin-client/src/composables/useAdminAuth.ts`

**Vorher**:
```typescript
// Prüfung auf Workspace-Admin-Rolle
if (!user.value?.workspaces?.some(w => w.role === 'admin')) {
    throw new Error('Admin access required')
}
```

**Nachher**:
```typescript
// Prüfung auf echte Admin-Rolle
if (!user.value?.is_admin) {
    throw new Error('Admin access required')
}
```

## Admin-Initialisierung

### 1. Init-Script

**Neue Datei**: `apps/server/init_admin.py`

```python
#!/usr/bin/env python3
"""
Admin User Initialization Script

Environment Variables:
- ADMIN_EMAIL: Email address for the admin user
- ADMIN_PASSWORD: Password for the admin user
- DATABASE_URL: PostgreSQL connection string
"""
```

**Features**:
- Standalone ausführbar
- Programmtisch importierbar
- Robuste Fehlerbehandlung
- Umfassendes Logging

### 2. Startup-Script

**Neue Datei**: `apps/server/startup.sh`

```bash
#!/bin/bash

# Initialize admin user if environment variables are set
if [ -n "$ADMIN_EMAIL" ] && [ -n "$ADMIN_PASSWORD" ]; then
    python init_admin.py
fi

# Start the FastAPI server
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3. Docker Integration

**Geänderte Datei**: `apps/server/Dockerfile`

```dockerfile
# Copy admin scripts
COPY init_admin.py .
COPY startup.sh .

# Make executable
RUN chmod +x startup.sh

# Use startup script instead of direct uvicorn
CMD ["./startup.sh"]
```

**Geänderte Datei**: `docker-compose.yml`

```yaml
services:
  fastapi:
    environment:
      ADMIN_EMAIL: ${ADMIN_EMAIL}      # ← NEU
      ADMIN_PASSWORD: ${ADMIN_PASSWORD} # ← NEU
```

## Environment-Variablen

### Neue Variablen

| Variable | Beschreibung | Default | Erforderlich |
|----------|--------------|---------|--------------|
| `ADMIN_EMAIL` | Email des System-Administrators | - | Ja (für Auto-Init) |
| `ADMIN_PASSWORD` | Passwort des System-Administrators | - | Ja (für Auto-Init) |

### Aktualisierte .env Files

**`.env`**:
```bash
# Admin User (for automatic admin user creation)
ADMIN_EMAIL=admin@localhost
ADMIN_PASSWORD=admin123
```

**`.env.example`**:
```bash
# Admin User Configuration (for automatic admin user creation)
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=change-me-secure-admin-password
```

## Deployment-Verhalten

### 1. Container-Startup-Sequenz

1. **PostgreSQL Container** startet
2. **FastAPI Container** startet und führt `startup.sh` aus:
   - Prüft auf `ADMIN_EMAIL` und `ADMIN_PASSWORD`
   - Falls gesetzt: Führt `python init_admin.py` aus
   - Startet FastAPI Server mit `uvicorn`

### 2. Admin-User-Logik

```python
async def ensure_admin_user(self, email: str, password: str) -> User:
    existing_user = await self.get_user_by_email(email)
    
    if existing_user:
        if not existing_user.is_admin:
            # Promote existing user to admin
            UPDATE users SET is_admin = TRUE WHERE id = ?
        return existing_user
    else:
        # Create new admin user
        return await self.create_admin_user(email, password)
```

**Verhalten**:
- **Benutzer existiert nicht**: Erstellt neuen Admin-Benutzer
- **Benutzer existiert, ist kein Admin**: Befördert zum Admin
- **Benutzer existiert, ist bereits Admin**: Keine Änderung

### 3. Fehlerbehandlung

- **Admin-Init schlägt fehl**: Server startet trotzdem (mit Warnung)
- **Keine Admin-Credentials**: Server startet ohne Admin-Initialisierung
- **Datenbank-Verbindung fehlt**: Admin-Init schlägt fehl, Server startet trotzdem

## Sicherheitsverbesserungen

### 1. Strikte Admin-Prüfung

**Vorher**: Workspace-basierte Admin-Rechte
```python
# Jeder mit Admin-Rolle in mindestens einem Workspace
```

**Nachher**: System-Admin-Flag
```python
# Nur Benutzer mit is_admin=TRUE
if not user.is_admin:
    raise HTTPException(status_code=403, detail="Admin access required")
```

### 2. Klare Rollenaufteilung

| Rolle | Berechtigung | Zugang |
|-------|-------------|--------|
| **Normaler Benutzer** | Workspace-Management | Client App (Port 3000) |
| **Workspace-Admin** | Workspace-Administration | Client App (Port 3000) |
| **System-Administrator** | System-wide Administration | Admin Dashboard (Port 3001) |

### 3. API-Endpunkt-Schutz

Alle `/api/admin/*` Endpunkte sind jetzt durch echte Admin-Rolle geschützt:

```python
@router.get("/users")
async def list_users(admin_id: str = Depends(verify_admin)):
    # Nur erreichbar für Benutzer mit is_admin=True
```

## Testing und Entwicklung

### 1. Lokaler Test des Admin-Scripts

```bash
cd apps/server
export ADMIN_EMAIL=test@admin.com
export ADMIN_PASSWORD=testpassword
export DATABASE_URL=postgresql://postgres:password@localhost:5432/livestore

python init_admin.py
```

### 2. Docker-Entwicklung

```bash
# Mit Standard-Admin
docker-compose up -d

# Mit Custom-Admin
ADMIN_EMAIL=custom@admin.com ADMIN_PASSWORD=custompass docker-compose up -d
```

### 3. Admin-Login Testen

1. Gehe zu http://localhost:3001
2. Login mit `admin@localhost` / `admin123`
3. Sollte Admin-Dashboard anzeigen

## Migration für bestehende Systeme

### 1. Automatische Datenbank-Migration

Das System führt automatisch folgende Migration aus:

```sql
DO $$ 
BEGIN 
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'is_admin'
    ) THEN
        ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE;
    END IF;
END $$;
```

### 2. Bestehende Admin-Benutzer

Bestehende Benutzer sind **nicht automatisch Admins**. Um einen bestehenden Benutzer zum Admin zu machen:

**Option 1**: Admin-Credentials in .env setzen
```bash
ADMIN_EMAIL=existing@user.com
ADMIN_PASSWORD=theirpassword
```

**Option 2**: Manuell in Datenbank
```sql
UPDATE users SET is_admin = TRUE WHERE email = 'existing@user.com';
```

**Option 3**: Über Admin-Init-Script
```python
from init_admin import init_admin_user
await init_admin_user(email='existing@user.com', password='theirpassword')
```

## Troubleshooting

### 1. Admin-Init schlägt fehl

**Logs prüfen**:
```bash
docker-compose logs fastapi | grep admin
```

**Häufige Probleme**:
- `DATABASE_URL` nicht gesetzt
- Database nicht erreichbar beim Startup
- Admin-Credentials fehlen

### 2. Admin-Login funktioniert nicht

**Prüfen ob Admin-Flag gesetzt ist**:
```sql
SELECT email, is_admin FROM users WHERE email = 'admin@localhost';
```

**Admin-Status prüfen**:
```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/auth/me
```

### 3. Permission Denied im Admin-Interface

**Frontend-Prüfung**: Das Admin-Interface prüft `user.is_admin`
**Backend-Prüfung**: Admin-API prüft Datenbank-Flag

**Debug-Steps**:
1. Login-Response prüfen (`is_admin: true`?)
2. Admin-API Logs prüfen
3. Database Admin-Flag prüfen

## Backup und Recovery

### 1. Admin-Benutzer Backup

```sql
-- Export admin users
SELECT id, email, is_admin, created_at 
FROM users 
WHERE is_admin = TRUE;
```

### 2. Emergency Admin Access

Falls der Admin-Zugang verloren geht:

```bash
# Via Init-Script
docker-compose exec fastapi python init_admin.py

# Via SQL
docker-compose exec postgres psql -U postgres -d livestore -c "UPDATE users SET is_admin = TRUE WHERE email = 'your@email.com';"
```

## Performance-Überlegungen

### 1. Admin-Prüfung

Jeder Admin-API-Aufruf führt eine Datenbank-Abfrage durch:
```python
user = await user_db.get_user_by_id(user_id)  # DB-Query
```

**Optimierung**: Caching des Admin-Status im JWT Token möglich, aber Sicherheitsrisiko bei Admin-Status-Änderungen.

### 2. Startup-Performance

Das Admin-Init-Script fügt ~1-2 Sekunden zum Container-Startup hinzu. Bei kritischen Deployments kann es deaktiviert werden durch Entfernen der Environment-Variablen.

## Fazit

Das neue Admin-System bietet:

✅ **Echte System-Administrator-Rolle**
✅ **Automatische Admin-Initialisierung**  
✅ **Environment-Variable-Konfiguration**
✅ **Robuste Fehlerbehandlung**
✅ **Backward-Kompatibilität**
✅ **Klare Sicherheitstrennung**

Die Implementierung ist produktionsreif und folgt Best Practices für Container-basierte Deployments.