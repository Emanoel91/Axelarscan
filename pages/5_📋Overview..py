import pandas as pd
import requests

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

# ------------------------------- Helper function ------------------------------
def fetch_chain_stats(chain_name, mode="source"):
    """
    mode = 'source'  -> Output
    mode = 'destination' -> Input
    """
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

    return {
        "Transfers": int(df["num_txs"].sum()),
        "Volume": float(df["volume"].sum()),
        "GMP_Transfers": int(df["gmp_num_txs"].sum()),
        "Token_Transfers": int(df["transfers_num_txs"].sum()),
        "GMP_Volume": float(df["gmp_volume"].sum()),
        "Token_Volume": float(df["transfers_volume"].sum()),
    }

# ------------------------------- Main loop -----------------------------------
rows = []

for chain in chains:
    output_stats = fetch_chain_stats(chain, mode="source")
    input_stats  = fetch_chain_stats(chain, mode="destination")

    rows.append({
        "Chain": chain,

        # -------- Output --------
        "Output Transfers": output_stats["Transfers"],
        "Output Volume": output_stats["Volume"],
        "GMP Output Transfers": output_stats["GMP_Transfers"],
        "Token Transfer Output Transfers": output_stats["Token_Transfers"],
        "GMP Output Volume": output_stats["GMP_Volume"],
        "Token Transfer Output Volume": output_stats["Token_Volume"],

        # -------- Input --------
        "Input Transfers": input_stats["Transfers"],
        "Input Volume": input_stats["Volume"],
        "GMP Input Transfers": input_stats["GMP_Transfers"],
        "Token Transfer Input Transfers": input_stats["Token_Transfers"],
        "GMP Input Volume": input_stats["GMP_Volume"],
        "Token Transfer Input Volume": input_stats["Token_Volume"],
    })

# ------------------------------- Final Table ----------------------------------
df_final = pd.DataFrame(rows)

# Sort alphabetically by chain name
df_final = df_final.sort_values("Chain").reset_index(drop=True)

# نمایش
print(df_final)

# اگر خواستی ذخیره کنی:
# df_final.to_csv("axelar_chain_kpis.csv", index=False)
