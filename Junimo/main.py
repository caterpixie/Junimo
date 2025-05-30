import os
from dotenv import load_dotenv
load_dotenv()

import discord
from discord.ext import commands
import aiomysql
import urllib.parse

from qotd import qotd_group, auto_post_qotd, set_bot as set_qotd_bot
from chores import set_bot as set_chores_bot, auto_post_chores
from uwu import set_bot as set_uwu_bot, uwu
from triggers import set_bot as set_trigger_bot

class Client(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pool = None

    async def setup_hook(self):
        db_url = os.getenv("DATABASE_URL")
        parsed = urllib.parse.urlparse(db_url)
    
        self.pool = await aiomysql.create_pool(
            host=parsed.hostname,
            port=parsed.port or 3306,
            user=parsed.username,
            password=parsed.password,
            db=parsed.path[1:],
            autocommit=True,
        )
        self.tree.add_command(qotd_group)
        self.tree.add_command(uwu)
        await self.tree.sync()

    async def on_ready(self):
        print(f'Logged on as {self.user}')
        if not auto_post_qotd.is_running():
            auto_post_qotd.start()
        
        if not auto_post_chores.is_running():
            auto_post_chores.start()

intents = discord.Intents.default()
intents.message_content = True
bot = Client(command_prefix="?", intents=intents)

# Set bot instance in each module
set_qotd_bot(bot)
set_chores_bot(bot)
set_uwu_bot(bot)
set_trigger_bot(bot)

bot.run(os.getenv("DISCORD_TOKEN"))
