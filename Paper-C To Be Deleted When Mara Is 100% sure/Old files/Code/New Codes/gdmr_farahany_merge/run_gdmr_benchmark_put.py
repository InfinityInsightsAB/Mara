#!/usr/bin/env python3
"""
Windows-safe wrapper around the repo's gDMR benchmark LSMC script.

This keeps the repo benchmark logic and env-variable interface unchanged, but
patches TemporaryDirectory cleanup so the script runs directly on Windows even
when memmap files are still being released during teardown.
"""

from __future__ import annotations

import gc
import runpy
import tempfile
from pathlib import Path


TARGET = Path(__file__).resolve().parents[2] / "gdmr_standalone" / "run_gdmr_benchmark_put.py"

_ORIG_CLEANUP = tempfile.TemporaryDirectory.cleanup


def _cleanup(self) -> None:
    gc.collect()
    try:
        _ORIG_CLEANUP(self)
    except PermissionError:
        # Windows can hold the memmap files briefly during teardown.
        pass


tempfile.TemporaryDirectory.cleanup = _cleanup


if __name__ == "__main__":
    runpy.run_path(str(TARGET), run_name="__main__")
