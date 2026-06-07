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
N = 10_000
N_low = 10_000
N_S = 2 ** 9
log_s_min = -3.0
log_s_max = 3.0
basis_degree = 3
N_hermite = 32
seed = 2026
low_seed = 2103
ridge_lambda = 1e-12

exercise_indices = np.rint(np.linspace(0.0, M, N_ex + 1)).astype(np.int32)
exercise_indices[0] = 0
exercise_indices[-1] = M
interval_steps = np.diff(exercise_indices)
exercise_times = T * exercise_indices / float(M)
rho_perp_sq = max(1.0 - rho * rho, 0.0)


def payoff(spot):
    return np.maximum(K - spot, 0.0)


def vol_basis(v):
    y = v / max(v0, 1e-8)
    return np.column_stack([
        np.ones_like(y),
        y,
        y * y,
        y * y * y,
    ])


def ridge_regression(x_design, y_target, ridge_value):
    left = x_design.T @ x_design + ridge_value * np.eye(x_design.shape[1])
    right = x_design.T @ y_target
    try:
        return np.linalg.solve(left, right)
    except np.linalg.LinAlgError:
        return np.linalg.lstsq(x_design, y_target, rcond=None)[0]


def simulate_full_paths(n_paths, seed_value):
    dt = T / M
    sqrt_dt = np.sqrt(dt)
    rng = np.random.default_rng(seed_value)

    spot = np.empty((N_ex + 1, n_paths), dtype=np.float32)
    v = np.empty((N_ex + 1, n_paths), dtype=np.float32)
    spot_now = np.full(n_paths, S0, dtype=np.float32)
    v_now = np.full(n_paths, v0, dtype=np.float32)
    spot[0] = spot_now
    v[0] = v_now

    for exercise_step, n_small_steps in enumerate(interval_steps, start=1):
        for _ in range(int(n_small_steps)):
            z_perp = rng.standard_normal(n_paths, dtype=np.float32)
            z_v = rng.standard_normal(n_paths, dtype=np.float32)
            v_pos = np.maximum(v_now, 0.0)
            sqrt_v = np.sqrt(v_pos)
            dw_v = sqrt_dt * z_v
            dw_s = sqrt_dt * (rho * z_v + np.sqrt(rho_perp_sq) * z_perp)

            v_next = v_pos + kappa * (theta - v_pos) * dt
            v_next += eta * sqrt_v * dw_v
            v_now = np.maximum(v_next, 0.0)

            log_move = (r - 0.5 * v_pos) * dt + sqrt_v * dw_s
            spot_now = spot_now * np.exp(log_move)

        spot[exercise_step] = spot_now
        v[exercise_step] = v_now

    return spot, v


def simulate_volatility_statistics(n_paths, seed_value):
    dt = T / M
    sqrt_dt = np.sqrt(dt)
    rng = np.random.default_rng(seed_value)

    v_paths = np.empty((N_ex + 1, n_paths), dtype=np.float32)
    a_stats = np.empty((N_ex, n_paths), dtype=np.float64)
    b_stats = np.empty((N_ex, n_paths), dtype=np.float64)
    z_stats = np.empty((N_ex, n_paths), dtype=np.float64)

    v_now = np.full(n_paths, v0, dtype=np.float32)
    v_paths[0] = v_now

    for exercise_step, n_small_steps in enumerate(interval_steps):
        a_step = np.zeros(n_paths, dtype=np.float64)
        b_step = np.zeros(n_paths, dtype=np.float64)
        z_step = np.zeros(n_paths, dtype=np.float64)

        for _ in range(int(n_small_steps)):
            z_v = rng.standard_normal(n_paths, dtype=np.float32)
            dw_v = sqrt_dt * z_v
            v_pos = np.maximum(v_now, 0.0)
            sqrt_v = np.sqrt(v_pos)

            a_step += (r - 0.5 * v_pos) * dt
            b_step += rho_perp_sq * v_pos * dt
            z_step += rho * sqrt_v * dw_v

            v_next = v_pos + kappa * (theta - v_pos) * dt
            v_next += eta * sqrt_v * dw_v
            v_now = np.maximum(v_next, 0.0)

        v_paths[exercise_step + 1] = v_now
        a_stats[exercise_step] = a_step
        b_stats[exercise_step] = b_step
        z_stats[exercise_step] = z_step

    return v_paths, a_stats, b_stats, z_stats


def build_asset_grid():
    return S0 * np.exp(np.linspace(log_s_min, log_s_max, N_S))


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
    nodes, weights = np.polynomial.hermite.hermgauss(N_hermite)
    weights = weights / np.sqrt(np.pi)
    v_paths, a_stats, b_stats, z_stats = simulate_volatility_statistics(N, seed)

    value_next = np.repeat(payoff_grid[None, :], N, axis=0)
    coefficient_steps = [None] * (N_ex + 1)

    for step in range(N_ex - 1, 0, -1):
        discount = np.exp(-r * (exercise_times[step + 1] - exercise_times[step]))
        v_now = np.maximum(v_paths[step], 0.0)
        shift = a_stats[step] + z_stats[step]
        variance = b_stats[step]

        pre_surface = np.empty_like(value_next)
        for path in range(N):
            pre_surface[path] = discount * conditional_expectation(
                asset_grid,
                value_next[path],
                float(shift[path]),
                float(variance[path]),
                nodes,
                weights,
            )

        basis_now = vol_basis(v_now).astype(np.float64)
        coefficient_step = np.empty((N_S, basis_now.shape[1]), dtype=np.float64)
        completed_surface = np.empty_like(pre_surface)

        for asset_index in range(N_S):
            coeff = ridge_regression(basis_now, pre_surface[:, asset_index], ridge_lambda)
            coefficient_step[asset_index] = coeff
            completed_surface[:, asset_index] = basis_now @ coeff

        value_next = np.maximum(payoff_grid[None, :], completed_surface)
        coefficient_steps[step] = coefficient_step

    discount0 = np.exp(-r * (exercise_times[1] - exercise_times[0]))
    pre_surface0 = np.empty_like(value_next)
    for path in range(N):
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
        for path in range(N)
    ])
    direct_price = max(float(payoff(S0)), float(np.mean(direct_values)))
    direct_error = float(np.std(direct_values, ddof=1) / np.sqrt(N))

    spot_low, v_low = simulate_full_paths(N_low, low_seed)
    low_cashflow = np.exp(-r * exercise_times[-1]) * payoff(spot_low[-1]).astype(np.float64)
    exercised = np.zeros(N_low, dtype=bool)

    for step in range(1, N_ex):
        exercise_value = payoff(spot_low[step]).astype(np.float64)
        continuation = continuation_from_coefficients(
            asset_grid,
            coefficient_steps[step],
            spot_low[step],
            v_low[step],
        )
        exercise_now = (~exercised) & (exercise_value >= continuation)
        low_cashflow[exercise_now] = np.exp(-r * exercise_times[step]) * exercise_value[exercise_now]
        exercised[exercise_now] = True

    low_price = max(float(payoff(S0)), float(np.mean(low_cashflow)))
    low_error = float(np.std(low_cashflow, ddof=1) / np.sqrt(N_low))
    return direct_price, direct_error, low_price, low_error


hybrid_direct_price, hybrid_direct_error, hybrid_low_price, hybrid_low_error = hybrid_prices()

print("Hybrid LSMC-PDE for a Bermudan put")
print("Model: Heston")
print(f"Option type:          {option_type}")
print(f"Spot:                 {S0:.2f}")
print(f"Strike:               {K:.2f}")
print(f"Maturity:             {T:.2f}")
print(f"Paths:                {N}")
print(f"Low paths:            {N_low}")
print(f"Exercise dates:       {N_ex}")
print(f"Euler steps:          {M}")
print(f"Basis degree:         {basis_degree}")
print(f"Asset grid points:    {N_S}")
print(f"Log-grid min:         {log_s_min:.1f}")
print(f"Log-grid max:         {log_s_max:.1f}")
print(f"Hermite nodes:        {N_hermite}")
print(f"Seed:                 {seed}")
print(f"Low seed:             {low_seed}")
print(f"Hybrid direct price:  {hybrid_direct_price:.6f}")
print(f"Hybrid direct error:  {hybrid_direct_error:.6f}")
print(f"Hybrid low price:     {hybrid_low_price:.6f}")
print(f"Hybrid low error:     {hybrid_low_error:.6f}")
