#!/usr/bin/env python3
"""
Wrapper around the Farahany-leaning FST/FFT gDMR hybrid script.

This keeps the gDMR Bermudan-option model, the FST/FFT conditional solver, and
the hybrid low-estimator recursion from the `gdmr_fst_swap_scripts` branch.
"""

from __future__ import annotations

import runpy
from pathlib import Path


TARGET = Path(__file__).resolve().parents[1] / "gdmr_fst_swap_scripts" / "run_gdmr_hybrid_put.py"


if __name__ == "__main__":
    runpy.run_path(str(TARGET), run_name="__main__")
