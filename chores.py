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

    # Define and register the /add_chore command
    @app_commands.command(name="add_chore", description="Add a new chore to the table")
    async def add_chore(
        interaction: discord.Interaction,
        name: str,
        description: str,
        first_post_at: str,
        interval_days: int,
        gif_url: str = None,
    ):
        description = description.replace("\\n", "\n")
        try:
            await interaction.response.defer(ephemeral=True)  # <-- this buys you more time
    
            post_time = datetime.strptime(first_post_at, "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo("America/Chicago"))
    
            if interval_days not in (7, 14, 28):
                await interaction.followup.send("Interval must be 7, 14, or 28 days.")
                return
    
            await bot.pool.execute(
                """
                INSERT INTO chores (guild_id, name, description, first_post_at, interval_days, gif_url)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                interaction.guild.id, name, description, post_time, interval_days, gif_url
            )
    
            await interaction.followup.send(f"Chore added: {description}")
        except ValueError:
            await interaction.followup.send("Date/time format must be YYYY-MM-DD HH:MM (24-hour)")
        except Exception as e:
            print("ERROR in add_chore:", e)
            await interaction.followup.send("Something went wrong adding the chore.")

@tasks.loop(minutes=1)
async def auto_post_chores():
    now = datetime.now(ZoneInfo("America/Chicago"))

    chores = await bot.pool.fetch("""
        SELECT * FROM chores
        WHERE is_active = TRUE
    """)

    webhook_url = os.getenv("WEBHOOK_URL")
    if not webhook_url:
        print("Webhook URL not found.")
        return

    async with aiohttp.ClientSession() as session:
        for chore in chores:
            first_post_at = chore["first_post_at"]
            last_posted = chore["last_posted"]
            interval = chore["interval_days"]

            # Skip if it's not yet time for the first post
            if last_posted is None:
                if now < first_post_at:
                    continue
            else:
                next_post = last_posted + timedelta(days=interval)
                if now < next_post:
                    continue

            # Post the chore
            embed = {
                "title": chore["name"],
                "description": chore["description"],
                "color": 0xFFA4C6,
            }
            if chore["gif_url"]:
                embed["image"] = {"url": chore["gif_url"]}

            await session.post(webhook_url, json={"embeds": [embed]})
            await bot.pool.execute(
                "UPDATE chores SET last_posted = $1 WHERE id = $2",
                now, chore["id"]
            )
