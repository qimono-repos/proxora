"""Next-value prediction: one task, classical (``lr``) or quantum (``qu``)."""

from __future__ import annotations

from proxora.forecast.linear import predict_next_linear
from proxora.forecast.quantum import predict_next_quantum
from proxora.forecast.types import Prediction
from proxora.scoring import score_forecast, summarize

METHODS = ("lr", "qu")


def predict_next(values: list[float], method: str = "lr", confidence: float = 0.9, **options) -> Prediction:
    """Predict the next value of ``values`` with the chosen method."""
    if method == "lr":
        return predict_next_linear(values, confidence=confidence)
    if method == "qu":
        return predict_next_quantum(values, confidence=confidence, **options)
    raise ValueError(f"Unknown method {method!r}; use one of {METHODS}.")


def backtest(
    values: list[float],
    methods: tuple[str, ...] = METHODS,
    min_train: int = 6,
    confidence: float = 0.9,
    **options,
) -> dict:
    """Walk-forward test: at each step t, train on values[:t] and predict values[t].

    Returns the scored predictions and a summary (MSPE, RMSPE, hit rate, ...) per
    method, so models are compared on the same series and the same metric.
    """
    values = [float(v) for v in values]
    if len(values) <= min_train:
        raise ValueError(f"Need more than min_train = {min_train} values to backtest.")
    results = {}
    for method in methods:
        steps, scores = [], []
        for t in range(min_train, len(values)):
            p = predict_next(values[:t], method=method, confidence=confidence, **(options if method == "qu" else {}))
            score = score_forecast(values[t], p.value, p.low, p.high)
            steps.append({"step": t, "prediction": p.value, "low": p.low, "high": p.high, **score.as_dict()})
            scores.append(score)
        results[method] = {"summary": summarize(scores), "steps": steps}
    return results


__all__ = ["METHODS", "Prediction", "backtest", "predict_next", "predict_next_linear", "predict_next_quantum"]
