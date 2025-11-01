import os
import requests
import pandas as pd
import streamlit as st
from urllib.parse import urlencode
from typing import Optional

DEFAULT_CANDIDATES = [
    "https://crypto-risk-api-production.up.railway.app",
    "https://crypto-risk-api.onrender.com",
    "http://api:8000",
    "http://localhost:8000",
]

def probe_api(base: str, timeout: float = 2.0) -> bool:
    try:
        r = requests.get(f"{base}/health", timeout=timeout)
        return r.ok and r.json().get("ok") is True
    except Exception:
        return False

def resolve_api_base() -> Optional[str]:
    """Resolve API base URL from environment or known candidates."""
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
st.title("Crypto Risk Dashboard")
st.caption("Graphs, Meters, and Hot Signals")

if not API_BASE:
    st.error("Could not locate the API automatically.")
    manual = st.text_input("Enter your API base URL (e.g., https://crypto-risk-api-production.up.railway.app)")
    if manual and probe_api(manual):
        API_BASE = manual
        st.success("Connected!")

if not API_BASE:
    st.error("Could not connect to API backend. Please ensure the API is running and reachable.")
    st.stop()

@st.cache_data(ttl=300)
def fetch_pairs() -> list[str]:
    try:
        resp = requests.get(f"{API_BASE}/pairs", timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get("pairs", ["binance:BTC/USDT"])
    except Exception as e:
        st.error(f"Error fetching pairs: {e}")
        return ["binance:BTC/USDT"]

@st.cache_data(ttl=300)
def fetch_timeseries(metric: str, pair: str, limit: int = 500) -> Optional[pd.DataFrame]:
    qs = urlencode({"pair": pair, "limit": limit})
    url = f"{API_BASE}/timeseries/{metric}?{qs}"
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        payload = r.json()
        rows = payload.get("rows", [])
        if not rows:
            return None
        df = pd.DataFrame(rows)
        if "ts" in df.columns:
            df["ts"] = pd.to_datetime(df["ts"], utc=True)
            df = df.set_index("ts")
        return df
    except Exception as e:
        st.error(f"Error fetching timeseries {metric}: {e}")
        return None

@st.cache_data(ttl=120)
def fetch_signals(pairs: list[str]) -> dict:
    try:
        qs = "?pairs=" + ",".join(pairs) if pairs else ""
        r = requests.get(f"{API_BASE}/signals{qs}", timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Error fetching signals: {e}")
        return {}

# Refresh button to clear cache
if st.button("Refresh Data"):
    fetch_pairs.clear()
    fetch_timeseries.clear()
    fetch_signals.clear()

pairs = fetch_pairs()
pair = None
if pairs:
    pair = st.selectbox("Select trading pair", pairs, index=0)
else:
    st.warning("No trading pairs available from API.")

# If no pair selected, stop further processing
if not pair:
    st.info("Select a pair to see data.")
    st.stop()

limit = 1000

st.subheader(f"Data for Pair: {pair}")

sig_payload = fetch_signals([pair]) or {}
signals_map = sig_payload.get("signals", {})
explanations = sig_payload.get("explanations", {})

st.subheader("Hot Signals")
if pair in signals_map:
    s = signals_map[pair]
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Market Regime", s.get("regime", "Unknown"))
    with c2:
        st.metric("Bias", s.get("bias", "Neutral"))
    with c3:
        st.metric("Long Prob. %", round(100 * float(s.get("long_prob", 0)), 1))
    with c4:
        st.metric("Short Prob. %", round(100 * float(s.get("short_prob", 0)), 1))
    if s.get("summary"):
        st.info(s["summary"])
else:
    st.write("No signal for selected pair yet.")

data_tabs = st.tabs(["Candles", "Funding", "Open Interest", "Volatility", "Sentiment"]) 

with data_tabs[0]:
    candles = fetch_timeseries("candles", pair=pair, limit=limit)
    if candles is not None and not candles.empty:
        st.line_chart(candles[["open", "high", "low", "close"]])
    else:
        st.write("No candles data available.")

with data_tabs[1]:
    funding = fetch_timeseries("funding", pair=pair, limit=limit)
    if funding is not None and not funding.empty:
        col = "rate" if "rate" in funding.columns else funding.columns[-1]
        st.line_chart(funding[col])
    else:
        st.write("No funding rate data available.")

with data_tabs[2]:
    oi = fetch_timeseries("oi", pair=pair, limit=limit)
    if oi is not None and not oi.empty:
        col = "value_usd" if "value_usd" in oi.columns else oi.columns[-1]
        st.line_chart(oi[col])
    else:
        st.write("No open interest data available.")

with data_tabs[3]:
    vol = fetch_timeseries("vol", pair=pair, limit=limit)
    if vol is not None and not vol.empty:
        col = "atr" if "atr" in vol.columns else vol.columns[-1]
        st.line_chart(vol[col])
    else:
        st.write("No volatility data available.")

with data_tabs[4]:
    sentiment = fetch_timeseries("sentiment", pair=pair, limit=limit)
    if sentiment is not None and not sentiment.empty:
        col = "score_norm" if "score_norm" in sentiment.columns else sentiment.columns[-1]
        st.line_chart(sentiment[col])
    else:
        st.write("No sentiment data available.")

st.divider()
st.caption("Configure pairs & scheduler in .env. Add API keys for live data.")

