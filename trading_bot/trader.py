"""Analista institucional: sesgo 1D+4H, ejecución 1H+15M, confluencia 3/5 y gestión de riesgo.

`evaluate_institutional` es una función pura (solo pandas) para poder probarla sin red.
La IA (Groq) solo redacta noticias y explicación; no decide dirección ni niveles.
"""
from __future__ import annotations

import asyncio
import logging
import math

import pandas as pd

from . import config, smc
from .patterns import detect_patterns

log = logging.getLogger(__name__)
AMBIGUOUS_PHRASE = "Condiciones ambiguas. Me mantengo fuera del mercado y explico por qué."
NEUTRAL_NEWS = {
    "news_summary": "Sin titulares verificables en las últimas 24 h.",
    "sentiment_label": "Neutral", "sentiment_score": 0.0,
    "macro_events": None, "high_impact_imminent": False, "available": False,
}


def _col(frame: pd.DataFrame, name: str):
    return float(frame[name].iloc[-1]) if name in frame and pd.notna(frame[name].iloc[-1]) else None


def _volume_state(frame: pd.DataFrame) -> str:
    if "Volume" not in frame or float(frame["Volume"].tail(20).sum()) <= 0:
        return "N/D (sin volumen fiable en este activo)"
    recent, base = float(frame["Volume"].tail(3).mean()), float(frame["Volume"].tail(20).mean())
    if base <= 0:
        return "N/D"
    ratio = recent / base
    if ratio >= 1.15:
        return f"alto ({ratio:.1f}x la media): confirma el movimiento"
    if ratio <= 0.7:
        return f"bajo ({ratio:.1f}x la media): desmiente/debilita el movimiento"
    return f"normal ({ratio:.1f}x la media)"


def _format_hold(hours: float) -> str:
    lo, hi = max(1.0, hours * 0.6), max(2.0, hours * 1.6)
    if hi < 24:
        return f"{lo:.0f} – {hi:.0f} horas (aprox.)"
    return f"{lo / 24:.1f} – {hi / 24:.1f} días (aprox.)"


def _dist_to_zone(price: float, zone: dict) -> float:
    if zone["low"] <= price <= zone["high"]:
        return 0.0
    return min(abs(price - zone["low"]), abs(price - zone["high"]))


def _macro_bias(ms_1d: dict, ms_4h: dict) -> tuple[str | None, str, bool]:
    """Devuelve (sesgo, texto, contradictorio)."""
    t1, t4 = ms_1d["effective_trend"], ms_4h["effective_trend"]
    raw = {ms_1d["trend"], ms_4h["trend"]} - {"LATERAL"}
    if len(raw) == 2:
        return None, f"1D {ms_1d['trend']} vs 4H {ms_4h['trend']}: estructuras opuestas", True
    if t1 == "ALCISTA" and t4 == "ALCISTA":
        return "ALCISTA", "1D y 4H alcistas alineados", False
    if t1 == "BAJISTA" and t4 == "BAJISTA":
        return "BAJISTA", "1D y 4H bajistas alineados", False
    direction = next(iter(raw), None)
    if direction:
        bad = "bajista" if direction == "ALCISTA" else "alcista"
        for name, ms in (("1D", ms_1d), ("4H", ms_4h)):
            if ms["event"] and bad in ms["event"].lower() and ms["event_status"] == "CONFIRMADO":
                return None, f"{ms['event']} confirmado en {name} contra la estructura {direction.lower()}", True
        return direction, f"sesgo {direction.lower()} (1D {ms_1d['trend']}, 4H {ms_4h['trend']})", False
    return None, "1D y 4H laterales: sin tendencia definida", False


def evaluate_institutional(frames: dict[str, pd.DataFrame], news: dict | None = None, stale: bool = False,
                           risk_pct: float | None = None, min_rr: float | None = None,
                           min_confluence: int | None = None) -> dict:
    risk_pct = risk_pct or config.RISK_PER_TRADE_PCT
    min_rr = min_rr or config.MIN_RR
    min_confluence = min_confluence or config.MIN_CONFLUENCE
    news = {**NEUTRAL_NEWS, **(news or {})}
    for needed in ("1d", "4h", "1h"):
        if needed not in frames:
            raise ValueError(f"Falta la temporalidad {needed.upper()} para el análisis institucional")
    f1d, f4h, f1h, f15 = frames["1d"], frames["4h"], frames["1h"], frames.get("15m")
    price = float((f15 if f15 is not None else f1h)["Close"].iloc[-1])
    atr = float(f1h["ATR"].iloc[-1])
    atr4 = float(f4h["ATR"].iloc[-1])

    ms = {tf: smc.market_structure(frames[tf]) for tf in frames}
    bias, bias_text, contradictory = _macro_bias(ms["1d"], ms["4h"])
    pdz = smc.premium_discount(f1h)
    fvgs = smc.fair_value_gaps(f1h, atr)
    obs = smc.order_blocks(f1h, atr)
    sweeps = smc.liquidity_sweeps(f1h)

    extras = {"EMA 50 (1H)": _col(f1h, "EMA50"), "EMA 200 (1H)": _col(f1h, "EMA200"),
              "VWAP (1H)": smc.vwap(f1h), "EMA 200 (4H)": _col(f4h, "EMA200"),
              "EMA 200 (1D)": _col(f1d, "EMA200"), "EMA 50 (1D)": _col(f1d, "EMA50"),
              "máx. 4H": ms["4h"]["last_high"], "mín. 4H": ms["4h"]["last_low"],
              "máx. 1D": ms["1d"]["last_high"], "mín. 1D": ms["1d"]["last_low"]}
    if pdz:
        extras.update(smc.fib_levels(pdz["high"], pdz["low"]))
    sr = smc.support_resistance(f1h, price, atr, extras)

    candle = [{**p, "tf": "1H"} for p in detect_patterns(f1h) if p["bias"] != "NEUTRAL"]
    if f15 is not None:
        candle += [{**p, "tf": "15M"} for p in detect_patterns(f15) if p["bias"] != "NEUTRAL"]
    chart = [{**p, "tf": "1H"} for p in smc.chart_patterns(f1h, atr)] + \
            [{**p, "tf": "4H"} for p in smc.chart_patterns(f4h, atr4)]
    rsi, macd, macd_sig = _col(f1h, "RSI"), _col(f1h, "MACD"), _col(f1h, "MACD_SIGNAL")
    hist_now = _col(f1h, "MACD_HIST")
    hist_prev = float(f1h["MACD_HIST"].iloc[-3]) if "MACD_HIST" in f1h and len(f1h) > 3 else None
    rsi_prev = float(f1h["RSI"].iloc[-4]) if "RSI" in f1h and len(f1h) > 4 else None
    div_rsi, div_macd = smc.divergence(f1h, "RSI"), smc.divergence(f1h, "MACD_HIST")
    momentum = {"rsi": rsi, "macd": macd, "macd_signal": macd_sig, "macd_hist": hist_now,
                "div_rsi": div_rsi, "div_macd": div_macd, "volume": _volume_state(f1h)}

    reasons: list[str] = []
    result = {
        "price": price, "atr": atr, "ms": {tf: {k: v for k, v in m.items() if k != "swings"} for tf, m in ms.items()},
        "bias": bias, "bias_text": bias_text, "premium_discount": pdz, "fvg": fvgs[:3], "order_blocks": obs[:3],
        "sweeps": sweeps[:3], "sr": sr, "candle_patterns": candle, "chart_patterns": chart, "momentum": momentum,
        "news": news, "criteria": {}, "confluence": None, "decision": "NO TRADE", "ambiguous": False,
        "setup": None, "reasons": reasons, "stale": stale,
    }

    last30 = f4h.tail(30)
    narrow = float(last30["High"].max() - last30["Low"].min()) < 3 * atr4
    if contradictory:
        result["ambiguous"] = True
        reasons.append("Estructura contradictoria entre marcos temporales: " + bias_text + ".")
    elif bias is None:
        result["ambiguous"] = True
        reasons.append("Sin sesgo macro claro: " + bias_text + ".")
    if narrow:
        result["ambiguous"] = True
        reasons.append("Mercado lateral muy estrecho en 4H (rango de 30 velas < 3 ATR).")
    if news.get("high_impact_imminent") and abs(float(news.get("sentiment_score", 0))) < 0.3:
        result["ambiguous"] = True
        reasons.append("Noticia de alto impacto inminente sin dirección clara.")
    if stale:
        reasons.append("Datos posiblemente obsoletos: no se opera con información retrasada.")
        return result
    if bias is None or result["ambiguous"]:
        return result

    direction = "LONG" if bias == "ALCISTA" else "SHORT"
    long = direction == "LONG"
    result["direction"] = direction

    # Criterio 1 — S/R de alta confluencia
    c1_zone = None
    for z in sr["all"]:
        if z["strength"] < 2:
            continue
        right_side = z["price"] <= price + 0.3 * atr if long else z["price"] >= price - 0.3 * atr
        if right_side and _dist_to_zone(price, z) <= 0.6 * atr:
            if c1_zone is None or z["strength"] > c1_zone["strength"]:
                c1_zone = z
    c1 = c1_zone is not None
    # Criterio 2 — patrón a favor
    want = "BULLISH" if long else "BEARISH"
    c2_hits = [p for p in candle + chart if p["bias"] == want]
    c2 = bool(c2_hits)
    # Criterio 3 — momentum sin divergencia contraria
    if long:
        rsi_ok = rsi is not None and 40 <= rsi < 70 and (rsi_prev is None or rsi > rsi_prev)
        macd_ok = (macd is not None and macd_sig is not None and macd > macd_sig) or \
                  (hist_now is not None and hist_prev is not None and hist_now > hist_prev)
        contra = "BEARISH" in (div_rsi, div_macd)
        extreme = rsi is not None and rsi > 75
    else:
        rsi_ok = rsi is not None and 30 < rsi <= 60 and (rsi_prev is None or rsi < rsi_prev)
        macd_ok = (macd is not None and macd_sig is not None and macd < macd_sig) or \
                  (hist_now is not None and hist_prev is not None and hist_now < hist_prev)
        contra = "BULLISH" in (div_rsi, div_macd)
        extreme = rsi is not None and rsi < 25
    c3 = (rsi_ok or macd_ok) and not contra and not extreme
    # Criterio 4 — SMC
    side = "BULLISH" if long else "BEARISH"
    near = 1.0 * atr
    ob_hit = [z for z in obs if z["side"] == side and _dist_to_zone(price, z) <= near]
    fvg_hit = [z for z in fvgs if z["side"] == side and _dist_to_zone(price, z) <= near]
    sweep_hit = [s for s in sweeps if s["bias"] == side]
    zone_ok = pdz is None or (pdz["zone"] != "PREMIUM" if long else pdz["zone"] != "DESCUENTO")
    c4 = bool(ob_hit or fvg_hit or sweep_hit) and zone_ok
    # Criterio 5 — noticias
    score = float(news.get("sentiment_score", 0) or 0)
    c5 = score > -0.5 if long else score < 0.5

    result["criteria"] = {
        1: {"ok": c1, "text": "S/R de alta confluencia: " + (f"{c1_zone['price']:.5g} ({', '.join(c1_zone['labels'][:3])})" if c1 else "precio lejos de zonas fuertes")},
        2: {"ok": c2, "text": "patrón a favor: " + (", ".join(f"{p['name']} {p['tf']}" for p in c2_hits[:3]) if c2 else "ninguno")},
        3: {"ok": c3, "text": f"momentum RSI {(rsi or 0):.1f} / MACD " + ("confirma" if (rsi_ok or macd_ok) else "no confirma") + (" / divergencia contraria" if contra else "")},
        4: {"ok": c4, "text": "SMC: " + (", ".join(filter(None, ["OB" if ob_hit else "", "FVG" if fvg_hit else "", "barrido" if sweep_hit else ""])) or "sin OB/FVG/barrido cercano") + (f"; precio en {pdz['zone'].lower()}" if pdz else "")},
        5: {"ok": c5, "text": f"noticias {news['sentiment_label'].lower()} ({score:+.2f})"},
    }
    confluence = sum(1 for c in result["criteria"].values() if c["ok"])
    result["confluence"] = confluence
    if confluence < min_confluence:
        result["ambiguous"] = True
        reasons.append(f"Confluencia insuficiente ({confluence}/5; mínimo {min_confluence}).")
        return result

    # Entrada: OB / FVG / S/R alineado más cercano, si no un rango corto junto al precio.
    candidates = []
    for z in ob_hit:
        candidates.append(("order block", z["low"], z["high"]))
    for z in fvg_hit:
        candidates.append(("FVG", z["low"], z["high"]))
    if c1_zone:
        candidates.append(("zona S/R", c1_zone["low"] - 0.1 * atr, c1_zone["high"] + 0.1 * atr))
    candidates = [c for c in candidates if (c[2] <= price + 0.3 * atr if long else c[1] >= price - 0.3 * atr)]
    if candidates:
        kind, zlo, zhi = min(candidates, key=lambda c: _dist_to_zone(price, {"low": c[1], "high": c[2]}))
    else:
        kind = "precio actual"
        zlo, zhi = (price - 0.3 * atr, price) if long else (price, price + 0.3 * atr)
    entry = (zlo + zhi) / 2
    swing_ref = ms["1h"]["last_low"] if long else ms["1h"]["last_high"]
    base = zlo if long else zhi
    if swing_ref is not None and (swing_ref < zlo if long else swing_ref > zhi) and abs(base - swing_ref) <= 1.5 * atr:
        base = swing_ref
    sl = base - 0.3 * atr if long else base + 0.3 * atr
    risk = abs(entry - sl)
    if risk <= 0 or risk > 6 * atr:
        reasons.append("Stop inválido o demasiado lejano para el ATR 1H.")
        return result

    # Objetivos: siguientes S/R relevantes en la dirección del trade (alcance realista).
    max_dist = min(8 * atr, 10 * risk)

    def usable(level: float) -> bool:
        gap = (level - entry) if long else (entry - level)
        return 0.5 * risk < gap <= max_dist

    def pick(cands: list[tuple[float, str]]) -> list[tuple[float, str]]:
        chosen: list[tuple[float, str]] = []
        for lv in sorted((c for c in cands if usable(c[0])), key=lambda c: abs(c[0] - entry)):
            if not chosen or abs(lv[0] - chosen[-1][0]) > 0.5 * atr:
                chosen.append(lv)
        return chosen

    levels = [(z["price"], "/".join(z["labels"][:2])) for z in sr["all"]]
    if pdz:
        levels.append((pdz["high"] if long else pdz["low"], "extremo del rango 1H"))
    targets = pick(levels)
    if len(targets) < 2 and pdz:
        span = pdz["high"] - pdz["low"]
        for ratio, label in ((0.272, "extensión Fib 1.272"), (0.618, "extensión Fib 1.618")):
            levels.append((pdz["high"] + ratio * span, label) if long else (pdz["low"] - ratio * span, label))
        targets = pick(levels)
    if len(targets) < 2:
        reasons.append("No hay dos objetivos claros basados en soporte/resistencia relevante.")
        return result
    (tp1, tp1_src), (tp2, tp2_src) = targets[0], targets[1]
    rr1, rr2 = abs(tp1 - entry) / risk, abs(tp2 - entry) / risk
    if rr2 < min_rr:
        reasons.append(f"R:R insuficiente (TP2 1:{rr2:.1f} < 1:{min_rr:g}); operación descartada.")
        return result

    hours = max(1.0, (abs(tp2 - entry) / atr) ** 2)
    result["decision"] = direction
    result["setup"] = {
        "kind": kind, "entry_low": zlo, "entry_high": zhi, "entry": entry, "sl": sl,
        "tp1": tp1, "tp1_src": tp1_src, "tp2": tp2, "tp2_src": tp2_src, "rr1": rr1, "rr2": rr2,
        "risk_pct": risk_pct, "hold": _format_hold(hours),
        "profit_tp1_on_risk": rr1 * 100, "profit_tp2_on_risk": rr2 * 100,
        "profit_tp1_account": rr1 * risk_pct, "profit_tp2_account": rr2 * risk_pct,
    }
    reasons.append(f"{direction} a favor de {bias_text}; confluencia {confluence}/5; R:R TP2 1:{rr2:.1f}.")
    return result


# ───────────────────────── noticias ─────────────────────────
def parse_news_items(items: list, limit: int = 8, now: float | None = None) -> list[str]:
    """Normaliza titulares de yfinance (formato antiguo y nuevo), últimas 24 h si hay fecha."""
    import time
    from datetime import datetime
    now = now or time.time()
    out: list[str] = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        content = item.get("content") if isinstance(item.get("content"), dict) else item
        title = (content.get("title") or item.get("title") or "").strip()
        if not title:
            continue
        ts = item.get("providerPublishTime")
        if ts is None and content.get("pubDate"):
            try:
                ts = datetime.fromisoformat(str(content["pubDate"]).replace("Z", "+00:00")).timestamp()
            except ValueError:
                ts = None
        if ts is not None and now - float(ts) > 24 * 3600:
            continue
        summary = (content.get("summary") or "").strip()
        out.append(title + (f" — {summary[:160]}" if summary else ""))
        if len(out) >= limit:
            break
    return out


def fetch_headlines(ticker: str) -> list[str]:
    if not config.NEWS_ENABLED:
        return []
    try:
        import yfinance as yf
        return parse_news_items(yf.Ticker(ticker).news)
    except Exception as exc:  # noticias son opcionales
        log.info("Sin noticias para %s: %s", ticker, type(exc).__name__)
        return []


# ───────────────────────── orquestación ─────────────────────────
async def institutional_analysis(asset: str, ticker: str) -> dict:
    from .ai import analyze_news, narrate_analysis
    from .market import get_market_frame, market_snapshot

    async def load(tf: str, required: bool):
        try:
            return await asyncio.to_thread(get_market_frame, ticker, tf)
        except Exception as exc:
            if required:
                raise RuntimeError(f"No se pudo descargar {tf.upper()} de {asset}: {exc}") from exc
            log.info("Temporalidad opcional %s no disponible para %s", tf, asset)
            return None

    loaded = await asyncio.gather(load("1d", True), load("4h", True), load("1h", True), load("15m", False))
    frames = {tf: fr for tf, fr in zip(("1d", "4h", "1h", "15m"), loaded) if fr is not None}
    snap = await asyncio.to_thread(market_snapshot, ticker, "1h")
    headlines = await asyncio.to_thread(fetch_headlines, ticker)
    news = await analyze_news(asset, headlines)
    result = evaluate_institutional(frames, news, stale=snap["stale"])
    result.update({"asset": asset, "ticker": ticker, "last_candle_utc": snap["last_candle_utc"],
                   "age_minutes": snap["age_minutes"], "has_15m": "15m" in frames})
    result["narrative"] = await narrate_analysis(result)
    return result
