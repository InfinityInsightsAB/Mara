#!/usr/bin/env python3
"""
Standalone hybrid LSMC-PDE Bermudan put pricer for the generalized Gatheral
Double Mean-Reverting (gDMR) model.

What is changed versus the original Gauss-Hermite version:
1. The one-step conditional expectation is evaluated with a Fourier space
   time-stepping (FST/FFT) convolution on the log-price grid.
2. The low estimator is kept hybrid: it simulates fresh volatility paths only
   and recursively re-solves the conditional one-step problem along those paths.

This mirrors the one-asset hybrid workflow described in Farahany's papers and
in the accompanying gDMR manuscript, but it is still a standalone research code
rather than the authors' original production implementation.

This BGK Testing copy keeps the Final-Code notation and interface, but its
default model block is set to the BGK screenshot parameters.
"""

from __future__ import annotations

import json
import math
import os
from typing import Optional

import numpy as np

# -----------------------------------------------------------------------------
# Model inputs for the generalized Gatheral double mean-reverting model.
# These defaults are the BGK screenshot parameter block rewritten in the
# Final-Code gDMR notation.
# -----------------------------------------------------------------------------
S0 = 100.0
v0 = 0.114
vp0 = 0.110
r = 0.0
kappa1 = 5.5
kappa2 = 0.1
theta = 0.078
xi1 = 2.689
xi2 = 0.502
delta1 = 0.94
delta2 = 0.94
rho12 = -0.982
rho13 = -0.727
rho23 = 0.59


# -----------------------------------------------------------------------------
# Helpers for environment-variable configuration.
# -----------------------------------------------------------------------------
def env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    return default if value is None else int(value)



def env_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    return default if value is None else float(value)


# -----------------------------------------------------------------------------
# Bermudan put setup.
# Defaults are kept moderate so the scripts are easy to test.
# -----------------------------------------------------------------------------
option_type = "put"
S0 = env_float("GDMR_S0", S0)
K = env_float("GDMR_STRIKE", 100.0)
T = env_float("GDMR_MATURITY", 1.0)
N = env_int("GDMR_HYBRID_PATHS", 1_000)
N_low = env_int("GDMR_HYBRID_LOW_PATHS", 1_000)
N_ex = env_int("GDMR_EXERCISE_DATES", 20)
M = env_int("GDMR_EULER_STEPS", 200)
N_S = env_int("GDMR_HYBRID_ASSET_POINTS", 181)
asset_low_factor = env_float("GDMR_HYBRID_ASSET_LOW_FACTOR", 0.35)
asset_high_factor = env_float("GDMR_HYBRID_ASSET_HIGH_FACTOR", 3.00)
# Shipped default is tuned to the best retained Farahany-style package result.
vol_truncation_quantile = env_float("GDMR_HYBRID_VOL_QUANTILE", 0.997)
fst_pad_factor = env_int("GDMR_HYBRID_FST_PAD_FACTOR", 4)
fst_batch_size = env_int("GDMR_HYBRID_FST_BATCH_SIZE", 256)
seed = env_int("GDMR_HYBRID_SEED", 2026)
low_seed = env_int("GDMR_HYBRID_LOW_SEED", 2103)
vol_basis_degree = 3
ridge_lambda = env_float("GDMR_HYBRID_RIDGE", 1e-10)

exercise_indices = np.rint(np.linspace(0.0, M, N_ex + 1)).astype(np.int32)
exercise_indices[0] = 0
exercise_indices[-1] = M
interval_steps = np.diff(exercise_indices)
exercise_times = T * exercise_indices / float(M)
internal_steps = M / float(N_ex)

if np.any(interval_steps <= 0):
    raise ValueError("Exercise grid must be strictly increasing after rounding.")
if N_S < 3:
    raise ValueError("N_S must be at least 3.")

corr23 = np.array(
    [
        [1.0, rho23],
        [rho23, 1.0],
    ],
    dtype=np.float64,
)
chol23 = np.linalg.cholesky(corr23).astype(np.float32)


# -----------------------------------------------------------------------------
# Core building blocks.
# -----------------------------------------------------------------------------
def payoff(spot: np.ndarray | float) -> np.ndarray | float:
    return np.maximum(K - spot, 0.0)



def projection_coefficients() -> tuple[float, float, float]:
    denominator = 1.0 - rho23**2
    beta2 = (rho12 - rho13 * rho23) / denominator
    beta3 = (rho13 - rho12 * rho23) / denominator
    sigma_perp_sq = (
        1.0 - rho12**2 - rho13**2 - rho23**2 + 2.0 * rho12 * rho13 * rho23
    ) / denominator
    return beta2, beta3, max(float(sigma_perp_sq), 0.0)



def vol_basis(
    v: np.ndarray,
    vp: np.ndarray,
    v_cap: float,
    vp_cap: float,
) -> np.ndarray:
    inside = ((v >= 0.0) & (v <= v_cap) & (vp >= 0.0) & (vp <= vp_cap)).astype(np.float64)
    y = np.clip(v, 0.0, v_cap) / max(v_cap, 1e-12)
    z = np.clip(vp, 0.0, vp_cap) / max(vp_cap, 1e-12)
    return np.column_stack(
        [
            inside,
            inside * y,
            inside * z,
            inside * y * y,
            inside * y * z,
            inside * z * z,
            inside * y * y * y,
            inside * y * y * z,
            inside * y * z * z,
            inside * z * z * z,
        ]
    )



def ridge_regression_all(x_design: np.ndarray, y_targets: np.ndarray, ridge_value: float) -> np.ndarray:
    """
    Solve all asset-grid regressions at once.

    Parameters
    ----------
    x_design : (n_samples, n_features)
    y_targets : (n_samples, n_targets)

    Returns
    -------
    coeff_targets : (n_targets, n_features)
        Each row contains the coefficient vector for one target column.
    """
    left = x_design.T @ x_design + ridge_value * np.eye(x_design.shape[1], dtype=np.float64)
    right = x_design.T @ y_targets
    try:
        coeff_t = np.linalg.solve(left, right)
    except np.linalg.LinAlgError:
        coeff_t = np.linalg.lstsq(left, right, rcond=None)[0]
    return coeff_t.T



def simulate_volatility_statistics(
    n_paths: int,
    seed_value: int,
    beta2: float,
    beta3: float,
    sigma_perp_sq: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    dt = T / M
    sqrt_dt = math.sqrt(dt)
    rng = np.random.default_rng(seed_value)

    v_paths = np.empty((N_ex + 1, n_paths), dtype=np.float32)
    vp_paths = np.empty((N_ex + 1, n_paths), dtype=np.float32)
    a_stats = np.empty((N_ex, n_paths), dtype=np.float64)
    b_stats = np.empty((N_ex, n_paths), dtype=np.float64)
    z_stats = np.empty((N_ex, n_paths), dtype=np.float64)

    v_now = np.full(n_paths, v0, dtype=np.float32)
    vp_now = np.full(n_paths, vp0, dtype=np.float32)
    v_paths[0] = v_now
    vp_paths[0] = vp_now

    for exercise_step, n_small_steps in enumerate(interval_steps):
        a_step = np.zeros(n_paths, dtype=np.float64)
        b_step = np.zeros(n_paths, dtype=np.float64)
        z_step = np.zeros(n_paths, dtype=np.float64)

        for _ in range(int(n_small_steps)):
            z23 = rng.standard_normal((n_paths, 2), dtype=np.float32) @ chol23.T
            z2 = z23[:, 0]
            z3 = z23[:, 1]
            dw2 = sqrt_dt * z2
            dw3 = sqrt_dt * z3

            v_pos = np.maximum(v_now, 0.0)
            vp_pos = np.maximum(vp_now, 0.0)
            sqrt_v = np.sqrt(v_pos)

            a_step += (r - 0.5 * v_pos) * dt
            b_step += sigma_perp_sq * v_pos * dt
            z_step += sqrt_v * (beta2 * dw2 + beta3 * dw3)

            vp_next = vp_pos + kappa2 * (theta - vp_pos) * dt
            vp_next += xi2 * np.power(vp_pos, delta2) * dw3
            vp_now = np.maximum(vp_next, 0.0)

            v_next = v_pos + kappa1 * (vp_pos - v_pos) * dt
            v_next += xi1 * np.power(v_pos, delta1) * dw2
            v_now = np.maximum(v_next, 0.0)

        v_paths[exercise_step + 1] = v_now
        vp_paths[exercise_step + 1] = vp_now
        a_stats[exercise_step] = a_step
        b_stats[exercise_step] = b_step
        z_stats[exercise_step] = z_step

    return v_paths, vp_paths, a_stats, b_stats, z_stats



def truncation_caps(v_paths: np.ndarray, vp_paths: np.ndarray) -> tuple[float, float]:
    v_cap = float(np.quantile(v_paths, vol_truncation_quantile))
    vp_cap = float(np.quantile(vp_paths, vol_truncation_quantile))
    return max(v_cap, v0), max(vp_cap, vp0)



def build_asset_grid() -> np.ndarray:
    low = max(S0 * asset_low_factor, 0.25 * K * asset_low_factor)
    high = max(S0, K) * asset_high_factor
    return np.exp(np.linspace(math.log(low), math.log(high), N_S))



def interpolation_weights(log_grid: np.ndarray, log_spot: float) -> tuple[int, int, float, float]:
    upper = int(np.searchsorted(log_grid, log_spot, side="right"))
    if upper <= 0:
        return 0, 0, 1.0, 0.0
    if upper >= log_grid.size:
        last = log_grid.size - 1
        return last, last, 1.0, 0.0
    lower = upper - 1
    left = float(log_grid[lower])
    right = float(log_grid[upper])
    if right <= left:
        return lower, upper, 1.0, 0.0
    weight_upper = (log_spot - left) / (right - left)
    weight_lower = 1.0 - weight_upper
    return lower, upper, weight_lower, weight_upper



def interpolate_rows_at_spot(log_grid: np.ndarray, values: np.ndarray, spot: float) -> np.ndarray:
    lower, upper, w_lower, w_upper = interpolation_weights(log_grid, math.log(spot))
    return w_lower * values[:, lower] + w_upper * values[:, upper]



def continuation_surface_from_coefficients(
    coefficient_step: np.ndarray,
    v: np.ndarray,
    vp: np.ndarray,
    v_cap: float,
    vp_cap: float,
) -> np.ndarray:
    basis_now = vol_basis(np.maximum(v, 0.0), np.maximum(vp, 0.0), v_cap, vp_cap)
    return basis_now @ coefficient_step.T


# -----------------------------------------------------------------------------
# FST / FFT conditional expectation.
# -----------------------------------------------------------------------------
def _fst_output_shape(n_space: int, pad_factor: int) -> tuple[int, int]:
    n_pad = 1
    target = max(2 * n_space, pad_factor * n_space)
    while n_pad < target:
        n_pad *= 2
    offset = (n_pad - n_space) // 2
    return n_pad, offset



def _interp_shifted_same_grid(
    log_grid: np.ndarray,
    terminal_values: np.ndarray,
    shift: float,
) -> np.ndarray:
    left = float(terminal_values[0])
    right = float(terminal_values[-1])
    return np.interp(log_grid + shift, log_grid, terminal_values, left=left, right=right)



def fst_conditional_expectation_batch(
    log_grid: np.ndarray,
    terminal_matrix: np.ndarray,
    shift_vec: np.ndarray,
    variance_vec: np.ndarray,
    *,
    pad_factor: int,
    batch_size: int,
) -> np.ndarray:
    """
    Evaluate E[f(X + shift + sqrt(var) Z)] row-wise using padded FFTs.

    The constant-edge padding is a practical stabilization to reduce the usual
    circular-convolution wrap-around of FFT-based methods.
    """
    terminal_matrix = np.asarray(terminal_matrix, dtype=np.float64)
    shift_vec = np.asarray(shift_vec, dtype=np.float64)
    variance_vec = np.asarray(variance_vec, dtype=np.float64)

    if terminal_matrix.ndim != 2:
        raise ValueError("terminal_matrix must be 2-dimensional.")
    n_paths, n_space = terminal_matrix.shape
    if shift_vec.shape != (n_paths,) or variance_vec.shape != (n_paths,):
        raise ValueError("shift_vec and variance_vec must match terminal_matrix row count.")

    dy = float(log_grid[1] - log_grid[0])
    n_pad, offset = _fst_output_shape(n_space, pad_factor)
    omega = 2.0 * math.pi * np.fft.fftfreq(n_pad, d=dy)[None, :]

    out = np.empty_like(terminal_matrix, dtype=np.float64)
    tiny_variance = 1e-14

    for start in range(0, n_paths, batch_size):
        end = min(start + batch_size, n_paths)
        chunk = terminal_matrix[start:end]
        shift_chunk = shift_vec[start:end]
        var_chunk = variance_vec[start:end]
        chunk_size = end - start

        padded = np.empty((chunk_size, n_pad), dtype=np.float64)
        padded[:, :offset] = chunk[:, [0]]
        padded[:, offset:offset + n_space] = chunk
        padded[:, offset + n_space:] = chunk[:, [-1]]

        # Very small variances are better handled by direct interpolation.
        small_mask = var_chunk <= tiny_variance
        if np.any(~small_mask):
            idx = np.where(~small_mask)[0]
            fft_values = np.fft.fft(padded[idx], axis=1)
            exponent = (
                1j * omega * shift_chunk[idx, None]
                - 0.5 * var_chunk[idx, None] * (omega**2)
            )
            multiplier = np.exp(exponent)
            conv = np.fft.ifft(fft_values * multiplier, axis=1).real
            out[start:end][idx] = conv[:, offset:offset + n_space]
        if np.any(small_mask):
            idx = np.where(small_mask)[0]
            for local_idx in idx:
                out[start + local_idx] = _interp_shifted_same_grid(
                    log_grid,
                    chunk[local_idx],
                    float(shift_chunk[local_idx]),
                )

    return out


# -----------------------------------------------------------------------------
# Main hybrid pricing routine.
# -----------------------------------------------------------------------------
def hybrid_prices() -> dict[str, float | int | bool]:
    beta2, beta3, sigma_perp_sq = projection_coefficients()
    asset_grid = build_asset_grid()
    log_asset_grid = np.log(asset_grid)
    payoff_grid = payoff(asset_grid).astype(np.float64)

    v_paths, vp_paths, a_stats, b_stats, z_stats = simulate_volatility_statistics(
        N,
        seed,
        beta2,
        beta3,
        sigma_perp_sq,
    )
    v_cap, vp_cap = truncation_caps(v_paths, vp_paths)

    value_next = np.repeat(payoff_grid[None, :], N, axis=0)
    coefficient_steps: list[Optional[np.ndarray]] = [None] * (N_ex + 1)

    for step in range(N_ex - 1, 0, -1):
        discount = math.exp(-r * float(exercise_times[step + 1] - exercise_times[step]))
        v_now = np.maximum(v_paths[step], 0.0)
        vp_now = np.maximum(vp_paths[step], 0.0)
        shift = a_stats[step] + z_stats[step]
        variance = b_stats[step]

        pre_surface = discount * fst_conditional_expectation_batch(
            log_asset_grid,
            value_next,
            shift,
            variance,
            pad_factor=fst_pad_factor,
            batch_size=fst_batch_size,
        )

        basis_now = vol_basis(v_now, vp_now, v_cap, vp_cap).astype(np.float64)
        coefficient_step = ridge_regression_all(basis_now, pre_surface, ridge_lambda)
        completed_surface = basis_now @ coefficient_step.T

        value_next = np.maximum(payoff_grid[None, :], completed_surface)
        coefficient_steps[step] = coefficient_step

    discount0 = math.exp(-r * float(exercise_times[1] - exercise_times[0]))
    pre_surface0 = discount0 * fst_conditional_expectation_batch(
        log_asset_grid,
        value_next,
        a_stats[0] + z_stats[0],
        b_stats[0],
        pad_factor=fst_pad_factor,
        batch_size=fst_batch_size,
    )
    direct_samples = interpolate_rows_at_spot(log_asset_grid, pre_surface0, S0)
    direct_price = max(float(payoff(S0)), float(np.mean(direct_samples)))
    direct_error = float(np.std(direct_samples, ddof=1) / math.sqrt(N)) if N > 1 else 0.0

    # -----------------------------------------------------------------
    # Hybrid low estimator: fresh volatility paths only.
    # -----------------------------------------------------------------
    v_low, vp_low, a_low, b_low, z_low = simulate_volatility_statistics(
        N_low,
        low_seed,
        beta2,
        beta3,
        sigma_perp_sq,
    )

    value_low = np.repeat(payoff_grid[None, :], N_low, axis=0)
    for step in range(N_ex - 1, 0, -1):
        coefficient_step = coefficient_steps[step]
        if coefficient_step is None:
            raise RuntimeError(f"Missing coefficient step for time index {step}.")

        discount = math.exp(-r * float(exercise_times[step + 1] - exercise_times[step]))
        pre_surface_low = discount * fst_conditional_expectation_batch(
            log_asset_grid,
            value_low,
            a_low[step] + z_low[step],
            b_low[step],
            pad_factor=fst_pad_factor,
            batch_size=fst_batch_size,
        )

        policy_continuation = continuation_surface_from_coefficients(
            coefficient_step,
            v_low[step],
            vp_low[step],
            v_cap,
            vp_cap,
        )
        hold_mask = policy_continuation > payoff_grid[None, :]
        value_low = np.where(hold_mask, pre_surface_low, payoff_grid[None, :])

    low_surface0 = discount0 * fst_conditional_expectation_batch(
        log_asset_grid,
        value_low,
        a_low[0] + z_low[0],
        b_low[0],
        pad_factor=fst_pad_factor,
        batch_size=fst_batch_size,
    )
    low_samples = interpolate_rows_at_spot(log_asset_grid, low_surface0, S0)
    # To match the paper/thesis low-estimator construction, time-zero exercise is
    # intentionally excluded here.
    low_price = float(np.mean(low_samples))
    low_error = float(np.std(low_samples, ddof=1) / math.sqrt(N_low)) if N_low > 1 else 0.0

    return {
        "S0": S0,
        "K": K,
        "T": T,
        "paths": N,
        "low_paths": N_low,
        "exercise_dates": N_ex,
        "euler_steps": M,
        "internal_steps": internal_steps,
        "asset_grid_points": N_S,
        "asset_low_factor": asset_low_factor,
        "asset_high_factor": asset_high_factor,
        "vol_basis_degree": vol_basis_degree,
        "vol_basis_size": int(vol_basis(np.array([v0]), np.array([vp0]), v_cap, vp_cap).shape[1]),
        "vol_quantile": vol_truncation_quantile,
        "v_cap": v_cap,
        "vp_cap": vp_cap,
        "seed": seed,
        "low_seed": low_seed,
        "beta2": beta2,
        "beta3": beta3,
        "sigma_perp_sq": sigma_perp_sq,
        "fst_pad_factor": fst_pad_factor,
        "fst_batch_size": fst_batch_size,
        "time_zero_exercise_in_low": False,
        "hybrid_direct_price": direct_price,
        "hybrid_direct_error": direct_error,
        "hybrid_low_price": low_price,
        "hybrid_low_error": low_error,
    }


if __name__ == "__main__":
    results = hybrid_prices()

    print("Hybrid LSMC-PDE for a Bermudan put")
    print("Model: generalized Gatheral double mean-reverting (gDMR)")
    print(f"Option type:                    {option_type}")
    print(f"Spot:                           {results['S0']:.2f}")
    print(f"Strike:                         {results['K']:.2f}")
    print(f"Maturity:                       {results['T']:.2f}")
    print(f"Training volatility paths:      {results['paths']}")
    print(f"Low-estimator volatility paths: {results['low_paths']}")
    print(f"Exercise dates:                 {results['exercise_dates']}")
    print(f"Euler steps:                    {results['euler_steps']}")
    print(f"Internal steps:                 {results['internal_steps']:.6g}")
    print(f"Asset grid points:              {results['asset_grid_points']}")
    print(f"Asset low factor:               {results['asset_low_factor']:.4f}")
    print(f"Asset high factor:              {results['asset_high_factor']:.4f}")
    print(f"FST pad factor:                 {results['fst_pad_factor']}")
    print(f"FST batch size:                 {results['fst_batch_size']}")
    print(f"Vol basis degree:               {results['vol_basis_degree']}")
    print(f"Vol basis size:                 {results['vol_basis_size']}")
    print(f"Vol truncation quantile:        {results['vol_quantile']:.4f}")
    print(f"Vol truncation v cap:           {results['v_cap']:.6f}")
    print(f"Vol truncation vp cap:          {results['vp_cap']:.6f}")
    print(f"Seed:                           {results['seed']}")
    print(f"Low seed:                       {results['low_seed']}")
    print(f"beta2:                          {results['beta2']:.6f}")
    print(f"beta3:                          {results['beta3']:.6f}")
    print(f"sigma_perp^2:                   {results['sigma_perp_sq']:.6f}")
    print(f"Time-zero exercise in low:      {results['time_zero_exercise_in_low']}")
    print(f"Hybrid direct price:            {results['hybrid_direct_price']:.6f}")
    print(f"Hybrid direct error:            {results['hybrid_direct_error']:.6f}")
    print(f"Hybrid low price:               {results['hybrid_low_price']:.6f}")
    print(f"Hybrid low error:               {results['hybrid_low_error']:.6f}")
    print("RESULT_JSON: " + json.dumps(results, sort_keys=True))
