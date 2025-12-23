import json
from datetime import datetime, timezone

import requests
from loguru import logger


class SignalBot:
    def __init__(self, base_url, phone_number):
        self.base_url = base_url.rstrip("/")
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

        response = requests.post(
            endpoint,
            headers=headers,
            data=json.dumps(payload),
            timeout=10,
        )

        response.raise_for_status()

        logger.info(
            f"Message sent successfully at {datetime.now(tz=timezone.utc)}",
        )
        return response.json()
