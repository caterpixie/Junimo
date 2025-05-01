import discord
from discord.ext import commands, tasks
from discord import ui, app_commands
import json
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# Replace these with your actual guild IDs
PIXIE_GUILD_ID = 1322072874214756375
AD_GUILD_ID = 1322423728457384018
GUILD_IDS = [PIXIE_GUILD_ID, AD_GUILD_ID]

# Helper functions
def get_qotd_file(guild_id):
    return f"qotd_{guild_id}.json"

def get_published_file(guild_id):
    return f"published_qotd_{guild_id}.json"

def load_json(filename):
    if not os.path.exists(filename):
        return []
    with open(filename, "r") as file:
        return json.load(file)

def save_json(filename, data):
    with open(filename, "w") as file:
        json.dump(data, file, indent=2)

class Client(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def setup_hook(self):
        for guild_id in GUILD_IDS:
            guild = discord.Object(id=guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)

    async def on_ready(self):
        print(f'Logged on as {self.user}')
        if not auto_post_qotd.is_running():
            auto_post_qotd.start()

# Paginator view
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

# QOTD command group
class QOTDGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="qotd", description="Manage QOTDs")

qotd_group = QOTDGroup()

@qotd_group.command(name="add", description="Adds a QOTD to the queue")
async def add_qotd(interaction: discord.Interaction, question: str):
    guild_id = interaction.guild.id
    qotd_file = get_qotd_file(guild_id)
    qotd = load_json(qotd_file)
    qotd.append({"question": question, "author": interaction.user.name})
    save_json(qotd_file, qotd)
    await interaction.response.send_message(f"Submitted QOTD: {question}", ephemeral=True)

@qotd_group.command(name="post", description="Manually posts the next QOTD")
async def post_qotd(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    qotd_file = get_qotd_file(guild_id)
    published_file = get_published_file(guild_id)
    qotd = load_json(qotd_file)
    if not qotd:
        await interaction.response.send_message("No QOTD in queue, slut")
        return

    next_q = qotd.pop(0)
    save_json(qotd_file, qotd)

    published = load_json(published_file)
    published.append({
        "question": next_q['question'],
        "author": next_q.get("author"),
        "timestamp": datetime.now(ZoneInfo("America/Chicago")).isoformat()
    })
    save_json(published_file, published)

    embed = discord.Embed(title="Question of the Day", description=next_q['question'], color=discord.Color.from_str("#A0EA67"))
    embed.set_footer(text=f"| Author: {next_q['author']} | {len(qotd)} QOTDs left in queue |")

    qotd_role = 1322073121842397226
    await interaction.response.send_message(content=f"<@&{qotd_role}>", embed=embed, allowed_mentions=discord.AllowedMentions(roles=True))

@qotd_group.command(name="view", description="View the list of upcoming QOTDs")
async def view_queue(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    qotd_file = get_qotd_file(guild_id)
    qotd = load_json(qotd_file)
    if not qotd:
        await interaction.response.send_message("QOTD queue empty, fill her up~")
        return

    pages = []
    per_page = 10
    for i in range(0, len(qotd), per_page):
        chunk = qotd[i:i+per_page]
        description = "\n".join(f"**{idx}.** {entry['question']}" for idx, entry in enumerate(chunk, start=i+1))
        embed = discord.Embed(title="Question of the Day Queue", description=description)
        embed.set_footer(text=f"Page {i//per_page + 1}/{(len(qotd)-1)//per_page + 1}")
        pages.append(embed)

    view = Pages(pages)
    await interaction.response.send_message(embed=pages[0], view=view, ephemeral=True)

@qotd_group.command(name="delete", description="Deletes a QOTD by index")
async def delete_qotd(interaction: discord.Interaction, index: int):
    guild_id = interaction.guild.id
    qotd_file = get_qotd_file(guild_id)
    qotd = load_json(qotd_file)

    if index < 1 or index > len(qotd):
        await interaction.response.send_message("Index invalid", ephemeral=True)
        return

    removed = qotd.pop(index - 1)
    save_json(qotd_file, qotd)
    await interaction.response.send_message(f"Removed QOTD #{index}: \"{removed['question']}\" by {removed.get('author')}", ephemeral=True)

@tasks.loop(minutes=1)
async def auto_post_qotd():
    now = datetime.now(ZoneInfo("America/Chicago"))
    if now.hour == 4 and now.minute == 20:
        for guild in bot.guilds:
            qotd_channel = discord.utils.get(guild.text_channels, name="qotd")
            if not qotd_channel:
                continue

            qotd_file = get_qotd_file(guild.id)
            published_file = get_published_file(guild.id)

            qotd = load_json(qotd_file)
            if not qotd:
                continue

            next_q = qotd.pop(0)
            save_json(qotd_file, qotd)

            published = load_json(published_file)
            published.append({
                "question": next_q['question'],
                "author": next_q.get("author"),
                "timestamp": datetime.now(ZoneInfo("America/Chicago")).isoformat()
            })
            save_json(published_file, published)

            embed = discord.Embed(title="Question of the Day", description=next_q['question'], color=discord.Color.from_str("#A0EA67"))
            embed.set_footer(text=f"| Author: {next_q['author']} | {len(qotd)} QOTDs left in queue |")

            qotd_role = 1322073121842397226
            await qotd_channel.send(content=f"<@&{qotd_role}>", embed=embed, allowed_mentions=discord.AllowedMentions(roles=True))

intents = discord.Intents.default()
intents.message_content = True
bot = Client(command_prefix="!", intents=intents)
bot.tree.add_command(qotd_group)

bot.run(os.getenv("DISCORD_TOKEN"))


token = os.getenv("DISCORD_TOKEN")
bot.run(token)
