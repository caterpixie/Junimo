import os
from dotenv import load_dotenv
load_dotenv()

import discord
from discord.ext import commands
import aiomysql
import urllib.parse

from confessions import confession_group, reply_to_confession_context, set_bot as set_confessions_bot, ConfessionInteractionView, ApprovalView

class PersistentApprovalView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Button(style=discord.ButtonStyle.success, label="✅ Approve", custom_id="approval_approve"))
        self.add_item(Button(style=discord.ButtonStyle.danger, label="❌ Deny", custom_id="approval_deny"))
        self.add_item(Button(style=discord.ButtonStyle.danger, label="💬 Deny with Reason", custom_id="approval_deny_reason"))

    await bot.add_view(PersistentApprovalView())

class Client(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pool = None

    async def setup_hook(self):
        set_confessions_bot(self)
        self.add_view(ConfessionInteractionView(self))
        self.add_view(ApprovalView())

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
        self.tree.add_command(confession_group, guild=discord.Object(id=1322072874214756375))
        self.tree.add_command(reply_to_confession_context, guild=discord.Object(id=1322072874214756375))
        
        await self.tree.sync(guild=discord.Object(id=1322072874214756375))

    async def on_ready(self):
        print(f'Logged on as {self.user}')

intents = discord.Intents.default()
intents.message_content = True
bot = Client(command_prefix="?", intents=intents)

set_confessions_bot(bot)

bot.run(os.getenv("DISCORD_TOKEN"))
