import os
from dotenv import load_dotenv
load_dotenv()

# TEST

import discord
from discord.ext import commands
from funwarns import set_bot as set_warn_bot, piss_on, give_foot, mop, sock, gag, ungag

class Client(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pool = None

    async def on_ready(self):
        self.tree.add_command(piss_on)
        self.tree.add_command(give_foot)
        self.tree.add_command(mop)
        self.tree.add_command(sock)
        self.tree.add_command(gag)
        self.tree.add_command(ungag)
        
        await self.tree.sync()
        print(f'Logged on as {self.user}')

intents = discord.Intents.default()
intents.message_content = True
bot = Client(command_prefix="!", intents=intents)

# Warn commands
set_warn_bot(bot)

bot.run(os.getenv("DISCORD_TOKEN"))
