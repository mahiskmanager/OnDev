"""Diagnóstico básico de entorno y servicios."""
import asyncio
import platform
from . import config, groq_pool

async def diagnose(bot) -> dict:
    result = {"python": platform.python_version(), "platform": platform.platform(),
              "database": str(config.DATABASE_PATH), "telegram": "PENDIENTE",
              "groq": "DESACTIVADO" if not config.GROQ_ENABLED else "PENDIENTE"}
    try:
        me = await bot.get_me()
        result["telegram"] = f"OK (@{me.username or 'bot'})"
    except Exception as exc:
        result["telegram"] = f"ERROR: {type(exc).__name__}"
    if config.GROQ_ENABLED and config.GROQ_API_KEYS:
        try:
            status = await asyncio.to_thread(groq_pool.ping_all)
            ok = sum(1 for v in status.values() if v == "OK")
            result["groq"] = f"{ok}/{len(status)} claves OK (modelo {config.GROQ_MODEL})"
            for index, value in status.items():
                if value != "OK":
                    result[f"groq_clave_{index}"] = value
        except Exception as exc:
            result["groq"] = f"ERROR: {type(exc).__name__}"
    return result
