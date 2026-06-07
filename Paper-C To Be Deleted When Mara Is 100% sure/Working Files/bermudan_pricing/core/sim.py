"""Simulation primitives for the generalized DMR model."""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from .config import GDMRParameters


@dataclass(frozen=True)
class SimulationOutput:
    times: np.ndarray
    s: np.ndarray
    v: np.ndarray
    v_prime: np.ndarray
    v_integral: np.ndarray
    drift_shift: np.ndarray
    correlated_shift: np.ndarray


def projection_coefficients(rho12: float, rho13: float, rho23: float) -> tuple[float, float, float]:
    """Return beta2, beta3, sigma_perp_sq used in the orthogonal decomposition."""
    if abs(rho23) >= 1.0:
        raise ValueError("|rho23| must be < 1 for conditional decomposition.")
    denom = 1.0 - rho23 * rho23
    beta2 = (rho12 - rho13 * rho23) / denom
    beta3 = (rho13 - rho12 * rho23) / denom
    sigma_perp_sq = (
        1.0
        - rho12 * rho12
        - rho13 * rho13
        - rho23 * rho23
        + 2.0 * rho12 * rho13 * rho23
    ) / denom
    if sigma_perp_sq < -1e-12:
        raise ValueError("Negative sigma_perp^2 from correlation matrix.")
    return float(beta2), float(beta3), float(max(0.0, sigma_perp_sq))


def simulate_gdmr_paths(
    params: GDMRParameters,
    n_paths: int,
    n_steps: int,
    T: float,
    seed: int,
) -> SimulationOutput:
    """Simulate one grid of \((S_t,v_t,v'_t)\) paths on exercise time dates."""
    dt = T / n_steps
    times = np.linspace(0.0, T, n_steps + 1)

    corr = np.array(
        [
            [1.0, params.rho12, params.rho13],
            [params.rho12, 1.0, params.rho23],
            [params.rho13, params.rho23, 1.0],
        ]
    )
    eigs = np.linalg.eigvalsh(corr)
    if np.min(eigs) < -1e-12:
        raise ValueError("Correlation matrix is not positive semidefinite.")
    chol = np.linalg.cholesky(corr)

    beta2, beta3, _ = projection_coefficients(params.rho12, params.rho13, params.rho23)

    s_paths = np.empty((n_paths, n_steps + 1), dtype=float)
    v_paths = np.empty((n_paths, n_steps + 1), dtype=float)
    vp_paths = np.empty((n_paths, n_steps + 1), dtype=float)
    v_integral = np.empty((n_paths, n_steps), dtype=float)
    drift_shift = np.empty((n_paths, n_steps), dtype=float)
    correlated_shift = np.empty((n_paths, n_steps), dtype=float)

    rng = np.random.default_rng(seed)
    s_paths[:, 0] = params.s0
    v_paths[:, 0] = params.v0
    vp_paths[:, 0] = params.v0_prime
    log_s = np.log(np.maximum(s_paths[:, 0], 1e-12))

    for step in range(n_steps):
        v_prev = np.maximum(v_paths[:, step], 0.0)
        vp_prev = np.maximum(vp_paths[:, step], 0.0)

        dW = rng.normal(size=(n_paths, 3)) @ chol.T * np.sqrt(dt)
        dW1 = dW[:, 0]
        dW2 = dW[:, 1]
        dW3 = dW[:, 2]

        vp_next = vp_prev + params.kappa2 * (params.theta - vp_prev) * dt
        vp_next = vp_next + params.xi2 * np.power(vp_prev, params.delta2) * dW3
        vp_paths[:, step + 1] = np.maximum(vp_next, 0.0)

        v_next = v_prev + params.kappa1 * (vp_prev - v_prev) * dt
        v_next = v_next + params.xi1 * np.power(v_prev, params.delta1) * dW2
        v_paths[:, step + 1] = np.maximum(v_next, 0.0)

        drift_shift[:, step] = params.r * dt - 0.5 * v_prev * dt
        correlated_shift[:, step] = np.sqrt(v_prev) * (beta2 * dW2 + beta3 * dW3)
        v_integral[:, step] = v_prev * dt

        log_s = log_s + drift_shift[:, step] + np.sqrt(v_prev) * dW1
        s_paths[:, step + 1] = np.exp(log_s)

    return SimulationOutput(
        times=times,
        s=s_paths,
        v=v_paths,
        v_prime=vp_paths,
        v_integral=v_integral,
        drift_shift=drift_shift,
        correlated_shift=correlated_shift,
    )

