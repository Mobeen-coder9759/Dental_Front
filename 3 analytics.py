import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import fetch_analytics
from particle_background import inject_particle_background
from ui import (
    inject_global_css,
    page_header,
    fmt_ts,
    fmt_null,
    booking_badge,
    code_pill,
    table_header,
    empty_state,
    render_html_table,
)

st.set_page_config(
    page_title="Analytics — Dental CRM",
    page_icon="🦷",
    layout="wide",
)
inject_global_css()
inject_particle_background()
st_autorefresh(interval=30_000, key="analytics_refresher")

page_header(
    "Practice Analytics & Audit",
    subtitle="Aggregated appointment data  ·  Auto-refreshes every 30 s",
)

# ── Fetch ──────────────────────────────────────────────────────────────────
data = fetch_analytics()
df_reason = data.get("by_reason", pd.DataFrame())
df_volume = data.get("call_volume", pd.DataFrame())
df_audit  = data.get("audit_log", pd.DataFrame())

# ── Charts row ────────────────────────────────────────────────────────────
col_left, col_right = st.columns(2, gap="medium")

with col_left:
    st.markdown(
        "<p style='font-size:11px;color:#6B7080;font-weight:600;letter-spacing:0.04em;text-transform:uppercase;margin-bottom:8px;'>Bookings by Reason</p>",
        unsafe_allow_html=True,
    )
    if not df_reason.empty:
        st.markdown(
            """
            <div style="
                background:#1A1D27;
                border:1px solid #2A2D3A;
                border-radius:6px;
                padding:16px;
            ">
            """,
            unsafe_allow_html=True,
        )
        st.bar_chart(
            df_reason.set_index("reason")["count"],
            height=280,
            color="#4A7CFF",
            use_container_width=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        empty_state("No reason data available.")

with col_right:
    st.markdown(
        "<p style='font-size:11px;color:#6B7080;font-weight:600;letter-spacing:0.04em;text-transform:uppercase;margin-bottom:8px;'>Call Volume Over Time</p>",
        unsafe_allow_html=True,
    )
    if not df_volume.empty:
        st.markdown(
            """
            <div style="
                background:#1A1D27;
                border:1px solid #2A2D3A;
                border-radius:6px;
                padding:16px;
            ">
            """,
            unsafe_allow_html=True,
        )
        df_volume["date"] = pd.to_datetime(df_volume["date"])
        st.line_chart(
            df_volume.set_index("date")["calls"],
            height=280,
            color="#2ECC71",
            use_container_width=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        empty_state("No call volume data available.")

# ── Spacer ─────────────────────────────────────────────────────────────────
st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# ── Audit log ──────────────────────────────────────────────────────────────
table_header("Cancellation & Reschedule Audit Log", len(df_audit))
st.markdown(
    "<p style='font-size:11px;color:#6B7080;margin-top:6px;margin-bottom:12px;'>Records where <code style='background:#1A1D27;border:1px solid #2A2D3A;padding:1px 5px;border-radius:3px;color:#9AA0B5;'>old_time</code> or <code style='background:#1A1D27;border:1px solid #2A2D3A;padding:1px 5px;border-radius:3px;color:#9AA0B5;'>cancel_time</code> is not null — for calendar event traceability.</p>",
    unsafe_allow_html=True,
)

if df_audit.empty:
    empty_state("No reschedule or cancellation events found.")
else:
    display = df_audit.copy()

    ts_cols = ["timestamp", "old_time", "cancel_time"]
    for col in ts_cols:
        if col in display.columns:
            display[col] = display[col].apply(fmt_ts)

    if "booking_type" in display.columns:
        display["booking_type"] = display["booking_type"].apply(booking_badge)

    if "calendar_event_id" in display.columns:
        display["calendar_event_id"] = display["calendar_event_id"].apply(code_pill)

    render_html_table(display, html_cols=["booking_type", "calendar_event_id"])