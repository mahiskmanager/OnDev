# Trading AI Analyzer Pro 3.1

Bot de Telegram para análisis técnico informativo con un **trader institucional IA**: sesgo en 1D+4H, zona de entrada en 1H+15M, confluencia mínima 3/5, riesgo/beneficio ≥ 1:2 y rotación automática entre hasta **7 API keys de Groq**. No ejecuta órdenes ni conecta con brokers.

## Novedades 3.1 (según `PROMPT COMPLETO — TRADER AI ANALISTA PROFESIONAL`)

- `/analizar BTCUSDT` (también `EURUSD`, `EUR/USD`, `AAPL`, `ETHUSDT`…): análisis completo con el formato de salida del prompt (📊 🔍 📰 📈 ⚖️ 🎯 ⏱️ 📈 🧠 ⚠️).
- Jerarquía de marcos: **1D + 4H** definen el sesgo (la estructura mayor manda); **1H + 15M** buscan la zona de entrada.
- Estructura SMC: BOS/CHoCH confirmados o pendientes, order blocks, fair value gaps, barridos de liquidez y zona de descuento/premium.
- Soportes/resistencias por confluencia (swings, extremos, EMA 50/200, VWAP, Fibonacci), patrones de velas y chartistas (doble techo/suelo, hombro-cabeza-hombro, triángulos, cuñas, banderas), RSI/MACD con divergencias y volumen.
- **Regla de confluencia:** setup válido solo con ≥ 3 de 5 criterios; con menos, `NO TRADE`.
- **Gestión de riesgo:** entrada (rango), SL estructural, TP1/TP2 en el siguiente S/R, R:R ≥ 1:2 (si no, se descarta), riesgo por operación configurable (1 % por defecto), tiempo estimado y rentabilidad sobre el capital arriesgado.
- **Cláusula de abstención:** con estructura contradictoria, confluencia insuficiente, mercado lateral muy estrecho o noticia de alto impacto inminente sin dirección, el bot escribe exactamente: *Condiciones ambiguas. Me mantengo fuera del mercado y explico por qué.*
- Noticias de las últimas 24 h (Yahoo Finance) con sentimiento −1…1 calculado por Groq; el sentimiento alimenta el criterio 5.
- **7 claves Groq con rotación automática** (round-robin por petición, salto de claves con 429/401/5xx) y modelo `llama-3.3-70b-versatile`.
- El motor rápido anterior (CALL/PUT, escáner, backtest) se conserva: ahora es `/rapido EUR/USD 5m`.

## Funciones

- Análisis multi-activo y multi-temporalidad (1m, 5m, 15m, 1h, 4h, 1d; la 4h se construye re-muestreando 60m).
- Indicadores: EMA 9/21/50/100/200, RSI, MACD, Bollinger Bands, ATR, ADX, Stochastic RSI, CCI, ROC, MFI, OBV, Williams %R y Donchian.
- Motor determinista de estrategias: tendencia, momentum, volatilidad, estructura y confirmación.
- Confirmación opcional multi-timeframe.
- Groq para explicar el contexto; la IA no puede convertir una señal técnica neutral en una entrada.
- Escáner manual y automático.
- Alertas con niveles técnicos orientativos (entrada de referencia, stop y objetivo por ATR).
- Registro SQLite de señales y resultados WIN/LOSS/VOID.
- Reconocimiento de patrones de velas: doji, martillo, rechazo superior, envolventes e inside bar.
- Backtesting OHLC con entrada en vela siguiente, costos simulados, win rate, profit factor y drawdown.
- Calculadora de riesgo, tamaño teórico de posición y diagnóstico de Telegram/Groq.
- Reintentos de descarga, validación de velas y logs rotativos.
- Estadísticas, filtros, exportación CSV y comandos administrativos.
- Protección por chat ID, configuración fuera del repositorio y logs sin credenciales.

## Requisitos

- Python 3.10 o superior (recomendado Python 3.11+).
- Cuenta/bot de Telegram y API key de Groq.
- Conexión a internet.
- Yahoo Finance puede retrasar, limitar o no proporcionar determinados intervalos/activos. No es una fuente de ejecución ni garantiza datos en tiempo real.

## Instalación rápida en Termux

```bash
pkg update -y
pkg install python git -y
git clone https://github.com/TU_USUARIO/trading-ai-analyzer-pro.git
cd trading-ai-analyzer-pro
bash install.sh
python run.py
```

Durante `bash install.sh` aparecerá un asistente que solicitará el token del bot, el ID numérico de tu chat y hasta 7 API keys de Groq (la 1 es obligatoria; Enter para terminar). Las claves se escribirán de forma oculta en `.env`. Si ya instalaste el proyecto, ejecuta `python setup_config.py --edit` para cambiar credenciales. `python run.py` también abrirá el asistente automáticamente si falta la configuración básica.

## Configuración

La configuración se realiza automáticamente con el asistente. También puedes editar `.env` manualmente:

```env
# === BOT TELEGRAM ===
TELEGRAM_BOT_TOKEN=PEGA_TOKEN_NUEVO
TELEGRAM_CHAT_ID=TU_CHAT_ID

# === 7 LLAVES API GROQ — ROTACIÓN AUTOMÁTICA (basta con 1) ===
GROQ_API_KEY_1=clave_groq_1
GROQ_API_KEY_2=clave_groq_2
# ... hasta GROQ_API_KEY_7
GROQ_ENABLED=true
GROQ_MODEL=llama-3.3-70b-versatile

# === ANALISTA INSTITUCIONAL ===
RISK_PER_TRADE_PCT=1.0
MIN_RR=2.0
MIN_CONFLUENCE=3
NEWS_ENABLED=true

MARKET_PROVIDER=yfinance
DEFAULT_TIMEFRAME=5m
SCAN_INTERVAL_SECONDS=180
SCAN_MIN_CONFIDENCE=68
SCAN_COOLDOWN_SECONDS=900
AUTO_SCAN_ENABLED=false
MULTI_TIMEFRAME_CONFIRMATION=true
TIMEZONE=America/Guatemala
```

No subas `.env`, `data/`, ni `logs/` a GitHub. El archivo `.env.example` no contiene secretos.

**Seguridad:** si el token de Telegram se publicó en logs, revócalo en @BotFather y crea uno nuevo. Nunca pegues tokens en issues, capturas ni commits.

## Comandos Telegram

- `/start` — ayuda.
- `/status` — estado y configuración no sensible.
- `/analizar BTCUSDT` — análisis institucional completo (1D+4H → 1H+15M, confluencia 3/5, SL/TP, R:R, noticias).
- `/rapido EUR/USD 5m` — motor técnico rápido CALL/PUT (temporalidades 1m, 5m, 15m, 1h, 4h, 1d).
- `/scan` — escaneo inmediato de todos los activos configurados.
- `/auto_on` — activar escaneo automático.
- `/auto_off` — detener escaneo automático.
- `/activos` — activos admitidos.
- `/timeframes` — temporalidades admitidas.
- `/senales` — últimas señales guardadas.
- `/stats` — estadísticas globales.
- `/stats_hoy` — estadísticas del día local.
- `/riesgo` — explicación de gestión de riesgo.
- `/calcriesgo 1000 1 1.0850 1.0800` — calcula exposición teórica.
- `/patrones EUR/USD 5m` — patrones en la última vela.
- `/backtest EUR/USD 5m 1000` — simulación histórica.
- `/health` — diagnóstico de Telegram y de cada clave Groq.
- `/exportar` — exportar historial CSV.
- `/modelos` — consultar modelos Groq disponibles (si está configurado).

Para analizar un activo se aceptan alias (`EUR/USD`, `EURUSD`, `BTC/USD`, `BTCUSDT`, `XAU/USD`) o ticker Yahoo incluido en la lista blanca (108 activos).

## Estrategia y límites

**Analista institucional (`/analizar`).** Las reglas (sesgo, confluencia, SL/TP, R:R, abstención) las decide un motor determinista en Python; Groq solo resume noticias, puntúa su sentimiento y redacta la explicación, y no puede convertir un `NO TRADE` en operación. Límites que conviene conocer:

- Order blocks, FVG, BOS/CHoCH y patrones chartistas son **detecciones programáticas con reglas explícitas**; pueden diferir de lo que marcaría un trader a ojo.
- El R:R mínimo (1:2) se evalúa contra **TP2**; TP1 y TP2 son los siguientes niveles de S/R con alcance realista (≤ 8 ATR de 1H).
- *Tiempo estimado* y *rentabilidad esperada* son **estimaciones**: el tiempo sale de la distancia a TP2 en unidades de ATR 1H; la rentabilidad es el múltiplo R:R sobre el capital arriesgado (p. ej. R:R 1:2,5 → +250 % del riesgo ≈ +2,5 % de la cuenta si arriesgas 1 %). No son probabilidades ni promesas.
- Las noticias vienen de Yahoo Finance y suelen faltar en forex; sin titulares el sentimiento es neutral (0) y el bot lo indica. El bot **no tiene calendario económico**: los eventos macro solo se mencionan si aparecen en los titulares, así que revisa uno antes de operar.
- Volumen: en forex e índices Yahoo no lo ofrece de forma fiable; en esos casos se marca `N/D`.
- Con datos retrasados (vela vieja) no se opera.

El motor combina puntuaciones técnicas; los porcentajes mostrados son **índices heurísticos de confluencia, no probabilidades de ganar**. Una señal requiere consenso mínimo y filtros de calidad. Los niveles ATR son referencias educativas, no órdenes ni recomendaciones.

Las velas más recientes pueden estar incompletas. Los intervalos intradía de Yahoo tienen límites de historial y disponibilidad. El bot marca la hora de la última vela y evita afirmar que una cotización es "tiempo real".

El resultado WIN/LOSS se introduce manualmente. Para una evaluación real se necesita un sistema de resolución por precio y vencimiento, incluyendo spread, comisiones y deslizamiento. Las estadísticas manuales no son backtesting.

## Pruebas

```bash
python -m unittest discover -s tests -v
```

Las pruebas unitarias no requieren credenciales ni conexión a mercado. La prueba de importación completa se omite automáticamente si aún no están instaladas las dependencias de `requirements.txt`.

## Documentación adicional

- `docs/ARQUITECTURA.md` — módulos y flujo de datos.
- `docs/ESTRATEGIA_Y_VALIDACION.md` — indicadores, backtesting y protocolo de validación.
- `docs/TERMUX.md` — instalación y mantenimiento en Android.
- `CHANGELOG.md` — cambios de la versión.

## Estructura

```text
trading-ai-analyzer-pro/
├── trading_bot/
│   ├── config.py
│   ├── indicators.py
│   ├── market.py
│   ├── strategies.py
│   ├── patterns.py
│   ├── risk.py
│   ├── backtest.py
│   ├── diagnostics.py
│   ├── ai.py
│   ├── groq_pool.py        # rotación de 7 claves Groq
│   ├── prompts.py          # prompt del trader institucional
│   ├── smc.py              # estructura, SMC, S/R, patrones chartistas
│   ├── trader.py           # confluencia 3/5, setup, R:R, abstención
│   ├── storage.py
│   ├── analyzer.py
│   ├── scanner.py
│   ├── formatting.py
│   └── handlers.py
├── tests/
├── docs/
├── data/
├── logs/
├── .env.example
├── .gitignore
├── install.sh
├── run.py
├── setup_config.py
└── requirements.txt
```

## Aviso

Software informativo y educativo. No ofrece asesoramiento financiero, no garantiza resultados y no ejecuta operaciones. Verifica datos y realiza pruebas históricas/forward-test antes de tomar decisiones.


## Perfil de análisis para InvestSmart

Esta versión mantiene el bot de Telegram y utiliza Groq (con rotación de claves) como segunda opinión sobre el análisis técnico. Incluye pares Forex adicionales (USD/CHF, USD/CAD, AUD/USD, NZD/USD, EUR/GBP, EUR/JPY, GBP/JPY, AUD/JPY, EUR/CHF y GBP/CHF) y el comando `/investsmart` con un procedimiento para validar manualmente cada activo en la plataforma.

**Límite de datos importante:** el proveedor incluido es Yahoo Finance. Sus símbolos y cotizaciones son referencias externas y no representan necesariamente el feed de InvestSmart, especialmente en instrumentos OTC. La IA no consulta la cuenta ni la API privada de InvestSmart, no conoce su payout/spread/vencimientos y no ejecuta órdenes. Si el precio o la vela no coinciden, no se debe operar con esa señal.

Groq recibe el snapshot técnico real obtenido por el proveedor y debe explicar confluencias, contradicciones y condiciones de confirmación. No puede cambiar una decisión `NO_OPERAR` por una entrada. La puntuación es un índice heurístico, nunca una probabilidad de ganar. No existe garantía de operaciones ganadoras.

Comandos añadidos: `/investsmart` para la guía de validación. Usa `/activos` para consultar el catálogo, `/analizar EUR/USD` para el análisis institucional y `/rapido EUR/USD 5m` para el motor rápido.
