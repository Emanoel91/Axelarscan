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
def format_number(x):
    x = float(x)
    if abs(x) >= 1e9:
        return f"{x/1e9:.2f}B"
    elif abs(x) >= 1e6:
        return f"{x/1e6:.2f}M"
    elif abs(x) >= 1e3:
        return f"{x/1e3:.2f}k"
    else:
        return f"{int(x)}"

def net_volume_color(val):
    if val > 0:
        return "color: green; font-weight: 700;"
    elif val < 0:
        return "color: red; font-weight: 700;"
    else:
        return "color: gray;"

@st.cache_data(show_spinner=False)
def fetch_chain_stats(chain, mode):
    params = {"sourceChain": chain} if mode == "source" else {"destinationChain": chain}
    try:
        r = requests.get(BASE_URL, params=params, timeout=30)
        data = r.json().get("data", [])
    except Exception:
        data = []

    if not data:
        return dict.fromkeys(
            ["Transfers","Volume","GMP_Transfers","Token_Transfers","GMP_Volume","Token_Volume"], 0
        )

    df = pd.DataFrame(data).fillna(0)

    return {
        "Transfers": df.get("num_txs", 0).sum(),
        "Volume": df.get("volume", 0).sum(),
        "GMP_Transfers": df.get("gmp_num_txs", 0).sum(),
        "Token_Transfers": df.get("transfers_num_txs", 0).sum(),
        "GMP_Volume": df.get("gmp_volume", 0).sum(),
        "Token_Volume": df.get("transfers_volume", 0).sum(),
    }

# ------------------------------- Build table ---------------------------------
with st.spinner("Fetching all chains data..."):
    rows = []
    for chain in chains:
        out_ = fetch_chain_stats(chain, "source")
        in_  = fetch_chain_stats(chain, "destination")

        rows.append({
            "Chain": chain,
            "Total Transfers": out_["Transfers"] + in_["Transfers"],
            "Total Volume ($)": out_["Volume"] + in_["Volume"],
            "Net Volume ($)": in_["Volume"] - out_["Volume"],

            "Output Transfers": out_["Transfers"],
            "Output Volume ($)": out_["Volume"],
            "Input Transfers": in_["Transfers"],
            "Input Volume ($)": in_["Volume"],
        })

df = pd.DataFrame(rows).sort_values("Chain").reset_index(drop=True)

# ------------------------------- Styled Table --------------------------------
st.subheader("📋 Interchain Flow Table")
styled_df = df.style.applymap(net_volume_color, subset=["Net Volume ($)"])
st.dataframe(styled_df, use_container_width=True)

# ------------------------------- Bar Charts ----------------------------------
st.subheader("📊 Chains Ranking")

c1, c2 = st.columns(2)

with c1:
    df_t = df.sort_values("Total Transfers", ascending=False)
    fig = px.bar(
        df_t, x="Chain", y="Total Transfers",
        title="Chains by Total Transfers",
        text=df_t["Total Transfers"].apply(format_number)
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

with c2:
    df_v = df.sort_values("Total Volume ($)", ascending=False)
    fig = px.bar(
        df_v, x="Chain", y="Total Volume ($)",
        title="Chains by Total Volume ($)",
        text=df_v["Total Volume ($)"].apply(format_number)
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

# ------------------------------- Donut Charts --------------------------------
st.subheader("🍩 Distribution Overview")

def donut_chart(df, value_col, title):
    top = df.sort_values(value_col, ascending=False).head(10)
    others = df[value_col].sum() - top[value_col].sum()
    donut_df = pd.concat([
        top[["Chain", value_col]],
        pd.DataFrame({"Chain": ["Others"], value_col: [others]})
    ])

    fig = px.pie(
        donut_df,
        names="Chain",
        values=value_col,
        hole=0.55,
        title=title
    )
    return fig

d1, d2 = st.columns(2)

with d1:
    st.plotly_chart(
        donut_chart(df, "Total Transfers", "Total Transfers Distribution"),
        use_container_width=True
    )

with d2:
    st.plotly_chart(
        donut_chart(df, "Total Volume ($)", "Total Volume Distribution ($)"),
        use_container_width=True
    )
