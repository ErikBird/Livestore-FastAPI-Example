import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import asyncpg

from app.core.logging import get_logger
from app.core.config import settings
from .base import EventStore

logger = get_logger(__name__)


class PostgresEventStore(EventStore):
    
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
        self.persistence_version = settings.persistence_format_version
    
    def _get_table_name(self, store_id: str) -> str:
        safe_store_id = re.sub(r"[^a-zA-Z0-9]", "_", store_id)
        table_name = f"eventlog_{self.persistence_version}_{safe_store_id}"
        logger.debug(f"Generated table name for store_id '{store_id}': {table_name}")
        return table_name
    
    async def ensure_table(self, store_id: str) -> None:
        table_name = self._get_table_name(store_id)
        logger.debug(f"Ensuring table {table_name} exists for store_id: {store_id}")
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        seq_num BIGINT PRIMARY KEY,
                        parent_seq_num BIGINT NOT NULL,
                        name TEXT NOT NULL,
                        args JSONB,
                        created_at TIMESTAMPTZ NOT NULL,
                        client_id TEXT NOT NULL,
                        session_id TEXT NOT NULL
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_{table_name}_seq 
                    ON {table_name}(seq_num);
                """)
                logger.info(f"Table {table_name} ensured for store_id: {store_id}")
        except Exception as e:
            logger.error(f"Error ensuring table {table_name} for store_id {store_id}: {e}")
            raise
    
    async def get_head(self, store_id: str) -> int:
        table_name = self._get_table_name(store_id)
        logger.debug(f"Getting head for store_id: {store_id}")
        
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(f"""
                    SELECT seq_num FROM {table_name} 
                    ORDER BY seq_num DESC LIMIT 1
                """)
                
                head = row["seq_num"] if row else 0
                logger.info(f"Head for store_id {store_id}: {head}")
                return head
        except Exception as e:
            logger.error(f"Error getting head for store_id {store_id}: {e}")
            raise
    
    async def get_events(
        self, 
        store_id: str, 
        cursor: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        table_name = self._get_table_name(store_id)
        logger.debug(f"Getting events for store_id: {store_id}, cursor: {cursor}")
        
        where_clause = "" if cursor is None else f"WHERE seq_num > {cursor}"
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(f"""
                    SELECT * FROM {table_name} 
                    {where_clause}
                    ORDER BY seq_num ASC
                """)
                
                events = []
                for row in rows:
                    args = row["args"]
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except (json.JSONDecodeError, TypeError):
                            pass
                    
                    event = {
                        "eventEncoded": {
                            "seqNum": row["seq_num"],
                            "parentSeqNum": row["parent_seq_num"],
                            "name": row["name"],
                            "args": args,
                            "clientId": row["client_id"],
                            "sessionId": row["session_id"],
                        },
                        "metadata": {"createdAt": row["created_at"].isoformat()}
                        if row["created_at"]
                        else None,
                    }
                    events.append(event)
                
                logger.info(f"Retrieved {len(events)} events for store_id {store_id}")
                return events
        except Exception as e:
            logger.error(f"Error retrieving events for store_id {store_id}: {e}")
            raise
    
    async def append_events(
        self,
        store_id: str,
        batch: List[Dict[str, Any]],
        created_at: Optional[datetime] = None
    ) -> None:
        if not batch:
            logger.debug(f"Empty batch for store_id {store_id}, nothing to append")
            return
        
        table_name = self._get_table_name(store_id)
        
        if created_at is None:
            created_at = datetime.now(timezone.utc)
        
        logger.debug(f"Appending {len(batch)} events to {table_name}")
        
        try:
            async with self.pool.acquire() as conn:
                CHUNK_SIZE = 100
                
                for i in range(0, len(batch), CHUNK_SIZE):
                    chunk = batch[i:i + CHUNK_SIZE]
                    
                    values = []
                    for event in chunk:
                        args = event.get("args")
                        if args is not None and not isinstance(args, str):
                            args = json.dumps(args)
                        
                        values.append((
                            event["seq_num"],
                            event["parent_seq_num"],
                            event["name"],
                            args,
                            created_at,
                            event["client_id"],
                            event["session_id"],
                        ))
                    
                    await conn.executemany(
                        f"""
                        INSERT INTO {table_name} 
                        (seq_num, parent_seq_num, name, args, created_at, client_id, session_id)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                        """,
                        values
                    )
                
                logger.info(f"Appended {len(batch)} events to store_id {store_id}")
        except Exception as e:
            logger.error(f"Error appending events to store_id {store_id}: {e}")
            raise
    
    async def reset_store(self, store_id: str) -> None:
        table_name = self._get_table_name(store_id)
        logger.info(f"Resetting store {store_id}")
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"DROP TABLE IF EXISTS {table_name}")
                logger.info(f"Table {table_name} dropped")
                
                await self.ensure_table(store_id)
                logger.info(f"Store {store_id} reset completed")
        except Exception as e:
            logger.error(f"Error resetting store {store_id}: {e}")
            raise