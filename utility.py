import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, Literal
from utils.helpers import has_permissions


class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
    
    @app_commands.command(name="echo", description="Send a message as the bot with various formatting options")
    @app_commands.describe(
        message="The text content to send",
        reply="Message ID to reply to (optional)",
        format="How to format the message (plain, embed, or code)"
    )
    async def echo(
        self,
        interaction: discord.Interaction,
        message: str,
        reply: Optional[str] = None,
        format: Optional[Literal["plain", "embed", "code"]] = "plain"
    ):
        if not await has_permissions(self.db, interaction, "echo"):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        target_message = None
        if reply:
            try:
                message_id = int(reply)
                target_message = await interaction.channel.fetch_message(message_id)
            except (ValueError, discord.NotFound):
                await interaction.followup.send("Invalid message ID provided.", ephemeral=True)
                return
            except discord.Forbidden:
                await interaction.followup.send("I don't have permission to fetch that message.", ephemeral=True)
                return
        
        try:
            if format == "embed":
                embed = discord.Embed(
                    description=message,
                    color=discord.Color.blue(),
                    timestamp=discord.utils.utcnow()
                )
                embed.set_footer(text=f"Sent by {interaction.user.name}", icon_url=interaction.user.display_avatar.url)
                
                if target_message:
                    await target_message.reply(embed=embed)
                else:
                    await interaction.channel.send(embed=embed)
            
            elif format == "code":
                formatted_message = f"```\n{message}\n```"
                if target_message:
                    await target_message.reply(formatted_message)
                else:
                    await interaction.channel.send(formatted_message)
            
            else:
                if target_message:
                    await target_message.reply(message)
                else:
                    await interaction.channel.send(message)
            
            await interaction.followup.send("Message sent successfully!", ephemeral=True)
            
            config = await self.db.get_guild_config(interaction.guild.id)
            if config and config.get('audit_log_enabled'):
                await self.db.add_audit_log(
                    interaction.guild.id,
                    "echo_command",
                    interaction.user.id,
                    details=f"Format: {format}, Reply: {reply is not None}"
                )
        
        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to send messages in this channel.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)
    
    @app_commands.command(name="ping", description="Check the bot's latency")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(
            f"🏓 Pong! Latency: {latency}ms",
            ephemeral=True
        )
    
    @app_commands.command(name="botinfo", description="Display information about the bot")
    async def botinfo(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Bot Information",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        
        embed.add_field(name="Bot Name", value=self.bot.user.name, inline=True)
        embed.add_field(name="Servers", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="Latency", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text="Clan Management Bot")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="help", description="Display all available commands")
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📚 Command Help",
            description="Here are all available commands organized by category:",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        
        embed.add_field(
            name="🛠️ Utility Commands",
            value="`/echo` `/ping` `/botinfo` `/help`",
            inline=False
        )
        
        embed.add_field(
            name="⚙️ Administrative Commands",
            value="`/setup` `/reset-bot` `/config view` `/config set` `/clan set-tag` `/clan set-requirements` "
                  "`/clan message` `/backup` `/restore` `/listbackups` `/permissions set` `/blacklist add` "
                  "`/blacklist remove` `/audit-log` `/auto-roles`",
            inline=False
        )
        
        embed.add_field(
            name="🛡️ Moderation Commands",
            value="`/warn` `/warnings` `/remove-warning` `/mute` `/unmute` `/kick` `/ban` `/unban` "
                  "`/purge` `/note` `/notes` `/verify` `/report` `/clean-bots` `/raid-shield` "
                  "`/lock-channel` `/unlock-channel` `/slowmode` `/scan-profile`",
            inline=False
        )
        
        embed.add_field(
            name="👥 Member Management",
            value="`/role-link` `/sync-ranks` `/import-members` `/export-members` "
                  "`/activity-threshold` `/force-activity-scan`",
            inline=False
        )
        
        embed.set_footer(text="Use /command_name to execute a command")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Utility(bot))
