import streamlit as st
import pandas as pd
import requests

# -------------------------------- Page config --------------------------------
st.set_page_config(
    page_title="Axelar Chain KPIs",
    page_icon="🔗",
    layout="wide"
)

st.title("🔗 Axelar – All-Time Input / Output KPIs by Chain")

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

# ------------------------------- Data fetcher ---------------------------------
@st.cache_data(show_spinner=False)
def fetch_chain_stats(chain_name, mode="source"):
    params = {}
    if mode == "source":
        params["sourceChain"] = chain_name
    else:
        params["destinationChain"] = chain_name

    try:
        r = requests.get(BASE_URL, params=params, timeout=30)
        r.raise_for_status()
        data = r.json().get("data", [])
    except Exception:
        data = []

    if not data:
        return {
            "Transfers": 0,
            "Volume": 0,
            "GMP_Transfers": 0,
            "Token_Transfers": 0,
            "GMP_Volume": 0,
            "Token_Volume": 0,
        }

    df = pd.DataFrame(data)

    for col in [
        "num_txs", "volume",
        "gmp_num_txs", "transfers_num_txs",
        "gmp_volume", "transfers_volume"
    ]:
        if col not in df.columns:
            df[col] = 0

    df = df.fillna(0)

    return {
        "Transfers": int(df["num_txs"].sum()),
        "Volume": float(df["volume"].sum()),
        "GMP_Transfers": int(df["gmp_num_txs"].sum()),
        "Token_Transfers": int(df["transfers_num_txs"].sum()),
        "GMP_Volume": float(df["gmp_volume"].sum()),
        "Token_Volume": float(df["transfers_volume"].sum()),
    }

# ------------------------------- Build table ---------------------------------
with st.spinner("Fetching all chains data from Axelar API..."):
    rows = []

    for chain in chains:
        output_stats = fetch_chain_stats(chain, "source")
        input_stats  = fetch_chain_stats(chain, "destination")

        # ---------- Calculated KPIs ----------
        total_transfers = output_stats["Transfers"] + input_stats["Transfers"]
        total_volume    = output_stats["Volume"] + input_stats["Volume"]
        net_volume      = input_stats["Volume"] - output_stats["Volume"]

        rows.append({
            "Chain": chain,

            # -------- NEW FIRST COLUMNS --------
            "Total Transfers": total_transfers,
            "Total Volume ($)": total_volume,
            "Net Volume ($)": net_volume,

            # -------- Output --------
            "Output Transfers": output_stats["Transfers"],
            "Output Volume ($)": output_stats["Volume"],
            "GMP Output Transfers": output_stats["GMP_Transfers"],
            "Token Transfer Output Transfers": output_stats["Token_Transfers"],
            "GMP Output Volume ($)": output_stats["GMP_Volume"],
            "Token Transfer Output Volume ($)": output_stats["Token_Volume"],

            # -------- Input --------
            "Input Transfers": input_stats["Transfers"],
            "Input Volume ($)": input_stats["Volume"],
            "GMP Input Transfers": input_stats["GMP_Transfers"],
            "Token Transfer Input Transfers": input_stats["Token_Transfers"],
            "GMP Input Volume ($)": input_stats["GMP_Volume"],
            "Token Transfer Input Volume ($)": input_stats["Token_Volume"],
        })

    df_final = (
        pd.DataFrame(rows)
        .sort_values("Chain")
        .reset_index(drop=True)
    )

# ------------------------------- Display -------------------------------------
st.subheader("📊 All-Time Interchain Flow Table")
st.dataframe(
    df_final,
    use_container_width=True,
    hide_index=True
)

# ------------------------------- Download ------------------------------------
st.download_button(
    "⬇️ Download CSV",
    df_final.to_csv(index=False),
    file_name="axelar_chain_kpis_all_time.csv",
    mime="text/csv"
)
