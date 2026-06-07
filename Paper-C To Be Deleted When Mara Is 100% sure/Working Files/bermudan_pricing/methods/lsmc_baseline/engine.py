"""Standard LSMC method for Bermudan pricing in the same model."""

from __future__ import annotations

import numpy as np

from ...core import GDMRParameters, MethodResult, OptionConfig, SolverConfig
from ...core.numerics import build_lsmbasis_state, ridge_regression
from ...core.sim import simulate_gdmr_paths


def run_standard_lsmc(
    model: GDMRParameters,
    option: OptionConfig,
    solver: SolverConfig,
) -> MethodResult:
    sim = simulate_gdmr_paths(model, solver.n_paths, solver.n_steps, solver.T, solver.seed)
    dt = solver.T / solver.n_steps
    discount = float(np.exp(-model.r * dt))

    terminal = option.payoff(sim.s[:, -1])  # vector length n_paths
    value_paths = np.zeros((solver.n_paths, solver.n_steps + 1), dtype=float)
    value_paths[:, -1] = terminal

    for step in reversed(range(solver.n_steps)):
        exercise = option.payoff(sim.s[:, step])
        # regress discounted continuation value on a polynomial state basis
        X = build_lsmbasis_state(sim.s[:, step], sim.v[:, step], sim.v_prime[:, step], max_order=2)
        y = discount * value_paths[:, step + 1]
        coeff = ridge_regression(X, y, ridge_lambda=solver.ridge_lambda)
        continuation = X @ coeff
        value_paths[:, step] = np.maximum(exercise, continuation)

    # start at same state, but keep Monte Carlo mean for consistency with standard LSMC practice
    direct = float(np.mean(value_paths[:, 0]))
    return MethodResult(
        method="standard_lsmc",
        direct_estimator=direct,
        low_estimator=None,
        value_paths=value_paths,
        times=sim.times,
        s_paths=sim.s,
        coeffs=coeff[:, None],  # not directly comparable but kept for diagnostic shape
        meta={"discount": discount, "basis_size": value_paths.shape[0], "paths": solver.n_paths},
    )
