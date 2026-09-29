import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

import sys, os
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


from auth import require_auth, render_user_sidebar
from database import fetch_hiring, update_applicant_status
from particle_background import inject_particle_background
from ui import (
    inject_global_css,
    page_header,
    kpi_strip,
    fmt_ts,
    hiring_badge,
    table_header,
    empty_state,
    render_html_table,
)

st.set_page_config(
    page_title="Hiring — Dental CRM",
    page_icon="🦷",
    layout="wide",
)
inject_global_css()
inject_particle_background()

# Guard Rail: Enforce Authentication & Role Authorization (Admin or HR)
require_auth(allowed_roles=["admin", "hr"])

st_autorefresh(interval=30_000, key="hiring_refresher")

# ── Sidebar filters ────────────────────────────────────────────────────────
with st.sidebar:
    render_user_sidebar()
    st.markdown("### Filters")
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    # Guard Rail: Enforce character length caps
    search = st.text_input("Search applicant", placeholder="Name or email…", max_chars=100)
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
    limit=250,
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

    render_html_table(display, html_cols=["application_status"])

    # ── Inline status updater with Guard Rails ──────────────────────────────────
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    st.markdown(
        "<p style='font-size:11px;color:#6B7080;font-weight:600;letter-spacing:0.04em;text-transform:uppercase;'>Update Applicant Status</p>",
        unsafe_allow_html=True,
    )

    with st.expander("Select applicant to update", expanded=False):
        emails = df_raw["applicant_email"].dropna().unique().tolist()
        if not emails:
            st.warning("No valid candidate email addresses found in the current selection.")
        else:
            target_email = st.selectbox("Applicant email", emails, key="update_email")

            new_status = st.selectbox(
                "New status",
                ["Pending", "Shortlisted", "Rejected", "Hired"],
                key="new_status",
            )

            # Guard Rail: Mandatory user action confirmation
            confirm = st.checkbox(
                f"I confirm setting status of {target_email} to '{new_status}'",
                key="confirm_status_change",
            )

            if st.button("Apply update", key="apply_update"):
                if not confirm:
                    st.warning("⚠️ Please check the confirmation box before applying the status update.")
                else:
                    ok = update_applicant_status(target_email, new_status.lower())
                    if ok:
                        st.success(f"Status updated → {new_status} for {target_email}")
                        st.cache_data.clear()
                        st.rerun()