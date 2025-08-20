import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from urllib.parse import unquote

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.authentication import AuthenticationMiddleware
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root (two levels up from this file)
project_root = Path(__file__).parent.parent.parent.parent
env_file = project_root / ".env"
load_dotenv(env_file)

from app.core import settings, setup_logging
from app.core.dependencies import init_db_pool, close_db_pool, get_db_pool
from app.core.logging import get_logger
from app.auth import CustomAuthBackend, WebSocketAuth
from app.db import PostgresEventStore, UserRepository
from app.websocket import ConnectionManager, WebSocketHandler
from app.services import EventService
from app.api import api_router

load_dotenv()

setup_logging(settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting up FastAPI server...")
    logger.debug(f"Environment: DATABASE_URL={settings.safe_database_url}")
    logger.debug(f"Environment: AUTH_TOKEN={'SET' if settings.auth_token else 'NOT SET'}")
    logger.debug(f"Environment: ADMIN_SECRET={'SET' if settings.admin_secret else 'NOT SET'}")
    
    try:
        pool = await init_db_pool()
        logger.info("✅ Database connection pool initialized successfully")
        
        user_db = UserRepository(pool)
        await user_db.create_tables()
        logger.info("✅ User database tables initialized")
        
        # Initialize admin user from environment variables
        admin_email = settings.admin_email
        admin_password = settings.admin_password
        
        if admin_email and admin_password:
            try:
                admin_user = await user_db.ensure_admin_user(admin_email, admin_password)
                logger.info(f"✅ Admin user ready: {admin_user.email} (ID: {admin_user.id})")
            except Exception as e:
                logger.error(f"❌ Failed to initialize admin user: {e}")
        else:
            logger.warning("⚠️ Admin user not configured (ADMIN_EMAIL and ADMIN_PASSWORD required)")
        
        app.state.db_pool = pool
        app.state.connection_manager = ConnectionManager()
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        raise
    
    yield
    
    logger.info("🛑 Shutting down FastAPI server...")
    try:
        await close_db_pool()
        logger.info("✅ Database connection pool closed successfully")
    except Exception as e:
        logger.error(f"❌ Error closing database connection: {e}")


app = FastAPI(
    title="LiveStore Sync Server",
    description="Python/FastAPI implementation compatible with @livestore/sync-cf",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    AuthenticationMiddleware,
    backend=CustomAuthBackend(),
    on_error=lambda conn, exc: PlainTextResponse(
        "Authentication failed", 
        status_code=401
    )
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
async def root():
    logger.debug("Root endpoint accessed")
    return PlainTextResponse(
        "Info: WebSocket sync backend endpoint for @livestore/sync-cf (Python/FastAPI implementation).",
        status_code=200
    )


@app.websocket("/websocket")
async def websocket_endpoint(
    websocket: WebSocket,
    storeId: str = Query(..., description="Store identifier"),
    payload: str = Query(None, description="Optional payload (URL-encoded JSON)")
):
    ws_auth = WebSocketAuth()
    
    parsed_payload = None
    auth_info = None
    logger.info(f"🔌 WebSocket connection attempt for storeId: {storeId}")
    logger.debug(f"📦 Raw payload received: {payload}")
    
    if payload:
        try:
            decoded_payload = unquote(payload)
            logger.debug(f"📦 Decoded payload: {decoded_payload}")
            parsed_payload = json.loads(decoded_payload)
            logger.debug(f"📦 Parsed payload: {parsed_payload}")
            
            try:
                auth_info = ws_auth.validate_payload(parsed_payload)
                logger.info(f"✅ WebSocket auth validated - authenticated: {auth_info['authenticated']}, admin: {auth_info['is_admin']}")
            except ValueError as auth_error:
                logger.error(f"❌ Authentication failed for storeId {storeId}: {auth_error}")
                await websocket.close(code=1008, reason=str(auth_error))
                return
                
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse payload JSON: {e}")
            await websocket.close(code=1003, reason="Invalid JSON payload format")
            return
        except Exception as e:
            logger.error(f"❌ Unexpected error parsing payload: {e}")
            logger.exception("Full traceback:")
            await websocket.close(code=1003, reason="Invalid payload format")
            return
    else:
        auth_info = ws_auth.validate_payload(None)
        logger.info(f"📦 No payload provided, using default auth: authenticated={auth_info['authenticated']}")
    
    connection_manager = app.state.connection_manager
    
    logger.debug(f"🔗 Attempting to connect WebSocket for storeId: {storeId}")
    await connection_manager.connect(websocket, storeId)
    logger.info(f"✅ WebSocket connected for store: {storeId}")
    
    pool = app.state.db_pool
    event_store = PostgresEventStore(pool)
    event_service = EventService(event_store, connection_manager)
    
    if storeId not in connection_manager.current_heads:
        await event_service.initialize_store(storeId)
    
    handler = WebSocketHandler(
        websocket=websocket,
        store_id=storeId,
        event_store=event_store,
        connection_manager=connection_manager,
        payload=parsed_payload,
        auth_info=auth_info
    )
    
    logger.debug(f"🔧 WebSocket handler created for storeId: {storeId} with auth_info: {auth_info}")
    
    active_count = connection_manager.get_active_connections(storeId)
    current_head = connection_manager.get_current_head(storeId)
    logger.info(f"📊 Store {storeId} - Active connections: {active_count}, Current head: {current_head}")
    
    try:
        while True:
            logger.debug(f"👂 Waiting for message from storeId: {storeId}")
            data = await websocket.receive_text()
            logger.debug(f"📨 Received message from storeId {storeId}: {data[:100]}..." if len(data) > 100 else f"📨 Received message from storeId {storeId}: {data}")
            
            await handler.handle_message(data)
            logger.debug(f"✅ Message handled for storeId: {storeId}")
            
    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket disconnected normally for store: {storeId}")
        connection_manager.disconnect(websocket, storeId)
        remaining_connections = connection_manager.get_active_connections(storeId)
        logger.info(f"📊 Store {storeId} - Remaining connections: {remaining_connections}")
    except Exception as e:
        logger.error(f"❌ WebSocket error for store {storeId}: {e}")
        logger.exception("Full exception traceback:")
        connection_manager.disconnect(websocket, storeId)
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except Exception as close_e:
            logger.error(f"❌ Error closing WebSocket: {close_e}")


if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"🚀 Starting server on {settings.host}:{settings.port}")
    logger.info(f"🔧 Reload mode: True")
    logger.info(f"📝 Log level: {settings.log_level.lower()}")
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level=settings.log_level.lower()
    )