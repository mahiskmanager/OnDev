import asyncio
import json
import logging
from . import config, groq_pool
from .prompts import TRADER_PROMPT, DATA_RULES, NEWS_TASK, NARRATIVE_TASK

log = logging.getLogger(__name__)

async def explain_with_groq(snapshot: dict, technical: dict) -> str | None:
    """Segunda opinión de IA; nunca crea señales ni sustituye los filtros técnicos."""
    if not config.GROQ_ENABLED or not config.GROQ_API_KEYS:
        return None

    system = (
        "Eres un analista cuantitativo especializado en Forex y trading de corto plazo, "
        "incluyendo plataformas de opciones digitales como InvestSmart. Analizas "
        "EXCLUSIVAMENTE los datos incluidos en el mensaje. No tienes acceso directo "
        "a InvestSmart, a su libro de precios, a sus activos OTC ni a noticias en vivo. "
        "No inventes cotizaciones, spreads, noticias, payout, horarios, probabilidades "
        "ni confirmaciones. La fuente y antigüedad de los datos deben respetarse. "
        "La decisión del motor técnico es inmutable: jamás conviertas NO_OPERAR en CALL/PUT. "
        "Si hay datos obsoletos, contradicciones, RSI extremo, ADX débil, cercanía a soporte/"
        "resistencia o falta de confirmación multi-temporal, recomienda NO_OPERAR. "
        "No prometas operaciones ganadoras ni uses porcentajes de acierto inventados. "
        "Para CALL/PUT solo describe una configuración candidata y qué confirmación esperar "
        "en la plataforma antes de entrar. Si el instrumento de InvestSmart es OTC, "
        "advierte que los datos externos pueden no representar ese precio OTC. "
        "Responde en español, claro y conciso, máximo 170 palabras."
    )
    user = {
        "market_snapshot": snapshot,
        "deterministic_engine": technical,
        "task": (
            "Evalúa coherencia de tendencia, momentum, volatilidad, estructura y niveles. "
            "Devuelve: veredicto (mantener decisión técnica o NO_OPERAR si hay riesgo de datos), "
            "confluencias, contradicciones, condición exacta que debe confirmarse en InvestSmart, "
            "y riesgo principal. No inventes hora de entrada ni vencimiento; el timeframe no "
            "garantiza que ese sea el vencimiento disponible."
        )
    }
    payload = {
        "model": config.GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system + ' Devuelve JSON con una única clave "explanation".'},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False, allow_nan=False)}
        ],
        "temperature": 0.1,
        "max_completion_tokens": 650,
        "response_format": {"type": "json_object"}
    }

    def request():
        content = groq_pool.chat_completion(payload)
        parsed = json.loads(content)
        explanation = parsed.get("explanation", "")
        if not isinstance(explanation, str):
            raise ValueError("Groq devolvió explanation con formato inválido")
        return explanation[:2200].strip() or None

    try:
        return await asyncio.to_thread(request)
    except Exception as exc:
        log.warning("Groq no disponible; se conserva análisis técnico: %s", exc)
        return None

async def list_models() -> list[str]:
    if not config.GROQ_API_KEYS:
        raise RuntimeError("Configura GROQ_API_KEY_1..7 en .env")
    return await asyncio.to_thread(groq_pool.list_models_sync)


async def _json_call(user_payload: dict, task: str, max_tokens: int = 500) -> dict | None:
    """Llamada JSON al analista institucional (rotando las claves Groq)."""
    if not config.GROQ_ENABLED or not config.GROQ_API_KEYS:
        return None
    payload = {
        "model": config.GROQ_MODEL,
        "messages": [
            {"role": "system", "content": TRADER_PROMPT + "\n\n" + DATA_RULES + "\n\n" + task},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, allow_nan=False, default=str)},
        ],
        "temperature": 0.1,
        "max_completion_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }

    def request():
        return json.loads(groq_pool.chat_completion(payload))

    try:
        parsed = await asyncio.to_thread(request)
        return parsed if isinstance(parsed, dict) else None
    except Exception as exc:
        log.warning("Groq no disponible para el analista institucional: %s", exc)
        return None


async def analyze_news(asset: str, headlines: list[str]) -> dict:
    """Resumen y sentimiento (-1..1) de titulares; neutral si no hay datos o Groq falla."""
    from .trader import NEUTRAL_NEWS
    if not headlines:
        return dict(NEUTRAL_NEWS)
    parsed = await _json_call({"asset": asset, "headlines_last_24h": headlines}, NEWS_TASK)
    if not parsed:
        out = dict(NEUTRAL_NEWS)
        out["news_summary"] = "Titulares recibidos pero sin análisis de IA disponible: " + "; ".join(h[:90] for h in headlines[:2])
        return out
    try:
        score = max(-1.0, min(1.0, float(parsed.get("sentiment_score", 0))))
    except (TypeError, ValueError):
        score = 0.0
    label = str(parsed.get("sentiment_label", "Neutral")).strip().capitalize()
    if label not in {"Positivo", "Negativo", "Neutral"}:
        label = "Positivo" if score > 0.15 else ("Negativo" if score < -0.15 else "Neutral")
    return {
        "news_summary": str(parsed.get("news_summary") or NEUTRAL_NEWS["news_summary"])[:500],
        "sentiment_label": label, "sentiment_score": score,
        "macro_events": (str(parsed["macro_events"])[:300] if parsed.get("macro_events") else None),
        "high_impact_imminent": bool(parsed.get("high_impact_imminent", False)), "available": True,
    }


async def narrate_analysis(result: dict) -> dict | None:
    """Contexto macro, razonamiento y aviso de riesgo redactados por Groq (opcional)."""
    s = result.get("setup")
    brief = {
        "asset": result.get("asset"), "decision": result["decision"], "ambiguous": result["ambiguous"],
        "bias": result["bias"], "bias_text": result["bias_text"], "confluence": result["confluence"],
        "criteria": {k: v for k, v in result["criteria"].items()}, "reasons": result["reasons"],
        "structure": {tf: {"trend": m["trend"], "event": m["event"], "status": m["event_status"]} for tf, m in result["ms"].items()},
        "premium_discount": (result["premium_discount"] or {}).get("zone"),
        "momentum": result["momentum"], "news": {k: result["news"].get(k) for k in ("sentiment_label", "sentiment_score", "macro_events")},
        "setup": {k: s[k] for k in ("entry", "sl", "tp1", "tp2", "rr1", "rr2")} if s else None,
    }
    parsed = await _json_call(brief, NARRATIVE_TASK, 450)
    if not parsed:
        return None
    return {k: str(parsed.get(k) or "")[:600] for k in ("macro_context", "reasoning", "risk_notice")}
