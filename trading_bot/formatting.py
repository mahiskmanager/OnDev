import html
from datetime import datetime
from zoneinfo import ZoneInfo
from . import config

def fmt_price(value):
    if value is None:
        return "N/A"
    value = float(value)
    if abs(value) >= 1000:
        return f"{value:,.2f}"
    if abs(value) >= 1:
        return f"{value:.5f}".rstrip("0").rstrip(".")
    return f"{value:.8f}".rstrip("0").rstrip(".")

def analysis_message(result):
    s = result["snapshot"]
    a = result["technical"]
    direction = a["direction"]
    icon = {"CALL": "🟢", "PUT": "🔴", "NO_OPERAR": "⚪"}.get(direction, "⚪")
    reasons = "\n".join(f"• {x}" for x in a.get("reasons", [])[:8]) or "• Sin confirmaciones"
    confirm = result.get("confirmations") or {}
    confirm_text = "\n".join(
        f"• {tf}: {v.get('direction', 'ERROR')}"
        for tf, v in confirm.items()
    ) or "No solicitada"
    age = s["age_minutes"]
    stale_label = "⚠️ POSIBLEMENTE RETRASADO" if s["stale"] else "Edad de vela verificada"
    msg = f"""
📊 TRADING AI ANALYZER PRO
━━━━━━━━━━━━━━━━━━
Activo: {result['asset']}
Temporalidad: {result['timeframe']}
Fuente: {s['source']}
Última vela UTC: {s['last_candle_utc']}
Edad de vela: {age:.1f} min — {stale_label}

💰 Precio de referencia: {fmt_price(s['price'])}
Cambio vela: {s['change_pct']:.3f}%

📈 INDICADORES
RSI(14): {s['rsi']:.2f}
MACD: {s['macd']:.6f}
MACD señal: {s['macd_signal']:.6f}
EMA 9 / 21 / 50 / 100: {fmt_price(s['ema9'])} / {fmt_price(s['ema21'])} / {fmt_price(s['ema50'])} / {fmt_price(s.get('ema100'))}
ADX(14): {s['adx']:.2f}
MFI(14): {s.get('mfi', 50):.2f}
Williams %R: {s.get('williams_r', 0):.2f}
ATR(14): {fmt_price(s['atr'])}
CCI: {s['cci']:.1f}
Stoch RSI K/D: {s['stoch_k']:.2f}/{s['stoch_d']:.2f}
Bollinger superior/inferior: {fmt_price(s['bb_high'])} / {fmt_price(s['bb_low'])}

📍 Rango reciente
Soporte: {fmt_price(s['support'])}
Resistencia: {fmt_price(s['resistance'])}

━━━━━━━━━━━━━━━━━━
{icon} DECISIÓN TÉCNICA: {direction}
Índice de confluencia: {a['confidence']}/100
Puntuación CALL/PUT: {a['bull_score']}/{a['bear_score']}
Riesgo cualitativo: {a['risk']}

Entrada de referencia: {fmt_price(a.get('entry'))}
Stop técnico orientativo: {fmt_price(a.get('stop'))}
Objetivo técnico orientativo: {fmt_price(a.get('target'))}

Confirmación multi-temporal:
{confirm_text}

Fundamentos:
{reasons}
"""
    if result.get("explanation"):
        msg += "\n🧠 EXPLICACIÓN IA\n" + result["explanation"] + "\n"
    msg += (
        "\n⚠️ INFORMATIVO, NO GARANTÍA: no existe señal segura ni operación garantizada. "
        "La puntuación NO es probabilidad de éxito. Yahoo Finance puede retrasar datos "
        "y no replica necesariamente los precios OTC de InvestSmart. Compara el precio "
        "y la vela con InvestSmart antes de considerar cualquier entrada; si no coinciden, NO OPERAR."
    )
    return msg[:3900]

def signal_keyboard(signal_id):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🟢 WIN", callback_data=f"RESULT:WIN:{signal_id}"),
        InlineKeyboardButton("🔴 LOSS", callback_data=f"RESULT:LOSS:{signal_id}"),
        InlineKeyboardButton("⚪ VOID", callback_data=f"RESULT:VOID:{signal_id}")
    ]])


# ───────────────────────── analista institucional (formato Telegram) ─────────────────────────
def _zones_text(zones):
    if not zones:
        return "N/D"
    return "; ".join(f"{fmt_price(z['price'])} ({', '.join(z['labels'][:2])}, x{z['strength']})" for z in zones[:2])


def _cut(text: str, limit: int = 4000) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit("\n", 1)[0]
    return cut + "\n…"


def trader_message(r: dict) -> str:
    """Mensaje HTML para Telegram con el formato del analista profesional."""
    from .trader import AMBIGUOUS_PHRASE
    e = html.escape
    narr = r.get("narrative") or {}
    news = r["news"]
    ms = r["ms"]
    sr = r["sr"]
    mom = r["momentum"]
    pdz = r.get("premium_discount")
    setup = r.get("setup")
    ev = lambda m: f"{m['trend']}" + (f" · {m['event']} {m['event_status'].lower()}" if m.get("event") else "")

    macro_default = f"{r['bias_text']}. 1D {ev(ms['1d'])}; 4H {ev(ms['4h'])}."
    patterns = [f"{p['name']} {p['tf']} ({p['bias'].lower()})" for p in (r["candle_patterns"] + r["chart_patterns"])[:3]]
    div = [d for d in (("RSI " + mom["div_rsi"].lower()) if mom["div_rsi"] else None,
                       ("MACD " + mom["div_macd"].lower()) if mom["div_macd"] else None) if d]
    smc_bits = []
    if r["order_blocks"]:
        z = r["order_blocks"][0]
        smc_bits.append(f"OB {z['side'].lower()} {fmt_price(z['low'])}-{fmt_price(z['high'])}")
    if r["fvg"]:
        z = r["fvg"][0]
        smc_bits.append(f"FVG {z['side'].lower()} {fmt_price(z['low'])}-{fmt_price(z['high'])}")
    if r["sweeps"]:
        smc_bits.append("barrido " + ("de mínimos" if r["sweeps"][0]["side"] == "LOW" else "de máximos"))
    if pdz:
        smc_bits.append(f"zona {pdz['zone'].lower()}")

    lines = [
        f"📊 <b>{e(r['asset'])}</b> · 1D/4H → 1H{'/15M' if r.get('has_15m') else ''} · precio {fmt_price(r['price'])}",
        f"🔍 <b>Contexto macro:</b> {e((narr.get('macro_context') or macro_default)[:400])}",
        f"📰 <b>Noticias y macro:</b> {e(news['news_summary'][:500])} Sentimiento: <b>{e(news['sentiment_label'])}</b> ({news['sentiment_score']:+.2f}). "
        + e(news.get("macro_events") or "Sin eventos macro confirmados en los datos; revisa el calendario económico antes de operar."),
        "📈 <b>Análisis técnico:</b>",
        f"• Soportes: {e(_zones_text(sr['supports']))}",
        f"• Resistencias: {e(_zones_text(sr['resistances']))}",
        "• Zona más fuerte: " + (e(f"{fmt_price(sr['strongest']['price'])} ({', '.join(sr['strongest']['labels'][:3])})") if sr["strongest"] else "N/D"),
        "• Patrones: " + e(", ".join(patterns) if patterns else "sin patrón vigente"),
        f"• RSI {mom['rsi']:.1f} · MACD hist {mom['macd_hist']:+.5f}" + (" · divergencia " + e(", ".join(div)) if div else "") + f" · volumen {e(mom['volume'])}",
        "• SMC: " + e(", ".join(smc_bits) if smc_bits else "sin OB/FVG/barrido relevante"),
    ]
    if r["confluence"] is None:
        lines.append("⚖️ <b>Confluencia:</b> N/A (sin sesgo macro utilizable)")
    else:
        marks = " ".join(("✅" if r["criteria"][i]["ok"] else "❌") + str(i) for i in range(1, 6))
        lines.append(f"⚖️ <b>Confluencia:</b> {r['confluence']}/5 · {marks}")
        lines += [f"  {i}. {'✅' if r['criteria'][i]['ok'] else '❌'} {e(r['criteria'][i]['text'])}" for i in range(1, 6)]

    if setup:
        lines += [
            f"🎯 <b>Setup: {r['decision']}</b> | Entrada: {fmt_price(setup['entry_low'])} – {fmt_price(setup['entry_high'])} ({e(setup['kind'])}) | "
            f"SL: {fmt_price(setup['sl'])} | TP1: {fmt_price(setup['tp1'])} | TP2: {fmt_price(setup['tp2'])} | "
            f"R:R: 1:{setup['rr1']:.1f} / 1:{setup['rr2']:.1f}",
            f"⏱️ <b>Tiempo estimado:</b> {e(setup['hold'])}",
            f"📈 <b>Rentabilidad esperada:</b> TP1 ≈ +{setup['profit_tp1_on_risk']:.0f}% / TP2 ≈ +{setup['profit_tp2_on_risk']:.0f}% sobre el capital arriesgado "
            f"(≈ +{setup['profit_tp1_account']:.1f}% / +{setup['profit_tp2_account']:.1f}% de la cuenta arriesgando {setup['risk_pct']:g}%)",
        ]
    else:
        lines += ["🎯 <b>Setup: NO TRADE</b>", "⏱️ <b>Tiempo estimado:</b> N/A (sin operación)", "📈 <b>Rentabilidad esperada:</b> N/A (sin operación)"]
        if r["ambiguous"]:
            lines.append("&gt; " + e(AMBIGUOUS_PHRASE))

    reasoning = narr.get("reasoning") or " ".join(r["reasons"]) or "Sin setup válido."
    if r["ambiguous"] and not setup and narr.get("reasoning") and r["reasons"]:
        reasoning = " ".join(r["reasons"]) + " " + narr["reasoning"]
    lines.append(f"🧠 <b>Razonamiento:</b> {e(reasoning[:700])}")
    risk = narr.get("risk_notice") or "Reduce el tamaño si hay noticias de alto impacto y espera confirmación en velas cerradas."
    stale = " ⚠️ Datos posiblemente retrasados." if r.get("stale") else ""
    lines.append(f"⚠️ <b>Aviso de riesgo:</b> {e(risk[:400])}{stale} Análisis informativo (Yahoo Finance), no asesoría financiera ni garantía de resultado.")
    return _cut("\n".join(lines))
