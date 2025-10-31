import datetime as dt
def fetch_headlines_mock():
    now = dt.datetime.now(dt.timezone.utc)
    return [{
        "ts": now, "source": "mock", "title": "Market wobbles as OI surges; funding flips negative",
        "url": "https://example.com", "keywords": ["open interest", "funding"]
    }]
