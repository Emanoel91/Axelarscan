import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, time as dtime

# -------------------------------- Page config --------------------------------
st.set_page_config(page_title="Axelarscan", page_icon="https://axelarscan.io/logos/logo.png", layout="wide")
st.title("📈 Interchain Chart")
st.info("📊Charts initially display data for a default time range. Select a custom range to view results for your desired period.")
st.info("⏳On-chain data retrieval may take a few moments. Please wait while the results load.")

# ------------------------------- Chains list ---------------------------------
chains = [
    "Avalanche","Axelarnet","Ethereum","Fantom","Moonbeam","Polygon","acre","agoric",
    "allora","arbitrum","archway","assetmantle","aura","babylon","base","berachain",
    "binance","bitsong","blast","c4e","carbon","celestia","celo","centrifuge","chihuahua",
    "comdex","cosmoshub","crescent","dymension","e-money","elys","evmos","fetch","filecoin",
    "flow","fraxtal","fxcore","haqq","hedera","hyperliquid","immutable","injective","ixo",
    "jackal","juno","kava","ki","kujira","lava","linea","mantle","mantra","migaloo",
    "neutron","nolus","ojo","optimism","osmosis","persistence","plume","provenance","rebus",
    "regen","saga","scroll","secret","secret-snip","sei","sommelier","stargaze","stellar",
    "stride","sui","teritori","terra","terra-2","umee","xion","xpla","xrpl","xrpl-evm","zigchain"
]

# ------------------------------- Top filters (not sidebar) -------------------
# Default dates: 2025-01-01 to 2026-01-01
default_start = datetime(2025, 1, 1).date()
default_end = datetime(2026, 1, 1).date()

filter_col = st.container()
with filter_col:
    c1, c2, c3, c4, c5 = st.columns([2,2,2,2,1.2])
    with c1:
        source_chain = st.selectbox("Source Chain", [""] + chains, index=0)
    with c2:
        destination_chain = st.selectbox("Destination Chain", [""] + chains, index=0)
    with c3:
        from_date = st.date_input("Start Date", value=default_start)
    with c4:
        to_date = st.date_input("End Date", value=default_end)
    with c5:
        timeframe = st.selectbox("Time Frame", ["day", "week", "month"], index=2)  # default = month

# --- Sidebar Footer Slightly Left-Aligned ---------------------------------------------------------------------
st.sidebar.markdown(
    """
    <style>
    .sidebar-footer {
        position: fixed;
        bottom: 20px;
        width: 250px;
        font-size: 13px;
        color: gray;
        margin-left: 5px; 
        text-align: left;  
    }
    .sidebar-footer img {
        width: 16px;
        height: 16px;
        vertical-align: middle;
        border-radius: 50%;
        margin-right: 5px;
    }
    .sidebar-footer a {
        color: gray;
        text-decoration: none;
    }
    </style>

    <div class="sidebar-footer">
        <div>
            <a href="https://x.com/axelar" target="_blank">
                <img src="https://img.cryptorank.io/coins/axelar1663924228506.png" alt="Axelar Logo">
                Powered by Axelar
            </a>
        </div>
        <div style="margin-top: 5px;">
            <a href="https://x.com/0xeman_raz" target="_blank">
                <img src="https://pbs.twimg.com/profile_images/1841479747332608000/bindDGZQ_400x400.jpg" alt="Eman Raz">
                Built by Eman Raz
            </a>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# ------------------------------- Helper: timestamp parsing -------------------
def safe_parse_timestamp_series(series):
    """
    ورودی می‌تواند: عدد ثانیه، عدد میلی‌ثانیه یا رشته ISO باشد.
    تابع تشخیص می‌دهد و pd.to_datetime با unit مناسب فراخوانی می‌شود.
    در صورت خطا، مقادیر نامعتبر به NaT تبدیل می‌شوند.
    """
    # اگر قبلاً series از نوع datetime باشد، برگردان
    if pd.api.types.is_datetime64_any_dtype(series):
        return pd.to_datetime(series)

    # تلاش برای تفسیر اعداد
    nums = pd.to_numeric(series, errors="coerce")
    if nums.notna().any():
        maxv = nums.max()
        # تشخیص میلی‌ثانیه یا ثانیه براساس بزرگی عدد
        if maxv > 1e11:
            unit = "ms"
        else:
            unit = "s"
        dt = pd.to_datetime(nums, unit=unit, errors="coerce")
        # اگر تقریباً همه NaT شد، احتمالاً رشته ISO هستند — تلاش دوباره
        if dt.notna().sum() == 0:
            return pd.to_datetime(series, errors="coerce")
        return dt

    # اگر به صورت رشته ISO باشد
    return pd.to_datetime(series, errors="coerce")

# ------------------------------- Build API params ----------------------------
base_url = "https://api.axelarscan.io/api/interchainChart"
params = {}
if source_chain:
    params["sourceChain"] = source_chain
if destination_chain:
    params["destinationChain"] = destination_chain

# convert from_date/to_date to unix (seconds)
if from_date:
    dt_from = datetime.combine(from_date, dtime.min)
    params["fromTime"] = int(dt_from.timestamp())
if to_date:
    dt_to = datetime.combine(to_date, dtime.max)
    params["toTime"] = int(dt_to.timestamp())

# ------------------------------- Fetch data ---------------------------------
with st.spinner("Fetching data from Axelar API..."):
    try:
        resp = requests.get(base_url, params=params, timeout=30)
        resp.raise_for_status()
        payload = resp.json()
        data = payload.get("data", [])
    except Exception as e:
        st.error(f"Error fetching data from API: {e}")
        data = []

# ------------------------------- DataFrame ---------------------------------
df = pd.DataFrame(data)

# If empty, create placeholder columns to avoid later crashes
if df.empty:
    st.warning("No data returned from API for the selected filters/range.")
    df = pd.DataFrame(columns=["timestamp","num_txs","volume","gmp_num_txs","gmp_volume","transfers_num_txs","transfers_volume"])

# --- IMPORTANT FIX:
# Overwrite (or create) single 'timestamp' column with parsed datetimes
# (this avoids creating duplicate column labels)
df["timestamp"] = safe_parse_timestamp_series(df.get("timestamp", pd.Series(dtype="object")))

# drop rows with invalid timestamp
df = df[~df["timestamp"].isna()].copy()

# ensure numeric columns exist (if missing from API, fill with zeros)
for col in ["num_txs","volume","gmp_num_txs","gmp_volume","transfers_num_txs","transfers_volume"]:
    if col not in df.columns:
        df[col] = 0

# Convert numeric columns properly
num_cols = ["num_txs","volume","gmp_num_txs","gmp_volume","transfers_num_txs","transfers_volume"]
df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce").fillna(0)

# Sort by timestamp and reset index
df = df.sort_values("timestamp").reset_index(drop=True)

# ------------------------------- Aggregation by timeframe -------------------
if timeframe == "day":
    df_agg = df.copy()
    df_agg["timestamp"] = pd.to_datetime(df_agg["timestamp"].dt.floor("D"))
    df_agg = df_agg.groupby("timestamp", as_index=False)[num_cols].sum()
elif timeframe == "week":
    df_agg = df.copy()
    df_agg = df_agg.set_index("timestamp").resample("W").sum(numeric_only=True).reset_index()
elif timeframe == "month":
    df_agg = df.copy()
    df_agg = df_agg.set_index("timestamp").resample("M").sum(numeric_only=True).reset_index()
else:
    df_agg = df.copy()

# If aggregation produced empty df (e.g. after filtering), create zeros to avoid plotting errors
if df_agg.empty:
    df_agg = pd.DataFrame({
        "timestamp": pd.to_datetime([]),
        "num_txs": pd.Series(dtype="int"),
        "volume": pd.Series(dtype="float"),
        "gmp_num_txs": pd.Series(dtype="int"),
        "gmp_volume": pd.Series(dtype="float"),
        "transfers_num_txs": pd.Series(dtype="int"),
        "transfers_volume": pd.Series(dtype="float"),
    })

# ------------------------------- KPIs --------------------------------------
total_txs = int(df_agg["num_txs"].sum()) if not df_agg.empty else 0
total_volume = float(df_agg["volume"].sum()) if not df_agg.empty else 0.0

col1, col2 = st.columns(2)

with col1:
    st.markdown(
        f"""
        <div style="background-color:#ffffff; padding:20px; border-radius:15px; text-align:center; box-shadow:0 4px 10px rgba(0,0,0,0.05);">
            <h2 style="color:#1f77b4; font-size:22px; margin-bottom:5px;">Total Number of Transfers</h2>
            <h1 style="color:#1f77b4; font-size:48px; font-weight:bold;">{total_txs:,}</h1>
        </div>
        """,
        unsafe_allow_html=True
    )

with col2:
    st.markdown(
        f"""
        <div style="background-color:#ffffff; padding:20px; border-radius:15px; text-align:center; box-shadow:0 4px 10px rgba(0,0,0,0.05);">
            <h2 style="color:#006400; font-size:22px; margin-bottom:5px;">Total Volume of Transfers</h2>
            <h1 style="color:#006400; font-size:48px; font-weight:bold;">${total_volume:,.2f}</h1>
        </div>
        """,
        unsafe_allow_html=True
    )
# ------------------------------- Chart 1: Number (bar) & Volume (line) -----
fig1 = go.Figure()

fig1.add_bar(x=df_agg["timestamp"], y=df_agg["num_txs"], name="Number of Transfers", yaxis="y1", opacity=0.75, marker_color="#178eff")
fig1.add_trace(go.Scatter(x=df_agg["timestamp"], y=df_agg["volume"], name="Volume of Transfers", yaxis="y2", mode="lines", line=dict(color="#f96819", width=2),
        marker=dict(color="#006400")))
fig1.update_layout(title="Volume & Number of Transfers Over Time", xaxis=dict(title="Date"), yaxis=dict(title="Txns count"), yaxis2=dict(title="$USD", overlaying="y", side="right"),
    legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5), height=480)
st.plotly_chart(fig1, use_container_width=True)


# ------------------------------- Chart 2: Number by service (stacked) ------
fig2 = px.bar(df_agg, x="timestamp", y=["gmp_num_txs", "transfers_num_txs"], title="Number of Transfers by Service Over Time",
             labels={"value": "Txns count", "variable": "Service", "timestamp": "Date"}, color_discrete_map={"gmp_num_txs": "#fd9a57", "transfers_num_txs": "#85c2fb"})
fig2.for_each_trace(lambda t: t.update(name="GMP" if t.name == "gmp_num_txs" else "Token Transfer"))
fig2.update_layout(barmode="stack", height=450)
st.plotly_chart(fig2, use_container_width=True)

# ------------------------------- Chart 3: Volume by service (stacked) ------
fig3 = px.bar(df_agg, x="timestamp", y=["gmp_volume", "transfers_volume"], title="Volume of Transfers by Service Over Time ($USD)",
    labels={"value": "Volume ($USD)", "variable": "Service", "timestamp": "Date"}, color_discrete_map={"gmp_volume": "#fd9a57", "transfers_volume": "#85c2fb"})
fig3.for_each_trace(lambda t: t.update(name="GMP" if t.name == "gmp_volume" else "Token Transfer"))
fig3.update_layout(barmode="stack", height=450)
st.plotly_chart(fig3, use_container_width=True)

# ------------------------------- Donut charts --------------------------------
col_a, col_b = st.columns(2)

with col_a:
    vals_num = [df_agg["gmp_num_txs"].sum(), df_agg["transfers_num_txs"].sum()]
    fig4 = px.pie(names=["GMP", "Token Transfers"], values=vals_num, hole=0.55, title="Total Number of Transfers by Service", color_discrete_sequence=["#fd9a57", "#85c2fb"])
    st.plotly_chart(fig4, use_container_width=True)

with col_b:
    vals_vol = [df_agg["gmp_volume"].sum(), df_agg["transfers_volume"].sum()]
    fig5 = px.pie(names=["GMP", "Token Transfer"], values=vals_vol, hole=0.55, title="Total Volume of Transfers by Service ($USD)", color_discrete_sequence=["#fd9a57", "#85c2fb"])
    st.plotly_chart(fig5, use_container_width=True)

