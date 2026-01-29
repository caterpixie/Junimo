# Junisheriff

A Discord bot created for the AD server with the main purpose of moderation; both serious and silly. It has the following features:
- Auto-moderation: slur filter, phishing link detection, link posting rules
- Detailed logging of server events: joined, left, message edits and deleted, voice channel changes and role changes.
- Full manual moderation system with warnings, kicks, bans, mutes and lockdowns. Includes specific rules like auto-kicking after first warn and auto-muting after second warning.
- Silly warning commands</br></br>

## AutoMod
All code for this portion of the bot is found in the automod.py file. All configuration can be done in the top portion of the file, labeled "CONFIGURATION"

Explanation of variables that can be changed:
- `GENERAL_CHANNEL_ID`: Channel ID for the "General Chat" channel. Used to prevent links in General.
- `LOG_CHANNEL_ID`: Channel ID for the case-logs channel.
- `ADMIN_ROLE_IDS`: Role IDs for the moderation permission roles. Used to bypass link posting but will not bypass the slur filter.
- `ALLOWED_GIF_DOMAINS`: Used to bypass link filter for specific domains in General Chat.
- `SLUR_LIST_FILE`: Text file where all recognized slurs are located. Can easily be edited/added to by editing this text file in PebbleHost only.</br></br>

## Logging
All code for this portion of the bot is found in the log.py file. All configuration can be done in the top portion of the file, labeled "CONFIGURATION"

Explanation of variables that can be changed:
- `LOG_CHANNEL_ID`: Channel ID for Arrival/Departure logs.
- `MESSAGE_LOG_CHANNEL_ID`: Channel ID for message edit/deletion logs.
- `USER_LOG_CHANNEL_ID`: Channel ID for user update logs.
- `POLL_CHANNEL_ID`: Channel ID for polls channel. Message edits from this channel are not logged.
- `SCRIPTURE_CHANNEL_ID`: Channel ID for starboard channel. Message edits from this channel are not logged.
- `OFFICIAL_MOD_CHANNEL_ID`: Channel ID for Official Mods chat. Minor Role notifications are sent here.
- `MINOR_ROLE_ID`: Role ID for the -17 age role. Triggers alert in `OFFICIAL_MOD_CHANNEL_ID` when selected.
- `MINOR_ALERT_PING_ROLE_ID`: Role ID for moderator permissions. Pings when `MINOR_ROLE_ID` is selected.
- `SKYLAR_USER_ID`: Literally just Skylar's user ID cause we post and strboard their deleted messages.</br></br>

## Fun Warn Commands
### Commands
- `/piss`: gives piss role (15 min)
- `/foot`: gives foot role (30 min)
- `/mop`: removes piss role
- `/sock`: removes foot role
- `/snatch`: gives bald role
- `/wig`: removes bald role
- `/gag`: native Discord timeout
- `/ungag`: removes timeout

### Updating Fun Warns
All code for this portion of the bot is found in the funwarns.py file. All configuration can be done in the top portion of the file, labeled "CONFIGURATION"

Explanation of variables that can be changed:
- `PISS_ROLE_ID`: Role ID for the piss role.
- `FOOT_ROLE_ID`: Role ID for the foot role.
- `BALD_ROLE_ID`: Role ID for the bald role.
- `PISS_DURATION_SECONDS`: Duration of the `/piss` command, in seconds.
- `FOOT_DURATION_SECONDS`: Duration of the `/foot` command, in seconds.
- `EMBED_COLOR_HEX`: Embed color for fun warns. Default is #99FCFF.</br></br>

## Serious Modding
### Commands
- `/mod warn <user> <reason>`: Warns a user + DMs them.
- `/mod warnings <user>`: Displays a user's warnings.
- `/mod clearwarns <user>`: Clears all of a user's warnings.
- `/mod delwarn <user>`: Deletes 1 selected warn from a user's log.
- `/mod kick <user> <reason>`: Kicks a user from the server + DMs them.
- `/mod ban <user> <reason> [appeal] [preserve_messages]`: Bans a user + DMs them. IF preserve messages set to false, it deletes the last 7 days of messages. If appeal is set to true, a link to a ban appeal form is attached to the DM embed.
- `/mod mute <user> <reason> [duration]`: Mutes a user using the Gag role. If no duration is input, it is indefinite until a mod unmutes them.
- `/mod unmute <user>`: Unmutes a user.</br></br>

### Updating the Mod Bot
All code for this portion of the bot is found in the mod.py file. All configuration can be done in the top portion of the file, labeled "CONFIGURATION"

Explanation of variables that can be changed:
- `CASE_LOG_CHANNEL_ID`: Channel ID for the case-log channel.
- `LOCKDOWN_ANNOUNCE_CHANNEL_ID`: In case of full server lockdown, an announcement is sent in this channel to tell the users. By default, this is General Chat.
- `GAG_ROLE_ID`: Role ID for the mute role.
- `APPEAL_FORM_URL`: Ban appeal form linked in DMs in case of a soft ban.
- `WARNS_PER_PAGE`: How many warnings are displayed per page when `/mod warnings <user>` is used.
- `EMBED_COLOR_HEX`: Embed color for general chat (ex. lockdown embed). Default is #99FCFF.
- `BAN_DELETE_DAYS_DEFAULT`: Number of days of messages that are deleted when someone is banned and their messages are not preserved. Number cannot be higher than 7 days due to Discord API.
