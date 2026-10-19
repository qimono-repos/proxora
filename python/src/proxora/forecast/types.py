"""Shared result type for every PROXORA predictor."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class Prediction:
    """A next-value forecast in the same shape the trading book logs:
    a point value plus a range (low, high) at a stated confidence."""

    method: str
    value: float
    low: float
    high: float
    confidence: float
    n_observations: int
    details: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return asdict(self)
