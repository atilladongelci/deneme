from __future__ import annotations

import os
from flask import Flask, jsonify, request

from reservation_tool.assistant import ReservationAssistant
from reservation_tool.message_client import ConsoleMessageClient
from reservation_tool.storage import JSONReservationStore

app = Flask(__name__)

store_path = os.environ.get("RESERVATION_STORE", "data/reservations.json")
store = JSONReservationStore(store_path)
message_client = ConsoleMessageClient()
assistant = ReservationAssistant(store, message_client)


@app.route("/health", methods=["GET"])
def health() -> tuple[str, int]:
    return "ok", 200


@app.route("/sms", methods=["POST"])
def sms_webhook():
    payload = request.get_json(force=True)
    phone_number = payload.get("from") or payload.get("phone_number")
    message = payload.get("message", "")
    if not phone_number:
        return jsonify({"error": "phone_number alanı gerekli"}), 400
    response = assistant.handle_incoming_message(phone_number, message)
    return jsonify({"response": response})


@app.route("/reservations", methods=["GET"])
def list_reservations():
    reservations = [
        {
            "customer_name": res.customer_name,
            "phone_number": res.phone_number,
            "scheduled_for": res.scheduled_for.isoformat(),
            "reminder_sent": res.reminder_sent,
        }
        for res in store.all()
    ]
    return jsonify(reservations)


@app.route("/shutdown", methods=["POST"])
def shutdown():
    assistant.shutdown()
    return "shutdown", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
