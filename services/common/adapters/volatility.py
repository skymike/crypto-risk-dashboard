def compute_atr_like(candles_df, window=14):
    if len(candles_df)==0: return None
    df = candles_df.copy().sort_values("ts")
    hl = df["high"] - df["low"]
    hc = (df["high"] - df["close"].shift()).abs()
    lc = (df["low"] - df["close"].shift()).abs()
    tr = (hl.to_frame("hl").join(hc.to_frame("hc")).join(lc.to_frame("lc"))).max(axis=1)
    atr = tr.rolling(window).mean()
    last = df["ts"].iloc[-1]
    return [{"pair": df["pair"].iloc[-1], "ts": last, "atr": float(atr.iloc[-1])}]
