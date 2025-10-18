from __future__ import annotations

from datetime import datetime

from .conversation import ConversationEngine, ConversationStore
from .message_client import MessageClient
from .models import ConversationNotFoundError, ConversationStep, Reservation
from .scheduler import ReminderScheduler
from .storage import JSONReservationStore


class ReservationAssistant:
    """High-level coordinator for SMS reservation flow."""

    def __init__(
        self,
        store: JSONReservationStore,
        message_client: MessageClient,
    ) -> None:
        self.store = store
        self.message_client = message_client
        self.conversations = ConversationStore()
        self.engine = ConversationEngine()
        self.scheduler = ReminderScheduler(self._send_reminder)
        self._load_existing_reminders()

    def _load_existing_reminders(self) -> None:
        reservations = list(self.store.all())
        self.scheduler.sync(reservations)

    def handle_incoming_message(self, phone_number: str, message: str) -> str:
        conversation = self.conversations.get(phone_number)
        response = self.engine.next_response(conversation, message)
        if conversation.step == ConversationStep.COMPLETE and conversation.is_ready_for_confirmation():
            reservation = self._create_reservation(conversation)
            confirmation_message = (
                f"{reservation.customer_name}, {reservation.scheduled_for:%d %B %Y %H:%M} için randevunuz onaylandı."
            )
            self.message_client.send_message(phone_number, confirmation_message)
            self._finalize_conversation(conversation)
            return confirmation_message
        self.message_client.send_message(phone_number, response)
        return response

    def _create_reservation(self, conversation) -> Reservation:
        scheduled_for = self._parse_scheduled_datetime(
            conversation.preferred_day, conversation.preferred_time
        )
        reservation = Reservation(
            phone_number=conversation.phone_number,
            customer_name=conversation.customer_name or "Müşterimiz",
            scheduled_for=scheduled_for,
        )
        self.store.save(reservation)
        self._sync_scheduler()
        return reservation

    def _finalize_conversation(self, conversation) -> None:
        self.conversations.clear(conversation.phone_number)

    def _sync_scheduler(self) -> None:
        reservations = list(self.store.all())
        self.scheduler.sync(reservations)
        self.store.update(reservations)

    def _send_reminder(self, reservation: Reservation) -> None:
        if reservation.reminder_sent:
            return
        reminder_message = (
            f"Merhaba {reservation.customer_name}! Yarın {reservation.scheduled_for:%H:%M}'deki berber randevunuz için sizi bekliyoruz."
        )
        self.message_client.send_message(reservation.phone_number, reminder_message)
        reservation.reminder_sent = True
        self._sync_scheduler()

    def _parse_scheduled_datetime(self, day: str | None, time_str: str | None) -> datetime:
        if not day or not time_str:
            raise ConversationNotFoundError("Incomplete reservation details.")
        try:
            scheduled = datetime.strptime(f"{day} {time_str}", "%d.%m.%Y %H:%M")
        except ValueError:
            scheduled = datetime.strptime(f"{day} {time_str}", "%d/%m/%Y %H:%M")
        return scheduled

    def shutdown(self) -> None:
        self.scheduler.shutdown()
