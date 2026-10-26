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
-e SENT_GAMES_FILE_PATH="/notifier/sent_games.json" \
notifier:<version>
```

Keep the `/notifier` volume when restarting or replacing the container. Notification
states are saved in `sent_games.json` using Epic's `namespace:id` offer identity,
so URL route, slug, or locale changes do not resend an offer already recorded as
`sent` or `pending`. A different offer ID counts as a new offer.

Existing URL-based JSON dictionaries and lists are migrated automatically when an
offer is encountered. Migration matches its current URL and both `/p/` and
`/bundles/` variants with the same base URL and slug, preserving the recorded state.
Keep the existing locale and base URL while migrating old records so they can be
matched; historical slug changes cannot be matched automatically.
Matched URL entries are replaced with the offer identity; unmatched history is kept.

The `pending` state is saved before sending. If the process stops after that save,
the offer stays skipped after restart even if delivery had not completed. Offers
recorded as `failed` remain eligible for retry.

If Epic's CMS is unavailable or returns an invalid response, notifications use
the `offerType` fallback URL. Failed lookups are retried on the next poll, and
recovering a different canonical URL does not resend an already recorded offer.
One-time runs using fallback URLs still exit successfully.

If you want to use the Signal bot, you need to set the following environment variables:
- SIGNAL_PHONE: Your phone number
- SIGNAL_GROUP_ID: The group ID

These can be retrieved from a running Signal API.

Instructions on how to run it can be found here https://github.com/bbernhard/signal-cli-rest-api
