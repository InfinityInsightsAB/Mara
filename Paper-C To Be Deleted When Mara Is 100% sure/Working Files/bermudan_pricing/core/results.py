"""Canonical result containers for all pricing engines."""

from __future__ import annotations

from dataclasses import dataclass, field
import numpy as np


@dataclass(frozen=True)
class MethodResult:
    """Standard result object returned by all pricers."""

    method: str
    direct_estimator: float
    low_estimator: float | None = None
    asset_grid: np.ndarray | None = None
    coeffs: np.ndarray | None = None
    value_paths: np.ndarray | None = None
    times: np.ndarray | None = None
    s_paths: np.ndarray | None = None
    meta: dict[str, float | int | str] = field(default_factory=dict)


@dataclass(frozen=True)
class MethodSummary:
    method: str
    direct: float
    low: float | None
    n_paths: int
    n_steps: int
    seed: int
