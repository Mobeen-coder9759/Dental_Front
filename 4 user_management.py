import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

import sys, os
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


from auth import require_auth, render_user_sidebar
from database import fetch_all_users, create_new_user, toggle_user_active_status
from particle_background import inject_particle_background
from ui import (
    inject_global_css,
    page_header,
    table_header,
    empty_state,
    render_html_table,
)

st.set_page_config(
    page_title="User Management — Dental CRM",
    page_icon="🦷",
    layout="wide",
)
inject_global_css()
inject_particle_background()

# Guard Rail: Restrict User Management exclusively to Admin role
require_auth(allowed_roles=["admin"])

st_autorefresh(interval=30_000, key="users_refresher")

with st.sidebar:
    render_user_sidebar()

page_header(
    "System User Management",
    subtitle="Create & manage practice staff user accounts in PostgreSQL",
)

# ── User List Table ────────────────────────────────────────────────────────
df_users = fetch_all_users()
table_header("Registered CRM Users", len(df_users))

if df_users.empty:
    empty_state("No users found in PostgreSQL database.")
else:
    display = df_users.copy()
    if "created_at" in display.columns:
        display["created_at"] = pd.to_datetime(display["created_at"]).dt.strftime("%Y-%m-%d %I:%M %p")
    
    render_html_table(display)

# ── Create & Deactivate Controls ───────────────────────────────────────────
st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
col1, col2 = st.columns(2, gap="large")

with col1:
    st.markdown(
        "<p style='font-size:12px;color:#9AA0B5;font-weight:600;letter-spacing:0.04em;text-transform:uppercase;'>➕ Create New User Account</p>",
        unsafe_allow_html=True,
    )
    with st.form("create_user_form", clear_on_submit=True):
        new_username = st.text_input("Username", max_chars=30, placeholder="e.g. jsmith")
        new_name = st.text_input("Full Name", max_chars=60, placeholder="e.g. Dr. John Smith")
        new_password = st.text_input("Initial Password", type="password", max_chars=50, placeholder="Min 6 chars")
        new_role = st.selectbox("Assigned Role", ["staff", "hr", "admin"])

        submit_user = st.form_submit_button("Create User", use_container_width=True)

        if submit_user:
            ok, msg = create_new_user(new_username, new_password, new_name, new_role)
            if ok:
                st.success(msg)
                st.cache_data.clear()
                st.rerun()
            else:
                st.error(msg)

with col2:
    st.markdown(
        "<p style='font-size:12px;color:#9AA0B5;font-weight:600;letter-spacing:0.04em;text-transform:uppercase;'>🔒 Manage Account Status</p>",
        unsafe_allow_html=True,
    )
    if not df_users.empty:
        usernames = df_users["username"].tolist()
        target_user = st.selectbox("Select user", usernames, key="select_target_user")
        
        # Get current status
        current_row = df_users[df_users["username"] == target_user]
        current_active = bool(current_row["is_active"].values[0]) if not current_row.empty else True
        
        new_active_status = st.radio(
            "Account Status",
            [True, False],
            format_func=lambda x: "Active (Enabled)" if x else "Disabled (Deactivated)",
            index=0 if current_active else 1,
            key="radio_active_status",
        )
        
        if st.button("Update Status", key="btn_update_user_status", use_container_width=True):
            if target_user.lower() == "admin" and not new_active_status:
                st.error("⚠️ Cannot deactivate the primary 'admin' account.")
            else:
                ok = toggle_user_active_status(target_user, new_active_status)
                if ok:
                    st.success(f"Status for '{target_user}' updated to {'Active' if new_active_status else 'Deactivated'}.")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Failed to update user status.")
