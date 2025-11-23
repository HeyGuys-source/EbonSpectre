import discord
from discord import app_commands
from discord.ext import commands
from utils.helpers import has_permissions, parse_duration, format_duration
from typing import Optional, Literal
from datetime import datetime, timedelta


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
    
    @app_commands.command(name="warn", description="Warn a user")
    @app_commands.describe(
        user="User to warn",
        reason="Reason for the warning"
    )
    @app_commands.default_permissions(moderate_members=True)
    async def warn(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str
    ):
        if not await has_permissions(self.db, interaction, "warn"):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        warning_id = await self.db.add_warning(
            interaction.guild.id,
            user.id,
            interaction.user.id,
            reason
        )
        
        try:
            await user.send(
                f"⚠️ You have been warned in **{interaction.guild.name}**\n"
                f"**Reason:** {reason}\n"
                f"**Warning ID:** {warning_id}"
            )
        except discord.Forbidden:
            pass
        
        await interaction.response.send_message(
            f"✅ {user.mention} has been warned.\n**Warning ID:** {warning_id}",
            ephemeral=True
        )
        
        config = await self.db.get_guild_config(interaction.guild.id)
        if config and config.get('audit_log_enabled'):
            await self.db.add_audit_log(
                interaction.guild.id,
                "warn",
                interaction.user.id,
                user.id,
                f"Reason: {reason}"
            )
    
    @app_commands.command(name="warnings", description="View warnings for a user")
    @app_commands.describe(user="User to check warnings for")
    async def warnings(
        self,
        interaction: discord.Interaction,
        user: discord.Member
    ):
        if not await has_permissions(self.db, interaction, "warnings"):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        warnings = await self.db.get_warnings(interaction.guild.id, user.id)
        
        if not warnings:
            await interaction.response.send_message(
                f"{user.mention} has no warnings.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title=f"⚠️ Warnings for {user.name}",
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )
        
        for warning in warnings[:10]:
            moderator = interaction.guild.get_member(warning['moderator_id'])
            mod_name = moderator.name if moderator else f"Unknown ({warning['moderator_id']})"
            
            embed.add_field(
                name=f"Warning #{warning['id']}",
                value=f"**Moderator:** {mod_name}\n"
                      f"**Reason:** {warning['reason']}\n"
                      f"**Date:** {warning['created_at'].strftime('%Y-%m-%d %H:%M')}",
                inline=False
            )
        
        embed.set_footer(text=f"Total warnings: {len(warnings)}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="remove-warning", description="Remove a specific warning")
    @app_commands.describe(
        user="User whose warning to remove",
        warning_id="ID of the warning to remove"
    )
    @app_commands.default_permissions(moderate_members=True)
    async def remove_warning(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        warning_id: int
    ):
        if not await has_permissions(self.db, interaction, "remove-warning"):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        removed = await self.db.remove_warning(warning_id, interaction.guild.id)
        
        if removed:
            await interaction.response.send_message(
                f"✅ Warning #{warning_id} has been removed from {user.mention}.",
                ephemeral=True
            )
            
            config = await self.db.get_guild_config(interaction.guild.id)
            if config and config.get('audit_log_enabled'):
                await self.db.add_audit_log(
                    interaction.guild.id,
                    "warning_removed",
                    interaction.user.id,
                    user.id,
                    f"Warning ID: {warning_id}"
                )
        else:
            await interaction.response.send_message(
                f"❌ Warning #{warning_id} not found.",
                ephemeral=True
            )
    
    @app_commands.command(name="mute", description="Mute a user for a specified duration")
    @app_commands.describe(
        user="User to mute",
        duration="Duration (e.g., 1h, 30m, 1d)",
        reason="Reason for muting"
    )
    @app_commands.default_permissions(moderate_members=True)
    async def mute(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        duration: str,
        reason: Optional[str] = None
    ):
        if not await has_permissions(self.db, interaction, "mute"):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        duration_td = parse_duration(duration)
        if not duration_td:
            await interaction.response.send_message(
                "❌ Invalid duration format. Use formats like: 1h, 30m, 1d, etc.",
                ephemeral=True
            )
            return
        
        if duration_td > timedelta(days=28):
            await interaction.response.send_message(
                "❌ Mute duration cannot exceed 28 days.",
                ephemeral=True
            )
            return
        
        expires_at = datetime.utcnow() + duration_td
        
        try:
            await user.timeout(expires_at, reason=reason)
            
            await self.db.add_mute(
                interaction.guild.id,
                user.id,
                interaction.user.id,
                expires_at,
                reason
            )
            
            await interaction.response.send_message(
                f"✅ {user.mention} has been muted for {format_duration(duration_td)}.",
                ephemeral=True
            )
            
            config = await self.db.get_guild_config(interaction.guild.id)
            if config and config.get('audit_log_enabled'):
                await self.db.add_audit_log(
                    interaction.guild.id,
                    "mute",
                    interaction.user.id,
                    user.id,
                    f"Duration: {format_duration(duration_td)}, Reason: {reason}"
                )
        
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to timeout this user.",
                ephemeral=True
            )
    
    @app_commands.command(name="unmute", description="Unmute a user")
    @app_commands.describe(user="User to unmute")
    @app_commands.default_permissions(moderate_members=True)
    async def unmute(
        self,
        interaction: discord.Interaction,
        user: discord.Member
    ):
        if not await has_permissions(self.db, interaction, "unmute"):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        try:
            await user.timeout(None)
            
            await self.db.remove_mute(interaction.guild.id, user.id)
            
            await interaction.response.send_message(
                f"✅ {user.mention} has been unmuted.",
                ephemeral=True
            )
            
            config = await self.db.get_guild_config(interaction.guild.id)
            if config and config.get('audit_log_enabled'):
                await self.db.add_audit_log(
                    interaction.guild.id,
                    "unmute",
                    interaction.user.id,
                    user.id
                )
        
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to remove timeout from this user.",
                ephemeral=True
            )
    
    @app_commands.command(name="kick", description="Kick a user from the server")
    @app_commands.describe(
        user="User to kick",
        reason="Reason for kicking"
    )
    @app_commands.default_permissions(kick_members=True)
    async def kick(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: Optional[str] = None
    ):
        if not await has_permissions(self.db, interaction, "kick"):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        try:
            await user.kick(reason=reason)
            
            await interaction.response.send_message(
                f"✅ {user.mention} has been kicked.\n**Reason:** {reason or 'No reason provided'}",
                ephemeral=True
            )
            
            config = await self.db.get_guild_config(interaction.guild.id)
            if config and config.get('audit_log_enabled'):
                await self.db.add_audit_log(
                    interaction.guild.id,
                    "kick",
                    interaction.user.id,
                    user.id,
                    f"Reason: {reason}"
                )
        
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to kick this user.",
                ephemeral=True
            )
    
    @app_commands.command(name="ban", description="Ban a user from the server")
    @app_commands.describe(
        user="User to ban",
        reason="Reason for banning"
    )
    @app_commands.default_permissions(ban_members=True)
    async def ban(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: Optional[str] = None
    ):
        if not await has_permissions(self.db, interaction, "ban"):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        try:
            await user.ban(reason=reason)
            
            await interaction.response.send_message(
                f"✅ {user.mention} has been banned.\n**Reason:** {reason or 'No reason provided'}",
                ephemeral=True
            )
            
            config = await self.db.get_guild_config(interaction.guild.id)
            if config and config.get('audit_log_enabled'):
                await self.db.add_audit_log(
                    interaction.guild.id,
                    "ban",
                    interaction.user.id,
                    user.id,
                    f"Reason: {reason}"
                )
        
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to ban this user.",
                ephemeral=True
            )
    
    @app_commands.command(name="unban", description="Unban a user from the server")
    @app_commands.describe(user_id="ID of the user to unban")
    @app_commands.default_permissions(ban_members=True)
    async def unban(
        self,
        interaction: discord.Interaction,
        user_id: str
    ):
        if not await has_permissions(self.db, interaction, "unban"):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        try:
            user_id_int = int(user_id)
            user = await self.bot.fetch_user(user_id_int)
            await interaction.guild.unban(user)
            
            await interaction.response.send_message(
                f"✅ {user.name} has been unbanned.",
                ephemeral=True
            )
            
            config = await self.db.get_guild_config(interaction.guild.id)
            if config and config.get('audit_log_enabled'):
                await self.db.add_audit_log(
                    interaction.guild.id,
                    "unban",
                    interaction.user.id,
                    user_id_int
                )
        
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid user ID.",
                ephemeral=True
            )
        except discord.NotFound:
            await interaction.response.send_message(
                "❌ User not found or not banned.",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to unban users.",
                ephemeral=True
            )
    
    @app_commands.command(name="purge", description="Delete multiple messages")
    @app_commands.describe(amount="Number of messages to delete (1-100)")
    @app_commands.default_permissions(manage_messages=True)
    async def purge(
        self,
        interaction: discord.Interaction,
        amount: int
    ):
        if not await has_permissions(self.db, interaction, "purge"):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        if amount < 1 or amount > 100:
            await interaction.response.send_message(
                "❌ Amount must be between 1 and 100.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            deleted = await interaction.channel.purge(limit=amount)
            
            await interaction.followup.send(
                f"✅ Deleted {len(deleted)} message(s).",
                ephemeral=True
            )
            
            config = await self.db.get_guild_config(interaction.guild.id)
            if config and config.get('audit_log_enabled'):
                await self.db.add_audit_log(
                    interaction.guild.id,
                    "purge",
                    interaction.user.id,
                    details=f"Deleted {len(deleted)} messages"
                )
        
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ I don't have permission to delete messages.",
                ephemeral=True
            )
    
    @app_commands.command(name="note", description="Add a staff note to a user")
    @app_commands.describe(
        user="User to add note to",
        note="The private note"
    )
    @app_commands.default_permissions(moderate_members=True)
    async def note(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        note: str
    ):
        if not await has_permissions(self.db, interaction, "note"):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        await self.db.add_staff_note(
            interaction.guild.id,
            user.id,
            interaction.user.id,
            note
        )
        
        await interaction.response.send_message(
            f"✅ Note added for {user.mention}.",
            ephemeral=True
        )
    
    @app_commands.command(name="notes", description="View staff notes for a user")
    @app_commands.describe(user="User to check notes for")
    async def notes(
        self,
        interaction: discord.Interaction,
        user: discord.Member
    ):
        if not await has_permissions(self.db, interaction, "notes"):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        notes = await self.db.get_staff_notes(interaction.guild.id, user.id)
        
        if not notes:
            await interaction.response.send_message(
                f"{user.mention} has no staff notes.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title=f"📝 Staff Notes for {user.name}",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        
        for note in notes[:10]:
            staff = interaction.guild.get_member(note['staff_id'])
            staff_name = staff.name if staff else f"Unknown ({note['staff_id']})"
            
            embed.add_field(
                name=f"Note #{note['id']} - {staff_name}",
                value=f"{note['note']}\n*{note['created_at'].strftime('%Y-%m-%d %H:%M')}*",
                inline=False
            )
        
        embed.set_footer(text=f"Total notes: {len(notes)}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="verify", description="Verify a user and assign starter roles")
    @app_commands.describe(user="User to verify")
    @app_commands.default_permissions(moderate_members=True)
    async def verify(
        self,
        interaction: discord.Interaction,
        user: discord.Member
    ):
        if not await has_permissions(self.db, interaction, "verify"):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        await interaction.response.send_message(
            f"✅ {user.mention} has been verified!",
            ephemeral=True
        )
        
        config = await self.db.get_guild_config(interaction.guild.id)
        if config and config.get('audit_log_enabled'):
            await self.db.add_audit_log(
                interaction.guild.id,
                "verify",
                interaction.user.id,
                user.id,
                "User verified"
            )
    
    @app_commands.command(name="report", description="Report a message to staff for review")
    @app_commands.describe(message_link="Link to the message to report")
    async def report(
        self,
        interaction: discord.Interaction,
        message_link: str
    ):
        await interaction.response.defer(ephemeral=True)
        
        config = await self.db.get_guild_config(interaction.guild.id)
        if not config or not config.get('logging_channel_id'):
            await interaction.followup.send(
                "❌ No logging channel configured. Ask an admin to set one with `/config set logging_channel`.",
                ephemeral=True
            )
            return
        
        logging_channel = interaction.guild.get_channel(config['logging_channel_id'])
        if not logging_channel:
            await interaction.followup.send(
                "❌ Logging channel not found.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="📋 Message Reported",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Reported By", value=interaction.user.mention, inline=True)
        embed.add_field(name="Message Link", value=message_link, inline=False)
        
        await logging_channel.send(embed=embed)
        await interaction.followup.send(
            "✅ Message has been reported to staff.",
            ephemeral=True
        )
    
    @app_commands.command(name="clean-bots", description="Delete bot spam messages from the channel")
    @app_commands.describe(amount="Number of messages to check (default: 50)")
    @app_commands.default_permissions(manage_messages=True)
    async def clean_bots(
        self,
        interaction: discord.Interaction,
        amount: int = 50
    ):
        if not await has_permissions(self.db, interaction, "clean-bots"):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        def is_bot(message):
            return message.author.bot
        
        try:
            deleted = await interaction.channel.purge(limit=amount, check=is_bot)
            
            await interaction.followup.send(
                f"✅ Deleted {len(deleted)} bot message(s).",
                ephemeral=True
            )
            
            config = await self.db.get_guild_config(interaction.guild.id)
            if config and config.get('audit_log_enabled'):
                await self.db.add_audit_log(
                    interaction.guild.id,
                    "clean_bots",
                    interaction.user.id,
                    details=f"Deleted {len(deleted)} bot messages"
                )
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ I don't have permission to delete messages.",
                ephemeral=True
            )
    
    @app_commands.command(name="raid-shield", description="Enable or disable raid protection mode")
    @app_commands.describe(action="Enable or disable raid shield")
    @app_commands.default_permissions(administrator=True)
    async def raid_shield(
        self,
        interaction: discord.Interaction,
        action: Literal["enable", "disable"]
    ):
        if not await has_permissions(self.db, interaction, "raid-shield"):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        enabled = action == "enable"
        
        await interaction.response.send_message(
            f"🛡️ Raid shield {'enabled' if enabled else 'disabled'}.\n"
            f"{'Server is now in lockdown mode.' if enabled else 'Server is back to normal.'}",
            ephemeral=True
        )
        
        config = await self.db.get_guild_config(interaction.guild.id)
        if config and config.get('audit_log_enabled'):
            await self.db.add_audit_log(
                interaction.guild.id,
                "raid_shield",
                interaction.user.id,
                details=f"Raid shield {action}d"
            )
    
    @app_commands.command(name="lock-channel", description="Lock the current channel")
    @app_commands.default_permissions(manage_channels=True)
    async def lock_channel(self, interaction: discord.Interaction):
        if not await has_permissions(self.db, interaction, "lock-channel"):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        try:
            await interaction.channel.set_permissions(
                interaction.guild.default_role,
                send_messages=False
            )
            
            await interaction.response.send_message(
                "🔒 Channel locked. Only moderators can send messages.",
                ephemeral=True
            )
            
            config = await self.db.get_guild_config(interaction.guild.id)
            if config and config.get('audit_log_enabled'):
                await self.db.add_audit_log(
                    interaction.guild.id,
                    "lock_channel",
                    interaction.user.id,
                    details=f"Locked {interaction.channel.name}"
                )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to manage channel permissions.",
                ephemeral=True
            )
    
    @app_commands.command(name="unlock-channel", description="Unlock the current channel")
    @app_commands.default_permissions(manage_channels=True)
    async def unlock_channel(self, interaction: discord.Interaction):
        if not await has_permissions(self.db, interaction, "unlock-channel"):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        try:
            await interaction.channel.set_permissions(
                interaction.guild.default_role,
                send_messages=None
            )
            
            await interaction.response.send_message(
                "🔓 Channel unlocked. Everyone can send messages again.",
                ephemeral=True
            )
            
            config = await self.db.get_guild_config(interaction.guild.id)
            if config and config.get('audit_log_enabled'):
                await self.db.add_audit_log(
                    interaction.guild.id,
                    "unlock_channel",
                    interaction.user.id,
                    details=f"Unlocked {interaction.channel.name}"
                )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to manage channel permissions.",
                ephemeral=True
            )
    
    @app_commands.command(name="slowmode", description="Set slowmode delay for the channel")
    @app_commands.describe(seconds="Slowmode delay in seconds (0 to disable)")
    @app_commands.default_permissions(manage_channels=True)
    async def slowmode(
        self,
        interaction: discord.Interaction,
        seconds: int
    ):
        if not await has_permissions(self.db, interaction, "slowmode"):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        if seconds < 0 or seconds > 21600:
            await interaction.response.send_message(
                "❌ Slowmode delay must be between 0 and 21600 seconds (6 hours).",
                ephemeral=True
            )
            return
        
        try:
            await interaction.channel.edit(slowmode_delay=seconds)
            
            if seconds == 0:
                await interaction.response.send_message(
                    "✅ Slowmode disabled.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"✅ Slowmode set to {seconds} second(s).",
                    ephemeral=True
                )
            
            config = await self.db.get_guild_config(interaction.guild.id)
            if config and config.get('audit_log_enabled'):
                await self.db.add_audit_log(
                    interaction.guild.id,
                    "slowmode",
                    interaction.user.id,
                    details=f"Set slowmode to {seconds}s in {interaction.channel.name}"
                )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to edit this channel.",
                ephemeral=True
            )
    
    @app_commands.command(name="scan-profile", description="Scan a user's profile for inappropriate content")
    @app_commands.describe(user="User to scan")
    @app_commands.default_permissions(moderate_members=True)
    async def scan_profile(
        self,
        interaction: discord.Interaction,
        user: discord.Member
    ):
        if not await has_permissions(self.db, interaction, "scan-profile"):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        embed = discord.Embed(
            title=f"🔍 Profile Scan: {user.name}",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Username", value=user.name, inline=True)
        embed.add_field(name="Display Name", value=user.display_name, inline=True)
        embed.add_field(name="User ID", value=user.id, inline=True)
        embed.add_field(name="Account Created", value=user.created_at.strftime('%Y-%m-%d'), inline=True)
        embed.add_field(name="Joined Server", value=user.joined_at.strftime('%Y-%m-%d') if user.joined_at else "Unknown", inline=True)
        
        flags = []
        if user.bot:
            flags.append("🤖 Bot Account")
        if user.premium_since:
            flags.append("💎 Server Booster")
        if user.timed_out_until:
            flags.append("⏰ Currently Muted")
        
        embed.add_field(
            name="Status",
            value="\n".join(flags) if flags else "No special flags",
            inline=False
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Moderation(bot))
