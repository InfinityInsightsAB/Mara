"""One-step conditional continuation evaluation for hybrid LSMC-PDE."""

from __future__ import annotations

import numpy as np
from numpy.polynomial.hermite import hermgauss


def conditional_expectation_one_step(
    asset_grid: np.ndarray,
    terminal_values: np.ndarray,
    mean_log_shift: float,
    variance: float,
    hermite_nodes: int = 16,
) -> np.ndarray:
    """Evaluate E[f(X_{n+1}) | X_n=s] with Gaussian quadrature."""
    if asset_grid.ndim != 1 or terminal_values.ndim != 1:
        raise ValueError("asset_grid and terminal_values must be 1D.")
    if asset_grid.shape != terminal_values.shape:
        raise ValueError("asset_grid and terminal_values must share shape.")
    if np.any(asset_grid <= 0):
        raise ValueError("asset_grid must be strictly positive.")

    log_s = np.log(asset_grid)
    term = np.asarray(terminal_values, dtype=float)
    left = float(term[0])
    right = float(term[-1])

    if variance <= 1e-16:
        return np.interp(log_s + mean_log_shift, log_s, term, left=left, right=right)

    nodes, weights = hermgauss(int(hermite_nodes))
    z = np.sqrt(2.0 * variance) * nodes + mean_log_shift
    z = np.clip(z, -80.0, 80.0)
    weights = weights / np.sqrt(np.pi)

    out = np.zeros_like(term, dtype=float)
    for w, zeta in zip(weights, z):
        x = log_s + zeta
        vals = np.interp(x, log_s, term, left=left, right=right)
        out += float(w) * vals
    return out
