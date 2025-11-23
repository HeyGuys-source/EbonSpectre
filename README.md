# Discord Clan Management Bot

A comprehensive Discord bot for clan management with administrative tools, moderation features, and member tracking.

## Features

### Administrative Commands
- `/setup` - Initialize the bot in the server
- `/config view` - View current bot configuration
- `/config set` - Modify bot settings
- `/clan set-tag` - Set the clan tag
- `/clan set-requirements` - Define clan joining requirements
- `/clan message` - Send clan-wide announcements
- `/backup` - Create a backup of bot data
- `/restore` - Restore from a backup
- `/permissions set` - Set command permissions
- `/blacklist add/remove` - Manage user blacklist

### Moderation Commands
- `/warn` - Warn a user
- `/warnings` - View user warnings
- `/remove-warning` - Remove a specific warning
- `/mute` - Mute a user with duration
- `/unmute` - Unmute a user
- `/kick` - Kick a user from the server
- `/ban` - Ban a user
- `/unban` - Unban a user
- `/purge` - Delete multiple messages
- `/note` - Add staff notes to users
- `/notes` - View staff notes

### Member Management
- `/role-link` - Link Discord roles to clan ranks
- `/sync-ranks` - Sync member ranks with Discord roles
- `/import-members` - Import members from CSV/Excel
- `/export-members` - Export member list to CSV
- `/activity-threshold` - Set inactivity threshold
- `/force-activity-scan` - Scan for inactive members

### Utility Commands
- `/echo` - Send messages as the bot with formatting options
  - Plain text, embed, or code block format
  - Optional reply to specific messages
- `/ping` - Check bot latency
- `/botinfo` - Display bot information

## Setup

### 1. Discord Bot Token
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to the "Bot" section and create a bot
4. Copy the bot token
5. Add it to the Replit Secrets as `DISCORD_BOT_TOKEN`

### 2. Bot Permissions
Invite the bot to your server with these permissions:
- Manage Roles
- Manage Channels
- Kick Members
- Ban Members
- Moderate Members
- Manage Messages
- Read Messages/View Channels
- Send Messages
- Embed Links
- Attach Files
- Read Message History

### 3. Database
The bot uses PostgreSQL for persistent storage. The database is automatically configured in Replit.

## Health Check
The bot includes a health check server running on port 8080:
- `/health` - Basic health status
- `/status` - Detailed bot status including guilds, latency, and users

## Architecture

### Project Structure
```
├── bot.py                 # Main bot file
├── health_check.py        # Health check server
├── database/
│   ├── db_manager.py      # Database operations
│   └── schema.sql         # Database schema
├── cogs/
│   ├── admin.py           # Administrative commands
│   ├── moderation.py      # Moderation commands
│   ├── members.py         # Member management
│   └── utility.py         # Utility commands
└── utils/
    └── helpers.py         # Helper functions
```

### Database Tables
- `guild_configs` - Server settings and configuration
- `members` - Clan member data
- `warnings` - User warnings
- `staff_notes` - Private moderator notes
- `audit_logs` - All bot actions
- `role_mappings` - Discord role to clan rank mappings
- `permissions` - Command permission restrictions
- `blacklist` - Blacklisted users
- `backups` - Backup data
- `mutes` - Active mute tracking

## Usage

### Running the Bot
The bot starts automatically when you run the Replit project.

### First Time Setup
1. Run `/setup` in your Discord server
2. Configure settings with `/config set`
3. Set up role mappings with `/role-link`
4. Import members with `/import-members` (optional)

## Features in Detail

### Echo Command
The `/echo` command allows staff to send messages as the bot:
- **Plain**: Regular text message
- **Embed**: Styled embed message
- **Code**: Code block formatted message
- **Reply**: Reply to a specific message by ID

### Activity Tracking
- Automatically tracks member activity
- Marks inactive members based on threshold
- Sends warnings for inactivity
- Supports custom threshold per server

### Permission System
- Restrict commands to specific roles
- Blacklist users from using the bot
- Administrator override for all commands
- Per-command permission settings

### Audit Logging
- Tracks all moderation actions
- Records configuration changes
- Logs member imports/exports
- Can be enabled/disabled per server

## Environment Variables
- `DISCORD_BOT_TOKEN` - Discord bot token (required)
- `DATABASE_URL` - PostgreSQL connection string (auto-configured)
- `HEALTH_CHECK_PORT` - Health check server port (default: 8080)
