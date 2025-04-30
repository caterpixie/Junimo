import discord
from discord.ext import commands, tasks
from discord import ui, app_commands
import json
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


QOTD_FILE = "qotd.json"
PUBLISHED_FILE = "published_qotd.json"

GUILD_ID = discord.Object(id=1322072874214756375)

def load_qotd():
    if not os.path.exists(QOTD_FILE):
        return []
    
    with open(QOTD_FILE, "r") as file:
        return json.load(file)
    
def save_qotd(qotd):
    with open(QOTD_FILE, "w") as file:
        json.dump(qotd, file, indent=2)

def load_published():
    if not os.path.exists(PUBLISHED_FILE):
        return []
    
    with open(PUBLISHED_FILE, "r") as file:
        return json.load(file)
    
def save_published(published):
    with open(PUBLISHED_FILE, "w") as file:
        json.dump(published, file, indent=2)

class Client(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.synced = False

    async def on_ready(self):
        print(f'Logged on as {self.user}')

        if not self.synced:
            try:
                guild = discord.Object(id=1322072874214756375)

                synced = await self.tree.sync(guild=guild)
                print(f'Synced {len(synced)} commands to guild {guild.id}')
                self.synced = True

            except Exception as e:
                print(f'Error syncing commands: {e}')
        
        auto_post_qotd.start()

# Lets embeds have several pages
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

intents = discord.Intents.default()
intents.message_content = True
bot = Client(command_prefix="!", intents=intents)

# slash commands
@bot.tree.command(name="addqotd", description="Adds a QOTD to the queue", guild=GUILD_ID)
async def add_qotd(interaction: discord.Interaction, question: str):
    qotd = load_qotd()
    qotd.append({
        "question": question,
        "author": interaction.user.name
    })
    save_qotd(qotd)

    await interaction.response.send_message("<:pleh:1362947686936084590> QOTD submitted!" )

@bot.tree.command(name="postqotd", description="Manually posts the next QOTD", guild=GUILD_ID)
async def post_qotd(interaction: discord.Interaction):
    qotd = load_qotd()
    if not qotd:
        await interaction.response.send_message("No QOTD in queue, slut")
        return
    
    next = qotd.pop(0)
    save_qotd(qotd)

    # logging
    published = load_published()
    published.append({
        "question": next['question'],
        "author": next.get("author"),
        "timestamp": datetime.now(ZoneInfo("America/Chicago")).isoformat()
    })
    save_published(published)

    qotd_role = 1322073121842397226

    embed = discord.Embed(title="Question of the Day", description=next['question'], color=discord.Color.from_str("#A0EA67"))
    embed.set_footer(text=f"| Author: {next['author']} | {len(qotd)} QOTDs left in queue |")

    await interaction.response.send_message(content=f"<@&{qotd_role}>", embed=embed, allowed_mentions=discord.AllowedMentions(roles=True))

@bot.tree.command(name="viewqueue", description="View the list of upcoming QOTDs", guild=GUILD_ID)
async def view_queue(interaction: discord.Interaction):
    qotd = load_qotd()
    if not qotd:
        await interaction.response.send_message("QOTD queue empty, fill her up~")
        return

    # splitting into pages of 10 QOTDs
    pages = []
    per_page = 10
    for i in range(0, len(qotd), per_page):
        chunk = qotd[i:i+per_page]
        description = ""
        for idx, entry in enumerate(chunk, start=i+1):
            description += f"**{idx}.** {entry['question']}\n"
        
        embed = discord.Embed(title="Question of the Day Queue", description=description)
        embed.set_footer(text=f"Page {i//per_page + 1}/{(len(qotd)-1)//per_page + 1}")
        pages.append(embed)

    view = Pages(pages)

    await interaction.response.send_message(embed=pages[0], view=view, ephemeral=True)

@bot.tree.command(name="deleteqotd", description="Deletes a QOTD in the queue by index #", guild=GUILD_ID)
async def delete_qotd(interaction: discord.Interaction, index: int):
    qotd = load_qotd()

    if index < 1 or index > len(qotd):
        await interaction.response.send_message("Index Invalid", ephemeral=True)
        return
    
    removed = qotd.pop(index -1)
    save_qotd(qotd)

    await interaction.response.send_message(f"Removed QOTD #{index}: \"{removed['question']}\" by {removed.get('author')}", ephemeral=True)

@tasks.loop(minutes=1)
async def auto_post_qotd():
    now = datetime.now(ZoneInfo("America/Chicago")) # CST Timezone (DST Handled)
    if now.hour == 4 and now.minute == 20:
        qotd_channel = bot.get_channel(1365204628253442048)
        qotd = load_qotd()
        if not qotd:
            return
        
        next = qotd.pop(0)
        save_qotd(qotd)

        published = load_published()
        published.append({
            "question": next['question'],
            "author": next.get("author"),
            "timestamp": datetime.now(ZoneInfo("America/Chicago")).isoformat()
        })

        save_published(published)

        qotd_role = 1322073121842397226

        embed = discord.Embed(title="Question of the Day", description=next['question'], color=discord.Color.from_str("#A0EA67"))
        embed.set_footer(text=f"| Author: {next['author']} | {len(qotd)} QOTDs left in queue |")

        await qotd_channel.send(content=f"<@&{qotd_role}>", embed=embed, allowed_mentions=discord.AllowedMentions(roles=True))

token = os.getenv("DISCORD_TOKEN")
bot.run(token)
