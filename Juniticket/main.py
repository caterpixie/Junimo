import os
from dotenv import load_dotenv
load_dotenv()

import discord
from discord.ext import commands
import aiomysql
import urllib.parse

import tickets
from tickets import ticket_group, set_bot as set_ticket_bot

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

        set_ticket_bot(self)

        self.add_view(TicketPanelView())
        self.add_view(CloseTicketView())  
        self.add_view(ConfirmCloseView())  
        
        self.tree.add_command(ticket_group)
        await self.tree.sync()

    
    async def on_ready(self):
        print(f"Logged on as {self.user}")


intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = Client(command_prefix="??", intents=intents)

bot.run(os.getenv("DISCORD_TOKEN"))
