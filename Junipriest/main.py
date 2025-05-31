import os
from dotenv import load_dotenv
load_dotenv()

import discord
from discord.ext import commands
import aiomysql
import urllib.parse

from confessions import (
    confession_group,
    reply_to_confession_context,
    set_bot as set_confessions_bot,
    ConfessionInteractionView
)

class Client(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pool = None

    async def setup_hook(self):
        set_confessions_bot(self)
        self.add_view(ConfessionInteractionView(self))  # ApprovalView removed

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

        guild_id = discord.Object(id=1322072874214756375)
        self.tree.add_command(confession_group, guild=guild_id)
        self.tree.add_command(reply_to_confession_context, guild=guild_id)
        await self.tree.sync(guild=guild_id)

        # Re-attach ApprovalView to all pending messages
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute("SELECT * FROM pending_confessions")
                    pending = await cur.fetchall()
        
                    channel = self.get_channel(CONFESSION_APPROVAL_CHANNEL)
                    if channel:
                        for row in pending:
                            try:
                                msg = await channel.fetch_message(row["message_id"])
                                view = ApprovalView(
                                    confession_text=row["confession_text"],
                                    submitter=await self.fetch_user(row["submitter_id"]),
                                    confession_number=0,  # Optional: store in DB if needed
                                    type=row["type"],
                                    reply_to_message_id=row["reply_to_message_id"]
                                )
                                await msg.edit(view=view)
                            except discord.NotFound:
                                # Message was deleted manually — clean it up from the DB
                                async with conn.cursor() as cleanup:
                                    await cleanup.execute("DELETE FROM pending_confessions WHERE message_id = %s", (row["message_id"],))
        except Exception as e:
            print(f"Error reattaching approval views: {e}")

    async def on_ready(self):
        print(f'Logged on as {self.user}')

intents = discord.Intents.default()
intents.message_content = True
bot = Client(command_prefix="?", intents=intents)

set_confessions_bot(bot)
bot.run(os.getenv("DISCORD_TOKEN"))
