import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime, time as dtime
import numpy as np

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

# ------------------------------- Helper: Fetch API --------------------------
def fetch_gmp_data(from_date, to_date):
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

# ------------------------------- Helper: Process Data -----------------------
def compute_volumes(source_chains):
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
    df_combined = df_combined[(df_combined["volume_in"] > 0) | (df_combined["volume_out"] > 0)]
    df_combined["net_volume"] = df_combined["volume_in"] - df_combined["volume_out"]
    return df_in[df_in["volume"]>0], df_out[df_out["volume"]>0], df_combined

# ------------------------------- Format Numbers -----------------------------
def format_volume(v):
    abs_v = abs(v)
    if abs_v >= 1_000_000_000:
        return f"{v/1_000_000_000:.2f}B"
    elif abs_v >= 1_000_000:
        return f"{v/1_000_000:.2f}m"
    elif abs_v >= 1_000:
        return f"{v/1_000:.2f}k"
    else:
        return f"{v:.2f}"

# ------------------------------- Main Logic ---------------------------------
if run_button:
    with st.spinner("Fetching data and building charts..."):
        data = fetch_gmp_data(from_date, to_date)
        if not data:
            st.warning("No data returned from API for the selected period.")
        else:
            df_in, df_out, df_comb = compute_volumes(data)

            # ---------------- Incoming Volume Chart ----------------
            fig_in = go.Figure()
            for _, row in df_in.sort_values("volume").iterrows():
                fig_in.add_trace(go.Bar(
                    x=[row["volume"]],
                    y=[row["chain"]],
                    orientation='h',
                    text=[f"{row['volume']:.2f}"],
                    textposition='outside',
                    marker_color='blue'
                ))
            fig_in.update_layout(title="📈 Total Incoming Volume (Destination Chains)",
                                 xaxis_title="Volume (USD)", yaxis_title="Destination Chain",
                                 height=900)

            # ---------------- Outgoing Volume Chart ----------------
            fig_out = go.Figure()
            for _, row in df_out.sort_values("volume").iterrows():
                fig_out.add_trace(go.Bar(
                    x=[row["volume"]],
                    y=[row["chain"]],
                    orientation='h',
                    text=[f"{row['volume']:.2f}"],
                    textposition='outside',
                    marker_color='orange'
                ))
            fig_out.update_layout(title="📉 Total Outgoing Volume (Source Chains)",
                                  xaxis_title="Volume (USD)", yaxis_title="Source Chain",
                                  height=900)

            # ---------------- Net Volume Chart ----------------
            fig_net = go.Figure()
            for _, row in df_comb.sort_values("net_volume").iterrows():
                color = "green" if row["net_volume"] >=0 else "red"
                fig_net.add_trace(go.Bar(
                    x=[row["net_volume"]],
                    y=[row["chain"]],
                    orientation='h',
                    text=[f"{row['net_volume']:.2f}"],
                    textposition='outside',
                    marker_color=color
                ))
            fig_net.update_layout(title="⚖️ Net Volume (Incoming - Outgoing)",
                                  xaxis_title="Net Volume (USD)", yaxis_title="Chain",
                                  height=900)

            # ---------------- Force-Directed Bubble Chart ----------------
            df_comb["abs_volume"] = df_comb["net_volume"].abs()
            max_vol = df_comb["abs_volume"].max()
            df_comb["size"] = df_comb["abs_volume"].apply(lambda v: 20 + (v/max_vol)*80)
            df_comb["color"] = df_comb["net_volume"].apply(lambda x: "green" if x>=0 else "red")
            df_comb["label"] = df_comb.apply(lambda r: f"{r['chain']}\n{format_volume(r['net_volume'])}", axis=1)

            # Force-directed layout using simple iterative repulsion/attraction
            n = len(df_comb)
            np.random.seed(0)
            pos = np.random.rand(n,2)
            sizes = df_comb["size"].values
            for _ in range(200):  # iterations
                for i in range(n):
                    for j in range(i+1,n):
                        dx = pos[j,0]-pos[i,0]
                        dy = pos[j,1]-pos[i,1]
                        dist = np.sqrt(dx**2 + dy**2)
                        min_dist = (sizes[i]+sizes[j])/200
                        if dist<1e-2:
                            dist=1e-2
                        if dist<min_dist:
                            move = (min_dist-dist)/2
                            angle = np.arctan2(dy,dx)
                            pos[i,0]-=np.cos(angle)*move
                            pos[i,1]-=np.sin(angle)*move
                            pos[j,0]+=np.cos(angle)*move
                            pos[j,1]+=np.sin(angle)*move
            df_comb["x"]=pos[:,0]
            df_comb["y"]=pos[:,1]

            fig_bubble = go.Figure()
            for _, row in df_comb.iterrows():
                fig_bubble.add_trace(go.Scatter(
                    x=[row["x"]], y=[row["y"]],
                    mode="markers+text",
                    marker=dict(size=row["size"], color=row["color"], opacity=0.8, line=dict(width=2,color="blue")),
                    text=[row["label"]],
                    textposition="middle center",
                    textfont=dict(color="black", size=12),
                    hoverinfo="text"
                ))
            fig_bubble.update_layout(title="🫧 Net Volume Bubble Cloud (Force-Directed)",
                                     xaxis=dict(visible=False), yaxis=dict(visible=False),
                                     height=600, showlegend=False, plot_bgcolor="rgba(0,0,0,0)")

            # ---------------- Display all charts ----------------
            st.plotly_chart(fig_in, use_container_width=True)
            st.plotly_chart(fig_out, use_container_width=True)
            st.plotly_chart(fig_net, use_container_width=True)
            st.plotly_chart(fig_bubble, use_container_width=True)

else:
    st.info("👆 Select a date range and click **Fetch Data** to load charts.")
