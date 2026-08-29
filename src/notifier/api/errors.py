from __future__ import annotations

from typing import Any


class EpicApiError(Exception):
    def __init__(
        self,
        message: str,
        error_code: int | str | None = None,
        service_response: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = (
            f"Error code: {error_code if error_code is not None else 'unknown'}. "
            f"{message.capitalize()}"
        )
        self.error_code = error_code
        self.exception_data = service_response

    def __str__(self) -> str:
        return self.message


class EpicNotFoundError(EpicApiError):
    pass
