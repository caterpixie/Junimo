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
            "title": "Chore of the Day!",
            "description": f"**{chore['description']}**",
            "color": 0xFFA0BE,
            "image": {
                "url": chore['gif_url']
            }
        }

        async with aiohttp.ClientSession() as session:
            await session.post(webhook_url, json={"embeds": [embed]})
            await interaction.response.send_message("Chore posted!", ephemeral=True
