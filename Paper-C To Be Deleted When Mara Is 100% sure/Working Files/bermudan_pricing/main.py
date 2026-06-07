"""CLI for running Bermudan pricing experiments."""

from __future__ import annotations

import argparse
import numpy as np

from .config import GDMRParameters, OptionConfig, SolverConfig
from .methods.hybrid import run_farahany_style_hybrid
from .methods.lsmc_baseline import run_standard_lsmc
from .experiments.compare_methods import run_and_print


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run Bermudan pricing experiments.")
    p.add_argument("--paths", type=int, default=500, help="Number of Monte Carlo paths.")
    p.add_argument("--steps", type=int, default=12, help="Number of Bermudan exercise steps.")
    p.add_argument("--nodes", type=int, default=16, help="Hermite quadrature nodes.")
    p.add_argument("--seed", type=int, default=2026, help="Random seed.")
    p.add_argument(
        "--method",
        choices=["hybrid", "lsmc", "compare"],
        default="hybrid",
        help="hybrid: Farahany-style mixed LSMC-PDE; lsmc: standard LSMC; compare: run both.",
    )
    p.add_argument(
        "--basis-degree",
        choices=["1", "2"],
        default="1",
        help="1=linear basis [1,v,v'], 2=quadratic with cross term.",
    )
    p.add_argument("--strike", type=float, default=100.0, help="Bermudan strike.")
    p.add_argument("--option-type", choices=["call", "put"], default="put")
    p.add_argument(
        "--ridge",
        type=float,
        default=1e-8,
        help="Ridge regularization on regression normal equations.",
    )
    p.add_argument("--s0", type=float, default=100.0, help="Initial spot.")
    return p.parse_args()


def make_solver_config(args: argparse.Namespace) -> SolverConfig:
    return SolverConfig(
        n_paths=args.paths,
        n_steps=args.steps,
        hermite_nodes=args.nodes,
        seed=args.seed,
        ridge_lambda=args.ridge,
        include_cross_term=args.basis_degree == "2",
    )


def main() -> None:
    args = parse_args()
    option = OptionConfig(strike=args.strike, option_type=args.option_type)
    model = GDMRParameters(s0=args.s0)
    solver = make_solver_config(args)

    if args.method == "hybrid":
        result = run_farahany_style_hybrid(model, option, solver)
        print("Hybrid (Farahany-style) result")
        print(f"  direct estimator: {result.direct_estimator:.6f}")
        print(f"  low estimator:    {result.low_estimator:.6f}")
        print(f"  paths:            {solver.n_paths}")
        print(f"  steps:            {solver.n_steps}")
        print(f"  asset grid size:  {solver.n_asset}")
        if result.coeffs is not None:
            print(f"  coefficient shape: {result.coeffs.shape}")
        if result.value_paths is not None:
            ratio = float(np.mean(np.isfinite(result.value_paths)))
            print(f"  finite value ratio: {ratio:.3f}")
    elif args.method == "lsmc":
        result = run_standard_lsmc(model, option, solver)
        print("Standard LSMC result")
        print(f"  direct estimator: {result.direct_estimator:.6f}")
        print(f"  paths:            {solver.n_paths}")
        print(f"  steps:            {solver.n_steps}")
    else:
        run_and_print(model, option, solver)


if __name__ == "__main__":
    main()
