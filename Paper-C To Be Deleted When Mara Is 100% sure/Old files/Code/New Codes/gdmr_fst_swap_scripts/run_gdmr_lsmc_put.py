#!/usr/bin/env python3
"""
Standalone Bermudan put pricer for the generalized Gatheral Double Mean-
Reverting (gDMR) model using a standard full-path LSMC policy.

The script reports a direct / high estimate from the training sample and an
independent low estimate from fresh paths.
"""

from __future__ import annotations

import json
import math
import os
from typing import Optional

import numpy as np

# -----------------------------------------------------------------------------
# Model inputs for the generalized Gatheral double mean-reverting model.
# -----------------------------------------------------------------------------
S0 = 100.0
v0 = 0.04
vp0 = 0.04
r = 0.03
kappa1 = 2.0
kappa2 = 1.0
theta = 0.04
xi1 = 0.35
xi2 = 0.20
delta1 = 0.5
delta2 = 0.5
rho12 = 0.20
rho13 = 0.10
rho23 = 0.10


def env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    return default if value is None else int(value)



def env_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    return default if value is None else float(value)


# -----------------------------------------------------------------------------
# Bermudan put set-up.
# -----------------------------------------------------------------------------
option_type = "put"
K = 100.0
T = 1.0
N = env_int("GDMR_LSMC_PATHS", 5_000)
N_low = env_int("GDMR_LSMC_LOW_PATHS", 5_000)
N_ex = env_int("GDMR_EXERCISE_DATES", 20)
M = env_int("GDMR_EULER_STEPS", 200)
seed = env_int("GDMR_LSMC_SEED", 1701)
low_seed = env_int("GDMR_LSMC_LOW_SEED", 1777)
ridge_lambda = env_float("GDMR_LSMC_RIDGE", 1e-10)

exercise_indices = np.rint(np.linspace(0.0, M, N_ex + 1)).astype(np.int32)
exercise_indices[0] = 0
exercise_indices[-1] = M
interval_steps = np.diff(exercise_indices)
exercise_times = T * exercise_indices / float(M)
internal_steps = M / float(N_ex)

if np.any(interval_steps <= 0):
    raise ValueError("Exercise grid must be strictly increasing after rounding.")

corr = np.array(
    [
        [1.0, rho12, rho13],
        [rho12, 1.0, rho23],
        [rho13, rho23, 1.0],
    ],
    dtype=np.float64,
)
chol = np.linalg.cholesky(corr).astype(np.float32)


# -----------------------------------------------------------------------------
# Core helpers.
# -----------------------------------------------------------------------------
def payoff(spot: np.ndarray | float) -> np.ndarray | float:
    return np.maximum(K - spot, 0.0)



def regression_features(spot: np.ndarray, v: np.ndarray, vp: np.ndarray) -> np.ndarray:
    x = spot / K - 1.0
    y = np.sqrt(np.maximum(v, 0.0) / max(theta, 1e-12)) - 1.0
    z = np.sqrt(np.maximum(vp, 0.0) / max(theta, 1e-12)) - 1.0
    p = payoff(spot) / K
    return np.column_stack(
        [
            np.ones_like(x),
            x,
            y,
            z,
            x * x,
            y * y,
            z * z,
            x * y,
            x * z,
            y * z,
            x * x * x,
            p,
            p * p,
            x * p,
            y * p,
            z * p,
        ]
    ).astype(np.float64)



def ridge_regression(x_design: np.ndarray, y_target: np.ndarray, ridge_value: float) -> np.ndarray:
    left = x_design.T @ x_design + ridge_value * np.eye(x_design.shape[1], dtype=np.float64)
    right = x_design.T @ y_target
    try:
        return np.linalg.solve(left, right)
    except np.linalg.LinAlgError:
        return np.linalg.lstsq(left, right, rcond=None)[0]



def continuation_from_coefficients(
    coeff: Optional[np.ndarray],
    spot: np.ndarray,
    v: np.ndarray,
    vp: np.ndarray,
) -> np.ndarray:
    if coeff is None:
        return np.zeros_like(spot, dtype=np.float64)
    return regression_features(spot, v, vp) @ coeff



def simulate_exercise_paths(n_paths: int, seed_value: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    dt = T / M
    sqrt_dt = math.sqrt(dt)
    rng = np.random.default_rng(seed_value)

    spot = np.empty((N_ex + 1, n_paths), dtype=np.float32)
    v = np.empty((N_ex + 1, n_paths), dtype=np.float32)
    vp = np.empty((N_ex + 1, n_paths), dtype=np.float32)

    spot_now = np.full(n_paths, S0, dtype=np.float32)
    v_now = np.full(n_paths, v0, dtype=np.float32)
    vp_now = np.full(n_paths, vp0, dtype=np.float32)
    spot[0] = spot_now
    v[0] = v_now
    vp[0] = vp_now

    for exercise_step, n_small_steps in enumerate(interval_steps, start=1):
        for _ in range(int(n_small_steps)):
            z = rng.standard_normal((n_paths, 3), dtype=np.float32) @ chol.T
            z1 = z[:, 0]
            z2 = z[:, 1]
            z3 = z[:, 2]

            v_pos = np.maximum(v_now, 0.0)
            vp_pos = np.maximum(vp_now, 0.0)

            vp_next = vp_pos + kappa2 * (theta - vp_pos) * dt
            vp_next += xi2 * np.power(vp_pos, delta2) * sqrt_dt * z3
            vp_now = np.maximum(vp_next, 0.0)

            v_next = v_pos + kappa1 * (vp_pos - v_pos) * dt
            v_next += xi1 * np.power(v_pos, delta1) * sqrt_dt * z2
            v_now = np.maximum(v_next, 0.0)

            log_move = (r - 0.5 * v_pos) * dt + np.sqrt(v_pos) * sqrt_dt * z1
            spot_now = spot_now * np.exp(log_move)

        spot[exercise_step] = spot_now
        v[exercise_step] = v_now
        vp[exercise_step] = vp_now

    return spot, v, vp


# -----------------------------------------------------------------------------
# LSMC pricing.
# -----------------------------------------------------------------------------
def lsmc_prices() -> dict[str, float | int | bool]:
    spot, v, vp = simulate_exercise_paths(N, seed)

    stop_index = np.full(N, N_ex, dtype=np.int32)
    cashflow = payoff(spot[-1]).astype(np.float64)
    coeff_steps: list[Optional[np.ndarray]] = [None] * (N_ex + 1)

    for step in range(N_ex - 1, 0, -1):
        alive = stop_index > step
        if not np.any(alive):
            continue

        spot_now = spot[step, alive].astype(np.float64)
        payoff_now = payoff(spot_now).astype(np.float64)
        itm = payoff_now > 0.0

        if not np.any(itm):
            coeff_steps[step] = None
            continue

        times_to_cf = exercise_times[stop_index[alive]] - exercise_times[step]
        continuation_target = cashflow[alive] * np.exp(-r * times_to_cf)

        features_itm = regression_features(
            spot_now[itm],
            v[step, alive][itm].astype(np.float64),
            vp[step, alive][itm].astype(np.float64),
        )
        coeff = ridge_regression(features_itm, continuation_target[itm], ridge_lambda)
        coeff_steps[step] = coeff

        continuation_pred = features_itm @ coeff
        exercise_now_itm = payoff_now[itm] >= continuation_pred

        alive_indices = np.where(alive)[0]
        itm_indices = alive_indices[itm]
        exercise_indices = itm_indices[exercise_now_itm]

        cashflow[exercise_indices] = payoff(spot[step, exercise_indices]).astype(np.float64)
        stop_index[exercise_indices] = step

    discounted_cf = cashflow * np.exp(-r * exercise_times[stop_index])
    direct_price = max(float(payoff(S0)), float(np.mean(discounted_cf)))
    direct_error = float(np.std(discounted_cf, ddof=1) / math.sqrt(N)) if N > 1 else 0.0

    # -----------------------------------------------------------------
    # Independent low estimator.
    # -----------------------------------------------------------------
    spot_low, v_low, vp_low = simulate_exercise_paths(N_low, low_seed)
    stop_index_low = np.full(N_low, N_ex, dtype=np.int32)
    cashflow_low = payoff(spot_low[-1]).astype(np.float64)

    for step in range(1, N_ex):
        alive = stop_index_low == N_ex
        if not np.any(alive):
            break

        payoff_now = payoff(spot_low[step, alive]).astype(np.float64)
        itm = payoff_now > 0.0
        if not np.any(itm):
            continue

        coeff = coeff_steps[step]
        continuation_pred = continuation_from_coefficients(
            coeff,
            spot_low[step, alive][itm].astype(np.float64),
            v_low[step, alive][itm].astype(np.float64),
            vp_low[step, alive][itm].astype(np.float64),
        )
        exercise_now_itm = payoff_now[itm] >= continuation_pred

        alive_indices = np.where(alive)[0]
        itm_indices = alive_indices[itm]
        exercise_indices = itm_indices[exercise_now_itm]

        cashflow_low[exercise_indices] = payoff(spot_low[step, exercise_indices]).astype(np.float64)
        stop_index_low[exercise_indices] = step

    discounted_low = cashflow_low * np.exp(-r * exercise_times[stop_index_low])
    # Time-zero exercise is intentionally excluded in the low estimator to match
    # the usual independent-policy-evaluation construction.
    low_price = float(np.mean(discounted_low))
    low_error = float(np.std(discounted_low, ddof=1) / math.sqrt(N_low)) if N_low > 1 else 0.0

    feature_size = regression_features(
        np.array([S0], dtype=np.float64),
        np.array([v0], dtype=np.float64),
        np.array([vp0], dtype=np.float64),
    ).shape[1]

    return {
        "S0": S0,
        "K": K,
        "T": T,
        "paths": N,
        "low_paths": N_low,
        "exercise_dates": N_ex,
        "euler_steps": M,
        "internal_steps": internal_steps,
        "feature_size": int(feature_size),
        "ridge_lambda": ridge_lambda,
        "seed": seed,
        "low_seed": low_seed,
        "time_zero_exercise_in_low": False,
        "lsmc_direct_price": direct_price,
        "lsmc_direct_error": direct_error,
        "lsmc_low_price": low_price,
        "lsmc_low_error": low_error,
    }


if __name__ == "__main__":
    results = lsmc_prices()

    print("LSMC for a Bermudan put")
    print("Model: generalized Gatheral double mean-reverting (gDMR)")
    print(f"Option type:               {option_type}")
    print(f"Spot:                      {results['S0']:.2f}")
    print(f"Strike:                    {results['K']:.2f}")
    print(f"Maturity:                  {results['T']:.2f}")
    print(f"Training paths:            {results['paths']}")
    print(f"Low-estimator paths:       {results['low_paths']}")
    print(f"Exercise dates:            {results['exercise_dates']}")
    print(f"Euler steps:               {results['euler_steps']}")
    print(f"Internal steps:            {results['internal_steps']:.6g}")
    print(f"Regression feature size:   {results['feature_size']}")
    print(f"Ridge lambda:              {results['ridge_lambda']:.3e}")
    print(f"Seed:                      {results['seed']}")
    print(f"Low seed:                  {results['low_seed']}")
    print(f"Time-zero exercise in low: {results['time_zero_exercise_in_low']}")
    print(f"LSMC direct price:         {results['lsmc_direct_price']:.6f}")
    print(f"LSMC direct error:         {results['lsmc_direct_error']:.6f}")
    print(f"LSMC low price:            {results['lsmc_low_price']:.6f}")
    print(f"LSMC low error:            {results['lsmc_low_error']:.6f}")
    print("RESULT_JSON: " + json.dumps(results, sort_keys=True))
