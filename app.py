import streamlit as st
from auth import require_auth, render_user_sidebar
from ui import inject_global_css
from particle_background import inject_particle_background
from streamlit_autorefresh import st_autorefresh

st.set_page_config(
    page_title="Dental CRM Portal",
    page_icon="🦷",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_global_css()
inject_particle_background()

# Guard Rail 1: Require authentication before displaying any page content
require_auth()

# Non-blocking auto-refresh (every 30s)
st_autorefresh(interval=30_000, key="landing_refresher")

# ── Sidebar branding & User profile ────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
        <div style="padding:4px 0 16px 0;">
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
    render_user_sidebar()
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
user = st.session_state.get("user", {})
user_role = user.get("role", "staff").upper()

st.markdown(
    f"""
    <div style="
        max-width: 620px;
        margin: 40px auto 0;
        text-align: center;
    ">
        <div style="font-size: 44px; margin-bottom: 12px;">🦷</div>
        <h1 style="
            font-size: 24px !important;
            font-weight: 700 !important;
            color: #E8EAF0 !important;
            margin-bottom: 8px;
        ">Welcome, {user.get('name', 'User')}</h1>
        <p style="
            color: #6B7080;
            font-size: 13px;
            margin-bottom: 28px;
        ">
            Authenticated Access Level: <strong style="color:#7B8CDE;">{user_role}</strong>
        </p>

        <div style="
            display: flex;
            gap: 14px;
            justify-content: center;
            flex-wrap: wrap;
        ">
            <div style="
                background:#1A1D27;
                border:1px solid #2A2D3A;
                border-radius:8px;
                padding:18px 22px;
                font-size:12px;
                color:#9AA0B5;
                flex:1;
                min-width:160px;
                text-align:left;
            ">
                <div style="font-size:22px;margin-bottom:8px;">📅</div>
                <div style="font-weight:600;color:#E8EAF0;font-size:14px;margin-bottom:4px;">Appointments</div>
                <div style="color:#6B7080;font-size:11px;line-height:1.4;">Schedule & bookings overview for clinic patients.</div>
            </div>
            <div style="
                background:#1A1D27;
                border:1px solid #2A2D3A;
                border-radius:8px;
                padding:18px 22px;
                font-size:12px;
                color:#9AA0B5;
                flex:1;
                min-width:160px;
                text-align:left;
            ">
                <div style="font-size:22px;margin-bottom:8px;">👤</div>
                <div style="font-weight:600;color:#E8EAF0;font-size:14px;margin-bottom:4px;">Hiring</div>
                <div style="color:#6B7080;font-size:11px;line-height:1.4;">Applicant pipeline & status candidate manager.</div>
            </div>
            <div style="
                background:#1A1D27;
                border:1px solid #2A2D3A;
                border-radius:8px;
                padding:18px 22px;
                font-size:12px;
                color:#9AA0B5;
                flex:1;
                min-width:160px;
                text-align:left;
            ">
                <div style="font-size:22px;margin-bottom:8px;">📊</div>
                <div style="font-weight:600;color:#E8EAF0;font-size:14px;margin-bottom:4px;">Analytics</div>
                <div style="color:#6B7080;font-size:11px;line-height:1.4;">Practice call volume & cancellation audit log.</div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)