import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, time as dtime

# ------------------------------ Page setup --------------------------------
st.set_page_config(page_title="Axelarscan Interchain Dashboard",
                   page_icon="https://axelarscan.io/logos/logo.png",
                   layout="wide")
st.title("🌉 Axelar Interchain Dashboard")

# ------------------------------ Chain list --------------------------------
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

# ------------------------------ Filters -----------------------------------
default_start = datetime(2025, 1, 1).date()
default_end = datetime(2025, 11, 1).date()

col1, col2, col3, col4 = st.columns([2,2,2,1.5])
with col1:
    selected_chain = st.selectbox("🔗 Select Chain", chains, index=0)
with col2:
    from_date = st.date_input("Start Date", value=default_start)
with col3:
    to_date = st.date_input("End Date", value=default_end)
with col4:
    timeframe = st.selectbox("🕒 Timeframe", ["day", "week", "month"], index=0)

# ------------------------------ Helper ------------------------------------
def safe_parse_timestamp_series(series):
    nums = pd.to_numeric(series, errors="coerce")
    if nums.notna().any():
        unit = "ms" if nums.max() > 1e11 else "s"
        return pd.to_datetime(nums, unit=unit, errors="coerce")
    return pd.to_datetime(series, errors="coerce")

def fetch_chain_data(chain, role, from_date, to_date):
    base_url = "https://api.axelarscan.io/api/interchainChart"
    dt_from = datetime.combine(from_date, dtime.min)
    dt_to = datetime.combine(to_date, dtime.max)
    params = {
        "fromTime": int(dt_from.timestamp()),
        "toTime": int(dt_to.timestamp()),
        role: chain
    }
    try:
        r = requests.get(base_url, params=params, timeout=40)
        r.raise_for_status()
        data = r.json().get("data", [])
        df = pd.DataFrame(data)
        if not df.empty:
            df["timestamp"] = safe_parse_timestamp_series(df["timestamp"])
            for col in ["num_txs","volume","gmp_num_txs","gmp_volume","transfers_num_txs","transfers_volume"]:
                if col not in df.columns:
                    df[col] = 0
            df = df.fillna(0).sort_values("timestamp")
        return df
    except Exception as e:
        st.error(f"Error fetching {role} data: {e}")
        return pd.DataFrame(columns=["timestamp","num_txs","volume","gmp_num_txs","gmp_volume","transfers_num_txs","transfers_volume"])

# ------------------------------ Fetch both roles ---------------------------
with st.spinner("Fetching data from Axelar API..."):
    df_out = fetch_chain_data(selected_chain, "sourceChain", from_date, to_date)
    df_in = fetch_chain_data(selected_chain, "destinationChain", from_date, to_date)

if df_out.empty and df_in.empty:
    st.warning("No data found for selected range/chain.")
    st.stop()

# ------------------------------ Aggregation ---------------------------
def aggregate(df, timeframe):
    if df.empty:
        return df
    df = df.copy()
    df = df.set_index("timestamp")
    if timeframe == "day":
        df = df.resample("D").sum()
    elif timeframe == "week":
        df = df.resample("W").sum()
    elif timeframe == "month":
        df = df.resample("M").sum()
    df = df.reset_index()
    return df

df_out_agg = aggregate(df_out, timeframe)
df_in_agg = aggregate(df_in, timeframe)

# ------------------------------ KPIs --------------------------------------
total_out_vol = df_out_agg["volume"].sum()
total_in_vol = df_in_agg["volume"].sum()
total_out_txs = df_out_agg["num_txs"].sum()
total_in_txs = df_in_agg["num_txs"].sum()
net_volume = total_in_vol - total_out_vol

st.markdown("### 📊 Key Performance Indicators (KPIs)")
k1, k2, k3 = st.columns(3)
k1.metric("💰 Total Volume", f"${(total_in_vol+total_out_vol):,.2f}")
k2.metric("🔁 Total Transfers", f"{int(total_in_txs+total_out_txs):,}")
k3.metric("⚖️ Net Bridged Volume", f"${net_volume:,.2f}")

# ------------------------------ Chart 1: In vs Out Volume ------------------
vol_df = pd.merge(df_in_agg[["timestamp","volume"]], 
                  df_out_agg[["timestamp","volume"]], 
                  on="timestamp", how="outer", suffixes=("_in","_out")).fillna(0)
vol_df["diff"] = vol_df["volume_in"] - vol_df["volume_out"]

fig_vol = go.Figure()
fig_vol.add_bar(x=vol_df["timestamp"], y=vol_df["volume_in"], name="Inbound Volume", marker_color="#00b894")
fig_vol.add_bar(x=vol_df["timestamp"], y=-vol_df["volume_out"], name="Outbound Volume", marker_color="#d63031")
fig_vol.add_trace(go.Scatter(x=vol_df["timestamp"], y=vol_df["diff"], name="Net Volume", mode="lines", yaxis="y2", line=dict(color="#0984e3", width=2)))
fig_vol.update_layout(title=f"🔹 Inbound & Outbound Volume per {timeframe.capitalize()}",
                      yaxis=dict(title="Volume ($)", side="left"),
                      yaxis2=dict(title="Net Volume ($)", overlaying="y", side="right"),
                      barmode="relative",
                      height=500)
st.plotly_chart(fig_vol, use_container_width=True)

# ------------------------------ Chart 2: Cumulative Net Volume -------------
vol_df["cum_diff"] = vol_df["diff"].cumsum()
fig_cum = px.line(vol_df, x="timestamp", y="cum_diff", title=f"📈 Cumulative Net Volume ({timeframe.capitalize()} Aggregation)", markers=True)
st.plotly_chart(fig_cum, use_container_width=True)

# ------------------------------ Chart 3: Tx Count stacked ------------------
tx_df = pd.merge(df_in_agg[["timestamp","num_txs"]],
                 df_out_agg[["timestamp","num_txs"]],
                 on="timestamp", how="outer", suffixes=("_in","_out")).fillna(0)
tx_df["total"] = tx_df["num_txs_in"] + tx_df["num_txs_out"]

fig_tx = go.Figure()
fig_tx.add_bar(x=tx_df["timestamp"], y=tx_df["num_txs_in"], name="Inbound Tx", marker_color="#74b9ff")
fig_tx.add_bar(x=tx_df["timestamp"], y=tx_df["num_txs_out"], name="Outbound Tx", marker_color="#ffeaa7")
fig_tx.add_trace(go.Scatter(x=tx_df["timestamp"], y=tx_df["total"], name="Total", mode="lines", line=dict(color="#6c5ce7", width=2)))
fig_tx.update_layout(barmode="stack", title=f"🧮 Inbound/Outbound Transaction Counts ({timeframe.capitalize()})")
st.plotly_chart(fig_tx, use_container_width=True)

# ------------------------------ Chart 4: Inbound Ratio ---------------------
tx_df["in_ratio"] = tx_df["num_txs_in"] / tx_df["total"].replace(0,1)
fig_ratio = px.line(tx_df, x="timestamp", y="in_ratio", title=f"📊 Inbound / Total Transaction Ratio ({timeframe.capitalize()})")
fig_ratio.update_yaxes(tickformat=".0%")
st.plotly_chart(fig_ratio, use_container_width=True)

# ------------------------------ Chart 5: Donuts ----------------------------
col_a, col_b = st.columns(2)
with col_a:
    fig_d1 = px.pie(names=["Inbound","Outbound"],
                    values=[total_in_vol, total_out_vol],
                    hole=0.55,
                    title="💵 Volume In vs Out",
                    color_discrete_sequence=["#00b894","#d63031"])
    st.plotly_chart(fig_d1, use_container_width=True)
with col_b:
    fig_d2 = px.pie(names=["Inbound","Outbound"],
                    values=[total_in_txs, total_out_txs],
                    hole=0.55,
                    title="🔁 Transaction Count In vs Out",
                    color_discrete_sequence=["#74b9ff","#ffeaa7"])
    st.plotly_chart(fig_d2, use_container_width=True)

# ------------------------------ Chart 6: Normalized Stacked Bars -----------
vol_norm = pd.DataFrame({
    "Type": ["Inbound","Outbound"],
    "GMP": [df_in_agg["gmp_volume"].sum(), df_out_agg["gmp_volume"].sum()],
    "TokenTransfer": [df_in_agg["transfers_volume"].sum(), df_out_agg["transfers_volume"].sum()]
})
vol_norm["total"] = vol_norm["GMP"] + vol_norm["TokenTransfer"]
for col in ["GMP","TokenTransfer"]:
    vol_norm[col] = vol_norm[col] / vol_norm["total"]

fig_norm_vol = go.Figure()
fig_norm_vol.add_bar(x=vol_norm["Type"], y=vol_norm["GMP"], name="GMP", marker_color="#fd9a57")
fig_norm_vol.add_bar(x=vol_norm["Type"], y=vol_norm["TokenTransfer"], name="Token Transfer", marker_color="#85c2fb")
fig_norm_vol.update_layout(barmode="stack", title="📦 Normalized Volume Share by Service", yaxis_tickformat=".0%")
st.plotly_chart(fig_norm_vol, use_container_width=True)

# ------------------------------ Chart 7: Normalized Tx Share ---------------
tx_norm = pd.DataFrame({
    "Type": ["Inbound","Outbound"],
    "GMP": [df_in_agg["gmp_num_txs"].sum(), df_out_agg["gmp_num_txs"].sum()],
    "TokenTransfer": [df_in_agg["transfers_num_txs"].sum(), df_out_agg["transfers_num_txs"].sum()]
})
tx_norm["total"] = tx_norm["GMP"] + tx_norm["TokenTransfer"]
for col in ["GMP","TokenTransfer"]:
    tx_norm[col] = tx_norm[col] / tx_norm["total"]

fig_norm_tx = go.Figure()
fig_norm_tx.add_bar(x=tx_norm["Type"], y=tx_norm["GMP"], name="GMP", marker_color="#fd9a57")
fig_norm_tx.add_bar(x=tx_norm["Type"], y=tx_norm["TokenTransfer"], name="Token Transfer", marker_color="#85c2fb")
fig_norm_tx.update_layout(barmode="stack", title="📦 Normalized Transaction Count Share by Service", yaxis_tickformat=".0%")
st.plotly_chart(fig_norm_tx, use_container_width=True)
