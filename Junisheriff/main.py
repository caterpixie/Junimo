import os
from dotenv import load_dotenv
load_dotenv()

import discord
from discord.ext import commands
import aiomysql
import urllib.parse
from mod import set_bot as set_warn_bot, mod_group
from log import setup_logging
from funwarns import setup_funwarns
from automod import setup_automod

class Client(commands.Bot):
    def __init__(self, guild_id: int, **kwargs):
        super().__init__(**kwargs)
        self.pool = None
        self.guild_id = guild_id 

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
        
        setup_funwarns(self)
        self.tree.add_command(mod_group)

        guild = discord.Object(id=self.guild_id)
        await self.tree.sync(guild=guild)

    async def on_ready(self):
        print(f'Logged on as {self.user}')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True
bot = Client(command_prefix="?", intents=intents, guild_id=1322423728457384018)

set_warn_bot(bot)
setup_logging(bot)
setup_automod(bot)

bot.run(os.getenv("DISCORD_TOKEN"))

