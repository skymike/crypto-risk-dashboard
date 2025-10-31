import datetime as dt, random

def fetch_open_interest(exchange_pair: str):
    now = dt.datetime.now(dt.timezone.utc).replace(second=0, microsecond=0)
    base = 1_000_000 + random.randint(-50_000, 50_000)
    return [{"pair": exchange_pair, "ts": now, "value_usd": float(base)}]
