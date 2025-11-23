import discord
from discord.ext import commands, tasks
import os
import asyncio
import logging
from dotenv import load_dotenv
from database import DatabaseManager
from health_check import HealthCheckServer

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ClanBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        intents.guilds = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
        
        self.db = DatabaseManager()
        self.health_server = HealthCheckServer(self)
    
    async def setup_hook(self):
        logger.info("Connecting to database...")
        await self.db.connect()
        logger.info("Database connected successfully")
        
        logger.info("Loading cogs...")
        cogs = ['cogs.utility', 'cogs.admin', 'cogs.moderation', 'cogs.members']
        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"Loaded cog: {cog}")
            except Exception as e:
                logger.error(f"Failed to load cog {cog}: {e}")
        
        logger.info("Starting health check server...")
        await self.health_server.start()
        
        logger.info("Starting background tasks...")
        self.check_expired_mutes.start()
    
    async def on_ready(self):
        logger.info(f"Bot is ready! Logged in as {self.user.name} ({self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guild(s)")
        
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} command(s)")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")
    
    async def on_guild_join(self, guild):
        logger.info(f"Joined new guild: {guild.name} ({guild.id})")
        await self.db.create_or_update_guild_config(
            guild.id,
            audit_log_enabled=True,
            activity_threshold_days=7
        )
    
    async def on_member_update(self, before, after):
        if before.roles != after.roles:
            config = await self.db.get_guild_config(after.guild.id)
            if config and config.get('auto_roles_enabled'):
                role_mappings = await self.db.get_role_mappings(after.guild.id)
                
                for mapping in role_mappings:
                    role = after.guild.get_role(mapping['discord_role_id'])
                    if role in after.roles and role not in before.roles:
                        member_data = await self.db.get_member(after.guild.id, after.id)
                        if member_data:
                            await self.db.add_member(
                                after.guild.id,
                                after.id,
                                str(after),
                                clan_rank=mapping['clan_rank']
                            )
    
    @tasks.loop(minutes=5)
    async def check_expired_mutes(self):
        try:
            expired_mutes = await self.db.get_expired_mutes()
            
            for mute in expired_mutes:
                guild = self.get_guild(mute['guild_id'])
                if not guild:
                    continue
                
                member = guild.get_member(mute['user_id'])
                if member:
                    try:
                        await member.timeout(None)
                    except discord.Forbidden:
                        pass
                
                await self.db.remove_mute(mute['guild_id'], mute['user_id'])
        except Exception as e:
            logger.error(f"Error checking expired mutes: {e}")
    
    @check_expired_mutes.before_loop
    async def before_check_expired_mutes(self):
        await self.wait_until_ready()
    
    async def close(self):
        logger.info("Shutting down bot...")
        self.check_expired_mutes.cancel()
        await self.health_server.stop()
        await self.db.close()
        await super().close()


async def main():
    bot_token = os.getenv('DISCORD_BOT_TOKEN')
    
    if not bot_token:
        logger.error("DISCORD_BOT_TOKEN not found in environment variables!")
        return
    
    bot = ClanBot()
    
    try:
        await bot.start(bot_token)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
    finally:
        await bot.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
