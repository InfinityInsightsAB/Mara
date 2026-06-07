import os
import tempfile
from pathlib import Path

import numpy as np

# Model inputs for the generalized Gatheral double mean-reverting model.
S0 = 100.0
V0 = 0.04
VP0 = 0.04
R = 0.03
KAPPA1 = 2.0
KAPPA2 = 1.0
THETA = 0.04
XI1 = 0.35
XI2 = 0.20
DELTA1 = 0.5
DELTA2 = 0.5
RHO12 = 0.20
RHO13 = 0.10
RHO23 = 0.10


def env_int(name, default):
    value = os.environ.get(name)
    if value is None:
        return default
    return int(value)


# Bermudan put setup.
OPTION_TYPE = "put"
STRIKE = 100.0
MATURITY = 1.0
N_PATHS = env_int("GDMR_LSMC_PATHS", 1_000_000)
N_EXERCISE_DATES = env_int("GDMR_EXERCISE_DATES", 100)
N_EULER_STEPS = env_int("GDMR_EULER_STEPS", 600)
SEED = env_int("GDMR_LSMC_SEED", 2026)
LOW_SEED = env_int("GDMR_LSMC_LOW_SEED", 2103)
BASIS_DEGREE = 3
RIDGE = 1e-10
MIN_REGRESSION_POINTS = 24

EXERCISE_INDICES = np.rint(np.linspace(0.0, N_EULER_STEPS, N_EXERCISE_DATES + 1)).astype(np.int32)
EXERCISE_INDICES[0] = 0
EXERCISE_INDICES[-1] = N_EULER_STEPS
INTERVAL_STEPS = np.diff(EXERCISE_INDICES)
EXERCISE_TIMES = MATURITY * EXERCISE_INDICES / float(N_EULER_STEPS)
INTERNAL_STEPS = N_EULER_STEPS / float(N_EXERCISE_DATES)

CORR = np.array([
    [1.0, RHO12, RHO13],
    [RHO12, 1.0, RHO23],
    [RHO13, RHO23, 1.0],
], dtype=np.float64)
CHOL = np.linalg.cholesky(CORR).astype(np.float32)


def payoff(spot):
    return np.maximum(STRIKE - spot, 0.0)


def state_basis(spot, v, vp):
    x = spot / STRIKE
    y = v / max(V0, 1e-8)
    z = vp / max(VP0, 1e-8)
    p = payoff(spot) / STRIKE
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


def ridge_regression(X, y, ridge_lambda):
    left = X.T @ X + ridge_lambda * np.eye(X.shape[1])
    right = X.T @ y
    try:
        return np.linalg.solve(left, right)
    except np.linalg.LinAlgError:
        return np.linalg.lstsq(X, y, rcond=None)[0]


def create_store(tmpdir, name, rows, cols):
    path = Path(tmpdir) / f"{name}.dat"
    return np.memmap(path, dtype=np.float32, mode="w+", shape=(rows, cols))


def close_store(store):
    store.flush()
    mmap_object = getattr(store, "_mmap", None)
    if mmap_object is not None:
        mmap_object.close()


def simulate_direct_states(spot_store, v_store, vp_store, seed):
    dt = MATURITY / N_EULER_STEPS
    sqrt_dt = np.sqrt(dt)
    rng = np.random.default_rng(seed)

    spot_now = np.full(N_PATHS, S0, dtype=np.float32)
    v_now = np.full(N_PATHS, V0, dtype=np.float32)
    vp_now = np.full(N_PATHS, VP0, dtype=np.float32)

    spot_store[0] = spot_now
    v_store[0] = v_now
    vp_store[0] = vp_now

    for exercise_step, n_small_steps in enumerate(INTERVAL_STEPS, start=1):
        for _ in range(int(n_small_steps)):
            shocks = rng.standard_normal((N_PATHS, 3), dtype=np.float32) @ CHOL.T
            z1 = shocks[:, 0]
            z2 = shocks[:, 1]
            z3 = shocks[:, 2]
            v_pos = np.maximum(v_now, 0.0)
            vp_pos = np.maximum(vp_now, 0.0)

            vp_next = vp_pos + KAPPA2 * (THETA - vp_pos) * dt
            vp_next += XI2 * np.power(vp_pos, DELTA2) * sqrt_dt * z3
            vp_now = np.maximum(vp_next, 0.0)

            v_next = v_pos + KAPPA1 * (vp_pos - v_pos) * dt
            v_next += XI1 * np.power(v_pos, DELTA1) * sqrt_dt * z2
            v_now = np.maximum(v_next, 0.0)

            log_move = (R - 0.5 * v_pos) * dt + np.sqrt(v_pos) * sqrt_dt * z1
            spot_now = spot_now * np.exp(log_move)

        spot_store[exercise_step] = spot_now
        v_store[exercise_step] = v_now
        vp_store[exercise_step] = vp_now

    spot_store.flush()
    v_store.flush()
    vp_store.flush()


def direct_estimator_from_store(spot_store, v_store, vp_store):
    cashflow = payoff(spot_store[-1]).astype(np.float64)
    exercise_index = np.full(N_PATHS, N_EXERCISE_DATES, dtype=np.int16)
    coefficients = [None] * (N_EXERCISE_DATES + 1)

    for step in range(N_EXERCISE_DATES - 1, 0, -1):
        spot_step = np.asarray(spot_store[step], dtype=np.float64)
        v_step = np.asarray(v_store[step], dtype=np.float64)
        vp_step = np.asarray(vp_store[step], dtype=np.float64)
        exercise_value = payoff(spot_step).astype(np.float64)
        alive = exercise_index > step
        in_money = alive & (exercise_value > 0.0)
        if not np.any(in_money):
            continue

        in_money_index = np.where(in_money)[0]
        if in_money_index.size < MIN_REGRESSION_POINTS:
            cashflow[in_money_index] = exercise_value[in_money_index]
            exercise_index[in_money_index] = step
            coefficients[step] = None
            continue

        X = state_basis(
            spot_step[in_money],
            v_step[in_money],
            vp_step[in_money],
        ).astype(np.float64)
        Y = np.exp(-R * (EXERCISE_TIMES[exercise_index[in_money]] - EXERCISE_TIMES[step])) * cashflow[in_money]
        coeff = ridge_regression(X, Y, RIDGE)
        continuation = X @ coeff
        exercise_now = exercise_value[in_money] >= continuation
        chosen = in_money_index[exercise_now]
        cashflow[chosen] = exercise_value[chosen]
        exercise_index[chosen] = step
        coefficients[step] = coeff

    discounted_cashflow = np.exp(-R * EXERCISE_TIMES[exercise_index]) * cashflow
    direct_price = max(float(payoff(S0)), float(np.mean(discounted_cashflow)))
    direct_error = float(np.std(discounted_cashflow, ddof=1) / np.sqrt(N_PATHS))
    return direct_price, direct_error, coefficients


def low_estimator_from_coefficients(coefficients, seed):
    dt = MATURITY / N_EULER_STEPS
    sqrt_dt = np.sqrt(dt)
    rng = np.random.default_rng(seed)

    spot_now = np.full(N_PATHS, S0, dtype=np.float32)
    v_now = np.full(N_PATHS, V0, dtype=np.float32)
    vp_now = np.full(N_PATHS, VP0, dtype=np.float32)

    low_cashflow = np.zeros(N_PATHS, dtype=np.float64)
    alive = np.ones(N_PATHS, dtype=bool)

    for exercise_step, n_small_steps in enumerate(INTERVAL_STEPS, start=1):
        for _ in range(int(n_small_steps)):
            shocks = rng.standard_normal((N_PATHS, 3), dtype=np.float32) @ CHOL.T
            z1 = shocks[:, 0]
            z2 = shocks[:, 1]
            z3 = shocks[:, 2]
            v_pos = np.maximum(v_now, 0.0)
            vp_pos = np.maximum(vp_now, 0.0)

            vp_next = vp_pos + KAPPA2 * (THETA - vp_pos) * dt
            vp_next += XI2 * np.power(vp_pos, DELTA2) * sqrt_dt * z3
            vp_now = np.maximum(vp_next, 0.0)

            v_next = v_pos + KAPPA1 * (vp_pos - v_pos) * dt
            v_next += XI1 * np.power(v_pos, DELTA1) * sqrt_dt * z2
            v_now = np.maximum(v_next, 0.0)

            log_move = (R - 0.5 * v_pos) * dt + np.sqrt(v_pos) * sqrt_dt * z1
            spot_now = spot_now * np.exp(log_move)

        if exercise_step == N_EXERCISE_DATES:
            low_cashflow[alive] = np.exp(-R * EXERCISE_TIMES[exercise_step]) * payoff(spot_now[alive])
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
        low_cashflow[chosen] = np.exp(-R * EXERCISE_TIMES[exercise_step]) * exercise_value[chosen]
        alive[chosen] = False

    low_price = max(float(payoff(S0)), float(np.mean(low_cashflow)))
    low_error = float(np.std(low_cashflow, ddof=1) / np.sqrt(N_PATHS))
    return low_price, low_error


def longstaff_schwartz_prices():
    with tempfile.TemporaryDirectory(prefix="gdmr_lsmc_") as tmpdir:
        spot_store = create_store(tmpdir, "spot", N_EXERCISE_DATES + 1, N_PATHS)
        v_store = create_store(tmpdir, "v", N_EXERCISE_DATES + 1, N_PATHS)
        vp_store = create_store(tmpdir, "vp", N_EXERCISE_DATES + 1, N_PATHS)
        try:
            simulate_direct_states(spot_store, v_store, vp_store, SEED)
            direct_price, direct_error, coefficients = direct_estimator_from_store(spot_store, v_store, vp_store)
            low_price, low_error = low_estimator_from_coefficients(coefficients, LOW_SEED)
        finally:
            close_store(spot_store)
            close_store(v_store)
            close_store(vp_store)
            del spot_store, v_store, vp_store
    return direct_price, direct_error, low_price, low_error


lsmc_direct_price, lsmc_direct_error, lsmc_low_price, lsmc_low_error = longstaff_schwartz_prices()

print("Longstaff-Schwartz Monte Carlo for a Bermudan put")
print("Model: generalized Gatheral double mean-reverting (gDMR)")
print(f"Option type:          {OPTION_TYPE}")
print(f"Spot:                 {S0:.2f}")
print(f"Strike:               {STRIKE:.2f}")
print(f"Maturity:             {MATURITY:.2f}")
print(f"Paths:                {N_PATHS}")
print(f"Exercise dates:       {N_EXERCISE_DATES}")
print(f"Euler steps:          {N_EULER_STEPS}")
print(f"Internal steps:       {INTERNAL_STEPS:.6g}")
print(f"Basis degree:         {BASIS_DEGREE}")
print(f"Basis size:           {state_basis(np.array([S0]), np.array([V0]), np.array([VP0])).shape[1]}")
print(f"Seed:                 {SEED}")
print(f"Low seed:             {LOW_SEED}")
print(f"LSMC direct price:    {lsmc_direct_price:.6f}")
print(f"LSMC direct error:    {lsmc_direct_error:.6f}")
print(f"LSMC low price:       {lsmc_low_price:.6f}")
print(f"LSMC low error:       {lsmc_low_error:.6f}")
