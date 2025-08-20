import asyncio
from typing import Dict, Set, Optional
from fastapi import WebSocket

from app.core.logging import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.current_heads: Dict[str, int] = {}
        self.push_semaphores: Dict[str, asyncio.Semaphore] = {}
    
    async def connect(self, websocket: WebSocket, store_id: str) -> None:
        logger.debug(f"ConnectionManager.connect called for store_id: {store_id}")
        await websocket.accept()
        logger.debug(f"WebSocket accepted for store_id: {store_id}")
        
        if store_id not in self.active_connections:
            logger.debug(f"Creating new connection set for store_id: {store_id}")
            self.active_connections[store_id] = set()
            self.push_semaphores[store_id] = asyncio.Semaphore(1)
        
        self.active_connections[store_id].add(websocket)
        connection_count = len(self.active_connections[store_id])
        logger.info(f"Store {store_id} now has {connection_count} active connection(s)")
    
    def disconnect(self, websocket: WebSocket, store_id: str) -> None:
        if store_id in self.active_connections:
            self.active_connections[store_id].discard(websocket)
            
            if not self.active_connections[store_id]:
                del self.active_connections[store_id]
                if store_id in self.current_heads:
                    del self.current_heads[store_id]
                if store_id in self.push_semaphores:
                    del self.push_semaphores[store_id]
    
    async def broadcast_to_store(
        self, 
        store_id: str, 
        message: str, 
        exclude: Optional[WebSocket] = None
    ) -> None:
        if store_id in self.active_connections:
            disconnected = set()
            
            for connection in self.active_connections[store_id]:
                if connection != exclude:
                    try:
                        await connection.send_text(message)
                    except:
                        disconnected.add(connection)
            
            for conn in disconnected:
                self.active_connections[store_id].discard(conn)
    
    def get_active_connections(self, store_id: str) -> int:
        return len(self.active_connections.get(store_id, set()))
    
    def get_current_head(self, store_id: str) -> int:
        return self.current_heads.get(store_id, 0)
    
    def set_current_head(self, store_id: str, head: int) -> None:
        self.current_heads[store_id] = head
    
    def get_push_semaphore(self, store_id: str) -> asyncio.Semaphore:
        if store_id not in self.push_semaphores:
            self.push_semaphores[store_id] = asyncio.Semaphore(1)
        return self.push_semaphores[store_id]