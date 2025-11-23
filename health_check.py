import asyncio
from aiohttp import web
import os
import logging

logger = logging.getLogger(__name__)


class HealthCheckServer:
    def __init__(self, bot):
        self.bot = bot
        self.port = int(os.getenv('HEALTH_CHECK_PORT', '8080'))
        self.app = web.Application()
        self.runner = None
        self.setup_routes()
    
    def setup_routes(self):
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_get('/status', self.bot_status)
    
    async def health_check(self, request):
        return web.json_response({
            'status': 'healthy',
            'bot': {
                'ready': self.bot.is_ready(),
                'latency': round(self.bot.latency * 1000, 2) if self.bot.is_ready() else None,
                'guilds': len(self.bot.guilds) if self.bot.is_ready() else 0
            }
        })
    
    async def bot_status(self, request):
        if not self.bot.is_ready():
            return web.json_response({
                'status': 'starting',
                'message': 'Bot is starting up...'
            }, status=503)
        
        return web.json_response({
            'status': 'online',
            'bot_name': self.bot.user.name,
            'bot_id': self.bot.user.id,
            'guilds': len(self.bot.guilds),
            'latency_ms': round(self.bot.latency * 1000, 2),
            'users': sum(guild.member_count for guild in self.bot.guilds)
        })
    
    async def start(self):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, '0.0.0.0', self.port)
        await site.start()
        logger.info(f"Health check server started on port {self.port}")
    
    async def stop(self):
        if self.runner:
            await self.runner.cleanup()
            logger.info("Health check server stopped")
