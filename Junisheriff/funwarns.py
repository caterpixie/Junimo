import discord
from discord import Member, app_commands
import asyncio
import re
from datetime import datetime, timedelta, timezone

# ========================================
# CONFIGURATION
# ========================================

PISS_ROLE_ID = 1332969280165384254
FOOT_ROLE_ID = 1364045363412992050
BALD_ROLE_ID = 1411215127255973938

PISS_DURATION_SECONDS = 900     
FOOT_DURATION_SECONDS = 1800  

ALLOWED_GUILD_ID = 123456789012345678

EMBED_COLOR_HEX = "#99FCFF"
PISS_EMOJI = "<:piss:1368444697638600715>"
MOP_EMOJI = "<:mop:1368480159602049075>"
SOCK_EMOJI = "<:sock:1368478716199698502>"
WHYIOUGHTA_EMOJI = "<:whyioughta:1368453281419890688>"

# ========================================
# BOT HOOKUP
# ========================================

bot = None


def set_bot(bot_instance):
    global bot
    bot = bot_instance


def setup_funwarns(bot_instance: discord.Client):
    set_bot(bot_instance)
    bot_instance.tree.add_command(piss_on)
    bot_instance.tree.add_command(give_foot)
    bot_instance.tree.add_command(mop)
    bot_instance.tree.add_command(sock)
    bot_instance.tree.add_command(gag)
    bot_instance.tree.add_command(ungag)
    bot_instance.tree.add_command(snatch)
    bot_instance.tree.add_command(wig)


def allowed_guild(interaction: discord.Interaction) -> bool:
    """Optional guard to only allow commands in a specific guild."""
    return ALLOWED_GUILD_ID is None or (interaction.guild and interaction.guild.id == ALLOWED_GUILD_ID)


# Parse inputs like 1m, 30d, 2h etc.
def parse_duration(duration_str: str) -> int:
    """Parses a duration string like '1m', '2h', '3d' into total seconds."""
    units = {'d': 86400, 'h': 3600, 'm': 60}
    matches = re.findall(r"(\d+)([dhm])", duration_str.lower())

    if not matches:
        raise ValueError("Invalid duration format. Use '30m', '2h', '1d2h30m', etc.")

    total_seconds = 0
    for value, unit in matches:
        total_seconds += int(value) * units[unit]

    if total_seconds == 0:
        raise ValueError("Duration must be greater than 0.")

    return total_seconds


def base_embed(description: str) -> discord.Embed:
    return discord.Embed(description=description, color=discord.Color.from_str(EMBED_COLOR_HEX))


@app_commands.command(name="piss", description="Add the piss role")
async def piss_on(interaction: discord.Interaction, user: Member):
    if not allowed_guild(interaction):
        return await interaction.response.send_message("This command can't be used in this server.", ephemeral=True)

    piss_role = interaction.guild.get_role(PISS_ROLE_ID)

    try:
        await user.add_roles(piss_role)
    except discord.Forbidden:
        return await interaction.response.send_message(
            "I don't have permission to assign that role (check role hierarchy or permissions).",
            ephemeral=True
        )
    except discord.HTTPException as e:
        return await interaction.response.send_message(f"Failed to assign role: {e}", ephemeral=True)

    embed = base_embed(f"{PISS_EMOJI} {user.mention} has been pissed on")
    await interaction.response.send_message(embed=embed, allowed_mentions=discord.AllowedMentions(roles=True))

    await asyncio.sleep(PISS_DURATION_SECONDS)
    await user.remove_roles(piss_role)


@app_commands.command(name="foot", description="Add the foot role")
async def give_foot(interaction: discord.Interaction, user: Member):
    if not allowed_guild(interaction):
        return await interaction.response.send_message("This command can't be used in this server.", ephemeral=True)

    foot_role = interaction.guild.get_role(FOOT_ROLE_ID)

    try:
        await user.add_roles(foot_role)
    except discord.Forbidden:
        return await interaction.response.send_message(
            "I don't have permission to assign that role (check role hierarchy or permissions).",
            ephemeral=True
        )
    except discord.HTTPException as e:
        return await interaction.response.send_message(f"Failed to assign role: {e}", ephemeral=True)

    embed = base_embed(
        f"{WHYIOUGHTA_EMOJI} getting pissed on isn't bad enough. {user.mention} gets Seb's right foot..."
    )
    await interaction.response.send_message(embed=embed, allowed_mentions=discord.AllowedMentions(roles=True))

    await asyncio.sleep(FOOT_DURATION_SECONDS)
    await user.remove_roles(foot_role)


@app_commands.command(name="snatch", description="Make someone bald")
async def snatch(interaction: discord.Interaction, user: Member):
    if not allowed_guild(interaction):
        return await interaction.response.send_message("This command can't be used in this server.", ephemeral=True)

    bald_role = interaction.guild.get_role(BALD_ROLE_ID)

    try:
        await user.add_roles(bald_role)
    except discord.Forbidden:
        return await interaction.response.send_message(
            "I don't have permission to assign that role (check role hierarchy or permissions).",
            ephemeral=True
        )
    except discord.HTTPException as e:
        return await interaction.response.send_message(f"Failed to assign role: {e}", ephemeral=True)

    embed = base_embed(f"{interaction.user} snatched {user.mention}'s wig. Dale.")
    await interaction.response.send_message(embed=embed, allowed_mentions=discord.AllowedMentions(roles=True))


@app_commands.command(name="wig", description="Hides baldness")
async def wig(interaction: discord.Interaction, user: Member):
    if not allowed_guild(interaction):
        return await interaction.response.send_message("This command can't be used in this server.", ephemeral=True)

    bald_role = interaction.guild.get_role(BALD_ROLE_ID)
    embed = base_embed(f"{interaction.user} put a wig on {user.mention}.")

    if bald_role in user.roles:
        await user.remove_roles(bald_role)
        await interaction.response.send_message(embed=embed, allowed_mentions=discord.AllowedMentions(roles=True))
    else:
        await interaction.response.send_message(f"{user.mention} doesn't have the bald role.", ephemeral=True)


@app_commands.command(name="mop", description="Removes the piss role")
async def mop(interaction: discord.Interaction, user: Member):
    if not allowed_guild(interaction):
        return await interaction.response.send_message("This command can't be used in this server.", ephemeral=True)

    piss_role = interaction.guild.get_role(PISS_ROLE_ID)
    embed = base_embed(f"{MOP_EMOJI} {interaction.user} wiped the piss from {user.mention}. Say thank you~")

    if piss_role in user.roles:
        await user.remove_roles(piss_role)
        await interaction.response.send_message(embed=embed, allowed_mentions=discord.AllowedMentions(roles=True))
    else:
        await interaction.response.send_message(f"{user.mention} doesn't have the piss role.", ephemeral=True)


@app_commands.command(name="sock", description="Removes the foot role")
async def sock(interaction: discord.Interaction, user: Member):
    if not allowed_guild(interaction):
        return await interaction.response.send_message("This command can't be used in this server.", ephemeral=True)

    foot_role = interaction.guild.get_role(FOOT_ROLE_ID)
    embed = base_embed(
        f"{SOCK_EMOJI} {interaction.user} put a sock on Seb's dogs. {user.mention}, you better be good or else it's coming back off."
    )

    if foot_role in user.roles:
        await user.remove_roles(foot_role)
        await interaction.response.send_message(embed=embed, allowed_mentions=discord.AllowedMentions(roles=True))
    else:
        await interaction.response.send_message(f"{user.mention} doesn't have the foot role.", ephemeral=True)


@app_commands.command(name="gag", description="Gags the user using native timeout")
async def gag(interaction: discord.Interaction, user: Member, duration: str, reason: str = None):
    if not allowed_guild(interaction):
        return await interaction.response.send_message("This command can't be used in this server.", ephemeral=True)

    try:
        seconds = parse_duration(duration)
        until = datetime.now(timezone.utc) + timedelta(seconds=seconds)
        await user.edit(timed_out_until=until, reason=reason)

        reason_text = f"\nReason: {reason}" if reason else ""
        embed = base_embed(f"{interaction.user} put the gag on {user.mention}.{reason_text}")
        await interaction.response.send_message(embed=embed, allowed_mentions=discord.AllowedMentions(users=True))

    except discord.Forbidden:
        await interaction.response.send_message("I don't have permission to timeout this user.", ephemeral=True)
    except discord.HTTPException as e:
        await interaction.response.send_message(f"Failed to timeout user: {e}", ephemeral=True)
    except ValueError as e:
        await interaction.response.send_message(str(e), ephemeral=True)


@app_commands.command(name="ungag", description="Removes the user's timeout")
async def ungag(interaction: discord.Interaction, user: Member):
    if not allowed_guild(interaction):
        return await interaction.response.send_message("This command can't be used in this server.", ephemeral=True)

    try:
        await user.edit(timed_out_until=None)
        embed = base_embed(
            f"{interaction.user} took the gag off {user.mention}. They won't hesitate to gag you again {WHYIOUGHTA_EMOJI}"
        )
        await interaction.response.send_message(embed=embed, allowed_mentions=discord.AllowedMentions(users=True))

    except discord.Forbidden:
        await interaction.response.send_message("I don't have permission to remove the timeout.", ephemeral=True)
    except discord.HTTPException as e:
        await interaction.response.send_message(f"Failed to remove timeout: {e}", ephemeral=True)


