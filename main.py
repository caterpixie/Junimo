import os
from dotenv import load_dotenv
load_dotenv()

import discord
from discord.ext import commands
import asyncpg
from setup import setup_chores, set_bot as setup_set_bot, delete_chores_table
from qotd import qotd_group, auto_post_qotd, set_bot as set_qotd_bot
from chores import set_bot as set_chores_bot, chore_add

class Client(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pool = None

    async def setup_hook(self):
        self.pool = await asyncpg.create_pool(os.getenv("DATABASE_URL"))
        self.tree.add_command(qotd_group)
        await self.tree.sync()

    async def on_ready(self):
        print(f'Logged on as {self.user}')
        if not auto_post_qotd.is_running():
            auto_post_qotd.start()

intents = discord.Intents.default()
intents.message_content = True
bot = Client(command_prefix="!", intents=intents)

# Set bot instance in each module
setup_set_bot(bot)
set_qotd_bot(bot)
set_chores_bot(bot)

# Add setup commands
bot.tree.add_command(setup_chores)
bot.tree.add_command(delete_chores_table)

bot.tree.add_command(chore_add)

bot.run(os.getenv("DISCORD_TOKEN"))
