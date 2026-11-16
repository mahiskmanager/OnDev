"""Estructura de mercado y Smart Money Concepts con reglas explícitas.

Solo depende de pandas/numpy: swings, BOS/CHoCH, order blocks, FVG, barridos de
liquidez, premium/descuento, Fibonacci, VWAP, soportes/resistencias por
confluencia, divergencias y patrones chartistas. Son heurísticas programáticas
y transparentes, no una lectura discrecional de gráfico.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# ───────────────────────── swings y estructura ─────────────────────────
def swing_points(df: pd.DataFrame, n: int = 3) -> list[dict]:
    """Fractales confirmados: máximo/mínimo con n velas a cada lado."""
    highs, lows = df["High"].to_numpy(float), df["Low"].to_numpy(float)
    out: list[dict] = []
    for i in range(n, len(df) - n):
        left_h, right_h = highs[i - n:i], highs[i + 1:i + n + 1]
        left_l, right_l = lows[i - n:i], lows[i + 1:i + n + 1]
        if highs[i] >= left_h.max() and highs[i] > right_h.max():
            out.append({"pos": i, "price": float(highs[i]), "kind": "H"})
        if lows[i] <= left_l.min() and lows[i] < right_l.min():
            out.append({"pos": i, "price": float(lows[i]), "kind": "L"})
    out.sort(key=lambda s: s["pos"])
    return out


def market_structure(df: pd.DataFrame, n: int = 3) -> dict:
    sw = swing_points(df, n)
    highs = [s for s in sw if s["kind"] == "H"]
    lows = [s for s in sw if s["kind"] == "L"]
    close = float(df["Close"].iloc[-1])
    atr = float(df["ATR"].iloc[-1]) if "ATR" in df else float((df["High"] - df["Low"]).tail(14).mean())
    res = {"trend": "LATERAL", "effective_trend": "LATERAL", "event": None, "event_status": None,
           "last_high": highs[-1]["price"] if highs else None,
           "last_low": lows[-1]["price"] if lows else None, "swings": sw}
    if len(highs) < 2 or len(lows) < 2:
        return res
    hh, lh = highs[-1]["price"] > highs[-2]["price"], highs[-1]["price"] < highs[-2]["price"]
    hl, ll = lows[-1]["price"] > lows[-2]["price"], lows[-1]["price"] < lows[-2]["price"]
    trend = "ALCISTA" if hh and hl else ("BAJISTA" if lh and ll else "LATERAL")
    res["trend"] = res["effective_trend"] = trend
    top, bottom = highs[-1]["price"], lows[-1]["price"]
    near = 0.3 * atr
    if trend == "ALCISTA":
        if close > top:
            res["event"], res["event_status"] = "BOS alcista", "CONFIRMADO"
        elif close < bottom:
            res["event"], res["event_status"] = "CHoCH bajista", "CONFIRMADO"
            res["effective_trend"] = "LATERAL"
        elif top - close <= near:
            res["event"], res["event_status"] = "BOS alcista", "PENDIENTE"
        elif close - bottom <= near:
            res["event"], res["event_status"] = "CHoCH bajista", "PENDIENTE"
    elif trend == "BAJISTA":
        if close < bottom:
            res["event"], res["event_status"] = "BOS bajista", "CONFIRMADO"
        elif close > top:
            res["event"], res["event_status"] = "CHoCH alcista", "CONFIRMADO"
            res["effective_trend"] = "LATERAL"
        elif close - bottom <= near:
            res["event"], res["event_status"] = "BOS bajista", "PENDIENTE"
        elif top - close <= near:
            res["event"], res["event_status"] = "CHoCH alcista", "PENDIENTE"
    else:
        if close > top:
            res["event"], res["event_status"] = "BOS alcista (ruptura de rango)", "CONFIRMADO"
        elif close < bottom:
            res["event"], res["event_status"] = "BOS bajista (ruptura de rango)", "CONFIRMADO"
    return res


# ───────────────────────── SMC: FVG, OB, barridos ─────────────────────────
def fair_value_gaps(df: pd.DataFrame, atr: float, lookback: int = 80) -> list[dict]:
    """FVG abiertos (no rellenados por completo), más recientes primero."""
    h, l = df["High"].to_numpy(float), df["Low"].to_numpy(float)
    out: list[dict] = []
    start = max(2, len(df) - lookback)
    for i in range(start, len(df)):
        if l[i] > h[i - 2] and (l[i] - h[i - 2]) >= 0.1 * atr:
            lo, hi = float(h[i - 2]), float(l[i])
            if i == len(df) - 1 or l[i + 1:].min() > lo:
                out.append({"side": "BULLISH", "low": lo, "high": hi, "bars_ago": len(df) - 1 - i})
        if h[i] < l[i - 2] and (l[i - 2] - h[i]) >= 0.1 * atr:
            lo, hi = float(h[i]), float(l[i - 2])
            if i == len(df) - 1 or h[i + 1:].max() < hi:
                out.append({"side": "BEARISH", "low": lo, "high": hi, "bars_ago": len(df) - 1 - i})
    return sorted(out, key=lambda z: z["bars_ago"])


def order_blocks(df: pd.DataFrame, atr: float, lookback: int = 100) -> list[dict]:
    """Última vela contraria antes de un desplazamiento ≥1.5 ATR, no invalidada."""
    o, c = df["Open"].to_numpy(float), df["Close"].to_numpy(float)
    h, l = df["High"].to_numpy(float), df["Low"].to_numpy(float)
    out: list[dict] = []
    start = max(0, len(df) - lookback)
    for i in range(start, len(df) - 2):
        window_end = min(len(df), i + 4)
        if c[i] < o[i] and c[i + 1] > o[i + 1]:
            if c[i + 1:window_end].max() > h[i] and c[i + 1:window_end].max() - l[i] >= 1.5 * atr:
                if c[i + 1:].min() >= l[i]:
                    out.append({"side": "BULLISH", "low": float(l[i]), "high": float(h[i]),
                                "bars_ago": len(df) - 1 - i,
                                "tested": bool(l[i + 4:].min() <= h[i]) if i + 4 < len(df) else False})
        if c[i] > o[i] and c[i + 1] < o[i + 1]:
            if c[i + 1:window_end].min() < l[i] and h[i] - c[i + 1:window_end].min() >= 1.5 * atr:
                if c[i + 1:].max() <= h[i]:
                    out.append({"side": "BEARISH", "low": float(l[i]), "high": float(h[i]),
                                "bars_ago": len(df) - 1 - i,
                                "tested": bool(h[i + 4:].max() >= l[i]) if i + 4 < len(df) else False})
    return sorted(out, key=lambda z: z["bars_ago"])


def liquidity_sweeps(df: pd.DataFrame, n: int = 3, window: int = 12) -> list[dict]:
    """Mecha que supera un swing previo y cierra de vuelta dentro del rango."""
    sw = swing_points(df, n)
    h, l, c = df["High"].to_numpy(float), df["Low"].to_numpy(float), df["Close"].to_numpy(float)
    out: list[dict] = []
    for k in range(max(0, len(df) - window), len(df)):
        for s in sw:
            if s["pos"] >= k - n:
                continue
            if s["kind"] == "H" and h[k] > s["price"] and c[k] < s["price"]:
                out.append({"side": "HIGH", "level": s["price"], "bias": "BEARISH", "bars_ago": len(df) - 1 - k})
            if s["kind"] == "L" and l[k] < s["price"] and c[k] > s["price"]:
                out.append({"side": "LOW", "level": s["price"], "bias": "BULLISH", "bars_ago": len(df) - 1 - k})
    seen, uniq = set(), []
    for x in sorted(out, key=lambda z: z["bars_ago"]):
        key = (x["side"], round(x["level"], 8))
        if key not in seen:
            seen.add(key)
            uniq.append(x)
    return uniq


def premium_discount(df: pd.DataFrame, n: int = 3) -> dict | None:
    sw = swing_points(df, n)
    highs = [s["price"] for s in sw if s["kind"] == "H"][-2:]
    lows = [s["price"] for s in sw if s["kind"] == "L"][-2:]
    if not highs or not lows:
        return None
    hi, lo = max(highs), min(lows)
    if hi <= lo:
        return None
    price = float(df["Close"].iloc[-1])
    pos = (price - lo) / (hi - lo)
    zone = "DESCUENTO" if pos < 0.45 else ("PREMIUM" if pos > 0.55 else "EQUILIBRIO")
    return {"high": hi, "low": lo, "equilibrium": (hi + lo) / 2, "position": pos, "zone": zone}


# ───────────────────────── niveles ─────────────────────────
def fib_levels(hi: float, lo: float) -> dict[str, float]:
    span = hi - lo
    return {f"Fib {r}": hi - r * span for r in (0.382, 0.5, 0.618, 0.786)}


def vwap(df: pd.DataFrame, window: int = 50) -> float | None:
    if "Volume" not in df or float(df["Volume"].tail(window).sum()) <= 0:
        return None
    t = df.tail(window)
    typical = (t["High"] + t["Low"] + t["Close"]) / 3
    return float((typical * t["Volume"]).sum() / t["Volume"].sum())


def support_resistance(df: pd.DataFrame, price: float, atr: float, extras: dict[str, float | None] | None = None,
                       n: int = 3, lookback: int = 150) -> dict:
    """Agrupa swings, extremos, medias, VWAP y Fibonacci en zonas de confluencia."""
    tail = df.tail(lookback)
    items: list[tuple[float, str]] = []
    for s in swing_points(tail, n):
        items.append((s["price"], "swing alto" if s["kind"] == "H" else "swing bajo"))
    items.append((float(tail["High"].max()), "máximo reciente"))
    items.append((float(tail["Low"].min()), "mínimo reciente"))
    for name, value in (extras or {}).items():
        if value is not None and np.isfinite(value):
            items.append((float(value), name))
    items.sort(key=lambda x: x[0])
    clusters: list[dict] = []
    for value, label in items:
        if clusters and abs(value - clusters[-1]["members"][-1][0]) <= 0.5 * atr:
            clusters[-1]["members"].append((value, label))
        else:
            clusters.append({"members": [(value, label)]})
    zones = []
    for cl in clusters:
        vals = [m[0] for m in cl["members"]]
        zones.append({"price": float(np.mean(vals)), "low": min(vals), "high": max(vals),
                      "strength": len(vals), "labels": sorted({m[1] for m in cl["members"]})})
    supports = sorted([z for z in zones if z["price"] < price], key=lambda z: -z["price"])
    resistances = sorted([z for z in zones if z["price"] > price], key=lambda z: z["price"])
    strongest = max(zones, key=lambda z: (z["strength"], -abs(z["price"] - price)), default=None)
    return {"supports": supports[:3], "resistances": resistances[:3], "strongest": strongest, "all": zones}


# ───────────────────────── divergencias ─────────────────────────
def divergence(df: pd.DataFrame, osc: str, n: int = 3) -> str | None:
    """'BEARISH' / 'BULLISH' si los dos últimos swings divergen del oscilador."""
    if osc not in df:
        return None
    sw = swing_points(df, n)
    highs = [s for s in sw if s["kind"] == "H"][-2:]
    lows = [s for s in sw if s["kind"] == "L"][-2:]
    values = df[osc].to_numpy(float)
    if len(highs) == 2 and highs[1]["price"] > highs[0]["price"] and values[highs[1]["pos"]] < values[highs[0]["pos"]]:
        return "BEARISH"
    if len(lows) == 2 and lows[1]["price"] < lows[0]["price"] and values[lows[1]["pos"]] > values[lows[0]["pos"]]:
        return "BULLISH"
    return None


# ───────────────────────── patrones chartistas ─────────────────────────
def _slope(points: list[dict]) -> float:
    xs = np.array([p["pos"] for p in points], float)
    ys = np.array([p["price"] for p in points], float)
    return float(np.polyfit(xs, ys, 1)[0]) if len(points) >= 2 else 0.0


def chart_patterns(df: pd.DataFrame, atr: float, n: int = 3) -> list[dict]:
    """Doble techo/suelo, hombro-cabeza-hombro (y su inverso), triángulos, cuñas y banderas."""
    sw = swing_points(df, n)
    highs = [s for s in sw if s["kind"] == "H"]
    lows = [s for s in sw if s["kind"] == "L"]
    close = float(df["Close"].iloc[-1])
    tol = 0.6 * atr
    out: list[dict] = []

    def add(name, bias, detail):
        out.append({"name": name, "bias": bias, "detail": detail})

    if len(highs) >= 2 and abs(highs[-1]["price"] - highs[-2]["price"]) <= tol:
        between = [s["price"] for s in lows if highs[-2]["pos"] < s["pos"] < highs[-1]["pos"]]
        if between and highs[-2]["price"] - min(between) >= 1.5 * atr:
            neck = min(between)
            add("Doble techo", "BEARISH", f"cuello {neck:.5g}; " + ("confirmado" if close < neck else "pendiente de ruptura del cuello"))
    if len(lows) >= 2 and abs(lows[-1]["price"] - lows[-2]["price"]) <= tol:
        between = [s["price"] for s in highs if lows[-2]["pos"] < s["pos"] < lows[-1]["pos"]]
        if between and max(between) - lows[-2]["price"] >= 1.5 * atr:
            neck = max(between)
            add("Doble suelo", "BULLISH", f"cuello {neck:.5g}; " + ("confirmado" if close > neck else "pendiente de ruptura del cuello"))
    if len(highs) >= 3:
        l, h, r = highs[-3], highs[-2], highs[-1]
        troughs = [s["price"] for s in lows if l["pos"] < s["pos"] < r["pos"]]
        if h["price"] > l["price"] and h["price"] > r["price"] and abs(l["price"] - r["price"]) <= 1.2 * atr and len(troughs) >= 2:
            neck = float(np.mean(sorted(troughs)[:2]))
            add("Hombro-cabeza-hombro", "BEARISH", f"cuello ≈ {neck:.5g}; " + ("confirmado" if close < neck else "sin ruptura del cuello"))
    if len(lows) >= 3:
        l, h, r = lows[-3], lows[-2], lows[-1]
        peaks = [s["price"] for s in highs if l["pos"] < s["pos"] < r["pos"]]
        if h["price"] < l["price"] and h["price"] < r["price"] and abs(l["price"] - r["price"]) <= 1.2 * atr and len(peaks) >= 2:
            neck = float(np.mean(sorted(peaks)[-2:]))
            add("Hombro-cabeza-hombro invertido", "BULLISH", f"cuello ≈ {neck:.5g}; " + ("confirmado" if close > neck else "sin ruptura del cuello"))
    if len(highs) >= 3 and len(lows) >= 3:
        hs, ls = _slope(highs[-3:]), _slope(lows[-3:])
        flat = 0.05 * atr
        if hs < -flat and ls > flat:
            add("Triángulo simétrico", "NEUTRAL", "máximos descendentes y mínimos ascendentes; vigilar ruptura")
        elif abs(hs) <= flat and ls > flat:
            add("Triángulo ascendente", "BULLISH", "techo plano con mínimos ascendentes")
        elif hs < -flat and abs(ls) <= flat:
            add("Triángulo descendente", "BEARISH", "suelo plano con máximos descendentes")
        elif hs > flat and ls > flat and ls > hs:
            add("Cuña ascendente", "BEARISH", "ambos extremos suben y se estrechan")
        elif hs < -flat and ls < -flat and hs < ls:
            add("Cuña descendente", "BULLISH", "ambos extremos bajan y se estrechan")
    if len(df) >= 25:
        seg = df.tail(25)
        impulse = seg.iloc[:12]
        flag = seg.iloc[12:]
        move = float(impulse["Close"].iloc[-1] - impulse["Close"].iloc[0])
        rng = float(flag["High"].max() - flag["Low"].min())
        drift = float(flag["Close"].iloc[-1] - flag["Close"].iloc[0])
        if abs(move) >= 3 * atr and rng <= 2 * atr:
            if move > 0 and drift <= 0:
                add("Bandera alcista", "BULLISH", "impulso fuerte y corrección estrecha")
            elif move < 0 and drift >= 0:
                add("Bandera bajista", "BEARISH", "impulso fuerte y rebote estrecho")
    return out
