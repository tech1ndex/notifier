from __future__ import annotations

import json
from pathlib import Path

from src.notifier.settings import EpicSettings


class SentGamesStorage:
    def __init__(self):
        settings = EpicSettings()
        self.settings = settings
        self.file_path = self.settings.sent_games_file_path
        self.sent_games: set[str] = self._load_sent_games()

    def _load_sent_games(self) -> set[str]:
        p = Path(self.file_path)
        if p.exists():
            with p.open() as f:
                return set(json.load(f))
        return set()

    def save_sent_games(self) -> None:
        p = Path(self.file_path)
        p.write_text(json.dumps(list(self.sent_games)))

    def is_game_sent(self, url: str) -> bool:
        return url in self.sent_games

    def mark_game_sent(self, url: str) -> None:
        self.sent_games.add(url)
        self.save_sent_games()
