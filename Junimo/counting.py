import discord
import asyncio
import json
import os

COUNTING_CHANNEL_ID = 1322430337132789851
LOSER_ROLE_ID = 1332969280165384254    
MILESTONES = [10, 50, 100, 150, 200, 300, 400, 500, 1000, 1500, 2000, 2500]
FUNNY_NUMBERS = [69, 420, 666, 8008]
DATA_FILE = "counting_data.json"

bot = None
current_count = 0
last_user_id = None


def load_count_data():
    global current_count, last_user_id
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                content = f.read().strip()
                if not content:
                    raise ValueError("Empty DATA_FILE")
                data = json.loads(content)
                current_count = data.get("current_count", 0)
                last_user_id = data.get("last_user_id", None)
        except (json.JSONDecodeError, ValueError):
            print("Warning: current_count.json is empty or invalid. Resetting count.")
            current_count = 0
            last_user_id = None
            save_count_data()  # Create a fresh DATA_FILE
    else:
        current_count = 0
        last_user_id = None
        save_count_data()  # Create a fresh DATA_FILE

def save_count_data():
    with open(DATA_FILE, "w") as f:
        json.dump({"current_count": current_count, "last_user_id": last_user_id}, f)


async def counting_on_message(message: discord.Message):
    global current_count, last_user_id

    if message.author.bot or message.channel.id != COUNTING_CHANNEL_ID:
        return

    guild = message.guild
    loser_role = guild.get_role(LOSER_ROLE_ID)

    # Parse number
    try:
        number = int(message.content.strip())
    except ValueError:
        if not message.author.bot:
            await message.delete()
        return

    # Check validity (increment of one, no double entries)
    if number == current_count + 1 and message.author.id != last_user_id:
        current_count = number
        last_user_id = message.author.id
        save_count_data()

        if number in FUNNY_NUMBERS:
            embed = discord.Embed(
                title=f"Funny Number: {number}",
                description="Nice.",
                color=discord.Color.from_str("#99FCFF")
            )
            await message.channel.send(embed=embed, allowed_mentions=discord.AllowedMentions(roles=True))
            triggermsg = await message.channel.send("!zliwpj")
            await triggermsg.delete()

        elif number == 3000:
            embed = discord.Embed(
                title=f"Milestone Reached: {number}",
                description=f"{message.author.mention} reached a milestone! This is your last milestone — this counting channel has gotten out of hand you nerds.",
                color=discord.Color.from_str("#99FCFF")
            )
            await message.channel.send(embed=embed, allowed_mentions=discord.AllowedMentions(roles=True))
            triggermsg = await message.channel.send("!zliwpj")
            await triggermsg.delete()

        elif number in MILESTONES:
            embed = discord.Embed(
                title=f"Milestone Reached: {number}",
                description=f"{message.author.mention} reached a milestone! Here's a dopamine hit for knowing how to count I guess.",
                color=discord.Color.from_str("#99FCFF")
            )
            await message.channel.send(embed=embed, allowed_mentions=discord.AllowedMentions(roles=True))
            triggermsg = await message.channel.send("!zliwpj")
            await triggermsg.delete()
        
    else:
        # Wrong number
        await message.delete()
        embed = discord.Embed(
            title="Counting Reset",
            description=f"{message.author.mention} messed up the count at **{current_count}** and has been given the {loser_role.mention} role! The count has been reset to **0**.",
            color=discord.Color.from_str("#99FCFF")
        )
        await message.channel.send(embed=embed, allowed_mentions=discord.AllowedMentions(roles=True))
        current_count = 0
        last_user_id = None
        save_count_data()

        # Add loser role
        if loser_role:
            await message.author.add_roles(loser_role)
            await asyncio.sleep(300)  # 5 minutes
            await message.author.remove_roles(loser_role)

def set_bot(bot_instance):
    global bot
    bot = bot_instance
    load_count_data()  # Load data on startup
    bot.add_listener(counting_on_message, "on_message")
