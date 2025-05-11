import json
import discord
import aiomysql

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
                elif row["response_type"] == "embed":
                    try:
                        embed_data = json.loads(row["response_text"])
                    except json.JSONDecodeError:
                        await message.channel.send("Invalid embed format.")
                        return
                        
                    embed = discord.Embed(
                        title=embed_data.get("title"),
                        description=embed_data.get("description"),
                        color=discord.Color.from_str("#C8FF99")
                    )
                        
                    if "image" in embed_data:
                        embed.set_image(url=embed_data["image"])
                    if "footer" in embed_data:
                        embed.set_footer(text=embed_data["footer"])
                    if "thumbnail" in embed_data:
                        embed.set_thumbnail(url=embed_data["thumbnail"])
                    if "author" in embed_data:
                        embed.set_author(name=embed_data["author"])
    
                    await message.channel.send(embed=embed)
                break
