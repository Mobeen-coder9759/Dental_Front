import datetime
import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import fetch_appointments
from particle_background import inject_particle_background
from ui import (
    inject_global_css,
    page_header,
    kpi_strip,
    fmt_ts,
    fmt_null,
    booking_badge,
    table_header,
    empty_state,
    render_html_table,
)

st.set_page_config(
    page_title="Appointments — Dental CRM",
    page_icon="🦷",
    layout="wide",
)
inject_global_css()
inject_particle_background()
st_autorefresh(interval=30_000, key="appointments_refresher")

# ── Sidebar filters ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Filters")
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    today = datetime.date.today()
    start_date = st.date_input("From", value=today - datetime.timedelta(days=30))
    end_date = st.date_input("To", value=today)

    search = st.text_input("Search patient", placeholder="Name or email…")

    status = st.selectbox(
        "Booking type",
        ["All", "New", "Rescheduled", "Cancelled"],
    )

# ── Fetch data ─────────────────────────────────────────────────────────────
df_raw = fetch_appointments(
    start_date=start_date,
    end_date=end_date,
    search=search if search else None,
    status=status if status != "All" else None,
)

# ── Page header ────────────────────────────────────────────────────────────
page_header(
    "Appointments & Schedule",
    subtitle=f"Auto-refreshes every 30 s  ·  Showing {start_date} → {end_date}",
)

# ── KPI strip ──────────────────────────────────────────────────────────────
if not df_raw.empty:
    ts = pd.to_datetime(df_raw["timestamp"])
    total_today = int((ts.dt.date == today).sum())

    # "Upcoming" = appointments actually scheduled for today or later.
    # booking_time holds the rescheduled slot; otherwise fall back to the
    # original call timestamp only when no reschedule has happened.
    effective_time = df_raw.get("booking_time")
    if effective_time is not None:
        effective_time = pd.to_datetime(effective_time.fillna(df_raw["timestamp"]))
    else:
        effective_time = ts
    total_upcoming = int((effective_time.dt.date >= today).sum())

    total_rescheduled = int(
        df_raw["booking_type"].str.lower().eq("rescheduled").sum()
    ) if "booking_type" in df_raw.columns else 0
    total_cancelled = int(
        df_raw["booking_type"].str.lower().eq("cancelled").sum()
    ) if "booking_type" in df_raw.columns else 0
else:
    total_today = total_upcoming = total_rescheduled = total_cancelled = 0

kpi_strip([
    {"label": "Today's Appointments", "value": total_today},
    {"label": "Upcoming",             "value": total_upcoming},
    {"label": "Rescheduled",          "value": total_rescheduled},
    {"label": "Cancelled",            "value": total_cancelled},
])

# ── Table ──────────────────────────────────────────────────────────────────
table_header("Appointment Records", len(df_raw))

if df_raw.empty:
    empty_state()
else:
    display = df_raw.copy()

    ts_cols = ["timestamp", "old_time", "booking_time", "cancel_time"]
    for col in ts_cols:
        if col in display.columns:
            display[col] = display[col].apply(fmt_ts)

    if "booking_type" in display.columns:
        display["booking_type"] = display["booking_type"].apply(booking_badge)

    if "dob" in display.columns:
        display["dob"] = display["dob"].apply(fmt_null)

    if "calendar_event_id" in display.columns:
        display["calendar_event_id"] = display["calendar_event_id"].apply(fmt_null)

    # Only booking_type is pre-built HTML (a badge) — everything else gets
    # HTML-escaped by render_html_table to prevent stored XSS from webhook data.
    render_html_table(display, html_cols=["booking_type"])