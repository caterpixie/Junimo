import discord
import discord.ext
from discord import app_commands, ui
import datetime
from datetime import timezone
import aiomysql
from zoneinfo import ZoneInfo
import re
import asyncio

bot = None
CASE_LOG_CHANNEL=1322430975480692789

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
        self.add_item(discord.ui.Button(label="Appeal Ban", url="https://forms.gle/SzbABy1Jkv2oGpr97"))
    
        
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




## WARNING COMMANDS

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
        color=discord.Color.from_str("#99FCFF")
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

    modlog_channel = interaction.guild.get_channel(CASE_LOG_CHANNEL)
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
        # Auto-kick after 1st warn: DM -> kick -> log
        try:
            dm_kick = discord.Embed(
                description=("You have been automatically kicked from the After Dark server after receiving a warning."),
                color=discord.Color.red(),
            )
            dm_kick.timestamp = now
            await user.send(embed=dm_kick)
            
        except discord.Forbidden:
            # Can't DM them; just let the mod know
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

        # Kick the user
        try:
            await user.kick(
                reason=f"Automatically kicked after first warning. Reason: {reason}"
            )
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
            return  # stop if kick failed

        # Log the kick
        kick_log = discord.Embed(
            title="User auto-kicked",
            description=f"{user.mention} has been kicked after receiving their first warning.",
            color=discord.Color.orange(),
        )
        kick_log.set_author(name=str(user), icon_url=safe_avatar_url(user))
        kick_log.add_field(name="Reason", value=reason, inline=False)
        kick_log.timestamp = now

        if modlog_channel:
            await modlog_channel.send(embed=kick_log)

    elif warn_count == 2:
        # Automatically mute after second warn
        gag = interaction.guild.get_role(1322686350063042610)
        if gag:
            await user.add_roles(gag, reason="Automute after 2 warnings")

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
            await cur.execute("""
                SELECT mod_name, reason, timestamp FROM warns
                WHERE guild_id = %s AND user_id = %s
                ORDER BY timestamp DESC
            """, (interaction.guild.id, user.id))
            records = await cur.fetchall()
    
    if not records:
        await interaction.response.send_message(f"{user.name} has no warns logged.")
        return

    per_page = 10
    pages = []
    for i in range(0, len(records), per_page):
        chunk = records[i:i+per_page]
        cst = ZoneInfo("America/Chicago")
        description = "\n".join(
            f"**Moderator: {entry['mod_name']}**\n{entry['reason']} *(<t:{int(entry['timestamp'].replace(tzinfo=timezone.utc).astimezone(cst).timestamp())}:f> CST)*\n"
            for idx, entry in enumerate(chunk, start=i+1))
        embed = discord.Embed(
            title=f"{len(records)} warnings for {user}:", 
            description=description, 
            color=discord.Color.from_str("#99FCFF")
        )
        embed.set_footer(text=f"Page {i//per_page + 1}/{(len(records)-1)//per_page + 1}")
        embed.set_author(name=str(user), icon_url=safe_avatar_url(user))
        pages.append(embed)

    view = Pages(pages)
    await interaction.response.send_message(embed=pages[0], view=view)

@mod_group.command(name="clearwarns", description="Clear all warnings for a user")
async def clear_warns(interaction: discord.Interaction, user: discord.Member):
    async with bot.pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                DELETE FROM warns WHERE guild_id = %s AND user_id = %s
            """, (interaction.guild.id, user.id))

    embed = discord.Embed(
        description=f"Warnings for {user.mention} have been cleared.",
        color=discord.Color.green()
    )

    await interaction.response.send_message(embed=embed)

@mod_group.command(name="delwarn", description="Delete a specific warning by its index in the user's log")
async def delete_warn(interaction: discord.Interaction, user: discord.Member):
    async with bot.pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("""
                SELECT id, reason, timestamp FROM warns
                WHERE guild_id = %s AND user_id = %s
                ORDER BY timestamp DESC
            """, (interaction.guild.id, user.id))
            records = await cur.fetchall()

        if not records:
            await interaction.response.send_message(f"{user.mention} has no warnings.", ephemeral=True)
            return

        view = WarnDropdown(user, records)
        await interaction.response.send_message(
            f"Select a warning to delete for {user.name}", view=view
        )




## BANNING COMMANDS

@mod_group.command(name="ban", description="Bans a user")
async def ban(
    interaction: discord.Interaction,
    user: discord.Member,
    reason: str,
    appeal: bool = False,
    preserve_messages: bool = False
):
    await interaction.response.defer(ephemeral=True)

    now = datetime.datetime.now(datetime.timezone.utc)

    # --- Try to DM the user first ---
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

    # --- Attempt to ban the user ---
    try:
        await interaction.guild.ban(
            user,
            reason=reason,
            delete_message_days=0 if preserve_messages else 7
        )
    except Exception as e:
        return await interaction.followup.send(f"Failed to ban user: {e}", ephemeral=True)

    # --- Confirmation to moderator ---
    embed = discord.Embed(
        description=f"{user.name} has been banned. || Reason: {reason}",
        color=discord.Color.from_str("#99FCFF")
    )
    await interaction.followup.send(embed=embed, ephemeral=True)

    # --- Log embed ---
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

    # --- Send to mod log channel ---
    modlog_channel = interaction.guild.get_channel(CASE_LOG_CHANNEL)
    if modlog_channel:
        try:
            await modlog_channel.send(embed=logembed)
        except Exception as e:
            print(f"Failed to send log to modlog channel: {e}")
    else:
        print("Modlog channel not found or CASE_LOG_CHANNEL ID is incorrect.")

## KICKING COMMANDS

@mod_group.command(name="kick", description="Kicks a user")
async def kick(interaction: discord.Interaction, user: discord.Member, reason: str):
    now = datetime.datetime.now(datetime.timezone.utc)

    try:
        dm_embed = discord.Embed(
            description=f"You have been kicked from the server After Dark.\n\n**Reason:** {reason}",
            color=discord.Color.orange()
        )
        dm_embed.timestamp = now
    
        await user.send(embed=dm_embed)
    except discord.Forbidden:
        if interaction.response.is_done():
            await interaction.followup.send(f"Unable to DM {user.mention}", ephemeral=True)
        else:
            await interaction.response.send_message(f"Unable to DM {user.mention}", ephemeral=True)
    await interaction.guild.kick(user, reason=reason)

    embed = discord.Embed(
        description=f"{user.mention} has been kicked. || Reason: {reason}",
        color=discord.Color.from_str("#99FCFF")
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

    logembed = discord.Embed(
        title=f"User kicked",
        color=discord.Color.orange()
    )
    logembed.set_author(name=str(user), icon_url=safe_avatar_url(user))
    logembed.add_field(name="User", value=f"{user.mention}")
    logembed.add_field(name="Moderator", value=f"{interaction.user.mention}")
    logembed.add_field(name="Reason", value=f"{reason}")
    logembed.timestamp = now

    # Log to modlog
    modlog_channel = interaction.guild.get_channel(CASE_LOG_CHANNEL)
    if modlog_channel:
        await modlog_channel.send(embed=logembed)




## MUTING COMMANDS

@mod_group.command(name="mute", description="Adds the gag role to the user (/srs modding only)")
async def mute(interaction: discord.Interaction, user: discord.Member, reason: str, duration: str=None):
    gag = interaction.guild.get_role(1322686350063042610)
    now = datetime.datetime.now(datetime.timezone.utc)

    duration_text = f" || Duration: {duration}" if reason else "|| Please open a ticket in After Dark to be unmuted."

    try:
        dm_embed = discord.Embed(
            description=f"You have been muted in the server After Dark.\n\n**Reason:** {reason}{duration_text}",
            color=discord.Color.orange()
        )
        dm_embed.timestamp = now
    
        await user.send(embed=dm_embed)
    except discord.Forbidden:
        if interaction.response.is_done():
            await interaction.followup.send(f"Unable to DM {user.mention}", ephemeral=True)
        else:
            await interaction.response.send_message(f"Unable to DM {user.mention}", ephemeral=True)

    try:
        await user.add_roles(gag)
    except discord.Forbidden:
        await interaction.response.send_message("I don't have permission to assign that role (check role hierarchy or permissions).", ephemeral=True)
        return
    except discord.HTTPException as e:
        await interaction.response.send_message(f"Failed to assign role: {e}", ephemeral=True)
        return
    
    embed = discord.Embed(
        description=f"{user.mention} has been muted. || Reason: {reason}",
        color=discord.Color.from_str("#99FCFF")
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

    logembed = discord.Embed(
        title=f"User muted",
        color=discord.Color.orange()
    )
    logembed.set_author(name=str(user), icon_url=safe_avatar_url(user))
    logembed.add_field(name="User", value=f"{user.mention}")
    logembed.add_field(name="Moderator", value=f"{interaction.user.mention}")
    logembed.add_field(name="Reason", value=f"{reason}")
    logembed.timestamp = now

    # Log to modlog
    modlog_channel = interaction.guild.get_channel(CASE_LOG_CHANNEL)
    if modlog_channel:
        await modlog_channel.send(embed=logembed)

    if not duration:
        return
    else:
        try:
            sleep_seconds = parse_duration(duration)
            await asyncio.sleep(sleep_seconds)
            await user.remove_roles(gag)
        except ValueError as e:
            await interaction.followup.send(str(e), ephemeral=True)

@mod_group.command(name="unmute", description="Removes the gag rule form a user")
async def unmute(interaction: discord.Interaction, user: discord.Member):
    gag = interaction.guild.get_role(1322686350063042610)
    now = datetime.datetime.now(datetime.timezone.utc)

    if gag in user.roles:
        await user.remove_roles(gag)
    
        embed = discord.Embed(
            description=f"{user.mention} has been unmuted.",
            color=discord.Color.from_str("#99FCFF")
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

        logembed = discord.Embed(
            title=f"User unmuted",
            color=discord.Color.green()
        )
        logembed.set_author(name=str(user), icon_url=safe_avatar_url(user))
        logembed.add_field(name="User", value=f"{user.mention}")
        logembed.add_field(name="Moderator", value=f"{interaction.user.mention}")
        logembed.timestamp = now

        # Log to modlog
        modlog_channel = interaction.guild.get_channel(CASE_LOG_CHANNEL)
        if modlog_channel:
            await modlog_channel.send(embed=logembed)

        # DM user
        try:
            dm_embed = discord.Embed(
                description=f"You have been unmuted in the server After Dark.\nPlease review the server rules; note that the next moderation action will be a 30 day ban from the server.",
                color=discord.Color.green()
            )
            dm_embed.timestamp = now
        
            await user.send(embed=dm_embed)
        except discord.Forbidden:
            if interaction.response.is_done():
                await interaction.followup.send(f"Unable to DM {user.mention}", ephemeral=True)
            else:
                await interaction.response.send_message(f"Unable to DM {user.mention}", ephemeral=True)
    else:
        embed = discord.Embed(
            description=f"{user.mention} is not currently muted.",
            color=discord.Color.from_str("#99FCFF")
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)




# LOCKDOWN COMMANDS

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
            color=discord.Color.from_str("#99FCFF")
        )
        await interaction.response.send_message(embed=embed)
        await channel.send(embed=embed)

        # Log to modlog
        log_embed = discord.Embed(
            title="Channel Lockdown",
            description=f"{channel.mention} locked.",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        log_embed.add_field(name="Moderator", value=f"{interaction.user.mention}")
        log_embed.add_field(name="Reason", value=f"{reason}")

        modlog_channel = guild.get_channel(CASE_LOG_CHANNEL)
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
    GENERAL_CHANNEL_ID = 1372430570822307890  

    new_permissions = everyone_role.permissions
    new_permissions.update(
        send_messages=False, 
        send_messages_in_threads=False,
        create_private_threads = False,
        create_public_threads = False
        )

    try:
        await everyone_role.edit(permissions=new_permissions)
    except discord.Forbidden:
        return await interaction.followup.send("I don't have permission to edit the default role.", ephemeral=True)

    # Mod response
    embed = discord.Embed(
        title="Server Locked",
        description="Server has been locked down. Mods can still talk in mod channels.",
        color=discord.Color.from_str("#99FCFF")
    )
    await interaction.followup.send(embed=embed)

    # Gen chat response
    general_channel = guild.get_channel(GENERAL_CHANNEL_ID)
    if general_channel:
        general_embed = discord.Embed(
            title="Server Locked",
            description="The server has been locked down. Once the mod team has handled the situation, it will be reopened.",
            color=discord.Color.from_str("#99FCFF")
        )
        await general_channel.send(embed=general_embed)

    # Log to modlogs
    log_embed = discord.Embed(
        title="Server Lockdown",
        description="The server has been locked down.",
        color=discord.Color.red(),
        timestamp=now
    )
    log_embed.add_field(name="Moderator", value=interaction.user.mention)
    log_embed.add_field(name="Reason", value=reason)

    modlog_channel = guild.get_channel(CASE_LOG_CHANNEL)
    if modlog_channel:
        await modlog_channel.send(embed=log_embed)





