from fastapi import FastAPI, Query
from services_common.db import fetch_df
from services_common.signals import latest_signals_for_pairs, signal_explanations
from services_common.config import load_config

app = FastAPI(title="Crypto Risk API", version="0.2.0")
cfg = load_config()

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/pairs")
def pairs():
    return {"pairs": cfg.symbols}

@app.get("/signals")
def get_signals(pairs: str | None = Query(None)):
    pairs_list = [p.strip() for p in pairs.split(",")] if pairs else cfg.symbols
    data = latest_signals_for_pairs(pairs_list)
    return {"signals": data, "explanations": signal_explanations()}

@app.get("/timeseries/{metric}")
def timeseries(metric: str, pair: str, limit: int = 500):
    table_map = {
        "candles": "candles",
        "funding": "funding_rates",
        "oi": "open_interest",
        "vol": "volatility",
        "sentiment": "sentiment"
    }
    if metric not in table_map:
        return {"error": "unknown metric"}
    table = table_map[metric]
    q = f"""
        SELECT * FROM {table}
        WHERE pair = %(pair)s
        ORDER BY ts DESC
        LIMIT %(limit)s
    """
    df = fetch_df(q, {"pair": pair, "limit": limit})
    return {"columns": list(df.columns), "rows": df.to_dict(orient="records")}
