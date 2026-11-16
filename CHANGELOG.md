# Changelog

## 3.1.0 — Trader institucional (PROMPT COMPLETO)

- Nuevo `/analizar ACTIVO`: sesgo 1D+4H, ejecución 1H+15M, formato de salida del prompt para Telegram (HTML).
- Nuevo `smc.py`: swings, BOS/CHoCH, order blocks, FVG, barridos de liquidez, premium/descuento, Fibonacci, VWAP, S/R por confluencia, divergencias RSI/MACD y patrones chartistas.
- Nuevo `trader.py`: regla de confluencia ≥ 3/5, entrada en rango, SL estructural, TP1/TP2, R:R ≥ 1:2, tiempo y rentabilidad estimados, cláusula de abstención con la frase exacta.
- Noticias 24 h y sentimiento −1…1 (Groq) integrados como criterio 5.
- Rotación automática de hasta 7 claves Groq (`GROQ_API_KEY_1..7`) con salto de claves limitadas; `/health` comprueba cada clave.
- Modelo por defecto `llama-3.3-70b-versatile`; `TELEGRAM_CHAT_ID` (se mantiene `ADMIN_CHAT_ID` por compatibilidad y `GROQ_API_KEY` como clave extra).
- Temporalidades 4h (re-muestreo de 60m) y 1d; alias `BTCUSDT`/`EURUSD` en comandos.
- El motor CALL/PUT anterior pasa a `/rapido`. El asistente de configuración pide hasta 7 claves.
- Parámetros nuevos: `RISK_PER_TRADE_PCT`, `MIN_RR`, `MIN_CONFLUENCE`, `NEWS_ENABLED`, `GROQ_KEY_COOLDOWN`, `MAX_STALE_MINUTES_4H/1D`.
- Pruebas nuevas: rotación de claves, SMC, decisión del trader, formato Telegram y configuración.

## 3.0.0

- Nuevo backtesting OHLC con ejecución en la vela siguiente, costos y drawdown.
- Detección de patrones japoneses.
- Calculadora de tamaño de posición y exposición.
- Diagnóstico de Telegram y Groq.
- Indicadores MFI, OBV, Williams %R y Donchian.
- EMA 100 y clasificación simple de volatilidad.
- Reintentos de descarga y validación OHLC.
- Logs rotativos y acceso limitado al chat privado administrador.
- Documentación ampliada y pruebas unitarias nuevas.


## Adaptación InvestSmart / Groq
- Ampliado el catálogo de pares Forex.
- Reforzado el prompt de Groq para evaluar confluencias y contradicciones sin inventar datos.
- Groq no puede convertir `NO_OPERAR` en CALL/PUT ni presentar índices como probabilidades.
- Añadido `/investsmart` con protocolo de validación manual y advertencia específica OTC.
- Aclarado que Yahoo Finance es una referencia externa, no el feed garantizado de InvestSmart.
- Eliminada la actualización forzada de pip del instalador Termux para evitar romper el paquete administrado por `pkg`.
