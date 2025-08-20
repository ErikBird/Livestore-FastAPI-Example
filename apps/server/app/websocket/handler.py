import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import WebSocket

from app.core.logging import get_logger
from app.core.config import settings
from app.db.postgres import PostgresEventStore
from .manager import ConnectionManager
from .protocol import (
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

logger = get_logger(__name__)


class WebSocketHandler:
    
    def __init__(
        self,
        websocket: WebSocket,
        store_id: str,
        event_store: PostgresEventStore,
        connection_manager: ConnectionManager,
        payload: Optional[Dict[str, Any]] = None,
        auth_info: Optional[Dict[str, Any]] = None
    ):
        self.websocket = websocket
        self.store_id = store_id
        self.event_store = event_store
        self.connection_manager = connection_manager
        self.payload = payload
        self.auth_info = auth_info or {
            "authenticated": False,
            "is_admin": False,
            "user_id": None
        }
        
        logger.info(
            f"WebSocketHandler initialized for store {store_id} - "
            f"Auth: {self.auth_info['authenticated']}, Admin: {self.auth_info['is_admin']}"
        )
    
    async def handle_pull_req(self, message: PullReq) -> None:
        try:
            cursor = message.cursor
            
            events = await self.event_store.get_events(self.store_id, cursor)
            
            if not events:
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
                for i in range(0, len(events), settings.pull_chunk_size):
                    chunk = events[i:i + settings.pull_chunk_size]
                    remaining = max(0, len(events) - (i + settings.pull_chunk_size))
                    
                    batch_items = []
                    for event_data in chunk:
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
    
    async def handle_push_req(self, message: PushReq) -> None:
        if not self.auth_info.get('authenticated', False):
            logger.warning(f"Unauthenticated push attempt for store {self.store_id}")
            error_msg = ErrorMessage(
                request_id=message.request_id,
                message="Authentication required for push operations"
            )
            await self.websocket.send_text(encode_server_message(error_msg))
            return
        
        semaphore = self.connection_manager.get_push_semaphore(self.store_id)
        
        async with semaphore:
            try:
                if not message.batch:
                    ack = PushAck(request_id=message.request_id)
                    await self.websocket.send_text(encode_server_message(ack))
                    return
                
                current_head = self.connection_manager.get_current_head(self.store_id)
                first_event = message.batch[0]
                
                if first_event.parent_seq_num != current_head:
                    error_msg = ErrorMessage(
                        request_id=message.request_id,
                        message=f"Invalid parent event number. Received e{first_event.parent_seq_num} but expected e{current_head}"
                    )
                    await self.websocket.send_text(encode_server_message(error_msg))
                    return
                
                ack = PushAck(request_id=message.request_id)
                await self.websocket.send_text(encode_server_message(ack))
                
                batch_dicts = []
                for event in message.batch:
                    batch_dicts.append(event.model_dump(by_alias=False))
                
                created_at = datetime.now(timezone.utc)
                await self.event_store.append_events(self.store_id, batch_dicts, created_at)
                
                last_event = message.batch[-1]
                self.connection_manager.set_current_head(self.store_id, last_event.seq_num)
                
                batch_items = []
                for event in message.batch:
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
                
                await self.connection_manager.broadcast_to_store(
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
    
    async def handle_ping(self, message: Ping) -> None:
        pong = Pong()
        await self.websocket.send_text(encode_server_message(pong))
    
    async def handle_admin_reset(self, message: AdminResetRoomReq) -> None:
        is_admin_authenticated = (
            message.admin_secret == settings.admin_secret or 
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
        
        await self.event_store.reset_store(self.store_id)
        self.connection_manager.set_current_head(self.store_id, 0)
        
        response = AdminResetRoomRes(request_id=message.request_id)
        await self.websocket.send_text(encode_server_message(response))
    
    async def handle_admin_info(self, message: AdminInfoReq) -> None:
        is_admin_authenticated = (
            message.admin_secret == settings.admin_secret or 
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
                "currentHead": self.connection_manager.get_current_head(self.store_id),
                "activeConnections": self.connection_manager.get_active_connections(self.store_id)
            }
        )
        await self.websocket.send_text(encode_server_message(response))
    
    async def handle_message(self, data: str) -> None:
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
            try:
                msg_dict = json.loads(data)
                request_id = msg_dict.get("requestId", "unknown")
            except:
                request_id = "unknown"
            
            logger.exception(f"Full error details for message handling in store {self.store_id}:")
            
            error_msg = ErrorMessage(
                request_id=request_id,
                message=str(e)
            )
            await self.websocket.send_text(encode_server_message(error_msg))