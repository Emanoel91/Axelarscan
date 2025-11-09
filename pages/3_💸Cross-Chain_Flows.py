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
st.title("💸Cross-Chain Flows (GMP Stats)")

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

# ------------------------------- Default date range --------------------------
default_start = datetime(2025, 1, 1).date()
default_end = datetime(2026, 1, 1).date()

col1, col2, col3 = st.columns([2,2,1])
with col1:
    from_date = st.date_input("Start Date", value=default_start)
with col2:
    to_date = st.date_input("End Date", value=default_end)
with col3:
    st.markdown("<br>", unsafe_allow_html=True)
    run_button = st.button("🔄 Fetch Data")

# ------------------------------- Helper Functions ---------------------------
def fetch_gmp_data(from_date, to_date):
    from_ts = int(datetime.combine(from_date, dtime.min).timestamp())
    to_ts = int(datetime.combine(to_date, dtime.max).timestamp())
    url = f"https://api.axelarscan.io/gmp/GMPStatsByChains?fromTime={from_ts}&toTime={to_ts}"
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return resp.json().get("source_chains", [])
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return []

def compute_volumes(source_chains):
    outgoing = {}
    incoming = {}
    for src in source_chains:
        src_key = src.get("key")
        dests = src.get("destination_chains", [])
        total_out = sum(d.get("volume",0) for d in dests)
        outgoing[src_key] = outgoing.get(src_key,0) + total_out
        for d in dests:
            dest_key = d.get("key")
            incoming[dest_key] = incoming.get(dest_key,0) + d.get("volume",0)
    df_in = pd.DataFrame(list(incoming.items()), columns=["chain","volume"])
    df_out = pd.DataFrame(list(outgoing.items()), columns=["chain","volume"])
    df_comb = pd.merge(df_in, df_out, on="chain", how="outer", suffixes=("_in","_out")).fillna(0)
    df_in = df_in[df_in["volume"]>0]
    df_out = df_out[df_out["volume"]>0]
    df_comb = df_comb[(df_comb["volume_in"]>0)|(df_comb["volume_out"]>0)]
    df_comb["net_volume"] = df_comb["volume_in"] - df_comb["volume_out"]
    return df_in, df_out, df_comb

def format_volume(v):
    abs_v = abs(v)
    if abs_v >= 1_000_000_000: return f"{v/1_000_000_000:.2f}B"
    if abs_v >= 1_000_000: return f"{v/1_000_000:.2f}m"
    if abs_v >= 1_000: return f"{v/1_000:.2f}k"
    return f"{v:.2f}"

# ------------------- Bubble Packing Algorithm -------------------------------
def pack_bubbles(sizes, iterations=3000):
    n = len(sizes)
    positions = np.random.rand(n,2)*0.8+0.1
    radii = sizes/2/np.max(sizes)*0.1
    for _ in range(iterations):
        for i in range(n):
            for j in range(i+1,n):
                dx = positions[j,0]-positions[i,0]
                dy = positions[j,1]-positions[i,1]
                dist = np.hypot(dx,dy)
                min_dist = radii[i]+radii[j]+0.005
                if dist < min_dist:
                    if dist==0: dx,dy = np.random.rand(2)-0.5; dist=np.hypot(dx,dy)
                    shift=(min_dist-dist)/2
                    positions[i,0]-=dx/dist*shift
                    positions[i,1]-=dy/dist*shift
                    positions[j,0]+=dx/dist*shift
                    positions[j,1]+=dy/dist*shift
        positions=np.clip(positions,0,1)
    return positions[:,0], positions[:,1]

# ------------------- Bubble Size by Category -------------------------------
def bubble_size_category(v):
    abs_v = abs(v)
    if abs_v < 10: return 20
    elif abs_v < 100: return 30
    elif abs_v < 1_000: return 40
    elif abs_v < 10_000: return 50
    elif abs_v < 100_000: return 60
    elif abs_v < 200_000: return 62
    elif abs_v < 400_000: return 64
    elif abs_v < 600_000: return 66
    elif abs_v < 800_000: return 68
    elif abs_v < 1_000_000: return 70
    elif abs_v < 2_000_000: return 72
    elif abs_v < 4_000_000: return 74
    elif abs_v < 6_000_000: return 76
    elif abs_v < 8_000_000: return 78
    elif abs_v < 10_000_000: return 80
    elif abs_v < 12_000_000: return 82
    elif abs_v < 14_000_000: return 84
    elif abs_v < 16_000_000: return 86
    elif abs_v < 18_000_000: return 88
    elif abs_v < 20_000_000: return 90
    elif abs_v < 25_000_000: return 92
    elif abs_v < 30_000_000: return 94
    elif abs_v < 35_000_000: return 96
    elif abs_v < 40_000_000: return 98
    elif abs_v < 45_000_000: return 99
    elif abs_v < 50_000_000: return 100
    elif abs_v < 60_000_000: return 110
    elif abs_v < 70_000_000: return 120
    elif abs_v < 80_000_000: return 130
    elif abs_v < 90_000_000: return 135
    elif abs_v < 100_000_000: return 140
    elif abs_v < 110_000_000: return 145
    elif abs_v < 120_000_000: return 150
    elif abs_v < 130_000_000: return 155
    elif abs_v < 140_000_000: return 160
    elif abs_v < 150_000_000: return 165
    elif abs_v < 160_000_000: return 170
    elif abs_v < 170_000_000: return 175
    elif abs_v < 180_000_000: return 180
    elif abs_v < 190_000_000: return 185
    else: return 190

# ------------------- Main Logic ---------------------------------------------
if run_button:
    with st.spinner("Fetching data and building charts..."):
        data = fetch_gmp_data(from_date,to_date)
        if not data:
            st.warning("No data returned for selected range.")
        else:
            df_in, df_out, df_comb = compute_volumes(data)

            # ------------------- 1️⃣ Incoming Volume -------------------
            df_in_sorted = df_in.sort_values("volume",ascending=True)
            df_in_sorted["formatted_volume"] = df_in_sorted["volume"].apply(format_volume)
            fig_in = px.bar(
                df_in_sorted,
                x="volume", y="chain", orientation="h",
                title="📈 Total Incoming Volume (Destination Chains)",
                color="chain", color_discrete_sequence=px.colors.qualitative.Bold,
                text="formatted_volume"
            )
            fig_in.update_layout(xaxis_title="Volume (USD)", yaxis_title="Destination Chain",
                                 showlegend=False, height=600)
            fig_in.update_traces(textposition="outside")
            st.plotly_chart(fig_in,use_container_width=True)

            # ------------------- 2️⃣ Outgoing Volume -------------------
            df_out_sorted = df_out.sort_values("volume",ascending=True)
            df_out_sorted["formatted_volume"] = df_out_sorted["volume"].apply(format_volume)
            fig_out = px.bar(
                df_out_sorted,
                x="volume", y="chain", orientation="h",
                title="📉 Total Outgoing Volume (Source Chains)",
                color="chain", color_discrete_sequence=px.colors.qualitative.Safe,
                text="formatted_volume"
            )
            fig_out.update_layout(xaxis_title="Volume (USD)", yaxis_title="Source Chain",
                                  showlegend=False, height=600)
            fig_out.update_traces(textposition="outside")
            st.plotly_chart(fig_out,use_container_width=True)

            # ------------------- 3️⃣ Net Volume -------------------
            df_comb_sorted = df_comb.sort_values("net_volume",ascending=True)
            df_comb_sorted["color"] = df_comb_sorted["net_volume"].apply(lambda x: "green" if x>=0 else "red")
            df_comb_sorted["formatted_volume"] = df_comb_sorted["net_volume"].apply(format_volume)
            fig_net = px.bar(
                df_comb_sorted,
                x="net_volume", y="chain", orientation="h",
                title="⚖️ Net Volume (Incoming - Outgoing)",
                color="color",
                color_discrete_map={"green":"green","red":"red"},
                text="formatted_volume"
            )
            fig_net.update_layout(xaxis_title="Net Volume (USD)", yaxis_title="Chain",
                                  showlegend=False, height=600)
            fig_net.update_traces(textposition="outside")
            st.plotly_chart(fig_net,use_container_width=True)

            # ------------------- 4️⃣ Bubble Chart -------------------
            df_comb_sorted["bubble_size"] = df_comb_sorted["net_volume"].apply(bubble_size_category)
            df_comb_sorted["label"] = df_comb_sorted.apply(lambda r: f"<b>{r['chain']}</b><br>{format_volume(r['net_volume'])}",axis=1)
            df_comb_sorted["x"], df_comb_sorted["y"] = pack_bubbles(df_comb_sorted["bubble_size"].values)

            fig_bubble = go.Figure()
            for _, row in df_comb_sorted.iterrows():
                fig_bubble.add_trace(go.Scatter(
                    x=[row["x"]], y=[row["y"]],
                    mode="markers+text",
                    text=[row["label"]],
                    textposition="middle center",
                    marker=dict(
                        size=row["bubble_size"],
                        color="green" if row["net_volume"]>=0 else "red",
                        opacity=0.7,
                        line=dict(width=2,color="#333")
                    ),
                    textfont=dict(color="white", size=12, family="Arial"),
                    hoverinfo="text"
                ))
            fig_bubble.update_layout(
                title="🫧 Net Volume Bubble Cloud",
                xaxis=dict(visible=False),
                yaxis=dict(visible=False),
                height=550,
                margin=dict(l=20,r=20,t=50,b=20),
                plot_bgcolor="rgba(0,0,0,0)",
                showlegend=False
            )
            st.plotly_chart(fig_bubble,use_container_width=True)
else:
    st.info("👆 Select a date range and click **Fetch Data** to load charts.")
