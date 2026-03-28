"""
tools.py — the three callable tools
  1. rag_tool          : query the FAISS index → context string
  2. save_booking_tool : persist to SQLite → booking_id
  3. send_email_tool   : SMTP confirmation email → success bool
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import (
    EMAIL_SENDER, EMAIL_PASSWORD, SMTP_HOST, SMTP_PORT, HOTEL_NAME
)
from app.rag_pipeline import retrieve
from db.database import upsert_customer, create_booking


# ── Tool 1: RAG ───────────────────────────────────────────────────────────────

def rag_tool(query: str) -> str:
    """
    Input : user's question (plain string)
    Output: retrieved context from uploaded PDFs, or a fallback string.

    The fallback matters — if no PDFs are uploaded yet, the LLM should still
    give a useful answer from its own knowledge, not crash or hallucinate a
    retrieval result.
    """
    context = retrieve(query)
    if context:
        return context
    return "No PDF knowledge base is loaded yet. Answer from general knowledge."


# ── Tool 2: Booking persistence ───────────────────────────────────────────────

def save_booking_tool(
    name: str,
    email: str,
    phone: str,
    booking_type: str,
    date: str,
    time: str,
) -> dict:
    """
    Input : all confirmed booking fields
    Output: {"success": True, "booking_id": "A3F9C2D1"}
         or {"success": False, "error": "..."}

    Separating success/failure into a dict (rather than raising exceptions)
    lets the chat layer produce friendly error messages without a try/except
    at every call site.
    """
    try:
        customer_id = upsert_customer(name=name, email=email, phone=phone)
        booking_id  = create_booking(
            customer_id=customer_id,
            booking_type=booking_type,
            date=date,
            time=time,
        )
        return {"success": True, "booking_id": booking_id}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── Tool 3: Email confirmation ────────────────────────────────────────────────

def send_email_tool(
    to_email: str,
    name: str,
    booking_id: str,
    booking_type: str,
    date: str,
    time: str,
) -> dict:
    """
    Input : recipient details
    Output: {"success": True} or {"success": False, "error": "..."}

    Uses Gmail SMTP with an App Password (not your real Gmail password).
    How to get one:
      Google Account → Security → 2-Step Verification → App passwords
      Create one named "hotel booking app", copy the 16-char password.
    """
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        # Graceful degradation — booking still saved, email just skipped
        return {"success": False, "error": "Email credentials not configured."}

    subject = f"Booking Confirmed – {HOTEL_NAME} | ID: {booking_id}"

    from datetime import datetime
    booked_at = datetime.utcnow().strftime("%d %B %Y, %H:%M UTC")

    html_body = f"""
    <html><body style="font-family: Arial, sans-serif; color: #333; max-width:600px; margin:auto;">

    <div style="background:#2c5f8a; padding:24px 32px; border-radius:8px 8px 0 0;">
      <h1 style="color:#fff; margin:0; font-size:22px;">Booking Confirmed</h1>
      <p style="color:#cde4f5; margin:4px 0 0;">{HOTEL_NAME}</p>
    </div>

    <div style="background:#f9fbfd; padding:24px 32px; border:1px solid #dde8f0; border-top:none;">
      <p style="font-size:16px;">Dear <strong>{name}</strong>,</p>
      <p>Thank you for choosing <strong>{HOTEL_NAME}</strong>. Your reservation is confirmed.
         Please keep this email as your booking reference.</p>

      <table style="border-collapse:collapse; width:100%; margin:20px 0;">
        <tr style="background:#2c5f8a; color:#fff;">
          <td style="padding:10px 14px; font-weight:bold; border-radius:4px 0 0 0;">Field</td>
          <td style="padding:10px 14px; border-radius:0 4px 0 0;">Details</td>
        </tr>
        <tr style="background:#eef4fa;">
          <td style="padding:9px 14px;"><strong>Booking ID</strong></td>
          <td style="padding:9px 14px; font-family:monospace; font-size:15px;">{booking_id}</td>
        </tr>
        <tr>
          <td style="padding:9px 14px;"><strong>Guest name</strong></td>
          <td style="padding:9px 14px;">{name}</td>
        </tr>
        <tr style="background:#eef4fa;">
          <td style="padding:9px 14px;"><strong>Room / Service</strong></td>
          <td style="padding:9px 14px;">{booking_type}</td>
        </tr>
        <tr>
          <td style="padding:9px 14px;"><strong>Check-in date</strong></td>
          <td style="padding:9px 14px;">{date}</td>
        </tr>
        <tr style="background:#eef4fa;">
          <td style="padding:9px 14px;"><strong>Check-in time</strong></td>
          <td style="padding:9px 14px;">{time}</td>
        </tr>
        <tr>
          <td style="padding:9px 14px;"><strong>Status</strong></td>
          <td style="padding:9px 14px;">
            <span style="background:#27ae60; color:#fff; padding:2px 10px;
                         border-radius:12px; font-size:13px;">Confirmed</span>
          </td>
        </tr>
        <tr style="background:#eef4fa;">
          <td style="padding:9px 14px;"><strong>Booked at</strong></td>
          <td style="padding:9px 14px;">{booked_at}</td>
        </tr>
      </table>

      <div style="background:#fff8e1; border-left:4px solid #f39c12;
                  padding:12px 16px; border-radius:0 4px 4px 0; margin:16px 0;">
        <strong>Important information</strong><br>
        <ul style="margin:8px 0 0; padding-left:18px;">
          <li>Please present this email or your Booking ID at check-in.</li>
          <li>Check-in time is from 2:00 PM. Early check-in is subject to availability.</li>
          <li>Check-out time is 11:00 AM.</li>
          <li>To modify or cancel your booking, reply to this email or call our front desk.</li>
        </ul>
      </div>

      <p style="margin-top:20px;">We look forward to welcoming you to <strong>{HOTEL_NAME}</strong>!</p>
    </div>

    <div style="background:#e8eef4; padding:12px 32px; border-radius:0 0 8px 8px;
                font-size:12px; color:#666; border:1px solid #dde8f0; border-top:none;">
      {HOTEL_NAME} • Reservations Team<br>
      This is an automated confirmation. Do not reply to this address.
    </div>

    </body></html>
    """

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = EMAIL_SENDER
        msg["To"]      = to_email
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, to_email, msg.as_string())

        return {"success": True}

    except smtplib.SMTPAuthenticationError:
        return {
            "success": False,
            "error": "Email authentication failed. Check your Gmail App Password in secrets.toml.",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
