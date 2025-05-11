import discord

bot = None
def set_bot(bot_instance):
    global bot
    bot = bot_instance

    @bot.event
    async def on_message(message):
        if message.author.bot:
            return

        triggers = await bot.pool.fetch(
            "SELECT trigger_text, response_text FROM triggers WHERE guild_id = $1",
            message.guild.id
        )

        for trigger in triggers:
            if trigger["trigger_text"] in message.content.lower():
                await message.channel.send(trigger["response_text"])
                break

        await bot.process_commands(message)
