# Junimo

Junimo is a Discord bot created for the AD server. Its current features include:
- A Question of the Day (QOTD) system
- Starboard
- A counting channel with rewards + penalties
- A chore of the day reminder system
- Text triggers
- An `/uwu` command

Many features of this bot are hardcoded as it is only meant for use within the AD server. This README will detail what all the features do as well as the basics on how to edit these hardcoded features.</br></br>

## QOTD System</br>
### Commands
- `/qotd add <question> [image]`: Adds a question to the queue.
- `/qotd post`: Manually posts the next question in queue. Note that this is posted in the channel in which it is called, and must therefore be called in the #of-the-day channel
- `/qotd view`: Lists the upcoming questions in the queue, indexed.
- `/qotd delete <index>`: Deletes a question in the queue. Takes the int input of "index" based on its position in `/qotd view`</br></br>

### Updating QOTD
All code for this portion of the bot is found in the `qotd.py` file. All configuration can be done in the top portion of the file, labeled "CONFIGURATION"

Explanation of variables that can be changed:
- `QOTD_CHANNEL_ID`: The channel ID where the bot will automatically post the question embed.
- `QOTD_ROLE_ID`: The role ID for the QOTD ping role.
- `AUTO_POST_HOUR`,`AUTO_POST_MINUTE`: Hour and minute at which QOTD embed is posted. This must be in the America/Chicago timezone to work with the PebbleHost server.
- `THREAD_NAME`: Name of the thread that is created under the QOTD embed where users can post their answers.
- `THREAD_AUTO_ARCHIVE_MINUTES`: How many minutes of inactivity in a thread before the thread is archived automatically.
- `EMBED_COLOR`: Color of the embed. Default is #9CEC61.
- `QUEUE_PAGE_SIZE`: How many entries will be shown in a single page when displaying the queue.</br></br>

## Chore of the Day System</br>
### Commands  
- `add_chore <name> <description> <first post time> <interval in days> <gif direct url>`: Adds a chore to the `chore` database. This command is not called in the `main.py` file as it was only used for the setup of the database. However it is kept in the files in the case that this feed needs to be edited or re-made.

Valid date format is: Y-m-d H:M. Must be in America/Chicago timezone (one hour earlier than CST)</br></br>

### Updating Chore of the Day  
I'm gonna be real, chore of the day is a mess that is difficult to edit and add chores into because the chore rotation is complex. If we choose to edit it it would need to be restarted from scratch. To do this: 

1. From the SQL database, delete all the entries in the "chores" table. This will give us a blank slate to put chores into.
2. Uncomment this line in `chores.py`: #bot.tree.add_command(add_chore).
3. Restart the PebbleHost server. This will add the `add_chore` command into the commands list so it will show up in Discord.
4. Manually add the chores using the command (necessary variables in order detailed above).

All code for this portion of the bot is found in the `chores.py` file. All configuration can be done in the top portion of the file, labeled "CONFIGURATION"</br></br>  

Explanation of variables that can be changed:
- `ALLOWED_INTERVAL_DAYS`: Accepted intervals, in days, for the `/add_chore` command. Example: if you want to post a specific chore every 3 days, you would need to add "3" to this list.
- `CHORE_PING_ROLE_ID`: Role ID for the chore of the day ping role.
- `CHORE_EMBED_COLOR`: Color of the embed. Default is 0xFFA4C6.</br></br>

Posting is done through the Junimaid webhook for the #of-the-day server in an embed. **The webhook URL can be updated in the .env file**</br></br>  

## Starboard</br>
### Updating Starboard
All code for this portion of the bot is found in the `starboard.py` file. All configuration can be done in the top portion of the file, labeled "CONFIGURATION"

Explanation of variables that can be changed:
- `STARBOARD_CHANNEL_ID`: Channel ID where starred messages will be posted.
- `EXCLUDED_CHANNEL_IDS`: Array of channels where starred messages will be ignored.
- `STAR_EMOJI`: Emoji used to star messages and send them to the starboard.
- `STAR_THRESHOLD`: Number of reactions needed to be sent to the starboard channel.
- `EMBED_COLOR`: Color of the embed. Default is #9CEC61.</br></br>

## Counting
### Updating Counting
All code for this portion of the bot is found in the `counting.py` file. All configuration can be done in the top portion of the file, labeled "CONFIGURATION"

Explanation of variables that can be changed:
- `COUNTING_CHANNEL_ID`: Channel ID where counting is possible.
- `LOSER_ROLE_ID`: Role ID for punishment role.
- `LOSER_ROLE_DURATION`: Duration of punishment role, in seconds.
- `MILESTONES`: Array of numbers at which a "reward" (hot man pic) will be posted using the secret trigger.
- `FINAL_MILESTONE`: A special last milestone
- `FUNNY_NUMBERS`: An array of special milestones because they are funny numbers.
- `EMBED_COLOR`: Color of the embed. Default is #99FCFF.
- `TRIGGER_BYPASS_MESSAGE`: Secret trigger for the hot men pics. Is deleted immediately after being posted to avoid user abuse. If it ends up getting abused/found out, it can be changed to another random string as long as the trigger in the triggers SQL table is also changed.</br></br>

## Misc Commands
- `/uwu`: Takes in text input and UwU-ifies it</br></br>

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
`triggers`
```sql
CREATE TABLE triggers (
  id INT AUTO_INCREMENT PRIMARY KEY,
  guild_id BIGINT,
  trigger_text TEXT,
  response_type VARCHAR(20),
  response_text TEXT
);
```
</br>

## Dependencies
- `discord.py`
- `asyncpg`
- `python-dotenv`  
