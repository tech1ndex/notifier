import json
import logging
from datetime import datetime, timezone

import requests


class SignalBot:
    def __init__(self, base_url, phone_number):
        self.base_url = base_url.rstrip('/')
        self.phone_number = phone_number

    def send_group_message(self, group_id, message):
        endpoint = f"{self.base_url}/v2/send"

        payload = {
            "message": message,
            "number": self.phone_number,
            "recipients": [group_id],
        }

        headers = {
            "Content-Type": "application/json",
        }

        response = requests.post(endpoint, headers=headers, data=json.dumps(payload), timeout=10)

        success_code = 201
        if response.status_code == success_code:
            logging.info("Message sent successfully at %s", datetime.now(tz=timezone.utc))
            return response.json()
        logging.error("Failed to send message. Status code: %s", response.status_code)
        logging.error("Response: %s", response.text)
        return None
