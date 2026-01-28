import discord
from discord import app_commands, ui
from discord.ui import View, Button, Modal, TextInput
import os
import json
import aiomysql
from datetime import timezone
from zoneinfo import ZoneInfo
import aiohttp
import io

# ============================================================
# CONFIGURATION
# ============================================================

HEADER_IMAGE = "https://i.imgur.com/aJMFW3t.png"


TICKET_CHANNEL_ID = 1423892472097931326
SUPPORT_CATEGORY_ID = 1423894614582235257

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
    "header_image": "https://i.imgur.com/aJMFW3t.png",
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
            overwrites=overwrites
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
    async def close_ticket(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):
        await interaction.response.send_message(
            "Are you sure you want to close this ticket?",
            view=ConfirmCloseView()
        )

class ConfirmCloseView(ui.View):
    def __init__(self):
        super().__init__(timeout=30)

    @ui.button(label="Confirm", style=discord.ButtonStyle.primary)
    async def confirm(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):
        await interaction.response.send_message(
            "Ticket closed.",
            ephemeral=True
        )
        await interaction.channel.delete(reason="Ticket closed")

    @ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):
        await interaction.response.send_message(
            "Ticket closure cancelled."
        )
        self.stop()

ticket_group = TicketGroup()

@ticket_group.command(name="setup", description="Sends the embed to the ticket channel")
async def embed_setup(interaction: discord.Interaction):
    ticket_embed_channel = interaction.guild.get_channel(TICKET_CHANNEL_ID)
    if not ticket_embed_channel:
        await interaction.response.send_message("Error: Ticket/support channel not found.", ephemeral=True)
        return
    
    headers = {
    "User-Agent": "Mozilla/5.0" 
    }
    
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(HEADER_IMAGE, allow_redirects=True) as resp:
            if resp.status != 200:
                await interaction.response.send_message(
                    f"Failed to fetch image (HTTP {resp.status}).",
                    ephemeral=True
                )
                return

            content_type = resp.headers.get("Content-Type", "")
            data = await resp.read()

    if not content_type.startswith("image/") or data[:10].lower().startswith(b"<!doctype") or data[:6].lower().startswith(b"<html"):
        await interaction.response.send_message(
            "Imgur returned a webpage instead of an image (blocked/redirected). Try using a Discord attachment or another direct image host.",
            ephemeral=True
        )
        return

    buf = io.BytesIO(data)
    buf.seek(0)

    file = discord.File(fp=buf, filename="ticket-banner.png")

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
