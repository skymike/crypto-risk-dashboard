import datetime as dt, ccxt

def fetch_candles(exchange_pair: str, timeframe="1h", limit=200):
    ex_name, pair = exchange_pair.split(":", 1)
    ex = getattr(ccxt, ex_name)()
    ohlcv = ex.fetch_ohlcv(pair, timeframe=timeframe, limit=limit)
    rows = []
    for t,o,h,l,c,v in ohlcv:
        ts = dt.datetime.utcfromtimestamp(t/1000).replace(tzinfo=dt.timezone.utc)
        rows.append({"pair": exchange_pair, "ts": ts, "open": o, "high": h, "low": l, "close": c, "volume": v})
    return rows

def mock_funding(exchange_pair: str, candles_df):
    rate = (candles_df["close"].pct_change().fillna(0).tail(1).iloc[0]) / 10 if len(candles_df) else 0.0
    ts = candles_df["ts"].tail(1).iloc[0] if len(candles_df) else dt.datetime.now(dt.timezone.utc)
    return [{"pair": exchange_pair, "ts": ts, "rate": float(rate)}]
