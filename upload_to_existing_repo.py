#!/usr/bin/env python3
import os, sys, json, textwrap, base64, shutil
from pathlib import Path
import urllib.request, urllib.parse

def gh_request(method, url, token, data=None, headers=None):
    hdr = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "crypto-risk-dashboard-uploader"
    }
    if headers: hdr.update(headers)
    req = urllib.request.Request(url, data=data, headers=hdr, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.getcode(), resp.read()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8","ignore")
        raise SystemExit(f"HTTP {e.code} Error at {url}\n{body}")

def gh_put_file(user, repo, token, path, content_bytes, message, branch="main"):
    url = f"https://api.github.com/repos/{user}/{repo}/contents/{urllib.parse.quote(path)}"
    payload = {
        "message": message,
        "content": base64.b64encode(content_bytes).decode("utf-8"),
        "branch": branch
    }
    code, body = gh_request("PUT", url, token, data=json.dumps(payload).encode("utf-8"))
    return json.loads(body.decode("utf-8"))

print("=== Upload crypto-risk-dashboard to an EXISTING GitHub repo ===")
gh_user = input("GitHub username: ").strip()
token   = input("GitHub Personal Access Token (classic, scope: repo; SSO authorized if needed): ").strip()
repo    = input("Existing repo name (exact): ").strip()
print("NOTE: The repo must already exist and have a README so branch 'main' exists.")

root = Path.cwd() / "crypto-risk-dashboard-starter"
if root.exists(): shutil.rmtree(root)
root.mkdir(parents=True, exist_ok=True)

def w(relpath: str, content: str):
    p = root / relpath
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")

# ------- Minimal starter (same structure you need) -------
w("README.md", """
# Crypto Risk Dashboard — Self-Hosted Starter
Dockerized stack: FastAPI API, worker (ingest+signals), Postgres (Timescale-ready), Streamlit UI.
Local: `cp .env.example .env` → `docker compose up --build`
Render deploy: use `render.yaml` (free Postgres + API + UI + worker).
""")

w(".env.example", """
POSTGRES_USER=cryptouser
POSTGRES_PASSWORD=cryptopass
POSTGRES_DB=cryptodb
POSTGRES_HOST=db
POSTGRES_PORT=5432
REDIS_URL=redis://redis:6379/0
SYMBOLS=binance:BTC/USDT,binance:ETH/USDT,bybit:SOL/USDT
SCHEDULE_MINUTES=5
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USER_AGENT=crypto-risk-app/0.1 by you
X_BEARER_TOKEN=
CRYPTOPANIC_API_KEY=
NEWSAPI_KEY=
COINGLASS_API_KEY=
""")

w("docker-compose.yml", """
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes: [ "db_data:/var/lib/postgresql/data" ]
    ports: [ "5432:5432" ]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 20
  redis:
    image: redis:7
    ports: [ "6379:6379" ]
  api:
    build: ./services/api
    env_file: .env
    depends_on: { db: { condition: service_healthy } }
    ports: [ "8000:8000" ]
  worker:
    build: ./services/worker
    env_file: .env
    depends_on:
      db: { condition: service_healthy }
      redis: { condition: service_started }
  ui:
    build: ./services/ui
    env_file: .env
    depends_on: { api: { condition: service_started } }
    ports: [ "8501:8501" ]
volumes: { db_data: {} }
""")

w("render.yaml", """
databases:
  - name: cryptodb
    databaseName: cryptodb
    plan: free
services:
  - type: web
    name: crypto-risk-api
    runtime: docker
    rootDir: services/api
    plan: free
    envVars:
      - key: DATABASE_URL
        fromDatabase: { name: cryptodb, property: connectionString }
      - key: SYMBOLS
        value: binance:BTC/USDT,binance:ETH/USDT,bybit:SOL/USDT
      - key: SCHEDULE_MINUTES
        value: "5"
  - type: web
    name: crypto-risk-ui
    runtime: docker
    rootDir: services/ui
    plan: free
    envVars:
      - key: API_CANDIDATES
        value: https://crypto-risk-api.onrender.com,http://api:8000,http://localhost:8000
  - type: worker
    name: crypto-risk-worker
    runtime: docker
    rootDir: services/worker
    plan: free
    envVars:
      - key: DATABASE_URL
        fromDatabase: { name: cryptodb, property: connectionString }
      - key: SYMBOLS
        value: binance:BTC/USDT,binance:ETH/USDT,bybit:SOL/USDT
      - key: SCHEDULE_MINUTES
        value: "5"
""")

common_reqs = """
fastapi==0.115.2
uvicorn[standard]==0.30.6
pydantic==2.9.2
python-dotenv==1.0.1
psycopg2-binary==2.9.9
SQLAlchemy==2.0.36
alembic==1.13.2
redis==5.0.8
celery==5.4.0
pandas==2.2.3
numpy==2.1.2
plotly==5.24.1
matplotlib==3.9.2
ccxt==4.4.6
scikit-learn==1.5.2
textblob==0.18.0.post0
nltk==3.9.1
requests==2.32.3
beautifulsoup4==4.12.3
"""

# API
(api := root / "services/api"); api.mkdir(parents=True, exist_ok=True)
(api / "Dockerfile").write_text("""FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn","main:app","--host","0.0.0.0","--port","8000"]""", encoding="utf-8")
(api / "requirements.txt").write_text(common_reqs, encoding="utf-8")
(api / "main.py").write_text("""
import os
from fastapi import FastAPI, Query
from services_common.db import fetch_df
from services_common.signals import latest_signals_for_pairs, signal_explanations
from services_common.config import load_config

app = FastAPI(title="Crypto Risk API", version="0.1.0")
cfg = load_config()

@app.get("/health")
def health(): return {"ok": True}

@app.get("/pairs")
def pairs(): return {"pairs": cfg.symbols}

@app.get("/signals")
def get_signals(pairs: str = Query(None)):
    pairs_list = [p.strip() for p in pairs.split(",")] if pairs else cfg.symbols
    data = latest_signals_for_pairs(pairs_list)
    return {"signals": data, "explanations": signal_explanations()}

@app.get("/timeseries/{metric}")
def timeseries(metric: str, pair: str, limit: int = 500):
    table_map = {"candles":"candles","funding":"funding_rates","oi":"open_interest","vol":"volatility","sentiment":"sentiment"}
    table = table_map.get(metric)
    if not table: return {"error":"unknown metric"}
    q = f"SELECT * FROM {table} WHERE pair=%(pair)s ORDER BY ts DESC LIMIT %(limit)s"
    df = fetch_df(q, {"pair": pair, "limit": limit})
    return {"columns": list(df.columns), "rows": df.to_dict(orient='records')}
""", encoding="utf-8")

# Worker
(worker := root / "services/worker"); worker.mkdir(parents=True, exist_ok=True)
(worker / "Dockerfile").write_text("""FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python","run_worker.py"]""", encoding="utf-8")
(worker / "requirements.txt").write_text(common_reqs, encoding="utf-8")
(worker / "run_worker.py").write_text("""
import os, time
from services_common.db import ensure_schema
from services_common.ingest import run_ingest_cycle
from services_common.signals import compute_all_signals
def main():
    ensure_schema()
    interval = int(os.getenv("SCHEDULE_MINUTES","5"))
    print(f"[worker] schedule {interval}m")
    while True:
        print("[worker] ingest..."); run_ingest_cycle()
        print("[worker] signals..."); compute_all_signals()
        print("[worker] sleep..."); time.sleep(interval*60)
if __name__=="__main__": main()
""", encoding="utf-8")

# UI
(ui := root / "services/ui"); ui.mkdir(parents=True, exist_ok=True)
(ui / "Dockerfile").write_text("""FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["streamlit","run","app.py","--server.port=8501","--server.address=0.0.0.0"]""", encoding="utf-8")
(ui / "requirements.txt").write_text(common_reqs + "\nstreamlit==1.39.0\nstreamlit_echarts==0.4.0\n", encoding="utf-8")
(ui / "app.py").write_text("""
import os, requests, pandas as pd
import streamlit as st
from urllib.parse import urlencode

DEFAULT_CANDIDATES = [
    "https://crypto-risk-api.onrender.com",
    "http://api:8000",
    "http://localhost:8000",
]

def probe_api(base: str, timeout=2.0) -> bool:
    try:
        r = requests.get(f"{base}/health", timeout=timeout)
        return r.ok and r.json().get("ok") is True
    except Exception: return False

def resolve_api_base():
    env_base = os.getenv("API_BASE","").strip()
    if env_base and probe_api(env_base): return env_base
    env_candidates = os.getenv("API_CANDIDATES","")
    candidates = [c.strip() for c in env_candidates.split(",") if c.strip()] if env_candidates else []
    merged, seen = [], set()
    for x in (candidates + DEFAULT_CANDIDATES):
        if x not in seen: merged.append(x); seen.add(x)
    for base in merged:
        if probe_api(base): return base
    return None

API_BASE = resolve_api_base()

st.set_page_config(page_title="Crypto Risk Dashboard", layout="wide")
st.title("🧭 Crypto Risk Dashboard")
st.caption("Self-hosted. Graphs • Meters • Hot Signals")

if not API_BASE:
    st.error("Could not locate the API automatically.")
    manual = st.text_input("Enter your API base URL")
    if manual and probe_api(manual):
        API_BASE = manual; st.success("Connected!")
if not API_BASE: st.stop()

resp = requests.get(f"{API_BASE}/pairs", timeout=30).json()
pairs = resp.get("pairs", ["binance:BTC/USDT"])

col1, col2 = st.columns([2,1])
with col1: pair = st.selectbox("Pair", pairs, index=0)
with col2: refresh = st.button("Refresh")

def fetch(metric, pair, limit=500):
    qs = urlencode({"pair": pair, "limit": limit})
    return requests.get(f"{API_BASE}/timeseries/{metric}?{qs}", timeout=30).json()

def get_signals(pairs=None):
    qs = "?pairs=" + ",".join(pairs) if pairs else ""
    return requests.get(f"{API_BASE}/signals{qs}", timeout=30).json()

sig = get_signals([pair]); signals = sig.get("signals", {})

st.subheader("Hot Signals")
if signals.get(pair):
    s = signals[pair]
    c1,c2,c3,c4 = st.columns(4)
    with c1: st.metric("Market Regime", s.get("regime","—"))
    with c2: st.metric("Bias", s.get("bias","—"))
    with c3: st.metric("Long Prob. %", round(100*s.get("long_prob",0),1))
    with c4: st.metric("Short Prob. %", round(100*s.get("short_prob",0),1))
    st.info(s.get("summary",""))
else: st.warning("No signals yet. The worker may still be seeding data.")
st.divider(); st.subheader("Charts")
tabs = st.tabs(["Candles","Funding","Open Interest","Volatility","Sentiment"])
with tabs[0]:
    rows = fetch("candles", pair, 300).get("rows", [])
    if rows: st.line_chart(pd.DataFrame(rows).sort_values("ts"), x="ts", y=["close"])
    else: st.write("No data yet.")
with tabs[1]:
    rows = fetch("funding", pair, 500).get("rows", [])
    if rows: st.line_chart(pd.DataFrame(rows).sort_values("ts"), x="ts", y=["rate"])
    else: st.write("No data yet.")
with tabs[2]:
    rows = fetch("oi", pair, 500).get("rows", [])
    if rows: st.line_chart(pd.DataFrame(rows).sort_values("ts"), x="ts", y=["value_usd"])
    else: st.write("No data yet.")
with tabs[3]:
    rows = fetch("vol", pair, 500).get("rows", [])
    if rows: st.line_chart(pd.DataFrame(rows).sort_values("ts"), x="ts", y=["atr"])
    else: st.write("No data yet.")
with tabs[4]:
    rows = fetch("sentiment", pair, 200).get("rows", [])
    if rows: st.line_chart(pd.DataFrame(rows).sort_values("ts"), x="ts", y=["score_norm"])
    else: st.write("No data yet.")
st.divider(); st.caption("Set API_BASE or API_CANDIDATES to skip auto-detect.")
""", encoding="utf-8")

# Shared lib
(common := root / "services/common"); common.mkdir(parents=True, exist_ok=True)
(common / "__init__.py").write_text("", encoding="utf-8")
(common / "config.py").write_text("""
import os
from dataclasses import dataclass
@dataclass
class Config:
    pg_user: str; pg_pass: str; pg_db: str; pg_host: str; pg_port: int; redis_url: str; symbols: list[str]
def load_config() -> Config:
    symbols = [s.strip() for s in os.getenv("SYMBOLS","binance:BTC/USDT").split(",") if s.strip()]
    return Config(
        pg_user=os.getenv("POSTGRES_USER","cryptouser"),
        pg_pass=os.getenv("POSTGRES_PASSWORD","cryptopass"),
        pg_db=os.getenv("POSTGRES_DB","cryptodb"),
        pg_host=os.getenv("POSTGRES_HOST","db"),
        pg_port=int(os.getenv("POSTGRES_PORT","5432")),
        redis_url=os.getenv("REDIS_URL","redis://redis:6379/0"),
        symbols=symbols
    )
""", encoding="utf-8")
(common / "db.py").write_text("""
import os, psycopg2, pandas as pd
from psycopg2.extras import execute_values
def _conn():
    url = os.getenv("DATABASE_URL")
    if url: return psycopg2.connect(url)
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST","db"),
        port=int(os.getenv("POSTGRES_PORT","5432")),
        dbname=os.getenv("POSTGRES_DB","cryptodb"),
        user=os.getenv("POSTGRES_USER","cryptouser"),
        password=os.getenv("POSTGRES_PASSWORD","cryptopass")
    )
def execute(sql, params=None):
    with _conn() as conn, conn.cursor() as cur: cur.execute(sql, params or {})
def fetch_df(sql, params=None)->pd.DataFrame:
    with _conn() as conn: return pd.read_sql(sql, conn, params=params)
def upsert_many(table: str, rows: list[dict], conflict_cols: list[str], update_cols: list[str]):
    if not rows: return
    cols=list(rows[0].keys()); vals=[[r[c] for c in cols] for r in rows]
    on_conflict=", ".join(conflict_cols); updates=", ".join([f"{c}=EXCLUDED.{c}" for c in update_cols])
    sql=f"INSERT INTO {table} ({','.join(cols)}) VALUES %s ON CONFLICT ({on_conflict}) DO UPDATE SET {updates}"
    with _conn() as conn, conn.cursor() as cur: execute_values(cur, sql, vals)
def ensure_schema():
    from services_common.schema import SCHEMA_SQL
    execute(SCHEMA_SQL)
""", encoding="utf-8")
(common / "schema.py").write_text("""
SCHEMA_SQL = '''
CREATE TABLE IF NOT EXISTS candles (pair text NOT NULL, ts timestamptz NOT NULL,
  open double precision, high double precision, low double precision, close double precision, volume double precision,
  PRIMARY KEY (pair, ts));
CREATE TABLE IF NOT EXISTS funding_rates (pair text NOT NULL, ts timestamptz NOT NULL, rate double precision, PRIMARY KEY (pair, ts));
CREATE TABLE IF NOT EXISTS open_interest (pair text NOT NULL, ts timestamptz NOT NULL, value_usd double precision, PRIMARY KEY (pair, ts));
CREATE TABLE IF NOT EXISTS volatility (pair text NOT NULL, ts timestamptz NOT NULL, atr double precision, PRIMARY KEY (pair, ts));
CREATE TABLE IF NOT EXISTS sentiment (pair text NOT NULL, ts timestamptz NOT NULL, mentions integer, score_norm double precision, keywords jsonb, PRIMARY KEY (pair, ts));
CREATE TABLE IF NOT EXISTS headlines (id bigserial PRIMARY KEY, ts timestamptz NOT NULL, source text, title text, url text, keywords jsonb);
CREATE TABLE IF NOT EXISTS signals (id bigserial PRIMARY KEY, ts timestamptz NOT NULL, pair text NOT NULL, regime text, bias text, long_prob double precision, short_prob double precision, summary text);
CREATE TABLE IF NOT EXISTS kv_store (k text PRIMARY KEY, v jsonb, updated_at timestamptz DEFAULT now());
';
""", encoding="utf-8")

# Adapters & ingest & signals
(ad := common / "adapters"); ad.mkdir(parents=True, exist_ok=True)
(ad / "__init__.py").write_text("", encoding="utf-8")
(ad / "exchanges.py").write_text("""
import datetime as dt, ccxt
def fetch_candles(exchange_pair: str, timeframe="1h", limit=200):
    ex_name, pair = exchange_pair.split(":", 1)
    ex = getattr(ccxt, ex_name)()
    ohlcv = ex.fetch_ohlcv(pair, timeframe=timeframe, limit=limit)
    rows=[]
    for t,o,h,l,c,v in ohlcv:
        ts=dt.datetime.utcfromtimestamp(t/1000).replace(tzinfo=dt.timezone.utc)
        rows.append({"pair": exchange_pair,"ts": ts,"open": o,"high": h,"low": l,"close": c,"volume": v})
    return rows
def mock_funding(exchange_pair: str, candles_df):
    rate=(candles_df["close"].pct_change().fillna(0).tail(1).iloc[0])/10 if len(candles_df) else 0.0
    ts=candles_df["ts"].tail(1).iloc[0] if len(candles_df) else dt.datetime.now(dt.timezone.utc)
    return [{"pair": exchange_pair, "ts": ts, "rate": float(rate)}]
""", encoding="utf-8")
(ad / "open_interest.py").write_text("""
import datetime as dt, random
def fetch_open_interest(exchange_pair: str):
    now=dt.datetime.now(dt.timezone.utc).replace(second=0, microsecond=0)
    base=1_000_000 + random.randint(-50_000, 50_000)
    return [{"pair": exchange_pair, "ts": now, "value_usd": float(base)}]
""", encoding="utf-8")
(ad / "volatility.py").write_text("""
def compute_atr_like(candles_df, window=14):
    if len(candles_df)==0: return None
    df=candles_df.copy().sort_values("ts")
    hl=df["high"]-df["low"]
    hc=(df["high"]-df["close"].shift()).abs()
    lc=(df["low"]-df["close"].shift()).abs()
    tr=(hl.to_frame("hl").join(hc.to_frame("hc")).join(lc.to_frame("lc"))).max(axis=1)
    atr=tr.rolling(window).mean()
    last=df["ts"].iloc[-1]
    return [{"pair": df["pair"].iloc[-1], "ts": last, "atr": float(atr.iloc[-1])}]
""", encoding="utf-8")
(ad / "sentiment.py").write_text("""
import datetime as dt, random
KEYWORDS=["liquidation","margin call","rekt","funding","open interest"]
def fetch_sentiment_mock(exchange_pair: str):
    now=dt.datetime.now(dt.timezone.utc).replace(second=0, microsecond=0)
    mentions=random.randint(5,50); score=random.uniform(-1,1)
    kw_counts={k: random.randint(0, mentions//2) for k in KEYWORDS}
    return [{"pair": exchange_pair, "ts": now, "mentions": mentions, "score_norm": score, "keywords": kw_counts}]
""", encoding="utf-8")
(ad / "headlines.py").write_text("""
import datetime as dt
def fetch_headlines_mock():
    now=dt.datetime.now(dt.timezone.utc)
    return [{"ts": now,"source":"mock","title":"Market wobbles as OI surges; funding flips negative","url":"https://example.com","keywords":["open interest","funding"]}]
""", encoding="utf-8")

(common / "ingest.py").write_text("""
import pandas as pd
from services_common.config import load_config
from services_common.db import upsert_many
from services_common.adapters.exchanges import fetch_candles, mock_funding
from services_common.adapters.open_interest import fetch_open_interest
from services_common.adapters.volatility import compute_atr_like
from services_common.adapters.sentiment import fetch_sentiment_mock
from services_common.adapters.headlines import fetch_headlines_mock
cfg = load_config()
def run_ingest_cycle():
    for pair in cfg.symbols:
        candle_rows = fetch_candles(pair, timeframe="1h", limit=200)
        upsert_many("candles", candle_rows, ["pair","ts"], ["open","high","low","close","volume"])
        df = pd.DataFrame(candle_rows)
        upsert_many("funding_rates", mock_funding(pair, df), ["pair","ts"], ["rate"])
        upsert_many("open_interest",  fetch_open_interest(pair), ["pair","ts"], ["value_usd"])
        vol = compute_atr_like(df)
        if vol: upsert_many("volatility", vol, ["pair","ts"], ["atr"])
        upsert_many("sentiment", fetch_sentiment_mock(pair), ["pair","ts"], ["mentions","score_norm","keywords"])
    upsert_many("headlines", fetch_headlines_mock(), ["id"], [])
""", encoding="utf-8")

(common / "signals.py").write_text("""
import pandas as pd
from services_common.db import fetch_df, upsert_many
from datetime import datetime, timezone
def _percentile(series: pd.Series, value: float):
    if series.empty: return None
    return (series < value).mean() * 100.0
def compute_market_stress(pair: str):
    oi = fetch_df("SELECT ts, value_usd FROM open_interest WHERE pair=%(pair)s AND ts > now() - interval '30 days' ORDER BY ts", {"pair": pair})
    fr = fetch_df("SELECT ts, rate FROM funding_rates WHERE pair=%(pair)s AND ts > now() - interval '14 days' ORDER BY ts", {"pair": pair})
    sent = fetch_df("SELECT ts, mentions, score_norm, keywords FROM sentiment WHERE pair=%(pair)s AND ts > now() - interval '14 days' ORDER BY ts", {"pair": pair})
    regime, bias = "Unknown", "Neutral"; long_prob = short_prob = 0.5; summary = "Insufficient data."
    if not oi.empty and not fr.empty and not sent.empty:
        latest_oi = oi["value_usd"].iloc[-1]; oi_pct = _percentile(oi["value_usd"], latest_oi); latest_funding = fr["rate"].iloc[-1]
        sent["liq_kw"] = sent["keywords"].apply(lambda d: (d.get("liquidation",0) if isinstance(d, dict) else 0) + (d.get("margin call",0) if isinstance(d, dict) else 0))
        last_week = sent.tail(max(1, len(sent)//2)); first_week = sent.head(len(sent)-len(last_week)) if len(sent)>1 else sent.head(1)
        base = max(1, first_week["liq_kw"].sum()); spike_ratio = (last_week["liq_kw"].sum()) / base
        if (oi_pct is not None) and oi_pct >= 90 and latest_funding < 0 and spike_ratio >= 2.0:
            regime, bias, long_prob, short_prob = "Risky / High Liquidation Risk","Short",0.25,0.75
            summary = "OI in 90th pct+, funding negative, and liquidation mentions up ≥200%. Consider caution or short bias."
        else:
            candles = fetch_df("SELECT ts, close FROM candles WHERE pair=%(pair)s ORDER BY ts DESC LIMIT 50", {"pair": pair}).sort_values("ts")
            slope = candles["close"].pct_change().fillna(0).tail(10).mean() if not candles.empty else 0.0
            if slope > 0 and latest_funding >= 0:
                regime, bias, long_prob, short_prob = "Constructive","Long",0.65,0.35
                summary = "Upward momentum + non-negative funding → modest long bias."
            elif slope < 0 and latest_funding <= 0:
                regime, bias, long_prob, short_prob = "Weak","Short",0.35,0.65
                summary = "Downward momentum + non-positive funding → modest short bias."
            else:
                regime, bias, long_prob, short_prob = "Balanced / Choppy","Flat",0.5,0.5
                summary = "Mixed signals; consider mean-reversion or wait."
    return {"pair": pair, "regime": regime, "bias": bias, "long_prob": float(long_prob), "short_prob": float(short_prob), "summary": summary}
def compute_all_signals():
    dfpairs = fetch_df("SELECT DISTINCT pair FROM candles"); out=[]
    for p in dfpairs.get("pair", []): out.append(compute_market_stress(p))
    now = datetime.now(timezone.utc)
    rows = [{"ts": now,"pair": s["pair"],"regime": s["regime"],"bias": s["bias"],"long_prob": s["long_prob"],"short_prob": s["short_prob"],"summary": s["summary"]} for s in out]
    if rows: upsert_many("signals", rows, ["id"], [])
def latest_signals_for_pairs(pairs: list[str]):
    placeholders = ",".join(["%s"]*len(pairs))
    q = f"SELECT DISTINCT ON (pair) pair, ts, regime, bias, long_prob, short_prob, summary FROM signals WHERE pair IN ({placeholders}) ORDER BY pair, ts DESC"
    df = fetch_df(q, pairs); result={}
    for _, r in df.iterrows(): result[r["pair"]] = dict(r)
    return result
def signal_explanations():
    return {"market_stress": "OI ≥ 90th pct + negative funding + liquidation keyword spike ≥ 200% → bearish risk."}
""", encoding="utf-8")

# Make services_common importable in Docker builds
(api / "services_common").mkdir(exist_ok=True)
(worker / "services_common").mkdir(exist_ok=True)
(api / "services_common/__init__.py").write_text("from pathlib import Path as _P; import sys as _s; _s.path.append(str(_P(__file__).resolve().parents[2]))\n", encoding="utf-8")
(worker / "services_common/__init__.py").write_text("from pathlib import Path as _P; import sys as _s; _s.path.append(str(_P(__file__).resolve().parents[2]))\n", encoding="utf-8")

# Upload all files
print("Uploading files to GitHub (branch 'main')...")
for p in root.rglob("*"):
    if p.is_dir(): continue
    rel = str(p.relative_to(root)).replace("\\", "/")
    content = p.read_bytes()
    gh_put_file(gh_user, repo, token, rel, content, f"Add {rel}", branch="main")

print("\n✅ Done!")
print(f"GitHub repository: https://github.com/{gh_user}/{repo}")
print("Next: Render → Blueprints → New Blueprint → pick this repo → Create.")
