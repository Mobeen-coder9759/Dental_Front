import os
import streamlit as st
from ui import inject_global_css
from streamlit_autorefresh import st_autorefresh
from database import fetch_data

st.set_page_config(
    page_title="Dental CRM",
    page_icon="🦷",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_global_css()

count = st_autorefresh(interval=10000, key="db_refresher")

df = fetch_data("SELECT * FROM appointments ORDER BY created_at DESC;")
st.dataframe(df)
# ── Sidebar branding ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
        <div style="padding:4px 0 20px 0;">
            <div style="font-size:15px;font-weight:700;color:#E8EAF0;letter-spacing:-0.01em;">
                🦷 Dental CRM
            </div>
            <div style="font-size:11px;color:#6B7080;margin-top:3px;">
                Practice Management Dashboard
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    st.markdown(
        """
        <div style="font-size:11px;color:#6B7080;padding:4px 0 8px;">
            NAVIGATION
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Landing page ───────────────────────────────────────────────────────────
st.markdown(
    """
    <div style="
        max-width: 560px;
        margin: 80px auto 0;
        text-align: center;
    ">
        <div style="
            font-size: 40px;
            margin-bottom: 16px;
        ">🦷</div>
        <h1 style="
            font-size: 22px !important;
            font-weight: 700 !important;
            color: #E8EAF0 !important;
            margin-bottom: 10px;
        ">Dental Practice CRM</h1>
        <p style="
            color: #6B7080;
            font-size: 13px;
            line-height: 1.6;
            margin-bottom: 32px;
        ">
            Connected to your Heroku PostgreSQL database.<br>
            Select a section from the sidebar to get started.
        </p>
        <div style="
            display: flex;
            gap: 12px;
            justify-content: center;
            flex-wrap: wrap;
        ">
            <div style="
                background:#1A1D27;
                border:1px solid #2A2D3A;
                border-radius:6px;
                padding:14px 24px;
                font-size:12px;
                color:#9AA0B5;
                min-width:140px;
            ">
                <div style="font-size:18px;margin-bottom:6px;">📅</div>
                <div style="font-weight:600;color:#E8EAF0;margin-bottom:3px;">Appointments</div>
                <div style="color:#6B7080;font-size:11px;">Schedule & bookings</div>
            </div>
            <div style="
                background:#1A1D27;
                border:1px solid #2A2D3A;
                border-radius:6px;
                padding:14px 24px;
                font-size:12px;
                color:#9AA0B5;
                min-width:140px;
            ">
                <div style="font-size:18px;margin-bottom:6px;">👤</div>
                <div style="font-weight:600;color:#E8EAF0;margin-bottom:3px;">Hiring</div>
                <div style="color:#6B7080;font-size:11px;">Applicant pipeline</div>
            </div>
            <div style="
                background:#1A1D27;
                border:1px solid #2A2D3A;
                border-radius:6px;
                padding:14px 24px;
                font-size:12px;
                color:#9AA0B5;
                min-width:140px;
            ">
                <div style="font-size:18px;margin-bottom:6px;">📊</div>
                <div style="font-weight:600;color:#E8EAF0;margin-bottom:3px;">Analytics</div>
                <div style="color:#6B7080;font-size:11px;">Charts & audit logs</div>
            </div>
        </div>
        <p style="
            margin-top: 40px;
            font-size: 11px;
            color: #3A3D4A;
        ">
            Auto-refreshes every 30 s  ·  Data via Heroku PostgreSQL  ·  Vapi + n8n integration
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)