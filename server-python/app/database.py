import asyncio
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import asyncpg

logger = logging.getLogger(__name__)


PERSISTENCE_FORMAT_VERSION = 7
PULL_CHUNK_SIZE = 100


class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.lock = asyncio.Lock()

    async def connect(self):
        """Initialize database connection"""
        logger.info(f"💾 Database.connect called")

        if self.pool:
            logger.debug(f"📊 Database connection already exists")
            return

        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            raise ValueError("DATABASE_URL environment variable is required")

        if not db_url.startswith("postgresql"):
            raise ValueError(f"Only PostgreSQL is supported. Got: {db_url}")

        logger.info(f"🔗 Connecting to database: {db_url}")

        try:
            safe_db_url = db_url
            if "@" in db_url:
                parts = db_url.split("@")
                safe_db_url = (
                    parts[0].split("://")[0] + "://***:***@" + "@".join(parts[1:])
                )
            logger.info(f"🔗 Connecting to PostgreSQL: {safe_db_url}")

            self.pool = await asyncpg.create_pool(
                db_url, min_size=5, max_size=20, command_timeout=60
            )
            logger.info(
                f"✅ PostgreSQL connection pool created successfully (min: 5, max: 20)"
            )

            # Test database connection
            async with self.pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                logger.info(f"✅ PostgreSQL connection test successful: {result}")

        except Exception as e:
            logger.error(f"❌ Failed to create PostgreSQL connection pool: {e}")
            raise

    async def disconnect(self):
        """Close connection pool"""
        logger.info(f"🔌 Database.disconnect called")

        if self.pool:
            try:
                await self.pool.close()
                self.pool = None
                logger.info(f"✅ Database connection pool closed successfully")
            except Exception as e:
                logger.error(f"❌ Error closing database connection pool: {e}")
        else:
            logger.debug(f"📊 No database connection pool to close")

    def _get_table_name(self, store_id: str) -> str:
        """Generate table name from store_id"""
        safe_store_id = re.sub(r"[^a-zA-Z0-9]", "_", store_id)
        table_name = f"eventlog_{PERSISTENCE_FORMAT_VERSION}_{safe_store_id}"
        logger.debug(f"🏷️ Generated table name for store_id '{store_id}': {table_name}")
        return table_name

    async def ensure_table(self, store_id: str):
        """Create table if it doesn't exist"""
        table_name = self._get_table_name(store_id)
        logger.debug(
            f"📋 Database.ensure_table called for store_id: {store_id}, table_name: {table_name}"
        )

        try:
            async with self.pool.acquire() as conn:
                logger.debug(f"💾 Creating table {table_name} if not exists...")
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
                logger.info(f"✅ Table {table_name} ensured for store_id: {store_id}")
        except Exception as e:
            logger.error(
                f"❌ Error ensuring table {table_name} for store_id {store_id}: {e}"
            )
            raise

    async def get_head(self, store_id: str) -> int:
        """Get the latest sequence number for a store"""
        table_name = self._get_table_name(store_id)
        logger.debug(
            f"🔍 Database.get_head called for store_id: {store_id}, table_name: {table_name}"
        )

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(f"""
                    SELECT seq_num FROM {table_name} 
                    ORDER BY seq_num DESC LIMIT 1
                """)

                head = row["seq_num"] if row else 0
                logger.info(f"📊 Head for store_id {store_id}: {head}")
                return head
        except Exception as e:
            logger.error(f"❌ Error getting head for store_id {store_id}: {e}")
            raise

    async def get_events(
        self, store_id: str, cursor: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve events from the database"""
        table_name = self._get_table_name(store_id)
        logger.debug(
            f"🔍 Database.get_events called for store_id: {store_id}, cursor: {cursor}, table_name: {table_name}"
        )

        where_clause = "" if cursor is None else f"WHERE seq_num > {cursor}"

        try:
            async with self.pool.acquire() as conn:
                logger.debug(
                    f"💾 Querying events from {table_name} with cursor {cursor}..."
                )
                rows = await conn.fetch(f"""
                    SELECT * FROM {table_name} 
                    {where_clause}
                    ORDER BY seq_num ASC
                """)

                events = []
                for idx, row in enumerate(rows):
                    event = {
                        "eventEncoded": {
                            "seqNum": row["seq_num"],
                            "parentSeqNum": row["parent_seq_num"],
                            "name": row["name"],
                            "args": row["args"],
                            "clientId": row["client_id"],
                            "sessionId": row["session_id"],
                        },
                        "metadata": {"createdAt": row["created_at"].isoformat()}
                        if row["created_at"]
                        else None,
                    }
                    events.append(event)
                    logger.debug(
                        f"📋 Event {idx + 1}: seq_num={row['seq_num']}, name={row['name']}"
                    )

                logger.info(
                    f"📊 Retrieved {len(events)} event(s) for store_id {store_id} from cursor {cursor}"
                )
                return events
        except Exception as e:
            logger.error(f"❌ Error retrieving events for store_id {store_id}: {e}")
            raise

    async def append_events(
        self,
        store_id: str,
        batch: List[Dict[str, Any]],
        created_at: Optional[datetime] = None,
    ):
        """Append events to the database"""
        logger.info(
            f"💾 Database.append_events called for store_id: {store_id}, batch size: {len(batch)}"
        )

        if not batch:
            logger.debug(f"📦 Empty batch for store_id {store_id}, nothing to append")
            return

        table_name = self._get_table_name(store_id)

        if created_at is None:
            created_at = datetime.utcnow()

        logger.debug(
            f"💾 Appending {len(batch)} event(s) to {table_name} at {created_at}"
        )

        try:
            async with self.pool.acquire() as conn:
                # PostgreSQL doesn't have the same insert limits as D1
                # But we'll chunk for consistency
                CHUNK_SIZE = 100

                for i in range(0, len(batch), CHUNK_SIZE):
                    chunk = batch[i : i + CHUNK_SIZE]
                    chunk_num = (i // CHUNK_SIZE) + 1
                    total_chunks = (len(batch) + CHUNK_SIZE - 1) // CHUNK_SIZE

                    logger.debug(
                        f"📦 Processing chunk {chunk_num}/{total_chunks} ({len(chunk)} events)"
                    )

                    # Prepare values for bulk insert
                    values = []
                    for idx, event in enumerate(chunk):
                        values.append(
                            (
                                event["seq_num"],
                                event["parent_seq_num"],
                                event["name"],
                                event.get("args"),  # JSONB column handles serialization
                                created_at,
                                event["client_id"],
                                event["session_id"],
                            )
                        )
                        logger.debug(
                            f"📋 Chunk {chunk_num} Event {idx + 1}: seq_num={event['seq_num']}, name={event['name']}"
                        )

                    # Use executemany for efficient bulk insert
                    logger.debug(f"💾 Inserting chunk {chunk_num} into {table_name}...")
                    await conn.executemany(
                        f"""
                        INSERT INTO {table_name} 
                        (seq_num, parent_seq_num, name, args, created_at, client_id, session_id)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                        values,
                    )
                    logger.info(
                        f"✅ Chunk {chunk_num}/{total_chunks} inserted successfully"
                    )

            logger.info(
                f"✅ All {len(batch)} event(s) appended successfully to store_id {store_id}"
            )
        except Exception as e:
            logger.error(f"❌ Error appending events to store_id {store_id}: {e}")
            raise

    async def reset_store(self, store_id: str):
        """Drop and recreate the table for a store"""
        table_name = self._get_table_name(store_id)
        logger.info(
            f"🧹 Database.reset_store called for store_id: {store_id}, table_name: {table_name}"
        )

        try:
            async with self.pool.acquire() as conn:
                logger.debug(f"🗑️ Dropping table {table_name}...")
                await conn.execute(f"DROP TABLE IF EXISTS {table_name}")
                logger.info(f"✅ Table {table_name} dropped")

                logger.debug(f"📋 Recreating table {table_name}...")
                await self.ensure_table(store_id)
                logger.info(f"✅ Store {store_id} reset completed")
        except Exception as e:
            logger.error(f"❌ Error resetting store {store_id}: {e}")
            raise


# Global database instance
db = Database()
