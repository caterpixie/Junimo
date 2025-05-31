import discord
import re
import datetime
from safebrowsing import is_phishing_link

def set_bot(bot_instance):
    global bot
    bot = bot_instance

def setup_automod(bot_instance: discord.Client):
    set_bot(bot_instance)

    @bot_instance.event
    async def on_message(message: discord.Message):
        if message.guild is None or message.author.bot:
            return
        if message.guild.id != SERVER:
            return

        if await check_phishing(message):
            return
        if await check_no_links_in_general(message):
            return
        if await check_slurs(message):
            return
        
        await bot.process_commands(message)


def load_slurs(filename="slurs.txt"):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return [line.strip().lower() for line in f if line.strip() and not line.startswith("#")]
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
        
async def check_no_links_in_general(message):
    if message.channel.id == GENERAL_CHANNEL and "http" in message.content:
        try:
            await message.delete()
        except discord.NotFound:
            pass
    
        return True
    return False

async def check_slurs(message):
    content = message.content.lower()
    now = datetime.datetime.now(datetime.timezone.utc)

    for slur in load_slurs():  # Dynamically reload the list
        if is_slur_in_text(content, slur):
            embed = discord.Embed(
                title="Message Auto-deleted",
                description=f"**Message by {message.author.mention} deleted in {message.channel.mention} due to bad word detected**\n\n{message.content}",
                color=discord.Color.from_str("#7CE4FF")
            )
            embed.set_author(name=str(message.author), icon_url=safe_avatar_url(message.author))
            embed.timestamp = now

            await log_event(LOG_CHANNEL, embed)
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
                description=f"**Message by {message.author.mention} deleted in {message.channel.mention} due to phishing or dangerous link detected**\n\n{message.content}",
                color=discord.Color.from_str("#7CE4FF")
            )
            embed.set_author(name=str(message.author), icon_url=safe_avatar_url(message.author))
            embed.timestamp = now

            await log_event(LOG_CHANNEL, embed)

            try:
                await message.delete()
            except discord.NotFound:
                print(f"[automod] Message {message.id} already deleted.")

            return True

    return False

    
SERVER=1322072874214756375
GENERAL_CHANNEL=1378137773478772797
LOG_CHANNEL=1378137722958647419

