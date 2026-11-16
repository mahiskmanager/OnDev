import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

def _bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "si", "sí"}

def _int(name: str, default: int, minimum: int = 1) -> int:
    try:
        return max(minimum, int(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default

def _float(name: str, default: float, minimum: float = 0.0) -> float:
    try:
        return max(minimum, float(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default

def _is_placeholder(value: str) -> bool:
    low = value.strip().lower()
    return low.startswith(("tu_", "clave_groq_", "pega_"))

def _groq_keys() -> list[str]:
    """Reúne GROQ_API_KEY_1..7 (y la clave legacy GROQ_API_KEY) sin duplicados."""
    keys: list[str] = []
    for index in range(1, 8):
        value = os.getenv(f"GROQ_API_KEY_{index}", "").strip()
        if value and not _is_placeholder(value) and value not in keys:
            keys.append(value)
    legacy = os.getenv("GROQ_API_KEY", "").strip()
    if legacy and not _is_placeholder(legacy) and legacy not in keys:
        keys.append(legacy)
    return keys

TOKEN = "" if _is_placeholder(os.getenv("TELEGRAM_BOT_TOKEN", "")) else os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
# TELEGRAM_CHAT_ID es el nombre oficial; ADMIN_CHAT_ID se conserva por compatibilidad.
ADMIN_CHAT_ID = (os.getenv("TELEGRAM_CHAT_ID") or os.getenv("ADMIN_CHAT_ID") or "").strip()
if _is_placeholder(ADMIN_CHAT_ID):
    ADMIN_CHAT_ID = ""
GROQ_API_KEYS = _groq_keys()
GROQ_API_KEY = GROQ_API_KEYS[0] if GROQ_API_KEYS else ""
GROQ_ENABLED = _bool("GROQ_ENABLED", bool(GROQ_API_KEYS))
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
GROQ_TIMEOUT = _int("GROQ_TIMEOUT", 35)
GROQ_KEY_COOLDOWN = _int("GROQ_KEY_COOLDOWN", 60)
# Parámetros del analista institucional
RISK_PER_TRADE_PCT = _float("RISK_PER_TRADE_PCT", 1.0, 0.1)
MIN_RR = _float("MIN_RR", 2.0, 1.0)
MIN_CONFLUENCE = _int("MIN_CONFLUENCE", 3, 1)
NEWS_ENABLED = _bool("NEWS_ENABLED", True)
TIMEZONE = os.getenv("TIMEZONE", "America/Guatemala")
DEFAULT_TIMEFRAME = os.getenv("DEFAULT_TIMEFRAME", "5m").lower()
CACHE_SECONDS = _int("CACHE_SECONDS", 25)
MARKET_TIMEOUT = _int("MARKET_TIMEOUT", 25)
MIN_CANDLES = _int("MIN_CANDLES", 80, 60)
AUTO_SCAN_ENABLED = _bool("AUTO_SCAN_ENABLED", False)
SCAN_INTERVAL_SECONDS = _int("SCAN_INTERVAL_SECONDS", 180, 30)
SCAN_MIN_CONFIDENCE = _int("SCAN_MIN_CONFIDENCE", 68, 1)
SCAN_COOLDOWN_SECONDS = _int("SCAN_COOLDOWN_SECONDS", 900, 60)
MULTI_TIMEFRAME_CONFIRMATION = _bool("MULTI_TIMEFRAME_CONFIRMATION", True)
MAX_SCAN_ALERTS = _int("MAX_SCAN_ALERTS", 3)
MIN_SCORE = _int("MIN_SCORE", 6, 1)
MIN_SCORE_GAP = _int("MIN_SCORE_GAP", 2, 1)
ATR_STOP_MULTIPLIER = _float("ATR_STOP_MULTIPLIER", 1.5, 0.1)
ATR_TARGET_MULTIPLIER = _float("ATR_TARGET_MULTIPLIER", 2.0, 0.1)
DATABASE_PATH = ROOT / os.getenv("DATABASE_PATH", "data/signals.sqlite3")
LOG_PATH = ROOT / os.getenv("LOG_PATH", "logs/bot.log")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

STALE_MINUTES = {
    "1m": _int("MAX_STALE_MINUTES_1M", 15),
    "5m": _int("MAX_STALE_MINUTES_5M", 30),
    "15m": _int("MAX_STALE_MINUTES_15M", 60),
    "1h": _int("MAX_STALE_MINUTES_1H", 180),
    "4h": _int("MAX_STALE_MINUTES_4H", 600),
    "1d": _int("MAX_STALE_MINUTES_1D", 4320),
}

ASSETS = {
    # === FOREX MAJORS ===
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "JPY=X",
    "USD/CHF": "CHF=X",
    "USD/CAD": "CAD=X",
    "AUD/USD": "AUDUSD=X",
    "NZD/USD": "NZDUSD=X",

    # === FOREX CROSSES ===
    "EUR/GBP": "EURGBP=X",
    "EUR/JPY": "EURJPY=X",
    "EUR/CHF": "EURCHF=X",
    "EUR/AUD": "EURAUD=X",
    "EUR/CAD": "EURCAD=X",
    "EUR/NZD": "EURNZD=X",
    "GBP/JPY": "GBPJPY=X",
    "GBP/CHF": "GBPCHF=X",
    "GBP/AUD": "GBPAUD=X",
    "GBP/CAD": "GBPCAD=X",
    "GBP/NZD": "GBPNZD=X",
    "AUD/JPY": "AUDJPY=X",
    "AUD/CHF": "AUDCHF=X",
    "AUD/CAD": "AUDCAD=X",
    "AUD/NZD": "AUDNZD=X",
    "CAD/JPY": "CADJPY=X",
    "CAD/CHF": "CADCHF=X",
    "NZD/JPY": "NZDJPY=X",
    "NZD/CHF": "NZDCHF=X",
    "NZD/CAD": "NZDCAD=X",
    "CHF/JPY": "CHFJPY=X",

    # === FOREX EXOTICS ===
    "USD/MXN": "MXN=X",
    "USD/TRY": "TRY=X",
    "USD/ZAR": "ZAR=X",
    "USD/SGD": "SGD=X",
    "USD/HKD": "HKD=X",
    "USD/SEK": "SEK=X",
    "USD/NOK": "NOK=X",
    "USD/PLN": "PLN=X",
    "EUR/TRY": "EURTRY=X",
    "GBP/TRY": "GBPTRY=X",

    # === METALS ===
    "XAU/USD": "GC=F",
    "XAG/USD": "SI=F",
    "XPT/USD": "PL=F",
    "XPD/USD": "PA=F",

    # === ENERGY / COMMODITIES ===
    "USOIL": "CL=F",
    "UKOIL": "BZ=F",
    "NATGAS": "NG=F",
    "COPPER": "HG=F",

    # === INDICES ===
    "SPX500": "^GSPC",
    "NASDAQ": "^IXIC",
    "US30": "^DJI",
    "US100": "^NDX",
    "GER40": "^GDAXI",
    "UK100": "^FTSE",
    "FRA40": "^FCHI",
    "JP225": "^N225",
    "AUS200": "^AXJO",
    "HK50": "^HSI",
    "EU50": "^STOXX50E",
    "ESP35": "^IBEX",

    # === CRYPTO (principales) ===
    "BTC/USD": "BTC-USD",
    "ETH/USD": "ETH-USD",
    "BNB/USD": "BNB-USD",
    "XRP/USD": "XRP-USD",
    "SOL/USD": "SOL-USD",
    "ADA/USD": "ADA-USD",
    "DOGE/USD": "DOGE-USD",
    "AVAX/USD": "AVAX-USD",
    "DOT/USD": "DOT-USD",
    "LINK/USD": "LINK-USD",
    "MATIC/USD": "MATIC-USD",
    "LTC/USD": "LTC-USD",
    "BCH/USD": "BCH-USD",
    "ATOM/USD": "ATOM-USD",
    "UNI/USD": "UNI-USD",
    "NEAR/USD": "NEAR-USD",
    "APT/USD": "APT-USD",
    "ARB/USD": "ARB-USD",
    "OP/USD": "OP-USD",
    "SUI/USD": "SUI-USD",
    "PEPE/USD": "PEPE-USD",
    "SHIB/USD": "SHIB-USD",
    "TRX/USD": "TRX-USD",
    "TON/USD": "TON-USD",
    "ICP/USD": "ICP-USD",
    "FIL/USD": "FIL-USD",
    "INJ/USD": "INJ-USD",
    "AAVE/USD": "AAVE-USD",
    "MKR/USD": "MKR-USD",
    "CRV/USD": "CRV-USD",

    # === ACCIONES POPULARES (CFD / Binary style) ===
    "AAPL": "AAPL",
    "TSLA": "TSLA",
    "AMZN": "AMZN",
    "NVDA": "NVDA",
    "MSFT": "MSFT",
    "GOOGL": "GOOGL",
    "META": "META",
    "NFLX": "NFLX",
    "AMD": "AMD",
    "INTC": "INTC",
    "BABA": "BABA",
    "JPM": "JPM",
    "BAC": "BAC",
    "V": "V",
    "MA": "MA",
    "DIS": "DIS",
    "PYPL": "PYPL",
    "COIN": "COIN",
    "PLTR": "PLTR",
    "UBER": "UBER",
}

# 4h no existe en Yahoo Finance: se descarga en 60m y se re-muestrea a 4 horas.
TIMEFRAMES = {"1m": "1m", "5m": "5m", "15m": "15m", "1h": "60m", "4h": "60m", "1d": "1d"}
# Jerarquía del analista institucional (el marco mayor manda).
MACRO_TIMEFRAMES = ("1d", "4h")
OPERATIVE_TIMEFRAMES = ("1h", "15m")

def validate_config():
    if not TOKEN:
        raise RuntimeError("Falta TELEGRAM_BOT_TOKEN en .env")
    if not ADMIN_CHAT_ID:
        raise RuntimeError("Falta TELEGRAM_CHAT_ID en .env")
    if GROQ_ENABLED and not GROQ_API_KEYS:
        raise RuntimeError("GROQ_ENABLED=true pero falta al menos una GROQ_API_KEY_1..7")
    if DEFAULT_TIMEFRAME not in TIMEFRAMES:
        raise RuntimeError(f"DEFAULT_TIMEFRAME inválido: {DEFAULT_TIMEFRAME}")


def _norm(text: str) -> str:
    return "".join(ch for ch in str(text).upper() if ch.isalnum())

def resolve_asset(text: str) -> str | None:
    """Acepta 'EUR/USD', 'EURUSD', 'BTCUSDT', 'btc-usd', 'AAPL' o un ticker de Yahoo."""
    wanted = _norm(text)
    if not wanted:
        return None
    candidates = [wanted]
    if wanted.endswith("USDT"):
        candidates.append(wanted[:-4] + "USD")
    for candidate in candidates:
        for name, ticker in ASSETS.items():
            if candidate == _norm(name) or candidate == _norm(ticker):
                return name
    return None
