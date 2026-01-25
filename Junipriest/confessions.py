import discord
from discord import app_commands, ui
from discord.ui import View, Button, Modal, TextInput
import os
import json
import aiomysql
from datetime import timezone
from zoneinfo import ZoneInfo

# ============================================================
# CONFIG (edit everything you want to customize in this section)
# ============================================================

# Channel IDs
CONFESSION_CHANNEL_ID = 1322430350575669320
CONFESSION_APPROVAL_CHANNEL_ID = 1322431042501738550
CONFESSION_LOGS_CHANNEL_ID = 1322431064777429124

# Local files
COUNTER_FILE = "confession_counter.txt"
LATEST_CONFESSION_FILE = "latest_confession.txt"
PENDING_CONFESSIONS_FILE = "pending_confessions.json"

# Timezones / formatting
DENIAL_LOG_TIMEZONE = "America/Chicago"  # used for /confession denials display
DENIAL_LOG_TZ_LABEL = "CST"              # label shown in embed

# Embed colors
COLOR_CONFESSION = "#DCA8FF"
COLOR_REPLY = "#ECD0FF"
COLOR_DENIAL_LOG = "#99FCFF"
COLOR_APPROVED_LOG = "green"
COLOR_DENIED_LOG = "red"

# UI strings (buttons / modal titles / labels)
BTN_LABEL_SUBMIT = "Submit a Confession!"
BTN_LABEL_REPLY = "Reply"
BTN_LABEL_APPROVE = "✅ Approve"
BTN_LABEL_DENY = "❌ Deny"
BTN_LABEL_DENY_REASON = "💬 Deny with Reason"
BTN_LABEL_PREV = "Previous"
BTN_LABEL_NEXT = "Next"

MODAL_TITLE_SUBMIT = "Submit a Confession"
MODAL_TITLE_REPLY = "Reply to a Confession"
MODAL_TITLE_DENY_REASON = "Deny Confession with Reason"

INPUT_LABEL_CONFESSION = "Your Confession"
INPUT_LABEL_REPLY = "Your Reply"
INPUT_LABEL_DENY_REASON = "Reason"
INPUT_PLACEHOLDER_DENY_REASON = "Why is this being denied?"

# Custom IDs (Discord UI persistence / uniqueness)
CUSTOM_ID_CONFESSION_SUBMIT = "confession_submit"
CUSTOM_ID_CONFESSION_REPLY = "confession_reply"
CUSTOM_ID_APPROVAL_APPROVE = "approval_approve"
CUSTOM_ID_APPROVAL_DENY = "approval_deny"
CUSTOM_ID_APPROVAL_DENY_REASON = "approval_denyreason"

# Embed titles / field names
EMBED_TITLE_CONFESSION_AWAITING = "Confession Awaiting Review"
EMBED_TITLE_REPLY_AWAITING = "Reply Awaiting Review"
EMBED_TITLE_ANON_CONFESSION = "Anonymous Confession"
EMBED_TITLE_ANON_REPLY = "Anonymous Reply"
EMBED_TITLE_DENIED_DM = "Your Denied Confession"
EMBED_TITLE_APPROVED_LOG = "Approved"
EMBED_TITLE_DENIED_LOG = "Confession Denied"

FIELD_USER = "User"
FIELD_APPROVED_BY = "Approved By"
FIELD_DENIED_BY = "Denied By"
FIELD_REASON = "Reason"
FIELD_ORIGINAL_MESSAGE = "Original Message"
FIELD_ORIGINAL_CONFESSION = "Original Confession"

# User-facing messages
MSG_SUBMITTED_CONFESSION = "Your confession has been submitted!"
MSG_SUBMITTED_REPLY = "Your reply has been submitted!"
MSG_CONFESSION_SUBMITTED_CMD = "Confession submitted!"
MSG_NOT_FOUND_ORIGINAL = "Original confession not found."
MSG_INVALID_LINK = "Invalid message link. Please make sure it's a valid Discord message URL."
MSG_CHANNEL_NOT_FOUND_FROM_LINK = "Could not find the channel from that link."
MSG_MESSAGE_NOT_FOUND = "Message not found. Make sure the link is from this server."
MSG_APPROVED = "Approved and posted!"
MSG_DENIED = "Confession denied."
MSG_DENIED_WITH_REASON = "Confession has been denied with reason."
MSG_NO_DENIALS = "{username} has no denied confessions logged."

# DM text
DM_DENIED_PREFIX = "Your confession in After Dark has been denied."
DM_DENIED_WITH_REASON_PREFIX = "Your confession in After Dark was denied."
DM_REASON_HEADER = "**Reason:**"

# Link formats
JUMP_MESSAGE_URL = "https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"

# Pagination
DENIALS_PER_PAGE = 10

# ============================================================

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

    @ui.button(label=BTN_LABEL_PREV, style=discord.ButtonStyle.primary)
    async def previous_page(self, interaction: discord.Interaction, button: ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    @ui.button(label=BTN_LABEL_NEXT, style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: ui.Button):
        if self.current_page < len(self.embeds) - 1:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)


def get_next_confession_number():
    if not os.path.exists(COUNTER_FILE):
        with open(COUNTER_FILE, "w") as f:
            f.write("1")
            return 1

    with open(COUNTER_FILE, "r+") as f:
        number = int(f.read().strip())
        f.seek(0)
        f.write(str(number + 1))
        f.truncate()
        return number


def get_latest_confession_id():
    if os.path.exists(LATEST_CONFESSION_FILE):
        with open(LATEST_CONFESSION_FILE, "r") as f:
            try:
                return int(f.read().strip())
            except ValueError:
                return None
    return None


def set_latest_confession_id(message_id):
    with open(LATEST_CONFESSION_FILE, "w") as f:
        f.write(str(message_id))


def log_pending_confession(message_id, data):
    try:
        if os.path.exists(PENDING_CONFESSIONS_FILE):
            with open(PENDING_CONFESSIONS_FILE, "r") as f:
                pending = json.load(f)
        else:
            pending = {}

        pending[str(message_id)] = data

        with open(PENDING_CONFESSIONS_FILE, "w") as f:
            json.dump(pending, f, indent=4)
        print(f"[LOG] Saved pending confession {message_id}")
    except Exception as e:
        print(f"[ERROR] Logging pending confession: {e}")


def remove_pending_confession(message_id):
    try:
        if os.path.exists(PENDING_CONFESSIONS_FILE):
            with open(PENDING_CONFESSIONS_FILE, "r") as f:
                pending = json.load(f)
            if str(message_id) in pending:
                del pending[str(message_id)]
                with open(PENDING_CONFESSIONS_FILE, "w") as f:
                    json.dump(pending, f, indent=4)
    except Exception as e:
        print(f"[ERROR] Removing pending confession: {e}")


def safe_avatar_url(user):
    return user.avatar.url if user.avatar else None


async def record_denial_event(
    guild_id: int,
    user_id: int,
    confession_text: str,
    denied_by_name: str,
    reason: str | None
) -> int:
    """
    Inserts a NEW denial event row with a precise interaction timestamp (NOW()).
    Returns the user's total number of denial events after insert.
    """
    async with bot.pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO confession_denials (guild_id, user_id, denied_by_name, confession_text, reason)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (guild_id, user_id, denied_by_name, confession_text, reason)
            )

            await cur.execute(
                """
                SELECT COUNT(*) FROM confession_denials
                WHERE guild_id = %s AND user_id = %s
                """,
                (guild_id, user_id)
            )
            row = await cur.fetchone()
            return int(row[0]) if row and row[0] is not None else 1


class ConfessionInteractionView(View):
    def __init__(self, bot_instance):
        super().__init__(timeout=None)
        self.bot = bot_instance

    @discord.ui.button(label=BTN_LABEL_SUBMIT, style=discord.ButtonStyle.primary, custom_id=CUSTOM_ID_CONFESSION_SUBMIT)
    async def submit_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(ConfessionSubmitModal())

    @discord.ui.button(label=BTN_LABEL_REPLY, style=discord.ButtonStyle.secondary, custom_id=CUSTOM_ID_CONFESSION_REPLY)
    async def reply_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(ConfessionReplyModal(interaction.message.id))


class ConfessionSubmitModal(Modal, title=MODAL_TITLE_SUBMIT):
    confession = TextInput(label=INPUT_LABEL_CONFESSION, style=discord.TextStyle.paragraph, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        confession_number = get_next_confession_number()
        approval_channel = interaction.guild.get_channel(CONFESSION_APPROVAL_CHANNEL_ID)

        embed = discord.Embed(
            title=f"{EMBED_TITLE_CONFESSION_AWAITING} (#{confession_number})",
            description=f"\"{self.confession.value}\"",
            colour=discord.Color.from_str(COLOR_CONFESSION)
        )
        embed.add_field(name=FIELD_USER, value=f"||{interaction.user.name} (`{interaction.user.id}`)||")

        view = ApprovalView(self.confession.value, interaction.user, confession_number)
        approval_message = await approval_channel.send(embed=embed, view=view)

        log_pending_confession(approval_message.id, {
            "confession_text": self.confession.value,
            "submitter_id": interaction.user.id,
            "submitter_name": interaction.user.name,
            "confession_number": confession_number,
            "type": "confession",
            "reply_to_message_id": None
        })

        await interaction.response.send_message(MSG_SUBMITTED_CONFESSION, ephemeral=True)


class ConfessionReplyModal(Modal, title=MODAL_TITLE_REPLY):
    reply = TextInput(label=INPUT_LABEL_REPLY, style=discord.TextStyle.paragraph, required=True)

    def __init__(self, original_message_id: int):
        super().__init__()
        self.original_message_id = original_message_id

    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.guild.get_channel(CONFESSION_CHANNEL_ID)

        try:
            await channel.fetch_message(self.original_message_id)
        except discord.NotFound:
            await interaction.response.send_message(MSG_NOT_FOUND_ORIGINAL, ephemeral=True)
            return

        confession_number = get_next_confession_number()
        approval_channel = interaction.guild.get_channel(CONFESSION_APPROVAL_CHANNEL_ID)

        jump_link = JUMP_MESSAGE_URL.format(
            guild_id=interaction.guild.id,
            channel_id=channel.id,
            message_id=self.original_message_id
        )

        embed = discord.Embed(
            title=f"{EMBED_TITLE_REPLY_AWAITING} (#{confession_number})",
            description=f"\"{self.reply.value}\"",
            color=discord.Color.from_str(COLOR_REPLY)
        )
        embed.add_field(name=FIELD_USER, value=f"||{interaction.user.name} (`{interaction.user.id}`)||")
        embed.add_field(
            name=FIELD_ORIGINAL_MESSAGE,
            value=f"[Jump to message]({jump_link})",
            inline=False
        )

        view = ApprovalView(
            confession_text=self.reply.value,
            submitter=interaction.user,
            confession_number=confession_number,
            type="reply",
            reply_to_message_id=self.original_message_id
        )
        approval_message = await approval_channel.send(embed=embed, view=view)

        log_pending_confession(approval_message.id, {
            "confession_text": self.reply.value,
            "submitter_id": interaction.user.id,
            "submitter_name": interaction.user.name,
            "confession_number": confession_number,
            "type": "reply",
            "reply_to_message_id": self.original_message_id
        })
        await interaction.response.send_message(MSG_SUBMITTED_REPLY, ephemeral=True)


class ApprovalView(View):
    def __init__(self, confession_text, submitter, confession_number, type="confession", reply_to_message_id=None):
        super().__init__(timeout=None)
        self.confession_text = confession_text
        self.confession_number = confession_number
        self.submitter = submitter
        self.type = type
        self.reply_to_message_id = reply_to_message_id

    @discord.ui.button(label=BTN_LABEL_APPROVE, style=discord.ButtonStyle.success, custom_id=CUSTOM_ID_APPROVAL_APPROVE)
    async def approve(self, interaction: discord.Interaction, button: Button):
        channel = interaction.guild.get_channel(CONFESSION_CHANNEL_ID)
        logchannel = interaction.guild.get_channel(CONFESSION_LOGS_CHANNEL_ID)

        if self.type == "reply":
            jump_url = JUMP_MESSAGE_URL.format(
                guild_id=interaction.guild.id,
                channel_id=channel.id,
                message_id=self.reply_to_message_id
            )
            embed = discord.Embed(
                title=f"{EMBED_TITLE_ANON_REPLY} (#{self.confession_number})",
                description=f"\"{self.confession_text}\"\n",
                color=discord.Color.from_str(COLOR_REPLY)
            )
            embed.add_field(name=FIELD_ORIGINAL_CONFESSION, value=f"[Jump to confession]({jump_url})", inline=False)
        else:
            embed = discord.Embed(
                title=f"{EMBED_TITLE_ANON_CONFESSION} (#{self.confession_number})",
                description=f"\"{self.confession_text}\"",
                color=discord.Color.from_str(COLOR_CONFESSION)
            )

        new_message = await channel.send(embed=embed, view=ConfessionInteractionView(bot))

        last_message_id = get_latest_confession_id()
        if last_message_id:
            try:
                old_message = await channel.fetch_message(last_message_id)
                await old_message.edit(view=None)
            except discord.NotFound:
                pass

        set_latest_confession_id(new_message.id)

        await interaction.response.send_message(MSG_APPROVED, ephemeral=True)
        remove_pending_confession(interaction.message.id)
        await interaction.message.delete()

        logembed = discord.Embed(
            title=f"{EMBED_TITLE_APPROVED_LOG} (#{self.confession_number})",
            description=f"\"{self.confession_text}\"",
            color=discord.Color.green()
        )
        logembed.add_field(name=FIELD_USER, value=f"||{self.submitter.name} (`{self.submitter.id}`)||")
        logembed.add_field(name=FIELD_APPROVED_BY, value=f"{interaction.user.mention}", inline=False)

        await logchannel.send(embed=logembed)

    @discord.ui.button(label=BTN_LABEL_DENY, style=discord.ButtonStyle.danger, custom_id=CUSTOM_ID_APPROVAL_DENY)
    async def deny(self, interaction: discord.Interaction, button: Button):
        logchannel = interaction.guild.get_channel(CONFESSION_LOGS_CHANNEL_ID)

        try:
            embed = discord.Embed(
                title=EMBED_TITLE_DENIED_DM,
                description=f"\"{self.confession_text}\"",
                color=discord.Color.red()
            )
            await self.submitter.send(
                DM_DENIED_PREFIX,
                embed=embed
            )
        except discord.Forbidden:
            pass

        await interaction.response.send_message(MSG_DENIED, ephemeral=True)
        remove_pending_confession(interaction.message.id)
        await interaction.message.delete()

        logembed = discord.Embed(
            title=f"{EMBED_TITLE_DENIED_LOG} (#{self.confession_number})",
            description=f"\"{self.confession_text}\"",
            color=discord.Color.red()
        )
        logembed.add_field(name=FIELD_USER, value=f"||{self.submitter.name} (`{self.submitter.id}`)||")
        logembed.add_field(name=FIELD_DENIED_BY, value=f"{interaction.user.mention}", inline=False)

        await logchannel.send(embed=logembed)

    @discord.ui.button(label=BTN_LABEL_DENY_REASON, style=discord.ButtonStyle.danger, custom_id=CUSTOM_ID_APPROVAL_DENY_REASON)
    async def deny_with_reason(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(DenyReasonModal(
            self.submitter,
            self.confession_text,
            interaction.guild,
            self.confession_number
        ))


class DenyReasonModal(Modal, title=MODAL_TITLE_DENY_REASON):
    reason = TextInput(label=INPUT_LABEL_DENY_REASON, placeholder=INPUT_PLACEHOLDER_DENY_REASON, required=True)

    def __init__(self, submitter, confession_text, guild, confession_number):
        super().__init__()
        self.submitter = submitter
        self.confession_text = confession_text
        self.confession_number = confession_number
        self.guild = guild

    async def on_submit(self, interaction: discord.Interaction):
        logchannel = interaction.guild.get_channel(CONFESSION_LOGS_CHANNEL_ID)

        embed = discord.Embed(
            title=EMBED_TITLE_DENIED_DM,
            description=f"\"{self.confession_text}\"",
            color=discord.Color.red()
        )
        try:
            await self.submitter.send(
                f"{DM_DENIED_WITH_REASON_PREFIX}\n{DM_REASON_HEADER}\n{self.reason.value}",
                embed=embed
            )
        except discord.Forbidden:
            pass

        total_denials = await record_denial_event(
            guild_id=interaction.guild.id,
            user_id=self.submitter.id,
            confession_text=self.confession_text,
            denied_by_name=interaction.user.name,
            reason=self.reason.value
        )

        await interaction.response.send_message(
            f"{MSG_DENIED_WITH_REASON}\n"
            f"This user now has **{total_denials}** denied confession(s).",
            ephemeral=True
        )

        remove_pending_confession(interaction.message.id)
        await interaction.message.delete()

        logembed = discord.Embed(
            title=f"{EMBED_TITLE_DENIED_LOG} (#{self.confession_number})",
            description=f"\"{self.confession_text}\"",
            color=discord.Color.red()
        )
        logembed.add_field(name=FIELD_USER, value=f"||{self.submitter.name} (`{self.submitter.id}`)||")
        logembed.add_field(name=FIELD_DENIED_BY, value=f"{interaction.user.mention}", inline=False)
        logembed.add_field(name=FIELD_REASON, value=f"{self.reason.value}", inline=False)
        await logchannel.send(embed=logembed)


class ConfessionGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="confession", description="Confession Commands")

confession_group = ConfessionGroup()


@confession_group.command(name="submit", description="Post a confession")
async def submit_confession(interaction: discord.Interaction, confession: str):
    confession_number = get_next_confession_number()

    approval_channel = interaction.guild.get_channel(CONFESSION_APPROVAL_CHANNEL_ID)
    if not approval_channel:
        await interaction.response.send_message("Confessions channel not found.", ephemeral=True)
        return

    embed = discord.Embed(
        title=f"{EMBED_TITLE_CONFESSION_AWAITING} (#{confession_number})",
        description=f"\"{confession}\"",
        colour=discord.Color.from_str(COLOR_CONFESSION)
    )
    embed.add_field(name=FIELD_USER, value=f"||{interaction.user.name} (`{interaction.user.id}`)||")

    view = ApprovalView(confession, interaction.user, confession_number)
    approval_message = await approval_channel.send(embed=embed, view=view)

    log_pending_confession(approval_message.id, {
        "confession_text": confession,
        "submitter_id": interaction.user.id,
        "submitter_name": interaction.user.name,
        "confession_number": confession_number,
        "type": "confession",
        "reply_to_message_id": None
    })
    await interaction.response.send_message(MSG_CONFESSION_SUBMITTED_CMD, ephemeral=True)


@confession_group.command(name="reply", description="Reply to a confession")
async def reply_to_confession(interaction: discord.Interaction, message_link: str):
    try:
        parts = message_link.strip().split("/")
        if len(parts) < 3:
            raise ValueError("Invalid link format")

        channel_id = int(parts[-2])
        message_id = int(parts[-1])
    except (ValueError, IndexError):
        await interaction.response.send_message(MSG_INVALID_LINK, ephemeral=True)
        return

    channel = interaction.guild.get_channel(channel_id)
    if not channel:
        await interaction.response.send_message(MSG_CHANNEL_NOT_FOUND_FROM_LINK, ephemeral=True)
        return

    try:
        await channel.fetch_message(message_id)
    except discord.NotFound:
        await interaction.response.send_message(MSG_MESSAGE_NOT_FOUND, ephemeral=True)
        return

    await interaction.response.send_modal(ConfessionReplyModal(message_id))


@confession_group.command(name="denials", description="Displays a user's past denied confessions")
async def denial_log(interaction: discord.Interaction, user: discord.Member):
    async with bot.pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                """
                SELECT denied_by_name, confession_text, reason, timestamp
                FROM confession_denials
                WHERE guild_id = %s AND user_id = %s
                ORDER BY timestamp DESC
                """,
                (interaction.guild.id, user.id)
            )
            records = await cur.fetchall()

    if not records:
        await interaction.response.send_message(
            MSG_NO_DENIALS.format(username=user.name),
            ephemeral=True
        )
        return

    pages = []
    log_tz = ZoneInfo(DENIAL_LOG_TIMEZONE)

    for i in range(0, len(records), DENIALS_PER_PAGE):
        chunk = records[i:i+DENIALS_PER_PAGE]
        description = "\n".join(
            (
                f"**Moderator:** {entry['denied_by_name']}\n"
                f"**Confession:** {entry['confession_text']}\n"
                f"**Reason:** {entry['reason'] or '—'}\n"
                f"*<t:{int(entry['timestamp'].replace(tzinfo=timezone.utc).astimezone(log_tz).timestamp())}:f> {DENIAL_LOG_TZ_LABEL}*\n"
            )
            for entry in chunk
        )

        embed = discord.Embed(
            title=f"{len(records)} denied confession(s) for {user}:",
            description=description,
            color=discord.Color.from_str(COLOR_DENIAL_LOG)
        )
        embed.set_footer(text=f"Page {i//DENIALS_PER_PAGE + 1}/{(len(records)-1)//DENIALS_PER_PAGE + 1}")
        embed.set_author(name=str(user), icon_url=safe_avatar_url(user))
        pages.append(embed)

    view = Pages(pages)
    await interaction.response.send_message(embed=pages[0], view=view, ephemeral=True)


@app_commands.context_menu(name="Reply to Confession")
async def reply_to_confession_context(interaction: discord.Interaction, message: discord.Message):
    await interaction.response.send_modal(ConfessionReplyModal(message.id))
