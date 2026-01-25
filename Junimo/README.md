# Junimo

Junimo is a Discord bot created for the AD server. Its current features include:
- A Question of the Day (QOTD) system
- Starboard
- A counting channel with rewards + penalties
- A chore of the day reminder system
- Text triggers
- An `/uwu` command

Many features of this bot are hardcoded as it is only meant for use within the AD server. This README will detail what all the features do as well as the basics on how to edit these hardcoded features.

## QOTD System
- `/qotd add <question> [image]`: Adds a question to the queue.
- `/qotd post`: Manually posts the next question in queue. Note that this is posted in the channel in which it is called, and must therefore be called in the #of-the-day channel
- `/qotd view`: Lists the upcoming questions in the queue, indexed.
- `/qotd delete <index>`: Deletes a question in the queue. Takes the int input of "index" based on its position in `/qotd view`

This bot posts chores automatically at 4:20AM CST. **This is a hardcoded element**  
Chores are posted to the #of-the-day channel in the AD server. **This channel ID is a hardcoded element**

### Chore of the Day System
- `add_chore`: Adds a chore to the `chore` database. This command is not called in the `main.py` file as it was only used for the setup of the database. However it is kept in the files in the case that this feed needs to be edited or re-made.

Posting is done through the Junimaid webhook for the #of-the-day server in an embed. **The webhook URL is hardcoded in the .env file**  
Chores are stored in the `chore` database.

### Misc Commands
- `/uwu`: Takes in text input and UwU-ifies it

## Databases
`qotds`
```sql
CREATE TABLE qotds (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT,
    question TEXT,
    author TEXT,
    is_published BOOLEAN DEFAULT FALSE
);
```  
`chores`
```sql
CREATE TABLE chores (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT,
    name TEXT,
    description TEXT,
    first_post_at DATETIME,
    interval_days INT,
    gif_url TEXT,
    last_posted DATETIME,
    is_active BOOLEAN DEFAULT TRUE
);
```

## Dependencies
- `discord.py`
- `asyncpg`
- `python-dotenv`  
