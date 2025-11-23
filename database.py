import asyncpg
import os
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.url = os.getenv("DATABASE_URL")
        self.pool = None

    async def connect(self):
        """Create the asyncpg connection pool."""
        if not self.url:
            raise RuntimeError("DATABASE_URL is not set in environment variables")

        logger.info("Creating asyncpg pool...")
        self.pool = await asyncpg.create_pool(self.url)
        logger.info("Database pool created")

    #
    # ────────────────────────────────────────────────────────────────
    #   REQUIRED METHOD USED BY YOUR BOT
    # ────────────────────────────────────────────────────────────────
    #

    async def create_or_update_guild_config(self, guild_id, audit_log_enabled=True, activity_threshold_days=7):
        """Creates or updates guild config table entry."""
        
        async with self.pool.acquire() as conn:
            # Create table if it does not exist
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS guild_config (
                    guild_id BIGINT PRIMARY KEY,
                    audit_log_enabled BOOLEAN NOT NULL,
                    activity_threshold_days INTEGER NOT NULL
                );
            """)

            # Insert or update row
            await conn.execute("""
                INSERT INTO guild_config (guild_id, audit_log_enabled, activity_threshold_days)
                VALUES ($1, $2, $3)
                ON CONFLICT (guild_id)
                DO UPDATE SET
                    audit_log_enabled = EXCLUDED.audit_log_enabled,
                    activity_threshold_days = EXCLUDED.activity_threshold_days;
            """, guild_id, audit_log_enabled, activity_threshold_days)

            logger.info(f"Updated config for guild {guild_id}")
