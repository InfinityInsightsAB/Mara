"""Top-level package exports for model, methods, and experiment helpers."""

from .core import (
    GDMRParameters,
    MethodResult,
    OptionConfig,
    SolverConfig,
    SimulationOutput,
)
from .core import projection_coefficients, simulate_gdmr_paths
from .methods.hybrid.engine import run_farahany_style_hybrid
from .methods.lsmc_baseline.engine import run_standard_lsmc
from .reference.farahany_style import run_farahany_style_hybrid as run_farahany_reference
from .lsmc_pde import run_hybrid_pricing

__all__ = [
    "GDMRParameters",
    "OptionConfig",
    "SolverConfig",
    "MethodResult",
    "run_hybrid_pricing",
    "run_farahany_style_hybrid",
    "run_farahany_reference",
    "run_standard_lsmc",
    "SimulationOutput",
    "projection_coefficients",
    "simulate_gdmr_paths",
    "MethodResult",
]
__version__ = "0.2.0"
