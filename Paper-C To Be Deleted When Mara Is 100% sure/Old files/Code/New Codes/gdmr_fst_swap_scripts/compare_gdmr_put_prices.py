#!/usr/bin/env python3
"""
Run the standalone gDMR Bermudan put pricers and compare their outputs.

It launches:
- run_gdmr_lsmc_put.py
- run_gdmr_hybrid_put_fst.py

and prints a small comparison report. The scripts inherit the current shell
environment, so any GDMR_* overrides you set are passed through automatically.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def run_script(script_path: Path) -> tuple[dict, str]:
    completed = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
        env=os.environ.copy(),
        check=False,
    )
    output = completed.stdout
    if completed.returncode != 0:
        raise RuntimeError(
            f"Script failed: {script_path.name}\n"
            f"Return code: {completed.returncode}\n"
            f"STDOUT:\n{completed.stdout}\n"
            f"STDERR:\n{completed.stderr}"
        )

    result_line = None
    for line in output.splitlines()[::-1]:
        if line.startswith("RESULT_JSON: "):
            result_line = line[len("RESULT_JSON: "):]
            break
    if result_line is None:
        raise RuntimeError(f"No RESULT_JSON line found in {script_path.name} output.")
    return json.loads(result_line), output


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent
    lsmc_path = base_dir / "run_gdmr_lsmc_put.py"
    hybrid_path = base_dir / "run_gdmr_hybrid_put.py"

    lsmc, lsmc_stdout = run_script(lsmc_path)
    hybrid, hybrid_stdout = run_script(hybrid_path)

    print("Comparison of gDMR Bermudan put pricers")
    print("========================================")
    print(f"LSMC script:   {lsmc_path.name}")
    print(f"Hybrid script: {hybrid_path.name}")
    print()
    print("LSMC")
    print(f"  direct price: {lsmc['lsmc_direct_price']:.6f} ± {lsmc['lsmc_direct_error']:.6f}")
    print(f"  low price:    {lsmc['lsmc_low_price']:.6f} ± {lsmc['lsmc_low_error']:.6f}")
    print()
    print("Hybrid LSMC-PDE (FST)")
    print(f"  direct price: {hybrid['hybrid_direct_price']:.6f} ± {hybrid['hybrid_direct_error']:.6f}")
    print(f"  low price:    {hybrid['hybrid_low_price']:.6f} ± {hybrid['hybrid_low_error']:.6f}")
    print()
    print("Differences")
    print(f"  direct (hybrid - lsmc): {hybrid['hybrid_direct_price'] - lsmc['lsmc_direct_price']:+.6f}")
    print(f"  low    (hybrid - lsmc): {hybrid['hybrid_low_price'] - lsmc['lsmc_low_price']:+.6f}")
    print()
    print("Notes")
    print(f"  LSMC time-zero exercise in low:   {lsmc['time_zero_exercise_in_low']}")
    print(f"  Hybrid time-zero exercise in low: {hybrid['time_zero_exercise_in_low']}")
    print()
    print("RAW_LSMC_JSON: " + json.dumps(lsmc, sort_keys=True))
    print("RAW_HYBRID_JSON: " + json.dumps(hybrid, sort_keys=True))
