"""Reproduce Farahany's Table 9 and Table 10 Heston benchmarks."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Literal

import numpy as np

from ..core.numerics import ridge_regression
from ..core.results import MethodResult
from ..core.config import OptionConfig
from ..methods.hybrid.pde import conditional_expectation_one_step


@dataclass(frozen=True)
class HestonParameters:
    """Heston model parameters used in the paper benchmark."""

    s0: float = 10.0
    v0: float = 0.15
    r: float = 0.02
    kappa: float = 5.0
    theta: float = 0.16
    eta: float = 0.9
    rho: float = 0.1
    T: float = 1.0

    def validate(self) -> None:
        if self.s0 <= 0:
            raise ValueError("s0 must be positive.")
        if self.v0 <= 0:
            raise ValueError("v0 must be positive.")
        if not (-1.0 <= self.rho <= 1.0):
            raise ValueError("rho must be in [-1, 1].")
        if self.kappa <= 0:
            raise ValueError("kappa must be positive.")
        if self.theta <= 0:
            raise ValueError("theta must be positive.")
        if self.eta <= 0:
            raise ValueError("eta must be positive.")


@dataclass(frozen=True)
class HestonSolverConfig:
    """Numerical settings for the Heston benchmark."""

    n_paths: int = 10000
    n_steps: int = 12
    n_asset: int = 27
    hermite_nodes: int = 16
    ridge_lambda: float = 1e-8
    vol_basis_degree: int = 3
    state_basis_degree: int = 3
    seed: int = 2026
    v_integral_mode: Literal["left", "midpoint", "trapezoid", "expected"] = "left"
    low_mode: Literal["average_pre", "policy"] = "average_pre"
    low_paths: int = 0


@dataclass(frozen=True)
class HestonSimulationOutput:
    times: np.ndarray
    s: np.ndarray
    v: np.ndarray
    drift_shift: np.ndarray
    correlated_shift: np.ndarray
    v_integral: np.ndarray


def build_heston_grid(s0: float, n_grid: int, log_low: float = -3.0, log_high: float = 3.0) -> np.ndarray:
    s0 = float(max(s0, 1e-12))
    n_grid = int(n_grid)
    if n_grid < 3:
        raise ValueError("n_grid must be >= 3.")
    lo = np.log(s0) + float(log_low)
    hi = np.log(s0) + float(log_high)
    return np.exp(np.linspace(lo, hi, n_grid))


def build_heston_vol_basis(v: np.ndarray, degree: int) -> np.ndarray:
    v = np.asarray(v, dtype=float)
    cols = [np.ones_like(v)]
    for p in range(1, int(degree) + 1):
        cols.append(v ** p)
    return np.column_stack(cols)


def build_heston_state_basis(s: np.ndarray, v: np.ndarray, max_degree: int) -> np.ndarray:
    s = np.asarray(s, dtype=float)
    v = np.asarray(v, dtype=float)
    cols = [np.ones_like(s)]
    if max_degree >= 1:
        cols.extend([s, v])
    if max_degree >= 2:
        cols.extend([s * s, s * v, v * v])
    if max_degree >= 3:
        cols.extend([s ** 3, v ** 3, (s ** 2) * v, s * (v ** 2)])
    return np.column_stack(cols)


def simulate_heston_paths(
    params: HestonParameters,
    n_paths: int,
    n_steps: int,
    seed: int,
    v_integral_mode: Literal["left", "midpoint", "trapezoid", "expected"] = "left",
) -> HestonSimulationOutput:
    params.validate()
    dt = params.T / n_steps
    times = np.linspace(0.0, params.T, n_steps + 1)
    s_paths = np.empty((n_paths, n_steps + 1), dtype=float)
    v_paths = np.empty((n_paths, n_steps + 1), dtype=float)
    drift_shift = np.empty((n_paths, n_steps), dtype=float)
    correlated_shift = np.empty((n_paths, n_steps), dtype=float)
    v_integral = np.empty((n_paths, n_steps), dtype=float)

    rng = np.random.default_rng(seed)
    s_paths[:, 0] = params.s0
    v_paths[:, 0] = max(params.v0, 0.0)
    sqrt_dt = np.sqrt(dt)
    rho_perp = float(np.sqrt(max(0.0, 1.0 - params.rho * params.rho)))
    log_s = np.log(np.maximum(s_paths[:, 0], 1e-12))

    for step in range(n_steps):
        v_prev = np.maximum(v_paths[:, step], 0.0)
        sqrt_v_prev = np.sqrt(v_prev)
        z2 = rng.normal(size=n_paths)
        z1 = rng.normal(size=n_paths)
        dW2 = sqrt_dt * z2
        dW1_perp = sqrt_dt * z1

        dv = params.kappa * (params.theta - v_prev) * dt + params.eta * sqrt_v_prev * dW2
        v_unclipped_next = v_prev + dv
        v_next = np.maximum(v_unclipped_next, 0.0)
        if v_integral_mode == "left":
            v_integral[:, step] = v_prev * dt
        elif v_integral_mode in {"midpoint", "trapezoid"}:
            v_integral[:, step] = 0.5 * (v_prev + v_next) * dt
        elif v_integral_mode == "expected":
            kappa_dt = params.kappa * dt
            if kappa_dt == 0:
                v_integral[:, step] = v_prev * dt
            else:
                v_integral[:, step] = (
                    params.theta * dt
                    + (v_prev - params.theta) * (1.0 - np.exp(-kappa_dt)) / params.kappa
                )
        else:
            raise ValueError("v_integral_mode must be 'left', 'midpoint', 'trapezoid', or 'expected'.")
        v_paths[:, step + 1] = v_next

        corr_shift = params.rho * sqrt_v_prev * dW2
        drift_shift[:, step] = params.r * dt - 0.5 * v_prev * dt
        correlated_shift[:, step] = corr_shift
        log_s = log_s + drift_shift[:, step] + corr_shift + rho_perp * sqrt_v_prev * dW1_perp
        s_paths[:, step + 1] = np.exp(log_s)

    return HestonSimulationOutput(
        times=times,
        s=s_paths,
        v=v_paths,
        drift_shift=drift_shift,
        correlated_shift=correlated_shift,
        v_integral=v_integral,
    )


def _interpolate_rows_at_value(x_grid: np.ndarray, y_grid: np.ndarray, x: float) -> np.ndarray:
    log_x_grid = np.log(x_grid)
    lx = np.log(x)
    return np.array(
        [
            np.interp(lx, log_x_grid, y_row, left=float(y_row[0]), right=float(y_row[-1]))
            for y_row in y_grid
        ],
        dtype=float,
    )


def _interpolate_rows_at_values(
    x_grid: np.ndarray,
    y_grid: np.ndarray,
    x: np.ndarray,
) -> np.ndarray:
    log_x_grid = np.log(x_grid)
    lx = np.log(np.asarray(x))
    return np.array(
        [
            np.interp(xi, log_x_grid, y_row, left=float(y_row[0]), right=float(y_row[-1]))
            for xi, y_row in zip(lx, y_grid)
        ],
        dtype=float,
    )


def run_heston_hybrid(
    model: HestonParameters,
    option: OptionConfig,
    cfg: HestonSolverConfig,
) -> MethodResult:
    model.validate()
    sim = simulate_heston_paths(
        model,
        cfg.n_paths,
        cfg.n_steps,
        cfg.seed,
        v_integral_mode=cfg.v_integral_mode,
    )
    dt = model.T / cfg.n_steps
    discount = float(np.exp(-model.r * dt))
    asset_grid = build_heston_grid(model.s0, cfg.n_asset)
    payoff_grid = option.payoff(asset_grid)

    coeffs = np.zeros(
        (cfg.n_steps, cfg.n_asset, cfg.vol_basis_degree + 1),
        dtype=float,
    )
    value = np.zeros((cfg.n_paths, cfg.n_steps + 1, cfg.n_asset), dtype=float)
    value[:, -1, :] = payoff_grid[None, :]
    pre_surface_t0: np.ndarray | None = None

    for step in reversed(range(cfg.n_steps)):
        terminal = value[:, step + 1, :]
        pre_surface = np.zeros((cfg.n_paths, cfg.n_asset), dtype=float)
        for j in range(cfg.n_paths):
            pre_surface[j, :] = discount * conditional_expectation_one_step(
                asset_grid=asset_grid,
                terminal_values=terminal[j, :],
                mean_log_shift=float(sim.drift_shift[j, step] + sim.correlated_shift[j, step]),
                variance=float((1.0 - model.rho * model.rho) * sim.v_integral[j, step]),
                hermite_nodes=cfg.hermite_nodes,
            )
        if step == 0:
            pre_surface_t0 = pre_surface.copy()

        basis_now = build_heston_vol_basis(sim.v[:, step], cfg.vol_basis_degree)
        continuation = np.zeros((cfg.n_paths, cfg.n_asset), dtype=float)
        for i in range(cfg.n_asset):
            coeff = ridge_regression(basis_now, pre_surface[:, i], ridge_lambda=cfg.ridge_lambda)
            coeffs[step, i, : coeff.size] = coeff
            continuation[:, i] = basis_now @ coeff
        value[:, step, :] = np.maximum(payoff_grid[None, :], continuation)

    basis0 = build_heston_vol_basis(np.array([model.v0]), cfg.vol_basis_degree)[0]
    continuation_at_s0 = np.array([float(c @ basis0) for c in coeffs[0]])
    direct_cont = float(_interpolate_rows_at_value(asset_grid, continuation_at_s0[None, :], model.s0)[0])
    direct = float(max(float(option.payoff(model.s0)), direct_cont))

    if pre_surface_t0 is None:
        raise RuntimeError("Could not capture step-zero pre-surface.")

    if cfg.low_mode == "average_pre":
        low_cont = float(np.mean(_interpolate_rows_at_value(asset_grid, pre_surface_t0, model.s0)))
        low = float(max(float(option.payoff(model.s0)), low_cont))
    elif cfg.low_mode == "policy":
        n_low_paths = cfg.low_paths if cfg.low_paths > 0 else cfg.n_paths
        low_seed = cfg.seed + 1
        low_sim = simulate_heston_paths(
            model,
            n_low_paths,
            cfg.n_steps,
            low_seed,
            v_integral_mode=cfg.v_integral_mode,
        )
        low_vals = np.zeros((n_low_paths, cfg.n_steps + 1), dtype=float)
        low_vals[:, -1] = option.payoff(low_sim.s[:, -1])
        for step in reversed(range(cfg.n_steps)):
            basis_now = build_heston_vol_basis(low_sim.v[:, step], cfg.vol_basis_degree)
            cont_grid = basis_now @ coeffs[step].T
            cont = _interpolate_rows_at_values(asset_grid, cont_grid, low_sim.s[:, step])
            exercise = option.payoff(low_sim.s[:, step])
            low_vals[:, step] = np.where(cont > exercise, discount * low_vals[:, step + 1], exercise)
        low = float(np.mean(low_vals[:, 0]))
        low = float(max(float(option.payoff(model.s0)), low))
    else:
        raise ValueError(f"Unknown low_mode: {cfg.low_mode}")

    return MethodResult(
        method="heston_hybrid",
        direct_estimator=direct,
        low_estimator=low,
        asset_grid=asset_grid,
        coeffs=coeffs,
        value_paths=value,
        times=sim.times,
        s_paths=sim.s,
        meta={
            "model": "heston",
            "n_asset": cfg.n_asset,
            "n_paths": cfg.n_paths,
            "basis_degree": cfg.vol_basis_degree,
            "seed": cfg.seed,
            "low_mode": cfg.low_mode,
            "v_integral_mode": cfg.v_integral_mode,
        },
    )


def run_heston_standard_lsmc(
    model: HestonParameters,
    option: OptionConfig,
    cfg: HestonSolverConfig,
) -> MethodResult:
    model.validate()
    sim = simulate_heston_paths(
        model,
        cfg.n_paths,
        cfg.n_steps,
        cfg.seed,
        v_integral_mode=cfg.v_integral_mode,
    )
    dt = model.T / cfg.n_steps
    discount = float(np.exp(-model.r * dt))

    values = np.zeros((cfg.n_paths, cfg.n_steps + 1), dtype=float)
    values[:, -1] = option.payoff(sim.s[:, -1])
    coeffs: list[np.ndarray] = [None for _ in range(cfg.n_steps)]
    for step in reversed(range(cfg.n_steps)):
        x = build_heston_state_basis(sim.s[:, step], sim.v[:, step], cfg.state_basis_degree)
        y = discount * values[:, step + 1]
        coeff = ridge_regression(x, y, ridge_lambda=cfg.ridge_lambda)
        continuation = x @ coeff
        exercise = option.payoff(sim.s[:, step])
        values[:, step] = np.maximum(exercise, continuation)
        coeffs[step] = coeff

    direct = float(np.mean(values[:, 0]))

    # simple lower estimator using an out-of-sample policy application
    n_low_paths = cfg.low_paths if cfg.low_paths > 0 else cfg.n_paths
    low_sim = simulate_heston_paths(
        model,
        n_low_paths,
        cfg.n_steps,
        cfg.seed + 1,
        v_integral_mode=cfg.v_integral_mode,
    )
    low_vals = np.zeros((n_low_paths, cfg.n_steps + 1), dtype=float)
    low_vals[:, -1] = option.payoff(low_sim.s[:, -1])
    for step in reversed(range(cfg.n_steps)):
        x_low = build_heston_state_basis(
            low_sim.s[:, step],
            low_sim.v[:, step],
            cfg.state_basis_degree,
        )
        coeff_step = coeffs[step]
        cont = x_low[:, : coeff_step.size] @ coeff_step
        exercise = option.payoff(low_sim.s[:, step])
        low_vals[:, step] = np.where(cont > exercise, discount * low_vals[:, step + 1], exercise)
    low = float(np.mean(low_vals[:, 0]))

    coeffs_array = np.stack(coeffs, axis=0)

    return MethodResult(
        method="heston_lsmc",
        direct_estimator=direct,
        low_estimator=low,
        coeffs=coeffs_array,
        value_paths=values,
        times=low_sim.times,
        s_paths=low_sim.s,
        meta={
            "model": "heston",
            "method": "lsmc",
            "n_paths": cfg.n_paths,
            "low_paths": cfg.low_paths if cfg.low_paths > 0 else cfg.n_paths,
            "n_steps": cfg.n_steps,
            "basis_degree": cfg.state_basis_degree,
            "seed": cfg.seed,
            "v_integral_mode": cfg.v_integral_mode,
        },
    )


def run_table9_table10(cfg: HestonSolverConfig, option: OptionConfig, base_model: HestonParameters) -> tuple[
    dict[int, dict[float, MethodResult]], MethodResult
]:
    table9: dict[int, dict[float, MethodResult]] = {}
    scales = (0.95, 1.0, 1.05)
    for ns in (27, 28, 29):
        run_cfg = HestonSolverConfig(
            n_paths=cfg.n_paths,
            n_steps=cfg.n_steps,
            n_asset=ns,
            hermite_nodes=cfg.hermite_nodes,
            ridge_lambda=cfg.ridge_lambda,
            vol_basis_degree=cfg.vol_basis_degree,
            state_basis_degree=cfg.state_basis_degree,
            seed=cfg.seed,
            v_integral_mode=cfg.v_integral_mode,
            low_mode=cfg.low_mode,
            low_paths=cfg.low_paths,
        )
        row: dict[float, MethodResult] = {}
        for i, scale in enumerate(scales):
            model = HestonParameters(
                s0=base_model.s0 * scale,
                v0=base_model.v0,
                r=base_model.r,
                kappa=base_model.kappa,
                theta=base_model.theta,
                eta=base_model.eta,
                rho=base_model.rho,
                T=base_model.T,
            )
            row[scale] = run_heston_hybrid(model, option, run_cfg)
        table9[ns] = row

    base = HestonParameters(
        s0=base_model.s0,
        v0=base_model.v0,
        r=base_model.r,
        kappa=base_model.kappa,
        theta=base_model.theta,
        eta=base_model.eta,
        rho=base_model.rho,
        T=base_model.T,
    )
    table10 = run_heston_standard_lsmc(base, option, cfg)
    return table9, table10


def _format_scalar(value: float, width: int = 10) -> str:
    return f"{value:{width}.4f}"


def print_table9(table9: dict[int, dict[float, MethodResult]]) -> None:
    print("Table 9 (Heston LSMC-PDE replication)")
    reference = {0.95: 1.6712, 1.0: 1.4507, 1.05: 1.2565}
    print("Reference: 0.95*S0 = 1.6712, S0 = 1.4507, 1.05*S0 = 1.2565")
    print(
        "Ns    Direct(0.95S0)   Low(0.95S0)   d(0.95S0)   Direct(S0)   Low(S0)   d(S0)   Direct(1.05S0)   Low(1.05S0)   d(1.05S0)"
    )
    for ns in sorted(table9.keys()):
        row = table9[ns]
        r095 = row[0.95]
        r10 = row[1.0]
        r105 = row[1.05]
        d095 = r095.direct_estimator - reference[0.95]
        d10 = r10.direct_estimator - reference[1.0]
        d105 = r105.direct_estimator - reference[1.05]
        print(
            f"{ns:<5}"
            + f"{_format_scalar(r095.direct_estimator):>16}"
            + f"{_format_scalar(r095.low_estimator or float('nan')):>16}"
            + f"{d095:+.4f}".rjust(12)
            + f"{_format_scalar(r10.direct_estimator):>14}"
            + f"{_format_scalar(r10.low_estimator or float('nan')):>11}"
            + f"{d10:+.4f}".rjust(10)
            + f"{_format_scalar(r105.direct_estimator):>17}"
            + f"{_format_scalar(r105.low_estimator or float('nan')):>12}"
            + f"{d105:+.4f}".rjust(13)
        )


def print_table10(lsmc: MethodResult) -> None:
    print("Table 10 (Heston LSMC replication)")
    print("Reference direct=1.4494, low=1.4487")
    print(f"Direct: {_format_scalar(lsmc.direct_estimator)}  d={lsmc.direct_estimator - 1.4494:+.4f}")
    print(
        f"Low   : {_format_scalar(float(lsmc.low_estimator) if lsmc.low_estimator is not None else float('nan'))}  "
        f"d={float(lsmc.low_estimator) - 1.4487:+.4f}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Recreate Table 9 and Table 10 benchmarks.")
    parser.add_argument("--paths", type=int, default=12000)
    parser.add_argument("--steps", type=int, default=12)
    parser.add_argument("--nodes", type=int, default=16)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--ridge", type=float, default=1e-8)
    parser.add_argument("--vol-degree", type=int, default=3)
    parser.add_argument("--state-degree", type=int, default=3)
    parser.add_argument(
        "--v-integral-mode",
        choices=["left", "midpoint", "trapezoid", "expected"],
        default="left",
        help="How to approximate integrated variance in one-step conditional expectation.",
    )
    parser.add_argument(
        "--low-mode",
        choices=["average_pre", "policy"],
        default="average_pre",
        help="Low-estimator construction used for the Heston hybrid output.",
    )
    parser.add_argument("--low-paths", type=int, default=0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model = HestonParameters()
    option = OptionConfig(strike=10.0, option_type="put")
    cfg = HestonSolverConfig(
        n_paths=args.paths,
        n_steps=args.steps,
        n_asset=27,
        hermite_nodes=args.nodes,
        ridge_lambda=args.ridge,
        vol_basis_degree=args.vol_degree,
        state_basis_degree=args.state_degree,
        seed=args.seed,
        v_integral_mode=args.v_integral_mode,
        low_mode=args.low_mode,
        low_paths=args.low_paths,
    )

    table9, table10 = run_table9_table10(cfg, option, model)
    print_table9(table9)
    print()
    print_table10(table10)


if __name__ == "__main__":
    main()
