import discord
import datetime
from datetime import datetime, timezone

bot = None
LOG_CHANNEL=1322430928555085824
MESSAGE_LOG_CHANNEL=1322430962981801984
USER_LOG_CHANNEL=1322430941993373850

def set_bot(bot_instance):
    global bot
    bot = bot_instance

def setup_logging(bot_instance: discord.Client):
    set_bot(bot_instance)

    @bot_instance.event
    async def on_member_join(user: discord.Member):
        await log_member_join(user)
    
    @bot_instance.event
    async def on_member_remove(user: discord.Member):
        await log_member_remove(user)

    @bot_instance.event
    async def on_message_delete(user: discord.Member):
        await log_message_delete(user)
    
    @bot_instance.event
    async def on_message_edit(before: discord.Message, after: discord.Message):
        await log_message_edit(before, after)

    @bot_instance.event
    async def on_member_update(before: discord.Member, after: discord.Member):
        await log_member_update(before, after)

    @bot_instance.event
    async def on_voice_state_update(user: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        await log_voice_state_update(user, before, after)

async def log_event(channel_id: int, embed: discord.Embed):
    channel = bot.get_channel(channel_id)
    if channel:
        await channel.send(embed=embed)




# ARRIVAL/DEPARTURE LOGS

async def log_member_join(user: discord.Member):
    now = datetime.now(timezone.utc)
    timestamp = int(user.created_at.timestamp())

    embed = discord.Embed(
        title="User Joined",
        color=discord.Color.green()
    )
    embed.set_thumbnail(url=user.avatar.url if user.avatar else None)
    embed.set_author(name=str(user), icon_url=user.avatar.url)
    embed.add_field(
        name="User",
        value=f"{user.mention}"
    )
    embed.add_field(
        name="Account Created",
        value=f"<t:{timestamp}:R>",
        inline=False
    )
    embed.set_footer(text=f"ID: {user.id}")
    embed.timestamp = now

    await log_event(LOG_CHANNEL, embed)

async def log_member_remove(user: discord.Member):
    now = datetime.now(timezone.utc)

    embed = discord.Embed(
        title="User Left",
        color=discord.Color.red()
    )
    embed.set_thumbnail(url=user.avatar.url if user.avatar else None)
    embed.set_author(name=str(user), icon_url=user.avatar.url)
    embed.set_footer(text=f"ID: {user.id}")
    embed.timestamp = now

    await log_event(LOG_CHANNEL, embed)




# MESSAGE LOGS

async def log_message_delete(message: discord.Message):
    now = datetime.now(timezone.utc)
    
    if message.author.bot:
        return
    embed = discord.Embed(
        description=f"**Message by {message.author.mention} deleted in {message.channel.mention}**\n{message.content}",
        color=discord.Color.red()
    )
    embed.set_author(name=str(message.author), icon_url=message.author.avatar.url)
    embed.timestamp = now

    # Log deleted images
    if message.attachments:
        image_url = [attachment.url for attachment in message.attachments if attachment.content_type and "image" in attachment.content_type]
        if image_url:
            embed.add_field(name="Image(s)", value="\n".join(image_url), inline=False)
            embed.set_image(url=image_url[0])
    await log_event(MESSAGE_LOG_CHANNEL, embed)

async def log_message_edit(before: discord.Message, after: discord.Message):
    now = datetime.now(timezone.utc)
    jump_url = f"https://discord.com/channels/{before.guild.id}/{before.channel.id}/{before.id}"

    if before.author.bot:
        return 
    if before.guild is None:
        return 
    if before.content == after.content:
        return 

    embed = discord.Embed(
        description=f"**Message by {before.author.mention} edited in {before.channel.mention}**\n[Jump to message]({jump_url})",
        color=discord.Color.orange()
    )
    embed.set_author(name=str(before.author), icon_url=before.author.avatar.url)
    embed.add_field(
        name="Before",
        value=f"{before.content}"
    )
    embed.add_field(
        name="After",
        value=f"{after.content}",
        inline=False
    )
    embed.timestamp = now

    await log_event(MESSAGE_LOG_CHANNEL, embed)




# USER LOGS

async def log_member_update(before: discord.Member, after: discord.Member):
    if before.bot:
        return
    
    now = datetime.now(timezone.utc)
    changes = []

    # Nickname change
    if before.nick != after.nick:
        changes.append(f"Nickname: `{before.nick}` → `{after.nick}`")

    # Role add/remove
    before_roles = set(before.roles)
    after_roles = set(after.roles)
    
    added_roles = after_roles - before_roles
    removed_roles = before_roles - after_roles

    if added_roles:
        changes.append(f"Roles Added: {', '.join(role.mention for role in added_roles)}")
    if removed_roles:
        changes.append(f"Roles Removed {', '.join(role.mention for role in removed_roles)}")

    if not changes:
        return
    
    embed = discord.Embed(
        title="User Updated",
        color=discord.Color.from_str("#7CE4FF")
    )
    embed.set_author(name=str(before), icon_url=before.avatar.url)
    embed.add_field(name="User", value=f"{before.mention} (`{before.id}`)")
    embed.add_field(name="Changes", value="\n".join(changes), inline=False)
    embed.timestamp = now

    await log_event(USER_LOG_CHANNEL, embed)

async def log_voice_state_update(user: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    if user.bot:
        return

    now = datetime.now(timezone.utc)

    if before.channel != after.channel:
        if before.channel and not after.channel:
            embed = discord.Embed(
                description=f"{user.mention} left voice channel {before.channel.mention}",
                color=discord.Color.red()
            )
            embed.timestamp = now
            embed.set_author(name=str(user), icon_url=user.avatar.url)

        elif after.channel and not before.channel:
            embed = discord.Embed(
                description=f"{user.mention} joined voice channel {after.channel.mention}",
                color=discord.Color.green()
            )
            embed.timestamp = now
            embed.set_author(name=str(user), icon_url=user.avatar.url)

        elif before.channel and after.channel:
            embed = discord.Embed(
                description=f"{user.mention} moved from voice channel {before.channel.mention} to {after.channel.mention}",
                color=discord.Color.green()
            )
            embed.timestamp = now
            embed.set_author(name=str(user), icon_url=user.avatar.url)

    await log_event(USER_LOG_CHANNEL, embed)
