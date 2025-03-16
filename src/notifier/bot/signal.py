import requests
import json
from datetime import datetime
import logging

class SignalBot:
    def __init__(self, base_url, phone_number):
        self.base_url = base_url.rstrip('/')
        self.phone_number = phone_number

    def send_group_message(self, group_id, message):
        endpoint = f"{self.base_url}/v2/send"

        payload = {
            "message": message,
            "number": self.phone_number,
            "recipients": [group_id]
        }

        headers = {
            "Content-Type": "application/json"
        }

        response = requests.post(endpoint, headers=headers, data=json.dumps(payload))

        if response.status_code == 201:
            logging.info(f"Message sent successfully at {datetime.now()}")
            return response.json()
        else:
            logging.error(f"Failed to send message. Status code: {response.status_code}")
            logging.error(f"Response: {response.text}")
            return None