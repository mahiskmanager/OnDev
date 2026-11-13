# Changelog

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
