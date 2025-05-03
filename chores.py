import discord
from discord import app_commands
from discord.ext import tasks
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import aiohttp
import os

bot = None
def set_bot(bot_instance):
    global bot
    bot = bot_instance

    @bot.tree.command(name="chore_test", description="Manually post chore")
    async def chore_test(interaction: discord.Interaction):
        chore = await bot.pool.fetchrow(
            "SELECT * FROM chores WHERE is_active = TRUE ORDER BY first_post_at ASC LIMIT 1"
        )

        webhook_url = os.getenv("WEBHOOK_URL")
        print("DEBUG - webhook_url:", webhook_url)

        if not webhook_url:
            print("Webhook URL not configured in environment.")
            await interaction.response.send_message("Webhook URL not configured.", ephemeral=True)
            return

        embed = {
            "title": f"{chore['name']}",
            "description": f"{chore['description']}",
            "color": 0xFFA4C6,
            "image": {
                "url": chore['gif_url']
            }
        }

        async with aiohttp.ClientSession() as session:
            await session.post(webhook_url, json={"embeds": [embed]})
            await interaction.response.send_message("Chore posted!", ephemeral=True)

@app_commands.command(name="add_chore", description="Add a new chore to the table")
@app_commands.describe(
    name="Name of the chore",
    description="Subtitle for the chore",
    first_post_at="Day where it will post first (2025-05-28 17:00)",
    interval_days="How many days between repeats?",
    gif_url="Direct link to gif"
)
async def chore_add(
    interaction: discord.Interaction,
    description: str,
    first_post_at: str,
    interval_days: int,
    gif_url: str = None
):

    try:
        # Parse datetime from string
        dt = datetime.strptime(first_post_at, "%Y-%m-%d %H:%M")
        dt = dt.replace(tzinfo=ZoneInfo("America/Chicago"))

        # Validate interval
        if interval_days not in (7, 14, 28):
            await interaction.response.send_message("Interval must be 7, 14, or 28 days.", ephemeral=True)
            return

        await bot.pool.execute(
            """
            INSERT INTO chores (guild_id, description, first_post_at, interval_days, gif_url)
            VALUES ($1, $2, $3, $4, $5)
            """,
            interaction.guild.id, description, dt, interval_days, gif_url
        )
        await interaction.response.send_message("Chore added successfully!", ephemeral=True)
    except ValueError:
        await interaction.response.send_message("Invalid datetime format. Use YYYY-MM-DD HH:MM", ephemeral=True)
