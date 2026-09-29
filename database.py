import os
import logging
import hashlib
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Load environment variables from .env if available
load_dotenv()

# Configure logging for database backend
logger = logging.getLogger("dental_crm_db")
logger.setLevel(logging.ERROR)


@st.cache_resource
def get_engine():
    """
    Create (and cache) a single SQLAlchemy engine/pool for the app's lifetime.
    
    Guard Rails Applied:
    - Connection pooling: pool_size=5, max_overflow=10, pool_recycle=1800
    - Pre-ping connection health check
    - Statement execution timeout (10 seconds)
    - SSL mode enforced
    """
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        logger.error("DATABASE_URL environment variable is not set.")
        raise ValueError("DATABASE_URL environment variable is not set.")

    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    if "sslmode" not in url:
        separator = "&" if "?" in url else "?"
        url += f"{separator}sslmode=require"

    try:
        engine = create_engine(
            url,
            pool_size=5,
            max_overflow=10,
            pool_recycle=1800,
            pool_pre_ping=True,
            connect_args={"options": "-c statement_timeout=10000ms"},
        )
        return engine
    except Exception as e:
        logger.critical(f"Failed to create database engine: {e}", exc_info=True)
        raise e


def init_user_db():
    """
    Ensure the `app_users` table exists in PostgreSQL and seed initial default admin/staff/hr accounts if empty.
    """
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS app_users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        name VARCHAR(100) NOT NULL,
        role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'staff', 'hr')),
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    try:
        engine = get_engine()
        with engine.begin() as conn:
            conn.execute(text(create_table_sql))

            # Check if any users exist; if empty, seed default accounts
            count_res = conn.execute(text("SELECT COUNT(*) FROM app_users")).scalar()
            if count_res == 0:
                logger.info("Seeding initial default user accounts into PostgreSQL...")
                seed_sql = text("""
                    INSERT INTO app_users (username, password_hash, name, role)
                    VALUES (:username, :password_hash, :name, :role)
                """)
                default_users = [
                    {
                        "username": "admin",
                        "password_hash": hashlib.sha256(os.environ.get("ADMIN_PASSWORD", "admin123").encode()).hexdigest(),
                        "name": "Dr. Sarah Jenkins (Admin)",
                        "role": "admin",
                    },
                    {
                        "username": "staff",
                        "password_hash": hashlib.sha256(os.environ.get("STAFF_PASSWORD", "staff123").encode()).hexdigest(),
                        "name": "Front Desk Staff",
                        "role": "staff",
                    },
                    {
                        "username": "hr",
                        "password_hash": hashlib.sha256(os.environ.get("HR_PASSWORD", "hr123").encode()).hexdigest(),
                        "name": "HR Manager",
                        "role": "hr",
                    },
                ]
                for user in default_users:
                    conn.execute(seed_sql, user)
    except SQLAlchemyError as e:
        logger.error(f"Error initializing user database: {e}", exc_info=True)


def get_user_by_username(username: str) -> dict | None:
    """
    Query PostgreSQL for a specific active user by username.
    """
    init_user_db()
    sql = text("""
        SELECT username, password_hash, name, role, is_active
        FROM app_users
        WHERE LOWER(username) = :username
    """)
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(sql, {"username": username.strip().lower()}).first()
            if result:
                return {
                    "username": result[0],
                    "password_hash": result[1],
                    "name": result[2],
                    "role": result[3],
                    "is_active": result[4],
                }
            return None
    except SQLAlchemyError as e:
        logger.error(f"Failed to fetch user by username: {e}", exc_info=True)
        return None


@st.cache_data(ttl=15)
def fetch_all_users() -> pd.DataFrame:
    """
    Fetch list of all registered system users for Admin User Management interface.
    """
    init_user_db()
    sql = """
        SELECT id, username, name, role, is_active, created_at
        FROM app_users
        ORDER BY id ASC
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            return pd.read_sql(text(sql), conn)
    except SQLAlchemyError as e:
        logger.error(f"Failed to fetch all users: {e}", exc_info=True)
        st.error("⚠️ Failed to load user list from database.")
        return pd.DataFrame()


def create_new_user(username: str, password_raw: str, name: str, role: str) -> tuple[bool, str]:
    """
    Create and insert a new system user into PostgreSQL.
    """
    init_user_db()
    clean_user = username.strip().lower()
    clean_name = name.strip()
    clean_role = role.strip().lower()

    if not clean_user or len(clean_user) < 3:
        return False, "Username must be at least 3 characters long."
    if not password_raw or len(password_raw) < 6:
        return False, "Password must be at least 6 characters long."
    if not clean_name:
        return False, "Full Name is required."
    if clean_role not in {"admin", "staff", "hr"}:
        return False, "Invalid role specified."

    # Check if username already exists
    existing = get_user_by_username(clean_user)
    if existing:
        return False, f"Username '{clean_user}' is already registered."

    pass_hash = hashlib.sha256(password_raw.encode()).hexdigest()
    sql = text("""
        INSERT INTO app_users (username, password_hash, name, role, is_active)
        VALUES (:username, :password_hash, :name, :role, TRUE)
    """)
    try:
        engine = get_engine()
        with engine.begin() as conn:
            conn.execute(sql, {
                "username": clean_user,
                "password_hash": pass_hash,
                "name": clean_name,
                "role": clean_role,
            })
        logger.info(f"Created new user account: {clean_user} ({clean_role})")
        return True, f"User '{clean_user}' created successfully."
    except SQLAlchemyError as e:
        logger.error(f"Failed to create user: {e}", exc_info=True)
        return False, "Database error creating user."


def toggle_user_active_status(username: str, is_active: bool) -> bool:
    """
    Enable or deactivate a user account in PostgreSQL.
    """
    sql = text("""
        UPDATE app_users
        SET is_active = :is_active
        WHERE LOWER(username) = :username
    """)
    try:
        engine = get_engine()
        with engine.begin() as conn:
            conn.execute(sql, {"username": username.strip().lower(), "is_active": is_active})
        st.cache_data.clear()
        return True
    except SQLAlchemyError as e:
        logger.error(f"Failed to update user active status: {e}", exc_info=True)
        return False


@st.cache_data(ttl=30)
def fetch_appointments(
    start_date=None,
    end_date=None,
    search=None,
    status=None,
    limit: int = 250,
) -> pd.DataFrame:
    """
    Fetch appointment records with parameterized SQL and mandatory pagination limit.
    """
    limit = min(max(1, limit), 1000)

    sql = """
        SELECT
            timestamp,
            name,
            email,
            dob,
            insurance,
            reason,
            booking_type,
            old_time,
            booking_time,
            cancel_time,
            calendar_event_id
        FROM appointments
        WHERE 1=1
    """
    params = {}

    if start_date:
        sql += " AND DATE(timestamp) >= :start_date"
        params["start_date"] = start_date
    if end_date:
        sql += " AND DATE(timestamp) <= :end_date"
        params["end_date"] = end_date
    if search and search.strip():
        clean_search = search.strip()[:100]
        sql += " AND (LOWER(name) LIKE :search OR LOWER(email) LIKE :search)"
        params["search"] = f"%{clean_search.lower()}%"
    if status and status != "All":
        sql += " AND LOWER(booking_type) = :status"
        params["status"] = status.lower()

    sql += " ORDER BY timestamp DESC LIMIT :limit"
    params["limit"] = limit

    try:
        engine = get_engine()
        with engine.connect() as conn:
            return pd.read_sql(text(sql), conn, params=params)
    except SQLAlchemyError as e:
        logger.error(f"Database error in fetch_appointments: {e}", exc_info=True)
        st.error("⚠️ Database query failed or timed out. Please try again.")
        return pd.DataFrame()


@st.cache_data(ttl=30)
def fetch_hiring(
    search=None,
    position=None,
    status=None,
    limit: int = 250,
) -> pd.DataFrame:
    """
    Fetch hiring application records with parameterized SQL and mandatory limit.
    """
    limit = min(max(1, limit), 1000)

    sql = """
        SELECT
            timestamp,
            applicant_name,
            applicant_email,
            applicant_phone,
            position_applied,
            years_experience,
            application_status
        FROM hiring_applications
        WHERE 1=1
    """
    params = {}

    if search and search.strip():
        clean_search = search.strip()[:100]
        sql += " AND (LOWER(applicant_name) LIKE :search OR LOWER(applicant_email) LIKE :search)"
        params["search"] = f"%{clean_search.lower()}%"
    if position and position != "All":
        sql += " AND LOWER(position_applied) = :position"
        params["position"] = position.lower()
    if status and status != "All":
        sql += " AND LOWER(application_status) = :status"
        params["status"] = status.lower()

    sql += " ORDER BY timestamp DESC LIMIT :limit"
    params["limit"] = limit

    try:
        engine = get_engine()
        with engine.connect() as conn:
            return pd.read_sql(text(sql), conn, params=params)
    except SQLAlchemyError as e:
        logger.error(f"Database error in fetch_hiring: {e}", exc_info=True)
        st.error("⚠️ Database query failed or timed out. Please try again.")
        return pd.DataFrame()


@st.cache_data(ttl=30)
def fetch_analytics(limit: int = 250) -> dict:
    """
    Fetch analytics aggregations and audit records safely.
    """
    limit = min(max(1, limit), 1000)
    queries = {
        "by_reason": """
            SELECT reason, COUNT(*) as count
            FROM appointments
            WHERE reason IS NOT NULL
            GROUP BY reason
            ORDER BY count DESC
            LIMIT 50
        """,
        "call_volume": """
            SELECT DATE(timestamp) as date, COUNT(*) as calls
            FROM appointments
            GROUP BY DATE(timestamp)
            ORDER BY date ASC
            LIMIT 90
        """,
        "audit_log": f"""
            SELECT
                timestamp,
                name,
                email,
                booking_type,
                old_time,
                cancel_time,
                calendar_event_id
            FROM appointments
            WHERE old_time IS NOT NULL OR cancel_time IS NOT NULL
            ORDER BY timestamp DESC
            LIMIT {limit}
        """,
    }
    results = {}
    try:
        engine = get_engine()
        with engine.connect() as conn:
            for key, sql in queries.items():
                results[key] = pd.read_sql(text(sql), conn)
    except SQLAlchemyError as e:
        logger.error(f"Database error in fetch_analytics: {e}", exc_info=True)
        st.error("⚠️ Analytics data temporary fetch error.")
        for key in queries:
            results[key] = pd.DataFrame()
    return results


def update_applicant_status(email: str, new_status: str) -> bool:
    """
    Update candidate status with validation and execution guard rails.
    """
    VALID_STATUSES = {"pending", "shortlisted", "rejected", "hired"}
    clean_status = new_status.lower().strip()
    clean_email = email.lower().strip()

    if clean_status not in VALID_STATUSES:
        logger.warning(f"Invalid status update attempt: {new_status}")
        st.error("Invalid application status specified.")
        return False

    if not clean_email or "@" not in clean_email:
        st.error("Invalid email address for status update.")
        return False

    sql = text(
        "UPDATE hiring_applications SET application_status = :status WHERE LOWER(applicant_email) = :email"
    )
    try:
        engine = get_engine()
        with engine.begin() as conn:
            result = conn.execute(sql, {"status": clean_status, "email": clean_email})
            if result.rowcount == 0:
                st.warning("No candidate record found matching the specified email.")
                return False
        logger.info(f"Updated status for candidate {clean_email} -> {clean_status}")
        return True
    except SQLAlchemyError as e:
        logger.error(f"Failed to update applicant status: {e}", exc_info=True)
        st.error("⚠️ Failed to update candidate status. Please try again.")
        return False