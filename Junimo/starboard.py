import discord

STARBOARD_CHANNEL_ID = 1378101526022848522
STAR_THRESHOLD = 1
bot = None

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

    message = await channel.fetch_message(payload.message_id)

    count = 0
    for reaction in message.reactions:
        if str(reaction.emoji) == "⭐":
          count = reaction.count

    if count >= STAR_THRESHOLD:
      starboard = bot.get_channel(STARBOARD_CHANNEL_ID)
      if not starboard:
        return

      embed = discord.Embed(
          description=message.content,
          color=discord.Color.gold()
      )
      embed.set_author(name=str(message.author), icon_url=message.author.display_avatar.url)
      embed.add_field(name="Jump to Message", value=f"[Click here]({message.jump_url})")
      if message.attachments:
          embed.set_image(url=message.attachments[0].url)
      await starboard.send(embed=embed)
