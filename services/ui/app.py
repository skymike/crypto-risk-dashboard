import os
import requests
import pandas as pd
import streamlit as st
from urllib.parse import urlencode
from typing import Optional

DEFAULT_CANDIDATES = [
    "https://crypto-risk-api.onrender.com",
    "http://api:8000",
    "http://localhost:8000",
]

def probe_api(base: str, timeout=2.0) -> bool:
    try:
        r = requests.get(f"{base}/health", timeout=timeout)
        return r.ok and r.json().get("ok") is True
    except Exception:
        return False

def resolve_api_base() -> Optional[str]:
    env_base = os.getenv("API_BASE", "").strip()
    if env_base and probe_api(env_base):
        return env_base
    env_candidates = os.getenv("API_CANDIDATES", "")
    candidates = [c.strip() for c in env_candidates.split(",") if c.strip()] if env_candidates else []
    seen, merged = set(), []
    for x in (candidates + DEFAULT_CANDIDATES):
        if x not in seen:
            merged.append(x)
            seen.add(x)
    for base in merged:
        if probe_api(base):
            return base
    return None

API_BASE = resolve_api_base()

st.set_page_config(page_title="Crypto Risk Dashboard", layout="wide")
st.title("🧭 Crypto Risk Dashboard")

if not API_BASE:
    st.error("Could not connect to API backend. Please ensure the API is running and reachable.")
    st.stop()

@st.cache_data(ttl=300)
def fetch(endpoint: str, params: Optional[dict] = None) -> Optional[pd.DataFrame]:
    url = f"{API_BASE}/{endpoint}"
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if "data" in data and isinstance(data["data"], list):
            return pd.DataFrame(data["data"])
        else:
            st.warning(f"No data found for endpoint: {endpoint}")
            return None
    except Exception as e:
        st.error(f"Error fetching {endpoint}: {e}")
        return None

# Refresh button to clear cache
if st.button("Refresh Data"):
    fetch.clear()

pairs_df = fetch("pairs")
pair = None
if pairs_df is not None and not pairs_df.empty:
    pair = st.selectbox("Select trading pair", pairs_df["pair"].unique())
else:
    st.warning("No trading pairs available from API.")

# If no pair selected, stop further processing
if not pair:
    st.info("Select a pair to see data.")
    st.stop()

limit = 1000

st.subheader(f"Data for Pair: {pair}")

data_tabs = st.tabs(["Candles", "Funding Rates", "Open Interest", "Volatility", "Sentiment", "Signals"])

with data_tabs[0]:
    candles = fetch("candles", params={"pair": pair, "limit": limit})
    if candles is not None and not candles.empty:
        st.line_chart(candles.set_index("ts")[["open", "high", "low", "close"]])
    else:
        st.write("No candles data available.")

with data_tabs[1]:
    funding = fetch("funding", params={"pair": pair, "limit": limit})
    if funding is not None and not funding.empty:
        st.line_chart(funding.set_index("ts")["funding_rate"])
    else:
        st.write("No funding rate data available.")

with data_tabs[2]:
    oi = fetch("open_interest", params={"pair": pair, "limit": limit})
    if oi is not None and not oi.empty:
        st.line_chart(oi.set_index("ts")["open_interest"])
    else:
        st.write("No open interest data available.")

with data_tabs[3]:
    vol = fetch("volatility", params={"pair": pair, "limit": limit})
    if vol is not None and not vol.empty:
        st.line_chart(vol.set_index("ts")["atr"])
    else:
        st.write("No volatility data available.")

with data_tabs[4]:
    sentiment = fetch("sentiment", params={"pair": pair, "limit": limit})
    if sentiment is not None and not sentiment.empty:
        st.line_chart(sentiment.set_index("ts")["sentiment_score"])
    else:
        st.write("No sentiment data available.")

with data_tabs[5]:
    signals = fetch("signals", params={"pair": pair})
    if signals is not None and not signals.empty:
        st.write(signals)
    else:
        st.write("No signals data available.")

st.caption("Configure pairs, scheduler, and API keys in your .env file or Render.com environment settings.")
