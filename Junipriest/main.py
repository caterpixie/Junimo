import os
import logging
from dotenv import load_dotenv

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

load_dotenv()

CONFESSION_APPROVAL_CHANNEL = 1322431042501738550

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s %(message)s",
)

async def restore_pending_confessions(bot: commands.Bot) -> None:
    import json
    path = "pending_confessions.json"
    if not os.path.exists(path):
        logging.info("[RESTORE] No pending confessions to restore.")
        return

    with open(path, "r", encoding="utf-8") as f:
        pending = json.load(f)

    try:
        channel = await bot.fetch_channel(CONFESSION_APPROVAL_CHANNEL)
    except Exception as e:
        logging.error(f"[RESTORE ERROR] Could not fetch approval channel: {e}")
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
            logging.info(f"[RESTORE] Restored view for message {msg_id}")
        except Exception as e:
            logging.warning(f"[RESTORE ERROR] Could not restore {msg_id}: {e}")

class Client(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pool: aiomysql.Pool | None = None

    async def setup_db_pool(self) -> None:
        """Create and attach the aiomysql pool to the bot."""
        self.pool = await aiomysql.create_pool(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "3306")),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASS", ""),
            db=os.getenv("DB_NAME", "junipriest"),
            autocommit=True,
            minsize=int(os.getenv("DB_MINSIZE", "1")),
            maxsize=int(os.getenv("DB_MAXSIZE", "5")),
        )
        logging.info("[DB] MySQL pool created.")

    async def setup_hook(self) -> None:
        await self.setup_db_pool()

        set_confessions_bot(self)
        self.add_view(ConfessionInteractionView(self))
        
        await restore_pending_confessions(self)

        self.tree.add_command(confession_group)
        self.tree.add_command(reply_to_confession_context)
        await self.tree.sync()
        logging.info("[SYNC] App commands synced.")

    async def close(self) -> None:
        if self.pool is not None:
            self.pool.close()
            await self.pool.wait_closed()
            logging.info("[DB] MySQL pool closed.")
        await super().close()

    async def on_ready(self):
        logging.info(f"Logged in as {self.user} (id: {self.user.id})")
        
intents = discord.Intents.default()
intents.message_content = True
bot = Client(command_prefix="?", intents=intents)

set_confessions_bot(bot)
bot.run(os.getenv("DISCORD_TOKEN"))



