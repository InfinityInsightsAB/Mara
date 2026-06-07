"""Hybrid LSMC-PDE pricing engine."""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass

from ...core import (
    GDMRParameters,
    MethodResult,
    OptionConfig,
    SolverConfig,
)
from ...core.numerics import (
    build_asset_grid,
    build_vol_basis,
    ridge_regression,
)
from ...core.sim import projection_coefficients, simulate_gdmr_paths
from .pde import conditional_expectation_one_step


def _interpolate_rows_at_value(x_grid: np.ndarray, y_grid: np.ndarray, x: float) -> np.ndarray:
    log_x_grid = np.log(x_grid)
    lx = np.log(x)
    return np.array([np.interp(lx, log_x_grid, y_row, left=float(y_row[0]), right=float(y_row[-1])) for y_row in y_grid], dtype=float)


def run_farahany_style_hybrid(
    model: GDMRParameters,
    option: OptionConfig,
    solver: SolverConfig,
) -> MethodResult:
    """Baseline implementation of the mixed LSMC-PDE setup."""
    sim = simulate_gdmr_paths(model, solver.n_paths, solver.n_steps, solver.T, solver.seed)

    asset_grid = build_asset_grid(
        model.s0,
        option.strike,
        solver.n_asset,
        solver.s_grid_low_factor,
        solver.s_grid_high_factor,
    )
    payoff_grid = option.payoff(asset_grid)

    dt = solver.T / solver.n_steps
    discount = float(np.exp(-model.r * dt))
    beta2, beta3, sigma_perp_sq = projection_coefficients(model.rho12, model.rho13, model.rho23)
    del beta2, beta3

    n_paths = solver.n_paths
    n_steps = solver.n_steps
    n_asset = solver.n_asset

    coeffs = np.zeros((n_steps, n_asset, 4 if solver.include_cross_term else 3), dtype=float)
    value = np.zeros((n_paths, n_steps + 1, n_asset), dtype=float)
    value[:, -1, :] = payoff_grid[None, :]
    pre_surface_t0 = None

    for step in reversed(range(n_steps)):
        terminal = value[:, step + 1, :]
        pre_surface = np.zeros((n_paths, n_asset), dtype=float)

        for j in range(n_paths):
            shift = float(sim.drift_shift[j, step] + sim.correlated_shift[j, step])
            variance = sigma_perp_sq * sim.v_integral[j, step]
            pre_surface[j, :] = discount * conditional_expectation_one_step(
                asset_grid=asset_grid,
                terminal_values=terminal[j, :],
                mean_log_shift=shift,
                variance=variance,
                hermite_nodes=solver.hermite_nodes,
            )

        if step == 0:
            pre_surface_t0 = pre_surface.copy()

        basis_now = build_vol_basis(sim.v[:, step], sim.v_prime[:, step], include_cross_term=solver.include_cross_term)
        cont_completed = np.zeros((n_paths, n_asset), dtype=float)
        for i in range(n_asset):
            coeff = ridge_regression(
                basis_now,
                pre_surface[:, i],
                ridge_lambda=solver.ridge_lambda,
            )
            coeffs[step, i, : coeff.size] = coeff
            cont_completed[:, i] = basis_now @ coeff

        value[:, step, :] = np.maximum(payoff_grid[None, :], cont_completed)

    continuation_at_s0 = _interpolate_rows_at_value(
        asset_grid,
        coeffs[0].T,
        model.s0,
    )
    basis0 = build_vol_basis(
        np.array([model.v0]),
        np.array([model.v0_prime]),
        include_cross_term=solver.include_cross_term,
    )[0]
    direct_cont = float(continuation_at_s0 @ basis0)
    direct = float(max(float(option.payoff(model.s0)), direct_cont))

    if pre_surface_t0 is None:
        raise RuntimeError("Could not capture first-step pre-surface.")
    low_cont = float(np.mean(_interpolate_rows_at_value(asset_grid, pre_surface_t0, model.s0)))
    low = float(max(float(option.payoff(model.s0)), low_cont))

    return MethodResult(
        method="farahany_hybrid_repro",
        direct_estimator=direct,
        low_estimator=low,
        asset_grid=asset_grid,
        coeffs=coeffs,
        value_paths=value,
        times=sim.times,
        s_paths=sim.s,
        meta={"model": "gdmr", "steps": n_steps, "paths": n_paths},
    )
