import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from io import BytesIO

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
def to_excel(df, sheet_name="Sheet1"):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=True)
    return buffer.getvalue()

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
df.index = df.index + 1

# ------------------------------- Main table -----------------------------------
st.subheader("📋 Interchain Flow Table")

num_cols = df.select_dtypes("number").columns
styled_df = (
    df.style
      .applymap(net_color, subset=["Net Volume ($)"])
      .format({col: smart_fmt for col in num_cols})
)

st.dataframe(styled_df, use_container_width=True)

st.download_button(
    "⬇️ Download Interchain Flow (Excel)",
    to_excel(df, "Interchain Flow"),
    "axelar_interchain_flow.xlsx"
)

# ------------------------------- Rankings -------------------------------------
st.subheader("📊 Chains Ranking")

c1, c2 = st.columns(2)

with c1:
    df_tr = df.sort_values("Total Transfers", ascending=False)
    fig = px.bar(df_tr, x="Chain", y="Total Transfers", title="Chains by Total Transfers")
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

    st.download_button(
        "⬇️ Download Transfers Ranking (Excel)",
        to_excel(df_tr, "Transfers Ranking"),
        "chains_by_total_transfers.xlsx"
    )

with c2:
    df_vol = df.sort_values("Total Volume ($)", ascending=False)
    fig = px.bar(df_vol, x="Chain", y="Total Volume ($)", title="Chains by Total Volume ($)")
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

    st.download_button(
        "⬇️ Download Volume Ranking (Excel)",
        to_excel(df_vol, "Volume Ranking"),
        "chains_by_total_volume.xlsx"
    )

# ------------------------------- Distribution --------------------------------
st.subheader("🍩 Distribution by Ranges")

transfer_bins = [0,10,50,100,500,1000,5000,10000,20000,50000,1e12]
transfer_labels = ["<10","11–50","51–100","101–500","501–1000",
                   "1001–5000","5001–10000","10001–20000",
                   "20001–50000",">50000"]

volume_bins = [0,10,100,1e3,1e4,1e5,1e6,1e7,1e8,5e8,1e9,1e12]
volume_labels = ["<$10","$10–100","$100–1k","$1k–10k","$10k–100k",
                 "$100k–1m","$1m–10m","$10m–100m",
                 "$100m–500m","$500m–1b",">$1b"]

df["Transfer Range"] = pd.cut(df["Total Transfers"], transfer_bins, labels=transfer_labels)
df["Volume Range"]   = pd.cut(df["Total Volume ($)"], volume_bins, labels=volume_labels)

def donut(series, title):
    vc = series.value_counts().reset_index(name="Chain Count")
    fig = px.pie(vc, names=series.name, values="Chain Count", hole=0.55, title=title)
    return fig, vc

d1, d2 = st.columns(2)

with d1:
    fig, dist_tr = donut(df["Transfer Range"], "Chains by Total Transfers Range")
    st.plotly_chart(fig, use_container_width=True)
    st.download_button(
        "⬇️ Download Transfer Range Distribution",
        to_excel(dist_tr, "Transfer Ranges"),
        "transfer_range_distribution.xlsx"
    )

with d2:
    fig, dist_vol = donut(df["Volume Range"], "Chains by Total Volume Range")
    st.plotly_chart(fig, use_container_width=True)
    st.download_button(
        "⬇️ Download Volume Range Distribution",
        to_excel(dist_vol, "Volume Ranges"),
        "volume_range_distribution.xlsx"
    )

# ------------------------------- TVL (Axelar + Llama) --------------------------
@st.cache_data(ttl=3600)
def load_axelar_api():
    return requests.get("https://api.axelarscan.io/api/getTVL").json()

@st.cache_data(ttl=3600)
def load_chains_api():
    return requests.get("https://api.llama.fi/v2/chains").json()

ax_data = load_axelar_api()
ax_tvl = sum(a.get("value",0) for a in ax_data.get("data",[]))

chains_df = pd.DataFrame(load_chains_api())[["name","tvl","tokenSymbol"]]
chains_df.columns = ["Chain Name","TVL (USD)","Native Token Symbol"]

chains_df = pd.concat([chains_df, pd.DataFrame([{
    "Chain Name":"Axelar","TVL (USD)":ax_tvl,"Native Token Symbol":"AXL"
}])])

chains_df = chains_df.sort_values("TVL (USD)", ascending=False).reset_index(drop=True)
chains_df.index += 1

st.markdown("### 📊 TVL of Different Chains")
st.dataframe(chains_df.style.format({"TVL (USD)":"{:,.0f}"}), use_container_width=True)

st.download_button(
    "⬇️ Download Chains TVL (Excel)",
    to_excel(chains_df, "TVL by Chain"),
    "chains_tvl.xlsx"
)

# ------------------------------- Top 20 TVL ----------------------------------
top20 = chains_df.head(20)

def human(n):
    return f"{n/1e9:.1f}B" if n>=1e9 else f"{n/1e6:.1f}M" if n>=1e6 else f"{n/1e3:.1f}K"

fig = px.bar(
    top20, x="Chain Name", y="TVL (USD)",
    text=top20["TVL (USD)"].apply(human),
    title="🏆 Top 20 Chains by TVL"
)
fig.update_traces(textposition="outside")
st.plotly_chart(fig, use_container_width=True)

st.download_button(
    "⬇️ Download Top 20 Chains by TVL (Excel)",
    to_excel(top20, "Top 20 TVL"),
    "top_20_chains_by_tvl.xlsx"
)
