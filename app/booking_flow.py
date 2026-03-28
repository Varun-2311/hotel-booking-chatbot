"""
booking_flow.py - slot-filling state machine for hotel bookings.
"""

import json
import re

import streamlit as st
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from app.knowledge import answer_known_hotel_fact
from app.tools import save_booking_tool, send_email_tool
from app.validation import (
    validate_date,
    validate_email,
    validate_phone,
    validate_slots,
    validate_time,
)


REQUIRED_SLOTS = ["name", "email", "phone", "booking_type", "date", "time"]

SLOT_QUESTIONS = {
    "name": "What's your full name?",
    "email": "What's your email address? We'll send your confirmation there.",
    "phone": "What's your phone number?",
    "booking_type": (
        "What type of room or service would you like to book? "
        "(for example Deluxe Room, Suite, Airport Transfer, Spa Package)"
    ),
    "date": "What date would you like to check in? Please use YYYY-MM-DD.",
    "time": "What is your preferred check-in time? For example 2:00 PM or 14:00.",
}


def init_booking_state() -> None:
    if "booking_slots" not in st.session_state:
        st.session_state["booking_slots"] = {slot: None for slot in REQUIRED_SLOTS}
    if "booking_active" not in st.session_state:
        st.session_state["booking_active"] = False
    if "booking_awaiting_confirmation" not in st.session_state:
        st.session_state["booking_awaiting_confirmation"] = False


def reset_booking_state() -> None:
    st.session_state["booking_slots"] = {slot: None for slot in REQUIRED_SLOTS}
    st.session_state["booking_active"] = False
    st.session_state["booking_awaiting_confirmation"] = False


def get_missing_slots() -> list[str]:
    slots = st.session_state.get("booking_slots", {})
    return [slot for slot in REQUIRED_SLOTS if not slots.get(slot)]


def extract_slots_from_message(message: str, llm: ChatGroq) -> dict:
    system = """You are a data extraction assistant. Extract hotel booking information from the user message.

Return ONLY a valid JSON object with these keys (use null for anything not mentioned):
{
  "name": null,
  "email": null,
  "phone": null,
  "booking_type": null,
  "date": null,
  "time": null
}

Rules:
- name: full name only
- email: valid email address only
- phone: digits and common separators only
- booking_type: room or service type
- date: convert to YYYY-MM-DD format if possible, else keep as-is
- time: keep the user's wording if it is already a valid time
- Return ONLY JSON."""

    try:
        response = llm.invoke(
            [SystemMessage(content=system), HumanMessage(content=message)]
        )
        raw = response.content.strip()
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
        extracted = json.loads(raw)
        return {key: value for key, value in extracted.items() if value and key in REQUIRED_SLOTS}
    except Exception:
        return {}


def build_confirmation_summary(slots: dict) -> str:
    return f"""Here's a summary of your booking:

| Field | Value |
|---|---|
| **Name** | {slots['name']} |
| **Email** | {slots['email']} |
| **Phone** | {slots['phone']} |
| **Room / Service** | {slots['booking_type']} |
| **Check-in date** | {slots['date']} |
| **Check-in time** | {slots['time']} |

Shall I confirm this booking? Reply **yes** to confirm or **no** to make changes."""


def build_continue_prompt(slots: dict) -> str:
    missing = get_missing_slots()
    if not missing:
        return ""

    next_slot = missing[0]

    if next_slot == "booking_type":
        return (
            "If one of those options sounds good, tell me which room or service you'd like, "
            "and I'll continue your booking."
        )

    if slots.get("booking_type"):
        return f"Whenever you're ready, {SLOT_QUESTIONS[next_slot]}"

    return (
        "Once you've picked your preferred room or service, let me know and I'll continue the booking."
    )


def prefill_slots_from_history(llm: ChatGroq) -> None:
    slots = st.session_state.get("booking_slots", {})
    if any(value for value in slots.values()):
        return

    history = st.session_state.get("messages", [])
    if not history:
        return

    transcript = "\n".join(
        f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
        for msg in history[-10:]
    )

    system = """A user is starting a hotel booking. Read this conversation and extract any booking details already mentioned.

Return ONLY a valid JSON object (null for anything not mentioned):
{
  "name": null,
  "email": null,
  "phone": null,
  "booking_type": null,
  "date": null,
  "time": null
}

Rules:
- date must be YYYY-MM-DD if convertible
- Return ONLY JSON."""

    try:
        response = llm.invoke(
            [SystemMessage(content=system), HumanMessage(content=f"Conversation:\n{transcript}")]
        )
        raw = response.content.strip()
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
        extracted = json.loads(raw)
        for slot, value in extracted.items():
            if value and slot in REQUIRED_SLOTS:
                slots[slot] = value
    except Exception:
        pass


def handle_booking_turn(user_message: str, llm: ChatGroq) -> str:
    slots = st.session_state["booking_slots"]
    awaiting_confirmation = st.session_state["booking_awaiting_confirmation"]

    if awaiting_confirmation:
        msg_lower = user_message.lower().strip()

        if any(word in msg_lower for word in ["yes", "confirm", "correct", "ok", "sure", "yep", "yeah"]):
            result = save_booking_tool(
                name=slots["name"],
                email=slots["email"],
                phone=slots["phone"],
                booking_type=slots["booking_type"],
                date=slots["date"],
                time=slots["time"],
            )

            if not result["success"]:
                reset_booking_state()
                return f"Sorry, there was a problem saving your booking: {result['error']}. Please try again."

            booking_id = result["booking_id"]
            email_result = send_email_tool(
                to_email=slots["email"],
                name=slots["name"],
                booking_id=booking_id,
                booking_type=slots["booking_type"],
                date=slots["date"],
                time=slots["time"],
            )

            reset_booking_state()

            email_status = (
                "A confirmation email has been sent to your inbox."
                if email_result["success"]
                else (
                    f"(Note: email could not be sent - {email_result.get('error', 'unknown error')} "
                    "but your booking is saved.)"
                )
            )

            return (
                f"Your booking is confirmed. Your booking ID is **{booking_id}**.\n\n"
                f"{email_status}\n\n"
                "Is there anything else I can help you with?"
            )

        if any(word in msg_lower for word in ["no", "cancel", "change", "edit", "wrong"]):
            st.session_state["booking_awaiting_confirmation"] = False
            return "No problem. What would you like to change? Tell me the corrected details and I will update them."

        return "Just to confirm, would you like to proceed with this booking? Please reply yes or no."

    if not any(value for value in slots.values()):
        prefill_slots_from_history(llm)

    extracted = extract_slots_from_message(user_message, llm)
    for slot, value in extracted.items():
        if value:
            slots[slot] = value

    exact_answer = answer_known_hotel_fact(user_message)
    if exact_answer and not extracted:
        continue_prompt = build_continue_prompt(slots)
        if continue_prompt:
            return f"{exact_answer}\n\n{continue_prompt}"
        return exact_answer

    errors = validate_slots(slots)
    if errors:
        if slots.get("email") and not validate_email(slots["email"]):
            slots["email"] = None
        if slots.get("phone") and not validate_phone(slots["phone"]):
            slots["phone"] = None
        if slots.get("date") and not validate_date(slots["date"]):
            slots["date"] = None
        if slots.get("time") and not validate_time(slots["time"]):
            slots["time"] = None
        return errors[0]

    missing = get_missing_slots()
    if missing:
        return SLOT_QUESTIONS[missing[0]]

    st.session_state["booking_awaiting_confirmation"] = True
    return build_confirmation_summary(slots)
