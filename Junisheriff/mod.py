import discord
from discord import app_commands, ui
import datetime
from datetime import timezone
import aiomysql
from zoneinfo import ZoneInfo
import re
import asyncio

# ============================================
# CONFIGURATION
# ============================================

CASE_LOG_CHANNEL_ID = 1322430975480692789
LOCKDOWN_ANNOUNCE_CHANNEL_ID = 1372430570822307890  

GAG_ROLE_ID = 1322686350063042610 

APPEAL_FORM_URL = "https://forms.gle/SzbABy1Jkv2oGpr97"

WARNS_PER_PAGE = 10
WARN_LOG_TIMEZONE = "America/Chicago"  
WARN_LOG_TZ_LABEL = "CST"

EMBED_COLOR_HEX = "#99FCFF"

# Message deletion after ban (Discord API only uses 0-7 days)
BAN_DELETE_DAYS_DEFAULT = 7

# ============================================
# BOT HOOKUP
# ============================================

bot = None


def set_bot(bot_instance):
    global bot
    bot = bot_instance


class Pages(ui.View):
    def __init__(self, embeds):
        super().__init__(timeout=None)
        self.embeds = embeds
        self.current_page = 0
        self.update_buttons()

    def update_buttons(self):
        self.children[0].disabled = self.current_page == 0
        self.children[1].disabled = self.current_page == len(self.embeds) - 1

    @ui.button(label="Previous", style=discord.ButtonStyle.primary)
    async def previous_page(self, interaction: discord.Interaction, button: ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    @ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: ui.Button):
        if self.current_page < len(self.embeds) - 1:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)


class WarnDropdown(ui.View):
    def __init__(self, user, warns):
        super().__init__(timeout=60)
        self.user = user
        self.warns = warns

        options = [
            discord.SelectOption(
                label=f"{entry['reason'][:90]}",
                value=str(entry["id"])
            )
            for entry in warns
        ]

        self.select = ui.Select(
            placeholder="Select a warning to delete",
            min_values=1,
            max_values=1,
            options=options
        )
        self.select.callback = self.on_select
        self.add_item(self.select)

    async def on_select(self, interaction: discord.Interaction):
        warn_id = int(self.select.values[0])
        async with bot.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("DELETE FROM warns WHERE id = %s", (warn_id,))
        await interaction.response.edit_message(
            content=f"Warning deleted for {self.user.name}.", view=None
        )


class AppealButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Appeal Ban", url=APPEAL_FORM_URL))


class ModGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="mod", description="for /srs moderating")


mod_group = ModGroup()


# Parse inputs like 1m, 30d, 2h etc.
def parse_duration(duration_str: str) -> int:
    """Parses a duration string like '1m', '2h', '3d' into total seconds."""
    units = {'d': 86400, 'h': 3600, 'm': 60}
    matches = re.findall(r"(\d+)([dhm])", duration_str.lower())

    if not matches:
        raise ValueError("Invalid duration format. Use '30m', '2h', or 1d.")

    total_seconds = 0
    for value, unit in matches:
        total_seconds += int(value) * units[unit]

    if total_seconds == 0:
        raise ValueError("Duration must be greater than 0.")

    return total_seconds


def safe_avatar_url(user):
    return user.avatar.url if user.avatar else None


# ================= WARNING COMMANDS =================

@mod_group.command(name="warn", description="Warn a user")
async def warn(interaction: discord.Interaction, user: discord.Member, reason: str):
    # Insert warn into DB
    async with bot.pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO warns (guild_id, user_id, mod_name, reason)
                VALUES (%s, %s, %s, %s)
                """,
                (interaction.guild.id, user.id, interaction.user.name, reason),
            )

    now = datetime.datetime.now(datetime.timezone.utc)

    # Acknowledge to moderator
    embed = discord.Embed(
        description=f"{user.mention} has been warned. || Reason: {reason}",
        color=discord.Color.from_str(EMBED_COLOR_HEX)
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

    # Log warn
    logembed = discord.Embed(
        title="User warned",
        color=discord.Color.orange()
    )
    logembed.set_author(name=str(user), icon_url=safe_avatar_url(user))
    logembed.add_field(name="User", value=user.mention)
    logembed.add_field(name="Moderator", value=interaction.user.mention)
    logembed.add_field(name="Reason", value=reason)
    logembed.timestamp = now
    logembed.set_footer(text=f"ID:{user.id}")

    modlog_channel = interaction.guild.get_channel(CASE_LOG_CHANNEL_ID)
    if modlog_channel:
        await modlog_channel.send(embed=logembed)

    # Try to DM about the warn itself
    try:
        dm_embed = discord.Embed(
            description=f"You have been warned in the server After Dark.\n\n**Reason:** {reason}",
            color=discord.Color.red()
        )
        dm_embed.timestamp = now
        await user.send(embed=dm_embed)
    except discord.Forbidden:
        if interaction.response.is_done():
            await interaction.followup.send(f"Unable to DM {user.mention}", ephemeral=True)
        else:
            await interaction.response.send_message(f"Unable to DM {user.mention}", ephemeral=True)

    # Check previous warns (including this one)
    async with bot.pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT COUNT(*)
                FROM warns
                WHERE guild_id = %s AND user_id = %s
                """,
                (interaction.guild.id, user.id),
            )
            row = await cur.fetchone()
            warn_count = row[0] if row else 0

    # Take action based on warn count
    if warn_count == 1:
        # Auto-kick after 1st warn
        try:
            dm_kick = discord.Embed(
                description="You have been automatically kicked from the After Dark server after receiving a warning. You can re-join whenever you'd like, but please make sure to read the rules. Another warning will lead to being muted.",
                color=discord.Color.red(),
            )
            dm_kick.timestamp = now
            await user.send(embed=dm_kick)
        except discord.Forbidden:
            if interaction.response.is_done():
                await interaction.followup.send(
                    f"Unable to DM {user.mention} before kicking them.",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    f"Unable to DM {user.mention} before kicking them.",
                    ephemeral=True,
                )

        try:
            await user.kick(reason=f"Automatically kicked after first warning. Reason: {reason}")
        except discord.Forbidden:
            if interaction.response.is_done():
                await interaction.followup.send(
                    f"Unable to kick {user.mention} (missing permissions or hierarchy).",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    f"Unable to kick {user.mention} (missing permissions or hierarchy).",
                    ephemeral=True,
                )
            return

        kick_log = discord.Embed(
            title="User auto-kicked",
            description=f"{user.mention} has been kicked after receiving their first warning.",
            color=discord.Color.orange(),
        )
        kick_log.set_author(name=str(user), icon_url=safe_avatar_url(user))
        kick_log.add_field(name="Reason", value=reason, inline=False)
        kick_log.timestamp = now
        kick_log.set_footer(text=f"ID:{user.id}")

        if modlog_channel:
            await modlog_channel.send(embed=kick_log)

    elif warn_count == 2:
        # Auto-mute after second warn
        gag_role = interaction.guild.get_role(GAG_ROLE_ID)
        if gag_role:
            await user.add_roles(gag_role, reason="Automute after 2 warnings")

        automute_logembed = discord.Embed(
            title="User automuted",
            description=(
                f"{user.mention} has been automuted after receiving 2 warnings. "
                "They will need to open a ticket in order to be unmuted."
            ),
            color=discord.Color.orange(),
        )
        automute_logembed.set_author(name=str(user), icon_url=safe_avatar_url(user))
        automute_logembed.timestamp = now
        automute_logembed.set_footer(text=f"ID:{user.id}")

        if modlog_channel:
            await modlog_channel.send(embed=automute_logembed)

        try:
            dm_embed = discord.Embed(
                description=(
                    "You have been automuted in the After Dark server after receiving 2 warnings. "
                    "In order for this mute to be lifted, you will need to open a ticket in the server."
                ),
                color=discord.Color.red(),
            )
            dm_embed.timestamp = now
            await user.send(embed=dm_embed)
        except discord.Forbidden:
            if interaction.response.is_done():
                await interaction.followup.send(f"Unable to DM {user.mention}", ephemeral=True)
            else:
                await interaction.response.send_message(f"Unable to DM {user.mention}", ephemeral=True)


@mod_group.command(name="warnings", description="Displays a user's past warns")
async def warn_log(interaction: discord.Interaction, user: discord.Member):
    async with bot.pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                """
                SELECT mod_name, reason, timestamp FROM warns
                WHERE guild_id = %s AND user_id = %s
                ORDER BY timestamp DESC
                """,
                (interaction.guild.id, user.id)
            )
            records = await cur.fetchall()

    if not records:
        await interaction.response.send_message(f"{user.name} has no warns logged.")
        return

    per_page = WARNS_PER_PAGE
    pages = []
    display_tz = ZoneInfo(WARN_LOG_TIMEZONE)

    for i in range(0, len(records), per_page):
        chunk = records[i:i + per_page]
        description = "\n".join(
            f"**Moderator: {entry['mod_name']}**\n"
            f"{entry['reason']} *(<t:{int(entry['timestamp'].replace(tzinfo=timezone.utc).astimezone(display_tz).timestamp())}:f> {WARN_LOG_TZ_LABEL})*\n"
            for entry in chunk
        )

        embed = discord.Embed(
            title=f"{len(records)} warnings for {user}:",
            description=description,
            color=discord.Color.from_str(EMBED_COLOR_HEX)
        )
        embed.set_footer(text=f"Page {i // per_page + 1}/{(len(records) - 1) // per_page + 1}")
        embed.set_author(name=str(user), icon_url=safe_avatar_url(user))
        pages.append(embed)

    view = Pages(pages)
    await interaction.response.send_message(embed=pages[0], view=view)


@mod_group.command(name="clearwarns", description="Clear all warnings for a user")
async def clear_warns(interaction: discord.Interaction, user: discord.Member):
    async with bot.pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM warns WHERE guild_id = %s AND user_id = %s",
                (interaction.guild.id, user.id)
            )

    embed = discord.Embed(
        description=f"Warnings for {user.mention} have been cleared.",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)


@mod_group.command(name="delwarn", description="Delete a specific warning by its index in the user's log")
async def delete_warn(interaction: discord.Interaction, user: discord.Member):
    async with bot.pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                """
                SELECT id, reason, timestamp FROM warns
                WHERE guild_id = %s AND user_id = %s
                ORDER BY timestamp DESC
                """,
                (interaction.guild.id, user.id)
            )
            records = await cur.fetchall()

        if not records:
            await interaction.response.send_message(f"{user.mention} has no warnings.", ephemeral=True)
            return

        view = WarnDropdown(user, records)
        await interaction.response.send_message(
            f"Select a warning to delete for {user.name}",
            view=view
        )


# ================= BANNING COMMANDS =================

@mod_group.command(name="ban", description="Bans a user")
async def ban(
    interaction: discord.Interaction,
    user: discord.Member,
    reason: str,
    appeal: bool = True,
    preserve_messages: bool = True
):
    await interaction.response.defer(ephemeral=True)

    now = datetime.datetime.now(datetime.timezone.utc)

    # Try DM first
    try:
        dm_embed = discord.Embed(
            description=f"You have been banned from the server After Dark.\n\n**Reason:** {reason}",
            color=discord.Color.red(),
            timestamp=now
        )
        if appeal:
            await user.send(embed=dm_embed, view=AppealButton())
        else:
            await user.send(embed=dm_embed)
    except discord.Forbidden:
        await interaction.followup.send(f"Unable to DM {user.mention}. Proceeding with ban.", ephemeral=True)

    # Ban
    delete_days = 0 if preserve_messages else BAN_DELETE_DAYS_DEFAULT
    try:
        await interaction.guild.ban(user, reason=reason, delete_message_days=delete_days)
    except Exception as e:
        return await interaction.followup.send(f"Failed to ban user: {e}", ephemeral=True)

    # Confirm
    embed = discord.Embed(
        description=f"{user.name} has been banned. || Reason: {reason}",
        color=discord.Color.from_str(EMBED_COLOR_HEX)
    )
    await interaction.followup.send(embed=embed, ephemeral=True)

    # Log
    icon = user.avatar.url if user.avatar else None
    logembed = discord.Embed(
        title="User banned",
        color=discord.Color.red(),
        timestamp=now
    )
    logembed.set_author(name=str(user), icon_url=icon)
    logembed.add_field(name="User", value=user.name)
    logembed.add_field(name="Moderator", value=interaction.user.mention)
    logembed.add_field(name="Reason", value=reason)
    logembed.set_footer(text=f"ID:{user.id}")

    modlog_channel = interaction.guild.get_channel(CASE_LOG_CHANNEL_ID)
    if modlog_channel:
        try:
            await modlog_channel.send(embed=logembed)
        except Exception as e:
            print(f"Failed to send log to modlog channel: {e}")
    else:
        print("Modlog channel not found or CASE_LOG_CHANNEL_ID is incorrect.")


@mod_group.command(name="unban", description="Unbans a user by their ID")
async def unban(
    interaction: discord.Interaction,
    user_id: str,
    reason: str
):
    await interaction.response.defer(ephemeral=True)

    # Validate ID
    try:
        target_id = int(user_id)
    except ValueError:
        return await interaction.followup.send(
            "This command uses the user ID to look up users int he ban list. Please provide a valid user ID.",
            ephemeral=True
        )

    guild = interaction.guild
    now = datetime.datetime.now(datetime.timezone.utc)

    # Fetch ban entry (so we can confirm they're actually banned + get user object)
    try:
        ban_entry = await guild.fetch_ban(discord.Object(id=target_id))
    except discord.NotFound:
        return await interaction.followup.send(
            "That user is not currently banned (or the ID is wrong).",
            ephemeral=True
        )
    except discord.Forbidden:
        return await interaction.followup.send(
            "I don't have permission to view bans / unban users. (Need Ban Members permission.)",
            ephemeral=True
        )
    except discord.HTTPException as e:
        return await interaction.followup.send(
            f"Failed to fetch ban info: {e}",
            ephemeral=True
        )

    banned_user = ban_entry.user  # discord.User

    # Unban
    try:
        await guild.unban(banned_user, reason=f"{reason} | Unbanned by {interaction.user} ({interaction.user.id})")
    except discord.Forbidden:
        return await interaction.followup.send(
            "I don't have permission to unban users. (Check role permissions/hierarchy.)",
            ephemeral=True
        )
    except discord.HTTPException as e:
        return await interaction.followup.send(
            f"Failed to unban: {e}",
            ephemeral=True
        )

    # Confirm to moderator
    confirm_embed = discord.Embed(
        description=f"Unbanned {banned_user} (ID: `{banned_user.id}`).\n\nReason: {reason}",
        color=discord.Color.from_str(EMBED_COLOR_HEX),
        timestamp=now
    )
    await interaction.followup.send(embed=confirm_embed, ephemeral=True)

    # Log to modlog
    modlog_channel = guild.get_channel(CASE_LOG_CHANNEL_ID)
    if modlog_channel:
        log_embed = discord.Embed(
            title="User unbanned",
            color=discord.Color.green(),
            timestamp=now
        )
        log_embed.set_author(name=str(banned_user), icon_url=safe_avatar_url(banned_user))
        log_embed.add_field(name="User", value=f"{banned_user} (`{banned_user.id}`)")
        log_embed.add_field(name="Moderator", value=interaction.user.mention)
        log_embed.add_field(name="Reason", value=reason)
        log_embed.set_footer(text=f"ID:{banned_user.id}")

        try:
            await modlog_channel.send(embed=log_embed)
        except Exception as e:
            print(f"Failed to send unban log to modlog channel: {e}")


# ================= KICKING COMMANDS =================

@mod_group.command(name="kick", description="Kicks a user")
async def kick(interaction: discord.Interaction, user: discord.Member, reason: str):
    now = datetime.datetime.now(datetime.timezone.utc)

    try:
        dm_embed = discord.Embed(
            description=f"You have been kicked from the server After Dark.\n\n**Reason:** {reason}",
            color=discord.Color.orange(),
            timestamp=now
        )
        await user.send(embed=dm_embed)
    except discord.Forbidden:
        if interaction.response.is_done():
            await interaction.followup.send(f"Unable to DM {user.mention}", ephemeral=True)
        else:
            await interaction.response.send_message(f"Unable to DM {user.mention}", ephemeral=True)

    await interaction.guild.kick(user, reason=reason)

    embed = discord.Embed(
        description=f"{user.mention} has been kicked. || Reason: {reason}",
        color=discord.Color.from_str(EMBED_COLOR_HEX)
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

    logembed = discord.Embed(title="User kicked", color=discord.Color.orange(), timestamp=now)
    logembed.set_author(name=str(user), icon_url=safe_avatar_url(user))
    logembed.add_field(name="User", value=user.mention)
    logembed.add_field(name="Moderator", value=interaction.user.mention)
    logembed.add_field(name="Reason", value=reason)
    logembed.set_footer(text=f"ID:{user.id}")

    modlog_channel = interaction.guild.get_channel(CASE_LOG_CHANNEL_ID)
    if modlog_channel:
        await modlog_channel.send(embed=logembed)


# ================= MUTING COMMANDS =================

@mod_group.command(name="mute", description="Adds the gag role to the user (/srs modding only)")
async def mute(interaction: discord.Interaction, user: discord.Member, reason: str, duration: str = None):
    gag_role = interaction.guild.get_role(GAG_ROLE_ID)
    now = datetime.datetime.now(datetime.timezone.utc)

    duration_text = f" || Duration: {duration}" if duration else " || Please open a ticket in After Dark to be unmuted."

    try:
        dm_embed = discord.Embed(
            description=f"You have been muted in the server After Dark.\n\n**Reason:** {reason}{duration_text}",
            color=discord.Color.orange(),
            timestamp=now
        )
        await user.send(embed=dm_embed)
    except discord.Forbidden:
        if interaction.response.is_done():
            await interaction.followup.send(f"Unable to DM {user.mention}", ephemeral=True)
        else:
            await interaction.response.send_message(f"Unable to DM {user.mention}", ephemeral=True)

    try:
        await user.add_roles(gag_role)
    except discord.Forbidden:
        await interaction.response.send_message(
            "I don't have permission to assign that role (check role hierarchy or permissions).",
            ephemeral=True
        )
        return
    except discord.HTTPException as e:
        await interaction.response.send_message(f"Failed to assign role: {e}", ephemeral=True)
        return

    embed = discord.Embed(
        description=f"{user.mention} has been muted. || Reason: {reason}",
        color=discord.Color.from_str(EMBED_COLOR_HEX)
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

    logembed = discord.Embed(title="User muted", color=discord.Color.orange(), timestamp=now)
    logembed.set_author(name=str(user), icon_url=safe_avatar_url(user))
    logembed.add_field(name="User", value=user.mention)
    logembed.add_field(name="Moderator", value=interaction.user.mention)
    logembed.add_field(name="Reason", value=reason)
    logembed.set_footer(text=f"ID:{user.id}")

    modlog_channel = interaction.guild.get_channel(CASE_LOG_CHANNEL_ID)
    if modlog_channel:
        await modlog_channel.send(embed=logembed)

    if not duration:
        return

    try:
        sleep_seconds = parse_duration(duration)
        await asyncio.sleep(sleep_seconds)
        await user.remove_roles(gag_role)
    except ValueError as e:
        await interaction.followup.send(str(e), ephemeral=True)


@mod_group.command(name="unmute", description="Removes the gag role from a user")
async def unmute(interaction: discord.Interaction, user: discord.Member):
    gag_role = interaction.guild.get_role(GAG_ROLE_ID)
    now = datetime.datetime.now(datetime.timezone.utc)

    if gag_role in user.roles:
        await user.remove_roles(gag_role)

        embed = discord.Embed(
            description=f"{user.mention} has been unmuted.",
            color=discord.Color.from_str(EMBED_COLOR_HEX)
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

        logembed = discord.Embed(title="User unmuted", color=discord.Color.green(), timestamp=now)
        logembed.set_author(name=str(user), icon_url=safe_avatar_url(user))
        logembed.add_field(name="User", value=user.mention)
        logembed.add_field(name="Moderator", value=interaction.user.mention)
        logembed.set_footer(text=f"ID:{user.id}")

        modlog_channel = interaction.guild.get_channel(CASE_LOG_CHANNEL_ID)
        if modlog_channel:
            await modlog_channel.send(embed=logembed)

        try:
            dm_embed = discord.Embed(
                description=(
                    "You have been unmuted in the server After Dark.\n"
                    "Please review the server rules; note that the next moderation action will be a 30 day ban from the server."
                ),
                color=discord.Color.green(),
                timestamp=now
            )
            await user.send(embed=dm_embed)
        except discord.Forbidden:
            if interaction.response.is_done():
                await interaction.followup.send(f"Unable to DM {user.mention}", ephemeral=True)
            else:
                await interaction.response.send_message(f"Unable to DM {user.mention}", ephemeral=True)
    else:
        embed = discord.Embed(
            description=f"{user.mention} is not currently muted.",
            color=discord.Color.from_str(EMBED_COLOR_HEX)
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ================= LOCKDOWN COMMANDS =================

@mod_group.command(name="lockdown_channel", description="Locks the current channel for all users")
async def lockdown_channel(interaction: discord.Interaction, reason: str = "No reason provided"):
    guild = interaction.guild
    channel = interaction.channel
    everyone_role = guild.default_role

    try:
        await channel.set_permissions(everyone_role, send_messages=False, reason=reason)

        embed = discord.Embed(
            title="Channel Locked",
            description=f"{channel.mention} has been locked down",
            color=discord.Color.from_str(EMBED_COLOR_HEX)
        )
        await interaction.response.send_message(embed=embed)
        await channel.send(embed=embed)

        log_embed = discord.Embed(
            title="Channel Lockdown",
            description=f"{channel.mention} locked.",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        log_embed.add_field(name="Moderator", value=interaction.user.mention)
        log_embed.add_field(name="Reason", value=reason)
        log_embed.set_footer(text=f"ID:{user.id}")

        modlog_channel = guild.get_channel(CASE_LOG_CHANNEL_ID)
        if modlog_channel:
            await modlog_channel.send(embed=log_embed)

    except discord.Forbidden:
        await interaction.response.send_message("I don’t have permission to change channel permissions.", ephemeral=True)


@mod_group.command(name="lockdown_server", description="Locks down all channels in the server, except the mod channels")
async def lockdown_server(interaction: discord.Interaction, reason: str = "No reason provided"):
    await interaction.response.defer()

    guild = interaction.guild
    now = datetime.datetime.now(datetime.timezone.utc)
    everyone_role = guild.default_role

    new_permissions = everyone_role.permissions
    new_permissions.update(
        send_messages=False,
        send_messages_in_threads=False,
        create_private_threads=False,
        create_public_threads=False
    )

    try:
        await everyone_role.edit(permissions=new_permissions)
    except discord.Forbidden:
        return await interaction.followup.send("I don't have permission to edit the default role.", ephemeral=True)

    embed = discord.Embed(
        title="Server Locked",
        description="Server has been locked down. Mods can still talk in mod channels.",
        color=discord.Color.from_str(EMBED_COLOR_HEX)
    )
    await interaction.followup.send(embed=embed)

    announce_channel = guild.get_channel(LOCKDOWN_ANNOUNCE_CHANNEL_ID)
    if announce_channel:
        general_embed = discord.Embed(
            title="Server Locked",
            description="The server has been locked down. Once the mod team has handled the situation, it will be reopened.",
            color=discord.Color.from_str(EMBED_COLOR_HEX)
        )
        await announce_channel.send(embed=general_embed)

    log_embed = discord.Embed(
        title="Server Lockdown",
        description="The server has been locked down.",
        color=discord.Color.red(),
        timestamp=now
    )
    log_embed.add_field(name="Moderator", value=interaction.user.mention)
    log_embed.add_field(name="Reason", value=reason)
    log_embed.set_footer(text=f"ID:{user.id}")

    modlog_channel = guild.get_channel(CASE_LOG_CHANNEL_ID)
    if modlog_channel:
        await modlog_channel.send(embed=log_embed)







