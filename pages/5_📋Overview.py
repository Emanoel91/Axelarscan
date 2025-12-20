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

def smart_fmt(x):
    if pd.isna(x):
        return ""
    if abs(x - int(x)) < 1e-9:
        return f"{int(x):,}"
    return f"{x:,.2f}".rstrip("0").rstrip(".")

def safe_sum(df, col):
    return float(df[col].sum()) if col in df.columns else 0.0

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
    for c in chains:
        out_ = fetch_chain(c, "source")
        in_  = fetch_chain(c, "destination")

        rows.append({
            "Chain": c,
            "Total Transfers": out_["Transfers"] + in_["Transfers"],
            "Total Volume ($)": out_["Volume"] + in_["Volume"],
            "Net Volume ($)": in_["Volume"] - out_["Volume"],
            "Output Transfers": out_["Transfers"],
            "Output Volume ($)": out_["Volume"],
            "Input Transfers": in_["Transfers"],
            "Input Volume ($)": in_["Volume"],
        })

df = pd.DataFrame(rows).sort_values("Chain").reset_index(drop=True)
df.index = df.index + 1  # index from 1

# ------------------------------- Display main table ---------------------------
st.subheader("📋 Interchain Flow Table")

num_cols = df.select_dtypes("number").columns
styled_df = (
    df.style
      .applymap(net_color, subset=["Net Volume ($)"])
      .format({col: smart_fmt for col in num_cols})
)

st.dataframe(styled_df, use_container_width=True)

# ------------------------------- Bar charts ----------------------------------
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

# ---- Transfer ranges ----
transfer_bins = [0,10,50,100,500,1000,5000,10000,20000,50000,1e12]
transfer_labels = [
    "<10","11–50","51–100","101–500","501–1000",
    "1001–5000","5001–10000","10001–20000",
    "20001–50000",">50000"
]

# ---- Volume ranges ----
volume_bins = [0,10,100,1e3,1e4,1e5,1e6,1e7,1e8,5e8,1e9,1e12]
volume_labels = [
    "<$10","$10–100","$100–1k","$1k–10k","$10k–100k",
    "$100k–1m","$1m–10m","$10m–100m",
    "$100m–500m","$500m–1b",">$1b"
]

df["Transfer Range"] = pd.cut(
    df["Total Transfers"],
    bins=transfer_bins,
    labels=transfer_labels
)

df["Volume Range"] = pd.cut(
    df["Total Volume ($)"],
    bins=volume_bins,
    labels=volume_labels
)

def donut_from_range(series, title):
    vc = series.value_counts().reset_index(name="count")
    fig = px.pie(
        vc,
        names=series.name,   # ← اسم واقعی ستون (حل نهایی خطا)
        values="count",
        hole=0.55,
        title=title
    )
    return fig

d1, d2 = st.columns(2)

with d1:
    st.plotly_chart(
        donut_from_range(
            df["Transfer Range"],
            "Chains by Total Transfers Range"
        ),
        use_container_width=True
    )

with d2:
    st.plotly_chart(
        donut_from_range(
            df["Volume Range"],
            "Chains by Total Volume Range"
        ),
        use_container_width=True
    )

# --------------------------------------------------------------------------------
# --- Load Axelar TVL API ---
@st.cache_data(ttl=3600)
def load_axelar_api():
    url = "https://api.axelarscan.io/api/getTVL"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Failed to fetch Axelar API: {response.status_code}")
        return None

data = load_axelar_api()

# --- Parse Axelar TVL ---
rows = []
if data and "data" in data:
    for asset in data["data"]:
        value = asset.get("value", 0)
        rows.append({"Total Asset Value (USD)": value})

axelar_df = pd.DataFrame(rows)
total_axelar_tvl = axelar_df["Total Asset Value (USD)"].sum()

# --------------------------------------------------------------------------------
# --- Load Chains TVL API (DefiLlama) ---
@st.cache_data(ttl=3600)
def load_chains_api():
    url = "https://api.llama.fi/v2/chains"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Failed to fetch Chains API: {response.status_code}")
        return []

chains_data = load_chains_api()
chains_df = pd.DataFrame(chains_data)

chains_df = chains_df[["name", "tvl", "tokenSymbol"]]
chains_df.columns = ["Chain Name", "TVL (USD)", "Native Token Symbol"]

# --- Add Axelar manually ---
chains_df = pd.concat([
    chains_df,
    pd.DataFrame([{
        "Chain Name": "Axelar",
        "TVL (USD)": total_axelar_tvl,
        "Native Token Symbol": "AXL"
    }])
], ignore_index=True)

chains_df = chains_df.sort_values("TVL (USD)", ascending=False).reset_index(drop=True)
chains_df.index = chains_df.index + 1

# --------------------------------------------------------------------------------
# --- Table: TVL of Different Chains ---
st.markdown("### 📊 TVL of Different Chains")

st.dataframe(
    chains_df.style.format({
        "TVL (USD)": "{:,.0f}"
    }),
    use_container_width=True
)

# --------------------------------------------------------------------------------
# --- Top 20 Chains by TVL ---
top_20_chains = chains_df.head(20).reset_index()

def human_format(num):
    if num >= 1e9:
        return f"{num/1e9:.1f}B"
    elif num >= 1e6:
        return f"{num/1e6:.1f}M"
    elif num >= 1e3:
        return f"{num/1e3:.1f}K"
    else:
        return str(int(num))

fig_bar = px.bar(
    top_20_chains,
    x="Chain Name",
    y="TVL (USD)",
    text=top_20_chains["TVL (USD)"].apply(human_format),
    title="🏆 Top 20 Chains by TVL ($USD)"
)

fig_bar.update_traces(textposition="outside")
fig_bar.update_layout(
    xaxis_title="Chain",
    yaxis_title="TVL ($USD)",
    showlegend=False,
    plot_bgcolor="white"
)

st.plotly_chart(fig_bar, use_container_width=True)
