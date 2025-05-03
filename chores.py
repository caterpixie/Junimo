import discord
from discord import app_commands
from datetime import datetime
from zoneinfo import ZoneInfo
import aiohttp
import os

bot = None

def set_bot(bot_instance):
    global bot
    bot = bot_instance

    # Define and register the /add_chore command
    @app_commands.command(name="add_chore", description="Add a new chore to the table")
    async def add_chore(
        interaction: discord.Interaction,
        description: str,
        first_post_at: str,
        interval_days: int,
        gif_url: str = None,
    ):
        try:
            post_time = datetime.strptime(first_post_at, "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo("America/Chicago"))
        except ValueError:
            await interaction.response.send_message("Date format must be YYYY-MM-DD", ephemeral=True)
            return

        if interval_days not in (7, 14, 28):
            await interaction.response.send_message("Interval must be 7, 14, or 28 days.", ephemeral=True)
            return

        await bot.pool.execute(
            """
            INSERT INTO chores (guild_id, description, first_post_at, interval_days, gif_url)
            VALUES ($1, $2, $3, $4, $5)
            """,
            interaction.guild.id, description, post_time, interval_days, gif_url
        )

        await interaction.response.send_message(f"Chore added: {description}", ephemeral=True)

    bot.tree.add_command(add_chore)

    # Existing test command
    @bot.tree.command(name="chore_test", description="Manually post chore")
    async def chore_test(interaction: discord.Interaction):
        chore = await bot.pool.fetchrow(
            "SELECT * FROM chores WHERE is_active = TRUE ORDER BY first_post_at ASC LIMIT 1"
        )

        webhook_url = os.getenv("WEBHOOK_URL")
        if not webhook_url:
            await interaction.response.send_message("Webhook URL not configured.", ephemeral=True)
            return

        embed = {
            "title": chore["description"],
            "description": f"Next due: {chore['first_post_at'].strftime('%Y-%m-%d')}",
            "color": 0xFFA4C6,
            "image": {"url": chore["gif_url"]} if chore["gif_url"] else {}
        }

        async with aiohttp.ClientSession() as session:
            await session.post(webhook_url, json={"embeds": [embed]})
            await interaction.response.send_message("Chore posted!", ephemeral=True)
