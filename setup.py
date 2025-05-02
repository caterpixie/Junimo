import discord
from discord import app_commands

bot = None
def set_bot(bot_instance):
    global bot
    bot = bot_instance

@app_commands.command(name="setup_chores", description="One-time setup to create chores table")
async def setup_chores(interaction: discord.Interaction):
    await bot.pool.execute("""
        CREATE TABLE IF NOT EXISTS chores (
            id SERIAL PRIMARY KEY,
            guild_id BIGINT NOT NULL,
            description TEXT NOT NULL,
            frequency TEXT CHECK (frequency IN ('weekly', 'biweekly', 'monthly')),
            author TEXT,
            last_posted TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE
        );
    """)
    await interaction.response.send_message("Chores table created or already exists.", ephemeral=True)

@app_commands.command(name="delete_chores_table", description="Deletes the chores table (dev only!)")
async def delete_chores_table(interaction: discord.Interaction):
    await bot.pool.execute("DROP TABLE IF EXISTS chores;")
    await interaction.response.send_message("⚠️ Chores table deleted.", ephemeral=True)
