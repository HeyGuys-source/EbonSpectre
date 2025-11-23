import asyncpg
import os
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta


class DatabaseManager:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is not set")
        
        self.pool = await asyncpg.create_pool(database_url, min_size=2, max_size=10)
        await self.initialize_schema()
    
    async def close(self):
        if self.pool:
            await self.pool.close()
    
    async def initialize_schema(self):
        with open('database/schema.sql', 'r') as f:
            schema_sql = f.read()
        
        async with self.pool.acquire() as conn:
            await conn.execute(schema_sql)
    
    async def get_guild_config(self, guild_id: int) -> Optional[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM guild_configs WHERE guild_id = $1",
                guild_id
            )
            return dict(row) if row else None
    
    async def create_or_update_guild_config(self, guild_id: int, **kwargs):
        async with self.pool.acquire() as conn:
            columns = ['guild_id'] + list(kwargs.keys())
            values = [guild_id] + list(kwargs.values())
            placeholders = ', '.join([f'${i+1}' for i in range(len(values))])
            columns_str = ', '.join(columns)
            
            update_str = ', '.join([f'{k} = EXCLUDED.{k}' for k in kwargs.keys()])
            update_str += ', updated_at = CURRENT_TIMESTAMP'
            
            query = f"""
                INSERT INTO guild_configs ({columns_str})
                VALUES ({placeholders})
                ON CONFLICT (guild_id) DO UPDATE SET {update_str}
            """
            await conn.execute(query, *values)
    
    async def add_warning(self, guild_id: int, user_id: int, moderator_id: int, reason: str) -> int:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO warnings (guild_id, user_id, moderator_id, reason)
                   VALUES ($1, $2, $3, $4) RETURNING id""",
                guild_id, user_id, moderator_id, reason
            )
            return row['id']
    
    async def get_warnings(self, guild_id: int, user_id: int) -> List[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM warnings WHERE guild_id = $1 AND user_id = $2 ORDER BY created_at DESC",
                guild_id, user_id
            )
            return [dict(row) for row in rows]
    
    async def remove_warning(self, warning_id: int, guild_id: int) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM warnings WHERE id = $1 AND guild_id = $2",
                warning_id, guild_id
            )
            return result != "DELETE 0"
    
    async def add_staff_note(self, guild_id: int, user_id: int, staff_id: int, note: str):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO staff_notes (guild_id, user_id, staff_id, note)
                   VALUES ($1, $2, $3, $4)""",
                guild_id, user_id, staff_id, note
            )
    
    async def get_staff_notes(self, guild_id: int, user_id: int) -> List[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM staff_notes WHERE guild_id = $1 AND user_id = $2 ORDER BY created_at DESC",
                guild_id, user_id
            )
            return [dict(row) for row in rows]
    
    async def add_audit_log(self, guild_id: int, action_type: str, moderator_id: Optional[int] = None,
                            target_user_id: Optional[int] = None, details: Optional[str] = None):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO audit_logs (guild_id, moderator_id, action_type, target_user_id, details)
                   VALUES ($1, $2, $3, $4, $5)""",
                guild_id, moderator_id, action_type, target_user_id, details
            )
    
    async def get_audit_logs(self, guild_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM audit_logs WHERE guild_id = $1 ORDER BY created_at DESC LIMIT $2",
                guild_id, limit
            )
            return [dict(row) for row in rows]
    
    async def add_member(self, guild_id: int, user_id: int, username: str, **kwargs):
        async with self.pool.acquire() as conn:
            columns = ['guild_id', 'user_id', 'username'] + list(kwargs.keys())
            values = [guild_id, user_id, username] + list(kwargs.values())
            placeholders = ', '.join([f'${i+1}' for i in range(len(values))])
            columns_str = ', '.join(columns)
            
            update_str = ', '.join([f'{k} = EXCLUDED.{k}' for k in ['username'] + list(kwargs.keys())])
            
            query = f"""
                INSERT INTO members ({columns_str})
                VALUES ({placeholders})
                ON CONFLICT (guild_id, user_id) DO UPDATE SET {update_str}
            """
            await conn.execute(query, *values)
    
    async def get_member(self, guild_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM members WHERE guild_id = $1 AND user_id = $2",
                guild_id, user_id
            )
            return dict(row) if row else None
    
    async def get_all_members(self, guild_id: int) -> List[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM members WHERE guild_id = $1 ORDER BY joined_at ASC",
                guild_id
            )
            return [dict(row) for row in rows]
    
    async def update_member_activity(self, guild_id: int, user_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """UPDATE members SET last_active = CURRENT_TIMESTAMP, is_inactive = FALSE
                   WHERE guild_id = $1 AND user_id = $2""",
                guild_id, user_id
            )
    
    async def mark_inactive_members(self, guild_id: int, threshold_days: int) -> List[int]:
        async with self.pool.acquire() as conn:
            threshold_date = datetime.utcnow() - timedelta(days=threshold_days)
            rows = await conn.fetch(
                """UPDATE members SET is_inactive = TRUE
                   WHERE guild_id = $1 AND last_active < $2 AND is_inactive = FALSE
                   RETURNING user_id""",
                guild_id, threshold_date
            )
            return [row['user_id'] for row in rows]
    
    async def add_role_mapping(self, guild_id: int, discord_role_id: int, clan_rank: str):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO role_mappings (guild_id, discord_role_id, clan_rank)
                   VALUES ($1, $2, $3)
                   ON CONFLICT (guild_id, discord_role_id) DO UPDATE SET clan_rank = EXCLUDED.clan_rank""",
                guild_id, discord_role_id, clan_rank
            )
    
    async def get_role_mappings(self, guild_id: int) -> List[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM role_mappings WHERE guild_id = $1",
                guild_id
            )
            return [dict(row) for row in rows]
    
    async def add_permission(self, guild_id: int, command_name: str, required_role_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO permissions (guild_id, command_name, required_role_id)
                   VALUES ($1, $2, $3)
                   ON CONFLICT (guild_id, command_name, required_role_id) DO NOTHING""",
                guild_id, command_name, required_role_id
            )
    
    async def get_permissions(self, guild_id: int, command_name: str) -> List[int]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT required_role_id FROM permissions WHERE guild_id = $1 AND command_name = $2",
                guild_id, command_name
            )
            return [row['required_role_id'] for row in rows]
    
    async def add_to_blacklist(self, guild_id: int, user_id: int, added_by: int, reason: Optional[str] = None):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO blacklist (guild_id, user_id, added_by, reason)
                   VALUES ($1, $2, $3, $4)
                   ON CONFLICT (guild_id, user_id) DO UPDATE SET reason = EXCLUDED.reason""",
                guild_id, user_id, added_by, reason
            )
    
    async def remove_from_blacklist(self, guild_id: int, user_id: int) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM blacklist WHERE guild_id = $1 AND user_id = $2",
                guild_id, user_id
            )
            return result != "DELETE 0"
    
    async def is_blacklisted(self, guild_id: int, user_id: int) -> bool:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT 1 FROM blacklist WHERE guild_id = $1 AND user_id = $2",
                guild_id, user_id
            )
            return row is not None
    
    async def create_backup(self, guild_id: int, created_by: int) -> int:
        async with self.pool.acquire() as conn:
            backup_data = {
                'config': await self.get_guild_config(guild_id),
                'members': await self.get_all_members(guild_id),
                'role_mappings': await self.get_role_mappings(guild_id),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            row = await conn.fetchrow(
                """INSERT INTO backups (guild_id, backup_data, created_by)
                   VALUES ($1, $2, $3) RETURNING id""",
                guild_id, json.dumps(backup_data, default=str), created_by
            )
            return row['id']
    
    async def get_backup(self, backup_id: int, guild_id: int) -> Optional[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM backups WHERE id = $1 AND guild_id = $2",
                backup_id, guild_id
            )
            if row:
                result = dict(row)
                result['backup_data'] = json.loads(result['backup_data'])
                return result
            return None
    
    async def get_all_backups(self, guild_id: int) -> List[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, guild_id, created_by, created_at FROM backups WHERE guild_id = $1 ORDER BY created_at DESC",
                guild_id
            )
            return [dict(row) for row in rows]
    
    async def add_mute(self, guild_id: int, user_id: int, moderator_id: int, expires_at: datetime, reason: Optional[str] = None):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO mutes (guild_id, user_id, moderator_id, expires_at, reason)
                   VALUES ($1, $2, $3, $4, $5)
                   ON CONFLICT (guild_id, user_id) DO UPDATE SET expires_at = EXCLUDED.expires_at, reason = EXCLUDED.reason""",
                guild_id, user_id, moderator_id, expires_at, reason
            )
    
    async def remove_mute(self, guild_id: int, user_id: int) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM mutes WHERE guild_id = $1 AND user_id = $2",
                guild_id, user_id
            )
            return result != "DELETE 0"
    
    async def get_expired_mutes(self) -> List[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM mutes WHERE expires_at <= CURRENT_TIMESTAMP"
            )
            return [dict(row) for row in rows]
    
    async def is_muted(self, guild_id: int, user_id: int) -> bool:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT 1 FROM mutes WHERE guild_id = $1 AND user_id = $2 AND expires_at > CURRENT_TIMESTAMP",
                guild_id, user_id
            )
            return row is not None
