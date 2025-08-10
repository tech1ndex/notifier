import json
from loguru import logger
from datetime import datetime, timezone

import requests


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

        success_code = 201
        if response.status_code == success_code:
            logger.info(
                f"Message sent successfully at {datetime.now(tz=timezone.utc)}"
            )
            return response.json()
        logger.error("Failed to send message. Status code: {}", response.status_code)
        logger.error("Response: {}", response.text)
        return None
