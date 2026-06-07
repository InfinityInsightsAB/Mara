import gc
import json
import math
import tempfile

import numpy as np


_ORIG_CLEANUP = tempfile.TemporaryDirectory.cleanup


def _cleanup(self) -> None:
    gc.collect()
    try:
        _ORIG_CLEANUP(self)
    except PermissionError:
        pass


tempfile.TemporaryDirectory.cleanup = _cleanup


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

option_type = "put"
K = 100.0
T = 1.0
N = 1_000_000
N_low = 1_000_000
N_ex = 100
M = 600
seed = 2026
low_seed = 2103
ridge_lambda = 1e-10
store_dir = None

basis_degree = 3
basis_size = 16
state_dtype = np.float32

exercise_indices = np.rint(np.linspace(0.0, M, N_ex + 1)).astype(np.int32)
exercise_indices[0] = 0
exercise_indices[-1] = M
interval_steps = np.diff(exercise_indices)
exercise_times = T * exercise_indices / float(M)
internal_steps = M / float(N_ex)

if M <= 0 or N_ex <= 0:
    raise ValueError("M and N_ex must be positive.")
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


def payoff(spot: np.ndarray | float) -> np.ndarray | float:
    return np.maximum(K - spot, 0.0)


def state_basis(spot: np.ndarray, v: np.ndarray, vp: np.ndarray) -> np.ndarray:
    r"""
    Use the full-state cubic basis

        (1, x, y, z, x^2, y^2, z^2, xy, xz, yz, x^3, y^3, z^3, p, p^2, p^3),

    with x = S/S0, y = v/theta, z = v'/theta, p = (K-S)^+/K.
    """
    x = spot.astype(np.float64) / max(S0, 1e-8)
    y = v.astype(np.float64) / max(theta, 1e-8)
    z = vp.astype(np.float64) / max(theta, 1e-8)
    p = payoff(spot).astype(np.float64) / max(K, 1e-8)
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
            y * y * y,
            z * z * z,
            p,
            p * p,
            p * p * p,
        ]
    )


def ridge_regression(x_design: np.ndarray, y_target: np.ndarray, ridge_value: float) -> np.ndarray:
    r"""Solve \arg\min_\beta ||y - X\beta||_2^2 + \lambda ||\beta||_2^2."""
    left = x_design.T @ x_design + ridge_value * np.eye(x_design.shape[1], dtype=np.float64)
    right = x_design.T @ y_target
    try:
        return np.linalg.solve(left, right)
    except np.linalg.LinAlgError:
        return np.linalg.lstsq(left, right, rcond=None)[0]


def make_state_store(
    prefix: str,
    n_paths: int,
    temp_dir: str,
) -> tuple[np.memmap, np.memmap, np.memmap]:
    shape = (N_ex + 1, n_paths)
    spot = np.memmap(
        f"{temp_dir}/{prefix}_spot.dat",
        mode="w+",
        dtype=state_dtype,
        shape=shape,
    )
    v = np.memmap(
        f"{temp_dir}/{prefix}_v.dat",
        mode="w+",
        dtype=state_dtype,
        shape=shape,
    )
    vp = np.memmap(
        f"{temp_dir}/{prefix}_vp.dat",
        mode="w+",
        dtype=state_dtype,
        shape=shape,
    )
    return spot, v, vp


def simulate_exercise_states(
    n_paths: int,
    seed_value: int,
    prefix: str,
    temp_dir: str,
) -> tuple[np.memmap, np.memmap, np.memmap]:
    r"""Euler scheme for (S,v,v') recorded only at Bermudan dates."""
    dt = T / M
    sqrt_dt = math.sqrt(dt)
    rng = np.random.default_rng(seed_value)
    spot, v, vp = make_state_store(prefix, n_paths, temp_dir)

    spot_now = np.full(n_paths, S0, dtype=state_dtype)
    v_now = np.full(n_paths, v0, dtype=state_dtype)
    vp_now = np.full(n_paths, vp0, dtype=state_dtype)
    spot[0] = spot_now
    v[0] = v_now
    vp[0] = vp_now

    for exercise_step, n_small_steps in enumerate(interval_steps, start=1):
        for _ in range(int(n_small_steps)):
            z = rng.standard_normal((n_paths, 3)).astype(np.float32) @ chol.T
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

    spot.flush()
    v.flush()
    vp.flush()
    return spot, v, vp


def lsmc_direct_and_coefficients() -> tuple[float, float, list[np.ndarray | None]]:
    r"""Backward LSMC recursion on the full state (S,v,v')."""
    coeff_steps: list[np.ndarray | None] = [None] * (N_ex + 1)
    with tempfile.TemporaryDirectory(dir=store_dir) as temp_dir:
        spot, v, vp = simulate_exercise_states(N, seed, "train", temp_dir)
        cashflow = payoff(np.asarray(spot[N_ex])).astype(np.float64)

        for step in range(N_ex - 1, 0, -1):
            dt_step = float(exercise_times[step + 1] - exercise_times[step])
            discounted_future = np.exp(-r * dt_step) * cashflow
            exercise_value = payoff(np.asarray(spot[step])).astype(np.float64)
            x_design = state_basis(np.asarray(spot[step]), np.asarray(v[step]), np.asarray(vp[step]))
            coeff = ridge_regression(x_design, discounted_future, ridge_lambda)
            continuation = x_design @ coeff
            exercise_now = exercise_value >= continuation
            cashflow = np.where(exercise_now, exercise_value, discounted_future)
            coeff_steps[step] = coeff

        time0_discount = np.exp(-r * float(exercise_times[1] - exercise_times[0]))
        direct_samples = time0_discount * cashflow
        direct_price = max(float(payoff(S0)), float(np.mean(direct_samples)))
        direct_error = float(np.std(direct_samples, ddof=1) / math.sqrt(N)) if N > 1 else 0.0

    return direct_price, direct_error, coeff_steps


def lsmc_low_estimator(coeff_steps: list[np.ndarray | None]) -> tuple[float, float]:
    r"""Fresh-path low estimator under the learned stopping rule."""
    with tempfile.TemporaryDirectory(dir=store_dir) as temp_dir:
        spot, v, vp = simulate_exercise_states(N_low, low_seed, "low", temp_dir)

        discounted_payoff = np.exp(-r * float(exercise_times[-1])) * payoff(np.asarray(spot[N_ex])).astype(np.float64)
        exercised = np.zeros(N_low, dtype=bool)

        for step in range(1, N_ex):
            coeff = coeff_steps[step]
            if coeff is None:
                raise RuntimeError(f"Missing coefficient step for time index {step}.")

            exercise_value = payoff(np.asarray(spot[step])).astype(np.float64)
            x_design = state_basis(np.asarray(spot[step]), np.asarray(v[step]), np.asarray(vp[step]))
            continuation = x_design @ coeff
            exercise_now = (~exercised) & (exercise_value >= continuation)
            discounted_payoff[exercise_now] = np.exp(-r * float(exercise_times[step])) * exercise_value[exercise_now]
            exercised[exercise_now] = True

        low_price = float(np.mean(discounted_payoff))
        low_error = float(np.std(discounted_payoff, ddof=1) / math.sqrt(N_low)) if N_low > 1 else 0.0

    return low_price, low_error


def benchmark_prices() -> dict[str, float | int | bool]:
    direct_price, direct_error, coeff_steps = lsmc_direct_and_coefficients()
    low_price, low_error = lsmc_low_estimator(coeff_steps)
    return {
        "S0": S0,
        "K": K,
        "T": T,
        "paths": N,
        "low_paths": N_low,
        "exercise_dates": N_ex,
        "euler_steps": M,
        "internal_steps": internal_steps,
        "basis_degree": basis_degree,
        "basis_size": basis_size,
        "seed": seed,
        "low_seed": low_seed,
        "time_zero_exercise_in_low": False,
        "lsmc_direct_price": direct_price,
        "lsmc_direct_error": direct_error,
        "lsmc_low_price": low_price,
        "lsmc_low_error": low_error,
    }


if __name__ == "__main__":
    results = benchmark_prices()

    print("LSMC benchmark for a Bermudan put")
    print("Model: generalized Gatheral double mean-reverting (gDMR)")
    print(f"Option type:          {option_type}")
    print(f"Spot:                 {results['S0']:.2f}")
    print(f"Strike:               {results['K']:.2f}")
    print(f"Maturity:             {results['T']:.2f}")
    print(f"Training paths:       {results['paths']}")
    print(f"Low-estimator paths:  {results['low_paths']}")
    print(f"Exercise dates:       {results['exercise_dates']}")
    print(f"Euler steps:          {results['euler_steps']}")
    print(f"Internal steps:       {results['internal_steps']:.6g}")
    print(f"Basis degree:         {results['basis_degree']}")
    print(f"Basis size:           {results['basis_size']}")
    print(f"Seed:                 {results['seed']}")
    print(f"Low seed:             {results['low_seed']}")
    print(f"Time-zero exercise in low: {results['time_zero_exercise_in_low']}")
    print(f"LSMC direct price:    {results['lsmc_direct_price']:.6f}")
    print(f"LSMC direct error:    {results['lsmc_direct_error']:.6f}")
    print(f"LSMC low price:       {results['lsmc_low_price']:.6f}")
    print(f"LSMC low error:       {results['lsmc_low_error']:.6f}")
    print("RESULT_JSON: " + json.dumps(results, sort_keys=True))
