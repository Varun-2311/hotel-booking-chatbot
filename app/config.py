"""
config.py — centralised configuration
Reads from .streamlit/secrets.toml when running on Streamlit Cloud,
or from environment variables locally.
"""

import streamlit as st


def get_secret(key: str, default: str = "") -> str:
    """
    Try st.secrets first (Streamlit Cloud / local secrets.toml),
    fall back to empty string so the app doesn't crash on missing keys.
    """
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError):
        return default


# ── LLM ──────────────────────────────────────────────────────────────────────
GROQ_API_KEY   = get_secret("GROQ_API_KEY")
GROQ_MODEL     = "llama-3.3-70b-versatile"   # best free model on Groq right now

# ── Email (Gmail SMTP) ────────────────────────────────────────────────────────
EMAIL_SENDER   = get_secret("EMAIL_SENDER")   # your Gmail address
EMAIL_PASSWORD = get_secret("EMAIL_PASSWORD") # Gmail app password (not your real password)
SMTP_HOST      = "smtp.gmail.com"
SMTP_PORT      = 587

# ── RAG ───────────────────────────────────────────────────────────────────────
# All-MiniLM is small (80 MB), fast, and good enough for hotel FAQ retrieval.
# The alternative is OpenAI's text-embedding-ada-002 — better quality but costs
# money per token and requires an OpenAI key.
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHUNK_SIZE      = 500    # characters per chunk
CHUNK_OVERLAP   = 50     # overlap to avoid cutting context at boundaries

# ── Booking domain ────────────────────────────────────────────────────────────
BOOKING_DOMAIN  = "hotel stay"
HOTEL_NAME      = "Grand Azure Hotel"

# ── Memory ────────────────────────────────────────────────────────────────────
MAX_HISTORY     = 25     # last N messages kept in short-term memory
