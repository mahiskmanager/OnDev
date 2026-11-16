"""Rotación automática entre varias API keys de Groq (round-robin + failover).

Cada petición usa la siguiente clave del anillo. Si una clave devuelve 429
(límite de tasa), 5xx o 401/403, se aparta temporalmente y la petición se
reintenta con la siguiente. Nunca se registran las claves, solo su posición.
"""
from __future__ import annotations

import logging
import threading
import time

import requests

from . import config

log = logging.getLogger(__name__)
CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
MODELS_URL = "https://api.groq.com/openai/v1/models"


class KeyRotator:
    def __init__(self, keys: list[str], cooldown: int = 60):
        self._keys = list(dict.fromkeys(k for k in keys if k))
        self._cooldown = max(1, cooldown)
        self._blocked_until: dict[int, float] = {}
        self._cursor = 0
        self._lock = threading.Lock()

    @property
    def size(self) -> int:
        return len(self._keys)

    def available(self) -> int:
        now = time.monotonic()
        with self._lock:
            return sum(1 for i in range(len(self._keys)) if self._blocked_until.get(i, 0) <= now)

    def next_key(self) -> tuple[int, str] | None:
        """Devuelve (posición, clave) siguiente del anillo, saltando las bloqueadas."""
        with self._lock:
            if not self._keys:
                return None
            now = time.monotonic()
            for _ in range(len(self._keys)):
                index = self._cursor % len(self._keys)
                self._cursor = (self._cursor + 1) % len(self._keys)
                if self._blocked_until.get(index, 0) <= now:
                    return index, self._keys[index]
            # Todas en enfriamiento: usa la que se libera antes.
            index = min(range(len(self._keys)), key=lambda i: self._blocked_until.get(i, 0))
            self._cursor = (index + 1) % len(self._keys)
            return index, self._keys[index]

    def block(self, index: int, seconds: float | None = None) -> None:
        with self._lock:
            self._blocked_until[index] = time.monotonic() + (seconds or self._cooldown)


rotator = KeyRotator(config.GROQ_API_KEYS, config.GROQ_KEY_COOLDOWN)


def _retry_after(response: requests.Response, default: float) -> float:
    try:
        return min(300.0, max(1.0, float(response.headers.get("retry-after", default))))
    except (TypeError, ValueError):
        return default


def chat_completion(payload: dict, pool: KeyRotator | None = None, timeout: int | None = None) -> str:
    """POST a /chat/completions rotando claves. Devuelve el contenido del mensaje."""
    pool = pool or rotator
    if pool.size == 0:
        raise RuntimeError("No hay GROQ_API_KEY_1..7 configuradas")
    timeout = timeout or config.GROQ_TIMEOUT
    last_error = "sin intentos"
    for _ in range(pool.size):
        picked = pool.next_key()
        if picked is None:
            break
        index, key = picked
        try:
            response = requests.post(
                CHAT_URL,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json=payload,
                timeout=timeout,
            )
        except requests.RequestException as exc:
            last_error = f"clave #{index + 1}: {type(exc).__name__}"
            pool.block(index, 15)
            log.warning("Groq %s; rotando a la siguiente clave", last_error)
            continue
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        last_error = f"clave #{index + 1}: HTTP {response.status_code}"
        if response.status_code == 429:
            pool.block(index, _retry_after(response, config.GROQ_KEY_COOLDOWN))
        elif response.status_code in {401, 403}:
            pool.block(index, 3600)
        elif response.status_code >= 500:
            pool.block(index, 10)
        else:
            # 400/404/422: error de la petición, otra clave no lo arregla.
            raise RuntimeError(f"Groq HTTP {response.status_code}: {response.text[:300]}")
        log.warning("Groq %s; rotando a la siguiente clave", last_error)
    raise RuntimeError(f"Todas las claves Groq fallaron ({last_error})")


def list_models_sync(pool: KeyRotator | None = None) -> list[str]:
    pool = pool or rotator
    picked = pool.next_key()
    if picked is None:
        raise RuntimeError("Configura GROQ_API_KEY_1..7 en .env")
    index, key = picked
    r = requests.get(MODELS_URL, headers={"Authorization": f"Bearer {key}"}, timeout=config.GROQ_TIMEOUT)
    r.raise_for_status()
    return sorted(x["id"] for x in r.json().get("data", []))


def ping_all(pool: KeyRotator | None = None) -> dict[int, str]:
    """Comprueba cada clave por separado (para /health)."""
    pool = pool or rotator
    out: dict[int, str] = {}
    for i, key in enumerate(pool._keys):
        try:
            r = requests.get(MODELS_URL, headers={"Authorization": f"Bearer {key}"}, timeout=10)
            out[i + 1] = "OK" if r.status_code == 200 else f"HTTP {r.status_code}"
        except requests.RequestException as exc:
            out[i + 1] = f"ERROR {type(exc).__name__}"
    return out
