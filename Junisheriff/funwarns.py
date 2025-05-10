import discord
from discord import Role, Member
from discord import app_commands
import asyncio
import re
from datetime import datetime, timedelta, timezone

GUILD_ID = 123456789012345678

bot = None
def set_bot(bot_instance):
    global bot
    bot = bot_instance

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
        
@app_commands.command(name="piss", description="Add the piss role")
async def piss_on(interaction: discord.Interaction, user: Member):
    piss = interaction.guild.get_role(1332969280165384254)

    try:
        await user.add_roles(piss)
    except discord.Forbidden:
        await interaction.response.send_message("I don't have permission to assign that role (check role hierarchy or permissions).", ephemeral=True)
        return
    except discord.HTTPException as e:
        await interaction.response.send_message(f"Failed to assign role: {e}", ephemeral=True)
        return
    
    embed = discord.Embed(
        description= f"<:piss:1368444697638600715> {user.mention} has been pissed on",
        color=discord.Color.from_str("#7CE4FF")
    )
    
    await interaction.response.send_message(embed=embed, allowed_mentions=discord.AllowedMentions(roles=True))

    await asyncio.sleep(900)
    await user.remove_roles(piss)

@app_commands.command(name="foot", description="Add the foot role")
async def give_foot(interaction: discord.Interaction, user: Member):
    foot = interaction.guild.get_role(1364045363412992050)

    try:
        await user.add_roles(foot)
    except discord.Forbidden:
        await interaction.response.send_message("I don't have permission to assign that role (check role hierarchy or permissions).", ephemeral=True)
        return
    except discord.HTTPException as e:
        await interaction.response.send_message(f"Failed to assign role: {e}", ephemeral=True)
        return
    
    embed = discord.Embed(
        description= f"<:whyioughta:1368453281419890688> getting pissed on isn't bad enough. {user.mention} gets Seb's right foot...",
        color=discord.Color.from_str("#7CE4FF")
    )
    
    await interaction.response.send_message(embed=embed, allowed_mentions=discord.AllowedMentions(roles=True))

    await asyncio.sleep(1800)
    await user.remove_roles(foot)

@app_commands.command(name="mop", description="Removes the piss role")
async def mop(interaction: discord.Interaction, user: Member):
    piss = interaction.guild.get_role(1332969280165384254)

    embed = discord.Embed(
        description= f"<:mop:1368480159602049075> {interaction.user} wiped the piss from {user.mention}. Say thank you~",
        color=discord.Color.from_str("#7CE4FF")
    )

    if piss in user.roles:
        await user.remove_roles(piss)
        await interaction.response.send_message(embed=embed, allowed_mentions=discord.AllowedMentions(roles=True))
    else:
        await interaction.response.send_message(f"{user.mention} doesn't have the piss role.", ephemeral=True)

@app_commands.command(name="sock", description="Removes the foot role")
async def sock(interaction: discord.Interaction, user: Member):
    foot = interaction.guild.get_role(1364045363412992050)

    embed = discord.Embed(
        description= f"<:sock:1368478716199698502> {interaction.user} put a sock on Seb's dogs. {user.mention}, you better be good or else it's coming back off.",
        color=discord.Color.from_str("#7CE4FF")
    )

    if foot in user.roles:
        await user.remove_roles(foot)
        await interaction.response.send_message(embed=embed, allowed_mentions=discord.AllowedMentions(roles=True))
    else:
        await interaction.response.send_message(f"{user.mention} doesn't have the foot role.", ephemeral=True)

@app_commands.command(name="gag", description="Gags the user using native timeout")
async def gag(interaction: discord.Interaction, user: Member, duration: str, reason: str = None):
    try:
        seconds = parse_duration(duration)
        until = datetime.now(timezone.utc) + timedelta(seconds=seconds)
        await user.edit(timed_out_until=until, reason=reason)

        reason_text = f"\nReason: {reason}" if reason else ""
        embed = discord.Embed(
            description=f"{interaction.user} put the gag on {user.mention}.{reason_text}",
            color=discord.Color.from_str("#7CE4FF")
        )
        await interaction.response.send_message(embed=embed, allowed_mentions=discord.AllowedMentions(users=True))

    except discord.Forbidden:
        await interaction.response.send_message("I don't have permission to timeout this user.", ephemeral=True)
    except discord.HTTPException as e:
        await interaction.response.send_message(f"Failed to timeout user: {e}", ephemeral=True)
    except ValueError as e:
        await interaction.response.send_message(str(e), ephemeral=True)


@app_commands.command(name="ungag", description="Removes the user's timeout")
async def ungag(interaction: discord.Interaction, user: Member):
    try:
        await user.edit(timed_out_until=None)
        embed = discord.Embed(
            description=f"{interaction.user} took the gag off {user.mention}. They won't hesitate to gag you again <:whyioughta:1368453281419890688>",
            color=discord.Color.from_str("#7CE4FF")
        )
        await interaction.response.send_message(embed=embed, allowed_mentions=discord.AllowedMentions(users=True))

    except discord.Forbidden:
        await interaction.response.send_message("I don't have permission to remove the timeout.", ephemeral=True)
    except discord.HTTPException as e:
        await interaction.response.send_message(f"Failed to remove timeout: {e}", ephemeral=True)
