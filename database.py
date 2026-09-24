import os
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


def get_engine():
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise ValueError("DATABASE_URL environment variable is not set.")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if "sslmode" not in url:
        url += "?sslmode=require"
    return create_engine(url, pool_pre_ping=True)


@st.cache_data(ttl=30)
def fetch_appointments(
    start_date=None,
    end_date=None,
    search=None,
    status=None,
) -> pd.DataFrame:
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
    if search:
        sql += " AND (LOWER(name) LIKE :search OR LOWER(email) LIKE :search)"
        params["search"] = f"%{search.lower()}%"
    if status and status != "All":
        sql += " AND LOWER(booking_type) = :status"
        params["status"] = status.lower()

    sql += " ORDER BY timestamp DESC"

    try:
        engine = get_engine()
        with engine.connect() as conn:
            return pd.read_sql(text(sql), conn, params=params)
    except SQLAlchemyError as e:
        st.error(f"Database error: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=30)
def fetch_hiring(search=None, position=None, status=None) -> pd.DataFrame:
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

    if search:
        sql += " AND (LOWER(applicant_name) LIKE :search OR LOWER(applicant_email) LIKE :search)"
        params["search"] = f"%{search.lower()}%"
    if position and position != "All":
        sql += " AND LOWER(position_applied) = :position"
        params["position"] = position.lower()
    if status and status != "All":
        sql += " AND LOWER(application_status) = :status"
        params["status"] = status.lower()

    sql += " ORDER BY timestamp DESC"

    try:
        engine = get_engine()
        with engine.connect() as conn:
            return pd.read_sql(text(sql), conn, params=params)
    except SQLAlchemyError as e:
        st.error(f"Database error: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=30)
def fetch_analytics() -> dict:
    queries = {
        "by_reason": """
            SELECT reason, COUNT(*) as count
            FROM appointments
            WHERE reason IS NOT NULL
            GROUP BY reason
            ORDER BY count DESC
        """,
        "call_volume": """
            SELECT DATE(timestamp) as date, COUNT(*) as calls
            FROM appointments
            GROUP BY DATE(timestamp)
            ORDER BY date ASC
        """,
        "audit_log": """
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
        """,
    }
    results = {}
    try:
        engine = get_engine()
        with engine.connect() as conn:
            for key, sql in queries.items():
                results[key] = pd.read_sql(text(sql), conn)
    except SQLAlchemyError as e:
        st.error(f"Database error: {e}")
        for key in queries:
            results[key] = pd.DataFrame()
    return results


def update_applicant_status(email: str, new_status: str) -> bool:
    sql = text(
        "UPDATE hiring_applications SET application_status = :status WHERE applicant_email = :email"
    )
    try:
        engine = get_engine()
        with engine.begin() as conn:
            conn.execute(sql, {"status": new_status, "email": email})
        return True
    except SQLAlchemyError as e:
        st.error(f"Update failed: {e}")
        return False
