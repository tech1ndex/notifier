```text
             _   _  __ _           
 _ __   ___ | |_(_)/ _(_) ___ _ __ 
| '_ \ / _ \| __| | |_| |/ _ \ '__|
| | | | (_) | |_| |  _| |  __/ |   
|_| |_|\___/ \__|_|_| |_|\___|_|   
```

A simple Python project to fetch a list of free Games on the Epic Games Store and notify a group.


#### Usage:

##### Docker:

###### Signal:
```bash
docker run -d \
--name notifier \
--restart unless-stopped \
-v "$(pwd)/notifier:/notifier" \
-e SIGNAL_PHONE='+16731274926' \
-e SIGNAL_GROUP_ID="groupID" \
-e SIGNAL_API_URL="http://localhost:8080" \
-e SENT_GAMES_FILE_PATH="/tmp/sent_games.json"
notifier:<version>
```

If you want to use the Signal bot, you need to set the following environment variables:
- SIGNAL_PHONE: Your phone number
- SIGNAL_GROUP_ID: The group ID

These can be retrieved from a running Signal API.

Instructions on how to run it can be found here https://github.com/bbernhard/signal-cli-rest-api