"""Forecast scoring: how far was each prediction from what actually happened?

Every forecast is a point on the model's line; the observed value is the data
point. The vertical gap between them is the residual, and squaring it gives the
"error square" of least-squares regression.

Raw squared errors are in the asset's own price units, so a $369 stock and a
$0.0006 token cannot share one mean. The percentage form fixes that:

    SPE  = ((actual - forecast) / actual) ** 2      one forecast
    MSPE = mean(SPE)                                 many forecasts
    RMSPE = sqrt(MSPE)                               "typical miss", as a fraction

A forecast may also carry a range [low, high]. That range is an epsilon tube as
in support vector regression: a miss that lands inside the tube costs nothing,
and only the distance outside the tube is penalised (``epsilon_loss``).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import sqrt
from typing import Iterable


@dataclass(frozen=True)
class ForecastScore:
    """The score of one forecast against one observed value."""

    actual: float
    forecast: float
    residual: float
    absolute_error: float
    squared_error: float
    percentage_error: float | None
    spe: float | None
    low: float | None
    high: float | None
    in_range: bool | None
    epsilon_loss: float | None
    epsilon_loss_pct: float | None

    def as_dict(self) -> dict:
        return asdict(self)


def score_forecast(
    actual: float,
    forecast: float,
    low: float | None = None,
    high: float | None = None,
) -> ForecastScore:
    """Score one forecast.

    ``low`` and ``high`` must be given together or not at all. Percentage
    measures are ``None`` when ``actual`` is zero, because they divide by it.
    """
    if (low is None) != (high is None):
        raise ValueError("Give both low and high for a range, or neither.")
    if low is not None and high is not None and low > high:
        raise ValueError(f"Range low ({low}) is above high ({high}).")

    residual = actual - forecast
    percentage_error = residual / actual if actual != 0 else None
    spe = percentage_error**2 if percentage_error is not None else None

    in_range = epsilon_loss = epsilon_loss_pct = None
    if low is not None and high is not None:
        in_range = low <= actual <= high
        epsilon_loss = max(0.0, low - actual, actual - high)
        epsilon_loss_pct = abs(epsilon_loss / actual) if actual != 0 else None

    return ForecastScore(
        actual=actual,
        forecast=forecast,
        residual=residual,
        absolute_error=abs(residual),
        squared_error=residual**2,
        percentage_error=percentage_error,
        spe=spe,
        low=low,
        high=high,
        in_range=in_range,
        epsilon_loss=epsilon_loss,
        epsilon_loss_pct=epsilon_loss_pct,
    )


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def summarize(scores: Iterable[ForecastScore]) -> dict:
    """Aggregate scores. Native-unit MSE is only meaningful within one asset."""
    scores = list(scores)
    spes = [s.spe for s in scores if s.spe is not None]
    pcts = [abs(s.percentage_error) for s in scores if s.percentage_error is not None]
    ranged = [s for s in scores if s.in_range is not None]
    eps_pct = [s.epsilon_loss_pct for s in ranged if s.epsilon_loss_pct is not None]

    mspe = _mean(spes)
    return {
        "n": len(scores),
        "mse": _mean([s.squared_error for s in scores]),
        "mspe": mspe,
        "rmspe": sqrt(mspe) if mspe is not None else None,
        "mape": _mean(pcts),
        "ranged_n": len(ranged),
        "hit_rate": _mean([1.0 if s.in_range else 0.0 for s in ranged]),
        "mean_epsilon_loss_pct": _mean(eps_pct),
    }


def score_batch(records: Iterable[dict]) -> dict:
    """Score many forecasts at once.

    Each record needs ``actual`` and ``forecast``; ``asset``, ``low`` and
    ``high`` are optional. Returns per-row scores, an overall summary (whose
    ``mse`` mixes price units, so prefer ``mspe`` there) and a per-asset
    summary (where ``mse`` is meaningful).
    """
    rows = []
    by_asset: dict[str, list[ForecastScore]] = {}
    for record in records:
        score = score_forecast(
            float(record["actual"]),
            float(record["forecast"]),
            None if record.get("low") is None else float(record["low"]),
            None if record.get("high") is None else float(record["high"]),
        )
        asset = str(record.get("asset") or "?")
        rows.append({"asset": asset, **score.as_dict()})
        by_asset.setdefault(asset, []).append(score)

    all_scores = [s for group in by_asset.values() for s in group]
    overall = summarize(all_scores)
    overall.pop("mse")  # mixes price units across assets; not meaningful
    return {
        "rows": rows,
        "overall": overall,
        "by_asset": {asset: summarize(group) for asset, group in by_asset.items()},
    }
