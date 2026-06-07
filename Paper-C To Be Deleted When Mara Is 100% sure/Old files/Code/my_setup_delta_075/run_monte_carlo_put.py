import os
import tempfile
from pathlib import Path

import numpy as np

# Model inputs for the generalized Gatheral double mean-reverting model.
S0 = 100.0
v0 = 0.04
vp0 = 0.04
r = 0.03
kappa1 = 2.0
kappa2 = 1.0
theta = 0.04
xi1 = 0.35
xi2 = 0.20
delta1 = 0.75
delta2 = 0.75
rho12 = 0.20
rho13 = 0.10
rho23 = 0.10


def env_int(name, default):
    value = os.environ.get(name)
    if value is None:
        return default
    return int(value)


def env_float(name, default):
    value = os.environ.get(name)
    if value is None:
        return default
    return float(value)


# Bermudan put setup.
option_type = "put"
K = env_float("GDMR_STRIKE", 100.0)
T = 1.0
N = env_int("GDMR_LSMC_PATHS", 1_000_000)
N_ex = env_int("GDMR_EXERCISE_DATES", 100)
M = env_int("GDMR_EULER_STEPS", 600)
seed = env_int("GDMR_LSMC_SEED", 2026)
low_seed = env_int("GDMR_LSMC_LOW_SEED", 2103)
basis_degree = 3
ridge_lambda = 1e-10
min_regression_points = 24

exercise_indices = np.rint(np.linspace(0.0, M, N_ex + 1)).astype(np.int32)
exercise_indices[0] = 0
exercise_indices[-1] = M
interval_steps = np.diff(exercise_indices)
exercise_times = T * exercise_indices / float(M)
internal_steps = M / float(N_ex)

corr = np.array([
    [1.0, rho12, rho13],
    [rho12, 1.0, rho23],
    [rho13, rho23, 1.0],
], dtype=np.float64)
chol = np.linalg.cholesky(corr).astype(np.float32)


def payoff(spot):
    return np.maximum(K - spot, 0.0)


def state_basis(spot, v, vp):
    x = spot / K
    y = v / max(v0, 1e-8)
    z = vp / max(vp0, 1e-8)
    p = payoff(spot) / K
    return np.column_stack([
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
    ])


def ridge_regression(x_design, y_target, ridge_value):
    left = x_design.T @ x_design + ridge_value * np.eye(x_design.shape[1])
    right = x_design.T @ y_target
    try:
        return np.linalg.solve(left, right)
    except np.linalg.LinAlgError:
        return np.linalg.lstsq(x_design, y_target, rcond=None)[0]


def create_store(tmpdir, name, rows, cols):
    path = Path(tmpdir) / f"{name}.dat"
    return np.memmap(path, dtype=np.float32, mode="w+", shape=(rows, cols))


def close_store(store):
    store.flush()
    mmap_object = getattr(store, "_mmap", None)
    if mmap_object is not None:
        mmap_object.close()


def simulate_direct_states(spot_store, v_store, vp_store, seed_value):
    dt = T / M
    sqrt_dt = np.sqrt(dt)
    rng = np.random.default_rng(seed_value)

    spot_now = np.full(N, S0, dtype=np.float32)
    v_now = np.full(N, v0, dtype=np.float32)
    vp_now = np.full(N, vp0, dtype=np.float32)

    spot_store[0] = spot_now
    v_store[0] = v_now
    vp_store[0] = vp_now

    for exercise_step, n_small_steps in enumerate(interval_steps, start=1):
        for _ in range(int(n_small_steps)):
            Z = rng.standard_normal((N, 3), dtype=np.float32) @ chol.T
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

        spot_store[exercise_step] = spot_now
        v_store[exercise_step] = v_now
        vp_store[exercise_step] = vp_now

    spot_store.flush()
    v_store.flush()
    vp_store.flush()


def direct_estimator_from_store(spot_store, v_store, vp_store):
    cashflow = payoff(spot_store[-1]).astype(np.float64)
    exercise_index = np.full(N, N_ex, dtype=np.int16)
    coefficients = [None] * (N_ex + 1)

    for step in range(N_ex - 1, 0, -1):
        spot_step = np.asarray(spot_store[step], dtype=np.float64)
        v_step = np.asarray(v_store[step], dtype=np.float64)
        vp_step = np.asarray(vp_store[step], dtype=np.float64)
        exercise_value = payoff(spot_step).astype(np.float64)
        alive = exercise_index > step
        in_money = alive & (exercise_value > 0.0)
        if not np.any(in_money):
            continue

        in_money_index = np.where(in_money)[0]
        if in_money_index.size < min_regression_points:
            cashflow[in_money_index] = exercise_value[in_money_index]
            exercise_index[in_money_index] = step
            coefficients[step] = None
            continue

        x_design = state_basis(
            spot_step[in_money],
            v_step[in_money],
            vp_step[in_money],
        ).astype(np.float64)
        y_target = np.exp(-r * (exercise_times[exercise_index[in_money]] - exercise_times[step])) * cashflow[in_money]
        coeff = ridge_regression(x_design, y_target, ridge_lambda)
        continuation = x_design @ coeff
        exercise_now = exercise_value[in_money] >= continuation
        chosen = in_money_index[exercise_now]
        cashflow[chosen] = exercise_value[chosen]
        exercise_index[chosen] = step
        coefficients[step] = coeff

    discounted_cashflow = np.exp(-r * exercise_times[exercise_index]) * cashflow
    direct_price = max(float(payoff(S0)), float(np.mean(discounted_cashflow)))
    direct_error = float(np.std(discounted_cashflow, ddof=1) / np.sqrt(N))
    return direct_price, direct_error, coefficients


def low_estimator_from_coefficients(coefficients, seed_value):
    dt = T / M
    sqrt_dt = np.sqrt(dt)
    rng = np.random.default_rng(seed_value)

    spot_now = np.full(N, S0, dtype=np.float32)
    v_now = np.full(N, v0, dtype=np.float32)
    vp_now = np.full(N, vp0, dtype=np.float32)

    low_cashflow = np.zeros(N, dtype=np.float64)
    alive = np.ones(N, dtype=bool)

    for exercise_step, n_small_steps in enumerate(interval_steps, start=1):
        for _ in range(int(n_small_steps)):
            Z = rng.standard_normal((N, 3), dtype=np.float32) @ chol.T
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

        if exercise_step == N_ex:
            low_cashflow[alive] = np.exp(-r * exercise_times[exercise_step]) * payoff(spot_now[alive])
            break

        exercise_value = payoff(spot_now).astype(np.float64)
        candidates = alive & (exercise_value > 0.0)
        if not np.any(candidates):
            continue

        coeff = coefficients[exercise_step]
        if coeff is None:
            continuation = np.zeros(np.count_nonzero(candidates), dtype=np.float64)
        else:
            continuation = state_basis(
                spot_now[candidates].astype(np.float64),
                v_now[candidates].astype(np.float64),
                vp_now[candidates].astype(np.float64),
            ).astype(np.float64) @ coeff

        candidate_index = np.where(candidates)[0]
        exercise_now = exercise_value[candidates] >= continuation
        chosen = candidate_index[exercise_now]
        low_cashflow[chosen] = np.exp(-r * exercise_times[exercise_step]) * exercise_value[chosen]
        alive[chosen] = False

    low_price = max(float(payoff(S0)), float(np.mean(low_cashflow)))
    low_error = float(np.std(low_cashflow, ddof=1) / np.sqrt(N))
    return low_price, low_error


def longstaff_schwartz_prices():
    with tempfile.TemporaryDirectory(prefix="gdmr_lsmc_") as tmpdir:
        spot_store = create_store(tmpdir, "spot", N_ex + 1, N)
        v_store = create_store(tmpdir, "v", N_ex + 1, N)
        vp_store = create_store(tmpdir, "vp", N_ex + 1, N)
        try:
            simulate_direct_states(spot_store, v_store, vp_store, seed)
            direct_price, direct_error, coefficients = direct_estimator_from_store(spot_store, v_store, vp_store)
            low_price, low_error = low_estimator_from_coefficients(coefficients, low_seed)
        finally:
            close_store(spot_store)
            close_store(v_store)
            close_store(vp_store)
            del spot_store, v_store, vp_store
    return direct_price, direct_error, low_price, low_error


lsmc_direct_price, lsmc_direct_error, lsmc_low_price, lsmc_low_error = longstaff_schwartz_prices()

print("Longstaff-Schwartz Monte Carlo for a Bermudan put")
print("Model: generalized Gatheral double mean-reverting (gDMR)")
print(f"Option type:          {option_type}")
print(f"Spot:                 {S0:.2f}")
print(f"Strike:               {K:.2f}")
print(f"Maturity:             {T:.2f}")
print(f"delta1:               {delta1:.2f}")
print(f"delta2:               {delta2:.2f}")
print(f"Paths:                {N}")
print(f"Exercise dates:       {N_ex}")
print(f"Euler steps:          {M}")
print(f"Internal steps:       {internal_steps:.6g}")
print(f"Basis degree:         {basis_degree}")
print(f"Basis size:           {state_basis(np.array([S0]), np.array([v0]), np.array([vp0])).shape[1]}")
print(f"Seed:                 {seed}")
print(f"Low seed:             {low_seed}")
print(f"LSMC direct price:    {lsmc_direct_price:.6f}")
print(f"LSMC direct error:    {lsmc_direct_error:.6f}")
print(f"LSMC low price:       {lsmc_low_price:.6f}")
print(f"LSMC low error:       {lsmc_low_error:.6f}")
