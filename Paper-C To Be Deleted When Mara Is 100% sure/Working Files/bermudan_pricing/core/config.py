"""Common configuration objects for pricing experiments."""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np


def _as_float(value: float, name: str) -> float:
    if not np.isfinite(value):
        raise ValueError(f"{name} must be finite, got {value}")
    return float(value)


@dataclass(frozen=True)
class GDMRParameters:
    """Model parameters for the generalized double mean-reverting model."""

    s0: float = 100.0
    v0: float = 0.04
    v0_prime: float = 0.04
    r: float = 0.03
    kappa1: float = 2.0
    kappa2: float = 1.0
    theta: float = 0.04
    xi1: float = 0.35
    xi2: float = 0.20
    delta1: float = 0.5
    delta2: float = 0.5
    rho12: float = 0.20
    rho13: float = 0.10
    rho23: float = 0.10

    def __post_init__(self) -> None:
        for key in [
            "s0",
            "v0",
            "v0_prime",
            "r",
            "kappa1",
            "kappa2",
            "theta",
            "xi1",
            "xi2",
            "delta1",
            "delta2",
            "rho12",
            "rho13",
            "rho23",
        ]:
            object.__setattr__(self, key, _as_float(getattr(self, key), key))

        if self.v0 < 0 or self.v0_prime < 0:
            raise ValueError("v0 and v0_prime must be non-negative.")
        if self.theta < 0:
            raise ValueError("theta must be non-negative.")
        if self.delta1 < 0.5 or self.delta2 < 0.5:
            raise ValueError("delta1 and delta2 must be >= 0.5.")
        for rho_name in ["rho12", "rho13", "rho23"]:
            value = getattr(self, rho_name)
            if value < -1.0 or value > 1.0:
                raise ValueError(f"{rho_name} must be in [-1, 1].")


@dataclass(frozen=True)
class OptionConfig:
    """Path-independent Bermudan payoff shape used at each exercise date."""

    strike: float = 100.0
    option_type: str = "put"

    def __post_init__(self) -> None:
        if self.strike <= 0:
            raise ValueError("strike must be positive.")
        t = self.option_type.lower()
        if t not in {"call", "put"}:
            raise ValueError("option_type must be 'call' or 'put'.")
        object.__setattr__(self, "option_type", t)

    def payoff(self, spot: np.ndarray | float) -> np.ndarray:
        if self.option_type == "call":
            return np.maximum(np.asarray(spot) - self.strike, 0.0)
        return np.maximum(self.strike - np.asarray(spot), 0.0)


@dataclass(frozen=True)
class SolverConfig:
    """Numerical options shared by all engines."""

    T: float = 1.0
    n_paths: int = 500
    n_steps: int = 12
    n_asset: int = 31
    s_grid_low_factor: float = 0.35
    s_grid_high_factor: float = 3.0
    hermite_nodes: int = 16
    ridge_lambda: float = 1e-8
    include_cross_term: bool = True
    seed: int = 2026

    def __post_init__(self) -> None:
        if self.T <= 0:
            raise ValueError("T must be positive.")
        if self.n_paths < 1:
            raise ValueError("n_paths must be >= 1.")
        if self.n_steps < 1:
            raise ValueError("n_steps must be >= 1.")
        if self.n_asset < 3:
            raise ValueError("n_asset must be >= 3.")
        if self.hermite_nodes < 3:
            raise ValueError("hermite_nodes must be >= 3.")
        if self.s_grid_low_factor <= 0 or self.s_grid_high_factor <= self.s_grid_low_factor:
            raise ValueError("Invalid asset-grid scaling factors.")

        object.__setattr__(self, "n_paths", int(self.n_paths))
        object.__setattr__(self, "n_steps", int(self.n_steps))
        object.__setattr__(self, "n_asset", int(self.n_asset))
        object.__setattr__(self, "hermite_nodes", int(self.hermite_nodes))
