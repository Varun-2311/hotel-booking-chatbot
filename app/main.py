"""
main.py — Streamlit entry point

Run with: streamlit run app/main.py
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st

from db.database import init_db
from app.chat_logic import init_memory, add_to_memory, process_message
from app.booking_flow import init_booking_state
from app.rag_pipeline import ingest_pdfs, auto_ingest_docs
from app.admin_dashboard import render_admin_dashboard
from app.config import HOTEL_NAME, GROQ_API_KEY


# ── One-time startup ──────────────────────────────────────────────────────────

init_db()
init_memory()
init_booking_state()
auto_ingest_docs()   # silently index bundled hotel docs on first load


# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title=f"{HOTEL_NAME} — AI Concierge",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("🏨 " + HOTEL_NAME)
    st.caption("AI Booking Assistant")

    page = st.radio("Navigate", ["Chat", "Admin Dashboard"], index=0)

    st.divider()

    # PDF uploader — only shown on Chat page
    if page == "Chat":
        st.subheader("Hotel documents (RAG)")
        uploaded_files = st.file_uploader(
            "Upload hotel PDFs (menu, policies, room guide…)",
            type=["pdf"],
            accept_multiple_files=True,
            help="Upload PDFs about your hotel. The assistant will use these to answer guest questions.",
        )

        if uploaded_files:
            if st.button("Process PDFs", use_container_width=True):
                with st.spinner("Reading and indexing PDFs…"):
                    ingest_pdfs(uploaded_files)
                st.success(f"Indexed {len(uploaded_files)} PDF(s). The assistant can now answer questions from these documents.")

        # Show RAG status
        if st.session_state.get("rag_ready"):
            n_chunks = len(st.session_state.get("rag_chunks", []))
            st.caption(f"Knowledge base: {n_chunks} chunks indexed ✓")
        else:
            st.caption("No documents loaded yet")

        st.divider()

        # Clear chat
        if st.button("Clear conversation", use_container_width=True):
            st.session_state["messages"] = []
            from app.booking_flow import reset_booking_state
            reset_booking_state()
            st.rerun()


# ── Page routing ──────────────────────────────────────────────────────────────

if page == "Admin Dashboard":
    render_admin_dashboard()

else:
    # ── Chat page ─────────────────────────────────────────────────────────────

    st.title("AI Hotel Concierge")

    # Upfront API key warning — surfaces the problem immediately instead of
    # waiting for the first message to fail
    if not GROQ_API_KEY:
        st.error(
            "**GROQ_API_KEY is not set.** "
            "Add it to `.streamlit/secrets.toml` and restart the app.",
            icon="🔑",
        )
        st.stop()

    # Show booking-in-progress indicator
    if st.session_state.get("booking_active"):
        st.info("Booking in progress — collecting your details. Type 'cancel booking' to stop.", icon="📋")

    # Display full conversation history
    for msg in st.session_state.get("messages", []):
        with st.chat_message(msg["role"], avatar="🧑" if msg["role"] == "user" else "🏨"):
            st.markdown(msg["content"])

    # Chat input
    placeholder = (
        "Collecting booking details…"
        if st.session_state.get("booking_active")
        else "Ask about the hotel · Book a room · Retrieve my booking"
    )
    if prompt := st.chat_input(placeholder):

        # Immediately render the user's message
        with st.chat_message("user", avatar="🧑"):
            st.markdown(prompt)
        add_to_memory("user", prompt)

        # Generate and render assistant response
        with st.chat_message("assistant", avatar="🏨"):
            with st.spinner("Thinking…"):
                response = process_message(prompt)
            st.markdown(response)

        add_to_memory("assistant", response)
        st.rerun()  # Refresh to update booking status indicator
