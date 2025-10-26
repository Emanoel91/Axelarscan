import streamlit as st
import pandas as pd
import requests
import snowflake.connector
import plotly.express as px
import plotly.graph_objects as go
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import networkx as nx

# --- Page Config ------------------------------------------------------------------------------------------------------
st.set_page_config(
    page_title="Axelarscan",
    page_icon="https://axelarscan.io/logos/logo.png",
    layout="wide"
)

# --- Title -----------------------------------------------------------------------------------------------------
st.title("📊 AXL Token Info")

st.info("📊Charts initially display data for a default time range. Select a custom range to view results for your desired period.")
st.info("⏳On-chain data retrieval may take a few moments. Please wait while the results load.")

# --- Sidebar Footer Slightly Left-Aligned ---------------------------------------------------------------------
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

# --- Snowflake Connection ----------------------------------------------------------------------------------------
snowflake_secrets = st.secrets["snowflake"]
user = snowflake_secrets["user"]
account = snowflake_secrets["account"]
private_key_str = snowflake_secrets["private_key"]
warehouse = snowflake_secrets.get("warehouse", "")
database = snowflake_secrets.get("database", "")
schema = snowflake_secrets.get("schema", "")

private_key_pem = f"-----BEGIN PRIVATE KEY-----\n{private_key_str}\n-----END PRIVATE KEY-----".encode("utf-8")
private_key = serialization.load_pem_private_key(
    private_key_pem,
    password=None,
    backend=default_backend()
)
private_key_bytes = private_key.private_bytes(
    encoding=serialization.Encoding.DER,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)

conn = snowflake.connector.connect(
    user=user,
    account=account,
    private_key=private_key_bytes,
    warehouse=warehouse,
    database=database,
    schema=schema
)

# --- Fetch Token Info from API ----------------------------------------------------------------------------------
@st.cache_data(ttl=300)
def get_token_info():
    url = "https://api.axelarscan.io/api/getTokenInfo"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

try:
    data = get_token_info()
    price = data.get("price", 0)
    market_cap = data.get("marketCap", 0)
    circulating_supply = data.get("circulatingSupply", 0)
    max_supply = data.get("maxSupply", 0)
    total_burned = data.get("totalBurned", 0)
    inflation = data.get("inflation", 0)

    # --- KPI Display Section -----------------------------------------------------------------------------------
    st.markdown("### 💎 AXL Key Performance Indicators")

    st.markdown(
        """
        <style>
        div[data-testid="stMetricValue"] {
            font-size: 28px;
            font-weight: 700;
            color: #00B8F4;
        }
        div[data-testid="stMetricLabel"] {
            font-size: 15px;
            color: #888;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # --- Row 1 ---
    col1, col2 = st.columns(2)
    with col1:
        st.metric("💰 Current Price (USD)", f"${price:,.3f}")
    with col2:
        st.metric("🏦 Market Cap (USD)", f"${market_cap:,.0f}")

    # --- Row 2 ---
    col3, col4 = st.columns(2)
    with col3:
        st.metric("🔄 Circulating Supply", f"{circulating_supply:,.0f} AXL")
    with col4:
        st.metric("📈 Max Supply", f"{max_supply:,.0f} AXL")

    # --- Row 3 ---
    col5, col6 = st.columns(2)
    with col5:
        st.metric("🔥 Total Burned", f"{total_burned:,.0f} AXL")
    with col6:
        st.metric("📊 Inflation", f"{inflation * 100:.2f}%")

except Exception as e:
    st.error(f"❌ Error fetching token data: {e}")
