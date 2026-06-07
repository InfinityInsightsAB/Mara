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
N_PATHS = 10_000
N_LOW_PATHS = 10_000
N_ASSET_POINTS = 2 ** 9
LOG_S_MIN = -3.0
LOG_S_MAX = 3.0
BASIS_DEGREE = 3
HERMITE_NODES = 32
SEED = 2026
LOW_SEED = 2103
RIDGE = 1e-12

EXERCISE_INDICES = np.rint(np.linspace(0.0, N_EULER_STEPS, N_EXERCISE_DATES + 1)).astype(np.int32)
EXERCISE_INDICES[0] = 0
EXERCISE_INDICES[-1] = N_EULER_STEPS
INTERVAL_STEPS = np.diff(EXERCISE_INDICES)
EXERCISE_TIMES = MATURITY * EXERCISE_INDICES / float(N_EULER_STEPS)
RHO_PERP_SQ = max(1.0 - RHO * RHO, 0.0)



def payoff(spot):
    return np.maximum(STRIKE - spot, 0.0)



def vol_basis(v):
    y = v / max(V0, 1e-8)
    return np.column_stack([
        np.ones_like(y),
        y,
        y * y,
        y * y * y,
    ])



def ridge_regression(X, y, ridge_lambda):
    left = X.T @ X + ridge_lambda * np.eye(X.shape[1])
    right = X.T @ y
    try:
        return np.linalg.solve(left, right)
    except np.linalg.LinAlgError:
        return np.linalg.lstsq(X, y, rcond=None)[0]



def simulate_full_paths(n_paths, seed):
    dt = MATURITY / N_EULER_STEPS
    sqrt_dt = np.sqrt(dt)
    rng = np.random.default_rng(seed)

    spot = np.empty((N_EXERCISE_DATES + 1, n_paths), dtype=np.float32)
    v = np.empty((N_EXERCISE_DATES + 1, n_paths), dtype=np.float32)
    spot_now = np.full(n_paths, S0, dtype=np.float32)
    v_now = np.full(n_paths, V0, dtype=np.float32)
    spot[0] = spot_now
    v[0] = v_now

    for exercise_step, n_small_steps in enumerate(INTERVAL_STEPS, start=1):
        for _ in range(int(n_small_steps)):
            z_perp = rng.standard_normal(n_paths, dtype=np.float32)
            z_v = rng.standard_normal(n_paths, dtype=np.float32)
            v_pos = np.maximum(v_now, 0.0)
            sqrt_v = np.sqrt(v_pos)
            dw_v = sqrt_dt * z_v
            dw_s = sqrt_dt * (RHO * z_v + np.sqrt(RHO_PERP_SQ) * z_perp)

            v_next = v_pos + KAPPA * (THETA - v_pos) * dt
            v_next += ETA * sqrt_v * dw_v
            v_now = np.maximum(v_next, 0.0)

            log_move = (R - 0.5 * v_pos) * dt + sqrt_v * dw_s
            spot_now = spot_now * np.exp(log_move)

        spot[exercise_step] = spot_now
        v[exercise_step] = v_now

    return spot, v



def simulate_volatility_statistics(n_paths, seed):
    dt = MATURITY / N_EULER_STEPS
    sqrt_dt = np.sqrt(dt)
    rng = np.random.default_rng(seed)

    v_paths = np.empty((N_EXERCISE_DATES + 1, n_paths), dtype=np.float32)
    a_stats = np.empty((N_EXERCISE_DATES, n_paths), dtype=np.float64)
    b_stats = np.empty((N_EXERCISE_DATES, n_paths), dtype=np.float64)
    z_stats = np.empty((N_EXERCISE_DATES, n_paths), dtype=np.float64)

    v_now = np.full(n_paths, V0, dtype=np.float32)
    v_paths[0] = v_now

    for exercise_step, n_small_steps in enumerate(INTERVAL_STEPS):
        a_step = np.zeros(n_paths, dtype=np.float64)
        b_step = np.zeros(n_paths, dtype=np.float64)
        z_step = np.zeros(n_paths, dtype=np.float64)

        for _ in range(int(n_small_steps)):
            z_v = rng.standard_normal(n_paths, dtype=np.float32)
            dw_v = sqrt_dt * z_v
            v_pos = np.maximum(v_now, 0.0)
            sqrt_v = np.sqrt(v_pos)

            a_step += (R - 0.5 * v_pos) * dt
            b_step += RHO_PERP_SQ * v_pos * dt
            z_step += RHO * sqrt_v * dw_v

            v_next = v_pos + KAPPA * (THETA - v_pos) * dt
            v_next += ETA * sqrt_v * dw_v
            v_now = np.maximum(v_next, 0.0)

        v_paths[exercise_step + 1] = v_now
        a_stats[exercise_step] = a_step
        b_stats[exercise_step] = b_step
        z_stats[exercise_step] = z_step

    return v_paths, a_stats, b_stats, z_stats



def build_asset_grid():
    return S0 * np.exp(np.linspace(LOG_S_MIN, LOG_S_MAX, N_ASSET_POINTS))



def conditional_expectation(asset_grid, terminal_values, shift, variance, nodes, weights):
    log_grid = np.log(asset_grid)
    left = float(terminal_values[0])
    right = float(terminal_values[-1])
    if variance <= 1e-14:
        return np.interp(log_grid + shift, log_grid, terminal_values, left=left, right=right)

    out = np.zeros_like(terminal_values, dtype=np.float64)
    moves = shift + np.sqrt(2.0 * variance) * nodes
    for weight, move in zip(weights, moves):
        out += weight * np.interp(log_grid + move, log_grid, terminal_values, left=left, right=right)
    return out



def continuation_from_coefficients(asset_grid, coeff_matrix, spot, v):
    basis = vol_basis(v)
    log_grid = np.log(asset_grid)
    log_spot = np.log(np.clip(spot, asset_grid[0], asset_grid[-1]))
    continuation = np.zeros_like(log_spot, dtype=np.float64)

    for k in range(basis.shape[1]):
        continuation += basis[:, k] * np.interp(log_spot, log_grid, coeff_matrix[:, k])

    return continuation



def hybrid_prices():
    asset_grid = build_asset_grid()
    payoff_grid = payoff(asset_grid).astype(np.float64)
    nodes, weights = np.polynomial.hermite.hermgauss(HERMITE_NODES)
    weights = weights / np.sqrt(np.pi)
    v_paths, a_stats, b_stats, z_stats = simulate_volatility_statistics(N_PATHS, SEED)

    value_next = np.repeat(payoff_grid[None, :], N_PATHS, axis=0)
    coefficient_steps = [None] * (N_EXERCISE_DATES + 1)

    for step in range(N_EXERCISE_DATES - 1, 0, -1):
        discount = np.exp(-R * (EXERCISE_TIMES[step + 1] - EXERCISE_TIMES[step]))
        v_now = np.maximum(v_paths[step], 0.0)
        shift = a_stats[step] + z_stats[step]
        variance = b_stats[step]

        pre_surface = np.empty_like(value_next)
        for path in range(N_PATHS):
            pre_surface[path] = discount * conditional_expectation(
                asset_grid,
                value_next[path],
                float(shift[path]),
                float(variance[path]),
                nodes,
                weights,
            )

        basis_now = vol_basis(v_now).astype(np.float64)
        coefficient_step = np.empty((N_ASSET_POINTS, basis_now.shape[1]), dtype=np.float64)
        completed_surface = np.empty_like(pre_surface)

        for asset_index in range(N_ASSET_POINTS):
            coeff = ridge_regression(basis_now, pre_surface[:, asset_index], RIDGE)
            coefficient_step[asset_index] = coeff
            completed_surface[:, asset_index] = basis_now @ coeff

        value_next = np.maximum(payoff_grid[None, :], completed_surface)
        coefficient_steps[step] = coefficient_step

    discount0 = np.exp(-R * (EXERCISE_TIMES[1] - EXERCISE_TIMES[0]))
    pre_surface0 = np.empty_like(value_next)
    for path in range(N_PATHS):
        pre_surface0[path] = discount0 * conditional_expectation(
            asset_grid,
            value_next[path],
            float(a_stats[0, path] + z_stats[0, path]),
            float(b_stats[0, path]),
            nodes,
            weights,
        )

    direct_values = np.array([
        np.interp(np.log(S0), np.log(asset_grid), pre_surface0[path])
        for path in range(N_PATHS)
    ])
    direct_price = max(float(payoff(S0)), float(np.mean(direct_values)))
    direct_error = float(np.std(direct_values, ddof=1) / np.sqrt(N_PATHS))

    spot_low, v_low = simulate_full_paths(N_LOW_PATHS, LOW_SEED)
    low_cashflow = np.exp(-R * EXERCISE_TIMES[-1]) * payoff(spot_low[-1]).astype(np.float64)
    exercised = np.zeros(N_LOW_PATHS, dtype=bool)

    for step in range(1, N_EXERCISE_DATES):
        exercise_value = payoff(spot_low[step]).astype(np.float64)
        continuation = continuation_from_coefficients(
            asset_grid,
            coefficient_steps[step],
            spot_low[step],
            v_low[step],
        )
        exercise_now = (~exercised) & (exercise_value >= continuation)
        low_cashflow[exercise_now] = np.exp(-R * EXERCISE_TIMES[step]) * exercise_value[exercise_now]
        exercised[exercise_now] = True

    low_price = max(float(payoff(S0)), float(np.mean(low_cashflow)))
    low_error = float(np.std(low_cashflow, ddof=1) / np.sqrt(N_LOW_PATHS))
    return direct_price, direct_error, low_price, low_error


hybrid_direct_price, hybrid_direct_error, hybrid_low_price, hybrid_low_error = hybrid_prices()

print("Hybrid LSMC-PDE for a Bermudan put")
print("Model: Heston")
print(f"Option type:          {OPTION_TYPE}")
print(f"Spot:                 {S0:.2f}")
print(f"Strike:               {STRIKE:.2f}")
print(f"Maturity:             {MATURITY:.2f}")
print(f"Paths:                {N_PATHS}")
print(f"Low paths:            {N_LOW_PATHS}")
print(f"Exercise dates:       {N_EXERCISE_DATES}")
print(f"Euler steps:          {N_EULER_STEPS}")
print(f"Basis degree:         {BASIS_DEGREE}")
print(f"Asset grid points:    {N_ASSET_POINTS}")
print(f"Log-grid min:         {LOG_S_MIN:.1f}")
print(f"Log-grid max:         {LOG_S_MAX:.1f}")
print(f"Hermite nodes:        {HERMITE_NODES}")
print(f"Seed:                 {SEED}")
print(f"Low seed:             {LOW_SEED}")
print(f"Hybrid direct price:  {hybrid_direct_price:.6f}")
print(f"Hybrid direct error:  {hybrid_direct_error:.6f}")
print(f"Hybrid low price:     {hybrid_low_price:.6f}")
print(f"Hybrid low error:     {hybrid_low_error:.6f}")
