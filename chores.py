import discord
from discord.ext import tasks
from discord import app_commands
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import aiohttp
import os

bot = None

def set_bot(bot_instance):
    global bot
    bot = bot_instance

# Manual command to test embed view
@app_commands.command(name="chore_test", description="Manually post the first active chore")
async def chore_test(interaction: discord.Interaction):
    chore = await bot.pool.fetchrow(
        "SELECT * FROM chores WHERE is_active = TRUE ORDER BY first_post_at ASC LIMIT 1"
    )

    webhook_url = os.getenv("WEBHOOK_URL")
    if not webhook_url:
        print("Webhook URL not configured in environment.")
        return

    embed = {
        "title": "Chore of the Day!",
        "description": f"**{chore['description']}**",
        "color": 0xFFA0BE, 
        "image": {
            "url": chore['gif_url']
        }
    } 
