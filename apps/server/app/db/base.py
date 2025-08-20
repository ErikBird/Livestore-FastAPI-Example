from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime


class EventStore(ABC):
    
    @abstractmethod
    async def ensure_table(self, store_id: str) -> None:
        pass
    
    @abstractmethod
    async def get_head(self, store_id: str) -> int:
        pass
    
    @abstractmethod
    async def get_events(
        self, 
        store_id: str, 
        cursor: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        pass
    
    @abstractmethod
    async def append_events(
        self,
        store_id: str,
        batch: List[Dict[str, Any]],
        created_at: Optional[datetime] = None
    ) -> None:
        pass
    
    @abstractmethod
    async def reset_store(self, store_id: str) -> None:
        pass