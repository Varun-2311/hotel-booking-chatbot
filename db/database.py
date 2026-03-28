"""
database.py — SQLite client
All DB access for the application goes through this module.
Tables: customers, bookings
"""

import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

# DB lives one level up from this file, in the project root
DB_PATH = Path(__file__).parent.parent / "bookings.db"


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def get_connection() -> sqlite3.Connection:
    """Return a connection with row_factory so rows behave like dicts."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """
    Create tables if they don't already exist.
    Call this once at app startup (main.py).
    """
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS customers (
                customer_id TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                email       TEXT NOT NULL UNIQUE,
                phone       TEXT NOT NULL,
                created_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS bookings (
                id           TEXT PRIMARY KEY,
                customer_id  TEXT NOT NULL,
                booking_type TEXT NOT NULL,
                date         TEXT NOT NULL,
                time         TEXT NOT NULL,
                status       TEXT NOT NULL DEFAULT 'confirmed',
                created_at   TEXT NOT NULL,
                FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
            );
        """)


# ── Customer helpers ──────────────────────────────────────────────────────────

def upsert_customer(name: str, email: str, phone: str) -> str:
    """
    Insert a new customer or return the existing customer_id if the
    email already exists.  Returns the customer_id string.
    """
    with get_connection() as conn:
        # Check if customer already exists by email
        row = conn.execute(
            "SELECT customer_id FROM customers WHERE email = ?", (email,)
        ).fetchone()

        if row:
            return row["customer_id"]

        customer_id = str(uuid.uuid4())
        conn.execute(
            """INSERT INTO customers (customer_id, name, email, phone, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (customer_id, name, email, phone, utc_now_iso()),
        )
        return customer_id


# ── Booking helpers ───────────────────────────────────────────────────────────

def create_booking(customer_id: str, booking_type: str, date: str, time: str) -> str:
    """
    Insert a booking record.  Returns the new booking id.
    """
    booking_id = str(uuid.uuid4())[:8].upper()   # short readable ID e.g. "A3F9C2D1"
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO bookings (id, customer_id, booking_type, date, time, status, created_at)
               VALUES (?, ?, ?, ?, ?, 'confirmed', ?)""",
            (booking_id, customer_id, booking_type, date, time, utc_now_iso()),
        )
    return booking_id


def get_all_bookings() -> list[dict]:
    """
    Return all bookings joined with customer info.
    Used by the admin dashboard.
    """
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT
                b.id            AS booking_id,
                b.booking_type,
                b.date,
                b.time,
                b.status,
                b.created_at,
                c.name,
                c.email,
                c.phone
            FROM bookings b
            JOIN customers c ON b.customer_id = c.customer_id
            ORDER BY b.created_at DESC
        """).fetchall()
    return [dict(r) for r in rows]


def update_booking_status(booking_id: str, new_status: str) -> bool:
    """
    Update the status of a booking (e.g. 'confirmed' → 'cancelled').
    Returns True if a row was actually updated.
    """
    try:
        with get_connection() as conn:
            cursor = conn.execute(
                "UPDATE bookings SET status = ? WHERE id = ?",
                (new_status, booking_id),
            )
            return cursor.rowcount > 0
    except Exception:
        return False


def cancel_booking(booking_id: str) -> bool:
    """Convenience wrapper — sets status to 'cancelled'."""
    return update_booking_status(booking_id, "cancelled")


def get_bookings_by_email(email: str) -> list[dict]:
    """
    Return all bookings for a given guest email.
    Used for 'retrieve my bookings' intent in the chat.
    """
    try:
        with get_connection() as conn:
            rows = conn.execute("""
                SELECT
                    b.id            AS booking_id,
                    b.booking_type,
                    b.date,
                    b.time,
                    b.status,
                    b.created_at,
                    c.name,
                    c.email,
                    c.phone
                FROM bookings b
                JOIN customers c ON b.customer_id = c.customer_id
                WHERE lower(c.email) = lower(?)
                ORDER BY b.date DESC
            """, (email,)).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


def search_bookings(query: str) -> list[dict]:
    """
    Simple case-insensitive search across name, email, date.
    Used by the admin dashboard search box.
    """
    q = f"%{query.lower()}%"
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT
                b.id            AS booking_id,
                b.booking_type,
                b.date,
                b.time,
                b.status,
                b.created_at,
                c.name,
                c.email,
                c.phone
            FROM bookings b
            JOIN customers c ON b.customer_id = c.customer_id
            WHERE lower(c.name)  LIKE ?
               OR lower(c.email) LIKE ?
               OR b.date         LIKE ?
            ORDER BY b.created_at DESC
        """, (q, q, q)).fetchall()
    return [dict(r) for r in rows]
