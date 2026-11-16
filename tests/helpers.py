"""Generadores de velas sintéticas con indicadores calculados solo con pandas."""
import numpy as np
import pandas as pd


def zigzag_frame(legs, start=100.0, seed=1, noise=0.15, volume=True):
    """legs = [(n_velas, delta_precio), ...] → DataFrame OHLC + indicadores básicos."""
    rng = np.random.default_rng(seed)
    closes = [start]
    for bars, delta in legs:
        step = delta / bars
        for _ in range(bars):
            closes.append(closes[-1] + step + rng.normal(0, noise))
    close = pd.Series(closes[1:], dtype=float)
    open_ = close.shift(1).fillna(start) + rng.normal(0, noise * 0.3, len(close))
    high = np.maximum(open_, close) + np.abs(rng.normal(0, noise * 0.8, len(close)))
    low = np.minimum(open_, close) - np.abs(rng.normal(0, noise * 0.8, len(close)))
    idx = pd.date_range("2026-01-01", periods=len(close), freq="h", tz="UTC")
    df = pd.DataFrame({"Open": open_.to_numpy(), "High": np.asarray(high), "Low": np.asarray(low), "Close": close.to_numpy()}, index=idx)
    df["Volume"] = rng.integers(800, 1200, len(df)).astype(float) if volume else 0.0
    return add_indicators(df)


def add_indicators(df):
    c, h, l = df["Close"], df["High"], df["Low"]
    df["EMA50"] = c.ewm(span=50, adjust=False).mean()
    df["EMA200"] = c.ewm(span=200, adjust=False).mean()
    delta = c.diff()
    up, down = delta.clip(lower=0), -delta.clip(upper=0)
    rs = up.ewm(alpha=1 / 14, adjust=False).mean() / down.ewm(alpha=1 / 14, adjust=False).mean().replace(0, np.nan)
    df["RSI"] = (100 - 100 / (1 + rs)).fillna(50)
    macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    df["MACD"] = macd
    df["MACD_SIGNAL"] = macd.ewm(span=9, adjust=False).mean()
    df["MACD_HIST"] = df["MACD"] - df["MACD_SIGNAL"]
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    df["ATR"] = tr.ewm(alpha=1 / 14, adjust=False).mean()
    return df.dropna()
