import os
import discord
from discord import app_commands, Embed, Color, Interaction
from discord.ext import commands, tasks
from discord.ext.commands import has_permissions
from clear import ClearCommands
import sqlite3
import logging
from logging.handlers import RotatingFileHandler
import asyncio
import re
import typing

import clear

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        RotatingFileHandler('roleinvite.log', maxBytes=5242880, backupCount=5, encoding='utf-8', mode='a'),
        logging.StreamHandler()
    ]
)


DB_PATH = "invites.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS invites (
        _id INTEGER PRIMARY KEY,
        invite_id TEXT UNIQUE,
        guild_id TEXT,
        role_id INTEGER,
        inviter INTEGER,
        uses INTEGER DEFAULT 0,
        max_uses INTEGER,
        duration INTEGER,
        channel_id INTEGER
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS default_roles (
        guild_id TEXT PRIMARY KEY,
        role_id INTEGER
    )''')
    conn.commit()
    conn.close()


def timer(time: str) -> int:
    units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
    match = re.fullmatch(r'([0-9]*\.?[0-9]+)([smhd])', time)
    if match is None:
        raise ValueError("Invalid time input")
    return int(float(match[1]) * units[match[2]])


def load_invites(guild_id: str) -> dict[str, dict[str, typing.Any]]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM invites WHERE guild_id = ?", (guild_id,))
    rows = c.fetchall()
    invites = {}
    for row in rows:
        invites[row[1]] = {
            "_id": row[0],
            "guild_id": row[2],
            "role_id": row[3],
            "inviter": row[4],
            "uses": row[5],
            "max_uses": row[6],
            "duration": row[7],
            "channel_id": row[8],
        }
    conn.close()
    return invites


def save_invite(invite_id: str, guild_id: str, role_id: int, inviter: int, uses: int, max_uses: int,
                duration: int, channel_id: int) -> None:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO invites (invite_id, guild_id, role_id, inviter, uses, max_uses, 
                duration, channel_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
              (invite_id, guild_id, role_id, inviter, uses, max_uses, duration, channel_id))
    conn.commit()
    conn.close()


def delete_invite(invite_id: str) -> None:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM invites WHERE invite_id = ?", (invite_id,))
    conn.commit()
    conn.close()


def update_invite_uses(invite_id: str, uses: int) -> None:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE invites SET uses = ? WHERE invite_id = ?", (uses, invite_id))
    conn.commit()
    conn.close()


def get_default_role(guild_id: int) -> int:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT role_id FROM default_roles WHERE guild_id = ?", (str(guild_id),))
    result = c.fetchone()
    conn.close()
    return int(result[0]) if result else 0


def set_default_role(guild_id: str, role_id: int) -> None:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO default_roles (guild_id, role_id) VALUES (?, ?)", (guild_id, role_id))
    conn.commit()
    conn.close()

intents = discord.Intents.default()
intents.invites = True
intents.guilds = True
intents.members = True
intents.messages = True

Role_Invite_Bot = commands.Bot(command_prefix="!", intents=intents)
init_db()


class RoleInvite(commands.Cog, name="roleinvite"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.pending: set = set()

    invite_group = app_commands.Group(name="rinv", description="Commands for managing role invites", guild_only=True)

    @invite_group.command(name="update", description="Update a Role Invite's uses")
    @commands.has_permissions(administrator=True)
    async def update_invite(self, interaction: discord.Interaction, invite_id: str, uses: int) -> None:
        try:
            update_invite_uses(invite_id, uses)
            await interaction.response.send_message(f"Invite {invite_id} uses updated to {uses}.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Failed to update invite: {e}", ephemeral=True)

    @invite_group.command(name="revoke", description="Revoke a Role Invite")
    @commands.has_permissions(administrator=True)
    async def revoke_invite(self, interaction: discord.Interaction, invite_id: str) -> None:
        try:
            invite = await self.bot.fetch_invite(invite_id)
            await invite.delete()
            delete_invite(invite_id)
            await interaction.response.send_message(f"Revoked invite {invite.url}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Failed to update invite: {e}", ephemeral=True)

    @invite_group.command(name="create", description="Create a Role Invite")
    @commands.has_permissions(administrator=True)
    async def create(
            self,
            interaction: discord.Interaction,
            role: discord.Role,
            channel: typing.Optional[discord.TextChannel] = None,
            duration: typing.Optional[str] = "0s",
            max_uses: typing.Optional[int] = 0
    ) -> None:
        default_channel = interaction.guild.system_channel or interaction.guild.public_updates_channel
        if channel is None:
            channel = default_channel or discord.utils.get(interaction.guild.text_channels)
        if channel is None:
            await interaction.response.send_message("No channel available to create the invite.", ephemeral=True,
                                                    delete_after=10)
            return
        try:
            duration_seconds = timer(duration) if duration not in ["0s", 0, "0"] else 0
        except ValueError:
            await interaction.response.send_message(
                "Invalid time input! Use e.g. `10m` for 10 minutes.",
                ephemeral=True, delete_after=10
            )
            return

        await interaction.response.send_message("Creating the Role Invite...", ephemeral=True, delete_after=10)
        try:
            invite = await channel.create_invite(
                max_age=duration_seconds,
                max_uses=max_uses if not max_uses == 1 else 2,
                reason=f"Role Invite for {role.name} by {interaction.user.name}"
            )
            guild_id = str(interaction.guild.id)
            save_invite(invite.id, guild_id, role.id, interaction.user.id, 0, max_uses, duration_seconds, channel.id)
            await interaction.followup.send(
                f"Role Invite created! Users who use the invite `{invite.url}` will receive the role **{role.name}**.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(f"Error creating the invite: {str(e)}", ephemeral=True)

    @invite_group.command(name="list", description="List all Role Invites")
    @commands.has_permissions(administrator=True)
    async def list_invites(self, interaction: discord.Interaction) -> None:
        guild_id = str(interaction.guild.id)
        invites_data = load_invites(guild_id)
        await interaction.response.defer(ephemeral=True)
        if not invites_data:
            await interaction.response.send_message("No role invites available.")
            return
        embeds = []
        current_embed = discord.Embed(title="Role Invites", color=discord.Color.blue())
        for index, (invite_id, data) in enumerate(invites_data.items(), 1):
            invite_url = f"https://discord.gg/{invite_id}"
            role = interaction.guild.get_role(data['role_id'])
            current_embed.add_field(
                name=f"Invite #{index}",
                value=f"[{invite_id}]({invite_url})\n"
                      f"Role: {f'<@&{role.id}>' if role else 'Role not found'}\n"
                      f"Uses: {data['uses']} / {data['max_uses'] if data['max_uses'] else "∞"}",
                inline=True
            )
            if index % 5 == 0:
                embeds.append(current_embed)
                current_embed = discord.Embed(title="Role Invites", color=discord.Color.blue())
        embeds.append(current_embed)
        for embed in embeds:
            await interaction.followup.send(embed=embed, ephemeral=True)

    @invite_group.command(name="setdefault", description="Set a default role for new members in the guild")
    @commands.has_permissions(administrator=True)
    async def set_default_role(self, interaction: discord.Interaction, role: discord.Role) -> None:
        set_default_role(str(interaction.guild.id), role.id)
        await interaction.response.send_message(f"Default role set to {role.name}.", ephemeral=True)

    @app_commands.command(name="info", description="Shows bot info")
    @commands.has_permissions(administrator=True)
    async def info(self, interaction: discord.Interaction) -> None:
        client_id = self.bot.application_id
        invite_link = f"https://discord.com/oauth2/authorize?client_id={client_id}&permissions=0&scope=bot+applications.commands"

        embed = discord.Embed(title="Bot Information", color=Color.blue())
        embed.description = f"[Invite me to your guild!]({invite_link})"
        embed.add_field(name="Bot Name", value=self.bot.user.name, inline=True)
        embed.add_field(name="Bot ID", value=self.bot.user.id, inline=True)
        embed.add_field(name="Server Count", value=f"{len(self.bot.guilds)}", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        """Listen for new invites being created and save them in the database."""
        guild_id = str(invite.guild.id)
        save_invite(invite.id, guild_id, 0, invite.inviter.id, invite.uses, invite.max_uses or 0, 0, 0)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite):
        """Listen for invites being deleted and remove them from the database."""
        delete_invite(invite.id)

    @commands.Cog.listener(name="on_member_join")
    async def on_member_join(self, member: discord.Member):
        """Event handler for member joins, assigns role based on invite used and updates invite data."""
        try:
            guild_invites_list = await member.guild.invites()
        except discord.Forbidden:
            return  # Permissions to view invites were denied

        if member.pending:
            return self.pending.add(member)
        if default_role := member.guild.get_role(get_default_role(member.guild.id)):
            await member.add_roles(default_role)
        await self._give_role(member, guild_invites_list)

    @tasks.loop(seconds=10)
    async def clean_up_invites(self):
        """Ensure invites from the server are present in the database and remove any that are not."""
        # Get current invites from the server
        current_invites = {}
        for guild in self.bot.guilds:
            try:
                invites = await guild.invites()
                for invite in invites:
                    current_invites[invite.id] = (
                    invite.code, invite.uses, str(guild.id), invite.inviter.id, invite.max_uses, invite.channel.id)
            except discord.Forbidden:
                continue

        """Get all invite IDs from the database."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT invite_id FROM invites")
        db_invite_ids = {row[0] for row in cursor.fetchall()}

        # Find invites that are in the server but not in the database
        invites_to_add = []
        for invite_id, (invite_code, invite_uses, guild_id, inviter, max_uses, channel_id) in current_invites.items():
            if invite_id not in db_invite_ids:
                # Append only the necessary fields for saving, and use None for missing fields
                invites_to_add.append((invite_id, guild_id, None, inviter, invite_uses, max_uses, None,
                                       channel_id))  # None for role_id and duration

        # Insert missing invites into the database
        for invite_data in invites_to_add:
            save_invite(*invite_data)

        if invites_to_add:
            logging.info(f"Added {len(invites_to_add)} invites to the database that were missing.")

        # Optionally, you can remove invites from the database that are no longer present on the server
        invites_to_delete = db_invite_ids - current_invites.keys()

        if invites_to_delete:
            # Create a placeholder for bulk delete
            placeholders = ', '.join('?' for _ in invites_to_delete)
            cursor.execute(f"DELETE FROM invites WHERE invite_id IN ({placeholders})", tuple(invites_to_delete))
            logging.info(
                f"Deleted {len(invites_to_delete)} invites from the database as they are no longer present on the server.")

        conn.commit()
        conn.close()

    @staticmethod
    async def _give_role(member: discord.Member, invites: list[discord.Invite]):
        """Assign role based on the invite used."""
        guild_id = str(member.guild.id)

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Get invite data which includes uses
        cursor.execute("SELECT invite_id, role_id, uses FROM invites WHERE guild_id = ?", (guild_id,))
        guild_invites_data = cursor.fetchall()

        for invite_id, role_id, db_uses in guild_invites_data:
            invite = next((i for i in invites if i.id == invite_id), None)
            if invite and invite.uses > db_uses:  # Compare against uses from the database
                role = member.guild.get_role(role_id)
                if role:
                    try:
                        await member.add_roles(role)
                        logging.info(f"Assigned role {role.name} to {member.name} using invite {invite.code}.")
                        # Update invite uses in the database
                        cursor.execute("UPDATE invites SET uses = uses + 1 WHERE invite_id = ?", (invite.id,))
                        conn.commit()
                    except discord.Forbidden:
                        logging.warning(f"Failed to assign role {role.name} to {member.name}. Missing permissions.")
                    except Exception as e:
                        logging.error(f"Error assigning role {role.name} to {member.name}: {str(e)}")
                else:
                    logging.error(f"Role with ID {role_id} does not exist. Removing invite {invite_id} from database.")
                    delete_invite(invite_id)
                break  # Exit the loop after assigning the role

        conn.close()

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before in self.pending and before.pending != after.pending:
            try:
                guild_invites_list = await after.guild.invites()
            except errors.Forbidden:
                return
            if default_role := get_default_role(before.guild.id):
                await after.add_roles(after.guild.get_role(default_role))
            self.pending.remove(before)
            return await self._give_role(after, guild_invites_list)

    def cog_unload(self):
        if self.clean_up_invites:
            self.clean_up_invites.cancel()



async def setup(role_invite_bot: Role_Invite_Bot) -> None:
    check_invites = RoleInvite(Role_Invite_Bot).clean_up_invites
    if not check_invites.is_running():
        check_invites.start()
    await role_invite_bot.add_cog(RoleInvite(role_invite_bot))
    await role_invite_bot.add_cog(ClearCommands(role_invite_bot))

@Role_Invite_Bot.event
async def on_ready() -> None:
    await setup(Role_Invite_Bot)
    await Role_Invite_Bot.tree.sync()
    print(f"Bot is ready! Logged in as {Role_Invite_Bot.user}")


Role_Invite_Bot.run(os.getenv('TOKEN'))
