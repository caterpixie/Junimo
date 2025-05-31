import os
from dotenv import load_dotenv
load_dotenv()

import discord
from discord.ext import commands
import json

from confessions import confession_group, reply_to_confession_context, set_bot as set_confessions_bot, ConfessionInteractionView, ApprovalView

CONFESSION_APPROVAL_CHANNEL = 1378213253146218557

async def restore_pending_confessions(bot):
    if not os.path.exists("pending_confessions.json"):
        return

    with open("pending_confessions.json", "r") as f:
        pending = json.load(f)

    for msg_id, data in pending.items():
        try:
            channel = bot.get_channel(CONFESSION_APPROVAL_CHANNEL)
            message = await channel.fetch_message(int(msg_id))

            view = ApprovalView(
                confession_text=data["confession_text"],
                submitter=await bot.fetch_user(data["submitter_id"]),
                confession_number=data["confession_number"],
                type=data["type"],
                reply_to_message_id=data.get("reply_to_message_id")
            )

            await message.edit(view=view)
        except Exception as e:
            print(f"[RESTORE ERROR] Could not restore view for message {msg_id}: {e}")

class Client(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pool = None

    async def setup_hook(self):

        set_confessions_bot(self)
        self.add_view(ConfessionInteractionView(self)) 

        await restore_pending_confessions(self)

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
