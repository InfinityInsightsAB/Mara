import numpy as np

# Paper-faithful Heston model inputs from Farahany, Jackson, and Jaimungal (2020).
S0 = 10.0
v0 = 0.15
r = 0.02
kappa = 5.0
theta = 0.16
eta = 0.9
rho = 0.1

# Bermudan put setup from the paper.
option_type = "put"
K = 10.0
T = 1.0
N_ex = 12
M = 1000
N = 500_000
seed = 2026
low_seed = 2103
basis_degree = 3
ridge_lambda = 1e-12
min_regression_points = 20

exercise_indices = np.rint(np.linspace(0.0, M, N_ex + 1)).astype(np.int32)
exercise_indices[0] = 0
exercise_indices[-1] = M
interval_steps = np.diff(exercise_indices)
exercise_times = T * exercise_indices / float(M)

rho_perp = float(np.sqrt(max(1.0 - rho * rho, 0.0)))


def payoff(spot):
    return np.maximum(K - spot, 0.0)


def lsm_basis(spot, v):
    x = spot / K
    y = v / max(v0, 1e-8)
    p = payoff(spot) / K
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


def ridge_regression(x_design, y_target, ridge_value):
    left = x_design.T @ x_design + ridge_value * np.eye(x_design.shape[1])
    right = x_design.T @ y_target
    try:
        return np.linalg.solve(left, right)
    except np.linalg.LinAlgError:
        return np.linalg.lstsq(x_design, y_target, rcond=None)[0]


def simulate_exercise_states(seed_value):
    dt = T / M
    sqrt_dt = np.sqrt(dt)
    rng = np.random.default_rng(seed_value)

    spot = np.empty((N_ex + 1, N), dtype=np.float32)
    v = np.empty((N_ex + 1, N), dtype=np.float32)
    spot_now = np.full(N, S0, dtype=np.float32)
    v_now = np.full(N, v0, dtype=np.float32)
    spot[0] = spot_now
    v[0] = v_now

    for exercise_step, n_small_steps in enumerate(interval_steps, start=1):
        for _ in range(int(n_small_steps)):
            z_perp = rng.standard_normal(N, dtype=np.float32)
            z_v = rng.standard_normal(N, dtype=np.float32)
            v_pos = np.maximum(v_now, 0.0)
            sqrt_v = np.sqrt(v_pos)

            dw_v = sqrt_dt * z_v
            dw_s = sqrt_dt * (rho * z_v + rho_perp * z_perp)

            v_next = v_pos + kappa * (theta - v_pos) * dt
            v_next += eta * sqrt_v * dw_v
            v_now = np.maximum(v_next, 0.0)

            log_move = (r - 0.5 * v_pos) * dt + sqrt_v * dw_s
            spot_now = spot_now * np.exp(log_move)

        spot[exercise_step] = spot_now
        v[exercise_step] = v_now

    return spot, v


def direct_estimator(spot, v):
    cashflow = payoff(spot[-1]).astype(np.float64)
    exercise_index = np.full(N, N_ex, dtype=np.int16)
    coefficients = [None] * (N_ex + 1)

    for step in range(N_ex - 1, 0, -1):
        spot_step = np.asarray(spot[step], dtype=np.float64)
        v_step = np.asarray(v[step], dtype=np.float64)
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

        x_design = lsm_basis(spot_step[in_money], v_step[in_money]).astype(np.float64)
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


def low_estimator(coefficients, seed_value):
    dt = T / M
    sqrt_dt = np.sqrt(dt)
    rng = np.random.default_rng(seed_value)

    spot_now = np.full(N, S0, dtype=np.float32)
    v_now = np.full(N, v0, dtype=np.float32)
    low_cashflow = np.zeros(N, dtype=np.float64)
    alive = np.ones(N, dtype=bool)

    for exercise_step, n_small_steps in enumerate(interval_steps, start=1):
        for _ in range(int(n_small_steps)):
            z_perp = rng.standard_normal(N, dtype=np.float32)
            z_v = rng.standard_normal(N, dtype=np.float32)
            v_pos = np.maximum(v_now, 0.0)
            sqrt_v = np.sqrt(v_pos)

            dw_v = sqrt_dt * z_v
            dw_s = sqrt_dt * (rho * z_v + rho_perp * z_perp)

            v_next = v_pos + kappa * (theta - v_pos) * dt
            v_next += eta * sqrt_v * dw_v
            v_now = np.maximum(v_next, 0.0)

            log_move = (r - 0.5 * v_pos) * dt + sqrt_v * dw_s
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
            continuation = lsm_basis(
                spot_now[candidates].astype(np.float64),
                v_now[candidates].astype(np.float64),
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
    spot, v = simulate_exercise_states(seed)
    direct_price, direct_error, coefficients = direct_estimator(spot, v)
    low_price, low_error = low_estimator(coefficients, low_seed)
    return direct_price, direct_error, low_price, low_error


lsmc_direct_price, lsmc_direct_error, lsmc_low_price, lsmc_low_error = longstaff_schwartz_prices()

print("Longstaff-Schwartz Monte Carlo for a Bermudan put")
print("Model: Heston")
print(f"Option type:          {option_type}")
print(f"Spot:                 {S0:.2f}")
print(f"Strike:               {K:.2f}")
print(f"Maturity:             {T:.2f}")
print(f"Paths:                {N}")
print(f"Exercise dates:       {N_ex}")
print(f"Euler steps:          {M}")
print(f"Basis degree:         {basis_degree}")
print(f"Seed:                 {seed}")
print(f"Low seed:             {low_seed}")
print(f"LSMC direct price:    {lsmc_direct_price:.6f}")
print(f"LSMC direct error:    {lsmc_direct_error:.6f}")
print(f"LSMC low price:       {lsmc_low_price:.6f}")
print(f"LSMC low error:       {lsmc_low_error:.6f}")
