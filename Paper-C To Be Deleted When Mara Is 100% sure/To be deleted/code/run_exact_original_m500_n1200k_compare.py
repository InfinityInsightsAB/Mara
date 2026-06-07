from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ENGINE_DIR = ROOT / "benchmark_code_exact"
RESULTS_DIR = ROOT / "results"
LOGS_DIR = ROOT / "logs"
SCRATCH_DIR = ROOT / "scratch"
BENCHMARK_SCRIPT = ENGINE_DIR / "run_bgk_r03_benchmark_put.py"
PREVIOUS_CSV = RESULTS_DIR / "lsmc_m500_n1200k_benchmark_compare.csv"
OUTPUT_CSV = RESULTS_DIR / "exact_original_m500_n1200k_compare.csv"

MODEL_ENV = {
    "GDMR_S0": "100.0",
    "GDMR_V0": "0.114",
    "GDMR_VP0": "0.110",
    "GDMR_R": "0.02",
    "GDMR_KAPPA1": "5.5",
    "GDMR_KAPPA2": "0.1",
    "GDMR_THETA": "0.078",
    "GDMR_XI1": "2.689",
    "GDMR_XI2": "0.502",
    "GDMR_DELTA1": "0.5",
    "GDMR_DELTA2": "0.5",
    "GDMR_RHO12": "-0.982",
    "GDMR_RHO13": "-0.727",
    "GDMR_RHO23": "0.59",
    "GDMR_MATURITY": "1.0",
    "GDMR_EXERCISE_DATES": "12",
}

TARGETS = [("OTM put", 90.0), ("ATM", 100.0)]

FIELDS = [
    "study",
    "scenario",
    "K",
    "euler_steps",
    "paths",
    "low_paths",
    "seed",
    "low_seed",
    "price_direct",
    "se_direct",
    "previous_m500_price_direct",
    "abs_difference_from_previous_m500",
    "figure5_benchmark_direct_price",
    "relative_error_vs_figure5_benchmark",
    "price_low",
    "se_low",
    "r",
    "delta1",
    "delta2",
    "v0",
    "vp0",
    "T",
    "exercise_dates",
    "runtime_seconds",
    "benchmark_engine_sha256",
    "code_path",
    "log_path",
]


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_rows(rows: list[dict[str, Any]]) -> None:
    rows = sorted(rows, key=lambda row: float(row["K"]))
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})


def finite(value: Any) -> float:
    out = float(value)
    if not math.isfinite(out):
        raise RuntimeError(f"Non-finite value {value}")
    return out


def previous_row(strike: float) -> dict[str, str]:
    for row in read_rows(PREVIOUS_CSV):
        if row.get("K") == f"{strike:.0f}":
            return row
    raise RuntimeError(f"Missing previous M=500 row for K={strike:.0f}")


def run_one(scenario: str, strike: float) -> dict[str, Any]:
    env = os.environ.copy()
    env.update(MODEL_ENV)
    env.update(
        {
            "GDMR_STRIKE": f"{strike:.1f}",
            "GDMR_EULER_STEPS": "500",
            "GDMR_LSMC_PATHS": "1200000",
            "GDMR_LSMC_LOW_PATHS": "1200000",
            "GDMR_LSMC_SEED": "2026",
            "GDMR_LSMC_LOW_SEED": "2103",
            "GDMR_LSMC_STORE_DIR": str(SCRATCH_DIR / "exact_original_m500_n1200k"),
        }
    )
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / f"exact_original_m500_n1200k_K{strike:.0f}.log"
    start = time.perf_counter()
    completed = subprocess.run(
        [sys.executable, str(BENCHMARK_SCRIPT)],
        cwd=str(ENGINE_DIR),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    runtime = time.perf_counter() - start
    log_path.write_text(
        "COMMAND: "
        + " ".join([sys.executable, str(BENCHMARK_SCRIPT)])
        + "\n\nSTDOUT:\n"
        + completed.stdout
        + "\n\nSTDERR:\n"
        + completed.stderr
        + f"\n\nEXIT_CODE: {completed.returncode}\nRUNTIME_SECONDS: {runtime:.6f}\n",
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise RuntimeError(f"Run failed for K={strike:.0f}. See {log_path}")
    result_line = None
    for line in reversed(completed.stdout.splitlines()):
        if line.startswith("RESULT_JSON: "):
            result_line = line[len("RESULT_JSON: ") :]
            break
    if result_line is None:
        raise RuntimeError(f"Missing RESULT_JSON in {log_path}")
    result = json.loads(result_line)

    expected = {
        "K": strike,
        "r": 0.02,
        "delta1": 0.5,
        "delta2": 0.5,
        "v0": 0.114,
        "vp0": 0.110,
        "T": 1.0,
    }
    for key, value in expected.items():
        if not math.isclose(finite(result[key]), value, rel_tol=0.0, abs_tol=1e-12):
            raise RuntimeError(f"Unexpected {key}: {result[key]} != {value}")
    if int(result["euler_steps"]) != 500 or int(result["paths"]) != 1_200_000:
        raise RuntimeError("Unexpected M/N provenance")
    if int(result["exercise_dates"]) != 12:
        raise RuntimeError("Unexpected exercise_dates")

    previous = previous_row(strike)
    previous_price = finite(previous["benchmark_price_direct"])
    figure5_benchmark = 7.082115 if int(strike) == 90 else 9.921221
    price = finite(result["lsmc_direct_price"])
    return {
        "study": "exact_original_m500_n1200k_compare",
        "scenario": scenario,
        "K": f"{strike:.0f}",
        "euler_steps": int(result["euler_steps"]),
        "paths": int(result["paths"]),
        "low_paths": int(result["low_paths"]),
        "seed": int(result["seed"]),
        "low_seed": int(result["low_seed"]),
        "price_direct": f"{price:.12f}",
        "se_direct": f"{finite(result['lsmc_direct_error']):.12f}",
        "previous_m500_price_direct": f"{previous_price:.12f}",
        "abs_difference_from_previous_m500": f"{abs(price - previous_price):.12f}",
        "figure5_benchmark_direct_price": f"{figure5_benchmark:.6f}",
        "relative_error_vs_figure5_benchmark": f"{abs(price - figure5_benchmark) / abs(figure5_benchmark):.12f}",
        "price_low": f"{finite(result['lsmc_low_price']):.12f}",
        "se_low": f"{finite(result['lsmc_low_error']):.12f}",
        "r": result["r"],
        "delta1": result["delta1"],
        "delta2": result["delta2"],
        "v0": result["v0"],
        "vp0": result["vp0"],
        "T": result["T"],
        "exercise_dates": result["exercise_dates"],
        "runtime_seconds": f"{runtime:.6f}",
        "benchmark_engine_sha256": file_hash(BENCHMARK_SCRIPT),
        "code_path": str(BENCHMARK_SCRIPT),
        "log_path": str(log_path),
    }


def main() -> None:
    rows = [run_one(scenario, strike) for scenario, strike in TARGETS]
    write_rows(rows)
    for row in rows:
        print(
            f"K={row['K']} price={row['price_direct']} "
            f"prev_diff={row['abs_difference_from_previous_m500']} "
            f"rel_vs_fig5={row['relative_error_vs_figure5_benchmark']}",
            flush=True,
        )


if __name__ == "__main__":
    main()
