"""
TOOLS — las "conexiones al mundo real" de los agentes.

Cada tool es una función Python normal. El modelo no ejecuta código: solo puede
PEDIR que ejecutemos una tool (con ciertos argumentos), nosotros la corremos y le
devolvemos el resultado. Eso es el "function calling".

Para que el modelo sepa qué tools existen, cada una se describe en TOOL_SCHEMAS
(formato estándar de function-calling). La descripción y los nombres de los
parámetros son lo que el modelo lee para decidir cuándo usarla — escríbelos claro.

Agregar una tool nueva = escribir la función + agregar su schema + registrarla en
TOOL_REGISTRY. Nada más.
"""

from __future__ import annotations

import json

import numpy as np
import yfinance as yf

from .config import load_config

# Días de trading al año, para anualizar retornos y volatilidad.
TRADING_DAYS = 252


# ─────────────────────────────────────────────────────────────────────
# Implementaciones de las tools
# ─────────────────────────────────────────────────────────────────────
def list_universe() -> str:
    """Devuelve la lista de tickers candidatos definida en config.yaml."""
    tickers = load_config()["universe"]["tickers"]
    return json.dumps({"universe": tickers, "count": len(tickers)})


def get_market_data(tickers: list[str], period: str = "1y") -> str:
    """
    Descarga datos de mercado en vivo desde Yahoo Finance para los tickers dados.

    Devuelve, por cada ticker: último precio, retorno total del período y nombre
    de la empresa (cuando está disponible).
    """
    if isinstance(tickers, str):
        tickers = [tickers]

    data = yf.download(
        tickers, period=period, progress=False, auto_adjust=True
    )["Close"]

    # yfinance devuelve una Serie (1 ticker) o un DataFrame (varios); unificamos.
    if hasattr(data, "to_frame") and data.ndim == 1:
        data = data.to_frame(name=tickers[0])

    result = {}
    for ticker in tickers:
        if ticker not in data.columns:
            result[ticker] = {"error": "sin datos"}
            continue
        prices = data[ticker].dropna()
        if len(prices) < 2:
            result[ticker] = {"error": "datos insuficientes"}
            continue
        total_return = float(prices.iloc[-1] / prices.iloc[0] - 1)
        result[ticker] = {
            "last_price": round(float(prices.iloc[-1]), 2),
            "total_return_pct": round(total_return * 100, 2),
        }
    return json.dumps(result)


def compute_metrics(tickers: list[str], period: str = "1y") -> str:
    """
    Calcula métricas cuantitativas para los tickers dados, usando datos en vivo.

    Por cada ticker: retorno anualizado (%), volatilidad anualizada (%) y ratio de
    Sharpe simple (retorno/volatilidad, tasa libre de riesgo = 0). Además entrega la
    correlación promedio de cada acción con el resto (señal de diversificación).
    """
    if isinstance(tickers, str):
        tickers = [tickers]

    data = yf.download(
        tickers, period=period, progress=False, auto_adjust=True
    )["Close"]

    if hasattr(data, "to_frame") and data.ndim == 1:
        data = data.to_frame(name=tickers[0])

    daily_returns = data.pct_change().dropna()

    metrics = {}
    for ticker in tickers:
        if ticker not in daily_returns.columns:
            metrics[ticker] = {"error": "sin datos"}
            continue
        r = daily_returns[ticker]
        ann_return = float(r.mean() * TRADING_DAYS)
        ann_vol = float(r.std() * np.sqrt(TRADING_DAYS))
        sharpe = float(ann_return / ann_vol) if ann_vol > 0 else 0.0
        metrics[ticker] = {
            "annual_return_pct": round(ann_return * 100, 2),
            "annual_volatility_pct": round(ann_vol * 100, 2),
            "sharpe_ratio": round(sharpe, 2),
        }

    # Correlación promedio de cada acción con las demás (excluye su propia diagonal).
    if daily_returns.shape[1] > 1:
        corr = daily_returns.corr()
        for ticker in corr.columns:
            others = corr[ticker].drop(labels=[ticker])
            if ticker in metrics and "error" not in metrics[ticker]:
                metrics[ticker]["avg_correlation"] = round(float(others.mean()), 2)

    return json.dumps(metrics)


# ─────────────────────────────────────────────────────────────────────
# Registro: nombre de tool -> función Python
# ─────────────────────────────────────────────────────────────────────
TOOL_REGISTRY = {
    "list_universe": list_universe,
    "get_market_data": get_market_data,
    "compute_metrics": compute_metrics,
}


# ─────────────────────────────────────────────────────────────────────
# Schemas: lo que el modelo "ve" de cada tool (function-calling)
# ─────────────────────────────────────────────────────────────────────
TOOL_SCHEMAS = {
    "list_universe": {
        "type": "function",
        "function": {
            "name": "list_universe",
            "description": (
                "Devuelve la lista de tickers candidatos (el universo de inversión) "
                "definida en la configuración. Úsala primero para saber con qué "
                "acciones puedes trabajar."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    "get_market_data": {
        "type": "function",
        "function": {
            "name": "get_market_data",
            "description": (
                "Descarga datos de mercado en vivo (último precio y retorno del "
                "período) desde Yahoo Finance para una lista de tickers."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "tickers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Lista de tickers, ej. ['AAPL', 'MSFT'].",
                    },
                    "period": {
                        "type": "string",
                        "description": "Ventana histórica (1mo, 3mo, 6mo, 1y, 2y, 5y).",
                    },
                },
                "required": ["tickers"],
            },
        },
    },
    "compute_metrics": {
        "type": "function",
        "function": {
            "name": "compute_metrics",
            "description": (
                "Calcula retorno anualizado, volatilidad, ratio de Sharpe y "
                "correlación promedio para una lista de tickers, con datos en vivo."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "tickers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Lista de tickers a analizar.",
                    },
                    "period": {
                        "type": "string",
                        "description": "Ventana histórica (1mo, 3mo, 6mo, 1y, 2y, 5y).",
                    },
                },
                "required": ["tickers"],
            },
        },
    },
}


def run_tool(name: str, arguments: dict) -> str:
    """Ejecuta una tool por nombre con los argumentos que pidió el modelo."""
    if name not in TOOL_REGISTRY:
        return json.dumps({"error": f"tool desconocida: {name}"})
    try:
        return TOOL_REGISTRY[name](**arguments)
    except Exception as exc:  # noqa: BLE001 - queremos devolver el error al modelo
        return json.dumps({"error": str(exc)})


def schemas_for(tool_names: list[str]) -> list[dict]:
    """Devuelve los schemas de las tools indicadas (las que un agente declaró usar)."""
    return [TOOL_SCHEMAS[name] for name in tool_names if name in TOOL_SCHEMAS]
