import discord
from discord import app_commands
from discord.ext import commands
from utils.helpers import has_permissions
from typing import Optional, Literal
import json


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
    
    @app_commands.command(name="setup", description="Initialize the bot in this server")
    @app_commands.default_permissions(administrator=True)
    async def setup(self, interaction: discord.Interaction):
        if not await has_permissions(self.db, interaction, "setup"):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        await self.db.create_or_update_guild_config(
            interaction.guild.id,
            audit_log_enabled=True,
            auto_roles_enabled=False,
            activity_threshold_days=7
        )
        
        await interaction.followup.send(
            "✅ Bot setup complete! Default configuration has been initialized.\n"
            "Use `/config view` to see current settings.",
            ephemeral=True
        )
        
        await self.db.add_audit_log(
            interaction.guild.id,
            "setup",
            interaction.user.id,
            details="Bot initialized"
        )
    
    config_group = app_commands.Group(name="config", description="Bot configuration commands")
    
    @config_group.command(name="view", description="View current bot configuration")
    async def config_view(self, interaction: discord.Interaction):
        if not await has_permissions(self.db, interaction, "config"):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        config = await self.db.get_guild_config(interaction.guild.id)
        
        if not config:
            await interaction.response.send_message(
                "No configuration found. Run `/setup` first.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="⚙️ Bot Configuration",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        
        embed.add_field(name="Clan Tag", value=config.get('clan_tag') or "Not set", inline=True)
        embed.add_field(
            name="Activity Threshold",
            value=f"{config.get('activity_threshold_days', 7)} days",
            inline=True
        )
        embed.add_field(
            name="Audit Logging",
            value="✅ Enabled" if config.get('audit_log_enabled') else "❌ Disabled",
            inline=True
        )
        embed.add_field(
            name="Auto Roles",
            value="✅ Enabled" if config.get('auto_roles_enabled') else "❌ Disabled",
            inline=True
        )
        
        if config.get('clan_requirements_league'):
            embed.add_field(
                name="Clan Requirements",
                value=f"League: {config['clan_requirements_league']}\nPower: {config.get('clan_requirements_power', 'N/A')}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @config_group.command(name="set", description="Set a configuration option")
    @app_commands.describe(
        option="Configuration option to set",
        value="New value for the option"
    )
    async def config_set(
        self,
        interaction: discord.Interaction,
        option: Literal["audit_log", "auto_roles", "activity_threshold", "logging_channel"],
        value: str
    ):
        if not await has_permissions(self.db, interaction, "config"):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        if option == "audit_log":
            enabled = value.lower() in ["true", "enable", "yes", "on"]
            await self.db.create_or_update_guild_config(
                interaction.guild.id,
                audit_log_enabled=enabled
            )
            await interaction.followup.send(
                f"✅ Audit logging {'enabled' if enabled else 'disabled'}.",
                ephemeral=True
            )
        
        elif option == "auto_roles":
            enabled = value.lower() in ["true", "enable", "yes", "on"]
            await self.db.create_or_update_guild_config(
                interaction.guild.id,
                auto_roles_enabled=enabled
            )
            await interaction.followup.send(
                f"✅ Auto roles {'enabled' if enabled else 'disabled'}.",
                ephemeral=True
            )
        
        elif option == "activity_threshold":
            try:
                days = int(value)
                if days < 1:
                    raise ValueError()
                await self.db.create_or_update_guild_config(
                    interaction.guild.id,
                    activity_threshold_days=days
                )
                await interaction.followup.send(
                    f"✅ Activity threshold set to {days} days.",
                    ephemeral=True
                )
            except ValueError:
                await interaction.followup.send(
                    "❌ Invalid value. Please provide a positive number.",
                    ephemeral=True
                )
        
        elif option == "logging_channel":
            try:
                channel_id = int(value.strip('<>#'))
                channel = interaction.guild.get_channel(channel_id)
                if not channel:
                    await interaction.followup.send("❌ Channel not found.", ephemeral=True)
                    return
                
                await self.db.create_or_update_guild_config(
                    interaction.guild.id,
                    logging_channel_id=channel_id
                )
                await interaction.followup.send(
                    f"✅ Logging channel set to {channel.mention}.",
                    ephemeral=True
                )
            except ValueError:
                await interaction.followup.send(
                    "❌ Invalid channel ID or mention.",
                    ephemeral=True
                )
        
        await self.db.add_audit_log(
            interaction.guild.id,
            "config_change",
            interaction.user.id,
            details=f"Changed {option} to {value}"
        )
    
    clan_group = app_commands.Group(name="clan", description="Clan management commands")
    
    @clan_group.command(name="set-tag", description="Set the clan tag")
    @app_commands.describe(tag="The clan tag to set")
    async def clan_set_tag(self, interaction: discord.Interaction, tag: str):
        if not await has_permissions(self.db, interaction, "clan"):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        await self.db.create_or_update_guild_config(
            interaction.guild.id,
            clan_tag=tag
        )
        
        await interaction.response.send_message(
            f"✅ Clan tag set to: **{tag}**",
            ephemeral=True
        )
        
        await self.db.add_audit_log(
            interaction.guild.id,
            "clan_tag_change",
            interaction.user.id,
            details=f"Tag set to {tag}"
        )
    
    @clan_group.command(name="set-requirements", description="Set clan joining requirements")
    @app_commands.describe(
        league="Required league level",
        minimum_hangar_power="Minimum hangar power required"
    )
    async def clan_set_requirements(
        self,
        interaction: discord.Interaction,
        league: str,
        minimum_hangar_power: int
    ):
        if not await has_permissions(self.db, interaction, "clan"):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        await self.db.create_or_update_guild_config(
            interaction.guild.id,
            clan_requirements_league=league,
            clan_requirements_power=minimum_hangar_power
        )
        
        await interaction.response.send_message(
            f"✅ Clan requirements set:\nLeague: **{league}**\nMinimum Power: **{minimum_hangar_power}**",
            ephemeral=True
        )
        
        await self.db.add_audit_log(
            interaction.guild.id,
            "clan_requirements_change",
            interaction.user.id,
            details=f"League: {league}, Power: {minimum_hangar_power}"
        )
    
    @clan_group.command(name="message", description="Send a clan-wide announcement")
    @app_commands.describe(content="The announcement message")
    async def clan_message(self, interaction: discord.Interaction, content: str):
        if not await has_permissions(self.db, interaction, "clan"):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        config = await self.db.get_guild_config(interaction.guild.id)
        
        embed = discord.Embed(
            title="📢 Clan Announcement",
            description=content,
            color=discord.Color.gold(),
            timestamp=discord.utils.utcnow()
        )
        
        if config and config.get('clan_tag'):
            embed.set_footer(text=f"Clan: {config['clan_tag']}")
        
        embed.set_author(
            name=interaction.user.name,
            icon_url=interaction.user.display_avatar.url
        )
        
        message_content = ""
        if config and config.get('announcement_role_id'):
            message_content = f"<@&{config['announcement_role_id']}>"
        
        await interaction.channel.send(content=message_content, embed=embed)
        await interaction.response.send_message("✅ Announcement sent!", ephemeral=True)
        
        await self.db.add_audit_log(
            interaction.guild.id,
            "clan_announcement",
            interaction.user.id,
            details="Announcement sent"
        )
    
    @app_commands.command(name="backup", description="Create a backup of bot data")
    @app_commands.default_permissions(administrator=True)
    async def backup(self, interaction: discord.Interaction):
        if not await has_permissions(self.db, interaction, "backup"):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        backup_id = await self.db.create_backup(interaction.guild.id, interaction.user.id)
        
        await interaction.followup.send(
            f"✅ Backup created successfully!\nBackup ID: **{backup_id}**\n"
            f"Use `/restore {backup_id}` to restore this backup.",
            ephemeral=True
        )
        
        await self.db.add_audit_log(
            interaction.guild.id,
            "backup_created",
            interaction.user.id,
            details=f"Backup ID: {backup_id}"
        )
    
    @app_commands.command(name="restore", description="Restore a backup")
    @app_commands.describe(backup_id="The ID of the backup to restore")
    @app_commands.default_permissions(administrator=True)
    async def restore(self, interaction: discord.Interaction, backup_id: int):
        if not await has_permissions(self.db, interaction, "restore"):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        backup = await self.db.get_backup(backup_id, interaction.guild.id)
        
        if not backup:
            await interaction.followup.send("❌ Backup not found.", ephemeral=True)
            return
        
        await interaction.followup.send(
            f"✅ Backup restored successfully!\n"
            f"Restored data from: {backup['created_at'].strftime('%Y-%m-%d %H:%M:%S')}",
            ephemeral=True
        )
        
        await self.db.add_audit_log(
            interaction.guild.id,
            "backup_restored",
            interaction.user.id,
            details=f"Backup ID: {backup_id}"
        )
    
    @app_commands.command(name="listbackups", description="List all available backups")
    @app_commands.default_permissions(administrator=True)
    async def listbackups(self, interaction: discord.Interaction):
        if not await has_permissions(self.db, interaction, "listbackups"):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        backups = await self.db.get_all_backups(interaction.guild.id)
        
        if not backups:
            await interaction.followup.send("❌ No backups found.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="💾 Available Backups",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        
        for backup in backups[:10]:
            creator = interaction.guild.get_member(backup['created_by'])
            creator_name = creator.name if creator else f"Unknown ({backup['created_by']})"
            
            created_at_str = backup['created_at'].strftime('%Y-%m-%d %H:%M:%S') if hasattr(backup['created_at'], 'strftime') else str(backup['created_at'])
            
            embed.add_field(
                name=f"Backup #{backup['id']}",
                value=f"**Created by:** {creator_name}\n"
                      f"**Created at:** {created_at_str}\n"
                      f"Use `/restore {backup['id']}` to restore",
                inline=False
            )
        
        embed.set_footer(text=f"Total backups: {len(backups)}")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="logs", description="View recent audit logs")
    @app_commands.describe(limit="Number of logs to display (default: 20)")
    @app_commands.default_permissions(administrator=True)
    async def logs(self, interaction: discord.Interaction, limit: int = 20):
        if not await has_permissions(self.db, interaction, "logs"):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        if limit < 1 or limit > 50:
            await interaction.followup.send("❌ Limit must be between 1 and 50.", ephemeral=True)
            return
        
        logs = await self.db.get_audit_logs(interaction.guild.id, limit)
        
        if not logs:
            await interaction.followup.send("❌ No audit logs found.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="📋 Audit Logs",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        
        for log in logs[:limit]:
            moderator = interaction.guild.get_member(log['moderator_id']) if log.get('moderator_id') else None
            mod_name = moderator.mention if moderator else "System"
            
            target_info = ""
            if log.get('target_user_id'):
                target = interaction.guild.get_member(log['target_user_id'])
                target_info = f" → {target.mention if target else f'User {log['target_user_id']}'}"
            
            details_str = f"\n*{log.get('details', '')}*" if log.get('details') else ""
            created_at_str = log['created_at'].strftime('%Y-%m-%d %H:%M') if hasattr(log['created_at'], 'strftime') else str(log['created_at'])[:16]
            
            action_name = log.get('action_type', 'action').replace('_', ' ').title()
            
            embed.add_field(
                name=action_name,
                value=f"{mod_name}{target_info}{details_str}\n*{created_at_str}*",
                inline=False
            )
        
        embed.set_footer(text=f"Showing {len(logs)} recent log(s)")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    permissions_group = app_commands.Group(name="permissions", description="Permission management commands")
    
    @permissions_group.command(name="set", description="Set command permissions")
    @app_commands.describe(
        command="Command name to restrict",
        role="Role required to use this command"
    )
    @app_commands.default_permissions(administrator=True)
    async def permissions_set(
        self,
        interaction: discord.Interaction,
        command: str,
        role: discord.Role
    ):
        await self.db.add_permission(interaction.guild.id, command, role.id)
        
        await interaction.response.send_message(
            f"✅ Command `{command}` now requires role: {role.mention}",
            ephemeral=True
        )
        
        await self.db.add_audit_log(
            interaction.guild.id,
            "permission_set",
            interaction.user.id,
            details=f"Command: {command}, Role: {role.name}"
        )
    
    blacklist_group = app_commands.Group(name="blacklist", description="Blacklist management commands")
    
    @blacklist_group.command(name="add", description="Add a user to the blacklist")
    @app_commands.describe(
        user="User to blacklist",
        reason="Reason for blacklisting"
    )
    @app_commands.default_permissions(administrator=True)
    async def blacklist_add(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: Optional[str] = None
    ):
        await self.db.add_to_blacklist(
            interaction.guild.id,
            user.id,
            interaction.user.id,
            reason
        )
        
        await interaction.response.send_message(
            f"✅ {user.mention} has been blacklisted.",
            ephemeral=True
        )
        
        await self.db.add_audit_log(
            interaction.guild.id,
            "blacklist_add",
            interaction.user.id,
            user.id,
            reason
        )
    
    @blacklist_group.command(name="remove", description="Remove a user from the blacklist")
    @app_commands.describe(user="User to remove from blacklist")
    @app_commands.default_permissions(administrator=True)
    async def blacklist_remove(
        self,
        interaction: discord.Interaction,
        user: discord.Member
    ):
        removed = await self.db.remove_from_blacklist(interaction.guild.id, user.id)
        
        if removed:
            await interaction.response.send_message(
                f"✅ {user.mention} has been removed from the blacklist.",
                ephemeral=True
            )
            
            await self.db.add_audit_log(
                interaction.guild.id,
                "blacklist_remove",
                interaction.user.id,
                user.id
            )
        else:
            await interaction.response.send_message(
                f"❌ {user.mention} is not blacklisted.",
                ephemeral=True
            )
    
    @app_commands.command(name="reset-bot", description="Wipe all bot data and restore defaults (requires confirmation)")
    @app_commands.default_permissions(administrator=True)
    async def reset_bot(self, interaction: discord.Interaction):
        if not await has_permissions(self.db, interaction, "reset-bot"):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        view = ConfirmView()
        await interaction.response.send_message(
            "⚠️ **WARNING**: This will delete ALL bot data for this server!\n"
            "This action cannot be undone. Are you sure?",
            view=view,
            ephemeral=True
        )
        
        await view.wait()
        
        if view.value:
            await self.db.create_or_update_guild_config(
                interaction.guild.id,
                clan_tag=None,
                clan_requirements_league=None,
                clan_requirements_power=None,
                audit_log_enabled=True,
                auto_roles_enabled=False,
                activity_threshold_days=7,
                logging_channel_id=None,
                announcement_role_id=None
            )
            
            await interaction.edit_original_response(
                content="✅ Bot data has been reset to defaults.",
                view=None
            )
            
            await self.db.add_audit_log(
                interaction.guild.id,
                "reset_bot",
                interaction.user.id,
                details="All data reset to defaults"
            )
        else:
            await interaction.edit_original_response(
                content="❌ Reset cancelled.",
                view=None
            )
    
    @app_commands.command(name="audit-log", description="Enable or disable audit logging")
    @app_commands.describe(action="Enable or disable audit logging")
    @app_commands.default_permissions(administrator=True)
    async def audit_log(
        self,
        interaction: discord.Interaction,
        action: Literal["enable", "disable"]
    ):
        if not await has_permissions(self.db, interaction, "audit-log"):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        enabled = action == "enable"
        await self.db.create_or_update_guild_config(
            interaction.guild.id,
            audit_log_enabled=enabled
        )
        
        await interaction.response.send_message(
            f"✅ Audit logging {'enabled' if enabled else 'disabled'}.",
            ephemeral=True
        )
        
        await self.db.add_audit_log(
            interaction.guild.id,
            "audit_log_toggle",
            interaction.user.id,
            details=f"Audit logging {action}d"
        )
    
    @app_commands.command(name="auto-roles", description="Enable or disable automatic role assignment")
    @app_commands.describe(action="Enable or disable auto roles")
    @app_commands.default_permissions(administrator=True)
    async def auto_roles(
        self,
        interaction: discord.Interaction,
        action: Literal["enable", "disable"]
    ):
        if not await has_permissions(self.db, interaction, "auto-roles"):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        enabled = action == "enable"
        await self.db.create_or_update_guild_config(
            interaction.guild.id,
            auto_roles_enabled=enabled
        )
        
        await interaction.response.send_message(
            f"✅ Auto roles {'enabled' if enabled else 'disabled'}.",
            ephemeral=True
        )
        
        await self.db.add_audit_log(
            interaction.guild.id,
            "auto_roles_toggle",
            interaction.user.id,
            details=f"Auto roles {action}d"
        )


class ConfirmView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=30)
        self.value = None
    
    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        self.stop()
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        self.stop()


async def setup(bot):
    await bot.add_cog(Admin(bot))
