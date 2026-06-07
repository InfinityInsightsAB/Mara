import numpy as np

# Paper-faithful Heston model inputs from Farahany, Jackson, and Jaimungal (2020).
S0 = 10.0
V0 = 0.15
R = 0.02
KAPPA = 5.0
THETA = 0.16
ETA = 0.9
RHO = 0.1

# Bermudan put setup from the paper.
OPTION_TYPE = "put"
STRIKE = 10.0
MATURITY = 1.0
N_EXERCISE_DATES = 12
N_EULER_STEPS = 1000
N_PATHS = 500_000
SEED = 2026
LOW_SEED = 2103
BASIS_DEGREE = 3
RIDGE = 1e-12
MIN_REGRESSION_POINTS = 20

EXERCISE_INDICES = np.rint(np.linspace(0.0, N_EULER_STEPS, N_EXERCISE_DATES + 1)).astype(np.int32)
EXERCISE_INDICES[0] = 0
EXERCISE_INDICES[-1] = N_EULER_STEPS
INTERVAL_STEPS = np.diff(EXERCISE_INDICES)
EXERCISE_TIMES = MATURITY * EXERCISE_INDICES / float(N_EULER_STEPS)

RHO_PERP = float(np.sqrt(max(1.0 - RHO * RHO, 0.0)))



def payoff(spot):
    return np.maximum(STRIKE - spot, 0.0)



def lsm_basis(spot, v):
    x = spot / STRIKE
    y = v / max(V0, 1e-8)
    p = payoff(spot) / STRIKE
    return np.column_stack([
        np.ones_like(x),
        x,
        y,
        x * x,
        x * y,
        y * y,
        x * x * x,
        x * x * y,
        x * y * y,
        y * y * y,
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



def simulate_exercise_states(seed):
    dt = MATURITY / N_EULER_STEPS
    sqrt_dt = np.sqrt(dt)
    rng = np.random.default_rng(seed)

    spot = np.empty((N_EXERCISE_DATES + 1, N_PATHS), dtype=np.float32)
    v = np.empty((N_EXERCISE_DATES + 1, N_PATHS), dtype=np.float32)
    spot_now = np.full(N_PATHS, S0, dtype=np.float32)
    v_now = np.full(N_PATHS, V0, dtype=np.float32)
    spot[0] = spot_now
    v[0] = v_now

    for exercise_step, n_small_steps in enumerate(INTERVAL_STEPS, start=1):
        for _ in range(int(n_small_steps)):
            z_perp = rng.standard_normal(N_PATHS, dtype=np.float32)
            z_v = rng.standard_normal(N_PATHS, dtype=np.float32)
            v_pos = np.maximum(v_now, 0.0)
            sqrt_v = np.sqrt(v_pos)

            dw_v = sqrt_dt * z_v
            dw_s = sqrt_dt * (RHO * z_v + RHO_PERP * z_perp)

            v_next = v_pos + KAPPA * (THETA - v_pos) * dt
            v_next += ETA * sqrt_v * dw_v
            v_now = np.maximum(v_next, 0.0)

            log_move = (R - 0.5 * v_pos) * dt + sqrt_v * dw_s
            spot_now = spot_now * np.exp(log_move)

        spot[exercise_step] = spot_now
        v[exercise_step] = v_now

    return spot, v



def direct_estimator(spot, v):
    cashflow = payoff(spot[-1]).astype(np.float64)
    exercise_index = np.full(N_PATHS, N_EXERCISE_DATES, dtype=np.int16)
    coefficients = [None] * (N_EXERCISE_DATES + 1)

    for step in range(N_EXERCISE_DATES - 1, 0, -1):
        spot_step = np.asarray(spot[step], dtype=np.float64)
        v_step = np.asarray(v[step], dtype=np.float64)
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

        X = lsm_basis(spot_step[in_money], v_step[in_money]).astype(np.float64)
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



def low_estimator(coefficients, seed):
    dt = MATURITY / N_EULER_STEPS
    sqrt_dt = np.sqrt(dt)
    rng = np.random.default_rng(seed)

    spot_now = np.full(N_PATHS, S0, dtype=np.float32)
    v_now = np.full(N_PATHS, V0, dtype=np.float32)
    low_cashflow = np.zeros(N_PATHS, dtype=np.float64)
    alive = np.ones(N_PATHS, dtype=bool)

    for exercise_step, n_small_steps in enumerate(INTERVAL_STEPS, start=1):
        for _ in range(int(n_small_steps)):
            z_perp = rng.standard_normal(N_PATHS, dtype=np.float32)
            z_v = rng.standard_normal(N_PATHS, dtype=np.float32)
            v_pos = np.maximum(v_now, 0.0)
            sqrt_v = np.sqrt(v_pos)

            dw_v = sqrt_dt * z_v
            dw_s = sqrt_dt * (RHO * z_v + RHO_PERP * z_perp)

            v_next = v_pos + KAPPA * (THETA - v_pos) * dt
            v_next += ETA * sqrt_v * dw_v
            v_now = np.maximum(v_next, 0.0)

            log_move = (R - 0.5 * v_pos) * dt + sqrt_v * dw_s
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
            continuation = lsm_basis(
                spot_now[candidates].astype(np.float64),
                v_now[candidates].astype(np.float64),
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
    spot, v = simulate_exercise_states(SEED)
    direct_price, direct_error, coefficients = direct_estimator(spot, v)
    low_price, low_error = low_estimator(coefficients, LOW_SEED)
    return direct_price, direct_error, low_price, low_error


lsmc_direct_price, lsmc_direct_error, lsmc_low_price, lsmc_low_error = longstaff_schwartz_prices()

print("Longstaff-Schwartz Monte Carlo for a Bermudan put")
print("Model: Heston")
print(f"Option type:          {OPTION_TYPE}")
print(f"Spot:                 {S0:.2f}")
print(f"Strike:               {STRIKE:.2f}")
print(f"Maturity:             {MATURITY:.2f}")
print(f"Paths:                {N_PATHS}")
print(f"Exercise dates:       {N_EXERCISE_DATES}")
print(f"Euler steps:          {N_EULER_STEPS}")
print(f"Basis degree:         {BASIS_DEGREE}")
print(f"Seed:                 {SEED}")
print(f"Low seed:             {LOW_SEED}")
print(f"LSMC direct price:    {lsmc_direct_price:.6f}")
print(f"LSMC direct error:    {lsmc_direct_error:.6f}")
print(f"LSMC low price:       {lsmc_low_price:.6f}")
print(f"LSMC low error:       {lsmc_low_error:.6f}")
