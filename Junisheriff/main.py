import os
from dotenv import load_dotenv
load_dotenv()

import discord
from discord.ext import commands
from funwarns import setup_funwarns

class Client(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pool = None

    async def on_ready(self):
        setup_funwarns(self)
        
        await self.tree.sync()
        print(f'Logged on as {self.user}')

intents = discord.Intents.default()
intents.message_content = True
bot = Client(command_prefix="?", intents=intents)

bot.run(os.getenv("DISCORD_TOKEN"))
