from typing import Dict, List, Optional, Any
from datetime import datetime

from app.core.logging import get_logger
from app.db.postgres import PostgresEventStore
from app.websocket.manager import ConnectionManager

logger = get_logger(__name__)


class EventService:
    
    def __init__(
        self,
        event_store: PostgresEventStore,
        connection_manager: ConnectionManager
    ):
        self.event_store = event_store
        self.connection_manager = connection_manager
    
    async def initialize_store(self, store_id: str) -> int:
        await self.event_store.ensure_table(store_id)
        head = await self.event_store.get_head(store_id)
        self.connection_manager.set_current_head(store_id, head)
        logger.info(f"Store {store_id} initialized with head: {head}")
        return head
    
    async def get_events(
        self, 
        store_id: str, 
        cursor: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        return await self.event_store.get_events(store_id, cursor)
    
    async def append_events(
        self,
        store_id: str,
        events: List[Dict[str, Any]],
        created_at: Optional[datetime] = None
    ) -> int:
        if not events:
            return self.connection_manager.get_current_head(store_id)
        
        await self.event_store.append_events(store_id, events, created_at)
        
        last_seq_num = events[-1]["seq_num"]
        self.connection_manager.set_current_head(store_id, last_seq_num)
        
        logger.info(f"Appended {len(events)} events to store {store_id}, new head: {last_seq_num}")
        return last_seq_num
    
    async def reset_store(self, store_id: str) -> None:
        await self.event_store.reset_store(store_id)
        self.connection_manager.set_current_head(store_id, 0)
        logger.info(f"Store {store_id} reset completed")
    
    def validate_parent_sequence(
        self, 
        store_id: str, 
        parent_seq_num: int
    ) -> tuple[bool, Optional[str]]:
        current_head = self.connection_manager.get_current_head(store_id)
        if parent_seq_num != current_head:
            error_msg = f"Invalid parent event number. Received e{parent_seq_num} but expected e{current_head}"
            return False, error_msg
        return True, None