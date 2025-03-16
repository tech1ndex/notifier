import json
import os
from typing import Set

class SentGamesStorage:
    def __init__(self, file_path: str = "sent_games.json"):
        self.file_path = file_path
        self.sent_games: Set[str] = self._load_sent_games()

    def _load_sent_games(self) -> Set[str]:
        if os.path.exists(self.file_path):
            with open(self.file_path, "r") as f:
                return set(json.load(f))
        return set()

    def save_sent_games(self) -> None:
        with open(self.file_path, "w") as f:
            json.dump(list(self.sent_games), f)

    def is_game_sent(self, url: str) -> bool:
        return url in self.sent_games

    def mark_game_sent(self, url: str) -> None:
        self.sent_games.add(url)
        self.save_sent_games()