import pandas as pd
import streamlit as st
import plotly.express as px
import hashlib
from datetime import datetime

st.set_page_config(page_title="Enterprise Reconciliation System", layout="wide")

# ================= LOGIN (DEPLOY SAFE) =================

# Store users (hashed password)
USERS = {
    "admin": hashlib.sha256("admin123".encode()).hexdigest(),
    "siddhi": hashlib.sha256("#siddhi2007".encode()).hexdigest()
}

def check_login(username, password):
    if username in USERS:
        return USERS[username] == hashlib.sha256(password.encode()).hexdigest()
    return False


def login():
    st.title("🔐 Login")

    user = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if check_login(user, password):
            st.session_state["logged_in"] = True
        else:
            st.error("Invalid credentials")


# Session
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    login()
    st.stop()

# ================= DASHBOARD =================

st.title("💼 Enterprise Reconciliation Dashboard")

# Logout
if st.button("🚪 Logout"):
    st.session_state["logged_in"] = False
    st.rerun()

# Theme
theme = st.sidebar.selectbox("🎨 Theme", ["Light", "Dark"])

if theme == "Dark":
    st.markdown(
        """
        <style>
        .stApp {
            background-color: #0E1117;
            color: white;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

# Upload
col1, col2 = st.columns(2)

with col1:
    bank_file = st.file_uploader("📂 Upload Bank File", type=["csv"])

with col2:
    gateway_file = st.file_uploader("📂 Upload Gateway File", type=["csv"])

if bank_file and gateway_file:

    bank = pd.read_csv(bank_file)
    gateway = pd.read_csv(gateway_file)

    # Convert date
    bank["date"] = pd.to_datetime(bank["date"])
    gateway["date"] = pd.to_datetime(gateway["date"])

    # Merge
    merged = bank.merge(
        gateway,
        on="transaction_id",
        how="outer",
        suffixes=('_bank', '_gateway'),
        indicator=True
    )

    # Status logic
    def get_status(row):
        if row["_merge"] == "left_only":
            return "Missing in Gateway"
        elif row["_merge"] == "right_only":
            return "Missing in Bank"
        elif row["amount_bank"] != row["amount_gateway"]:
            return "Amount Mismatch"
        else:
            return "Matched"

    merged["Status"] = merged.apply(get_status, axis=1)

    mismatch = merged[merged["Status"] != "Matched"]

    # Filters
    st.sidebar.header("🎯 Filters")

    min_amount = st.sidebar.number_input("Min Amount", value=0)
    max_amount = st.sidebar.number_input("Max Amount", value=10000)

    start_date = st.sidebar.date_input("Start Date", value=datetime(2024, 1, 1))
    end_date = st.sidebar.date_input("End Date", value=datetime(2024, 12, 31))

    filtered = mismatch[
        (mismatch["amount_bank"].fillna(0) >= min_amount) &
        (mismatch["amount_bank"].fillna(0) <= max_amount) &
        (mismatch["date_bank"] >= pd.to_datetime(start_date)) &
        (mismatch["date_bank"] <= pd.to_datetime(end_date))
    ]

    # Metrics
    col1, col2, col3 = st.columns(3)

    col1.metric("Total Records", len(merged))
    col2.metric("Matched", len(merged) - len(mismatch))
    col3.metric("Mismatched", len(mismatch))

    st.divider()

    # Alert
    if len(mismatch) > 0:
        st.error(f"⚠️ {len(mismatch)} mismatches detected!")
    else:
        st.success("✅ All transactions matched")

    # Pie Chart
    st.subheader("📊 Status Distribution")
    fig = px.pie(merged, names="Status")
    st.plotly_chart(fig, use_container_width=True)

    # Trend
    st.subheader("📈 Daily Trend")
    trend = merged.groupby(merged["date_bank"].dt.date)["transaction_id"].count()
    st.line_chart(trend)

    # Table
    st.subheader("📋 Detailed Report")
    st.dataframe(filtered, use_container_width=True)

    # Download
    csv = filtered.to_csv(index=False).encode("utf-8")

    st.download_button(
        "📥 Download Report",
        data=csv,
        file_name="reconciliation_report.csv",
        mime="text/csv"
    )

    # Insights
    st.subheader("🤖 Insights")

    high_value = mismatch[mismatch["amount_bank"].fillna(0) > 2000]
    issue_breakdown = mismatch["Status"].value_counts()

    st.write("🔴 High Value Issues:", len(high_value))
    st.write("📊 Issue Breakdown:")
    st.write(issue_breakdown)

    st.dataframe(high_value, use_container_width=True)

else:
    st.info("👆 Upload both files to continue")