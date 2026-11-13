import asyncio
import json
import logging
import requests
from . import config

log = logging.getLogger(__name__)
URL = "https://api.groq.com/openai/v1/chat/completions"

async def explain_with_groq(snapshot: dict, technical: dict) -> str | None:
    """Segunda opinión de IA; nunca crea señales ni sustituye los filtros técnicos."""
    if not config.GROQ_ENABLED or not config.GROQ_API_KEY:
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
        response = requests.post(
            URL,
            headers={"Authorization": f"Bearer {config.GROQ_API_KEY}", "Content-Type": "application/json"},
            json=payload,
            timeout=config.GROQ_TIMEOUT
        )
        if response.status_code != 200:
            raise RuntimeError(f"Groq HTTP {response.status_code}: {response.text[:300]}")
        data = response.json()
        content = data["choices"][0]["message"]["content"]
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
    if not config.GROQ_API_KEY:
        raise RuntimeError("Configura GROQ_API_KEY en .env")

    def request():
        r = requests.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {config.GROQ_API_KEY}"},
            timeout=config.GROQ_TIMEOUT
        )
        r.raise_for_status()
        return sorted(x["id"] for x in r.json().get("data", []))

    return await asyncio.to_thread(request)
