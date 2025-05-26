import discord
from discord.ext import tasks
from discord import app_commands, ui
from datetime import datetime
from zoneinfo import ZoneInfo
import aiomysql
import os
import urllib.parse

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

class QOTDReplyModal(ui.Modal, title="Reply to QOTD"):
    def __init__(self, qotd_text, forward_channel_id):
        super().__init__()
        self.qotd_text = qotd_text
        self.forward_channel_id = forward_channel_id
        self.response = ui.TextInput(label="Your Answer", style=discord.TextStyle.paragraph, required=True, max_length=1000)
        self.add_item(self.response)

    async def on_submit(self, interaction: discord.Interaction):
        forward_channel = bot.get_channel(self.forward_channel_id)
        if forward_channel:
            embed = discord.Embed(
                title=f"{self.qotd_text}",
                description=f"{self.response.value}",
                color=discord.Color.from_str("#A0EA67")
            )
            embed.set_author(name=str(interaction.user.display_name), icon_url=interaction.user.display_avatar.url)
            
            await forward_channel.send(embed=embed)
            await interaction.response.send_message("Your reply has been submitted!", ephemeral=True)
        else:
            await interaction.response.send_message("Failed to find the response channel.", ephemeral=True)

class QOTDView(ui.View):
    def __init__(self, question: str, forward_channel_id: int):
        super().__init__(timeout=None)
        self.question = question
        self.forward_channel_id = forward_channel_id

    @ui.button(label="Reply", style=discord.ButtonStyle.primary, custom_id="qotd_reply")
    async def reply_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(
            QOTDReplyModal(self.question, self.forward_channel_id)
        )


class QOTDGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="qotd", description="Manage QOTDs")

qotd_group = QOTDGroup()

@qotd_group.command(name="add", description="Adds a QOTD to the queue")
async def add_qotd(interaction: discord.Interaction, question: str, image: discord.Attachment = None):
    async with bot.pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO qotds (guild_id, question, author, is_published, image_url) VALUES (%s, %s, %s, FALSE, %s)",
                (interaction.guild.id, question, interaction.user.name, image.url if image else None)
            )
    await interaction.response.send_message(f"Submitted QOTD: {question}", ephemeral=True)

@qotd_group.command(name="post", description="Manually post QOTD (Only use in #of-the-day)")
async def post_qotd(interaction: discord.Interaction):
    async with bot.pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT * FROM qotds WHERE guild_id = %s AND is_published = FALSE ORDER BY id ASC LIMIT 1",
                (interaction.guild.id,)
            )
            record = await cur.fetchone()
            if not record:
                await interaction.response.send_message("No QOTD in queue, slut", ephemeral=True)
                return

            await cur.execute("UPDATE qotds SET is_published = TRUE WHERE id = %s", (record["id"],))

            await cur.execute(
                "SELECT COUNT(*) AS count FROM qotds WHERE guild_id = %s AND is_published = FALSE",
                (interaction.guild.id,)
            )
            count = (await cur.fetchone())["count"]

    embed = discord.Embed(title="Question of the Day", description=record["question"], color=discord.Color.from_str("#A0EA67"))
    if record.get("image_url"):
        embed.set_image(url=record["image_url"])
    embed.set_footer(text=f"| Author: {record['author']} | {count} QOTDs left in queue |")

    qotd_role = 1322427477053669406
    forward_channel_id = 1322430254534361089
    view = QOTDView(record["question"], forward_channel_id)
    await interaction.response.send_message(content=f"<@&{qotd_role}>", embed=embed, view=view, allowed_mentions=discord.AllowedMentions(roles=True))

@qotd_group.command(name="view", description="View the list of upcoming QOTDs")
async def view_queue(interaction: discord.Interaction):
    async with bot.pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT * FROM qotds WHERE guild_id = %s AND is_published = FALSE ORDER BY id ASC",
                (interaction.guild.id,)
            )
            records = await cur.fetchall()

    if not records:
        await interaction.response.send_message("QOTD queue empty, fill her up~", ephemeral=True)
        return

    per_page = 10
    pages = []
    for i in range(0, len(records), per_page):
        chunk = records[i:i+per_page]
        description = "\n".join(f"**{idx}.** {entry['question']}" for idx, entry in enumerate(chunk, start=i+1))
        embed = discord.Embed(title="Question of the Day Queue", description=description)
        embed.set_footer(text=f"Page {i//per_page + 1}/{(len(records)-1)//per_page + 1}")
        pages.append(embed)

    view = Pages(pages)
    await interaction.response.send_message(embed=pages[0], view=view, ephemeral=True)

@qotd_group.command(name="delete", description="Deletes a QOTD by index")
async def delete_qotd(interaction: discord.Interaction, index: int):
    async with bot.pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT id, question, author FROM qotds WHERE guild_id = %s AND is_published = FALSE ORDER BY id ASC",
                (interaction.guild.id,)
            )
            records = await cur.fetchall()

            if index < 1 or index > len(records):
                await interaction.response.send_message("Index invalid", ephemeral=True)
                return

            target = records[index - 1]
            await cur.execute("DELETE FROM qotds WHERE id = %s", (target["id"],))

    await interaction.response.send_message(f"Removed QOTD #{index}: \"{target['question']}\" by {target['author']}", ephemeral=True)

@tasks.loop(minutes=1)
async def auto_post_qotd():
    now = datetime.now(ZoneInfo("America/Chicago"))
    if now.hour == 15 and now.minute == 20:
        for guild in bot.guilds:
            qotd_channel = guild.get_channel(1322429106868191283)
            if not qotd_channel:
                continue

            async with bot.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(
                        "SELECT * FROM qotds WHERE guild_id = %s AND is_published = FALSE ORDER BY id ASC LIMIT 1",
                        (guild.id,)
                    )
                    record = await cur.fetchone()
                    if not record:
                        continue

                    await cur.execute("UPDATE qotds SET is_published = TRUE WHERE id = %s", (record["id"],))

                    await cur.execute(
                        "SELECT COUNT(*) AS count FROM qotds WHERE guild_id = %s AND is_published = FALSE",
                        (guild.id,)
                    )
                    count = (await cur.fetchone())["count"]

            embed = discord.Embed(title="Question of the Day", description=record["question"], color=discord.Color.from_str("#A0EA67"))
            if record.get("image_url"):
                embed.set_image(url=record["image_url"])
            embed.set_footer(text=f"| Author: {record['author']} | {count} QOTDs left in queue |")
        
            qotd_role = 1322427477053669406
            forward_channel_id = 1322430254534361089
            view = QOTDView(record["question"], forward_channel_id)
            await qotd_channel.send(content=f"<@&{qotd_role}>", embed=embed, view=view, allowed_mentions=discord.AllowedMentions(roles=True))
