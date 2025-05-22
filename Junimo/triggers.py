import json
import discord
import aiomysql
from datetime import datetime

bot = None
def set_bot(bot_instance):
    global bot
    bot = bot_instance

    @bot.event
    async def on_message(message: discord.Message):
        if message.author.bot or not message.guild:
            return

        async with bot.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("""
                    SELECT trigger_text, response_type, response_text FROM triggers
                    WHERE guild_id = %s
                """, (message.guild.id,))
                rows = await cur.fetchall()

        content = message.content.lower()
        for row in rows:
            trigger_text = row["trigger_text"].lower()
            if trigger_text in content:
                if row["response_type"] == "plain":
                    await message.channel.send(row["response_text"])

                elif row["response_type"] == "random":
                    try:
                        options = json.loads(row["response_text"])
                        if isinstance(options, list) and options:
                            await message.channel.send(random.choice(options))
                        else:
                            await message.channel.send("No valid links available.")
                    except json.JSONDecodeError:
                        await message.channel.send("Invalid random link list.")
                        
                elif row["response_type"] == "embed":
                    try:
                        embed_data = json.loads(row["response_text"])
                    except json.JSONDecodeError:
                        await message.channel.send("Invalid embed format.")
                        return

                    embed = discord.Embed(
                        title=embed_data.get("title"),
                        description=embed_data.get("description"),
                        color=discord.Color.from_str("#C8FF99"),
                        url=embed_data.get("url")
                    )

                    # Timestamp
                    if "timestamp" in embed_data:
                        try:
                            embed.timestamp = datetime.fromisoformat(embed_data["timestamp"])
                        except Exception:
                            pass 

                    # Author block
                    if "author" in embed_data:
                        author = embed_data["author"]
                        if isinstance(author, dict):
                            embed.set_author(
                                name=author.get("name", ""),
                                url=author.get("url"),
                                icon_url=author.get("icon_url")
                            )
                        else:
                            embed.set_author(name=str(author))

                    # Footer block
                    if "footer" in embed_data:
                        footer = embed_data["footer"]
                        if isinstance(footer, dict):
                            embed.set_footer(
                                text=footer.get("text", ""),
                                icon_url=footer.get("icon_url")
                            )
                        else:
                            embed.set_footer(text=str(footer))

                    # Thumbnail and image
                    if "thumbnail" in embed_data:
                        embed.set_thumbnail(url=embed_data["thumbnail"])
                    if "image" in embed_data:
                        embed.set_image(url=embed_data["image"])

                    # Fields
                    if "fields" in embed_data:
                        for field in embed_data["fields"]:
                            embed.add_field(
                                name=field.get("name", "—"),
                                value=field.get("value", "—"),
                                inline=field.get("inline", False)
                            )

                    await message.channel.send(embed=embed)
                break
