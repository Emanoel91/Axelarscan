import streamlit as st
import pandas as pd
import requests
import plotly.express as px

# -------------------------------- Page config --------------------------------
st.set_page_config(page_title="Axelar Chain KPIs", layout="wide")
st.title("🔗 Axelar – All-Time Interchain KPIs by Chain")

# ------------------------------- Chains list ---------------------------------
chains = [
    "Avalanche","Axelarnet","Ethereum","Fantom","Moonbeam","Polygon","acre","agoric",
    "allora","arbitrum","archway","assetmantle","aura","babylon","base","berachain",
    "binance","bitsong","blast","c4e","carbon","celestia","celo","centrifuge","chihuahua",
    "comdex","cosmoshub","crescent","dymension","e-money","elys","evmos","fetch","filecoin",
    "flow","fraxtal","fxcore","haqq","hedera","hyperliquid","immutable","injective","ixo",
    "jackal","juno","kava","ki","kujira","lava","linea","mantle","mantra","migaloo","monad",
    "neutron","nolus","ojo","optimism","osmosis","persistence","plume","provenance","rebus",
    "regen","saga","scroll","secret","secret-snip","sei","sommelier","stargaze","stellar",
    "stride","sui","teritori","terra","terra-2","umee","xion","xpla","xrpl","xrpl-evm","zigchain"
]

BASE_URL = "https://api.axelarscan.io/api/interchainChart"

# ------------------------------- Helpers -------------------------------------
def net_color(v):
    if v > 0:
        return "color: green; font-weight: 700;"
    elif v < 0:
        return "color: red; font-weight: 700;"
    return "color: gray;"

def safe_sum(df, col):
    return float(df[col].sum()) if col in df.columns else 0.0

# ------------------------------- Fetch data ----------------------------------
@st.cache_data(show_spinner=False)
def fetch_chain(chain, mode):
    params = {"sourceChain": chain} if mode == "source" else {"destinationChain": chain}
    try:
        r = requests.get(BASE_URL, params=params, timeout=30)
        r.raise_for_status()
        data = r.json().get("data", [])
    except Exception:
        data = []

    if not data:
        return {"Transfers": 0.0, "Volume": 0.0}

    df = pd.DataFrame(data).fillna(0)

    return {
        "Transfers": safe_sum(df, "num_txs"),
        "Volume": safe_sum(df, "volume"),
    }

# ------------------------------- Build main table -----------------------------
rows = []

with st.spinner("Fetching all chains data..."):
    for chain in chains:
        out_ = fetch_chain(chain, "source")
        in_  = fetch_chain(chain, "destination")

        rows.append({
            "Chain": chain,

            # Calculated KPIs
            "Total Transfers": out_["Transfers"] + in_["Transfers"],
            "Total Volume ($)": out_["Volume"] + in_["Volume"],
            "Net Volume ($)": in_["Volume"] - out_["Volume"],

            # Raw
            "Output Transfers": out_["Transfers"],
            "Output Volume ($)": out_["Volume"],
            "Input Transfers": in_["Transfers"],
            "Input Volume ($)": in_["Volume"],
        })

df = pd.DataFrame(rows).sort_values("Chain").reset_index(drop=True)

# ------------------------------- Formatting table -----------------------------
num_cols = df.select_dtypes("number").columns
df[num_cols] = df[num_cols].round(2)

# index from 1
df.index = df.index + 1

# ------------------------------- Display table --------------------------------
st.subheader("📋 Interchain Flow Table")

st.dataframe(
    df.style.applymap(net_color, subset=["Net Volume ($)"]),
    use_container_width=True
)

# ------------------------------- Bar charts -----------------------------------
st.subheader("📊 Chains Ranking")

c1, c2 = st.columns(2)

with c1:
    fig = px.bar(
        df.sort_values("Total Transfers", ascending=False),
        x="Chain", y="Total Transfers",
        title="Chains by Total Transfers"
    )
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

with c2:
    fig = px.bar(
        df.sort_values("Total Volume ($)", ascending=False),
        x="Chain", y="Total Volume ($)",
        title="Chains by Total Volume ($)"
    )
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

# ------------------------------- Donut distributions --------------------------
st.subheader("🍩 Distribution by Ranges")

transfer_bins = [0,10,50,100,500,1000,5000,10000,20000,50000,1e12]
transfer_labels = [
    "<10","11–50","51–100","101–500","501–1000","1001–5000",
    "5001–10000","10001–20000","20001–50000",">50000"
]

volume_bins = [0,10,100,1e3,1e4,1e5,1e6,1e7,1e8,5e8,1e9,1e12]
volume_labels = [
    "<$10","$10–100","$100–1k","$1k–10k","$10k–100k",
    "$100k–1m","$1m–10m","$10m–100m","$100m–500m",
    "$500m–1b",">$1b"
]

df["Transfer Range"] = pd.cut(df["Total Transfers"], bins=transfer_bins, labels=transfer_labels)
df["Volume Range"] = pd.cut(df["Total Volume ($)"], bins=volume_bins, labels=volume_labels)

d1, d2 = st.columns(2)

with d1:
    fig = px.pie(
        df["Transfer Range"].value_counts().reset_index(),
        names="index", values="Transfer Range",
        hole=0.55,
        title="Chains by Total Transfers Range"
    )
    st.plotly_chart(fig, use_container_width=True)

with d2:
    fig = px.pie(
        df["Volume Range"].value_counts().reset_index(),
        names="index", values="Volume Range",
        hole=0.55,
        title="Chains by Total Volume Range"
    )
    st.plotly_chart(fig, use_container_width=True)

# ------------------------------- Tables per range -----------------------------
st.subheader("📋 Chains per Transfer Range")
for r in transfer_labels:
    sub = df[df["Transfer Range"] == r]
    if not sub.empty:
        st.markdown(f"**{r} Transfers**")
        st.dataframe(sub[["Chain", "Total Transfers"]], use_container_width=True)

st.subheader("📋 Chains per Volume Range")
for r in volume_labels:
    sub = df[df["Volume Range"] == r]
    if not sub.empty:
        st.markdown(f"**{r} Volume**")
        st.dataframe(sub[["Chain", "Total Volume ($)"]], use_container_width=True)
