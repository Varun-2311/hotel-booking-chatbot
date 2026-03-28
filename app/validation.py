"""
validation.py - pure validation helpers for booking data.
"""

from __future__ import annotations

import re
from datetime import date, datetime


EMAIL_RE = re.compile(r"[^@]+@[^@]+\.[^@]+")
PHONE_RE = re.compile(r"^[0-9+\-\s()]{7,20}$")
TIME_FORMATS = ("%I:%M %p", "%I %p", "%H:%M", "%H%M")


def validate_email(value: str) -> bool:
    return bool(value and EMAIL_RE.fullmatch(value.strip()))


def validate_phone(value: str) -> bool:
    return bool(value and PHONE_RE.fullmatch(value.strip()))


def validate_date(value: str) -> bool:
    if not value:
        return False
    try:
        parsed = datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError:
        return False
    return parsed >= date.today()


def validate_time(value: str) -> bool:
    if not value:
        return False
    cleaned = value.strip().upper()
    for fmt in TIME_FORMATS:
        try:
            datetime.strptime(cleaned, fmt)
            return True
        except ValueError:
            continue
    return False


def validate_slots(slots: dict) -> list[str]:
    errors: list[str] = []

    if slots.get("email") and not validate_email(slots["email"]):
        errors.append("That doesn't look like a valid email. Please enter it as name@domain.com.")

    if slots.get("phone") and not validate_phone(slots["phone"]):
        errors.append("Please enter a valid phone number using digits and common separators only.")

    if slots.get("date") and not validate_date(slots["date"]):
        errors.append("Please enter a valid future date as YYYY-MM-DD (for example 2026-04-15).")

    if slots.get("time") and not validate_time(slots["time"]):
        errors.append("Please enter a valid check-in time such as 2:00 PM or 14:00.")

    return errors
