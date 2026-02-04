import discord
from discord import app_commands, ui
from discord.ui import View, Button, Modal, TextInput
import aiohttp
import io
import re
import os
from transcripting import export_ticket_to_html, cleanup_file, upload_transcript_to_r2
from datetime import datetime, timezone

# ============================================================
# CONFIGURATION
# ============================================================

EMBED_LOG_COLOR = "#D71919"

TICKET_CHANNEL_ID = 1423892472097931326
SUPPORT_CATEGORY_ID = 1423894614582235257
LOG_CHANNEL_ID = 1466281964930727936

MOD_ROLE_IDS = {
   1370967596534595624
}

# For the embeds created in the individual ticket channels for the user
TICKET_TYPES = {
    "server-support": {
        "name_prefix": "support",
        "write_roles": [],  
        "view_roles": [],
        "title": "Server Support Ticket",
        "welcome": "thanks for opening a server support ticket! Please describe your issue, and we will be with you shortly."
    },
    "mod-help": {
        "name_prefix": "mod-help",
        "write_roles": [],  
        "view_roles": [],
        "title": "Mod Help Ticket",
        "welcome": "thank you for submitting a mod help ticket! Please make sure that you have checked the troubleshooting guide. Once you have, describe your issue and we will be with you as soon as we can."
    },
    "bug-report": {
        "name_prefix": "bug-report",
        "write_roles": [],  
        "view_roles": [],  
        "title": "Bug Report Ticket",
        "welcome": "thank you for submitting a bug report ticket! Please describe as well as provide some screenshots of the issue, and we will be with you as soon as we can."
    },
    "other": {
        "name_prefix": "other",
        "write_roles": [],  
        "view_roles": [],
        "title": "Some Other Kinda Ticket",
        "welcome": "thanks for opening a ticket! Please describe your issue, and we will be with you shortly."
    }
}

# For the ticket panel in the support channel
TICKET_PANEL = {
    "main_description": (
        "Still need to talk to staff about your mods, need to report a bug, or have some questions about the server?\n\nClick the button below to create a ticket!"
    ),
    "troubleshooting": {
        "enabled": True,
        "text": (
            "Need help with your mods? All of your questions can be answered in this [troubleshooting guide](https://www.nexusmods.com/stardewvalley/articles/3926)!"
        ),
    },
    "button": {
        "label": "Create Ticket",
        "emoji": "📨",
        "style": discord.ButtonStyle.secondary
    },
    "color": "#D71919"
}

# ============================================================
# BOT HOOKUP
# ============================================================

bot = None
def set_bot(bot_instance):
    global bot
    bot = bot_instance


def safe_avatar_url(user):
    return user.avatar.url if user.avatar else None

def is_mod(member: discord.Member) -> bool:
    return any(role.id in MOD_ROLE_IDS for role in member.roles)

def get_ticket_meta(channel: discord.TextChannel) -> dict:
    """
    Reads opener + type from channel.topic.
    topic format: "ticket_opener_id=123; ticket_type=mod-help"
    """
    topic = channel.topic or ""
    opener_match = re.search(r"ticket_opener_id=(\d+)", topic)
    type_match = re.search(r"ticket_type=([a-z0-9\-]+)", topic)

    opener_id = int(opener_match.group(1)) if opener_match else None
    ticket_type = type_match.group(1) if type_match else None

    return {"opener_id": opener_id, "ticket_type": ticket_type}

async def user_has_open_ticket(guild: discord.Guild, user: discord.Member):
    category = guild.get_channel(SUPPORT_CATEGORY_ID)
    if not category:
        return False

    for channel in category.text_channels:
        perms = channel.permissions_for(user)
        if perms.view_channel:
            return channel

    return None

async def log_ticket_open(
        guild: discord.Guild,
        user: discord.Member,
        channel: discord.TextChannel,
        ticket_type: str
    ):
        log_channel = guild.get_channel(LOG_CHANNEL_ID)
        if not log_channel:
            return

        embed = discord.Embed(
            title="Ticket Opened",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="User/Creator", value=f"{user.mention}\n`{user}`")
        embed.add_field(name="Ticket Type", value=ticket_type.replace("-", " ").title())
        embed.set_footer(text=f"ID: {user.id}")
        embed.set_author(name=str(user), icon_url=safe_avatar_url(user))

        await log_channel.send(embed=embed)

async def get_ticket_participants(channel: discord.TextChannel) -> list[discord.User]:
    participants: dict[int, discord.User] = {}

    async for msg in channel.history(limit=None):
        author = msg.author
        if author.bot:
            continue

        participants[author.id] = author

    return list(participants.values())

async def dm_transcript_to_non_mod_participants(
    participants: list[discord.abc.User],
    guild: discord.Guild,
    channel: discord.TextChannel,
    transcript_url: str
):
    for user in participants:
        if user.bot:
            continue

        member = user if isinstance(user, discord.Member) else guild.get_member(user.id)
        if member is None:
            try:
                member = await guild.fetch_member(user.id)
            except Exception:
                continue

        if is_mod(member):
            continue

        try:
            dm_embed = discord.Embed(
                title=f"Your ticket in **{guild.name}** was closed",
                description="You can view the full transcript by clicking the link below.",
                color=discord.Color.from_str(EMBED_LOG_COLOR),
                timestamp=datetime.now(timezone.utc)
            )

            dm_embed.add_field(
                name="Ticket Name", 
                value=f"`{channel.name}`"
            )


            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="View Transcript", url=transcript_url))

            await user.send(embed=dm_embed, view=view) 

        except (discord.Forbidden, discord.HTTPException):
            continue

async def log_ticket_close(
    guild: discord.Guild,
    closed_by: discord.Member,
    channel: discord.TextChannel,
    opened_by: discord.Member | None,
    ticket_type: str | None,
    transcript_url: str,
    participants: list[discord.Member] | None = None
):
    log_channel = guild.get_channel(LOG_CHANNEL_ID)
    if not log_channel:
        return

    embed = discord.Embed(
        title="Ticket Closed",
        color=discord.Color.from_str(EMBED_LOG_COLOR),
        timestamp=datetime.now(timezone.utc)
    )

    embed.add_field(
        name="Closed By",
        value=f"{closed_by.mention}\n`{closed_by}`",
        inline=False
    )

    embed.add_field(
        name="Ticket Type",
        value=(ticket_type or "Unknown").replace("-", " ").title(),
        inline=True
    )

    if participants:
        formatted = [
            f"{m.mention} (`{m.id}`)"
            for m in participants[:20]
        ]

        mentions = ", ".join(formatted)

        if len(participants) > 20:
            mentions += f"\n+ {len(participants) - 20} more"

        if len(mentions) > 1024:
            mentions = mentions[:1020] + "..."

        embed.add_field(
            name="Participants",
            value=mentions,
            inline=False
        )
    else:
        embed.add_field(
            name="Participants",
            value="No one interacted with this ticket.",
            inline=False
        )
    embed.set_author(name=str(closed_by), icon_url=safe_avatar_url(closed_by))

    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="View Transcript", url=transcript_url))

    await log_channel.send(embed=embed, view=view)

async def dm_user_ticket_attention(user: discord.abc.User, guild: discord.Guild, channel: discord.TextChannel):
    try:
        embed = discord.Embed(
            title="A ticket needs your attention",
            description=(
                f"A moderator added you to a ticket in **{guild.name}**.\n\n"
            ),
            color=discord.Color.from_str(EMBED_LOG_COLOR),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Open Ticket", value=f"https://discord.com/channels/{guild.id}/{channel.id}")

        await user.send(embed=embed)
    except (discord.Forbidden, discord.HTTPException):
        pass


class AddUserSelect(discord.ui.UserSelect):
    def __init__(self):
        super().__init__(
            placeholder="Select a user to add to this ticket…",
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: discord.Interaction):
        channel: discord.TextChannel = interaction.channel  
        guild: discord.Guild = interaction.guild  

        if not isinstance(interaction.user, discord.Member) or not is_mod(interaction.user):
            await interaction.response.send_message("You don’t have permission to use this.", ephemeral=True)
            return

        selected_user = self.values[0] 

        member = selected_user if isinstance(selected_user, discord.Member) else guild.get_member(selected_user.id)
        if member is None:
            try:
                member = await guild.fetch_member(selected_user.id)
            except Exception:
                member = None

        if member is None:
            await interaction.response.send_message("Couldn’t find that user in this server.", ephemeral=True)
            return

        # Add permissions: view + read history + write
        await channel.set_permissions(
            member,
            view_channel=True,
            read_message_history=True,
            send_messages=True
        )

        await interaction.response.send_message(
            f"Added {member.mention} to {channel.mention}.",
            ephemeral=True
        )

        await dm_user_ticket_attention(member, guild, channel)


class AddUserView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(AddUserSelect())

class TicketGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="ticket", description="Ticket Commands")

class TicketTypeSelect(ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Server Support", value="server-support"),
            discord.SelectOption(label="Mod Help", value="mod-help"),
            discord.SelectOption(label="Report a Bug", value="bug-report"),
            discord.SelectOption(label="Other", value="other")
        ]

        super().__init__(
            placeholder="What are you opening a ticket about?",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        author = interaction.user

        existing = await user_has_open_ticket(guild, author)
        if existing:
            await interaction.response.send_message(
                f"You already have an open ticket: {existing.mention}\n"
                "Please close it before creating a new one.",
                ephemeral=True
            )
            return

        ticket_type = self.values[0]
        config = TICKET_TYPES[ticket_type]

        category = guild.get_channel(SUPPORT_CATEGORY_ID)
        if not category:
            await interaction.response.send_message("Error: Support category not found.", ephemeral=True)
            return
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            author: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }

        for role_id in config["write_roles"]:
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True
                )

        for role_id in config["view_roles"]:
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=False,
                    read_message_history=True
                )

        safe_name = author.name.lower().replace(" ", "-")
        channel_name = f"{config['name_prefix']}-{safe_name}"[:90]
        
        ticket_channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            topic=f"ticket_opener_id={author.id}; ticket_type={ticket_type}"
        )

        await interaction.response.send_message(
            f"Your ticket has been created: {ticket_channel.mention}",
            ephemeral=True
        )

        embed = discord.Embed(
            title=f"{config['title']}",
            description=f"{author.mention}, {config['welcome']}",
            color=discord.Color.from_str("#D71919")
        )
        await ticket_channel.send(
            embed=embed,
            view=CloseTicketView()
        )

        await log_ticket_open(
            guild=guild,
            user=author,
            channel=ticket_channel,
            ticket_type=ticket_type
        )

        
class TicketPanelView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # keep it persistent-ish
        self.add_item(OpenTicketButton())

class TicketTypeView(ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(TicketTypeSelect())

class OpenTicketButton(ui.Button):
    def __init__(self):
        super().__init__(label="Create Ticket", style=discord.ButtonStyle.secondary, emoji="📨")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Choose a ticket type:",
            view=TicketTypeView(),
            ephemeral=True
        )

class CloseTicketView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="Close Ticket",
        style=discord.ButtonStyle.secondary,
        emoji="🔒"
    )
    async def close_ticket(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message(
            "Are you sure you want to close this ticket?",
            view=ConfirmCloseView()
        )

    @ui.button(
        label="Add User",
        style=discord.ButtonStyle.secondary,
    )
    async def add_user(self, interaction: discord.Interaction, button: ui.Button):
        if not isinstance(interaction.user, discord.Member) or not is_mod(interaction.user):
            await interaction.response.send_message("Only moderators can use this.", ephemeral=True)
            return

        await interaction.response.send_message(
            "Select a user to add to this ticket:",
            view=AddUserView(),
            ephemeral=True
        )
    
class ConfirmCloseView(ui.View):
    def __init__(self):
        super().__init__(timeout=30)

    @ui.button(label="Confirm", style=discord.ButtonStyle.primary)
    async def confirm(self, interaction: discord.Interaction, button: ui.Button):
        channel = interaction.channel
        guild = interaction.guild
        closed_by = interaction.user

        participants = await get_ticket_participants(channel)
        await interaction.response.send_message("Closing ticket and generating transcript...", ephemeral=True)

        meta = get_ticket_meta(channel)
        opener_id = meta["opener_id"]
        ticket_type = meta["ticket_type"]

        opened_by = None
        if opener_id:
            opened_by = guild.get_member(opener_id)
            if opened_by is None:
                try:
                    opened_by = await guild.fetch_member(opener_id)
                except Exception:
                    opened_by = None

        transcript_path = None
        try:
            transcript_path, slug = await export_ticket_to_html(channel)
            transcript_url = await upload_transcript_to_r2(transcript_path, slug)

            await log_ticket_close(
                guild=guild,
                closed_by=closed_by,
                channel=channel,
                opened_by=opened_by,
                ticket_type=ticket_type,
                transcript_url=transcript_url,
                participants=participants
            )

            await dm_transcript_to_non_mod_participants(
                participants=participants,
                guild=guild,
                channel=channel,
                transcript_url=transcript_url
            )

        except Exception as e:
            await interaction.followup.send(f"Transcript export failed: `{e}`", ephemeral=True)

        if transcript_path:
            cleanup_file(transcript_path)

        await channel.delete(reason="Ticket closed")

ticket_group = TicketGroup()

@ticket_group.command(name="setup", description="Sends the embed to the ticket channel")
async def embed_setup(interaction: discord.Interaction):
    ticket_embed_channel = interaction.guild.get_channel(TICKET_CHANNEL_ID)
    if not ticket_embed_channel:
        await interaction.response.send_message("Error: Ticket/support channel not found.", ephemeral=True)
        return

#    headers = {
#    "User-Agent": "Mozilla/5.0" 
#    }
#    
#    async with aiohttp.ClientSession(headers=headers) as session:
#        async with session.get(HEADER_IMAGE, allow_redirects=True) as resp:
#            if resp.status != 200:
#                await interaction.response.send_message(
#                    f"Failed to fetch image (HTTP {resp.status}).",
#                   ephemeral=True
#                )
#                return
#
#            content_type = resp.headers.get("Content-Type", "")
#            data = await resp.read()
#
#    if not content_type.startswith("image/") or data[:10].lower().startswith(b"<!doctype") or data[:6].lower().startswith(b"<html"):
#        await interaction.response.send_message(
#            "Imgur returned a webpage instead of an image (blocked/redirected). Try using a Discord attachment or another direct image host.",
#            ephemeral=True
#        )
#        return
#
#   buf = io.BytesIO(data)
#    buf.seek(0)

    file = discord.File("assets/ticket_header.png", filename="ticket_header.png")

    title_embed = discord.Embed(
        color=discord.Color.from_str(TICKET_PANEL["color"])
    )
    title_embed.set_image(url=TICKET_PANEL["header_image"])

    main_embed = discord.Embed(
        description=TICKET_PANEL["main_description"],
        color=discord.Color.from_str(TICKET_PANEL["color"])
    )

    await ticket_embed_channel.send(file=file)

    if TICKET_PANEL["troubleshooting"]["enabled"]:
        troubleshooting_embed = discord.Embed(
            description=TICKET_PANEL["troubleshooting"]["text"],
            color=discord.Color.from_str(TICKET_PANEL["color"]),
        )
        await ticket_embed_channel.send(embed=troubleshooting_embed)

    await ticket_embed_channel.send(embed=main_embed, view=TicketPanelView())
    await interaction.response.send_message("Ticket panel sent!", ephemeral=True)
