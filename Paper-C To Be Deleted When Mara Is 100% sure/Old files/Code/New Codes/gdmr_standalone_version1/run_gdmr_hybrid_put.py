import os

import numpy as np


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
# These defaults are a working standalone setup, not a published benchmark
# table from main.pdf.
# ---------------------------------------------------------------------------

S0 = env_float("GDMR_S0", 100.0)
v0 = env_float("GDMR_V0", 0.04)
vp0 = env_float("GDMR_VP0", 0.04)
r = env_float("GDMR_R", 0.03)
kappa1 = env_float("GDMR_KAPPA1", 2.0)
kappa2 = env_float("GDMR_KAPPA2", 1.0)
theta = env_float("GDMR_THETA", 0.04)
xi1 = env_float("GDMR_XI1", 0.35)
xi2 = env_float("GDMR_XI2", 0.20)
delta1 = env_float("GDMR_DELTA1", 0.5)
delta2 = env_float("GDMR_DELTA2", 0.5)
rho12 = env_float("GDMR_RHO12", 0.20)
rho13 = env_float("GDMR_RHO13", 0.10)
rho23 = env_float("GDMR_RHO23", 0.10)


# Bermudan put setup.
option_type = "put"
K = env_float("GDMR_STRIKE", 100.0)
T = env_float("GDMR_MATURITY", 1.0)
N = env_int("GDMR_HYBRID_PATHS", 30_000)
N_low = env_int("GDMR_HYBRID_LOW_PATHS", 30_000)
N_ex = env_int("GDMR_EXERCISE_DATES", 100)
M = env_int("GDMR_EULER_STEPS", 600)
N_S = env_int("GDMR_HYBRID_ASSET_POINTS", 181)
N_hermite = env_int("GDMR_HYBRID_HERMITE_NODES", 64)
asset_low_factor = env_float("GDMR_HYBRID_ASSET_LOW_FACTOR", 0.35)
asset_high_factor = env_float("GDMR_HYBRID_ASSET_HIGH_FACTOR", 3.00)
vol_truncation_quantile = env_float("GDMR_HYBRID_VOL_QUANTILE", 0.995)
seed = env_int("GDMR_HYBRID_SEED", 2026)
low_seed = env_int("GDMR_HYBRID_LOW_SEED", 2103)
ridge_lambda = env_float("GDMR_HYBRID_RIDGE", 1e-10)

vol_basis_degree = 3

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
corr23 = np.array([[1.0, rho23], [rho23, 1.0]], dtype=np.float64)
chol23 = np.linalg.cholesky(corr23).astype(np.float32)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def payoff(spot: np.ndarray) -> np.ndarray:
    return np.maximum(K - spot, 0.0)



def projection_coefficients() -> tuple[float, float, float]:
    beta2 = (rho12 - rho13 * rho23) / (1.0 - rho23**2)
    beta3 = (rho13 - rho12 * rho23) / (1.0 - rho23**2)
    sigma_perp_sq = (
        1.0 - rho12**2 - rho13**2 - rho23**2 + 2.0 * rho12 * rho13 * rho23
    ) / (1.0 - rho23**2)
    return beta2, beta3, max(float(sigma_perp_sq), 0.0)



def vol_basis(v: np.ndarray, vp: np.ndarray, v_cap: float, vp_cap: float) -> np.ndarray:
    inside = ((v >= 0.0) & (v <= v_cap) & (vp >= 0.0) & (vp <= vp_cap)).astype(np.float64)
    y = np.clip(v, 0.0, v_cap) / max(v_cap, 1e-8)
    z = np.clip(vp, 0.0, vp_cap) / max(vp_cap, 1e-8)
    return np.column_stack(
        [
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
        ]
    )



def ridge_regression(x_design: np.ndarray, y_target: np.ndarray, ridge_value: float) -> np.ndarray:
    left = x_design.T @ x_design + ridge_value * np.eye(x_design.shape[1])
    right = x_design.T @ y_target
    try:
        return np.linalg.solve(left, right)
    except np.linalg.LinAlgError:
        return np.linalg.lstsq(x_design, y_target, rcond=None)[0]



def simulate_full_paths(n_paths: int, seed_value: int):
    dt = T / M
    sqrt_dt = np.sqrt(dt)
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

    return spot, v, vp



def simulate_volatility_statistics(
    n_paths: int,
    seed_value: int,
    beta2: float,
    beta3: float,
    sigma_perp_sq: float,
):
    dt = T / M
    sqrt_dt = np.sqrt(dt)
    rng = np.random.default_rng(seed_value)

    v_paths = np.empty((N_ex + 1, n_paths), dtype=np.float32)
    vp_paths = np.empty((N_ex + 1, n_paths), dtype=np.float32)
    a_stats = np.empty((N_ex, n_paths), dtype=np.float64)
    b_stats = np.empty((N_ex, n_paths), dtype=np.float64)
    z_stats = np.empty((N_ex, n_paths), dtype=np.float64)

    v_now = np.full(n_paths, v0, dtype=np.float32)
    vp_now = np.full(n_paths, vp0, dtype=np.float32)
    v_paths[0] = v_now
    vp_paths[0] = vp_now

    for exercise_step, n_small_steps in enumerate(interval_steps):
        a_step = np.zeros(n_paths, dtype=np.float64)
        b_step = np.zeros(n_paths, dtype=np.float64)
        z_step = np.zeros(n_paths, dtype=np.float64)

        for _ in range(int(n_small_steps)):
            Z23 = rng.standard_normal((n_paths, 2)).astype(np.float32) @ chol23.T
            z2 = Z23[:, 0]
            z3 = Z23[:, 1]
            dw2 = sqrt_dt * z2
            dw3 = sqrt_dt * z3
            v_pos = np.maximum(v_now, 0.0)
            vp_pos = np.maximum(vp_now, 0.0)
            sqrt_v = np.sqrt(v_pos)

            a_step += (r - 0.5 * v_pos) * dt
            b_step += sigma_perp_sq * v_pos * dt
            z_step += sqrt_v * (beta2 * dw2 + beta3 * dw3)

            vp_next = vp_pos + kappa2 * (theta - vp_pos) * dt
            vp_next += xi2 * np.power(vp_pos, delta2) * dw3
            vp_now = np.maximum(vp_next, 0.0)

            v_next = v_pos + kappa1 * (vp_pos - v_pos) * dt
            v_next += xi1 * np.power(v_pos, delta1) * dw2
            v_now = np.maximum(v_next, 0.0)

        v_paths[exercise_step + 1] = v_now
        vp_paths[exercise_step + 1] = vp_now
        a_stats[exercise_step] = a_step
        b_stats[exercise_step] = b_step
        z_stats[exercise_step] = z_step

    return v_paths, vp_paths, a_stats, b_stats, z_stats



def truncation_caps(v_paths: np.ndarray, vp_paths: np.ndarray) -> tuple[float, float]:
    v_cap = float(np.quantile(v_paths, vol_truncation_quantile))
    vp_cap = float(np.quantile(vp_paths, vol_truncation_quantile))
    return max(v_cap, v0), max(vp_cap, vp0)



def build_asset_grid() -> np.ndarray:
    low = max(S0 * asset_low_factor, 0.25 * K * asset_low_factor)
    high = max(S0, K) * asset_high_factor
    return np.exp(np.linspace(np.log(low), np.log(high), N_S))



def conditional_expectation(
    log_grid: np.ndarray,
    terminal_values: np.ndarray,
    shift: float,
    variance: float,
    nodes: np.ndarray,
    weights: np.ndarray,
) -> np.ndarray:
    left = float(terminal_values[0])
    right = float(terminal_values[-1])
    if variance <= 1e-14:
        return np.interp(log_grid + shift, log_grid, terminal_values, left=left, right=right)

    out = np.zeros_like(terminal_values, dtype=np.float64)
    moves = shift + np.sqrt(2.0 * variance) * nodes
    for weight, move in zip(weights, moves):
        out += weight * np.interp(log_grid + move, log_grid, terminal_values, left=left, right=right)
    return out



def interpolation_weights(log_grid: np.ndarray, log_spot: float) -> tuple[int, int, float, float]:
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



def continuation_from_coefficients(
    asset_grid: np.ndarray,
    coeff_matrix: np.ndarray,
    spot: np.ndarray,
    v: np.ndarray,
    vp: np.ndarray,
    v_cap: float,
    vp_cap: float,
) -> np.ndarray:
    basis = vol_basis(v, vp, v_cap, vp_cap)
    log_grid = np.log(asset_grid)
    log_spot = np.log(np.clip(spot, asset_grid[0], asset_grid[-1]))
    continuation = np.zeros_like(log_spot, dtype=np.float64)

    for k in range(basis.shape[1]):
        continuation += basis[:, k] * np.interp(log_spot, log_grid, coeff_matrix[:, k])

    return continuation


# ---------------------------------------------------------------------------
# Main hybrid algorithm
# ---------------------------------------------------------------------------


def hybrid_prices() -> tuple[float, float, float, float, float, float]:
    beta2, beta3, sigma_perp_sq = projection_coefficients()
    asset_grid = build_asset_grid()
    log_asset_grid = np.log(asset_grid)
    payoff_grid = payoff(asset_grid).astype(np.float64)
    nodes, weights = np.polynomial.hermite.hermgauss(N_hermite)
    weights = weights / np.sqrt(np.pi)

    v_paths, vp_paths, a_stats, b_stats, z_stats = simulate_volatility_statistics(
        N,
        seed,
        beta2,
        beta3,
        sigma_perp_sq,
    )
    v_cap, vp_cap = truncation_caps(v_paths, vp_paths)

    value_next = np.repeat(payoff_grid[None, :], N, axis=0)
    coefficient_steps = [None] * (N_ex + 1)

    for step in range(N_ex - 1, 0, -1):
        discount = np.exp(-r * (exercise_times[step + 1] - exercise_times[step]))
        v_now = np.maximum(v_paths[step], 0.0)
        vp_now = np.maximum(vp_paths[step], 0.0)
        shift = a_stats[step] + z_stats[step]
        variance = b_stats[step]

        pre_surface = np.empty_like(value_next)
        for path in range(N):
            pre_surface[path] = discount * conditional_expectation(
                log_asset_grid,
                value_next[path],
                float(shift[path]),
                float(variance[path]),
                nodes,
                weights,
            )

        basis_now = vol_basis(v_now, vp_now, v_cap, vp_cap).astype(np.float64)
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
    direct_price = max(float(payoff(np.array([S0]))[0]), float(np.mean(direct_values)))
    direct_error = float(np.std(direct_values, ddof=1) / np.sqrt(N))

    spot_low, v_low, vp_low = simulate_full_paths(N_low, low_seed)
    low_cashflow = np.exp(-r * float(exercise_times[-1])) * payoff(spot_low[-1]).astype(np.float64)
    exercised = np.zeros(N_low, dtype=bool)

    for step in range(1, N_ex):
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
        low_cashflow[exercise_now] = np.exp(-r * float(exercise_times[step])) * exercise_value[exercise_now]
        exercised[exercise_now] = True

    # The low estimator follows an out-of-sample policy and excludes time-zero exercise.
    low_price = float(np.mean(low_cashflow))
    low_error = float(np.std(low_cashflow, ddof=1) / np.sqrt(N_low))
    return direct_price, direct_error, low_price, low_error, v_cap, vp_cap


# ---------------------------------------------------------------------------
# Main run
# ---------------------------------------------------------------------------


def main() -> None:
    (
        hybrid_direct_price,
        hybrid_direct_error,
        hybrid_low_price,
        hybrid_low_error,
        v_trunc_cap,
        vp_trunc_cap,
    ) = hybrid_prices()

    print("Hybrid LSMC-PDE for a Bermudan put")
    print("Model: generalized Gatheral double mean-reverting (gDMR)")
    print(f"Option type:          {option_type}")
    print(f"Spot:                 {S0:.2f}")
    print(f"Strike:               {K:.2f}")
    print(f"Maturity:             {T:.2f}")
    print(f"Paths:                {N}")
    print(f"Low paths:            {N_low}")
    print(f"Exercise dates:       {N_ex}")
    print(f"Euler steps:          {M}")
    print(f"Internal steps:       {internal_steps:.6g}")
    print(f"Asset grid points:    {N_S}")
    print(f"Asset low factor:     {asset_low_factor:.4f}")
    print(f"Asset high factor:    {asset_high_factor:.4f}")
    print(f"Hermite nodes:        {N_hermite}")
    print(f"Vol basis degree:     {vol_basis_degree}")
    print(
        f"Vol basis size:       {vol_basis(np.array([v0]), np.array([vp0]), v_trunc_cap, vp_trunc_cap).shape[1]}"
    )
    print(f"Vol trunc. quantile:  {vol_truncation_quantile:.4f}")
    print(f"Vol trunc. v cap:     {v_trunc_cap:.6f}")
    print(f"Vol trunc. vp cap:    {vp_trunc_cap:.6f}")
    print(f"Seed:                 {seed}")
    print(f"Low seed:             {low_seed}")
    print(f"Hybrid direct price:  {hybrid_direct_price:.6f}")
    print(f"Hybrid direct error:  {hybrid_direct_error:.6f}")
    print(f"Hybrid low price:     {hybrid_low_price:.6f}")
    print(f"Hybrid low error:     {hybrid_low_error:.6f}")


if __name__ == "__main__":
    main()
