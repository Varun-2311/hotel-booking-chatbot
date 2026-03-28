"""
chat_logic.py — intent detection, memory, and routing

Intents handled:
  booking          → slot-filling flow
  retrieve_booking → look up past bookings by email
  general          → RAG + LLM answer

Short-term memory = last MAX_HISTORY messages in st.session_state["messages"].
The full history is injected into every LLM call so the assistant never
forgets what was said earlier in the conversation.
"""

import re
import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from app.config import GROQ_API_KEY, GROQ_MODEL, MAX_HISTORY, HOTEL_NAME
from app.booking_flow import (
    handle_booking_turn,
    init_booking_state,
    reset_booking_state,
)
from app.knowledge import answer_known_hotel_fact
from app.tools import rag_tool
from db.database import get_bookings_by_email


# ── LLM initialisation ────────────────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def get_llm() -> ChatGroq:
    """Cache the Groq client — one instance for the whole server lifetime."""
    if not GROQ_API_KEY:
        st.error("GROQ_API_KEY is not set. Add it to .streamlit/secrets.toml.")
        st.stop()
    try:
        return ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL)
    except Exception as e:
        st.error(f"Failed to initialise LLM: {e}")
        st.stop()


# ── Intent detection ──────────────────────────────────────────────────────────

def detect_intent(message: str, llm: ChatGroq) -> str:
    """
    Returns one of: "booking" | "retrieve_booking" | "general"

    Three-way classification:
      booking          — wants to make a new reservation
      retrieve_booking — wants to look up / check an existing booking
      general          — hotel questions, small talk, anything else
    """
    system = """Classify the user message into exactly one of these three categories:

booking          — user wants to make a new hotel reservation or room booking
retrieve_booking — user wants to look up, check, or view an existing booking they made
general          — anything else: hotel questions, amenities, policies, small talk

Reply with ONLY one of these three words: booking  retrieve_booking  general"""

    try:
        response = llm.invoke([
            SystemMessage(content=system),
            HumanMessage(content=message),
        ])
        raw = response.content.strip().lower()
        if "retrieve" in raw:
            return "retrieve_booking"
        if "booking" in raw:
            return "booking"
        return "general"
    except Exception:
        return "general"


# ── Booking retrieval handler ─────────────────────────────────────────────────

def handle_retrieve_booking(user_message: str, llm: ChatGroq) -> str:
    """
    Extract an email from the user's message, look up their bookings in the DB,
    and return a formatted summary.

    Why require email? It's the unique identifier we have for guests.
    We don't expose all bookings — the user must provide their own email.
    """
    # Try to find an email in the message
    email_match = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", user_message)

    if not email_match:
        # Ask for it
        return (
            "I can look up your booking for you. "
            "Could you please share the email address you used when booking?"
        )

    email = email_match.group(0)

    try:
        bookings = get_bookings_by_email(email)
    except Exception as e:
        return f"I ran into a problem looking up your bookings: {e}. Please try again."

    if not bookings:
        return (
            f"I couldn't find any bookings for **{email}**. "
            "Please double-check the email address or contact the front desk."
        )

    lines = [f"Here are the bookings associated with **{email}**:\n"]
    for b in bookings:
        status_icon = "🟢" if b["status"] == "confirmed" else "🔴"
        lines.append(
            f"{status_icon} **Booking ID:** `{b['booking_id']}` | "
            f"{b['booking_type']} | {b['date']} {b['time']} | *{b['status']}*"
        )

    lines.append("\nIs there anything else I can help you with?")
    return "\n".join(lines)


# ── Memory helpers ────────────────────────────────────────────────────────────

def init_memory() -> None:
    if "messages" not in st.session_state:
        st.session_state["messages"] = []


def add_to_memory(role: str, content: str) -> None:
    """Append and trim to MAX_HISTORY."""
    st.session_state["messages"].append({"role": role, "content": content})
    if len(st.session_state["messages"]) > MAX_HISTORY:
        st.session_state["messages"] = st.session_state["messages"][-MAX_HISTORY:]


def get_langchain_messages(system_prompt: str) -> list:
    """
    Build the full message list for the LLM:
      [SystemMessage] + all conversation history as Human/AI messages.

    Passing the full history means the LLM knows:
      - what the user already told us (name, preferences mentioned earlier)
      - what the assistant already said (avoids repeating itself)
    This is how "use memory to avoid repeats" is implemented for general queries.
    For the booking flow, slot-state handles it at the Python level.
    """
    formatted = [SystemMessage(content=system_prompt)]
    for msg in st.session_state.get("messages", []):
        if msg["role"] == "user":
            formatted.append(HumanMessage(content=msg["content"]))
        else:
            formatted.append(AIMessage(content=msg["content"]))
    return formatted


# ── General query handler (RAG + LLM) ────────────────────────────────────────

def handle_general_query(user_message: str, llm: ChatGroq) -> str:
    """
    Retrieve PDF context then generate a grounded, memory-aware response.
    Full conversation history is included so the LLM never asks for
    information it already received in an earlier turn.
    """
    exact_answer = answer_known_hotel_fact(user_message)
    if exact_answer:
        return exact_answer

    try:
        context = rag_tool(user_message)
    except Exception as e:
        context = f"RAG retrieval failed: {e}"

    has_pdf_context = context and "No PDF" not in context

    system_prompt = f"""You are a warm, professional hotel concierge assistant for {HOTEL_NAME}.
Your role is to help guests with questions about the hotel and to assist with bookings.

{'Use the following excerpts from the hotel documentation to answer accurately:' if has_pdf_context else 'No hotel documents are loaded yet — answer from general hotel knowledge.'}

{context if has_pdf_context else ''}

Important guidelines:
- You have access to the full conversation history. Never ask for information the guest already provided.
- Be concise and friendly. Don't repeat what you just said.
- When the documentation includes exact values such as prices, timings, rates, limits, or policy windows, copy those values exactly.
- Prefer bullets or short tables for list questions such as room rates, amenities, policies, or timings.
- If some values are present and others are missing, list only the values that are present and explicitly say which item is missing.
- If asked about booking, let the guest know you can help and invite them to say "I'd like to book".
- If you don't know something specific to this hotel, say so honestly rather than guessing.
- Do not invent prices, availability, or policies."""

    messages = get_langchain_messages(system_prompt)

    try:
        response = llm.invoke(messages)
        return response.content
    except Exception as e:
        return (
            f"I'm sorry, something went wrong on my end ({e}). "
            "Please try again in a moment."
        )


# ── Main entry point ──────────────────────────────────────────────────────────

def process_message(user_message: str) -> str:
    """
    Central router — called by main.py for every user message.

    Priority order:
      1. Booking in progress           → continue slot-filling
      2. Cancel phrase detected        → abort booking
      3. Retrieve booking intent       → look up past bookings by email
      4. New booking intent            → start slot-filling
      5. General                       → RAG + LLM
    """
    llm = get_llm()

    # ── 1. Booking already in progress ────────────────────────────────────────
    if st.session_state.get("booking_active"):
        cancel_phrases = ["cancel booking", "stop booking", "never mind", "forget it", "start over"]
        if any(phrase in user_message.lower() for phrase in cancel_phrases):
            reset_booking_state()
            return "No problem — I've cancelled the booking process. How else can I help?"
        return handle_booking_turn(user_message, llm)

    # ── 2. Classify intent ────────────────────────────────────────────────────
    intent = detect_intent(user_message, llm)

    if intent == "retrieve_booking":
        return handle_retrieve_booking(user_message, llm)

    if intent == "booking":
        st.session_state["booking_active"] = True
        return handle_booking_turn(user_message, llm)

    return handle_general_query(user_message, llm)
