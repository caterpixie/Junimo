import discord
import datetime
from datetime import datetime, timezone

STARBOARD_CHANNEL_ID = 1378101526022848522
STAR_THRESHOLD = 1
bot = None

starred_messages = {}

def set_bot(bot_instance):
    global bot
    bot = bot_instance

def setup_starboard(bot_instance: discord.Client):
    set_bot(bot_instance)

    @bot_instance.event
    async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):

        
        if str(payload.emoji) != "⭐":
            return

        channel = bot.get_channel(payload.channel_id)
        if not channel:
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return

        # Count stars
        count = 0
        for reaction in message.reactions:
            if str(reaction.emoji) == "⭐":
                count = reaction.count

        if count < STAR_THRESHOLD:
            return

        starboard = bot.get_channel(STARBOARD_CHANNEL_ID)
        if not starboard:
            return

        now = datetime.now(timezone.utc)
        timestamp = int(message.created_at.timestamp())

        embed = discord.Embed(
            description=message.content or "[No text]",
            color=discord.Color.from_str("#A0EA67")
        )
        embed.set_author(name=str(message.author), icon_url=message.author.display_avatar.url)
        embed.add_field(name="Jump to Message", value=f"[Click here]({message.jump_url})")
        embed.timestamp = now

        if message.attachments:
            embed.set_image(url=message.attachments[0].url)

        if message.id in starred_messages:
            try:
                old_msg = await starboard.fetch_message(starred_messages[message.id])
                await old_msg.edit(content=f"⭐ {count}", embed=embed)
            except discord.NotFound:
                del starred_messages[message.id]
        else:
            starboard_msg = await starboard.send(content=f"⭐ {count}", embed=embed)
            starred_messages[message.id] = starboard_msg.id
