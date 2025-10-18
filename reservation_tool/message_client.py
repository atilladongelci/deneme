from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class MessageClient(Protocol):
    """A minimal interface for sending SMS messages."""

    def send_message(self, to: str, body: str) -> None:
        ...


@dataclass
class ConsoleMessageClient:
    """Simple client that prints outgoing messages to stdout."""

    def send_message(self, to: str, body: str) -> None:
        print(f"[SMS to {to}] {body}")
