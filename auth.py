import sys
import os
import hashlib
import streamlit as st

# Ensure project root is in sys.path for reliable module resolution
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from database import get_user_by_username, init_user_db


def verify_credentials(username: str, password: str) -> dict | None:
    """
    Verify username and password against PostgreSQL `app_users` database.
    """
    clean_username = username.strip().lower()
    user = get_user_by_username(clean_username)
    if not user:
        return None

    if not user.get("is_active", True):
        st.error("🔒 Account is deactivated. Please contact your system administrator.")
        return None

    input_hash = hashlib.sha256(password.encode()).hexdigest()
    if input_hash == user["password_hash"]:
        return user
    return None


def init_session_state():
    """Ensure authentication state keys are present in Streamlit session_state."""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "user" not in st.session_state:
        st.session_state["user"] = None


def render_login_form():
    """Render a clean, secure enterprise login interface."""
    init_user_db()
    st.markdown(
        """
        <div style="
            max-width: 420px;
            margin: 60px auto 20px;
            background: #1A1D27;
            border: 1px solid #2A2D3A;
            border-radius: 8px;
            padding: 32px 28px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
        ">
            <div style="text-align:center; margin-bottom: 24px;">
                <div style="font-size: 38px; margin-bottom: 8px;">🦷</div>
                <div style="font-size: 18px; font-weight: 700; color: #E8EAF0;">Dental CRM Portal</div>
                <div style="font-size: 12px; color: #6B7080; margin-top: 4px;">Secure Database-Backed Access</div>
            </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Username", max_chars=50, placeholder="Enter username…")
        password = st.text_input("Password", type="password", max_chars=50, placeholder="Enter password…")
        submitted = st.form_submit_button("Sign In", use_container_width=True)

        if submitted:
            if not username or not password:
                st.error("Please enter both username and password.")
            else:
                user_info = verify_credentials(username, password)
                if user_info:
                    st.session_state["authenticated"] = True
                    st.session_state["user"] = {
                        "username": user_info["username"],
                        "name": user_info["name"],
                        "role": user_info["role"],
                    }
                    st.success(f"Welcome back, {user_info['name']}!")
                    st.rerun()
                else:
                    st.error("Invalid credentials. Please check your username and password.")

    st.markdown("</div>", unsafe_allow_html=True)

    # Demo Credentials Notice
    st.markdown(
        """
        <div style="max-width: 420px; margin: 16px auto; font-size: 11px; color: #6B7080; background: #13151F; border: 1px dashed #2A2D3A; border-radius: 6px; padding: 12px 16px;">
            <strong style="color: #9AA0B5;">Database Accounts (Seeded in PostgreSQL):</strong><br/>
            • <code>admin</code> / <code>admin123</code> (Full Access, Analytics & User Management)<br/>
            • <code>staff</code> / <code>staff123</code> (Appointments & Schedule)<br/>
            • <code>hr</code> / <code>hr123</code> (Applicant Pipeline)
        </div>
        """,
        unsafe_allow_html=True,
    )


def require_auth(allowed_roles: list[str] | None = None) -> bool:
    """
    Guard rail function to enforce authentication and role authorization on a page.
    Returns True if user is authorized, stops execution if not.
    """
    init_session_state()

    if not st.session_state["authenticated"]:
        render_login_form()
        st.stop()
        return False

    user = st.session_state.get("user")
    if allowed_roles and user and user.get("role") not in allowed_roles:
        st.error(f"⛔ Access Denied: Role '{user.get('role').upper()}' does not have access to this section.")
        st.info(f"Required roles: {', '.join([r.upper() for r in allowed_roles])}")
        st.stop()
        return False

    return True


def render_user_sidebar():
    """Render logged-in user profile badge & logout button in sidebar."""
    init_session_state()
    if st.session_state.get("authenticated"):
        user = st.session_state.get("user", {})
        role_color = "#4A7CFF" if user.get("role") == "admin" else "#2ECC71" if user.get("role") == "staff" else "#F5A623"
        st.sidebar.markdown(
            f"""
            <div style="background:#1A1D27; border:1px solid #2A2D3A; border-radius:6px; padding:10px 12px; margin-bottom:14px;">
                <div style="font-size:12px; font-weight:600; color:#E8EAF0;">👤 {user.get('name', 'User')}</div>
                <div style="font-size:10px; color:{role_color}; font-weight:700; text-transform:uppercase; margin-top:2px;">
                    Role: {user.get('role', 'staff')}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.sidebar.button("🔒 Log Out", key="global_logout", use_container_width=True):
            st.session_state["authenticated"] = False
            st.session_state["user"] = None
            st.rerun()
