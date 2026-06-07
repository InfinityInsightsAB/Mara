import os

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


def env_float(name, default):
    value = os.environ.get(name)
    if value is None:
        return default
    return float(value)


# Bermudan put setup.
OPTION_TYPE = "put"
STRIKE = 100.0
MATURITY = 1.0
N_PATHS = env_int("GDMR_HYBRID_PATHS", 20_000)
N_LOW_PATHS = env_int("GDMR_HYBRID_LOW_PATHS", 20_000)
N_EXERCISE_DATES = env_int("GDMR_EXERCISE_DATES", 100)
N_EULER_STEPS = env_int("GDMR_EULER_STEPS", 600)
N_ASSET_POINTS = env_int("GDMR_HYBRID_ASSET_POINTS", 161)
HERMITE_NODES = env_int("GDMR_HYBRID_HERMITE_NODES", 48)
ASSET_LOW_FACTOR = env_float("GDMR_HYBRID_ASSET_LOW_FACTOR", 0.35)
ASSET_HIGH_FACTOR = env_float("GDMR_HYBRID_ASSET_HIGH_FACTOR", 3.00)
VOL_TRUNCATION_QUANTILE = env_float("GDMR_HYBRID_VOL_QUANTILE", 0.995)
SEED = env_int("GDMR_HYBRID_SEED", 2026)
LOW_SEED = env_int("GDMR_HYBRID_LOW_SEED", 2103)
VOL_BASIS_DEGREE = 3
RIDGE = 1e-10

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
CORR23 = np.array([
    [1.0, RHO23],
    [RHO23, 1.0],
], dtype=np.float64)
CHOL23 = np.linalg.cholesky(CORR23).astype(np.float32)


def payoff(spot):
    return np.maximum(STRIKE - spot, 0.0)


def projection_coefficients():
    beta2 = (RHO12 - RHO13 * RHO23) / (1.0 - RHO23 ** 2)
    beta3 = (RHO13 - RHO12 * RHO23) / (1.0 - RHO23 ** 2)
    sigma_perp_sq = (
        1.0 - RHO12 ** 2 - RHO13 ** 2 - RHO23 ** 2 + 2.0 * RHO12 * RHO13 * RHO23
    ) / (1.0 - RHO23 ** 2)
    return beta2, beta3, max(float(sigma_perp_sq), 0.0)


def vol_basis(v, vp, v_cap, vp_cap):
    inside = ((v >= 0.0) & (v <= v_cap) & (vp >= 0.0) & (vp <= vp_cap)).astype(np.float64)
    y = np.clip(v, 0.0, v_cap) / max(v_cap, 1e-8)
    z = np.clip(vp, 0.0, vp_cap) / max(vp_cap, 1e-8)
    return np.column_stack([
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
    vp = np.empty((N_EXERCISE_DATES + 1, n_paths), dtype=np.float32)
    spot_now = np.full(n_paths, S0, dtype=np.float32)
    v_now = np.full(n_paths, V0, dtype=np.float32)
    vp_now = np.full(n_paths, VP0, dtype=np.float32)
    spot[0] = spot_now
    v[0] = v_now
    vp[0] = vp_now

    for exercise_step, n_small_steps in enumerate(INTERVAL_STEPS, start=1):
        for _ in range(int(n_small_steps)):
            shocks = rng.standard_normal((n_paths, 3), dtype=np.float32) @ CHOL.T
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

        spot[exercise_step] = spot_now
        v[exercise_step] = v_now
        vp[exercise_step] = vp_now

    return spot, v, vp


def simulate_volatility_statistics(n_paths, seed, beta2, beta3, sigma_perp_sq):
    dt = MATURITY / N_EULER_STEPS
    sqrt_dt = np.sqrt(dt)
    rng = np.random.default_rng(seed)

    v_paths = np.empty((N_EXERCISE_DATES + 1, n_paths), dtype=np.float32)
    vp_paths = np.empty((N_EXERCISE_DATES + 1, n_paths), dtype=np.float32)
    a_stats = np.empty((N_EXERCISE_DATES, n_paths), dtype=np.float64)
    b_stats = np.empty((N_EXERCISE_DATES, n_paths), dtype=np.float64)
    z_stats = np.empty((N_EXERCISE_DATES, n_paths), dtype=np.float64)

    v_now = np.full(n_paths, V0, dtype=np.float32)
    vp_now = np.full(n_paths, VP0, dtype=np.float32)
    v_paths[0] = v_now
    vp_paths[0] = vp_now

    for exercise_step, n_small_steps in enumerate(INTERVAL_STEPS):
        a_step = np.zeros(n_paths, dtype=np.float64)
        b_step = np.zeros(n_paths, dtype=np.float64)
        z_step = np.zeros(n_paths, dtype=np.float64)

        for _ in range(int(n_small_steps)):
            shocks23 = rng.standard_normal((n_paths, 2), dtype=np.float32) @ CHOL23.T
            z2 = shocks23[:, 0]
            z3 = shocks23[:, 1]
            dw2 = sqrt_dt * z2
            dw3 = sqrt_dt * z3
            v_pos = np.maximum(v_now, 0.0)
            vp_pos = np.maximum(vp_now, 0.0)
            sqrt_v = np.sqrt(v_pos)

            a_step += (R - 0.5 * v_pos) * dt
            b_step += sigma_perp_sq * v_pos * dt
            z_step += sqrt_v * (beta2 * dw2 + beta3 * dw3)

            vp_next = vp_pos + KAPPA2 * (THETA - vp_pos) * dt
            vp_next += XI2 * np.power(vp_pos, DELTA2) * dw3
            vp_now = np.maximum(vp_next, 0.0)

            v_next = v_pos + KAPPA1 * (vp_pos - v_pos) * dt
            v_next += XI1 * np.power(v_pos, DELTA1) * dw2
            v_now = np.maximum(v_next, 0.0)

        v_paths[exercise_step + 1] = v_now
        vp_paths[exercise_step + 1] = vp_now
        a_stats[exercise_step] = a_step
        b_stats[exercise_step] = b_step
        z_stats[exercise_step] = z_step

    return v_paths, vp_paths, a_stats, b_stats, z_stats


def truncation_caps(v_paths, vp_paths):
    v_cap = float(np.quantile(v_paths, VOL_TRUNCATION_QUANTILE))
    vp_cap = float(np.quantile(vp_paths, VOL_TRUNCATION_QUANTILE))
    return max(v_cap, V0), max(vp_cap, VP0)


def build_asset_grid():
    low = max(S0 * ASSET_LOW_FACTOR, 0.25 * STRIKE * ASSET_LOW_FACTOR)
    high = max(S0, STRIKE) * ASSET_HIGH_FACTOR
    return np.exp(np.linspace(np.log(low), np.log(high), N_ASSET_POINTS))


def conditional_expectation(log_grid, terminal_values, shift, variance, nodes, weights):
    left = float(terminal_values[0])
    right = float(terminal_values[-1])
    if variance <= 1e-14:
        return np.interp(log_grid + shift, log_grid, terminal_values, left=left, right=right)

    out = np.zeros_like(terminal_values, dtype=np.float64)
    moves = shift + np.sqrt(2.0 * variance) * nodes
    for weight, move in zip(weights, moves):
        out += weight * np.interp(log_grid + move, log_grid, terminal_values, left=left, right=right)
    return out


def interpolation_weights(log_grid, log_spot):
    upper = int(np.searchsorted(log_grid, log_spot, side="right"))
    if upper <= 0:
        return 0, 0, 1.0, 0.0
    if upper >= log_grid.size:
        last = log_grid.size - 1
        return last, last, 1.0, 0.0
    lower = upper - 1
    left = log_grid[lower]
    right = log_grid[upper]
    if right <= left:
        return lower, upper, 1.0, 0.0
    weight_upper = (log_spot - left) / (right - left)
    weight_lower = 1.0 - weight_upper
    return lower, upper, weight_lower, weight_upper


def continuation_from_coefficients(asset_grid, coeff_matrix, spot, v, vp, v_cap, vp_cap):
    basis = vol_basis(v, vp, v_cap, vp_cap)
    log_grid = np.log(asset_grid)
    log_spot = np.log(np.clip(spot, asset_grid[0], asset_grid[-1]))
    continuation = np.zeros_like(log_spot, dtype=np.float64)

    for k in range(basis.shape[1]):
        continuation += basis[:, k] * np.interp(log_spot, log_grid, coeff_matrix[:, k])

    return continuation


def hybrid_prices():
    beta2, beta3, sigma_perp_sq = projection_coefficients()
    asset_grid = build_asset_grid()
    log_asset_grid = np.log(asset_grid)
    payoff_grid = payoff(asset_grid).astype(np.float64)
    nodes, weights = np.polynomial.hermite.hermgauss(HERMITE_NODES)
    weights = weights / np.sqrt(np.pi)
    v_paths, vp_paths, a_stats, b_stats, z_stats = simulate_volatility_statistics(
        N_PATHS,
        SEED,
        beta2,
        beta3,
        sigma_perp_sq,
    )
    v_cap, vp_cap = truncation_caps(v_paths, vp_paths)

    value_next = np.repeat(payoff_grid[None, :], N_PATHS, axis=0)
    coefficient_steps = [None] * (N_EXERCISE_DATES + 1)

    for step in range(N_EXERCISE_DATES - 1, 0, -1):
        discount = np.exp(-R * (EXERCISE_TIMES[step + 1] - EXERCISE_TIMES[step]))
        v_now = np.maximum(v_paths[step], 0.0)
        vp_now = np.maximum(vp_paths[step], 0.0)
        shift = a_stats[step] + z_stats[step]
        variance = b_stats[step]

        pre_surface = np.empty_like(value_next)
        for path in range(N_PATHS):
            pre_surface[path] = discount * conditional_expectation(
                log_asset_grid,
                value_next[path],
                float(shift[path]),
                float(variance[path]),
                nodes,
                weights,
            )

        basis_now = vol_basis(v_now, vp_now, v_cap, vp_cap).astype(np.float64)
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
            log_asset_grid,
            value_next[path],
            float(a_stats[0, path] + z_stats[0, path]),
            float(b_stats[0, path]),
            nodes,
            weights,
        )

    log_s0 = np.log(S0)
    lower, upper, weight_lower, weight_upper = interpolation_weights(log_asset_grid, log_s0)
    direct_values = weight_lower * pre_surface0[:, lower] + weight_upper * pre_surface0[:, upper]
    direct_price = max(float(payoff(S0)), float(np.mean(direct_values)))
    direct_error = float(np.std(direct_values, ddof=1) / np.sqrt(N_PATHS))

    spot_low, v_low, vp_low = simulate_full_paths(N_LOW_PATHS, LOW_SEED)
    low_cashflow = np.exp(-R * EXERCISE_TIMES[-1]) * payoff(spot_low[-1]).astype(np.float64)
    exercised = np.zeros(N_LOW_PATHS, dtype=bool)

    for step in range(1, N_EXERCISE_DATES):
        exercise_value = payoff(spot_low[step]).astype(np.float64)
        continuation = continuation_from_coefficients(
            asset_grid,
            coefficient_steps[step],
            spot_low[step],
            v_low[step],
            vp_low[step],
            v_cap,
            vp_cap,
        )
        exercise_now = (~exercised) & (exercise_value >= continuation)
        low_cashflow[exercise_now] = np.exp(-R * EXERCISE_TIMES[step]) * exercise_value[exercise_now]
        exercised[exercise_now] = True

    low_price = max(float(payoff(S0)), float(np.mean(low_cashflow)))
    low_error = float(np.std(low_cashflow, ddof=1) / np.sqrt(N_LOW_PATHS))
    return direct_price, direct_error, low_price, low_error, v_cap, vp_cap


hybrid_direct_price, hybrid_direct_error, hybrid_low_price, hybrid_low_error, v_trunc_cap, vp_trunc_cap = hybrid_prices()

print("Hybrid LSMC-PDE for a Bermudan put")
print("Model: generalized Gatheral double mean-reverting (gDMR)")
print(f"Option type:          {OPTION_TYPE}")
print(f"Spot:                 {S0:.2f}")
print(f"Strike:               {STRIKE:.2f}")
print(f"Maturity:             {MATURITY:.2f}")
print(f"Paths:                {N_PATHS}")
print(f"Low paths:            {N_LOW_PATHS}")
print(f"Exercise dates:       {N_EXERCISE_DATES}")
print(f"Euler steps:          {N_EULER_STEPS}")
print(f"Internal steps:       {INTERNAL_STEPS:.6g}")
print(f"Asset grid points:    {N_ASSET_POINTS}")
print(f"Asset low factor:     {ASSET_LOW_FACTOR:.4f}")
print(f"Asset high factor:    {ASSET_HIGH_FACTOR:.4f}")
print(f"Hermite nodes:        {HERMITE_NODES}")
print(f"Vol basis degree:     {VOL_BASIS_DEGREE}")
print(f"Vol basis size:       {vol_basis(np.array([V0]), np.array([VP0]), v_trunc_cap, vp_trunc_cap).shape[1]}")
print(f"Vol trunc. quantile:  {VOL_TRUNCATION_QUANTILE:.4f}")
print(f"Vol trunc. v cap:     {v_trunc_cap:.6f}")
print(f"Vol trunc. vp cap:    {vp_trunc_cap:.6f}")
print(f"Seed:                 {SEED}")
print(f"Low seed:             {LOW_SEED}")
print(f"Hybrid direct price:  {hybrid_direct_price:.6f}")
print(f"Hybrid direct error:  {hybrid_direct_error:.6f}")
print(f"Hybrid low price:     {hybrid_low_price:.6f}")
print(f"Hybrid low error:     {hybrid_low_error:.6f}")
