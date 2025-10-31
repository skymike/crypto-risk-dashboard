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
        fr = mock_funding(pair, df); upsert_many("funding_rates", fr, ["pair","ts"], ["rate"])

        oi = fetch_open_interest(pair); upsert_many("open_interest", oi, ["pair","ts"], ["value_usd"])

        vol = compute_atr_like(df)
        if vol: upsert_many("volatility", vol, ["pair","ts"], ["atr"])

        sent = fetch_sentiment_mock(pair); upsert_many("sentiment", sent, ["pair","ts"], ["mentions","score_norm","keywords"])

    h = fetch_headlines_mock()
    upsert_many("headlines", h, ["id"], [])
