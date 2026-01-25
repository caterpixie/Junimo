# Junipriest
Junimo is a Discord bot created for the AD server. Its primary feature is to allow users to anonymously post confessions, which are reviewed and either approved or denied by the server's moderators.</br></br>
It's important to note that no actual permission restrictions in the code. Any restrictions should be made by assigning the confession approval and log channels to role-restricted channels.</br></br>

### Features
Users can:
- Submit an anonymous confession (via a button/modal or `/confession submit`)
- Reply anonymously to an existing confession (via button/modal, context menu, or `/confession reply`)

Moderators can:
- Approve (posts to the public confessions channel)
- Deny (optionally with a reason, which is DM’d to the submitter)
- View a denial history for a user (`/confession denials`)</br></br>


### Updating Junipriest
All updatable code for this bot of the bot is found in the confessions.py file. All configuration can be done in the top portion of the file, labeled "CONFIGURATION"</br></br>

Explanation of variables that can be changed:
- `CONFESSION_CHANNEL_ID`: Channel ID for the channel where the confessions will be publicly posted.
- `CONFESSION_APPROVAL_CHANNEL_ID`: Channel ID for channel where confession approvals will be sent for mods to approve/deny.
- `CONFESSION_LOGS_CHANNEL_ID`: Channel ID for channel where confession approvals/denials will be logged for mods.
- `COLOR_CONFESSION`: Color for the confession embed. Default is #DCA8FF.
- `COLOR_REPLY`: Color for the reply embed. Default is #ECD0FF.
- `COLOR_DENIAL_LOG`: Color log logged confession denials. Default is #99FCFF.</br></br>

## Database
`confession_denials`
```sql
CREATE TABLE confession_denials (
  id INT AUTO_INCREMENT PRIMARY KEY,
  guild_id BIGINT NOT NULL,
  user_id BIGINT NOT NULL,
  denied_by_name VARCHAR(255) NOT NULL,
  confession_text TEXT NOT NULL,
  reason TEXT NULL,
  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_denials_guild_user_time
  ON confession_denials (guild_id, user_id, timestamp);
```
