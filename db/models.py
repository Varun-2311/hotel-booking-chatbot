"""
models.py — dataclass representations of DB rows.

These aren't ORM models — SQLite is accessed directly via database.py.
These classes exist for type clarity when passing booking data around the app,
and make it obvious what shape each object has.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class Customer:
    customer_id: str
    name: str
    email: str
    phone: str
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def __str__(self) -> str:
        return f"{self.name} <{self.email}>"


@dataclass
class Booking:
    id: str
    customer_id: str
    booking_type: str
    date: str
    time: str
    status: str = "confirmed"
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def summary(self) -> str:
        """Human-readable one-liner for logging and email subjects."""
        return (
            f"Booking {self.id} | {self.booking_type} | "
            f"{self.date} {self.time} | {self.status}"
        )

    @classmethod
    def from_dict(cls, d: dict) -> "Booking":
        return cls(
            id=d["booking_id"],
            customer_id=d.get("customer_id", ""),
            booking_type=d["booking_type"],
            date=d["date"],
            time=d["time"],
            status=d.get("status", "confirmed"),
            created_at=d.get("created_at", datetime.now(UTC).isoformat()),
        )
