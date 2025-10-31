import datetime as dt, random
KEYWORDS = ["liquidation","margin call","rekt","funding","open interest"]

def fetch_sentiment_mock(exchange_pair: str):
    now = dt.datetime.now(dt.timezone.utc).replace(second=0, microsecond=0)
    mentions = random.randint(5, 50)
    score = random.uniform(-1, 1)
    kw_counts = {k: random.randint(0, mentions//2) for k in KEYWORDS}
    return [{"pair": exchange_pair, "ts": now, "mentions": mentions, "score_norm": score, "keywords": kw_counts}]
