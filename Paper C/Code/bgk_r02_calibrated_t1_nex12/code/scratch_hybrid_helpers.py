from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class GdmrModel:
    s0: float
    v0: float
    vp0: float
    r: float
    kappa1: float
    kappa2: float
    theta: float
    xi1: float
    xi2: float
    delta1: float
    delta2: float
    rho12: float
    rho13: float
    rho23: float
    maturity: float


@dataclass(frozen=True)
class HybridSettings:
    strike: float
    paths: int
    low_paths: int
    exercise_dates: int
    euler_steps: int
    asset_points: int
    asset_low_factor: float
    asset_high_factor: float
    vol_quantile: float
    fst_pad_factor: int
    fst_batch_size: int
    seed: int
    low_seed: int
    ridge: float


@dataclass(frozen=True)
class ExerciseGrid:
    indices: np.ndarray
    intervals: np.ndarray
    times: np.ndarray
    internal_steps: float


def payoff_put(spot: np.ndarray | float, strike: float) -> np.ndarray | float:
    return np.maximum(strike - spot, 0.0)


def make_exercise_grid(maturity: float, euler_steps: int, exercise_dates: int) -> ExerciseGrid:
    if euler_steps <= 0:
        raise ValueError("GDMR_EULER_STEPS must be positive.")
    if exercise_dates <= 0:
        raise ValueError("GDMR_EXERCISE_DATES must be positive.")
    if exercise_dates > euler_steps:
        raise ValueError("GDMR_EXERCISE_DATES cannot exceed GDMR_EULER_STEPS.")

    indices = np.rint(np.linspace(0.0, euler_steps, exercise_dates + 1)).astype(np.int32)
    indices[0] = 0
    indices[-1] = euler_steps
    intervals = np.diff(indices)
    if np.any(intervals <= 0):
        raise ValueError("Exercise grid must be strictly increasing after rounding.")

    times = maturity * indices.astype(np.float64) / float(euler_steps)
    return ExerciseGrid(
        indices=indices,
        intervals=intervals,
        times=times,
        internal_steps=euler_steps / float(exercise_dates),
    )


def projection_coefficients(model: GdmrModel) -> tuple[float, float, float]:
    denominator = 1.0 - model.rho23 * model.rho23
    if denominator <= 0.0:
        raise ValueError("GDMR_RHO23 must be strictly between -1 and 1.")

    beta2 = (model.rho12 - model.rho13 * model.rho23) / denominator
    beta3 = (model.rho13 - model.rho12 * model.rho23) / denominator
    sigma_perp_sq = (
        1.0
        - model.rho12 * model.rho12
        - model.rho13 * model.rho13
        - model.rho23 * model.rho23
        + 2.0 * model.rho12 * model.rho13 * model.rho23
    ) / denominator
    if sigma_perp_sq < -1e-12:
        raise ValueError("Invalid correlation structure: negative orthogonal residual variance.")
    return float(beta2), float(beta3), max(float(sigma_perp_sq), 0.0)


def correlated_vol_cholesky(rho23: float) -> np.ndarray:
    corr = np.array([[1.0, rho23], [rho23, 1.0]], dtype=np.float64)
    return np.linalg.cholesky(corr).astype(np.float32)


def build_log_asset_grid(
    s0: float,
    strike: float,
    points: int,
    low_factor: float,
    high_factor: float,
) -> tuple[np.ndarray, np.ndarray]:
    if points < 3:
        raise ValueError("GDMR_HYBRID_ASSET_POINTS must be at least 3.")
    if low_factor <= 0.0 or high_factor <= 0.0:
        raise ValueError("Asset grid factors must be positive.")

    low = max(s0 * low_factor, 0.25 * strike * low_factor, 1e-8)
    high = max(s0, strike) * high_factor
    if high <= low:
        raise ValueError("Asset grid upper bound must exceed lower bound.")

    log_grid = np.linspace(math.log(low), math.log(high), points, dtype=np.float64)
    return log_grid, np.exp(log_grid)


def cubic_vol_basis(v: np.ndarray, vp: np.ndarray, v_cap: float, vp_cap: float) -> np.ndarray:
    v = np.asarray(v, dtype=np.float64)
    vp = np.asarray(vp, dtype=np.float64)
    inside = ((v >= 0.0) & (v <= v_cap) & (vp >= 0.0) & (vp <= vp_cap)).astype(np.float64)
    y = np.clip(v, 0.0, v_cap) / max(float(v_cap), 1e-12)
    z = np.clip(vp, 0.0, vp_cap) / max(float(vp_cap), 1e-12)
    return np.column_stack(
        (
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
        )
    )


def ridge_regression_by_asset(
    design: np.ndarray,
    targets: np.ndarray,
    ridge: float,
) -> np.ndarray:
    design = np.asarray(design, dtype=np.float64)
    targets = np.asarray(targets, dtype=np.float64)
    if design.ndim != 2 or targets.ndim != 2:
        raise ValueError("Regression design and targets must be 2-dimensional.")
    if design.shape[0] != targets.shape[0]:
        raise ValueError("Regression row counts must match.")

    left = design.T @ design
    if ridge > 0.0:
        left = left + ridge * np.eye(left.shape[0], dtype=np.float64)
    right = design.T @ targets
    try:
        coeff = np.linalg.solve(left, right)
    except np.linalg.LinAlgError:
        coeff = np.linalg.lstsq(left, right, rcond=None)[0]
    return coeff.T


def simulate_volatility_only(
    model: GdmrModel,
    grid: ExerciseGrid,
    n_paths: int,
    seed: int,
    beta2: float,
    beta3: float,
    sigma_perp_sq: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    if n_paths <= 0:
        raise ValueError("Path counts must be positive.")

    dt = model.maturity / float(grid.indices[-1])
    sqrt_dt = math.sqrt(dt)
    rng = np.random.default_rng(seed)
    chol23 = correlated_vol_cholesky(model.rho23)

    v_paths = np.empty((grid.intervals.size + 1, n_paths), dtype=np.float32)
    vp_paths = np.empty((grid.intervals.size + 1, n_paths), dtype=np.float32)
    drift_stats = np.empty((grid.intervals.size, n_paths), dtype=np.float64)
    variance_stats = np.empty((grid.intervals.size, n_paths), dtype=np.float64)
    projected_stats = np.empty((grid.intervals.size, n_paths), dtype=np.float64)

    v_now = np.full(n_paths, model.v0, dtype=np.float32)
    vp_now = np.full(n_paths, model.vp0, dtype=np.float32)
    v_paths[0] = v_now
    vp_paths[0] = vp_now

    for exercise_step, n_small_steps in enumerate(grid.intervals):
        drift = np.zeros(n_paths, dtype=np.float64)
        variance = np.zeros(n_paths, dtype=np.float64)
        projected = np.zeros(n_paths, dtype=np.float64)

        for _ in range(int(n_small_steps)):
            z23 = rng.standard_normal((n_paths, 2), dtype=np.float32) @ chol23.T
            z2 = z23[:, 0]
            z3 = z23[:, 1]
            dw2 = sqrt_dt * z2
            dw3 = sqrt_dt * z3

            v_pos = np.maximum(v_now, 0.0)
            vp_pos = np.maximum(vp_now, 0.0)
            sqrt_v = np.sqrt(v_pos)

            drift += (model.r - 0.5 * v_pos) * dt
            variance += sigma_perp_sq * v_pos * dt
            projected += sqrt_v * (beta2 * dw2 + beta3 * dw3)

            vp_next = vp_pos + model.kappa2 * (model.theta - vp_pos) * dt
            vp_next += model.xi2 * np.power(vp_pos, model.delta2) * dw3
            v_next = v_pos + model.kappa1 * (vp_pos - v_pos) * dt
            v_next += model.xi1 * np.power(v_pos, model.delta1) * dw2

            vp_now = np.maximum(vp_next, 0.0)
            v_now = np.maximum(v_next, 0.0)

        v_paths[exercise_step + 1] = v_now
        vp_paths[exercise_step + 1] = vp_now
        drift_stats[exercise_step] = drift
        variance_stats[exercise_step] = variance
        projected_stats[exercise_step] = projected

    return v_paths, vp_paths, drift_stats, variance_stats, projected_stats


def volatility_caps(
    v_paths: np.ndarray,
    vp_paths: np.ndarray,
    quantile: float,
    v0: float,
    vp0: float,
) -> tuple[float, float]:
    if not 0.0 < quantile <= 1.0:
        raise ValueError("GDMR_HYBRID_VOL_QUANTILE must be in (0, 1].")
    v_cap = float(np.quantile(v_paths, quantile))
    vp_cap = float(np.quantile(vp_paths, quantile))
    return max(v_cap, float(v0), 1e-12), max(vp_cap, float(vp0), 1e-12)


def _fft_output_shape(n_space: int, pad_factor: int) -> tuple[int, int]:
    if pad_factor < 1:
        raise ValueError("GDMR_HYBRID_FST_PAD_FACTOR must be at least 1.")
    target = max(2 * n_space, pad_factor * n_space)
    n_pad = 1
    while n_pad < target:
        n_pad *= 2
    offset = (n_pad - n_space) // 2
    return n_pad, offset


def _shift_without_diffusion(
    log_grid: np.ndarray,
    values: np.ndarray,
    shift: float,
) -> np.ndarray:
    return np.interp(
        log_grid + shift,
        log_grid,
        values,
        left=float(values[0]),
        right=float(values[-1]),
    )


def fft_conditional_expectation(
    log_grid: np.ndarray,
    continuation_rows: np.ndarray,
    shifts: np.ndarray,
    variances: np.ndarray,
    pad_factor: int,
    batch_size: int,
) -> np.ndarray:
    continuation_rows = np.asarray(continuation_rows, dtype=np.float64)
    shifts = np.asarray(shifts, dtype=np.float64)
    variances = np.asarray(variances, dtype=np.float64)
    if continuation_rows.ndim != 2:
        raise ValueError("continuation_rows must be 2-dimensional.")
    if shifts.shape != (continuation_rows.shape[0],):
        raise ValueError("shifts must match row count.")
    if variances.shape != (continuation_rows.shape[0],):
        raise ValueError("variances must match row count.")
    if batch_size <= 0:
        raise ValueError("GDMR_HYBRID_FST_BATCH_SIZE must be positive.")

    n_paths, n_space = continuation_rows.shape
    dy = float(log_grid[1] - log_grid[0])
    n_pad, offset = _fft_output_shape(n_space, pad_factor)
    omega = 2.0 * math.pi * np.fft.fftfreq(n_pad, d=dy)
    out = np.empty((n_paths, n_space), dtype=np.float64)

    tiny_variance = 1e-14
    for start in range(0, n_paths, batch_size):
        end = min(start + batch_size, n_paths)
        chunk = continuation_rows[start:end]
        chunk_size = end - start
        padded = np.empty((chunk_size, n_pad), dtype=np.float64)
        padded[:, :offset] = chunk[:, [0]]
        padded[:, offset : offset + n_space] = chunk
        padded[:, offset + n_space :] = chunk[:, [-1]]

        shift_chunk = shifts[start:end]
        var_chunk = np.maximum(variances[start:end], 0.0)
        diffuse_mask = var_chunk > tiny_variance
        if np.any(diffuse_mask):
            local = np.where(diffuse_mask)[0]
            fft_values = np.fft.fft(padded[local], axis=1)
            exponent = (
                1j * shift_chunk[local, None] * omega[None, :]
                - 0.5 * var_chunk[local, None] * omega[None, :] * omega[None, :]
            )
            smoothed = np.fft.ifft(fft_values * np.exp(exponent), axis=1).real
            out[start + local] = smoothed[:, offset : offset + n_space]

        if np.any(~diffuse_mask):
            local = np.where(~diffuse_mask)[0]
            for idx in local:
                out[start + idx] = _shift_without_diffusion(
                    log_grid,
                    chunk[idx],
                    float(shift_chunk[idx]),
                )

    return out


def interpolate_rows_at_spot(
    log_grid: np.ndarray,
    row_values: np.ndarray,
    spot: float,
) -> np.ndarray:
    log_spot = math.log(float(spot))
    upper = int(np.searchsorted(log_grid, log_spot, side="right"))
    if upper <= 0:
        return row_values[:, 0].copy()
    if upper >= log_grid.size:
        return row_values[:, -1].copy()

    lower = upper - 1
    left = float(log_grid[lower])
    right = float(log_grid[upper])
    weight_upper = (log_spot - left) / (right - left)
    weight_lower = 1.0 - weight_upper
    return weight_lower * row_values[:, lower] + weight_upper * row_values[:, upper]


def evaluate_policy_surface(
    coefficients: np.ndarray,
    v: np.ndarray,
    vp: np.ndarray,
    v_cap: float,
    vp_cap: float,
) -> np.ndarray:
    basis = cubic_vol_basis(np.maximum(v, 0.0), np.maximum(vp, 0.0), v_cap, vp_cap)
    return basis @ coefficients.T


def price_hybrid_put(model: GdmrModel, settings: HybridSettings) -> dict[str, float | int | bool | str]:
    grid = make_exercise_grid(model.maturity, settings.euler_steps, settings.exercise_dates)
    beta2, beta3, sigma_perp_sq = projection_coefficients(model)
    log_asset_grid, asset_grid = build_log_asset_grid(
        model.s0,
        settings.strike,
        settings.asset_points,
        settings.asset_low_factor,
        settings.asset_high_factor,
    )
    payoff_grid = payoff_put(asset_grid, settings.strike).astype(np.float64)

    v_train, vp_train, drift_train, var_train, proj_train = simulate_volatility_only(
        model,
        grid,
        settings.paths,
        settings.seed,
        beta2,
        beta3,
        sigma_perp_sq,
    )
    v_cap, vp_cap = volatility_caps(
        v_train,
        vp_train,
        settings.vol_quantile,
        model.v0,
        model.vp0,
    )

    value_next = np.repeat(payoff_grid[None, :], settings.paths, axis=0)
    coefficient_steps: list[np.ndarray | None] = [None] * (settings.exercise_dates + 1)

    for step in range(settings.exercise_dates - 1, 0, -1):
        discount = math.exp(-model.r * float(grid.times[step + 1] - grid.times[step]))
        pre_exercise = discount * fft_conditional_expectation(
            log_asset_grid,
            value_next,
            drift_train[step] + proj_train[step],
            var_train[step],
            settings.fst_pad_factor,
            settings.fst_batch_size,
        )
        design = cubic_vol_basis(v_train[step], vp_train[step], v_cap, vp_cap)
        coefficients = ridge_regression_by_asset(design, pre_exercise, settings.ridge)
        fitted_continuation = design @ coefficients.T
        value_next = np.maximum(payoff_grid[None, :], fitted_continuation)
        coefficient_steps[step] = coefficients

    discount0 = math.exp(-model.r * float(grid.times[1] - grid.times[0]))
    surface0 = discount0 * fft_conditional_expectation(
        log_asset_grid,
        value_next,
        drift_train[0] + proj_train[0],
        var_train[0],
        settings.fst_pad_factor,
        settings.fst_batch_size,
    )
    direct_samples = interpolate_rows_at_spot(log_asset_grid, surface0, model.s0)
    direct_price = max(float(payoff_put(model.s0, settings.strike)), float(np.mean(direct_samples)))
    direct_error = (
        float(np.std(direct_samples, ddof=1) / math.sqrt(settings.paths))
        if settings.paths > 1
        else 0.0
    )

    v_low, vp_low, drift_low, var_low, proj_low = simulate_volatility_only(
        model,
        grid,
        settings.low_paths,
        settings.low_seed,
        beta2,
        beta3,
        sigma_perp_sq,
    )
    value_low = np.repeat(payoff_grid[None, :], settings.low_paths, axis=0)

    for step in range(settings.exercise_dates - 1, 0, -1):
        coefficients = coefficient_steps[step]
        if coefficients is None:
            raise RuntimeError(f"Missing regression coefficients at exercise step {step}.")

        discount = math.exp(-model.r * float(grid.times[step + 1] - grid.times[step]))
        pre_exercise_low = discount * fft_conditional_expectation(
            log_asset_grid,
            value_low,
            drift_low[step] + proj_low[step],
            var_low[step],
            settings.fst_pad_factor,
            settings.fst_batch_size,
        )
        policy_continuation = evaluate_policy_surface(
            coefficients,
            v_low[step],
            vp_low[step],
            v_cap,
            vp_cap,
        )
        value_low = np.where(policy_continuation > payoff_grid[None, :], pre_exercise_low, payoff_grid[None, :])

    low_surface0 = discount0 * fft_conditional_expectation(
        log_asset_grid,
        value_low,
        drift_low[0] + proj_low[0],
        var_low[0],
        settings.fst_pad_factor,
        settings.fst_batch_size,
    )
    low_samples = interpolate_rows_at_spot(log_asset_grid, low_surface0, model.s0)
    low_price = float(np.mean(low_samples))
    low_error = (
        float(np.std(low_samples, ddof=1) / math.sqrt(settings.low_paths))
        if settings.low_paths > 1
        else 0.0
    )

    basis_size = int(cubic_vol_basis(np.array([model.v0]), np.array([model.vp0]), v_cap, vp_cap).shape[1])
    return {
        "method": "Hybrid LSMC-PDE with FFT from scratch",
        "option_type": "put",
        "S0": float(model.s0),
        "K": float(settings.strike),
        "T": float(model.maturity),
        "r": float(model.r),
        "v0": float(model.v0),
        "vp0": float(model.vp0),
        "kappa1": float(model.kappa1),
        "kappa2": float(model.kappa2),
        "theta": float(model.theta),
        "xi1": float(model.xi1),
        "xi2": float(model.xi2),
        "delta1": float(model.delta1),
        "delta2": float(model.delta2),
        "rho12": float(model.rho12),
        "rho13": float(model.rho13),
        "rho23": float(model.rho23),
        "paths": int(settings.paths),
        "low_paths": int(settings.low_paths),
        "exercise_dates": int(settings.exercise_dates),
        "euler_steps": int(settings.euler_steps),
        "internal_steps": float(grid.internal_steps),
        "asset_grid_points": int(settings.asset_points),
        "asset_low_factor": float(settings.asset_low_factor),
        "asset_high_factor": float(settings.asset_high_factor),
        "vol_basis_degree": 3,
        "vol_basis_size": basis_size,
        "vol_quantile": float(settings.vol_quantile),
        "v_cap": float(v_cap),
        "vp_cap": float(vp_cap),
        "seed": int(settings.seed),
        "low_seed": int(settings.low_seed),
        "beta2": float(beta2),
        "beta3": float(beta3),
        "sigma_perp_sq": float(sigma_perp_sq),
        "fst_pad_factor": int(settings.fst_pad_factor),
        "fst_batch_size": int(settings.fst_batch_size),
        "time_zero_exercise_in_low": False,
        "hybrid_direct_price": float(direct_price),
        "hybrid_direct_error": float(direct_error),
        "hybrid_low_price": float(low_price),
        "hybrid_low_error": float(low_error),
    }
