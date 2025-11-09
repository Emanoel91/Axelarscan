import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime, time as dtime

# ------------------------------- Page config --------------------------------
st.set_page_config(
    page_title="Chain Volume Analytics",
    page_icon="https://axelarscan.io/logos/logo.png",
    layout="wide"
)
st.title("💹 Cross-Chain Volume Analytics (GMPStatsByChains)")

# ------------------------------- Default date range --------------------------
default_start = datetime(2025, 1, 1).date()
default_end = datetime(2026, 1, 1).date()

col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    from_date = st.date_input("Start Date", value=default_start)
with col2:
    to_date = st.date_input("End Date", value=default_end)
with col3:
    st.markdown("<br>", unsafe_allow_html=True)
    run_button = st.button("🔄 Fetch Data")

# ------------------------------- Sidebar Footer -----------------------------
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

# ------------------------------- Helper -------------------------------------
def fetch_gmp_data(from_date, to_date):
    """Fetch data from Axelar GMPStatsByChains API within a given time range."""
    from_ts = int(datetime.combine(from_date, dtime.min).timestamp())
    to_ts = int(datetime.combine(to_date, dtime.max).timestamp())
    url = f"https://api.axelarscan.io/gmp/GMPStatsByChains?fromTime={from_ts}&toTime={to_ts}"

    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return resp.json().get("source_chains", [])
    except Exception as e:
        st.error(f"Error fetching data from API: {e}")
        return []

# ------------------------------- Process Data -------------------------------
def compute_volumes(source_chains):
    """Compute incoming, outgoing, and net volumes for each chain."""
    outgoing = {}
    incoming = {}

    for src in source_chains:
        src_key = src.get("key")
        dests = src.get("destination_chains", [])
        total_out = sum(d.get("volume", 0) for d in dests)
        outgoing[src_key] = outgoing.get(src_key, 0) + total_out

        for d in dests:
            dest_key = d.get("key")
            incoming[dest_key] = incoming.get(dest_key, 0) + d.get("volume", 0)

    df_in = pd.DataFrame(list(incoming.items()), columns=["chain", "volume"])
    df_out = pd.DataFrame(list(outgoing.items()), columns=["chain", "volume"])
    df_combined = pd.merge(df_in, df_out, on="chain", how="outer", suffixes=("_in", "_out")).fillna(0)
    df_combined["net_volume"] = df_combined["volume_in"] - df_combined["volume_out"]
    return df_in, df_out, df_combined

# ------------------------------- Chart Helper -------------------------------
def add_labels(fig, df, column):
    fig.update_traces(text=[f"{v:,.2f}" for v in df[column]], textposition="outside")

# ------------------------------- Main Logic ---------------------------------
if run_button:
    with st.spinner("Fetching data and building charts..."):
        data = fetch_gmp_data(from_date, to_date)

        if not data:
            st.warning("No data returned from API for the selected period.")
        else:
            df_in, df_out, df_comb = compute_volumes(data)

            # ------------------ Chart 1: Incoming volume ------------------
            fig_in = px.bar(
                df_in.sort_values("volume", ascending=True),
                x="volume", y="chain", orientation="h",
                title="📈 Total Incoming Volume (Destination Chains)",
                color="chain", color_discrete_sequence=px.colors.qualitative.Bold
            )
            add_labels(fig_in, df_in.sort_values("volume", ascending=True), "volume")
            fig_in.update_layout(xaxis_title="Volume (USD)", yaxis_title="Destination Chain", showlegend=False)

            # ------------------ Chart 2: Outgoing volume ------------------
            fig_out = px.bar(
                df_out.sort_values("volume", ascending=True),
                x="volume", y="chain", orientation="h",
                title="📉 Total Outgoing Volume (Source Chains)",
                color="chain", color_discrete_sequence=px.colors.qualitative.Safe
            )
            add_labels(fig_out, df_out.sort_values("volume", ascending=True), "volume")
            fig_out.update_layout(xaxis_title="Volume (USD)", yaxis_title="Source Chain", showlegend=False)

            # ------------------ Chart 3: Net volume ------------------
            fig_net = px.bar(
                df_comb.sort_values("net_volume", ascending=True),
                x="net_volume", y="chain", orientation="h",
                title="⚖️ Net Volume (Incoming - Outgoing)",
                color=df_comb["net_volume"].apply(lambda x: "Positive Net" if x >= 0 else "Negative Net"),
                color_discrete_map={"Positive Net": "green", "Negative Net": "red"}
            )
            add_labels(fig_net, df_comb.sort_values("net_volume", ascending=True), "net_volume")
            fig_net.update_layout(xaxis_title="Net Volume (USD)", yaxis_title="Chain", showlegend=True)

            # ------------------ Display charts ------------------
            st.plotly_chart(fig_in, use_container_width=True)
            st.plotly_chart(fig_out, use_container_width=True)
            st.plotly_chart(fig_net, use_container_width=True)
else:
    st.info("👆 Select a date range and click **Fetch Data** to load charts.")
