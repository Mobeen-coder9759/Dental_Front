import html as html_lib
import re
import pandas as pd
import streamlit as st

from particle_background import inject_particle_background


# ── Typography / visual design tokens ──────────────────────────────────────
BADGE_STYLES = {
    "new":         ("background:#1A3A5C;color:#4A9FFF;", "NEW"),
    "rescheduled": ("background:#3A2E10;color:#F5A623;", "RESCHEDULED"),
    "cancelled":   ("background:#3A1515;color:#E05252;", "CANCELLED"),
}

HIRING_BADGE_STYLES = {
    "pending":     ("background:#1E2640;color:#7B8CDE;", "PENDING"),
    "shortlisted": ("background:#1A3A2A;color:#2ECC71;", "SHORTLISTED"),
    "rejected":    ("background:#3A1515;color:#E05252;", "REJECTED"),
    "hired":       ("background:#1A3A2A;color:#00E5A0;", "HIRED"),
}

TABLE_ROW_STYLE = """<tr style="transition:background 0.1s;" onmouseover="this.style.background='#20233A'" onmouseout="this.style.background=''">"""
TABLE_TH_STYLE = """<th style="
    text-align:left;
    padding:8px 12px;
    border-bottom:1px solid #2A2D3A;
    font-size:11px;
    font-weight:600;
    color:#6B7080;
    letter-spacing:0.04em;
    text-transform:uppercase;
    white-space:nowrap;
">"""
TABLE_TD_STYLE = """<td style="
    padding:8px 12px;
    border-bottom:1px solid #1E2130;
    white-space:nowrap;
">"""
TABLE_STYLE = """<table style="
    width:100%;
    border-collapse:collapse;
    font-size:12.5px;
    color:#C8CDD8;
    background:#1A1D27;
" """


# ── Privacy & PHI/PII Masking Utilities ────────────────────────────────────
def mask_email(val) -> str:
    """Mask email address for privacy compliance: e.g. j***n@example.com"""
    if pd.isnull(val) or not str(val).strip():
        return "—"
    s = str(val).strip()
    if "@" not in s:
        return s[:2] + "***"
    name, domain = s.split("@", 1)
    if len(name) <= 2:
        masked_name = name[0] + "*"
    else:
        masked_name = name[0] + "*" * (len(name) - 2) + name[-1]
    return f"{masked_name}@{domain}"


def mask_dob(val) -> str:
    """Mask date of birth for HIPAA compliance: e.g. ****-**-15"""
    if pd.isnull(val) or not str(val).strip():
        return "—"
    s = str(val).strip()
    # If standard YYYY-MM-DD
    parts = s.split("-")
    if len(parts) == 3:
        return f"****-**-{parts[2]}"
    return "**/**/****"


def mask_name(val) -> str:
    """Mask full name: e.g. John Doe -> John D."""
    if pd.isnull(val) or not str(val).strip():
        return "—"
    parts = str(val).strip().split()
    if len(parts) == 1:
        return parts[0][0] + "***"
    return f"{parts[0]} {parts[-1][0]}."


def mask_phone(val) -> str:
    """Mask phone number: e.g. ***-***-1234"""
    if pd.isnull(val) or not str(val).strip():
        return "—"
    digits = re.sub(r"\D", "", str(val))
    if len(digits) >= 4:
        return f"***-***-{digits[-4:]}"
    return "***-***-****"


def inject_global_css():
    st.markdown(
        """
        <style>
        /* ── Reset & base ── */
        html, body {
            background-color: #0F1117;
            color: #E8EAF0;
            font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif;
            font-size: 14px;
        }

        .stApp, [data-testid="stAppViewContainer"] {
            background-color: transparent !important;
        }

        /* ── Sidebar ── */
        [data-testid="stSidebar"] {
            background-color: #13151F;
            border-right: 1px solid #2A2D3A;
        }
        [data-testid="stSidebar"] .stMarkdown p,
        [data-testid="stSidebar"] label {
            color: #9AA0B5 !important;
            font-size: 12px;
            letter-spacing: 0.02em;
        }
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {
            color: #E8EAF0;
        }

        /* ── Hide default Streamlit chrome ── */
        #MainMenu, footer, header { visibility: hidden; }
        [data-testid="stDecoration"] { display: none; }

        /* ── Headings ── */
        h1 { font-size: 20px !important; font-weight: 600 !important; color: #E8EAF0 !important; letter-spacing: -0.01em; }
        h2 { font-size: 15px !important; font-weight: 500 !important; color: #B0B8CC !important; }
        h3 { font-size: 13px !important; font-weight: 500 !important; color: #9AA0B5 !important; }

        /* ── KPI card strip ── */
        .kpi-row { display: flex; gap: 12px; margin-bottom: 20px; }
        .kpi-card {
            flex: 1;
            background: #1A1D27;
            border: 1px solid #2A2D3A;
            border-radius: 6px;
            padding: 14px 18px;
        }
        .kpi-label {
            font-size: 11px;
            color: #6B7080;
            font-weight: 500;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            margin-bottom: 6px;
        }
        .kpi-value {
            font-size: 26px;
            font-weight: 700;
            color: #E8EAF0;
            line-height: 1;
        }
        .kpi-sub {
            font-size: 11px;
            color: #6B7080;
            margin-top: 4px;
        }

        /* ── Section divider ── */
        .section-divider {
            border: none;
            border-top: 1px solid #2A2D3A;
            margin: 16px 0;
        }

        /* ── Data table wrapper ── */
        .table-wrapper {
            background: #1A1D27;
            border: 1px solid #2A2D3A;
            border-radius: 6px;
            overflow: hidden;
        }
        .table-header {
            padding: 10px 16px;
            border-bottom: 1px solid #2A2D3A;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .table-title {
            font-size: 12px;
            font-weight: 600;
            color: #9AA0B5;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }
        .table-count {
            font-size: 11px;
            color: #6B7080;
        }

        /* ── Inline badge ── */
        .badge {
            display: inline-block;
            padding: 2px 7px;
            border-radius: 3px;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 0.06em;
        }

        /* ── Streamlit dataframe override ── */
        [data-testid="stDataFrame"] {
            border: none !important;
        }

        /* ── Inputs ── */
        [data-testid="stTextInput"] input,
        [data-testid="stSelectbox"] > div > div,
        [data-testid="stDateInput"] input {
            background-color: #1A1D27 !important;
            border: 1px solid #2A2D3A !important;
            color: #E8EAF0 !important;
            border-radius: 4px !important;
            font-size: 13px !important;
        }

        /* ── Buttons ── */
        .stButton > button {
            background: #1A1D27;
            border: 1px solid #2A2D3A;
            color: #B0B8CC;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
            padding: 5px 14px;
            cursor: pointer;
            transition: border-color 0.15s, color 0.15s;
        }
        .stButton > button:hover {
            border-color: #4A7CFF;
            color: #4A7CFF;
        }

        /* ── Alerts ── */
        .stAlert {
            background: #1A1D27 !important;
            border: 1px solid #2A2D3A !important;
            border-radius: 4px !important;
        }

        /* ── Metric delta ── */
        [data-testid="stMetricDelta"] { font-size: 11px; }

        /* ── Page top padding ── */
        .block-container { padding-top: 24px !important; padding-bottom: 40px !important; }

        /* ── Auto-refresh notice ── */
        .refresh-tag {
            display: inline-block;
            font-size: 10px;
            color: #6B7080;
            background: #1A1D27;
            border: 1px solid #2A2D3A;
            border-radius: 3px;
            padding: 2px 8px;
            margin-left: 8px;
            vertical-align: middle;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Animated particle field behind the entire app (every page calls this
    # function, so every page gets the background).
    inject_particle_background()


def kpi_strip(cards: list[dict]):
    """cards = [{"label": "...", "value": 0, "sub": "..."}, ...]"""
    cols = st.columns(len(cards))
    for col, card in zip(cols, cards):
        with col:
            sub_html = f'<div class="kpi-sub">{card.get("sub", "")}</div>' if card.get("sub") else ""
            st.markdown(
                f"""
                <div class="kpi-card">
                    <div class="kpi-label">{card["label"]}</div>
                    <div class="kpi-value">{card["value"]}</div>
                    {sub_html}
                </div>
                """,
                unsafe_allow_html=True,
            )


def page_header(title: str, subtitle: str = ""):
    col1, col2 = st.columns([4, 1])
    with col1:
        sub_html = f"<p style='color:#6B7080;font-size:12px;margin-top:2px;'>{subtitle}</p>" if subtitle else ""
        st.markdown(
            f"<h1>{title}</h1>{sub_html}",
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        if st.button("↻ Refresh", key=f"refresh_{title}"):
            st.cache_data.clear()
            st.rerun()
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)


def fmt_ts(val) -> str:
    if pd.isnull(val):
        return "—"
    try:
        return pd.to_datetime(val).strftime("%Y-%m-%d %I:%M %p")
    except Exception:
        return str(val)


def fmt_null(val) -> str:
    if pd.isnull(val) or str(val).strip() == "":
        return "—"
    return str(val)


def booking_badge(val: str) -> str:
    key = str(val).lower().strip()
    style, label = BADGE_STYLES.get(key, ("background:#252836;color:#9AA0B5;", html_lib.escape(str(val).upper())))
    return f'<span class="badge" style="{style}">{label}</span>'


def hiring_badge(val: str) -> str:
    key = str(val).lower().strip()
    style, label = HIRING_BADGE_STYLES.get(key, ("background:#252836;color:#9AA0B5;", html_lib.escape(str(val).upper())))
    return f'<span class="badge" style="{style}">{label}</span>'


def code_pill(val) -> str:
    """Render a value as a monospace pill, HTML-escaped, or an em-dash if empty."""
    if val in (None, "", "—") or (isinstance(val, float) and pd.isnull(val)):
        return "—"
    safe = html_lib.escape(str(val))
    return (
        f"<code style='background:#13151F;border:1px solid #2A2D3A;padding:1px 6px;"
        f"border-radius:3px;font-size:11px;color:#7B8CDE;'>{safe}</code>"
    )


def table_header(title: str, count: int):
    st.markdown(
        f"""
        <div class="table-wrapper">
            <div class="table-header">
                <span class="table-title">{title}</span>
                <span class="table-count">{count} records</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def empty_state(msg: str = "No records match the current filters."):
    st.markdown(
        f"""
        <div style="
            background:#1A1D27;
            border:1px solid #2A2D3A;
            border-radius:6px;
            padding:40px;
            text-align:center;
            color:#6B7080;
            font-size:13px;
        ">
            {msg}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_html_table(
    display: pd.DataFrame,
    html_cols: list[str] | None = None,
    mask_phi: bool = False,
):
    """
    Render a DataFrame as a styled HTML table.

    Guard Rails:
    1. Escapes all untrusted raw cell content to prevent XSS.
    2. Supports `mask_phi` to automatically mask sensitive PII/PHI columns (DOB, Email, Phone, Name).
    """
    html_cols = set(html_cols or [])
    safe = display.copy()

    for col in safe.columns:
        if mask_phi:
            col_lower = col.lower()
            if "email" in col_lower:
                safe[col] = safe[col].apply(mask_email)
            elif "dob" in col_lower:
                safe[col] = safe[col].apply(mask_dob)
            elif "name" in col_lower:
                safe[col] = safe[col].apply(mask_name)
            elif "phone" in col_lower:
                safe[col] = safe[col].apply(mask_phone)

        if col not in html_cols:
            safe[col] = safe[col].apply(
                lambda v: html_lib.escape(str(v)) if not pd.isnull(v) else "—"
            )

    safe.columns = [c.replace("_", " ").title() for c in safe.columns]

    table_html = (
        safe.to_html(escape=False, index=False, border=0)
        .replace("<table", TABLE_STYLE)
        .replace("<th>", TABLE_TH_STYLE)
        .replace("<td>", TABLE_TD_STYLE)
        .replace("<tr>", TABLE_ROW_STYLE)
    )
    st.markdown(table_html, unsafe_allow_html=True)


def render_df(df: pd.DataFrame):
    """Render a DataFrame with dark-themed styling (safe, no raw HTML)."""
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )