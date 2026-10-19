"""PROXORA MCP server: forecasting and forecast scoring as MCP tools.

This module is only an adapter. All mathematics lives in the ``proxora``
engine (``python/src/proxora``); the tools here validate input, call the
engine and return plain JSON-able results, so any MCP client (Claude, other
models, scripts) can use the same predictor and the same scoring rules.

Tools
-----
score_forecast  one forecast vs the observed value: residual, square error,
                SPE, and the SVM-style epsilon-tube loss for a range.
score_batch     many forecasts: per-row scores plus MSPE / RMSPE / MAPE /
                hit rate, overall and per asset.
predict_next    next value of a series with ``lr`` (least squares) or ``qu``
                (variational quantum regressor), as a point plus a range.
backtest        walk-forward comparison of ``lr`` and ``qu`` on one series,
                scored with the same metrics, before trusting either.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from proxora import scoring
from proxora.forecast import backtest as engine_backtest
from proxora.forecast import predict_next as engine_predict_next

try:  # MCP Python SDK 2.x
    from mcp.server.mcpserver import MCPServer
except ImportError:  # MCP Python SDK 1.x
    from mcp.server.fastmcp import FastMCP as MCPServer


INSTRUCTIONS = """\
PROXORA predicts the next value of a series and scores forecasts.
Forecasts are a point plus a range [low, high]. Score them with SPE =
((actual - forecast) / actual)^2 and aggregate with MSPE / RMSPE, which are
comparable across assets of any price. A range works like an SVR epsilon tube:
misses inside it cost nothing. Compare 'lr' and 'qu' with backtest before
trusting either; no quantum advantage is assumed.
"""

server = MCPServer(name="proxora", instructions=INSTRUCTIONS)


class ForecastRecord(BaseModel):
    """One logged forecast and the value that was later observed."""

    actual: float = Field(description="Observed value at the forecast target time.")
    forecast: float = Field(description="The forecast point value.")
    low: float | None = Field(default=None, description="Lower edge of the forecast range.")
    high: float | None = Field(default=None, description="Upper edge of the forecast range.")
    asset: str | None = Field(default=None, description="Asset or lot label, e.g. 'TSLAB'.")


@server.tool()
def score_forecast(
    actual: float,
    forecast: float,
    low: float | None = None,
    high: float | None = None,
) -> dict:
    """Score one forecast against the observed value.

    Returns residual (actual - forecast), absolute and squared error, percentage
    error, SPE, and, when low/high are given, whether the actual landed in range
    and the epsilon-tube loss (distance outside the range, 0 inside it).
    """
    return scoring.score_forecast(actual, forecast, low, high).as_dict()


@server.tool()
def score_batch(records: list[ForecastRecord]) -> dict:
    """Score many forecasts at once.

    Returns per-row scores, an overall summary (MSPE, RMSPE, MAPE, hit rate,
    mean epsilon loss) and a per-asset summary that also includes MSE in the
    asset's own price units.
    """
    return scoring.score_batch(record.model_dump() for record in records)


@server.tool()
def predict_next(
    values: list[float],
    method: Literal["lr", "qu"] = "lr",
    confidence: float = 0.9,
    lags: int = 2,
    layers: int = 2,
    seed: int = 42,
    backend: Literal["numpy", "qiskit"] = "numpy",
    target: Literal["diff", "level"] = "diff",
) -> dict:
    """Predict the next value of an evenly spaced series (oldest first).

    method 'lr': least-squares line on the time index, with a classical
    prediction interval. method 'qu': variational quantum regressor (one qubit
    per lag, data re-uploading layers, <Z> readout); 'lags', 'layers', 'seed',
    'backend' and 'target' apply only to 'qu'. Returns value, low, high,
    confidence and model details.
    """
    options = {}
    if method == "qu":
        options = {"lags": lags, "layers": layers, "seed": seed, "backend": backend, "target": target}
    return engine_predict_next(values, method=method, confidence=confidence, **options).as_dict()


@server.tool()
def backtest(
    values: list[float],
    methods: list[Literal["lr", "qu"]] | None = None,
    min_train: int = 6,
    confidence: float = 0.9,
) -> dict:
    """Walk-forward test on one series: at each step, train on the past and
    predict the next value, then score it. Returns a summary (MSPE, RMSPE, hit
    rate, ...) and the scored steps for each method."""
    chosen = tuple(methods) if methods else ("lr", "qu")
    return engine_backtest(values, methods=chosen, min_train=min_train, confidence=confidence)


def main() -> None:
    """Run the server over stdio (the transport MCP clients launch locally)."""
    server.run()


if __name__ == "__main__":
    main()
