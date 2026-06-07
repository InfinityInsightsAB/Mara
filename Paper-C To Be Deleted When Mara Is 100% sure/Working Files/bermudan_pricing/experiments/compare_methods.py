"""Run the same model through multiple pricers and compare outputs."""

from __future__ import annotations

from dataclasses import dataclass
import argparse
import numpy as np

from ..core import GDMRParameters, OptionConfig, SolverConfig
from ..reference.farahany_style import run_farahany_style_hybrid
from ..methods.lsmc_baseline.engine import run_standard_lsmc


@dataclass
class ComparisonSummary:
    farahany: float
    standard_lsmc: float
    abs_diff: float
    rel_diff: float | None


def run_comparison(
    model: GDMRParameters,
    option: OptionConfig,
    solver: SolverConfig,
) -> ComparisonSummary:
    far = run_farahany_style_hybrid(model, option, solver)
    lsmc = run_standard_lsmc(model, option, solver)
    far_est = far.direct_estimator
    lsmc_est = lsmc.direct_estimator
    abs_diff = abs(far_est - lsmc_est)
    rel_diff = abs_diff / abs(lsmc_est) if lsmc_est != 0 else None
    return ComparisonSummary(
        farahany=far_est,
        standard_lsmc=lsmc_est,
        abs_diff=abs_diff,
        rel_diff=rel_diff,
    )


def _as_float(x: float) -> str:
    return f"{x:,.8f}"


def print_comparison(summary: ComparisonSummary) -> None:
    print("Method comparison (same model, same setup)")
    print(f"Farahany-repro price: {_as_float(summary.farahany)}")
    print(f"Standard LSMC price: {_as_float(summary.standard_lsmc)}")
    print(f"Absolute diff:       {_as_float(summary.abs_diff)}")
    if summary.rel_diff is None:
        print("Relative diff:       undefined (LSMC close to 0)")
    else:
        print(f"Relative diff:       {100.0 * summary.rel_diff:.8f}%")


def run_and_print(
    model: GDMRParameters,
    option: OptionConfig,
    solver: SolverConfig,
) -> ComparisonSummary:
    out = run_comparison(model, option, solver)
    print_comparison(out)
    return out


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Compare Farahany-style hybrid vs standard LSMC under a common setup."
    )
    p.add_argument("--paths", type=int, default=500, help="Number of Monte Carlo paths.")
    p.add_argument("--steps", type=int, default=12, help="Number of Bermudan exercise steps.")
    p.add_argument("--nodes", type=int, default=16, help="Hermite quadrature nodes.")
    p.add_argument("--seed", type=int, default=2026, help="Random seed.")
    p.add_argument("--strike", type=float, default=100.0, help="Bermudan strike.")
    p.add_argument("--option-type", choices=["call", "put"], default="put")
    p.add_argument("--s0", type=float, default=100.0, help="Initial spot.")
    p.add_argument(
        "--basis-degree",
        choices=["1", "2"],
        default="1",
        help="Hybrid basis: 1=linear vol basis, 2=quadratic with cross term.",
    )
    p.add_argument("--ridge", type=float, default=1e-8, help="Ridge regularization.")
    return p


def main() -> None:
    args = parse_args().parse_args()
    model = GDMRParameters(s0=args.s0)
    option = OptionConfig(strike=args.strike, option_type=args.option_type)
    solver = SolverConfig(
        n_paths=args.paths,
        n_steps=args.steps,
        hermite_nodes=args.nodes,
        seed=args.seed,
        ridge_lambda=args.ridge,
        include_cross_term=args.basis_degree == "2",
    )
    result = run_comparison(model, option, solver)
    print_comparison(result)
