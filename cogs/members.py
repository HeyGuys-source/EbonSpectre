import discord
from discord import app_commands
from discord.ext import commands
from utils.helpers import has_permissions
from typing import Optional
import pandas as pd
import io


class Members(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
    
    @app_commands.command(name="role-link", description="Link a Discord role to a clan rank")
    @app_commands.describe(
        discord_role="The Discord role to link",
        clan_rank="The clan rank (R1-R5)"
    )
    @app_commands.default_permissions(administrator=True)
    async def role_link(
        self,
        interaction: discord.Interaction,
        discord_role: discord.Role,
        clan_rank: str
    ):
        if not await has_permissions(self.db, interaction, "role-link"):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        await self.db.add_role_mapping(
            interaction.guild.id,
            discord_role.id,
            clan_rank
        )
        
        await interaction.response.send_message(
            f"✅ Linked {discord_role.mention} to clan rank **{clan_rank}**.",
            ephemeral=True
        )
        
        config = await self.db.get_guild_config(interaction.guild.id)
        if config and config.get('audit_log_enabled'):
            await self.db.add_audit_log(
                interaction.guild.id,
                "role_link",
                interaction.user.id,
                details=f"Role: {discord_role.name}, Rank: {clan_rank}"
            )
    
    @app_commands.command(name="sync-ranks", description="Sync all member ranks with their Discord roles")
    @app_commands.default_permissions(administrator=True)
    async def sync_ranks(self, interaction: discord.Interaction):
        if not await has_permissions(self.db, interaction, "sync-ranks"):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        role_mappings = await self.db.get_role_mappings(interaction.guild.id)
        members = await self.db.get_all_members(interaction.guild.id)
        
        synced = 0
        for member_data in members:
            member = interaction.guild.get_member(member_data['user_id'])
            if not member:
                continue
            
            clan_rank = member_data.get('clan_rank')
            if not clan_rank:
                continue
            
            for mapping in role_mappings:
                if mapping['clan_rank'] == clan_rank:
                    role = interaction.guild.get_role(mapping['discord_role_id'])
                    if role and role not in member.roles:
                        try:
                            await member.add_roles(role)
                            synced += 1
                        except discord.Forbidden:
                            pass
        
        await interaction.followup.send(
            f"✅ Rank sync complete! Updated {synced} member(s).",
            ephemeral=True
        )
        
        config = await self.db.get_guild_config(interaction.guild.id)
        if config and config.get('audit_log_enabled'):
            await self.db.add_audit_log(
                interaction.guild.id,
                "sync_ranks",
                interaction.user.id,
                details=f"Synced {synced} members"
            )
    
    @app_commands.command(name="import-members", description="Import members from a CSV/Excel file")
    @app_commands.describe(file="CSV or Excel file containing member data")
    @app_commands.default_permissions(administrator=True)
    async def import_members(
        self,
        interaction: discord.Interaction,
        file: discord.Attachment
    ):
        if not await has_permissions(self.db, interaction, "import-members"):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        if not file.filename.endswith(('.csv', '.xlsx', '.xls')):
            await interaction.followup.send(
                "❌ Invalid file format. Please upload a CSV or Excel file.",
                ephemeral=True
            )
            return
        
        try:
            file_bytes = await file.read()
            
            if file.filename.endswith('.csv'):
                df = pd.read_csv(io.BytesIO(file_bytes))
            else:
                df = pd.read_excel(io.BytesIO(file_bytes))
            
            required_columns = ['user_id', 'username']
            if not all(col in df.columns for col in required_columns):
                await interaction.followup.send(
                    f"❌ Missing required columns. File must contain: {', '.join(required_columns)}",
                    ephemeral=True
                )
                return
            
            imported = 0
            for _, row in df.iterrows():
                kwargs = {}
                if 'clan_rank' in df.columns:
                    kwargs['clan_rank'] = row['clan_rank']
                if 'hangar_power' in df.columns:
                    kwargs['hangar_power'] = int(row['hangar_power']) if pd.notna(row['hangar_power']) else None
                if 'league' in df.columns:
                    kwargs['league'] = row['league']
                
                await self.db.add_member(
                    interaction.guild.id,
                    int(row['user_id']),
                    str(row['username']),
                    **kwargs
                )
                imported += 1
            
            await interaction.followup.send(
                f"✅ Successfully imported {imported} member(s)!",
                ephemeral=True
            )
            
            config = await self.db.get_guild_config(interaction.guild.id)
            if config and config.get('audit_log_enabled'):
                await self.db.add_audit_log(
                    interaction.guild.id,
                    "import_members",
                    interaction.user.id,
                    details=f"Imported {imported} members"
                )
        
        except Exception as e:
            await interaction.followup.send(
                f"❌ Error importing file: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="export-members", description="Export member list to CSV")
    @app_commands.default_permissions(administrator=True)
    async def export_members(self, interaction: discord.Interaction):
        if not await has_permissions(self.db, interaction, "export-members"):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        members = await self.db.get_all_members(interaction.guild.id)
        
        if not members:
            await interaction.followup.send(
                "❌ No members found in the database.",
                ephemeral=True
            )
            return
        
        df = pd.DataFrame(members)
        
        columns_to_export = ['user_id', 'username', 'clan_rank', 'hangar_power', 'league', 'last_active', 'is_inactive', 'joined_at']
        existing_columns = [col for col in columns_to_export if col in df.columns]
        df = df[existing_columns]
        
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        
        file = discord.File(
            io.BytesIO(csv_buffer.getvalue().encode()),
            filename=f"members_{interaction.guild.name}_{discord.utils.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        await interaction.followup.send(
            f"✅ Exported {len(members)} member(s).",
            file=file,
            ephemeral=True
        )
        
        config = await self.db.get_guild_config(interaction.guild.id)
        if config and config.get('audit_log_enabled'):
            await self.db.add_audit_log(
                interaction.guild.id,
                "export_members",
                interaction.user.id,
                details=f"Exported {len(members)} members"
            )
    
    @app_commands.command(name="activity-threshold", description="Set inactivity threshold in days")
    @app_commands.describe(days="Number of days before marking as inactive")
    @app_commands.default_permissions(administrator=True)
    async def activity_threshold(
        self,
        interaction: discord.Interaction,
        days: int
    ):
        if not await has_permissions(self.db, interaction, "activity-threshold"):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        if days < 1:
            await interaction.response.send_message(
                "❌ Threshold must be at least 1 day.",
                ephemeral=True
            )
            return
        
        await self.db.create_or_update_guild_config(
            interaction.guild.id,
            activity_threshold_days=days
        )
        
        await interaction.response.send_message(
            f"✅ Activity threshold set to **{days} day(s)**.",
            ephemeral=True
        )
        
        config = await self.db.get_guild_config(interaction.guild.id)
        if config and config.get('audit_log_enabled'):
            await self.db.add_audit_log(
                interaction.guild.id,
                "activity_threshold_change",
                interaction.user.id,
                details=f"Threshold: {days} days"
            )
    
    @app_commands.command(name="force-activity-scan", description="Scan for inactive members")
    @app_commands.default_permissions(administrator=True)
    async def force_activity_scan(self, interaction: discord.Interaction):
        if not await has_permissions(self.db, interaction, "force-activity-scan"):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        config = await self.db.get_guild_config(interaction.guild.id)
        threshold_days = config.get('activity_threshold_days', 7) if config else 7
        
        inactive_user_ids = await self.db.mark_inactive_members(
            interaction.guild.id,
            threshold_days
        )
        
        if inactive_user_ids:
            embed = discord.Embed(
                title="⚠️ Inactive Members Detected",
                description=f"Found {len(inactive_user_ids)} inactive member(s) (>{threshold_days} days)",
                color=discord.Color.orange(),
                timestamp=discord.utils.utcnow()
            )
            
            member_mentions = []
            for user_id in inactive_user_ids[:25]:
                member = interaction.guild.get_member(user_id)
                if member:
                    member_mentions.append(member.mention)
            
            if member_mentions:
                embed.add_field(
                    name="Inactive Members",
                    value='\n'.join(member_mentions),
                    inline=False
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(
                "✅ No inactive members found.",
                ephemeral=True
            )
        
        if config and config.get('audit_log_enabled'):
            await self.db.add_audit_log(
                interaction.guild.id,
                "activity_scan",
                interaction.user.id,
                details=f"Found {len(inactive_user_ids)} inactive members"
            )


async def setup(bot):
    await bot.add_cog(Members(bot))
