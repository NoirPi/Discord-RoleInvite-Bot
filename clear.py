from time import sleep

import discord.errors
from discord import app_commands, Interaction, TextChannel, Member, DMChannel
from discord.ext import commands
import asyncio

from discord.ext.commands import guild_only, dm_only


class ClearCommands(commands.Cog, name="clear"):
    """Clear Commands"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    clear_commands = app_commands.Group(name="clear", description="Clear Commands", guild_only=True)

    # Nuke command
    @clear_commands.command(name="nuke", description="Nuke a whole Channel")
    @commands.has_permissions(administrator=True)
    async def _nuke(self, interaction: Interaction, channel: TextChannel = None):
        """Nuke a whole Channel"""
        channel = channel or interaction.channel
        if channel:
            new_channel = await channel.clone()
            await new_channel.edit(position=channel.position)
            await channel.delete()
            await new_channel.send(
                embed=discord.Embed(
                    description=f'💣 Channel #{channel.name} successfully nuked by {interaction.user.display_name}',
                    color=0x1FFF00, timestamp=interaction.created_at), delete_after=30)

    # Clear main command group
    @clear_commands.command(name="default", description="Delete Messages inside a Text Channel")
    @commands.has_permissions(administrator=True)
    @app_commands.describe(amount="Number of messages to delete")
    async def default(self, interaction: Interaction, amount: int):
        """Delete Messages inside a Text Channel"""
        if interaction.channel:
            deleted = await bulk_delete_messages(interaction.channel, amount, lambda m: not m.pinned)
            await clear_success_message(interaction, deleted)

    # Clear bot messages
    @clear_commands.command(name="bot", description="Delete Messages from Bots inside a Text Channel")
    @commands.has_permissions(administrator=True)
    async def bot(self, interaction: Interaction, amount: int):
        """Delete Messages from Bots"""
        if interaction.channel:
            deleted = await bulk_delete_messages(interaction.channel, amount, lambda m: m.author.bot and not m.pinned)
            await clear_success_message(interaction, deleted)

    # Clear messages from a specific member
    @clear_commands.command(name="member", description="Delete Messages from a specific Member")
    @commands.has_permissions(administrator=True)
    async def member(self, interaction: Interaction, user: Member, amount: int):
        """Delete Messages from a specific Member"""
        if interaction.channel:
            deleted = await bulk_delete_messages(interaction.channel, amount, lambda m: m.author == user and not m.pinned)
            await clear_success_message(interaction, deleted)

    # Clear messages containing a specific word
    @clear_commands.command(name="contains", description="Delete Messages containing a specific word")
    @commands.has_permissions(administrator=True)
    async def contains(self, interaction: Interaction, word: str, amount: int):
        """Delete Messages which contain a specific word"""
        if interaction.channel:
            deleted = await bulk_delete_messages(
                interaction.channel, amount, lambda m: word.lower() in m.content.lower() and not m.pinned)
            await clear_success_message(interaction, deleted)

    # Clear messages starting with a specific word
    @clear_commands.command(name="startswith", description="Delete Messages starting with a specific word")
    @commands.has_permissions(administrator=True)
    async def startswith(self, interaction: Interaction, word: str, amount: int):
        """Delete Messages that start with a specific word"""
        if interaction.channel:
            deleted = await bulk_delete_messages(
                interaction.channel, amount, lambda m: m.content.lower().startswith(word.lower()) and not m.pinned)
            await clear_success_message(interaction, deleted)

    # Clear messages with attachments
    @clear_commands.command(name="attachment", description="Delete Messages containing attachments")
    @commands.has_permissions(administrator=True)
    async def attachment(self, interaction: Interaction, amount: int):
        """Delete Messages containing attachments"""
        if interaction.channel:
            deleted = await bulk_delete_messages(interaction.channel, amount, lambda m: len(m.attachments) > 0 and not m.pinned)
            await clear_success_message(interaction, deleted)

    # Clear messages with embeds
    @clear_commands.command(name="embeds", description="Delete Messages containing embeds")
    @commands.has_permissions(administrator=True)
    async def embeds(self, interaction: Interaction, amount: int):
        """Delete Messages containing embeds"""
        if interaction.channel:
            deleted = await bulk_delete_messages(interaction.channel, amount, lambda m: len(m.embeds) > 0 and not m.pinned)
            await clear_success_message(interaction, deleted)

    # Clear messages containing mentions
    @clear_commands.command(name="mentions", description="Delete Messages containing mentions")
    @commands.has_permissions(administrator=True)
    async def mentions(self, interaction: Interaction, amount: int):
        """Delete Messages containing mentions"""
        if interaction.channel:
            deleted = await bulk_delete_messages(
                interaction.channel, amount, lambda m: (len(m.mentions) > 0 or len(m.channel_mentions) > 0 or len(m.role_mentions) > 0) and not m.pinned)
            await clear_success_message(interaction, deleted)

    # # DM clear command
    @app_commands.command(name="dm", description="Delete Bot Messages in Private DM Channels")
    @app_commands.dm_only()
    async def dm(self, interaction: Interaction):
        """Delete Bot Messages in Private DM Channels"""
        if isinstance(interaction.channel, DMChannel):
            async for msg in interaction.channel.history(limit=500):
                if msg.author == self.bot.user and not msg.pinned:
                    await msg.delete()

async def bulk_delete_messages(channel, amount, check):
    """Helper function to delete messages matching a condition."""
    try:
        delete = await channel.purge(check=check, limit=amount, bulk=True)
        # sleep(1)
        return len(delete)
    except discord.errors.NotFound:
        return None
    except discord.errors.RateLimited:
        pass

async def clear_success_message(interaction: Interaction, count: int):
    """Helper function to send a success message after clearing messages."""
    # noinspection PyBroadException
    try:
        await interaction.response.send_message(f"Deleted {count} messages.", ephemeral=True)
    except discord.errors.NotFound:
        return
    except Exception:
        pass

async def clear_check(interaction: Interaction, amount: int, limit: int) -> bool:
    """Check if the amount of messages to delete is within the allowed limit."""
    if amount > limit:
        await interaction.response.send_message(f"You can delete a maximum of {limit} messages at once.", ephemeral=True)
        return False
    return True
