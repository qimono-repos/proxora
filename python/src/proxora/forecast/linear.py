"""Classical next-value prediction: ordinary least squares on the time index.

The same model as ``clojure/src/proxora/regression.clj``: treat the sequence as
y-values at x = 0, 1, 2, ... and extrapolate the fitted line one step. The range
is the classical prediction interval for a new observation:

    y_hat +/- t(1 - alpha/2, n - 2) * s * sqrt(1 + 1/n + (x0 - mean_x)^2 / Sxx)
"""

from __future__ import annotations

from math import sqrt

from scipy.stats import t as student_t

from proxora.forecast.types import Prediction


def fit_line(values: list[float]) -> tuple[float, float]:
    """Return (intercept, slope) of the least-squares line through the series."""
    n = len(values)
    if n < 2:
        raise ValueError("Linear regression needs at least two values.")
    xs = range(n)
    mean_x = (n - 1) / 2
    mean_y = sum(values) / n
    sxx = sum((x - mean_x) ** 2 for x in xs)
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, values))
    slope = sxy / sxx
    return mean_y - slope * mean_x, slope


def predict_next_linear(values: list[float], confidence: float = 0.9) -> Prediction:
    """Predict the next value of ``values`` with an OLS prediction interval."""
    values = [float(v) for v in values]
    intercept, slope = fit_line(values)
    n = len(values)
    x0 = n
    point = intercept + slope * x0

    residuals = [y - (intercept + slope * x) for x, y in enumerate(values)]
    low = high = point
    s = None
    if n >= 3:
        s = sqrt(sum(r * r for r in residuals) / (n - 2))
        mean_x = (n - 1) / 2
        sxx = sum((x - mean_x) ** 2 for x in range(n))
        t_crit = float(student_t.ppf(1 - (1 - confidence) / 2, n - 2))
        half_width = t_crit * s * sqrt(1 + 1 / n + (x0 - mean_x) ** 2 / sxx)
        low, high = point - half_width, point + half_width

    return Prediction(
        method="lr",
        value=point,
        low=low,
        high=high,
        confidence=confidence,
        n_observations=n,
        details={
            "intercept": intercept,
            "slope": slope,
            "residual_std": s,
            "in_sample_rmse": sqrt(sum(r * r for r in residuals) / n),
        },
    )
