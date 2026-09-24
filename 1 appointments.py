import datetime
import pandas as pd
import streamlit as st

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import fetch_appointments
from ui import (
    inject_global_css,
    page_header,
    kpi_strip,
    fmt_ts,
    fmt_null,
    booking_badge,
    table_header,
    empty_state,
    render_df,
)

st.set_page_config(
    page_title="Appointments — Dental CRM",
    page_icon="🦷",
    layout="wide",
)
inject_global_css()

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
    total_today = int(
        df_raw[pd.to_datetime(df_raw["timestamp"]).dt.date == today].shape[0]
    )
    total_upcoming = int(
        df_raw[
            pd.to_datetime(df_raw.get("booking_time", df_raw["timestamp"])).dt.date >= today
        ].shape[0]
    )
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
    # Format columns
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

    # Rename for display
    display.columns = [c.replace("_", " ").title() for c in display.columns]

    # HTML table for badge rendering
    st.markdown(
        display.to_html(
            escape=False,
            index=False,
            classes="",
            border=0,
        ).replace(
            "<table",
            """<table style="
                width:100%;
                border-collapse:collapse;
                font-size:12.5px;
                color:#C8CDD8;
                background:#1A1D27;
            " """,
        ).replace(
            "<th>",
            """<th style="
                text-align:left;
                padding:8px 12px;
                border-bottom:1px solid #2A2D3A;
                font-size:11px;
                font-weight:600;
                color:#6B7080;
                letter-spacing:0.04em;
                text-transform:uppercase;
                white-space:nowrap;
            ">""",
        ).replace(
            "<td>",
            """<td style="
                padding:8px 12px;
                border-bottom:1px solid #1E2130;
                white-space:nowrap;
            ">""",
        ).replace(
            "<tr>",
            """<tr style="transition:background 0.1s;" onmouseover="this.style.background='#20233A'" onmouseout="this.style.background=''">""",
        ),
        unsafe_allow_html=True,
    )

# ── Auto-rerun every 30s ───────────────────────────────────────────────────
import time
time.sleep(30)
st.rerun()