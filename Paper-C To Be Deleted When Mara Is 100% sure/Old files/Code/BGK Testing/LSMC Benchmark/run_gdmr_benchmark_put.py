import gc
import os
import tempfile
from typing import Optional, Tuple

import numpy as np


_ORIG_CLEANUP = tempfile.TemporaryDirectory.cleanup


def _cleanup(self) -> None:
    gc.collect()
    try:
        _ORIG_CLEANUP(self)
    except PermissionError:
        # Windows can hold memmap files briefly during teardown.
        pass


tempfile.TemporaryDirectory.cleanup = _cleanup


# ---------------------------------------------------------------------------
# Environment helpers
# ---------------------------------------------------------------------------


def env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    return int(value)



def env_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    if value is None:
        return default
    return float(value)


# ---------------------------------------------------------------------------
# Model inputs for the generalized Gatheral double mean-reverting model.
# These defaults are the BGK screenshot parameter block rewritten in the
# Final-Code gDMR notation.
# ---------------------------------------------------------------------------

S0 = env_float("GDMR_S0", 100.0)
v0 = env_float("GDMR_V0", 0.114)
vp0 = env_float("GDMR_VP0", 0.110)
r = env_float("GDMR_R", 0.0)
kappa1 = env_float("GDMR_KAPPA1", 5.5)
kappa2 = env_float("GDMR_KAPPA2", 0.1)
theta = env_float("GDMR_THETA", 0.078)
xi1 = env_float("GDMR_XI1", 2.689)
xi2 = env_float("GDMR_XI2", 0.502)
delta1 = env_float("GDMR_DELTA1", 0.94)
delta2 = env_float("GDMR_DELTA2", 0.94)
rho12 = env_float("GDMR_RHO12", -0.982)
rho13 = env_float("GDMR_RHO13", -0.727)
rho23 = env_float("GDMR_RHO23", 0.59)


# Bermudan put setup.
option_type = "put"
K = env_float("GDMR_STRIKE", 100.0)
T = env_float("GDMR_MATURITY", 1.0)
N = env_int("GDMR_LSMC_PATHS", 1_000_000)
N_low = env_int("GDMR_LSMC_LOW_PATHS", N)
N_ex = env_int("GDMR_EXERCISE_DATES", 100)
M = env_int("GDMR_EULER_STEPS", 600)
seed = env_int("GDMR_LSMC_SEED", 2026)
low_seed = env_int("GDMR_LSMC_LOW_SEED", 2103)
ridge_lambda = env_float("GDMR_LSMC_RIDGE", 1e-10)
store_dir = os.environ.get("GDMR_LSMC_STORE_DIR")

basis_degree = 3
basis_size = 16
state_dtype = np.float32

exercise_indices = np.rint(np.linspace(0.0, M, N_ex + 1)).astype(np.int32)
exercise_indices[0] = 0
exercise_indices[-1] = M
interval_steps = np.diff(exercise_indices)
exercise_times = T * exercise_indices / float(M)
internal_steps = M / float(N_ex)

corr = np.array(
    [
        [1.0, rho12, rho13],
        [rho12, 1.0, rho23],
        [rho13, rho23, 1.0],
    ],
    dtype=np.float64,
)
chol = np.linalg.cholesky(corr).astype(np.float32)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def payoff(spot: np.ndarray) -> np.ndarray:
    return np.maximum(K - spot, 0.0)



def state_basis(spot: np.ndarray, v: np.ndarray, vp: np.ndarray) -> np.ndarray:
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
    left = x_design.T @ x_design + ridge_value * np.eye(x_design.shape[1])
    right = x_design.T @ y_target
    try:
        return np.linalg.solve(left, right)
    except np.linalg.LinAlgError:
        return np.linalg.lstsq(x_design, y_target, rcond=None)[0]



def make_state_store(
    prefix: str,
    n_paths: int,
    temp_dir: str,
) -> Tuple[np.memmap, np.memmap, np.memmap]:
    shape = (N_ex + 1, n_paths)
    spot = np.memmap(
        os.path.join(temp_dir, f"{prefix}_spot.dat"),
        mode="w+",
        dtype=state_dtype,
        shape=shape,
    )
    v = np.memmap(
        os.path.join(temp_dir, f"{prefix}_v.dat"),
        mode="w+",
        dtype=state_dtype,
        shape=shape,
    )
    vp = np.memmap(
        os.path.join(temp_dir, f"{prefix}_vp.dat"),
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
) -> Tuple[np.memmap, np.memmap, np.memmap]:
    dt = T / M
    sqrt_dt = np.sqrt(dt)
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
            Z = rng.standard_normal((n_paths, 3)).astype(np.float32) @ chol.T
            z1 = Z[:, 0]
            z2 = Z[:, 1]
            z3 = Z[:, 2]
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



def lsmc_direct_and_coefficients() -> Tuple[float, float, list]:
    coeff_steps = [None] * (N_ex + 1)
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
        direct_price = max(float(payoff(np.array([S0]))[0]), float(np.mean(direct_samples)))
        direct_error = float(np.std(direct_samples, ddof=1) / np.sqrt(N))

    return direct_price, direct_error, coeff_steps



def lsmc_low_estimator(coeff_steps: list) -> Tuple[float, float]:
    with tempfile.TemporaryDirectory(dir=store_dir) as temp_dir:
        spot, v, vp = simulate_exercise_states(N_low, low_seed, "low", temp_dir)

        discounted_payoff = np.exp(-r * float(exercise_times[-1])) * payoff(np.asarray(spot[N_ex])).astype(np.float64)
        exercised = np.zeros(N_low, dtype=bool)

        for step in range(1, N_ex):
            exercise_value = payoff(np.asarray(spot[step])).astype(np.float64)
            x_design = state_basis(np.asarray(spot[step]), np.asarray(v[step]), np.asarray(vp[step]))
            continuation = x_design @ coeff_steps[step]
            exercise_now = (~exercised) & (exercise_value >= continuation)
            discounted_payoff[exercise_now] = np.exp(-r * float(exercise_times[step])) * exercise_value[exercise_now]
            exercised[exercise_now] = True

        low_price = float(np.mean(discounted_payoff))
        low_error = float(np.std(discounted_payoff, ddof=1) / np.sqrt(N_low))

    return low_price, low_error


# ---------------------------------------------------------------------------
# Main run
# ---------------------------------------------------------------------------


def main() -> None:
    direct_price, direct_error, coeff_steps = lsmc_direct_and_coefficients()
    low_price, low_error = lsmc_low_estimator(coeff_steps)

    print("LSMC benchmark for a Bermudan put")
    print("Model: generalized Gatheral double mean-reverting (gDMR)")
    print(f"Option type:          {option_type}")
    print(f"Spot:                 {S0:.2f}")
    print(f"Strike:               {K:.2f}")
    print(f"Maturity:             {T:.2f}")
    print(f"Training paths:       {N}")
    print(f"Low-estimator paths:  {N_low}")
    print(f"Exercise dates:       {N_ex}")
    print(f"Euler steps:          {M}")
    print(f"Internal steps:       {internal_steps:.6g}")
    print(f"Basis degree:         {basis_degree}")
    print(f"Basis size:           {basis_size}")
    print(f"Seed:                 {seed}")
    print(f"Low seed:             {low_seed}")
    print(f"LSMC direct price:    {direct_price:.6f}")
    print(f"LSMC direct error:    {direct_error:.6f}")
    print(f"LSMC low price:       {low_price:.6f}")
    print(f"LSMC low error:       {low_error:.6f}")


if __name__ == "__main__":
    main()
