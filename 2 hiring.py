import pandas as pd
import streamlit as st

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import fetch_hiring, update_applicant_status
from ui import (
    inject_global_css,
    page_header,
    kpi_strip,
    fmt_ts,
    fmt_null,
    hiring_badge,
    table_header,
    empty_state,
)

st.set_page_config(
    page_title="Hiring — Dental CRM",
    page_icon="🦷",
    layout="wide",
)
inject_global_css()

# ── Sidebar filters ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Filters")
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    search = st.text_input("Search applicant", placeholder="Name or email…")
    position = st.selectbox(
        "Position",
        ["All", "Dental Assistant", "Receptionist", "Hygienist", "Office Manager", "Dentist"],
    )
    status = st.selectbox(
        "Status",
        ["All", "Pending", "Shortlisted", "Rejected", "Hired"],
    )

# ── Fetch ──────────────────────────────────────────────────────────────────
df_raw = fetch_hiring(
    search=search if search else None,
    position=position if position != "All" else None,
    status=status if status != "All" else None,
)

# ── Page header ────────────────────────────────────────────────────────────
page_header(
    "Hiring Applications",
    subtitle="Manage and update applicant statuses · Auto-refreshes every 30 s",
)

# ── KPI strip ──────────────────────────────────────────────────────────────
if not df_raw.empty:
    total = len(df_raw)
    pending = int(df_raw["application_status"].str.lower().eq("pending").sum()) if "application_status" in df_raw.columns else 0
    shortlisted = int(df_raw["application_status"].str.lower().eq("shortlisted").sum()) if "application_status" in df_raw.columns else 0
    rejected = int(df_raw["application_status"].str.lower().eq("rejected").sum()) if "application_status" in df_raw.columns else 0
else:
    total = pending = shortlisted = rejected = 0

kpi_strip([
    {"label": "Total Applicants",  "value": total},
    {"label": "Pending Review",    "value": pending},
    {"label": "Shortlisted",       "value": shortlisted},
    {"label": "Rejected",          "value": rejected},
])

# ── Table ──────────────────────────────────────────────────────────────────
table_header("Applicant Records", len(df_raw))

if df_raw.empty:
    empty_state("No applicants match the current filters.")
else:
    display = df_raw.copy()

    if "timestamp" in display.columns:
        display["timestamp"] = display["timestamp"].apply(fmt_ts)

    if "application_status" in display.columns:
        display["application_status"] = display["application_status"].apply(hiring_badge)

    display.columns = [c.replace("_", " ").title() for c in display.columns]

    st.markdown(
        display.to_html(
            escape=False,
            index=False,
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
            """<tr onmouseover="this.style.background='#20233A'" onmouseout="this.style.background=''">""",
        ),
        unsafe_allow_html=True,
    )

    # ── Inline status updater ──────────────────────────────────────────────
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    st.markdown(
        "<p style='font-size:11px;color:#6B7080;font-weight:600;letter-spacing:0.04em;text-transform:uppercase;'>Update Applicant Status</p>",
        unsafe_allow_html=True,
    )

    with st.expander("Select applicant to update", expanded=False):
        emails = df_raw["applicant_email"].dropna().unique().tolist()
        target_email = st.selectbox("Applicant email", emails, key="update_email")

        new_status = st.selectbox(
            "New status",
            ["Pending", "Shortlisted", "Rejected", "Hired"],
            key="new_status",
        )

        if st.button("Apply update", key="apply_update"):
            ok = update_applicant_status(target_email, new_status.lower())
            if ok:
                st.success(f"Status updated → {new_status}")
                st.cache_data.clear()
                st.rerun()

# ── Auto-rerun every 30s ───────────────────────────────────────────────────
import time
time.sleep(30)
st.rerun()