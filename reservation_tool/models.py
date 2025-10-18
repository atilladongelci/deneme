from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class ConversationStep(str, Enum):
    """State machine steps for the SMS assistant."""

    GREETING = "greeting"
    ASK_NAME = "ask_name"
    ASK_DAY = "ask_day"
    ASK_TIME = "ask_time"
    CONFIRMATION = "confirmation"
    COMPLETE = "complete"


@dataclass
class Conversation:
    """Conversation state for a single phone number."""

    phone_number: str
    step: ConversationStep = ConversationStep.GREETING
    customer_name: Optional[str] = None
    preferred_day: Optional[str] = None
    preferred_time: Optional[str] = None

    def is_ready_for_confirmation(self) -> bool:
        return (
            self.customer_name is not None
            and self.preferred_day is not None
            and self.preferred_time is not None
        )


@dataclass
class Reservation:
    """Concrete reservation entity stored once the flow is completed."""

    phone_number: str
    customer_name: str
    scheduled_for: datetime
    created_at: datetime = field(default_factory=datetime.utcnow)
    reminder_sent: bool = False


class ReservationError(Exception):
    """Base exception for reservation issues."""


class ReservationConflictError(ReservationError):
    """Raised when a conflicting reservation exists for the same time slot."""


class ConversationNotFoundError(ReservationError):
    """Raised when a conversation is expected but missing."""
