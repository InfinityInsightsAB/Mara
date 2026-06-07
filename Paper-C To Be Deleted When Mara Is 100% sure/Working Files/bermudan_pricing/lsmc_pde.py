"""Backward-compatible alias for the hybrid LSMC--PDE engine."""

from .core.results import MethodResult as PricingResult
from .methods.hybrid.engine import run_farahany_style_hybrid as run_hybrid_pricing

__all__ = ["PricingResult", "run_hybrid_pricing"]
