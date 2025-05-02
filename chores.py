import discord
from discord.ext import tasks
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import aiohttp
import os

bot = None

def set_bot(bot_instance):
    global bot
    bot = bot_instance

# Manual command to test embed view
@bot.tree.command(name="chore_test", description="Manually post chore")
async def chore_test(interaction: discord.Interaction):
    chore = await bot.pool.fetchrow(
        "SELECT * FROM chores WHERE is_active = TRUE ORDER BY first_post_at ASC LIMIT 1"
    )

    webhook_url = os.getenv("https://discord.com/api/webhooks/1367720529292951602/bCe9LBAJS6rr6XHcUNhQevnC3QxlCRrwojo0vxAXxdgtA_J-SkxXYPwvh8D7rLpHJ9vC")
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
