import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import numpy as np
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

# ------------------- Main Logic ---------------------------------------------
if run_button:
    with st.spinner("Fetching data..."):
        data = fetch_gmp_data(from_date,to_date)
        if not data:
            st.warning("No data returned for selected range.")
        else:
            df_in, df_out, df_comb = compute_volumes(data)

            # ------------------- Bubble Chart -------------------
            df_comb = df_comb.sort_values("net_volume",ascending=True)
            df_comb["abs_volume"] = df_comb["net_volume"].abs()
            max_vol = df_comb["abs_volume"].max()
            # Logarithmic scaling
            df_comb["bubble_size"] = df_comb["abs_volume"].apply(lambda v: 20+100*np.log1p(v)/np.log1p(max_vol))
            df_comb["color"] = df_comb["net_volume"].apply(lambda x: "green" if x>=0 else "red")
            df_comb["label"] = df_comb.apply(lambda r: f"<b>{r['chain']}</b>\n{format_volume(r['net_volume'])}", axis=1)
            df_comb["x"], df_comb["y"] = pack_bubbles(df_comb["bubble_size"].values)

            fig_bubble = go.Figure()
            for _, row in df_comb.iterrows():
                fig_bubble.add_trace(go.Scatter(
                    x=[row["x"]], y=[row["y"]],
                    mode="markers+text",
                    text=[row["label"]],
                    textposition="middle center",
                    marker=dict(
                        size=row["bubble_size"],
                        color=row["color"],
                        opacity=0.7,
                        line=dict(width=2, color="#333")
                    ),
                    textfont=dict(color="white", size=12, family="Arial"),
                    hoverinfo="text"
                ))

            fig_bubble.update_layout(
                title="🫧 Net Volume Bubble Cloud",
                xaxis=dict(visible=False),
                yaxis=dict(visible=False),
                height=700,
                margin=dict(l=20,r=20,t=50,b=20),
                plot_bgcolor="rgba(0,0,0,0)",
                showlegend=False
            )
            st.plotly_chart(fig_bubble,use_container_width=True)
else:
    st.info("👆 Select a date range and click **Fetch Data** to load charts.")
