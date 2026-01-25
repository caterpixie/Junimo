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
- `SLUR_LIST_FILE`: Text file where all recognized slurs are located. Can easily be edited/added to by editing this text file.</br></br>

