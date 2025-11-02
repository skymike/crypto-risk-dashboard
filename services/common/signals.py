import pandas as pd
from services.common.db import fetch_df, upsert_many, execute

def _percentile(series: pd.Series, value: float):
    if series.empty:
        return None
    return (series < value).mean() * 100.0

def compute_market_stress(pair: str):
    oi = fetch_df("""
        SELECT ts, value_usd FROM open_interest
        WHERE pair=%(pair)s AND ts > now() - interval '30 days'
        ORDER BY ts
    """, {"pair": pair})
    fr = fetch_df("""
        SELECT ts, rate FROM funding_rates
        WHERE pair=%(pair)s AND ts > now() - interval '14 days'
        ORDER BY ts
    """, {"pair": pair})
    sent = fetch_df("""
        SELECT ts, mentions, score_norm, keywords FROM sentiment
        WHERE pair=%(pair)s AND ts > now() - interval '14 days'
        ORDER BY ts
    """, {"pair": pair})

    regime = "Unknown"
    bias = "Neutral"
    long_prob = 0.5
    short_prob = 0.5
    summary = "Insufficient data."

    if not oi.empty and not fr.empty and not sent.empty:
        latest_oi = oi["value_usd"].iloc[-1]
        oi_pct = _percentile(oi["value_usd"], latest_oi)
        latest_funding = fr["rate"].iloc[-1]
        sent["liq_kw"] = sent["keywords"].apply(lambda d: (d.get("liquidation",0) if isinstance(d, dict) else 0) + (d.get("margin call",0) if isinstance(d, dict) else 0))
        last_week = sent.tail(max(1, len(sent)//2))
        first_week = sent.head(len(sent)-len(last_week)) if len(sent)>1 else sent.head(1)
        base = max(1, first_week["liq_kw"].sum())
        spike_ratio = (last_week["liq_kw"].sum()) / base

        if oi_pct is not None and oi_pct >= 90 and latest_funding < 0 and spike_ratio >= 2.0:
            regime = "Risky / High Liquidation Risk"
            bias = "Short"
            long_prob = 0.25
            short_prob = 0.75
            summary = "OI in 90th pct+, funding negative, and liquidation mentions up ≥200%. Consider caution or short bias."
        else:
            candles = fetch_df("""
                SELECT ts, close FROM candles WHERE pair=%(pair)s ORDER BY ts DESC LIMIT 50
            """, {"pair": pair}).sort_values("ts")
            slope = 0.0
            if not candles.empty:
                y = candles["close"].pct_change().fillna(0).tail(10)
                slope = y.mean()
            if slope > 0 and latest_funding >= 0:
                regime = "Constructive"
                bias = "Long"
                long_prob = 0.65
                short_prob = 0.35
                summary = "Upward momentum with non-negative funding suggests a modest long bias."
            elif slope < 0 and latest_funding <= 0:
                regime = "Weak"
                bias = "Short"
                long_prob = 0.35
                short_prob = 0.65
                summary = "Downward momentum with non-positive funding suggests a modest short bias."
            else:
                regime = "Balanced / Choppy"
                bias = "Flat"
                long_prob = 0.5
                short_prob = 0.5
                summary = "Mixed signals; prefer mean-reversion or wait for clarity."

    return {
        "pair": pair,
        "regime": regime,
        "bias": bias,
        "long_prob": float(long_prob),
        "short_prob": float(short_prob),
        "summary": summary
    }

def compute_all_signals():
    pairs_df = fetch_df("SELECT DISTINCT pair FROM candles")
    pairs = list(pairs_df["pair"]) if "pair" in pairs_df else []
    out = []
    for p in pairs:
        s = compute_market_stress(p)
        out.append(s)
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    rows = [{
        "ts": now, "pair": s["pair"], "regime": s["regime"], "bias": s["bias"],
        "long_prob": s["long_prob"], "short_prob": s["short_prob"], "summary": s["summary"]
    } for s in out]
    if rows:
        sql = """
        INSERT INTO signals (ts, pair, regime, bias, long_prob, short_prob, summary)
        VALUES (%(ts)s, %(pair)s, %(regime)s, %(bias)s, %(long_prob)s, %(short_prob)s, %(summary)s)
        """
        for row in rows:
            execute(sql, row)

def latest_signals_for_pairs(pairs: list[str]):
    placeholders = ",".join(["%s"]*len(pairs))
    q = f"""
        SELECT DISTINCT ON (pair) pair, ts, regime, bias, long_prob, short_prob, summary
        FROM signals
        WHERE pair IN ({placeholders})
        ORDER BY pair, ts DESC
    """
    df = fetch_df(q, pairs)
    result = {}
    for _, r in df.iterrows():
        result[r["pair"]] = dict(r)
    return result

def signal_explanations():
    return {"market_stress": "OI ≥ 90th pct + negative funding + liquidation keyword spike ≥ 200% → bearish risk."}
