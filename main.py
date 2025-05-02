import discord
from discord.ext import commands
import os
import asyncpg
from setup import setup_chores, set_bot as setup_set_bot, delete_chores_table
from qotd import qotd_group, auto_post_qotd

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

import qotd
qotd.set_bot(bot)

bot.run(os.getenv("DISCORD_TOKEN"))
