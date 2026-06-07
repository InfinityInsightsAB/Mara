"""Backward-compatible alias for simulation primitives."""

from .core.sim import (
    SimulationOutput,
    projection_coefficients,
    simulate_gdmr_paths,
)

__all__ = ["SimulationOutput", "projection_coefficients", "simulate_gdmr_paths"]
