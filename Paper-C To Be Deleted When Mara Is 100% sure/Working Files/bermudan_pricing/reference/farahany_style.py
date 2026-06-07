"""Reference implementation that mirrors the mixed LSMC--PDE structure in the paper."""

from __future__ import annotations

from ..core import GDMRParameters, MethodResult, OptionConfig, SolverConfig
from ..methods.hybrid.engine import run_farahany_style_hybrid as _run_hybrid


def run_farahany_style_hybrid(
    model: GDMRParameters,
    option: OptionConfig,
    solver: SolverConfig,
) -> MethodResult:
    result = _run_hybrid(model, option, solver)
    # preserve naming to make comparison logs explicit.
    return MethodResult(
        method="farahany_repro",
        direct_estimator=result.direct_estimator,
        low_estimator=result.low_estimator,
        asset_grid=result.asset_grid,
        coeffs=result.coeffs,
        value_paths=result.value_paths,
        times=result.times,
        s_paths=result.s_paths,
        meta=result.meta | {"reference": "farahany_2020"},
    )
