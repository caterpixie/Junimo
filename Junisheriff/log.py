import discord
import datetime
from datetime import datetime, timezone

bot = None

AD_SERVER=1322423728457384018

LOG_CHANNEL=1322430928555085824
MESSAGE_LOG_CHANNEL=1322430962981801984
USER_LOG_CHANNEL=1322430941993373850
OFFICIAL_MOD_CHANNEL=1348402476759515276

SKYLAR_ID = 772218973080518676
SCRIPTURE_CHANNEL = 1323794218539548682

MINOR_ROLE = 1364393285900042251

def set_bot(bot_instance):
    global bot
    bot = bot_instance

def setup_logging(bot_instance: discord.Client):
    set_bot(bot_instance)

    @bot_instance.event
    async def on_member_join(user: discord.Member):
        if user.guild.id != AD_SERVER:
            return
        await log_member_join(user)
    
    @bot_instance.event
    async def on_member_remove(user: discord.Member):
        if user.guild.id != AD_SERVER:
            return
        await log_member_remove(user)

    @bot_instance.event
    async def on_message_delete(user: discord.Member):
        if user.guild is None or user.guild.id != AD_SERVER:
            return
        await log_message_delete(user)
    
    @bot_instance.event
    async def on_message_edit(before: discord.Message, after: discord.Message):
        if before.guild is None or before.guild.id != AD_SERVER:
            return
        await log_message_edit(before, after)

    @bot_instance.event
    async def on_member_update(before: discord.Member, after: discord.Member):
        if before.guild.id != AD_SERVER:
            return
        await log_member_update(before, after)

    @bot_instance.event
    async def on_voice_state_update(user: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if user.guild.id != AD_SERVER:
            return
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
    icon_url = user.avatar.url if user.avatar else user.default_avatar.url
    
    embed.set_author(name=str(user), icon_url=icon_url)
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
    roles = [role.mention for role in user.roles if role.name != "@everyone"]
    role_text = ", ".join(roles) if roles else "No roles"

    embed = discord.Embed(
        title="User Left",
        description=f"**Roles:** {role_text}",
        color=discord.Color.red()
    )
    embed.set_thumbnail(url=user.avatar.url if user.avatar else None)
    icon_url = user.avatar.url if user.avatar else user.default_avatar.url
    
    embed.set_author(name=str(user), icon_url=icon_url)
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

    if message.author.id == SKYLAR_ID:
        await message.channel.send(embed=embed)
        
        scripture = bot.get_channel(SCRIPTURE_CHANNEL)
        if scripture:
            await scripture.send(embed=embed)

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
        description=f"**Message by {before.author.mention} edited in {before.channel.mention}**\n[Jump to message]({jump_url})\n\n**Before:**\n{before.content}\n\n**After:**\n{after.content}",
        color=discord.Color.orange()
    )
    icon_url = before.author.avatar.url if before.author.avatar else user.default_avatar.url
    embed.set_author(name=str(before.author), icon_url=icon_url)
    embed.timestamp = now

    await log_event(MESSAGE_LOG_CHANNEL, embed)

            





# USER LOGS

async def log_member_update(before: discord.Member, after: discord.Member):
    if before.bot:
        return
    
    now = datetime.now(timezone.utc)
    changes = []
    minor = False

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
        if any(role.id == MINOR_ROLE for role in added_roles):
            minor = True
    if removed_roles:
        changes.append(f"Roles Removed {', '.join(role.mention for role in removed_roles)}")

    if not changes:
        return
    
    embed = discord.Embed(
        title="User Updated",
        color=discord.Color.from_str("#FDB574")
    )
    icon_url = before.avatar.url if before.avatar else before.default_avatar.url
    embed.set_author(name=str(before), icon_url=icon_url)
    embed.add_field(name="User", value=f"{before.mention} (`{before.id}`)")
    embed.add_field(name="Changes", value="\n".join(changes), inline=False)
    embed.timestamp = now

    await log_event(USER_LOG_CHANNEL, embed)

    if minor:
        minor_embed = discord.Embed(
            title = "Stinky Minor Alert",
            description = f"User {before.mention} has selected the -17 role. SIC 'EM",
            color=discord.Color.red(),
        )
        await log_event(OFFICIAL_MOD_CHANNEL, minor_embed)
    
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
            await log_event(USER_LOG_CHANNEL, embed)


        elif after.channel and not before.channel:
            embed = discord.Embed(
                description=f"{user.mention} joined voice channel {after.channel.mention}",
                color=discord.Color.green()
            )
            embed.timestamp = now
            embed.set_author(name=str(user), icon_url=user.avatar.url)
            await log_event(USER_LOG_CHANNEL, embed)


        elif before.channel and after.channel:
            embed = discord.Embed(
                description=f"{user.mention} moved from voice channel {before.channel.mention} to {after.channel.mention}",
                color=discord.Color.green()
            )
            embed.timestamp = now
            icon_url = user.avatar.url if user.avatar else user.default_avatar.url
    
            embed.set_author(name=str(user), icon_url=icon_url)
            await log_event(USER_LOG_CHANNEL, embed)


    
