import requests
import pandas as pd
import plotly.express as px
from datetime import datetime

# 🕒 Define default time range (Unix timestamps)
from_time = int(datetime(2025, 1, 1).timestamp())
to_time = int(datetime(2026, 1, 1).timestamp())

# 🔗 Base API endpoint
url = f"https://api.axelarscan.io/gmp/GMPStatsByChains?fromTime={from_time}&toTime={to_time}"

# 📥 Fetch data from API
response = requests.get(url)
data = response.json()

# ✅ Extract source chains
source_chains = data.get("source_chains", [])

# 🧮 Calculate outgoing and incoming volumes for each chain
outgoing_volumes = {}
incoming_volumes = {}

for source in source_chains:
    src_key = source["key"]
    dests = source.get("destination_chains", [])
    
    # Total outgoing volume from each source chain
    total_out = sum(d.get("volume", 0) for d in dests)
    outgoing_volumes[src_key] = outgoing_volumes.get(src_key, 0) + total_out
    
    # Total incoming volume for each destination chain
    for d in dests:
        dest_key = d["key"]
        incoming_volumes[dest_key] = incoming_volumes.get(dest_key, 0) + d.get("volume", 0)

# 📊 Build DataFrames for incoming and outgoing volumes
incoming_df = pd.DataFrame(list(incoming_volumes.items()), columns=["chain", "volume"])
outgoing_df = pd.DataFrame(list(outgoing_volumes.items()), columns=["chain", "volume"])

# 🧾 Merge data to calculate net volume
combined_df = pd.merge(incoming_df, outgoing_df, on="chain", how="outer", suffixes=("_in", "_out")).fillna(0)
combined_df["net_volume"] = combined_df["volume_in"] - combined_df["volume_out"]

# 🎨 Helper function to add text labels on bars
def add_value_labels(fig, df, column):
    fig.update_traces(text=[f"{v:,.2f}" for v in df[column]], textposition='outside')

# 1️⃣ Incoming volume chart (Destination Chains)
fig_in = px.bar(
    incoming_df.sort_values("volume", ascending=True),
    x="volume", y="chain",
    orientation="h",
    title="📈 Total Incoming Volume per Chain (Destination Chains)",
    color="chain",
    color_discrete_sequence=px.colors.qualitative.Bold
)
add_value_labels(fig_in, incoming_df.sort_values("volume", ascending=True), "volume")
fig_in.update_layout(xaxis_title="Volume", yaxis_title="Destination Chain", showlegend=False)

# 2️⃣ Outgoing volume chart (Source Chains)
fig_out = px.bar(
    outgoing_df.sort_values("volume", ascending=True),
    x="volume", y="chain",
    orientation="h",
    title="📉 Total Outgoing Volume per Chain (Source Chains)",
    color="chain",
    color_discrete_sequence=px.colors.qualitative.Safe
)
add_value_labels(fig_out, outgoing_df.sort_values("volume", ascending=True), "volume")
fig_out.update_layout(xaxis_title="Volume", yaxis_title="Source Chain", showlegend=False)

# 3️⃣ Net volume chart (Incoming - Outgoing)
fig_net = px.bar(
    combined_df.sort_values("net_volume", ascending=True),
    x="net_volume", y="chain",
    orientation="h",
    title="⚖️ Net Volume per Chain (Incoming - Outgoing)",
    color=combined_df["net_volume"].apply(lambda x: "Positive Net" if x >= 0 else "Negative Net"),
    color_discrete_map={"Positive Net": "green", "Negative Net": "red"}
)
add_value_labels(fig_net, combined_df.sort_values("net_volume", ascending=True), "net_volume")
fig_net.update_layout(xaxis_title="Net Volume", yaxis_title="Chain", showlegend=True)

# 📊 Display all charts
fig_in.show()
fig_out.show()
fig_net.show()
