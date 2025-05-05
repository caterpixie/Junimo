import discord
from discord import app_commands
import re

bot = None
def set_bot(bot_instance):
    global bot
    bot = bot_instance

@app_commands.command(name="uwu", description="UuW-ifies a message")
async def uwu(interaction: discord.Interaction, message: str):
    message = message.replace("r", "w").replace("R", "W")
    message = message.replace("l", "w").replace("L", "W")

    await interaction.response.send_message("-#", message)
