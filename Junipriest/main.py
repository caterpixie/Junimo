import os
from dotenv import load_dotenv
load_dotenv()

import discord
from discord.ext import commands

from confessions import (
    confession_group,
    reply_to_confession_context,
    set_bot as set_confessions_bot,
    ConfessionInteractionView,
    ApprovalView
)

CONFESSION_APPROVAL_CHANNEL=1378213253146218557

class Client(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pool = None

    async def setup_hook(self):

        set_confessions_bot(self)
        self.add_view(ConfessionInteractionView(self)) 

        guild_id = discord.Object(id=1322072874214756375)
        self.tree.add_command(confession_group, guild=guild_id)
        self.tree.add_command(reply_to_confession_context, guild=guild_id)
        await self.tree.sync(guild=guild_id)

    async def on_ready(self):
        print(f'Logged on as {self.user}')

intents = discord.Intents.default()
intents.message_content = True
bot = Client(command_prefix="?", intents=intents)

set_confessions_bot(bot)
bot.run(os.getenv("DISCORD_TOKEN"))
