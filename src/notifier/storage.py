from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


class SentGamesStorage:
    def __init__(self, file_path: str):
        self.file_path = file_path

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
        p.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(p.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(self._states, f)
                f.flush()
                os.fsync(f.fileno())
            Path(tmp).replace(p)
        finally:
            Path(tmp).unlink(missing_ok=True)

    def get_game_state(self, game_key: str) -> str | None:
        return self._states.get(game_key)

    def get_or_migrate_game_state(
        self,
        game_key: str,
        legacy_keys: tuple[str, ...],
    ) -> str | None:
        if game_key in self._states:
            return self._states[game_key]

        legacy_states = {self._states.get(key) for key in legacy_keys}
        state = next(
            (state for state in ("sent", "pending", "failed") if state in legacy_states),
            None,
        )
        if state is not None:
            self._states[game_key] = state
            for key in legacy_keys:
                self._states.pop(key, None)
            self.save_states()
        return state

    def set_game_state(self, game_key: str, state: str) -> None:
        self._states[game_key] = state
        self.save_states()

    def is_game_sent(self, game_key: str) -> bool:
        return self._states.get(game_key) == "sent"

    def mark_game_sent(self, game_key: str) -> None:
        self.set_game_state(game_key, "sent")

    def mark_game_pending(self, game_key: str) -> None:
        self.set_game_state(game_key, "pending")

    def mark_game_failed(self, game_key: str) -> None:
        self.set_game_state(game_key, "failed")
