import streamlit as st
import pandas as pd
import requests
import plotly.express as px
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

    df_in = df_in[df_in["volume"] > 0]
    df_out = df_out[df_out["volume"] > 0]
    df_combined = df_combined[(df_combined["volume_in"] > 0) | (df_combined["volume_out"] > 0)]

    df_combined["net_volume"] = df_combined["volume_in"] - df_combined["volume_out"]
    return df_in, df_out, df_combined

# ------------------------------- Bubble Packing Helper ----------------------
def pack_bubbles(sizes, width=1.0, height=1.0, padding=0.01, iterations=2000):
    """Force-directed bubble packing."""
    n = len(sizes)
    positions = np.random.rand(n, 2) * 0.8 + 0.1  # start in center area
    radii = sizes / 2 / max(sizes) * 0.1  # normalized radii

    for _ in range(iterations):
        for i in range(n):
            for j in range(i+1, n):
                dx = positions[j,0] - positions[i,0]
                dy = positions[j,1] - positions[i,1]
                dist = np.hypot(dx, dy)
                min_dist = radii[i] + radii[j] + padding
                if dist < min_dist:
                    if dist == 0:
                        dx, dy = np.random.rand(2)-0.5
                        dist = np.hypot(dx, dy)
                    shift = (min_dist - dist)/2
                    positions[i,0] -= dx/dist*shift
                    positions[i,1] -= dy/dist*shift
                    positions[j,0] += dx/dist*shift
                    positions[j,1] += dy/dist*shift
        positions = np.clip(positions, 0, 1)
    return positions[:,0], positions[:,1]

# ------------------------------- Main Logic ---------------------------------
if run_button:
    with st.spinner("Fetching data and building charts..."):
        data = fetch_gmp_data(from_date, to_date)

        if not data:
            st.warning("No data returned from API for the selected period.")
        else:
            df_in, df_out, df_comb = compute_volumes(data)

            # Bar Charts
            df_in_sorted = df_in.sort_values("volume", ascending=True)
            fig_in = px.bar(
                df_in_sorted,
                x="volume", y="chain", orientation="h",
                title="📈 Total Incoming Volume (Destination Chains)",
                color="chain", color_discrete_sequence=px.colors.qualitative.Bold,
                text=df_in_sorted["volume"].round(2)
            )
            fig_in.update_layout(xaxis_title="Volume (USD)", yaxis_title="Destination Chain",
                                 showlegend=False, height=600)
            fig_in.update_traces(textposition="outside")

            df_out_sorted = df_out.sort_values("volume", ascending=True)
            fig_out = px.bar(
                df_out_sorted,
                x="volume", y="chain", orientation="h",
                title="📉 Total Outgoing Volume (Source Chains)",
                color="chain", color_discrete_sequence=px.colors.qualitative.Safe,
                text=df_out_sorted["volume"].round(2)
            )
            fig_out.update_layout(xaxis_title="Volume (USD)", yaxis_title="Source Chain",
                                  showlegend=False, height=600)
            fig_out.update_traces(textposition="outside")

            df_comb_sorted = df_comb.sort_values("net_volume", ascending=True)
            df_comb_sorted["color"] = df_comb_sorted["net_volume"].apply(lambda x: "red" if x < 0 else "green")

            fig_net = px.bar(
                df_comb_sorted,
                x="net_volume", y="chain", orientation="h",
                title="⚖️ Net Volume (Incoming - Outgoing)",
                color="color",
                color_discrete_map={"green": "green", "red": "red"},
                text=df_comb_sorted["net_volume"].round(2)
            )
            fig_net.update_layout(xaxis_title="Net Volume (USD)", yaxis_title="Chain",
                                  showlegend=False, height=600)
            fig_net.update_traces(textposition="outside")

            # ------------------- Bubble Chart -------------------
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

            df_comb_sorted["abs_volume"] = df_comb_sorted["net_volume"].abs()
            df_comb_sorted["bubble_size"] = df_comb_sorted["abs_volume"].apply(
                lambda v: 20 + 100*np.log1p(v)/np.log1p(df_comb_sorted["abs_volume"].max())
            )
            df_comb_sorted["color"] = df_comb_sorted["net_volume"].apply(lambda x: "green" if x >=0 else "red")
            df_comb_sorted["label"] = df_comb_sorted.apply(
                lambda r: f"<b>{r['chain']}</b>\n{format_volume(r['net_volume'])}", axis=1
            )

            df_comb_sorted["x"], df_comb_sorted["y"] = pack_bubbles(df_comb_sorted["bubble_size"].values)

            fig_bubble = go.Figure()
            for _, row in df_comb_sorted.iterrows():
                fig_bubble.add_trace(go.Scatter(
                    x=[row["x"]],
                    y=[row["y"]],
                    mode="markers+text",
                    text=[row["label"]],
                    textposition="middle center",
                    marker=dict(
                        size=row["bubble_size"],
                        color=row["color"],
                        opacity=0.8,
                        line=dict(width=2, color="blue")
                    ),
                    textfont=dict(color="black", size=12, family="Arial"),
                    hoverinfo="text"
                ))

            fig_bubble.update_layout(
                title="🫧 Net Volume Bubble Cloud (Positive vs Negative)",
                xaxis=dict(visible=False),
                yaxis=dict(visible=False),
                height=700,
                showlegend=False,
                margin=dict(l=20,r=20,t=50,b=20),
                plot_bgcolor="rgba(0,0,0,0)"
            )

            st.plotly_chart(fig_in, use_container_width=True)
            st.plotly_chart(fig_out, use_container_width=True)
            st.plotly_chart(fig_net, use_container_width=True)
            st.plotly_chart(fig_bubble, use_container_width=True)

else:
    st.info("👆 Select a date range و click **Fetch Data** to load charts.")
