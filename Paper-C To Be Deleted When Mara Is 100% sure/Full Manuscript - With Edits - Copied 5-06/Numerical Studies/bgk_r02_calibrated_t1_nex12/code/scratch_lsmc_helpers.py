from __future__ import annotations

import gc
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np


STATE_DTYPE = np.float32
BASIS_DEGREE = 3
BASIS_SIZE = 16


@dataclass(frozen=True)
class GDMRParameters:
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


@dataclass(frozen=True)
class LSMCSettings:
    strike: float
    maturity: float
    paths: int
    low_paths: int
    exercise_dates: int
    euler_steps: int
    seed: int
    low_seed: int
    ridge: float
    scratch_root: Path
    chunk_size: int


@dataclass(frozen=True)
class ExerciseGrid:
    indices: np.ndarray
    times: np.ndarray
    interval_steps: np.ndarray

    @property
    def internal_steps(self) -> float:
        return float(self.indices[-1]) / float(len(self.indices) - 1)


def build_exercise_grid(maturity: float, euler_steps: int, exercise_dates: int) -> ExerciseGrid:
    if maturity <= 0.0:
        raise ValueError("GDMR_MATURITY must be positive.")
    if euler_steps <= 0:
        raise ValueError("GDMR_EULER_STEPS must be positive.")
    if exercise_dates <= 0:
        raise ValueError("GDMR_EXERCISE_DATES must be positive.")

    indices = np.rint(np.linspace(0.0, euler_steps, exercise_dates + 1)).astype(np.int32)
    indices[0] = 0
    indices[-1] = euler_steps
    interval_steps = np.diff(indices)
    if np.any(interval_steps <= 0):
        raise ValueError("GDMR_EULER_STEPS must be at least GDMR_EXERCISE_DATES.")
    times = maturity * indices.astype(np.float64) / float(euler_steps)
    return ExerciseGrid(indices=indices, times=times, interval_steps=interval_steps)


def correlated_cholesky(params: GDMRParameters) -> np.ndarray:
    corr = np.array(
        [
            [1.0, params.rho12, params.rho13],
            [params.rho12, 1.0, params.rho23],
            [params.rho13, params.rho23, 1.0],
        ],
        dtype=np.float64,
    )
    return np.linalg.cholesky(corr).astype(np.float32)


def put_payoff(spot: np.ndarray | float, strike: float) -> np.ndarray:
    return np.maximum(strike - np.asarray(spot), 0.0)


def chunk_slices(length: int, chunk_size: int) -> Iterable[slice]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive.")
    for start in range(0, length, chunk_size):
        yield slice(start, min(start + chunk_size, length))


def state_basis(
    spot: np.ndarray,
    variance: np.ndarray,
    variance_prime: np.ndarray,
    params: GDMRParameters,
    strike: float,
) -> np.ndarray:
    x = spot.astype(np.float64, copy=False) / max(params.s0, 1e-12)
    y = variance.astype(np.float64, copy=False) / max(params.theta, 1e-12)
    z = variance_prime.astype(np.float64, copy=False) / max(params.theta, 1e-12)
    p = put_payoff(spot, strike).astype(np.float64, copy=False) / max(strike, 1e-12)
    return np.column_stack(
        (
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
        )
    )


def solve_ridge(normal: np.ndarray, rhs: np.ndarray, ridge: float) -> np.ndarray:
    left = normal + ridge * np.eye(normal.shape[0], dtype=np.float64)
    try:
        return np.linalg.solve(left, rhs)
    except np.linalg.LinAlgError:
        return np.linalg.lstsq(left, rhs, rcond=None)[0]


def standard_error(samples: np.ndarray) -> float:
    if samples.size <= 1:
        return 0.0
    return float(np.std(samples, ddof=1) / np.sqrt(samples.size))


def create_run_store(root: Path, prefix: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    run_dir = root / f"{prefix}_{uuid.uuid4().hex}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def close_memmaps(*arrays: np.memmap | None) -> None:
    for array in arrays:
        if array is None:
            continue
        try:
            array.flush()
        except Exception:
            pass
        mmap_obj = getattr(array, "_mmap", None)
        if mmap_obj is not None:
            try:
                mmap_obj.close()
            except Exception:
                pass


def cleanup_run_store(run_dir: Path) -> None:
    gc.collect()
    try:
        shutil.rmtree(run_dir)
    except FileNotFoundError:
        pass
    except PermissionError:
        pass


def make_state_store(run_dir: Path, prefix: str, exercise_dates: int, paths: int) -> tuple[np.memmap, np.memmap, np.memmap]:
    shape = (exercise_dates + 1, paths)
    spot = np.memmap(run_dir / f"{prefix}_spot.dat", mode="w+", dtype=STATE_DTYPE, shape=shape)
    variance = np.memmap(run_dir / f"{prefix}_variance.dat", mode="w+", dtype=STATE_DTYPE, shape=shape)
    variance_prime = np.memmap(run_dir / f"{prefix}_variance_prime.dat", mode="w+", dtype=STATE_DTYPE, shape=shape)
    return spot, variance, variance_prime


def simulate_exercise_states(
    params: GDMRParameters,
    settings: LSMCSettings,
    grid: ExerciseGrid,
    paths: int,
    seed: int,
    prefix: str,
    run_dir: Path,
) -> tuple[np.memmap, np.memmap, np.memmap]:
    dt = settings.maturity / float(settings.euler_steps)
    sqrt_dt = np.sqrt(dt)
    chol = correlated_cholesky(params)
    rng = np.random.default_rng(seed)
    spot, variance, variance_prime = make_state_store(run_dir, prefix, settings.exercise_dates, paths)

    spot_now = np.full(paths, params.s0, dtype=STATE_DTYPE)
    variance_now = np.full(paths, params.v0, dtype=STATE_DTYPE)
    variance_prime_now = np.full(paths, params.vp0, dtype=STATE_DTYPE)
    spot[0] = spot_now
    variance[0] = variance_now
    variance_prime[0] = variance_prime_now

    for exercise_step, small_steps in enumerate(grid.interval_steps, start=1):
        for _ in range(int(small_steps)):
            normals = rng.standard_normal((paths, 3)).astype(np.float32) @ chol.T
            z_spot = normals[:, 0]
            z_var = normals[:, 1]
            z_var_prime = normals[:, 2]

            var_pos = np.maximum(variance_now, 0.0)
            var_prime_pos = np.maximum(variance_prime_now, 0.0)

            var_prime_next = var_prime_pos + params.kappa2 * (params.theta - var_prime_pos) * dt
            var_prime_next += params.xi2 * np.power(var_prime_pos, params.delta2) * sqrt_dt * z_var_prime
            variance_prime_now = np.maximum(var_prime_next, 0.0).astype(STATE_DTYPE, copy=False)

            var_next = var_pos + params.kappa1 * (var_prime_pos - var_pos) * dt
            var_next += params.xi1 * np.power(var_pos, params.delta1) * sqrt_dt * z_var
            variance_now = np.maximum(var_next, 0.0).astype(STATE_DTYPE, copy=False)

            log_move = (params.r - 0.5 * var_pos) * dt + np.sqrt(var_pos) * sqrt_dt * z_spot
            spot_now = (spot_now * np.exp(log_move)).astype(STATE_DTYPE, copy=False)

        spot[exercise_step] = spot_now
        variance[exercise_step] = variance_now
        variance_prime[exercise_step] = variance_prime_now

    spot.flush()
    variance.flush()
    variance_prime.flush()
    return spot, variance, variance_prime


def fit_continuation(
    spot: np.ndarray,
    variance: np.ndarray,
    variance_prime: np.ndarray,
    target: np.ndarray,
    params: GDMRParameters,
    settings: LSMCSettings,
) -> np.ndarray:
    normal = np.zeros((BASIS_SIZE, BASIS_SIZE), dtype=np.float64)
    rhs = np.zeros(BASIS_SIZE, dtype=np.float64)
    for slc in chunk_slices(target.size, settings.chunk_size):
        design = state_basis(spot[slc], variance[slc], variance_prime[slc], params, settings.strike)
        target_chunk = target[slc]
        normal += design.T @ design
        rhs += design.T @ target_chunk
    return solve_ridge(normal, rhs, settings.ridge)


def direct_estimator(
    params: GDMRParameters,
    settings: LSMCSettings,
    grid: ExerciseGrid,
) -> tuple[float, float, list[np.ndarray | None]]:
    coeff_steps: list[np.ndarray | None] = [None] * (settings.exercise_dates + 1)
    run_dir = create_run_store(settings.scratch_root, "direct")
    spot = variance = variance_prime = None
    try:
        spot, variance, variance_prime = simulate_exercise_states(
            params, settings, grid, settings.paths, settings.seed, "direct", run_dir
        )
        cashflow = put_payoff(np.asarray(spot[settings.exercise_dates]), settings.strike).astype(np.float64)

        for step in range(settings.exercise_dates - 1, 0, -1):
            step_discount = np.exp(-params.r * float(grid.times[step + 1] - grid.times[step]))
            discounted_future = step_discount * cashflow
            coeff = fit_continuation(
                np.asarray(spot[step]),
                np.asarray(variance[step]),
                np.asarray(variance_prime[step]),
                discounted_future,
                params,
                settings,
            )
            coeff_steps[step] = coeff

            for slc in chunk_slices(settings.paths, settings.chunk_size):
                design = state_basis(spot[step, slc], variance[step, slc], variance_prime[step, slc], params, settings.strike)
                continuation = design @ coeff
                exercise_value = put_payoff(spot[step, slc], settings.strike).astype(np.float64, copy=False)
                cashflow[slc] = np.where(exercise_value >= continuation, exercise_value, discounted_future[slc])

        time0_discount = np.exp(-params.r * float(grid.times[1] - grid.times[0]))
        direct_samples = time0_discount * cashflow
        immediate = float(put_payoff(params.s0, settings.strike))
        direct_price = max(immediate, float(np.mean(direct_samples)))
        return direct_price, standard_error(direct_samples), coeff_steps
    finally:
        close_memmaps(spot, variance, variance_prime)
        del spot, variance, variance_prime
        gc.collect()
        cleanup_run_store(run_dir)


def low_estimator(
    coeff_steps: list[np.ndarray | None],
    params: GDMRParameters,
    settings: LSMCSettings,
    grid: ExerciseGrid,
) -> tuple[float, float]:
    run_dir = create_run_store(settings.scratch_root, "low")
    spot = variance = variance_prime = None
    try:
        spot, variance, variance_prime = simulate_exercise_states(
            params, settings, grid, settings.low_paths, settings.low_seed, "low", run_dir
        )
        discounted_payoff = np.exp(-params.r * settings.maturity) * put_payoff(
            np.asarray(spot[settings.exercise_dates]), settings.strike
        ).astype(np.float64)
        exercised = np.zeros(settings.low_paths, dtype=bool)

        for step in range(1, settings.exercise_dates):
            coeff = coeff_steps[step]
            if coeff is None:
                raise ValueError(f"Missing continuation coefficients for exercise step {step}.")

            step_discount = np.exp(-params.r * float(grid.times[step]))
            for slc in chunk_slices(settings.low_paths, settings.chunk_size):
                design = state_basis(spot[step, slc], variance[step, slc], variance_prime[step, slc], params, settings.strike)
                continuation = design @ coeff
                exercise_value = put_payoff(spot[step, slc], settings.strike).astype(np.float64, copy=False)
                payoff_chunk = discounted_payoff[slc]
                exercised_chunk = exercised[slc]
                exercise_now = (~exercised_chunk) & (exercise_value >= continuation)
                payoff_chunk[exercise_now] = step_discount * exercise_value[exercise_now]
                exercised_chunk[exercise_now] = True

        return float(np.mean(discounted_payoff)), standard_error(discounted_payoff)
    finally:
        close_memmaps(spot, variance, variance_prime)
        del spot, variance, variance_prime
        gc.collect()
        cleanup_run_store(run_dir)


def price_plain_lsmc(params: GDMRParameters, settings: LSMCSettings) -> dict[str, float | int | str]:
    if settings.paths <= 0 or settings.low_paths <= 0:
        raise ValueError("GDMR_LSMC_PATHS and GDMR_LSMC_LOW_PATHS must be positive.")
    grid = build_exercise_grid(settings.maturity, settings.euler_steps, settings.exercise_dates)
    direct_price, direct_error, coeff_steps = direct_estimator(params, settings, grid)
    low_price, low_error = low_estimator(coeff_steps, params, settings, grid)
    return {
        "method": "LSMC Benchmark",
        "engine": "from_scratch_plain_lsmc",
        "option_type": "put",
        "S0": params.s0,
        "K": settings.strike,
        "T": settings.maturity,
        "r": params.r,
        "v0": params.v0,
        "vp0": params.vp0,
        "kappa1": params.kappa1,
        "kappa2": params.kappa2,
        "theta": params.theta,
        "xi1": params.xi1,
        "xi2": params.xi2,
        "delta1": params.delta1,
        "delta2": params.delta2,
        "rho12": params.rho12,
        "rho13": params.rho13,
        "rho23": params.rho23,
        "paths": settings.paths,
        "low_paths": settings.low_paths,
        "exercise_dates": settings.exercise_dates,
        "euler_steps": settings.euler_steps,
        "internal_steps": grid.internal_steps,
        "basis_degree": BASIS_DEGREE,
        "basis_size": BASIS_SIZE,
        "seed": settings.seed,
        "low_seed": settings.low_seed,
        "ridge": settings.ridge,
        "state_dtype": str(np.dtype(STATE_DTYPE)),
        "scratch_root": str(settings.scratch_root),
        "lsmc_direct_price": direct_price,
        "lsmc_direct_error": direct_error,
        "lsmc_low_price": low_price,
        "lsmc_low_error": low_error,
    }
