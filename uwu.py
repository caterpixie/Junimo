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

    prefixes = ["UwU ", "H-hewwo?? ", "OWO ", "HIIII! ", "<3 ", "Huohhhh. ", "Haiiiii! ", "*blushes* ", "^-^ ", "OwO what's this? ", ">.< "]
    suffixes = [" ʕ•ᴥ•ʔ", " ( ͡° ᴥ ͡°)", " (´・ω・｀)", " ;-;", " >_<", " ._.", " ^_^", " (• o •)", " (•́︿•̀)", " ( ´•̥̥̥ω•̥̥̥` )", " :D", " ◠‿◠✿)", " (✿ ♡‿♡)", " :3", " °○°/", " UwU", " :P", " (ʘᗩʘ')", " ( ˘ ³˘)♥", " (人◕ω◕)", " (；ω；)", " :O"]

    message = random.choice(prefixes) + message + random.choice(suffixes)
    
    await interaction.response.send_message(f"-# {message}")
