import discord
from discord import app_commands
import re
import random

bot = None
def set_bot(bot_instance):
    global bot
    bot = bot_instance

@app_commands.command(name="uwu", description="UuW-ifies a message")
async def uwu(interaction: discord.Interaction, message: str):
    message = message.replace("r", "w").replace("l", "w")
    message = message.replace("R", "W").replace("L", "W")
    message = re.sub(r"n(?!\b)", "ny", message)
    message = re.sub(r"N(?!\b)", "Ny", message)
    
    await interaction.response.send_message(f"-# {message}")
