import discord
from discord import app_commands
from discord.ext import tasks
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import aiohttp
import os
import aiomysql

# =========================
# CONFIGURATION
# =========================

# Do not change the timezone or the datetime format. 
# It is necessary for it to be in America/Chicago to work with the PebbleHost server.
TIMEZONE_NAME = "America/Chicago"
DATETIME_FORMAT = "%Y-%m-%d %H:%M"

# See .env file to change the webhook URL
WEBHOOK_ENV_VAR = "WEBHOOK_URL"

ALLOWED_INTERVAL_DAYS = (7, 14, 28)

CHORE_PING_ROLE_ID = "1332568557313200188"
CHORE_EMBED_COLOR = 0xFFA4C6

# =========================
# BOT HOOKUP
# =========================
bot = None


def set_bot(bot_instance):
    global bot
    bot = bot_instance

    @app_commands.command(name="add_chore", description="Add a new chore to the table")
    async def add_chore(
        interaction: discord.Interaction,
        name: str,
        description: str,
        first_post_at: str,
        interval_days: int,
        gif_url: str = None,
    ):
        description = description.replace("\\n", "\n")
        try:
            await interaction.response.defer(ephemeral=True)

            post_time = datetime.strptime(first_post_at, DATETIME_FORMAT).replace(
                tzinfo=ZoneInfo(TIMEZONE_NAME)
            )

            if interval_days not in ALLOWED_INTERVAL_DAYS:
                allowed = ", ".join(map(str, ALLOWED_INTERVAL_DAYS))
                await interaction.followup.send(f"Interval must be {allowed} days.")
                return

            async with bot.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        INSERT INTO chores (guild_id, name, description, first_post_at, interval_days, gif_url)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (interaction.guild.id, name, description, post_time, interval_days, gif_url),
                    )

            await interaction.followup.send(f"Chore added: {description}")

        except ValueError:
            await interaction.followup.send(
                f"Date/time format must be {DATETIME_FORMAT.replace('%Y', 'YYYY').replace('%m', 'MM').replace('%d', 'DD').replace('%H', 'HH').replace('%M', 'MM')} (24-hour)"
            )
        except Exception as e:
            print("ERROR in add_chore:", e)
            await interaction.followup.send("Something went wrong adding the chore.")

    #bot.tree.add_command(add_chore)


@tasks.loop(minutes=1)
async def auto_post_chores():
    now = datetime.now(ZoneInfo(TIMEZONE_NAME))

    async with bot.pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                """
                SELECT * FROM chores
                WHERE is_active = TRUE
                """
            )
            chores = await cur.fetchall()

    webhook_url = os.getenv(WEBHOOK_ENV_VAR)
    if not webhook_url:
        print(f"{WEBHOOK_ENV_VAR} not found.")
        return

    async with aiohttp.ClientSession() as session:
        for chore in chores:
            first_post_at = chore["first_post_at"]
            last_posted = chore["last_posted"]
            interval = chore["interval_days"]

            if first_post_at and first_post_at.tzinfo is None:
                first_post_at = first_post_at.replace(tzinfo=ZoneInfo(TIMEZONE_NAME))
            if last_posted and last_posted.tzinfo is None:
                last_posted = last_posted.replace(tzinfo=ZoneInfo(TIMEZONE_NAME))

            if last_posted is None:
                if now < first_post_at:
                    continue
            else:
                next_post = last_posted + timedelta(days=interval)
                if now < next_post:
                    continue

            embed = {
                "title": chore["name"],
                "description": chore["description"],
                "color": CHORE_EMBED_COLOR,
            }
            if chore["gif_url"]:
                embed["image"] = {"url": chore["gif_url"]}

            payload = {
                "content": f"<@&{CHORE_PING_ROLE_ID}>",
                "embeds": [embed],
                "allowed_mentions": {"roles": [CHORE_PING_ROLE_ID]},
            }

            await session.post(webhook_url, json=payload)
            
            async with bot.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "UPDATE chores SET last_posted = %s WHERE id = %s",
                        (now, chore["id"]),
                    )
