# Discord Clan Management Bot

## Project Overview
A feature-rich Discord bot designed for clan management with comprehensive administrative, moderation, and member tracking capabilities. Built with discord.py and PostgreSQL for persistent storage.

## Recent Changes
- 2025-01-23: Initial project setup
  - Created organized cog-based architecture
  - Implemented all 40+ administrative and moderation commands
  - Set up PostgreSQL database with complete schema
  - Added health check endpoint for monitoring
  - Implemented /echo command with multiple format options

## Project Architecture

### Structure
The bot follows a modular cog-based architecture:
- **bot.py**: Main bot entry point with event handlers
- **cogs/**: Separate modules for different command categories
  - admin.py: Administrative commands (setup, config, clan, backup, permissions)
  - moderation.py: Moderation tools (warn, mute, kick, ban, purge)
  - members.py: Member management (import/export, role-link, activity tracking)
  - utility.py: Utility commands (echo, ping, botinfo)
- **database/**: Database layer with schema and manager
- **utils/**: Helper functions for permissions and parsing
- **health_check.py**: HTTP server for health monitoring

### Database Schema
Comprehensive PostgreSQL schema with tables for:
- Guild configurations and settings
- Member data with clan ranks and activity
- Warnings, staff notes, and audit logs
- Role mappings and permissions
- Blacklist and mutes tracking
- Backup system for data recovery

### Key Features
1. **Echo Command**: Flexible message sending with plain/embed/code formats and reply support
2. **Permission System**: Role-based command restrictions with blacklist support
3. **Activity Tracking**: Automated inactivity detection and warnings
4. **Member Management**: CSV/Excel import/export for bulk operations
5. **Audit Logging**: Complete tracking of all bot actions
6. **Health Monitoring**: HTTP endpoints for bot status checks
7. **Auto Role Sync**: Automatic Discord role assignment based on clan ranks

## Configuration

### Required Secrets
- `DISCORD_BOT_TOKEN`: Discord bot token from Developer Portal

### Database
PostgreSQL database is automatically configured via Replit integration with the following tables:
- guild_configs, members, warnings, staff_notes, audit_logs
- role_mappings, permissions, blacklist, backups, mutes

### Environment Variables
- `HEALTH_CHECK_PORT`: 8080 (health check server)
- Database credentials (auto-configured by Replit)

## Development Guidelines

### Adding New Commands
1. Identify the appropriate cog (admin, moderation, members, utility)
2. Add the command with proper decorators and permissions
3. Update the database manager if new data operations are needed
4. Add audit logging for administrative actions
5. Test thoroughly before deploying

### Database Changes
1. Update `database/schema.sql` with new tables or columns
2. Add corresponding methods to `database/db_manager.py`
3. The schema is applied automatically on bot startup

### Code Conventions
- Use async/await for all Discord and database operations
- Follow the permission check pattern with `has_permissions()`
- Add audit logging for important actions
- Use embeds for rich formatted responses
- Handle errors gracefully with user-friendly messages

## User Preferences
- Clean, organized code with separation of concerns
- Comprehensive database persistence for all features
- Health check endpoint for monitoring
- Modular cog-based architecture for maintainability
- Proper error handling and user feedback
