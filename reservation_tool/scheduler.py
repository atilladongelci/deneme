from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable, Iterable

from apscheduler.schedulers.background import BackgroundScheduler

from .models import Reservation

ReminderCallback = Callable[[Reservation], None]


class ReminderScheduler:
    """Schedules reminder messages one day before reservations."""

    def __init__(self, on_reminder: ReminderCallback) -> None:
        self.scheduler = BackgroundScheduler()
        self.on_reminder = on_reminder
        self.scheduler.start(paused=True)

    def sync(self, reservations: Iterable[Reservation]) -> None:
        self.scheduler.remove_all_jobs()
        now = datetime.utcnow()
        for reservation in reservations:
            run_time = reservation.scheduled_for - timedelta(days=1)
            if run_time < now:
                # If the reminder time already passed, send immediately.
                self.on_reminder(reservation)
            else:
                self.scheduler.add_job(
                    self.on_reminder,
                    "date",
                    run_date=run_time,
                    args=[reservation],
                    id=f"reminder-{reservation.phone_number}-{reservation.scheduled_for.isoformat()}",
                )
        self.scheduler.resume()

    def shutdown(self) -> None:
        self.scheduler.shutdown(wait=False)
