from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .models import Reservation, ReservationConflictError


class ReservationStore:
    """Abstract base for storing reservations."""

    def save(self, reservation: Reservation) -> None:
        raise NotImplementedError

    def all(self) -> Iterable[Reservation]:
        raise NotImplementedError

    def find_by_slot(self, scheduled_for: datetime) -> Optional[Reservation]:
        raise NotImplementedError


class JSONReservationStore(ReservationStore):
    """Simple JSON-file based reservation persistence."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write([])

    def _read(self) -> List[Dict]:
        with self.path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _write(self, data: List[Dict]) -> None:
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)

    def save(self, reservation: Reservation) -> None:
        if self.find_by_slot(reservation.scheduled_for):
            raise ReservationConflictError(
                "A reservation already exists for the selected time slot."
            )
        data = self._read()
        data.append(self._serialize(reservation))
        self._write(data)

    def all(self) -> Iterable[Reservation]:
        data = self._read()
        return [self._deserialize(item) for item in data]

    def find_by_slot(self, scheduled_for: datetime) -> Optional[Reservation]:
        for reservation in self.all():
            if reservation.scheduled_for == scheduled_for:
                return reservation
        return None

    def update(self, reservations: Iterable[Reservation]) -> None:
        data = [self._serialize(res) for res in reservations]
        self._write(data)

    @staticmethod
    def _serialize(reservation: Reservation) -> Dict:
        payload = asdict(reservation)
        payload["scheduled_for"] = reservation.scheduled_for.isoformat()
        payload["created_at"] = reservation.created_at.isoformat()
        return payload

    @staticmethod
    def _deserialize(data: Dict) -> Reservation:
        return Reservation(
            phone_number=data["phone_number"],
            customer_name=data["customer_name"],
            scheduled_for=datetime.fromisoformat(data["scheduled_for"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            reminder_sent=data.get("reminder_sent", False),
        )
