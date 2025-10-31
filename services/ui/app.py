import os, requests, pandas as pd, time
import streamlit as st
from urllib.parse import urlencode

DEFAULT_CANDIDATES = [
    # 1) Render default if you kept the blueprint names:
    "https://crypto-risk-api.onrender.com",
    # 2) Local docker compose:
    "http://api:8000",
    "http://localhost:8000",
]

def probe_api(base: str, timeout=2.0) -> bool:
    try:
        r = requests.get(f"{base}/health", timeout=timeout)
        return r.ok and r.json().get("ok") is True
    except Exception:
        return False

def resolve_api_base():
    # Priority 1: explicit env var
    env_base = os.getenv("API_BASE", "").strip()
    if env_base and probe_api(env_base):
        return env_base

    # Priority 2: comma-separated list of candidates from env
    env_candidates = os.getenv("API_CANDIDATES", "")
    candidates = [c.strip() for c in env_candidates.split(",") if c.strip()] if env_candidates else []
    # Merge with defaults (preserve order; avoid dups)
    seen = set()
    merged = []
    for x in (candidates + DEFAULT_CANDIDATES):
        if x not in seen:
            merged.append(x)
            seen.add(x)

    for base in merged:
        if probe_api(base):
            return base

    return None  # nothing worked

API_BASE = resolve_api_base()

st.set_page_config(page_title="Crypto Risk Dashboard", layout="wide")
st.title("🧭 Crypto Risk Dashboard")
st.caption("Self-hosted. Graphs • Meters • Hot Signals")

if not API_BASE:
    st.error("Could not locate the API automatically.")
    manual = st.text_input("Enter your API base URL (e.g., https://crypto-risk-api.onrender.com)")
    if manual:
        if probe_api(manual):
            API_BASE = manual
            st.success("Connected!")
        else:
            st.warning("That URL didn’t respond at /health. Double-check and try again.")

if not API_BASE:
    st.stop()

# Pairs
resp = requests.get(f"{API_BASE}/pairs", timeout=30).json()
pairs = resp.get("pairs", ["binance:BTC/USDT"])

col1, col2 = st.columns([2,1])
with col1:
    pair = st.selectbox("Pair", pairs, index=0)
with col2:
    refresh = st.button("Refresh")

def fetch(metric, pair, limit=500):
    qs = urlencode({"pair": pair, "limit": limit})
    r = requests.get(f"{API_BASE}/timeseries/{metric}?{qs}", timeout=30)
    return r.json()

def get_signals(pairs=None):
    qs = ""
    if pairs:
        qs = "?pairs=" + ",".join(pairs)
    r = requests.get(f"{API_BASE}/signals{qs}", timeout=30)
    return r.json()

sig = get_signals([pair])
signals = sig.get("signals", {})
explanations = sig.get("explanations", {})

st.subheader("Hot Signals")
if signals.get(pair):
    s = signals[pair]
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Market Regime", s.get("regime","—"))
    with c2:
        st.metric("Bias", s.get("bias","—"))
    with c3:
        st.metric("Long Prob. %", round(100*s.get("long_prob",0),1))
    with c4:
        st.metric("Short Prob. %", round(100*s.get("short_prob",0),1))
    st.info(s.get("summary",""))
else:
    st.warning("No signals yet. The worker may still be seeding data.")

st.divider()
st.subheader("Charts")

tabs = st.tabs(["Candles", "Funding", "Open Interest", "Volatility", "Sentiment"])

with tabs[0]:
    data = fetch("candles", pair, limit=300)
    rows = data.get("rows", [])
    if rows:
        df = pd.DataFrame(rows).sort_values("ts")
        st.line_chart(df, x="ts", y=["close"])
    else:
        st.write("No data yet.")

with tabs[1]:
    data = fetch("funding", pair, limit=500)
    rows = data.get("rows", [])
    if rows:
        df = pd.DataFrame(rows).sort_values("ts")
        st.line_chart(df, x="ts", y=["rate"])
    else:
        st.write("No data yet.")

with tabs[2]:
    data = fetch("oi", pair, limit=500)
    rows = data.get("rows", [])
    if rows:
        df = pd.DataFrame(rows).sort_values("ts")
        st.line_chart(df, x="ts", y=["value_usd"])
    else:
        st.write("No data yet.")

with tabs[3]:
    data = fetch("vol", pair, limit=500)
    rows = data.get("rows", [])
    if rows:
        df = pd.DataFrame(rows).sort_values("ts")
        st.line_chart(df, x="ts", y=["atr"])
    else:
        st.write("No data yet.")

with tabs[4]:
    data = fetch("sentiment", pair, limit=200)
    rows = data.get("rows", [])
    if rows:
        df = pd.DataFrame(rows).sort_values("ts")
        st.line_chart(df, x="ts", y=["score_norm"])
    else:
        st.write("No data yet.")

st.divider()
st.caption("Tip: set API_BASE or API_CANDIDATES env vars to skip auto-detect.")
