import asyncio
import json
import logging
from typing import Dict, Set, Optional, Any
from datetime import datetime, timezone
from fastapi import WebSocket, WebSocketDisconnect
from app.message_types import (
    parse_client_message,
    encode_server_message,
    PullReq, PullRes, PullResBatchItem, PullResRequestId,
    PushReq, PushAck,
    Ping, Pong,
    ErrorMessage,
    AdminResetRoomReq, AdminResetRoomRes,
    AdminInfoReq, AdminInfoRes,
    EventEncoded, SyncMetadata, OptionMetadata
)
from app.database import db, PULL_CHUNK_SIZE


logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # Store WebSocket connections per store_id
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Store current head per store
        self.current_heads: Dict[str, int] = {}
        # Semaphore for push operations per store
        self.push_semaphores: Dict[str, asyncio.Semaphore] = {}
        
    async def connect(self, websocket: WebSocket, store_id: str):
        """Accept WebSocket connection and add to store's connection set"""
        logger.debug(f"🔗 ConnectionManager.connect called for store_id: {store_id}")
        await websocket.accept()
        logger.debug(f"✅ WebSocket accepted for store_id: {store_id}")
        
        if store_id not in self.active_connections:
            logger.debug(f"🆕 Creating new connection set for store_id: {store_id}")
            self.active_connections[store_id] = set()
            self.push_semaphores[store_id] = asyncio.Semaphore(1)
        else:
            logger.debug(f"🔄 Using existing connection set for store_id: {store_id}")
            
        self.active_connections[store_id].add(websocket)
        connection_count = len(self.active_connections[store_id])
        logger.info(f"📊 Store {store_id} now has {connection_count} active connection(s)")
        
        # Initialize current head if not already done
        if store_id not in self.current_heads:
            logger.debug(f"📋 Ensuring table exists for store_id: {store_id}")
            await db.ensure_table(store_id)
            logger.debug(f"✅ Table ensured for store_id: {store_id}")
            
            logger.debug(f"🔍 Getting current head for store_id: {store_id}")
            head = await db.get_head(store_id)
            self.current_heads[store_id] = head
            logger.info(f"📊 Store {store_id} initialized with head: {head}")
        else:
            current_head = self.current_heads[store_id]
            logger.debug(f"📊 Store {store_id} already initialized with head: {current_head}")
    
    def disconnect(self, websocket: WebSocket, store_id: str):
        """Remove WebSocket from store's connection set"""
        if store_id in self.active_connections:
            self.active_connections[store_id].discard(websocket)
            
            # Clean up if no more connections for this store
            if not self.active_connections[store_id]:
                del self.active_connections[store_id]
                if store_id in self.current_heads:
                    del self.current_heads[store_id]
                if store_id in self.push_semaphores:
                    del self.push_semaphores[store_id]
    
    async def broadcast_to_store(self, store_id: str, message: str, exclude: Optional[WebSocket] = None):
        """Broadcast message to all connections of a store"""
        if store_id in self.active_connections:
            disconnected = set()
            
            for connection in self.active_connections[store_id]:
                if connection != exclude:
                    try:
                        await connection.send_text(message)
                    except:
                        disconnected.add(connection)
            
            # Clean up disconnected connections
            for conn in disconnected:
                self.active_connections[store_id].discard(conn)


manager = ConnectionManager()


class WebSocketHandler:
    def __init__(self, websocket: WebSocket, store_id: str, payload: Optional[Dict[str, Any]] = None, auth_info: Optional[Dict[str, Any]] = None):
        self.websocket = websocket
        self.store_id = store_id
        self.payload = payload
        self.auth_info = auth_info or {"authenticated": False, "is_admin": False, "user_id": None}
        self.admin_secret = None  # Set from environment in main.py
        
        # Log authentication status
        logger.info(f"WebSocketHandler initialized for store {store_id} - Auth: {self.auth_info['authenticated']}, Admin: {self.auth_info['is_admin']}")
    
    async def handle_pull_req(self, message: PullReq):
        """Handle pull request - send events from cursor"""
        try:
            cursor = message.cursor
            
            # Get events from database
            events = await db.get_events(self.store_id, cursor)
            
            # Send in chunks
            if not events:
                # Send at least one response even if no events
                response = PullRes(
                    batch=[],
                    request_id=PullResRequestId(
                        context="pull",
                        request_id=message.request_id
                    ),
                    remaining=0
                )
                await self.websocket.send_text(encode_server_message(response))
            else:
                # Send events in chunks
                for i in range(0, len(events), PULL_CHUNK_SIZE):
                    chunk = events[i:i + PULL_CHUNK_SIZE]
                    remaining = max(0, len(events) - (i + PULL_CHUNK_SIZE))
                    
                    batch_items = []
                    for event_data in chunk:
                        # Convert metadata to Option format
                        metadata_dict = event_data.get("metadata")
                        if metadata_dict:
                            metadata = OptionMetadata.some(SyncMetadata(**metadata_dict))
                        else:
                            metadata = OptionMetadata.none()
                        
                        batch_items.append(PullResBatchItem(
                            event_encoded=EventEncoded(**event_data["eventEncoded"]),
                            metadata=metadata
                        ))
                    
                    response = PullRes(
                        batch=batch_items,
                        request_id=PullResRequestId(
                            context="pull",
                            request_id=message.request_id
                        ),
                        remaining=remaining
                    )
                    
                    await self.websocket.send_text(encode_server_message(response))
                    
        except Exception as e:
            logger.error(f"Error handling pull request: {e}")
            error_msg = ErrorMessage(
                request_id=message.request_id,
                message=str(e)
            )
            await self.websocket.send_text(encode_server_message(error_msg))
    
    async def handle_push_req(self, message: PushReq):
        """Handle push request - store events and broadcast"""
        # Check if user is authenticated for push operations
        if not self.auth_info.get('authenticated', False):
            logger.warning(f"Unauthenticated push attempt for store {self.store_id}")
            error_msg = ErrorMessage(
                request_id=message.request_id,
                message="Authentication required for push operations"
            )
            await self.websocket.send_text(encode_server_message(error_msg))
            return
            
        semaphore = manager.push_semaphores.get(self.store_id)
        if not semaphore:
            semaphore = asyncio.Semaphore(1)
            manager.push_semaphores[self.store_id] = semaphore
        
        async with semaphore:
            try:
                if not message.batch:
                    # Empty batch, just acknowledge
                    ack = PushAck(request_id=message.request_id)
                    await self.websocket.send_text(encode_server_message(ack))
                    return
                
                # Validate parent sequence number
                current_head = manager.current_heads.get(self.store_id, 0)
                first_event = message.batch[0]
                
                if first_event.parent_seq_num != current_head:
                    error_msg = ErrorMessage(
                        request_id=message.request_id,
                        message=f"Invalid parent event number. Received e{first_event.parent_seq_num} but expected e{current_head}"
                    )
                    await self.websocket.send_text(encode_server_message(error_msg))
                    return
                
                # Send acknowledgment first
                ack = PushAck(request_id=message.request_id)
                await self.websocket.send_text(encode_server_message(ack))
                
                # Convert events to dict format for database
                batch_dicts = []
                for event in message.batch:
                    batch_dicts.append(event.model_dump(by_alias=False))
                
                # Store events in database
                created_at = datetime.now(timezone.utc)
                await db.append_events(self.store_id, batch_dicts, created_at)
                
                # Update current head
                last_event = message.batch[-1]
                manager.current_heads[self.store_id] = last_event.seq_num
                
                # Broadcast to all connected clients
                batch_items = []
                for event in message.batch:
                    # Create metadata with Option format
                    metadata = OptionMetadata.some(
                        SyncMetadata(created_at=created_at.isoformat())
                    )
                    batch_items.append(PullResBatchItem(
                        event_encoded=event,
                        metadata=metadata
                    ))
                
                broadcast_msg = PullRes(
                    batch=batch_items,
                    request_id=PullResRequestId(
                        context="push",
                        request_id=message.request_id
                    ),
                    remaining=0
                )
                
                # Broadcast to all connections including the sender
                await manager.broadcast_to_store(
                    self.store_id,
                    encode_server_message(broadcast_msg)
                )
                
            except Exception as e:
                logger.error(f"Error handling push request: {e}")
                error_msg = ErrorMessage(
                    request_id=message.request_id,
                    message=str(e)
                )
                await self.websocket.send_text(encode_server_message(error_msg))
    
    async def handle_ping(self, message: Ping):
        """Handle ping message"""
        pong = Pong()
        await self.websocket.send_text(encode_server_message(pong))
    
    async def handle_admin_reset(self, message: AdminResetRoomReq):
        """Handle admin reset request"""
        import os
        admin_secret = os.getenv("ADMIN_SECRET", "change-me-admin-secret")
        
        # Check both message admin_secret and auth_info for admin privileges
        is_admin_authenticated = (
            message.admin_secret == admin_secret or 
            self.auth_info.get('is_admin', False)
        )
        
        if not is_admin_authenticated:
            logger.warning(f"Unauthorized admin reset attempt for store {self.store_id}")
            error_msg = ErrorMessage(
                request_id=message.request_id,
                message="Invalid admin secret or insufficient privileges"
            )
            await self.websocket.send_text(encode_server_message(error_msg))
            return
        
        # Reset the store
        await db.reset_store(self.store_id)
        manager.current_heads[self.store_id] = 0
        
        response = AdminResetRoomRes(request_id=message.request_id)
        await self.websocket.send_text(encode_server_message(response))
    
    async def handle_admin_info(self, message: AdminInfoReq):
        """Handle admin info request"""
        import os
        admin_secret = os.getenv("ADMIN_SECRET", "change-me-admin-secret")
        
        # Check both message admin_secret and auth_info for admin privileges
        is_admin_authenticated = (
            message.admin_secret == admin_secret or 
            self.auth_info.get('is_admin', False)
        )
        
        if not is_admin_authenticated:
            logger.warning(f"Unauthorized admin info request for store {self.store_id}")
            error_msg = ErrorMessage(
                request_id=message.request_id,
                message="Invalid admin secret or insufficient privileges"
            )
            await self.websocket.send_text(encode_server_message(error_msg))
            return
        
        response = AdminInfoRes(
            request_id=message.request_id,
            info={
                "durableObjectId": f"python-server-{self.store_id}",
                "storeId": self.store_id,
                "currentHead": manager.current_heads.get(self.store_id, 0),
                "activeConnections": len(manager.active_connections.get(self.store_id, set()))
            }
        )
        await self.websocket.send_text(encode_server_message(response))
    
    async def handle_message(self, data: str):
        """Route incoming message to appropriate handler"""
        try:
            message = parse_client_message(data)
            
            if hasattr(message, '_tag'):
                tag = message._tag
            else:
                tag = message.tag
            
            if tag == "WSMessage.PullReq":
                await self.handle_pull_req(message)
            elif tag == "WSMessage.PushReq":
                await self.handle_push_req(message)
            elif tag == "WSMessage.Ping":
                await self.handle_ping(message)
            elif tag == "WSMessage.AdminResetRoomReq":
                await self.handle_admin_reset(message)
            elif tag == "WSMessage.AdminInfoReq":
                await self.handle_admin_info(message)
            else:
                logger.warning(f"Unknown message type: {tag}")
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            # Try to extract request_id from raw message
            try:
                msg_dict = json.loads(data)
                request_id = msg_dict.get("requestId", "unknown")
            except:
                request_id = "unknown"
            
            # Log the full error for debugging
            logger.exception(f"Full error details for message handling in store {self.store_id}:")
            
            error_msg = ErrorMessage(
                request_id=request_id,
                message=str(e)
            )
            await self.websocket.send_text(encode_server_message(error_msg))