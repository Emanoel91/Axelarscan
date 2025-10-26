import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import time

# --- Page Config ------------------------------------------------------------------------------------------------------
st.set_page_config(
    page_title="Axelarscan",
    page_icon="https://axelarscan.io/logos/logo.png",
    layout="wide"
)

# --- Title ------------------------------------------------------------------------------------------------------------
st.title("📈 Interchain Chart")

st.info("📊Charts initially display data for a default time range. Select a custom range to view results for your desired period.")
st.info("⏳On-chain data retrieval may take a few moments. Please wait while the results load.")

# --- Sidebar Filters --------------------------------------------------------------------------------------------------
st.sidebar.header("🔍 Filters")

chains = [
    "Avalanche", "Axelarnet", "Ethereum", "Fantom", "Moonbeam", "Polygon", "acre", "agoric",
    "allora", "arbitrum", "archway", "assetmantle", "aura", "babylon", "base", "berachain",
    "binance", "bitsong", "blast", "c4e", "carbon", "celestia", "celo", "centrifuge", "chihuahua",
    "comdex", "cosmoshub", "crescent", "dymension", "e-money", "elys", "evmos", "fetch", "filecoin",
    "flow", "fraxtal", "fxcore", "haqq", "hedera", "hyperliquid", "immutable", "injective", "ixo",
    "jackal", "juno", "kava", "ki", "kujira", "lava", "linea", "mantle", "mantra", "migaloo",
    "neutron", "nolus", "ojo", "optimism", "osmosis", "persistence", "plume", "provenance", "rebus",
    "regen", "saga", "scroll", "secret", "secret-snip", "sei", "sommelier", "stargaze", "stellar",
    "stride", "sui", "teritori", "terra", "terra-2", "umee", "xion", "xpla", "xrpl", "xrpl-evm",
    "zigchain"
]

source_chain = st.sidebar.selectbox("Source Chain", [""] + chains)
destination_chain = st.sidebar.selectbox("Destination Chain", [""] + chains)

col1, col2 = st.sidebar.columns(2)
from_date = col1.date_input("Start Date")
to_date = col2.date_input("End Date")

timeframe = st.sidebar.selectbox("Time Frame", ["day", "week", "month"], index=2)

# --- Sidebar Footer ---------------------------------------------------------------------------------------------------
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

# --- API Request ------------------------------------------------------------------------------------------------------

base_url = "https://api.axelarscan.io/api/interchainChart"
params = {}

if source_chain:
    params["sourceChain"] = source_chain
if destination_chain:
    params["destinationChain"] = destination_chain
if from_date:
    params["fromTime"] = int(time.mktime(datetime.combine(from_date, datetime.min.time()).timetuple()))
if to_date:
    params["toTime"] = int(time.mktime(datetime.combine(to_date, datetime.max.time()).timetuple()))

with st.spinner("Fetching data from Axelar API..."):
    response = requests.get(base_url, params=params)
    data = response.json()["data"]

df = pd.DataFrame(data)
df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")

# --- Time Frame Aggregation --------------------------------------------------------------------------------------------

if timeframe == "week":
    df = df.resample("W", on="timestamp").sum(numeric_only=True)
    df = df.reset_index()
elif timeframe == "month":
    df = df.resample("M", on="timestamp").sum(numeric_only=True)
    df = df.reset_index()
# day = default granularity, no need to resample

# --- KPIs --------------------------------------------------------------------------------------------------------------
total_txs = df["num_txs"].sum()
total_volume = df["volume"].sum()

kpi1, kpi2 = st.columns(2)
kpi1.metric("Total Number of Transfers", f"{total_txs:,.0f}")
kpi2.metric("Total Volume of Transfers", f"{total_volume:,.2f}")

# --- Chart 1: Volume & Number of Transfers Over Time -------------------------------------------------------------------
fig1 = go.Figure()

fig1.add_bar(
    x=df["timestamp"], y=df["num_txs"], name="Number of Transfers", yaxis="y1", opacity=0.6
)

fig1.add_trace(
    go.Scatter(
        x=df["timestamp"], y=df["volume"], name="Volume of Transfers", yaxis="y2", mode="lines+markers"
    )
)

fig1.update_layout(
    title="Volume & Number of Transfers Over Time",
    xaxis=dict(title="Date"),
    yaxis=dict(title="Number of Transfers"),
    yaxis2=dict(title="Volume", overlaying="y", side="right"),
    legend=dict(orientation="h", y=-0.2),
    height=500
)
st.plotly_chart(fig1, use_container_width=True)

# --- Chart 2: Number of Transfers by Service Over Time -----------------------------------------------------------------
fig2 = px.bar(
    df,
    x="timestamp",
    y=["gmp_num_txs", "transfers_num_txs"],
    title="Number of Transfers by Service Over Time",
)
fig2.update_layout(barmode="stack", height=400)
st.plotly_chart(fig2, use_container_width=True)

# --- Chart 3: Volume of Transfers by Service Over Time -----------------------------------------------------------------
fig3 = px.bar(
    df,
    x="timestamp",
    y=["gmp_volume", "transfers_volume"],
    title="Volume of Transfers by Service Over Time",
)
fig3.update_layout(barmode="stack", height=400)
st.plotly_chart(fig3, use_container_width=True)

# --- Chart 4 & 5: Donut Charts ----------------------------------------------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    fig4 = px.pie(
        names=["GMP Transfers", "Token Transfers"],
        values=[df["gmp_num_txs"].sum(), df["transfers_num_txs"].sum()],
        hole=0.6,
        title="Total Number of Transfers by Service"
    )
    st.plotly_chart(fig4, use_container_width=True)

with col2:
    fig5 = px.pie(
        names=["GMP Volume", "Token Transfer Volume"],
        values=[df["gmp_volume"].sum(), df["transfers_volume"].sum()],
        hole=0.6,
        title="Total Volume of Transfers by Service"
    )
    st.plotly_chart(fig5, use_container_width=True)
