# 📈 Interchain Chart - Streamlit Dashboard
import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date
import plotly.express as px

# -------------------- PAGE CONFIG --------------------
st.set_page_config(page_title="Axelar Interchain Metrics", layout="wide")

# -------------------- TITLE --------------------
st.title("📈 Interchain Dashboard (Axelar)")

# -------------------- FILTERS (TOP BAR) --------------------
col1, col2, col3, col4 = st.columns(4)

with col1:
    metric_type = st.selectbox(
        "Select Metric Type",
        ["All", "GMP", "Transfers"],
        index=0,
    )

with col2:
    timeframe = st.selectbox(
        "Aggregation",
        ["day", "week", "month"],
        index=0,
    )

with col3:
    start_date = st.date_input(
        "Start Date",
        date(2025, 1, 1)
    )

with col4:
    end_date = st.date_input(
        "End Date",
        date(2026, 1, 1)
    )

# -------------------- FETCH DATA --------------------
API_URL = "https://api.axelarscan.io/interchain/statistics"

try:
    response = requests.get(API_URL, timeout=20)
    response.raise_for_status()
    data = response.json().get("data", [])
except Exception as e:
    st.error(f"❌ Error fetching data: {e}")
    data = []

df = pd.DataFrame(data)

# اگر خالی بود برای جلوگیری از خطا، ستون‌ها را ایجاد می‌کنیم
if df.empty:
    st.warning("No data received from API.")
    df = pd.DataFrame(columns=[
        "timestamp","num_txs","volume",
        "gmp_num_txs","gmp_volume","transfers_num_txs","transfers_volume"
    ])

# -------------------- TIMESTAMP CLEANING --------------------
def parse_timestamp_series(s):
    """Smart timestamp parsing (detects ms/s and handles NaT safely)."""
    if pd.api.types.is_datetime64_any_dtype(s):
        return pd.to_datetime(s)

    nums = pd.to_numeric(s, errors="coerce")
    if nums.notna().any():
        maxv = nums.max()
        unit = "ms" if maxv > 1e11 else "s"
        dt = pd.to_datetime(nums, unit=unit, errors="coerce")
        if dt.notna().sum() == 0:
            return pd.to_datetime(s, errors="coerce")
        return dt

    return pd.to_datetime(s, errors="coerce")

df["timestamp"] = parse_timestamp_series(df.get("timestamp", pd.Series([], dtype="object")))
df = df[~df["timestamp"].isna()].copy()
df = df.sort_values("timestamp").reset_index(drop=True)

# -------------------- SANITIZE NUMERIC COLUMNS --------------------
for col in ["num_txs","volume","gmp_num_txs","gmp_volume","transfers_num_txs","transfers_volume"]:
    if col not in df.columns:
        df[col] = 0
df[["num_txs","volume","gmp_num_txs","gmp_volume","transfers_num_txs","transfers_volume"]] = \
    df[["num_txs","volume","gmp_num_txs","gmp_volume","transfers_num_txs","transfers_volume"]].apply(
        pd.to_numeric, errors="coerce"
    ).fillna(0)

# -------------------- FILTER BY DATE --------------------
mask = (df["timestamp"].dt.date >= start_date) & (df["timestamp"].dt.date <= end_date)
df = df.loc[mask]

# -------------------- AGGREGATION --------------------
if timeframe == "day":
    df_agg = df.copy()
    df_agg["timestamp"] = df_agg["timestamp"].dt.floor("D")
    df_agg = df_agg.groupby("timestamp", as_index=False)[
        ["num_txs","volume","gmp_num_txs","gmp_volume","transfers_num_txs","transfers_volume"]
    ].sum()
elif timeframe == "week":
    df_agg = df.set_index("timestamp").resample("W").sum(numeric_only=True).reset_index()
elif timeframe == "month":
    df_agg = df.set_index("timestamp").resample("M").sum(numeric_only=True).reset_index()
else:
    df_agg = df.copy()

# -------------------- FILTER BY METRIC TYPE --------------------
if metric_type == "All":
    df_agg["Transactions"] = df_agg["num_txs"]
    df_agg["Volume"] = df_agg["volume"]
elif metric_type == "GMP":
    df_agg["Transactions"] = df_agg["gmp_num_txs"]
    df_agg["Volume"] = df_agg["gmp_volume"]
else:
    df_agg["Transactions"] = df_agg["transfers_num_txs"]
    df_agg["Volume"] = df_agg["transfers_volume"]

# -------------------- CHARTS --------------------
col_a, col_b = st.columns(2)

with col_a:
    fig_txs = px.line(
        df_agg, x="timestamp", y="Transactions",
        title=f"{metric_type} Transactions Over Time",
        markers=True
    )
    st.plotly_chart(fig_txs, use_container_width=True)

with col_b:
    fig_vol = px.line(
        df_agg, x="timestamp", y="Volume",
        title=f"{metric_type} Volume Over Time",
        markers=True
    )
    st.plotly_chart(fig_vol, use_container_width=True)

# -------------------- SIDEBAR FOOTER --------------------
st.sidebar.markdown(
    """
    <div style="font-size:13px;color:gray;text-align:left;">
      <div>
        <a href="https://x.com/axelar" target="_blank">
          <img src="https://img.cryptorank.io/coins/axelar1663924228506.png"
               style="width:16px;height:16px;border-radius:50%;
               vertical-align:middle;margin-right:6px;">
          Powered by Axelar
        </a>
      </div>
      <div style="margin-top:6px;">
        <a href="https://x.com/0xeman_raz" target="_blank">
          <img src="https://pbs.twimg.com/profile_images/1841479747332608000/bindDGZQ_400x400.jpg"
               style="width:16px;height:16px;border-radius:50%;
               vertical-align:middle;margin-right:6px;">
          Built by Eman Raz
        </a>
      </div>
    </div>
    """,
    unsafe_allow_html=True
)
