import discord
from discord import app_commands
from discord.ui import View, Button, Modal, TextInput
import os
import traceback

CONFESSION_CHANNEL=1378213216479477890
CONFESSION_APPROVAL_CHANNEL=1378213253146218557
CONFESSION_LOGS=1378217144223010826

COUNTER_FILE = "confession_counter.txt"
LATEST_CONFESSION_FILE = "latest_confession.txt"

bot = None
def set_bot(bot_instance):
    global bot
    bot = bot_instance

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
        if os.path.exists("pending_confessions.json"):
            with open("pending_confessions.json", "r") as f:
                pending = json.load(f)
        else:
            pending = {}

        pending[str(message_id)] = data

        with open("pending_confessions.json", "w") as f:
            json.dump(pending, f, indent=4)
        print(f"[LOG] Saved pending confession {message_id}")
    except Exception as e:
        print(f"[ERROR] Logging pending confession: {e}")

class ConfessionInteractionView(View):
    def __init__(self, bot_instance):
        super().__init__(timeout=None)
        self.bot = bot_instance

    @discord.ui.button(label="Submit a Confession!", style=discord.ButtonStyle.primary, custom_id="confession_submit")
    async def submit_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(ConfessionSubmitModal())

    @discord.ui.button(label="Reply", style=discord.ButtonStyle.secondary, custom_id="confession_reply")
    async def reply_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(ConfessionReplyModal(interaction.message.id))

class ConfessionSubmitModal(Modal, title="Submit a Confession"):
    confession = TextInput(label="Your Confession", style=discord.TextStyle.paragraph, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        confession_number = get_next_confession_number()
        approval_channel = interaction.guild.get_channel(CONFESSION_APPROVAL_CHANNEL)

        embed = discord.Embed(
            title=f"Confession Awaiting Review (#{confession_number})",
            description=f"\"{self.confession.value}\"",
            colour=discord.Color.from_str("#CD98E7")
        )
        embed.add_field(name="User", value=f"||{interaction.user.name} (`{interaction.user.id}`)||")

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
        await interaction.response.send_message("Your confession has been submitted!", ephemeral=True)

        def log_pending_confession(message_id, data):
            try:
                if os.path.exists("pending_confessions.json"):
                    with open("pending_confessions.json", "r") as f:
                        pending = json.load(f)
                else:
                    pending = {}
        
                pending[str(message_id)] = data
        
                with open("pending_confessions.json", "w") as f:
                    json.dump(pending, f, indent=4)
            except Exception as e:
                print(f"[ERROR] Logging pending confession: {e}")


class ConfessionReplyModal(Modal, title="Reply to a Confession"):
    reply = TextInput(label="Your Reply", style=discord.TextStyle.paragraph, required=True)

    def __init__(self, original_message_id: int):
        super().__init__()
        self.original_message_id = original_message_id

    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.guild.get_channel(CONFESSION_CHANNEL)

        try:
            original = await channel.fetch_message(self.original_message_id)
        except discord.NotFound:
            await interaction.response.send_message("Original confession not found.", ephemeral=True)
            return

        confession_number = get_next_confession_number()
        approval_channel = interaction.guild.get_channel(CONFESSION_APPROVAL_CHANNEL)
        

        embed = discord.Embed(
            title=f"Reply Awaiting Review (#{confession_number})",
            description=f"\"{self.reply.value}\"",
            color=discord.Color.blurple()
        )
        embed.add_field(name="User", value=f"||{interaction.user.name} (`{interaction.user.id}`)||")
        embed.add_field(name="Original Message", value=f"[Jump to message](https://discord.com/channels/{interaction.guild.id}/{channel.id}/{self.original_message_id})", inline=False)

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
        await interaction.response.send_message("Your reply has been submitted!", ephemeral=True)

        
        def log_pending_confession(message_id, data):
            try:
                if os.path.exists("pending_confessions.json"):
                    with open("pending_confessions.json", "r") as f:
                        pending = json.load(f)
                else:
                    pending = {}
        
                pending[str(message_id)] = data
        
                with open("pending_confessions.json", "w") as f:
                    json.dump(pending, f, indent=4)
            except Exception as e:
                print(f"[ERROR] Logging pending confession: {e}")

class ApprovalView(View):
    def __init__(self, confession_text, submitter, confession_number, type="confession", reply_to_message_id=None):
        super().__init__(timeout=None)
        self.confession_text = confession_text
        self.confession_number = confession_number
        self.submitter = submitter
        self.type = type
        self.reply_to_message_id = reply_to_message_id

    @discord.ui.button(label="✅ Approve", style=discord.ButtonStyle.success, custom_id="approval_approve")
    async def approve(self, interaction: discord.Interaction, button: Button):
        channel = interaction.guild.get_channel(CONFESSION_CHANNEL)
        logchannel = interaction.guild.get_channel(CONFESSION_LOGS)

        if self.type == "reply":
            jump_url = f"https://discord.com/channels/{interaction.guild.id}/{channel.id}/{self.reply_to_message_id}"
            embed = discord.Embed(
                title=f"Anonymous Reply (#{self.confession_number})",
                description=f"\"{self.confession_text}\"\n",
                color=discord.Color.from_str("#E9CAF8")
            )
            embed.add_field(name="Original Confession", value=f"[Jump to confession]({jump_url})", inline=False)
        else:
            embed = discord.Embed(
                title=f"Anonymous Confession (#{self.confession_number})",
                description=f"\"{self.confession_text}\"",
                color=discord.Color.from_str("#CD98E7")
            )

        new_message = await channel.send(embed=embed, view=ConfessionInteractionView(bot))


        # Remove old buttons
        last_message_id = get_latest_confession_id()
        if last_message_id:
            try:
                old_message = await channel.fetch_message(last_message_id)
                await old_message.edit(view=None)
            except discord.NotFound:
                pass
                
        set_latest_confession_id(new_message.id)

        await interaction.response.send_message("Approved and posted!", ephemeral=True)
        remove_pending_confession(interaction.message.id)
        await interaction.message.delete()

        logembed = discord.Embed(
            title=f"{'Reply' if self.type == 'reply' else 'Confession'} Approved (#{self.confession_number})",
            description=f"\"{self.confession_text}\"",
            color=discord.Color.green()
        )
        logembed.add_field(name="User", value=f"||{self.submitter.name} (`{self.submitter.id}`)||")
        logembed.add_field(name="Approved By", value=f"{interaction.user.mention}", inline=False)

        await logchannel.send(embed=logembed)
        
        # Remove from JSON
        def remove_pending_confession(message_id):
            try:
                if os.path.exists("pending_confessions.json"):
                    with open("pending_confessions.json", "r") as f:
                        pending = json.load(f)
                    if str(message_id) in pending:
                        del pending[str(message_id)]
                        with open("pending_confessions.json", "w") as f:
                            json.dump(pending, f, indent=4)
            except Exception as e:
                print(f"[ERROR] Removing pending confession: {e}")

    @discord.ui.button(label="❌ Deny", style=discord.ButtonStyle.danger, custom_id="approval_deny")
    async def deny(self, interaction: discord.Interaction, button: Button):
        logchannel = interaction.guild.get_channel(CONFESSION_LOGS)
        await interaction.response.send_message("Confession denied.", ephemeral=True)
        remove_pending_confession(interaction.message.id)
        await interaction.message.delete()

        logembed = discord.Embed(
            title=f"Confession Denied (#{self.confession_number})",
            description=f"\"{self.confession_text}\"",
            color=discord.Color.red()
        )
        logembed.add_field(name="User", value=f"||{self.submitter.name} (`{self.submitter.id}`)||")
        logembed.add_field(name="Denied By", value=f"{interaction.user.mention}", inline=False)

        await logchannel.send(embed=logembed)

    @discord.ui.button(label="💬 Deny with Reason", style=discord.ButtonStyle.danger, custom_id="approval_denyreason")
    async def deny_with_reason(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(DenyReasonModal(self.submitter, self.confession_text, interaction.guild, self.confession_number))

        # Remove from JSON
        def remove_pending_confession(message_id):
            try:
                if os.path.exists("pending_confessions.json"):
                    with open("pending_confessions.json", "r") as f:
                        pending = json.load(f)
                    if str(message_id) in pending:
                        del pending[str(message_id)]
                        with open("pending_confessions.json", "w") as f:
                            json.dump(pending, f, indent=4)
            except Exception as e:
                print(f"[ERROR] Removing pending confession: {e}")


class DenyReasonModal(Modal, title="Deny Confession with Reason"):
    reason = TextInput(label="Reason", placeholder="Why is this being denied?", required=True)

    def __init__(self, submitter, confession_text, guild, confession_number):
        super().__init__()
        self.submitter = submitter
        self.confession_text = confession_text
        self.confession_number = confession_number
        self.guild = guild

    async def on_submit(self, interaction: discord.Interaction):
        logchannel = interaction.guild.get_channel(CONFESSION_LOGS)
        embed = discord.Embed(
            title="Your Denied Confession",
            description=f"\"{self.confession_text}\"",
            color=discord.Color.red()
        )
        try:
            await self.submitter.send(
                f"Your confession in After Dark was denied.\n**Reason:**\n{self.reason.value}",
                embed=embed
            )
        except discord.Forbidden:
            pass  # DMs are closed

        await interaction.response.send_message("Confession has been denied with reason.", ephemeral=True)
        remove_pending_confession(interaction.message.id)
        await interaction.message.delete()

        logembed = discord.Embed(
            title=f"Confession Denied (#{self.confession_number})",
            description=f"\"{self.confession_text}\"",
            color=discord.Color.red()
        )
        logembed.add_field(name="User", value=f"||{self.submitter.name} (`{self.submitter.id}`)||")
        logembed.add_field(name="Denied By", value=f"{interaction.user.mention}", inline=False)
        logembed.add_field(name="Reason", value=f"{self.reason.value}", inline=False)

        await logchannel.send(embed=logembed)

        # Remove from JSON
        def remove_pending_confession(message_id):
            try:
                if os.path.exists("pending_confessions.json"):
                    with open("pending_confessions.json", "r") as f:
                        pending = json.load(f)
                    if str(message_id) in pending:
                        del pending[str(message_id)]
                        with open("pending_confessions.json", "w") as f:
                            json.dump(pending, f, indent=4)
            except Exception as e:
                print(f"[ERROR] Removing pending confession: {e}")


class ConfessionGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="confession", description="Confession Commands")

confession_group = ConfessionGroup()

@confession_group.command(name="submit", description="Post a confession")
async def submit_confession(interaction: discord.Interaction, confession: str):
    confession_number = get_next_confession_number()

    approval_channel = interaction.guild.get_channel(CONFESSION_APPROVAL_CHANNEL)
    if not approval_channel:
        await interaction.response.send_message("Confessions channel not found.", ephemeral=True)
        return
    
    embed = discord.Embed(
        title=f"Confession Awaiting Review (#{confession_number})",
        description=f"\"{confession}\"",
        colour=discord.Color.from_str("#CD98E7")
    )
    embed.add_field(name="User", value=f"||{interaction.user.name} (`{interaction.user.id}`)||")

    view = ApprovalView(confession, interaction.user, confession_number)
    await approval_channel.send(embed=embed, view=view)
    await interaction.response.send_message("Confession submitted!", ephemeral=True)

@confession_group.command(name="reply", description="Reply to a confession")
async def reply_to_confession(interaction: discord.Interaction, message_link: str):
    try:
        parts = message_link.strip().split("/")
        if len(parts) < 3:
            raise ValueError("Invalid link format")

        channel_id = int(parts[-2])
        message_id = int(parts[-1])
    except (ValueError, IndexError):
        await interaction.response.send_message("Invalid message link. Please make sure it's a valid Discord message URL.", ephemeral=True)
        return

    channel = interaction.guild.get_channel(channel_id)
    if not channel:
        await interaction.response.send_message("Could not find the channel from that link.", ephemeral=True)
        return

    try:
        await channel.fetch_message(message_id)
    except discord.NotFound:
        await interaction.response.send_message("Message not found. Make sure the link is from this server.", ephemeral=True)
        return

    await interaction.response.send_modal(ConfessionReplyModal(message_id))

@app_commands.context_menu(name="Reply to Confession")
async def reply_to_confession_context(interaction: discord.Interaction, message: discord.Message):
    await interaction.response.send_modal(ConfessionReplyModal(message.id))
