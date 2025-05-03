import discord
from discord import app_commands

bot = None
def set_bot(bot_instance):
    global bot
    bot = bot_instance
