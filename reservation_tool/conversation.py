from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from .models import Conversation, ConversationStep


class ConversationStore:
    """Simple in-memory conversation store keyed by phone number."""

    def __init__(self) -> None:
        self._conversations: Dict[str, Conversation] = {}

    def get(self, phone_number: str) -> Conversation:
        if phone_number not in self._conversations:
            self._conversations[phone_number] = Conversation(phone_number)
        return self._conversations[phone_number]

    def clear(self, phone_number: str) -> None:
        self._conversations.pop(phone_number, None)


class ConversationEngine:
    """Rule-based assistant that collects reservation details over SMS."""

    def next_response(self, conversation: Conversation, message: str) -> str:
        message = message.strip()
        if conversation.step == ConversationStep.GREETING:
            conversation.step = ConversationStep.ASK_NAME
            return (
                "Merhaba! Ben berber rezervasyon asistanıyım. Öncelikle adınızı alabilir miyim?"
            )

        if conversation.step == ConversationStep.ASK_NAME:
            conversation.customer_name = message or "Müşterimiz"
            conversation.step = ConversationStep.ASK_DAY
            return f"Teşekkürler {conversation.customer_name}! Hangi gün için randevu almak istersiniz?"

        if conversation.step == ConversationStep.ASK_DAY:
            conversation.preferred_day = message
            conversation.step = ConversationStep.ASK_TIME
            return (
                "Tamam. Saat kaçta gelmeyi planlıyorsunuz? Lütfen 24 saat formatında örn. 15:30 şeklinde yazın."
            )

        if conversation.step == ConversationStep.ASK_TIME:
            normalized = self._normalize_time(message)
            if not normalized:
                return "Saat formatını anlayamadım. Lütfen 24 saat formatında (örn. 14:30) yazın."
            conversation.preferred_time = normalized
            conversation.step = ConversationStep.CONFIRMATION
            return (
                "Harika! Lütfen randevuyu onaylamak için 'Evet' yazın veya düzeltmek için yeni saat/gün gönderin."
            )

        if conversation.step == ConversationStep.CONFIRMATION:
            if message.lower() in {"evet", "onay", "tamam", "ok"}:
                conversation.step = ConversationStep.COMPLETE
                return "Rezervasyonunuz oluşturuluyor."
            else:
                conversation.step = ConversationStep.ASK_DAY
                conversation.preferred_day = None
                conversation.preferred_time = None
                return "Anladım, o halde tekrar başlayalım. Hangi gün gelmek istersiniz?"

        return "Anlayamadım, lütfen tekrar yazar mısınız?"

    @staticmethod
    def _normalize_time(value: str) -> Optional[str]:
        for fmt in ("%H:%M", "%H.%M"):
            try:
                parsed = datetime.strptime(value, fmt)
                return parsed.strftime("%H:%M")
            except ValueError:
                continue
        return None
