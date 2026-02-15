import discord
import re
import datetime
from safebrowsing import is_phishing_link

# ==================================
# CONFIGURATION
# ==================================

SERVER_ID = 1322423728457384018

GENERAL_CHANNEL_ID = 1322423730982490185
LOG_CHANNEL_ID = 1322430975480692789

ADMIN_ROLE_IDS = [
    1322423969361432616,
    1322425878931705857
]

ALLOWED_GIF_DOMAINS = [
    "tenor.com",
    "giphy.com",
    "discord.com",
    ".gif",
    "ezgif.com",
    "klipy.com"
]

SLUR_LIST_FILE = "slurs.txt"

# ==================================
# BOT HOOKUP
# ==================================

bot = None

def set_bot(bot_instance):
    global bot
    bot = bot_instance


def setup_automod(bot_instance: discord.Client):
    set_bot(bot_instance)

    @bot_instance.event
    async def on_message(message: discord.Message):
        if message.guild is None or message.author.bot:
            return

        if message.guild.id != SERVER_ID:
            return

        if await check_phishing(message):
            return

        if await check_no_links_in_general(message):
            return

        if await check_slurs(message):
            return

        await bot.process_commands(message)


# -------- Utilities --------

def load_slurs(filename=SLUR_LIST_FILE):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return [
                line.strip().lower()
                for line in f
                if line.strip() and not line.startswith("#")
            ]
    except FileNotFoundError:
        print(f"[automod] Could not find {filename}")
        return []


def is_slur_in_text(text, slur):
    pattern = r'\b' + re.escape(slur) + r'\b'
    return re.search(pattern, text, re.IGNORECASE)


def safe_avatar_url(user):
    return user.avatar.url if user.avatar else discord.Embed.Empty


async def log_event(channel_id: int, embed: discord.Embed):
    channel = bot.get_channel(channel_id)
    if channel:
        await channel.send(embed=embed)


# -------- Checks --------

async def check_no_links(message):
    
    CHANNEL_NO_LINKS = 1322423730982490185     # general
    CHANNEL_GIF_ONLY = 1472458580815904943     # spicy-general

    if message.channel.id not in [CHANNEL_NO_LINKS, CHANNEL_GIF_ONLY]:
        return False

    if any(role.id in ADMIN_ROLE_IDS for role in message.author.roles):
        return False

    urls = re.findall(r'https?://\S+', message.content)

    if not urls:
        return False

    if message.channel.id == CHANNEL_NO_LINKS:
        try:
            await message.delete()
        except discord.NotFound:
            pass
        return True

    if message.channel.id == CHANNEL_GIF_ONLY:
        for url in urls:
            if not any(domain in url for domain in ALLOWED_GIF_DOMAINS):
                try:
                    await message.delete()
                except discord.NotFound:
                    pass
                return True

    return False

async def check_slurs(message):
    content = message.content.lower()
    now = datetime.datetime.now(datetime.timezone.utc)

    for slur in load_slurs():  # dynamically reload list
        if is_slur_in_text(content, slur):
            embed = discord.Embed(
                title="Message Auto-deleted",
                description=(
                    f"**Message by {message.author.mention} deleted in "
                    f"{message.channel.mention} due to bad word detected**\n\n"
                    f"{message.content}"
                ),
                color=discord.Color.from_str("#99FCFF")
            )
            embed.set_author(
                name=str(message.author),
                icon_url=safe_avatar_url(message.author)
            )
            embed.timestamp = now

            await log_event(LOG_CHANNEL_ID, embed)
            await message.delete()
            return True

    return False


async def check_phishing(message):
    urls = re.findall(r'https?://\S+', message.content)
    now = datetime.datetime.now(datetime.timezone.utc)

    for url in urls:
        if await is_phishing_link(url):
            embed = discord.Embed(
                title="Message Auto-deleted",
                description=(
                    f"**Message by {message.author.mention} deleted in "
                    f"{message.channel.mention} due to phishing or dangerous "
                    f"link detected**\n\n{message.content}"
                ),
                color=discord.Color.from_str("#99FCFF")
            )
            embed.set_author(
                name=str(message.author),
                icon_url=safe_avatar_url(message.author)
            )
            embed.timestamp = now

            await log_event(LOG_CHANNEL_ID, embed)

            try:
                await message.delete()
            except discord.NotFound:
                print(f"[automod] Message {message.id} already deleted.")

            return True

    return False

