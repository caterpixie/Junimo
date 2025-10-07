import os
from dotenv import load_dotenv
load_dotenv()

import json
import urllib.parse

import discord
from discord.ext import commands
import aiomysql

from confessions import (
    confession_group,
    reply_to_confession_context,
    set_bot as set_confessions_bot,
    ConfessionInteractionView,
    ApprovalView,
)

CONFESSION_APPROVAL_CHANNEL = 1322431042501738550
GUILD_ID = 1322072874214756375 

async def restore_pending_confessions(bot: commands.Bot):
    if not os.path.exists("pending_confessions.json"):
        print("[RESTORE] No pending confessions to restore.")
        return

    with open("pending_confessions.json", "r", encoding="utf-8") as f:
        pending = json.load(f)

    try:
        channel = await bot.fetch_channel(CONFESSION_APPROVAL_CHANNEL)
    except Exception as e:
        print(f"[RESTORE ERROR] Could not fetch approval channel: {e}")
        return

    for msg_id, data in pending.items():
        try:
            message = await channel.fetch_message(int(msg_id))
            submitter = await bot.fetch_user(data["submitter_id"])

            view = ApprovalView(
                confession_text=data["confession_text"],
                submitter=submitter,
                confession_number=data["confession_number"],
                type=data["type"],
                reply_to_message_id=data.get("reply_to_message_id"),
            )
            await message.edit(view=view)
            print(f"[RESTORE] Restored view for message {msg_id}")
        except Exception as e:
            print(f"[RESTORE ERROR] Could not restore view for message {msg_id}: {e}")

class Client(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pool: aiomysql.Pool | None = None

    async def setup_hook(self):
        
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            raise RuntimeError("DATABASE_URL is not set")

        parsed = urllib.parse.urlparse(db_url)
        user = urllib.parse.unquote(parsed.username or "")
        password = urllib.parse.unquote(parsed.password or "")
        database = parsed.path.lstrip("/")

        self.pool = await aiomysql.create_pool(
            host=parsed.hostname,
            port=parsed.port or 3306,
            user=user or None,
            password=password or None,
            db=database,
            autocommit=True,
        )

        set_confessions_bot(self)
        
        self.add_view(ConfessionInteractionView(self))
        await restore_pending_confessions(self)

        guild_obj = discord.Object(id=GUILD_ID)

        self.tree.add_command(confession_group, guild=guild_obj)
        self.tree.add_command(reply_to_confession_context, guild=guild_obj)
        await self.tree.sync(guild=guild_obj)
        

    async def on_ready(self):
        print(f"Logged on as {self.user}")


intents = discord.Intents.default()
intents.message_content = True 

bot = Client(command_prefix="?", intents=intents)

bot.run(os.getenv("DISCORD_TOKEN"))


