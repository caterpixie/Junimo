
import discord
from discord.ext import commands, tasks
from discord import ui, app_commands
import asyncpg
import os
from datetime import datetime
from zoneinfo import ZoneInfo

PIXIE_GUILD_ID = 1322072874214756375
AD_GUILD_ID = 1322423728457384018
GUILD_IDS = [PIXIE_GUILD_ID, AD_GUILD_ID]

class Client(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pool = None

    async def setup_hook(self):
        self.pool = await asyncpg.create_pool(os.getenv("DATABASE_URL"))
        await self.tree.sync()

    async def on_ready(self):
        print(f'Logged on as {self.user}')
        if not auto_post_qotd.is_running():
            auto_post_qotd.start()

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

class QOTDGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="qotd", description="Manage QOTDs")

qotd_group = QOTDGroup()

@qotd_group.command(name="add", description="Adds a QOTD to the queue")
async def add_qotd(interaction: discord.Interaction, question: str):
    await bot.pool.execute(
        "INSERT INTO qotds (guild_id, question, author, is_published) VALUES ($1, $2, $3, FALSE)",
        interaction.guild.id, question, interaction.user.name
    )
    await interaction.response.send_message(f"Submitted QOTD: {question}", ephemeral=True)

@qotd_group.command(name="post", description="Manually posts the next QOTD")
async def post_qotd(interaction: discord.Interaction):
    record = await bot.pool.fetchrow(
        "SELECT * FROM qotds WHERE guild_id = $1 AND is_published = FALSE ORDER BY id ASC LIMIT 1",
        interaction.guild.id
    )
    if not record:
        await interaction.response.send_message("No QOTD in queue, slut")
        return

    await bot.pool.execute("UPDATE qotds SET is_published = TRUE WHERE id = $1", record["id"])

    count = await bot.pool.fetchval(
        "SELECT COUNT(*) FROM qotds WHERE guild_id = $1 AND is_published = FALSE",
        interaction.guild.id
    )

    embed = discord.Embed(title="Question of the Day", description=record["question"], color=discord.Color.from_str("#A0EA67"))
    embed.set_footer(text=f"| Author: {record['author']} | {count} QOTDs left in queue |")

    qotd_role = 1322073121842397226
    await interaction.response.send_message(content=f"<@&{qotd_role}>", embed=embed, allowed_mentions=discord.AllowedMentions(roles=True))

@qotd_group.command(name="view", description="View the list of upcoming QOTDs")
async def view_queue(interaction: discord.Interaction):
    records = await bot.pool.fetch(
        "SELECT * FROM qotds WHERE guild_id = $1 AND is_published = FALSE ORDER BY id ASC",
        interaction.guild.id
    )
    if not records:
        await interaction.response.send_message("QOTD queue empty, fill her up~")
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
    records = await bot.pool.fetch(
        "SELECT id, question, author FROM qotds WHERE guild_id = $1 AND is_published = FALSE ORDER BY id ASC",
        interaction.guild.id
    )
    if index < 1 or index > len(records):
        await interaction.response.send_message("Index invalid", ephemeral=True)
        return

    target = records[index - 1]
    await bot.pool.execute("DELETE FROM qotds WHERE id = $1", target["id"])
    await interaction.response.send_message(f"Removed QOTD #{index}: \"{target['question']}\" by {target['author']}", ephemeral=True)

@tasks.loop(minutes=1)
async def auto_post_qotd():
    now = datetime.now(ZoneInfo("America/Chicago"))
    if now.hour == 4 and now.minute == 20:
        for guild in bot.guilds:
            qotd_channel = discord.utils.get(guild.text_channels, name="qotd")
            if not qotd_channel:
                continue

            record = await bot.pool.fetchrow(
                "SELECT * FROM qotds WHERE guild_id = $1 AND is_published = FALSE ORDER BY id ASC LIMIT 1",
                guild.id
            )
            if not record:
                continue

            await bot.pool.execute("UPDATE qotds SET is_published = TRUE WHERE id = $1", record["id"])

            count = await bot.pool.fetchval(
                "SELECT COUNT(*) FROM qotds WHERE guild_id = $1 AND is_published = FALSE",
                guild.id
            )

            embed = discord.Embed(title="Question of the Day", description=record["question"], color=discord.Color.from_str("#A0EA67"))
            embed.set_footer(text=f"| Author: {record['author']} | {count} QOTDs left in queue |")

            qotd_role = 1322073121842397226
            await qotd_channel.send(content=f"<@&{qotd_role}>", embed=embed, allowed_mentions=discord.AllowedMentions(roles=True))

intents = discord.Intents.default()
intents.message_content = True
bot = Client(command_prefix="!", intents=intents)
bot.tree.add_command(qotd_group)

bot.run(os.getenv("DISCORD_TOKEN"))
