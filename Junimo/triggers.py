import discord
import aiomysql

bot = None
def set_bot(bot_instance):
    global bot
    bot = bot_instance

    @bot.event
    async def on_message(message):
        if message.author.bot:
            return
    
        async with bot.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    "SELECT trigger_text, response_text FROM triggers WHERE guild_id = %s",
                    (message.guild.id,)
                )
                triggers = await cur.fetchall()
    
        for trigger in triggers:
            if trigger["trigger_text"] in message.content.lower():
                await message.channel.send(trigger["response_text"])
                break
    
        await bot.process_commands(message)
