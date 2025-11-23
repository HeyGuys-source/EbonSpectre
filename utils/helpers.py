import discord
from datetime import datetime, timedelta
from typing import Optional
import re


def parse_duration(duration_str: str) -> Optional[timedelta]:
    pattern = r'(\d+)([smhd])'
    matches = re.findall(pattern, duration_str.lower())
    
    if not matches:
        return None
    
    total_seconds = 0
    for value, unit in matches:
        value = int(value)
        if unit == 's':
            total_seconds += value
        elif unit == 'm':
            total_seconds += value * 60
        elif unit == 'h':
            total_seconds += value * 3600
        elif unit == 'd':
            total_seconds += value * 86400
    
    return timedelta(seconds=total_seconds)


def format_duration(td: timedelta) -> str:
    total_seconds = int(td.total_seconds())
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0:
        parts.append(f"{seconds}s")
    
    return ' '.join(parts) if parts else "0s"


async def has_permissions(db, interaction: discord.Interaction, command_name: str) -> bool:
    if interaction.user.guild_permissions.administrator:
        return True
    
    is_blacklisted = await db.is_blacklisted(interaction.guild.id, interaction.user.id)
    if is_blacklisted:
        return False
    
    required_roles = await db.get_permissions(interaction.guild.id, command_name)
    
    if not required_roles:
        return True
    
    user_role_ids = [role.id for role in interaction.user.roles]
    return any(role_id in user_role_ids for role_id in required_roles)
