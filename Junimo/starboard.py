import discord
from datetime import datetime, timezone

# =========================
# CONFIGURATION
# =========================

STARBOARD_CHANNEL_ID = 1323794218539548682
EXCLUDED_CHANNEL_IDS = [
    1348402616249487360,
    1322427028053561408,
    1348402476759515276,
    1322669947998048410,
    1322430843859370004,
    1322430860066295818,
    1341310543188721664,
    1322430599679447131,
]

STAR_EMOJI = "🍅"
STAR_THRESHOLD = 3

EMBED_COLOR = "#9CEC61"

# =========================
# BOT HOOKUP
# =========================
bot = None
starred_messages = {}


def set_bot(bot_instance):
    global bot
    bot = bot_instance


def setup_starboard(bot_instance: discord.Client):
    set_bot(bot_instance)

    @bot_instance.event
    async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):

        if str(payload.emoji) != STAR_EMOJI:
            return

        if payload.channel_id in EXCLUDED_CHANNEL_IDS:
            return

        channel = bot.get_channel(payload.channel_id)
        if not channel:
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return

        # Count star reactions
        count = 0
        for reaction in message.reactions:
            if str(reaction.emoji) == STAR_EMOJI:
                count = reaction.count

        if count < STAR_THRESHOLD:
            return

        starboard = bot.get_channel(STARBOARD_CHANNEL_ID)
        if not starboard:
            return

        embed = discord.Embed(
            description=f"{message.content}\n\n[Jump to Message!]({message.jump_url})" or "[No text]",
            color=discord.Color.from_str(EMBED_COLOR),
        )
        embed.set_author(
            name=str(message.author),
            icon_url=message.author.display_avatar.url,
        )
        embed.timestamp = datetime.now(timezone.utc)

        if message.attachments:
            embed.set_image(url=message.attachments[0].url)

        if message.id in starred_messages:
            try:
                old_msg = await starboard.fetch_message(starred_messages[message.id])
                await old_msg.edit(content=f"{STAR_EMOJI} {count}", embed=embed)
            except discord.NotFound:
                del starred_messages[message.id]
        else:
            starboard_msg = await starboard.send(content=f"{STAR_EMOJI} {count}", embed=embed)
            starred_messages[message.id] = starboard_msg.id
