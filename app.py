import os
import requests
import streamlit as st

st.set_page_config(
    page_title="Dental Dashboard",
    page_icon="🦷",
    layout="wide"
)

st.title("🦷 Dental Dashboard")
st.write("Checking backend connection...")

BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "http://127.0.0.1:8000"
)

try:
    response = requests.get(
        f"{BACKEND_URL}/health",
        timeout=10
    )

    if response.status_code == 200:
        st.success("Backend connected")
    else:
        st.error("Backend returned an error")

except requests.exceptions.RequestException:
    st.error("Could not connect to FastAPI")    