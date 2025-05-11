import discord
import aiosql

bot = None
def set_bot(bot_instance):
    global bot
    bot = bot_instance

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    async with bot.pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT trigger_text, response_type, response_text FROM triggers
                WHERE guild_id = %s
            """, (message.guild.id,))
            rows = await cur.fetchall()

    content = message.content.lower()
    for trigger_text, response_type, response_text in rows:
        if trigger_text.lower() in content:
            if response_type == 'plain':
                await message.channel.send(response_text)
            elif response_type == 'embed':
                embed = discord.Embed(description=response_text, color=discord.Color.purple())
                await message.channel.send(embed=embed)
            break
