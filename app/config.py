"""
config.py — centralised configuration
Reads from .streamlit/secrets.toml when running on Streamlit Cloud,
or from environment variables locally.
"""

import os
import streamlit as st


def get_secret(key: str, default: str = "") -> str:
    """
    Try st.secrets first (Streamlit Cloud / local secrets.toml),
    fall back to an environment variable and then the supplied default.
    """
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError):
        return os.getenv(key, default)


# ── LLM ───────────────────────────────────────────────────────────────────────
GROQ_API_KEY = get_secret("GROQ_API_KEY")
GROQ_MODEL = get_secret("GROQ_MODEL", "openai/gpt-oss-120b")

# ── Email (Gmail SMTP) ────────────────────────────────────────────────────────
EMAIL_SENDER = get_secret("EMAIL_SENDER")
EMAIL_PASSWORD = get_secret("EMAIL_PASSWORD")
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

# ── RAG ───────────────────────────────────────────────────────────────────────
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# ── Booking domain ────────────────────────────────────────────────────────────
BOOKING_DOMAIN = "hotel stay"
HOTEL_NAME = "Grand Azure Hotel"

# ── Memory ────────────────────────────────────────────────────────────────────
MAX_HISTORY = 25
