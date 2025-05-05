# Junimo

Junimo is a Discord bot created for the AD server. Its current features include a QOTD system which posts automatically daily, a Chore of the Day feed which posts twice a day, as well some smaller text features (/uwu)

As this bot is, for the moment, not expected to be used in other servers, some elements from the AD guild are hardcoded into the files. These will be detailed below within each category as well as in a separate section for ease of use.

## Features

### QOTD System
#### Commands:
`/qotd add`: Adds a question to the queue.
`/qotd post`: Manually posts the next question in queue. Note that this is posted in the channel in which it is called, and mmust therefore be called in the #of-the-day channel
`/qotd view`: Lists the upcoming questions in the queue.
`/qotd delete`: Deletes a question in the queue. Takes the int input of "index" based on its position in `/qotd view`
