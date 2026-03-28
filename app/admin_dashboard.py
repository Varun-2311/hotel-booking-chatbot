"""
admin_dashboard.py — full admin UI

Features:
  - View all bookings with metrics
  - Search by name / email / date
  - Cancel a booking (sets status = 'cancelled')
  - Edit booking status (admin override)
  - Export to CSV
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import pandas as pd
from db.database import get_all_bookings, search_bookings, cancel_booking, update_booking_status


def render_admin_dashboard() -> None:
    st.title("Admin Dashboard")
    st.caption("Manage all hotel bookings")

    # ── Search / filter row ────────────────────────────────────────────────────
    col_s, col_d = st.columns([2, 1])
    with col_s:
        search_query = st.text_input(
            "Search by name or email",
            placeholder="e.g.  John  or  guest@example.com",
        )
    with col_d:
        date_filter = st.date_input("Filter by check-in date", value=None)

    # ── Fetch data ─────────────────────────────────────────────────────────────
    try:
        if search_query.strip():
            bookings = search_bookings(search_query.strip())
        else:
            bookings = get_all_bookings()
    except Exception as e:
        st.error(f"Database error: {e}")
        return

    # Apply date filter on top of search results
    if date_filter:
        date_str = date_filter.strftime("%Y-%m-%d")
        bookings = [b for b in bookings if b["date"] == date_str]

    # ── Metrics row ────────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total bookings", len(bookings))
    confirmed  = sum(1 for b in bookings if b["status"] == "confirmed")
    cancelled  = sum(1 for b in bookings if b["status"] == "cancelled")
    col2.metric("Confirmed", confirmed)
    col3.metric("Cancelled", cancelled)
    col4.metric("Unique guests", len({b["email"] for b in bookings}))

    st.divider()

    if not bookings:
        st.info("No bookings found.")
        return

    # ── Export button ──────────────────────────────────────────────────────────
    df_export = pd.DataFrame(bookings)
    csv = df_export.to_csv(index=False)
    st.download_button(
        label="Export all as CSV",
        data=csv,
        file_name="bookings_export.csv",
        mime="text/csv",
    )

    st.divider()
    st.subheader("All bookings")

    # ── Per-booking cards with edit/cancel ─────────────────────────────────────
    for b in bookings:
        bid    = b["booking_id"]
        status = b["status"]

        badge = {"confirmed": "🟢", "cancelled": "🔴", "pending": "🟡"}.get(status, "⚪")

        with st.expander(
            f"{badge} **{bid}** — {b['name']} | {b['booking_type']} | {b['date']} {b['time']}"
        ):
            col_info, col_actions = st.columns([2, 1])

            with col_info:
                st.markdown(f"""
| Field | Value |
|---|---|
| **Booking ID** | `{bid}` |
| **Guest** | {b['name']} |
| **Email** | {b['email']} |
| **Phone** | {b['phone']} |
| **Room / Service** | {b['booking_type']} |
| **Check-in date** | {b['date']} |
| **Check-in time** | {b['time']} |
| **Status** | {status} |
| **Booked at** | {b['created_at']} |
""")

            with col_actions:
                st.markdown("**Actions**")

                # Cancel / restore toggle
                if status != "cancelled":
                    if st.button("Cancel booking", key=f"cancel_{bid}", type="secondary"):
                        try:
                            if cancel_booking(bid):
                                st.success(f"Booking {bid} cancelled.")
                                st.rerun()
                            else:
                                st.error("Booking not found.")
                        except Exception as e:
                            st.error(f"Error: {e}")
                else:
                    if st.button("Restore to confirmed", key=f"restore_{bid}"):
                        try:
                            if update_booking_status(bid, "confirmed"):
                                st.success(f"Booking {bid} restored.")
                                st.rerun()
                            else:
                                st.error("Booking not found.")
                        except Exception as e:
                            st.error(f"Error: {e}")

                st.markdown("---")
                st.caption("Override status")
                status_options = ["confirmed", "cancelled", "pending", "no-show"]
                new_status = st.selectbox(
                    "Set status",
                    options=status_options,
                    index=status_options.index(status) if status in status_options else 0,
                    key=f"status_select_{bid}",
                    label_visibility="collapsed",
                )
                if st.button("Apply", key=f"apply_{bid}"):
                    try:
                        update_booking_status(bid, new_status)
                        st.success(f"Status updated to '{new_status}'.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
