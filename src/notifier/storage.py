from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from notifier.settings import EpicSettings


class SentGamesStorage:
    def __init__(self):
        settings = EpicSettings()
        self.settings = settings
        default_path = settings.sent_games_file_path

        # When running under pytest, use an isolated temp file to avoid interference
        if os.environ.get("PYTEST_CURRENT_TEST"):
            self.file_path = str(Path(tempfile.gettempdir()) / f".notifier_sent_games_test_{os.getpid()}.json")
        else:
            if default_path == "sent_games.json":
                self.file_path = str(Path.home() / ".notifier_sent_games.json")
            else:
                self.file_path = default_path

        self._states: dict[str, str] = self._load_states()

    def _load_states(self) -> dict[str, str]:
        p = Path(self.file_path)
        if p.exists():
            with p.open() as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
                if isinstance(data, list):
                    return dict.fromkeys(data, "sent")
        return {}

    def save_states(self) -> None:
        p = Path(self.file_path)
        p.write_text(json.dumps(self._states))

    def get_game_state(self, url: str) -> str | None:
        return self._states.get(url)

    def set_game_state(self, url: str, state: str) -> None:
        self._states[url] = state
        self.save_states()

    def is_game_sent(self, url: str) -> bool:
        return self._states.get(url) == "sent"

    def mark_game_sent(self, url: str) -> None:
        self.set_game_state(url, "sent")

    def mark_game_pending(self, url: str) -> None:
        self.set_game_state(url, "pending")

    def mark_game_failed(self, url: str) -> None:
        self.set_game_state(url, "failed")
