#!/usr/bin/env python3
"""
Compare the final-package gDMR LSMC benchmark against the Farahany-style FST hybrid.

Both scripts live inside `Final Code`, so the package is self-contained.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
BENCHMARK_SCRIPT = THIS_DIR / "LSMC Benchmark" / "run_gdmr_benchmark_put.py"
HYBRID_SCRIPT = THIS_DIR / "Hybrid LSMC-PDE with FFT" / "run_gdmr_hybrid_put.py"

BENCHMARK_PATTERNS = {
    "lsmc_direct_price": r"LSMC direct price:\s*([0-9eE+\-.]+)",
    "lsmc_direct_error": r"LSMC direct error:\s*([0-9eE+\-.]+)",
    "lsmc_low_price": r"LSMC low price:\s*([0-9eE+\-.]+)",
    "lsmc_low_error": r"LSMC low error:\s*([0-9eE+\-.]+)",
}


def rel_error(value: float, reference: float) -> float:
    if abs(reference) <= 1e-16:
        return 0.0 if abs(value) <= 1e-16 else float("inf")
    return abs(value - reference) / abs(reference)


def gap_pct(low: float, direct: float) -> float:
    if abs(direct) <= 1e-16:
        return float("inf")
    return (low - direct) / direct


def run_benchmark() -> tuple[dict[str, float], str]:
    completed = subprocess.run(
        [sys.executable, str(BENCHMARK_SCRIPT)],
        cwd=str(THIS_DIR),
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=True,
    )
    stdout = completed.stdout
    values: dict[str, float] = {}
    for key, pattern in BENCHMARK_PATTERNS.items():
        match = re.search(pattern, stdout)
        if not match:
            raise RuntimeError(f"Could not parse {key} from benchmark output.\n{stdout}")
        values[key] = float(match.group(1))
    return values, stdout


def run_hybrid() -> tuple[dict[str, float], str]:
    completed = subprocess.run(
        [sys.executable, str(HYBRID_SCRIPT)],
        cwd=str(THIS_DIR),
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=True,
    )
    stdout = completed.stdout
    result_line = None
    for line in stdout.splitlines()[::-1]:
        if line.startswith("RESULT_JSON: "):
            result_line = line[len("RESULT_JSON: "):]
            break
    if result_line is None:
        raise RuntimeError(f"Could not parse RESULT_JSON from hybrid output.\n{stdout}")
    raw = json.loads(result_line)
    values = {
        "hybrid_direct_price": float(raw["hybrid_direct_price"]),
        "hybrid_direct_error": float(raw["hybrid_direct_error"]),
        "hybrid_low_price": float(raw["hybrid_low_price"]),
        "hybrid_low_error": float(raw["hybrid_low_error"]),
    }
    return values, stdout


if __name__ == "__main__":
    benchmark, benchmark_stdout = run_benchmark()
    hybrid, hybrid_stdout = run_hybrid()

    direct_rel = rel_error(hybrid["hybrid_direct_price"], benchmark["lsmc_direct_price"])
    low_rel = rel_error(hybrid["hybrid_low_price"], benchmark["lsmc_low_price"])
    benchmark_gap = gap_pct(benchmark["lsmc_low_price"], benchmark["lsmc_direct_price"])
    hybrid_gap = gap_pct(hybrid["hybrid_low_price"], hybrid["hybrid_direct_price"])

    print("gDMR Bermudan put: repo LSMC benchmark vs Farahany-style FST hybrid")
    print("===================================================================")
    print(f"Benchmark script: {BENCHMARK_SCRIPT.name}")
    print(f"Hybrid script:    {HYBRID_SCRIPT.name}")
    print()
    print("Benchmark LSMC")
    print(f"  direct price: {benchmark['lsmc_direct_price']:.6f} +/- {benchmark['lsmc_direct_error']:.6f}")
    print(f"  low price:    {benchmark['lsmc_low_price']:.6f} +/- {benchmark['lsmc_low_error']:.6f}")
    print()
    print("FST Hybrid")
    print(f"  direct price: {hybrid['hybrid_direct_price']:.6f} +/- {hybrid['hybrid_direct_error']:.6f}")
    print(f"  low price:    {hybrid['hybrid_low_price']:.6f} +/- {hybrid['hybrid_low_error']:.6f}")
    print()
    print("Headline comparison")
    print(f"  Hybrid direct relerr vs benchmark LSMC direct: {100.0 * direct_rel:.2f}%")
    print(f"  Hybrid low relerr vs benchmark LSMC low:       {100.0 * low_rel:.2f}%")
    print(f"  Benchmark direct-low gap:                      {100.0 * benchmark_gap:+.2f}%")
    print(f"  Hybrid direct-low gap:                         {100.0 * hybrid_gap:+.2f}%")
    print()
    print("RAW_BENCHMARK_STDOUT:")
    print(benchmark_stdout.rstrip())
    print()
    print("RAW_HYBRID_STDOUT:")
    print(hybrid_stdout.rstrip())
