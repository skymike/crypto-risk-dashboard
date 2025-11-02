import os
import requests
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from urllib.parse import urlencode
from typing import Optional
import plotly.graph_objects as go

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

# Minimal CSS tweaks for a softer, modern look
st.markdown(
    """
    <style>
    .main {
        background: radial-gradient(circle at top left, #101726, #05070f);
        color: #f5f7ff;
    }
    .stApp {
        background: transparent;
    }
    h1, h2, h3, h4 {
        color: #f5f7ff !important;
    }
    .rounded-card {
        background: rgba(15, 23, 42, 0.55);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(148, 163, 184, 0.2);
        border-radius: 20px;
        padding: 1.2rem 1.5rem;
        box-shadow: 0 18px 35px rgba(15, 23, 42, 0.3);
        margin-bottom: 1.5rem;
    }
    button[data-baseweb="button"],
    div.stButton > button {
        border-radius: 999px !important;
        border: 1px solid rgba(99, 102, 241, 0.45);
        font-weight: 600;
        background: linear-gradient(135deg, #f8fafc 0%, #6366f1 50%, #312e81 100%);
        color: #0f172a;
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.5), 0 12px 24px rgba(79, 70, 229, 0.35);
        text-shadow: none;
    }
    button[data-baseweb="button"]:hover,
    div.stButton > button:hover {
        filter: brightness(1.05);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.7), 0 14px 26px rgba(79,70,229,0.45);
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 999px !important;
        padding: 0.35rem 1.35rem;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(99, 102, 241, 0.2);
        color: #c7d2fe !important;
    }
    .stMetric {
        background: rgba(15, 23, 42, 0.65);
        border-radius: 18px;
        padding: 1rem;
        border: 1px solid rgba(148, 163, 184, 0.15);
    }
    .stMetric label {
        color: #cbd5f5 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

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

def trigger_manual_ingest() -> tuple[bool, str]:
    """Call the API endpoint to trigger a one-off ingest cycle."""
    try:
        resp = requests.post(f"{API_BASE}/ingest", timeout=10)
        resp.raise_for_status()
        payload = resp.json() if resp.headers.get("content-type","").startswith("application/json") else {}
        message = payload.get("message") or "Manual ingest triggered. Give it a few seconds to populate."
        return True, message
    except Exception as exc:
        return False, str(exc)


COINGECKO_IDS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binancecoin",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "AVAX": "avalanche-2",
    "DOT": "polkadot",
    "LINK": "chainlink",
}

COINCAP_IDS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binance-coin",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "AVAX": "avalanche",
    "TRX": "tron",
    "DOT": "polkadot",
    "LINK": "chainlink",
    "MATIC": "polygon",
    "UNI": "uniswap",
    "APT": "aptos",
    "ARB": "arbitrum",
    "ATOM": "cosmos",
    "OP": "optimism",
    "SEI": "sei-network",
    "NEAR": "near",
    "INJ": "injective-protocol",
}


def extract_base_symbols(pairs: list[str]) -> list[str]:
    bases = []
    for raw in pairs:
        try:
            base = raw.split(":", 1)[1] if ":" in raw else raw
            base = base.split("/", 1)[0]
            bases.append(base.upper())
        except Exception:
            continue
    return list(dict.fromkeys(bases))


@st.cache_data(ttl=60)
def fetch_market_snapshot(pairs: list[str]) -> dict[str, dict]:
    symbols = extract_base_symbols(pairs)
    ids = [COINGECKO_IDS[s] for s in symbols if s in COINGECKO_IDS]
    if not ids:
        return {}
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": ",".join(ids),
        "vs_currencies": "usd",
        "include_24hr_change": "true",
        "include_last_updated_at": "true",
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        payload = resp.json()
        simplified = {}
        for symbol, cg_id in COINGECKO_IDS.items():
            if cg_id in payload:
                entry = payload[cg_id]
                simplified[symbol] = {
                    "price": entry.get("usd"),
                    "change": entry.get("usd_24h_change"),
                    "updated": entry.get("last_updated_at"),
                }
        return simplified
    except Exception as exc:
        st.warning(f"Unable to fetch live market snapshot: {exc}")
    return {}


def build_aggr_trade_url(pair: str) -> str:
    target = pair.split(":", 1)[-1].replace("/", "").upper()
    return f"https://aggr.trade/?pair={target}"

@st.cache_data(ttl=600)
def fetch_fear_greed() -> Optional[dict]:
    try:
        resp = requests.get("https://api.alternative.me/fng/?limit=1", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("data"):
            return None
        entry = data["data"][0]
        return {
            "value": float(entry.get("value", 0)),
            "classification": entry.get("value_classification", "n/a"),
            "updated": entry.get("timestamp"),
        }
    except Exception:
        return None

@st.cache_data(ttl=180)
def fetch_asset_flows(pairs: list[str]) -> dict[str, dict]:
    symbols = extract_base_symbols(pairs)
    ids = [COINCAP_IDS[s] for s in symbols if s in COINCAP_IDS]
    try:
        params = {"limit": 5}
        if ids:
            params = {"ids": ",".join(ids)}
        resp = requests.get("https://api.coincap.io/v2/assets", params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        if not data and not ids:
            return {}
        if not data and ids:
            # fallback to global top assets if specific ids missing
            resp = requests.get("https://api.coincap.io/v2/assets", params={"limit": 5}, timeout=10)
            resp.raise_for_status()
            data = resp.json().get("data", [])
        out: dict[str, dict] = {}
        for asset in data:
            symbol = asset.get("symbol")
            if not symbol:
                continue
            try:
                out[symbol.upper()] = {
                    "price": float(asset.get("priceUsd") or 0),
                    "volume": float(asset.get("volumeUsd24Hr") or 0),
                    "change": float(asset.get("changePercent24Hr") or 0),
                    "market_cap": float(asset.get("marketCapUsd") or 0),
                }
            except (TypeError, ValueError):
                continue
        return out
    except Exception:
        return {}

@st.cache_data(ttl=600)
def fetch_alt_global() -> Optional[dict]:
    try:
        resp = requests.get("https://api.alternative.me/v2/global/?convert=USD", timeout=10)
        resp.raise_for_status()
        payload = resp.json()
        data = payload.get("data")
        if not isinstance(data, dict):
            return None
        quotes = data.get("quotes") or {}
        usd = quotes.get("USD") if isinstance(quotes, dict) else {}
        return {
            "market_cap": float(usd.get("total_market_cap", 0) or 0),
            "volume": float(usd.get("total_volume_24h", 0) or 0),
            "market_cap_change": float(
                usd.get("total_market_cap_yesterday_percentage_change", 0) or 0
            ),
            "active_cryptos": int(data.get("active_cryptocurrencies", 0) or 0),
            "active_markets": int(data.get("active_markets", 0) or 0),
            "btc_dominance": float(data.get("bitcoin_percentage_of_market_cap", 0) or 0),
        }
    except Exception:
        return None

# Refresh button to clear cache
controls = st.columns([1, 1, 3])
with controls[0]:
    if st.button("Refresh Data", use_container_width=True):
        fetch_pairs.clear()
        fetch_timeseries.clear()
        fetch_signals.clear()
        fetch_market_snapshot.clear()
        fetch_fear_greed.clear()
        fetch_asset_flows.clear()
        fetch_alt_global.clear()
with controls[1]:
    if st.button("Manual Data Pull", use_container_width=True):
        with st.spinner("Triggering worker ingest…"):
            ok, msg = trigger_manual_ingest()
        if ok:
            fetch_pairs.clear()
            fetch_timeseries.clear()
            fetch_signals.clear()
            fetch_market_snapshot.clear()
            fetch_fear_greed.clear()
            fetch_asset_flows.clear()
            fetch_alt_global.clear()
            st.success(msg)
        else:
            st.error(f"Manual ingest failed: {msg}")

pairs = fetch_pairs()
pair = None
if pairs:
    pair = st.selectbox("Select trading pair", pairs, index=0, format_func=lambda x: x.replace(":", " · "))
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

# Pre-load core time series once so analytics modules can reuse them
ts_cache: dict[str, Optional[pd.DataFrame]] = {
    "candles": fetch_timeseries("candles", pair=pair, limit=limit),
    "funding": fetch_timeseries("funding", pair=pair, limit=limit),
    "oi": fetch_timeseries("oi", pair=pair, limit=limit),
    "vol": fetch_timeseries("vol", pair=pair, limit=limit),
    "sentiment": fetch_timeseries("sentiment", pair=pair, limit=limit),
}

market_snapshot = fetch_market_snapshot(pairs)
if market_snapshot:
    st.subheader("Live Market Snapshot")
    cards = st.columns(min(4, len(market_snapshot)))
    idx = 0
    for symbol, data in market_snapshot.items():
        col = cards[idx % len(cards)]
        idx += 1
        with col:
            price = data.get("price")
            change = data.get("change")
            delta = f"{change:+.2f}%" if change is not None else "n/a"
            price_str = f"{price:,.2f} USD" if price is not None else "n/a"
            color = "#22c55e" if change is not None and change >= 0 else "#ef4444"
            st.markdown(
                f"""
                <div class="rounded-card">
                    <div style="font-size:0.9rem;color:#cdd4ff;">{symbol}</div>
                    <div style="font-size:1.8rem;font-weight:700;margin:0.2rem 0;">
                        {price_str}
                    </div>
                    <div style="font-size:0.9rem;color:{color}">
                        24h: {delta}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

macro = st.columns([1.2, 1, 1])
with macro[0]:
    fg = fetch_fear_greed()
    if fg:
        fg_val = float(fg["value"])
        gauge = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=fg_val,
                number={"suffix": " / 100", "font": {"color": "#f1f5ff"}},
                title={"text": f"Fear & Greed · {fg['classification']}", "font": {"color": "#e0e7ff"}},
                gauge={
                    "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#94a3b8"},
                    "bar": {"color": "#a855f7"},
                    "bgcolor": "#0f172a",
                    "borderwidth": 1,
                    "bordercolor": "#6366f1",
                    "steps": [
                        {"range": [0, 25], "color": "#7f1d1d"},
                        {"range": [25, 50], "color": "#b45309"},
                        {"range": [50, 75], "color": "#1f2937"},
                        {"range": [75, 100], "color": "#065f46"},
                    ],
                },
            )
        )
        gauge.update_layout(
            paper_bgcolor="rgba(15, 23, 42, 0.65)",
            font={"color": "#cdd4ff"},
            height=260,
            margin=dict(l=10, r=10, t=40, b=0),
        )
        st.plotly_chart(gauge, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("Fear & Greed data is temporarily unavailable.")

with macro[1]:
    flows = fetch_asset_flows(pairs)
    if flows:
        sorted_rows = sorted(flows.items(), key=lambda kv: kv[1]["volume"], reverse=True)
        top_rows = sorted_rows[:3]
        items = []
        for symbol, info in top_rows:
            vol_usd = info["volume"]
            change = info["change"]
            price = info["price"]
            items.append(
                f"""
                <div style="margin-bottom:0.8rem;">
                    <div style="font-size:0.95rem;color:#cdd4ff;">{symbol}</div>
                    <div style="font-size:1.4rem;font-weight:700;">{price:,.2f} USD</div>
                    <div style="font-size:0.85rem;color:#94a3b8;">
                        24h Vol: {vol_usd/1_000_000:,.1f}M • Change: <span style="color:{'#22c55e' if change >=0 else '#ef4444'}">{change:+.2f}%</span>
                    </div>
                </div>
                """
            )
        st.markdown(
            "<div class=\"rounded-card\">" + "".join(items) + "<div style=\"font-size:0.75rem;color:#94a3b8;\">Source: coincap.io</div></div>",
            unsafe_allow_html=True,
        )
    else:
        st.info("CoinCap asset metrics unavailable right now.")

with macro[2]:
    global_data = fetch_alt_global()
    if global_data:
        mc = global_data["market_cap"] / 1_000_000_000 if global_data["market_cap"] else 0
        vol = global_data["volume"] / 1_000_000_000 if global_data["volume"] else 0
        dom = global_data["btc_dominance"]
        change = global_data["market_cap_change"]
        st.markdown(
            f"""
            <div class="rounded-card">
                <div style="font-size:0.9rem;color:#cdd4ff;">Global Market Overview</div>
                <div style="font-size:1.3rem;font-weight:700;margin:0.4rem 0 0;">
                    MC: {mc:,.1f}B · 24h Vol: {vol:,.1f}B
                </div>
                <div style="font-size:0.95rem;color:#e0e7ff;margin-top:0.3rem;">
                    BTC Dominance: {dom:.1f}% · Change: <span style="color:{'#22c55e' if change >=0 else '#ef4444'}">{change:+.2f}%</span>
                </div>
                <div style="font-size:0.8rem;color:#94a3b8;margin-top:0.4rem;">
                    Active Assets: {global_data['active_cryptos']} · Markets: {global_data['active_markets']}
                </div>
                <div style="font-size:0.7rem;color:#64748b;margin-top:0.6rem;">Source: alternative.me</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.info("Alternative.me global metrics unavailable right now.")

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

visual_tabs = st.tabs(["Price Action", "Funding & OI", "Sentiment", "aggr.trade"])

with visual_tabs[0]:
    candles = ts_cache["candles"]
    if candles is not None and not candles.empty:
        fig = go.Figure(
            data=[
                go.Candlestick(
                    x=candles.index,
                    open=candles["open"],
                    high=candles["high"],
                    low=candles["low"],
                    close=candles["close"],
                    name="Price",
                )
            ]
        )
        fig.update_layout(
            margin=dict(l=0, r=0, t=35, b=0),
            template="plotly_dark",
            title=f"{pair} · Candlestick",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No candles data available.")

with visual_tabs[1]:
    funding = ts_cache["funding"]
    oi = ts_cache["oi"]
    if funding is not None and not funding.empty and oi is not None and not oi.empty:
        col = "rate" if "rate" in funding.columns else funding.columns[-1]
        oi_col = "value_usd" if "value_usd" in oi.columns else oi.columns[-1]
        merged = funding[[col]].join(oi[[oi_col]], how="inner")
        merged = merged.dropna()
        if merged.empty:
            st.info("Not enough overlapping funding/OI data.")
        else:
            fig = go.Figure()
            fig.add_trace(
                go.Bar(
                    x=merged.index,
                    y=merged[col] * 10000,
                    name="Funding (bps)",
                    marker_color="#22c55e",
                    opacity=0.6,
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=merged.index,
                    y=merged[oi_col] / 1_000_000,
                    name="Open Interest (M USD)",
                    mode="lines",
                    line=dict(color="#38bdf8", width=2),
                    yaxis="y2",
                )
            )
            fig.update_layout(
                template="plotly_dark",
                margin=dict(l=0, r=0, t=35, b=0),
                yaxis=dict(title="Funding (bps)"),
                yaxis2=dict(title="OI (Millions USD)", overlaying="y", side="right"),
                title=f"{pair} · Funding vs Open Interest",
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Funding or open interest data unavailable.")

with visual_tabs[2]:
    sentiment = ts_cache["sentiment"]
    if sentiment is not None and not sentiment.empty:
        metric = "score_norm" if "score_norm" in sentiment.columns else sentiment.columns[-1]
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=sentiment.index,
                y=sentiment[metric],
                name="Sentiment",
                line=dict(color="#f97316"),
                fill="tozeroy",
            )
        )
        fig.update_layout(
            template="plotly_dark",
            margin=dict(l=0, r=0, t=35, b=0),
            title=f"{pair} · Sentiment Trend",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No sentiment data available.")

with visual_tabs[3]:
    st.write("Live liquidation feed via aggr.trade")
    components.iframe(build_aggr_trade_url(pair), height=640, scrolling=True)

st.subheader("Insight Modules")
analysis_tabs = st.tabs(["Funding Overlay", "Volatility Pulse", "Sentiment Radar"])

with analysis_tabs[0]:
    candles = ts_cache["candles"]
    funding = ts_cache["funding"]
    if candles is None or candles.empty or funding is None or funding.empty:
        st.info("Need both candle and funding data for overlay.")
    else:
        merged = candles[["close"]].join(funding["rate" if "rate" in funding.columns else funding.columns[-1]], how="inner")
        merged = merged.dropna()
        if merged.empty:
            st.info("Not enough overlapping data for overlay.")
        else:
            price_norm = (merged["close"] / merged["close"].iloc[0]) * 100
            funding_bps = merged.iloc[:, 1] * 10000
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(x=merged.index, y=price_norm, name="Price (norm 100)", line=dict(color="#a855f7"))
            )
            fig.add_trace(
                go.Scatter(
                    x=merged.index,
                    y=funding_bps,
                    name="Funding (bps)",
                    line=dict(color="#f59e0b", dash="dot"),
                    yaxis="y2",
                )
            )
            fig.update_layout(
                template="plotly_dark",
                yaxis=dict(title="Price (index)"),
                yaxis2=dict(title="Funding (bps)", overlaying="y", side="right"),
                margin=dict(l=0, r=0, t=35, b=0),
            )
            st.plotly_chart(fig, use_container_width=True)

with analysis_tabs[1]:
    vol = ts_cache["vol"]
    if vol is None or vol.empty:
        st.info("Volatility data not available yet.")
    else:
        series = vol["atr"] if "atr" in vol.columns else vol.iloc[:, 0]
        metric_value = float(series.iloc[-1])
        fig = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=metric_value,
                title={"text": "ATR Snapshot"},
                gauge={
                    "axis": {"range": [0, series.max() * 1.2 if series.max() else 1]},
                    "bar": {"color": "#38bdf8"},
                    "bgcolor": "#0f172a",
                    "steps": [
                        {"range": [0, series.median()], "color": "#1e3a8a"},
                        {"range": [series.median(), series.max()], "color": "#0f766e"},
                    ],
                },
            )
        )
        fig.update_layout(template="plotly_dark", margin=dict(l=0, r=0, t=35, b=0))
        st.plotly_chart(fig, use_container_width=True)
        stats = series.describe().to_frame(name="ATR").T
        st.dataframe(stats)

with analysis_tabs[2]:
    sentiment = ts_cache["sentiment"]
    if sentiment is None or sentiment.empty or "keywords" not in sentiment.columns:
        st.info("Sentiment keyword data is not available.")
    else:
        latest = sentiment.dropna(subset=["keywords"]).iloc[-1]
        keywords = latest["keywords"]
        if isinstance(keywords, dict) and keywords:
            df_kw = (
                pd.DataFrame({"keyword": list(keywords.keys()), "count": list(keywords.values())})
                .sort_values("count", ascending=False)
                .head(15)
            )
            fig = go.Figure(
                go.Bar(
                    x=df_kw["keyword"],
                    y=df_kw["count"],
                    marker_color="#f472b6",
                )
            )
            fig.update_layout(template="plotly_dark", margin=dict(l=0, r=0, t=35, b=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Latest sentiment entry does not include keyword counts.")

st.divider()
st.caption("Configure pairs, Telegram alerts, and scheduler in .env. Add API keys for live data.")
