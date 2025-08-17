import os
import json
import logging
from datetime import datetime, timezone
from urllib.parse import unquote
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException, Depends, Request
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.authentication import AuthenticationMiddleware
from dotenv import load_dotenv
from app.database import db
from app.websocket_handler import WebSocketHandler, manager
from app.auth import CustomAuthBackend, WebSocketAuth, BearerTokenAuth

# Load environment variables from .env file
load_dotenv()


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    logger.info("🚀 Starting up FastAPI server...")
    logger.debug(f"Environment variables: DATABASE_URL present: {'DATABASE_URL' in os.environ}")
    logger.debug(f"Environment variables: AUTH_TOKEN={os.getenv('AUTH_TOKEN', 'NOT SET')}")
    logger.debug(f"Environment variables: ADMIN_SECRET={os.getenv('ADMIN_SECRET', 'NOT SET')}")
    
    try:
        await db.connect()
        logger.info("✅ Database connection pool initialized successfully")
        # Test database connection
        async with db.pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            logger.info(f"✅ Database connection test successful: {result}")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down FastAPI server...")
    try:
        await db.disconnect()
        logger.info("✅ Database connection pool closed successfully")
    except Exception as e:
        logger.error(f"❌ Error closing database connection: {e}")


app = FastAPI(
    title="LiveStore Sync Server",
    description="Python/FastAPI implementation compatible with @livestore/sync-cf",
    version="1.0.0",
    lifespan=lifespan
)

# Add Authentication Middleware
app.add_middleware(
    AuthenticationMiddleware,
    backend=CustomAuthBackend(),
    on_error=lambda conn, exc: PlainTextResponse(
        "Authentication failed", 
        status_code=401
    )
)

# Enable CORS (must be added after authentication middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint - informational"""
    logger.debug("📝 Root endpoint accessed")
    return PlainTextResponse(
        "Info: WebSocket sync backend endpoint for @livestore/sync-cf (Python/FastAPI implementation).",
        status_code=200
    )


@app.get("/health")
async def health_check(request: Request):
    """Health check endpoint"""
    logger.debug("🏥 Health check endpoint accessed")
    
    # Log authentication status if available
    if hasattr(request, 'user'):
        is_authenticated = request.user.is_authenticated
        logger.debug(f"Health check called by {'authenticated' if is_authenticated else 'unauthenticated'} user")
    else:
        logger.debug("Health check called without auth context")
    
    # Test database connection
    db_status = "unknown"
    try:
        if db.pool:
            async with db.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            db_status = "healthy"
            logger.debug("✅ Database health check passed")
        else:
            db_status = "no_connection"
            logger.warning("⚠️  Database pool not initialized")
    except Exception as e:
        db_status = f"error: {str(e)}"
        logger.error(f"❌ Database health check failed: {e}")
    
    return {
        "status": "healthy",
        "implementation": "python-fastapi",
        "compatible_with": "@livestore/sync-cf",
        "database_status": db_status,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.websocket("/websocket")
async def websocket_endpoint(
    websocket: WebSocket,
    storeId: str = Query(..., description="Store identifier"),
    payload: str = Query(None, description="Optional payload (URL-encoded JSON)")
):
    """
    WebSocket endpoint compatible with @livestore/sync-cf protocol
    
    URL Parameters:
    - storeId: Unique identifier for the store
    - payload: Optional URL-encoded JSON payload for authentication/context
    """
    
    # Initialize WebSocket authentication handler
    ws_auth = WebSocketAuth()
    
    # Parse payload if provided
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
            
            # Validate authentication
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
        # No payload provided, use default auth info
        auth_info = ws_auth.validate_payload(None)
        logger.info(f"📦 No payload provided, using default auth: authenticated={auth_info['authenticated']}")
    
    # Accept WebSocket connection
    logger.debug(f"🔗 Attempting to connect WebSocket for storeId: {storeId}")
    await manager.connect(websocket, storeId)
    logger.info(f"✅ WebSocket connected for store: {storeId}")
    
    # Create handler for this connection with auth info
    handler = WebSocketHandler(websocket, storeId, parsed_payload, auth_info)
    logger.debug(f"🔧 WebSocket handler created for storeId: {storeId} with auth_info: {auth_info}")
    
    # Log connection stats
    active_count = len(manager.active_connections.get(storeId, set()))
    current_head = manager.current_heads.get(storeId, -1)
    logger.info(f"📊 Store {storeId} - Active connections: {active_count}, Current head: {current_head}")
    
    try:
        # Set up ping/pong auto-response
        # Note: FastAPI's WebSocket doesn't have setWebSocketAutoResponse equivalent
        # We'll handle ping manually in the message loop
        
        while True:
            # Receive message from client
            logger.debug(f"👂 Waiting for message from storeId: {storeId}")
            data = await websocket.receive_text()
            logger.debug(f"📨 Received message from storeId {storeId}: {data[:100]}..." if len(data) > 100 else f"📨 Received message from storeId {storeId}: {data}")
            
            # Handle the message
            await handler.handle_message(data)
            logger.debug(f"✅ Message handled for storeId: {storeId}")
            
    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket disconnected normally for store: {storeId}")
        manager.disconnect(websocket, storeId)
        remaining_connections = len(manager.active_connections.get(storeId, set()))
        logger.info(f"📊 Store {storeId} - Remaining connections: {remaining_connections}")
    except Exception as e:
        logger.error(f"❌ WebSocket error for store {storeId}: {e}")
        logger.exception("Full exception traceback:")
        manager.disconnect(websocket, storeId)
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except Exception as close_e:
            logger.error(f"❌ Error closing WebSocket: {close_e}")


@app.get("/protected")
async def protected_endpoint(request: Request):
    """Protected endpoint that requires authentication"""
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        logger.warning("Unauthorized access attempt to protected endpoint")
        raise HTTPException(status_code=401, detail="Authentication required")
    
    logger.info(f"Protected endpoint accessed by authenticated user")
    return {
        "message": "This is a protected resource",
        "user": request.user.username if hasattr(request.user, 'username') else "authenticated_user"
    }


@app.get("/admin")
async def admin_endpoint(request: Request):
    """Admin endpoint that requires admin authentication"""
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        logger.warning("Unauthorized access attempt to admin endpoint")
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Check if user has admin scope
    if not hasattr(request, 'auth') or 'admin' not in request.auth.scopes:
        logger.warning("Non-admin user attempted to access admin endpoint")
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    logger.info("Admin endpoint accessed by admin user")
    return {
        "message": "Admin access granted",
        "admin": True
    }


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"🚀 Starting server on {host}:{port}")
    logger.info(f"🔧 Reload mode: True")
    logger.info(f"📝 Log level: debug")
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True,
        log_level="debug"
    )