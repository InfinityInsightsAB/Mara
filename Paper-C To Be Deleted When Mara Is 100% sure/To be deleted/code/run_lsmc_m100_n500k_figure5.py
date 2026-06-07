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
ENGINE_DIR = ROOT / "engine"
RESULTS_DIR = ROOT / "results"
LOGS_DIR = ROOT / "logs"
SCRATCH_DIR = ROOT / "scratch"
BENCHMARK_SCRIPT = ENGINE_DIR / "run_bgk_r03_benchmark_put.py"
OUTPUT_CSV = RESULTS_DIR / "lsmc_m100_n500k_figure5_benchmark.csv"


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

# Direct LSMC references used for Figure 5 in main_springer.pdf:
# robustness-case path sweep, M_ref=1200, N_ref=1,200,000.
FIGURE5_BENCHMARKS = [
    ("K=70 put", 70.0, 3.363539, 0.009321),
    ("K=80 put", 80.0, 4.961218, 0.011651),
    ("OTM put", 90.0, 7.082115, 0.014052),
    ("ATM", 100.0, 9.921221, 0.016333),
    ("ITM put", 110.0, 13.857272, 0.017759),
]

FIELDS = [
    "study",
    "figure",
    "scenario",
    "K",
    "euler_steps",
    "paths",
    "low_paths",
    "seed",
    "low_seed",
    "price_direct",
    "se_direct",
    "ci_width_direct",
    "price_low",
    "se_low",
    "direct_low_gap",
    "benchmark_direct_price",
    "benchmark_direct_se",
    "benchmark_euler_steps",
    "benchmark_paths",
    "rel_error_direct",
    "rel_ci_lower_direct",
    "rel_ci_upper_direct",
    "runtime_seconds",
    "r",
    "delta1",
    "delta2",
    "v0",
    "vp0",
    "T",
    "exercise_dates",
    "benchmark_engine_sha256",
]


def ensure_dirs() -> None:
    for path in (RESULTS_DIR, LOGS_DIR, SCRATCH_DIR):
        path.mkdir(parents=True, exist_ok=True)


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


def rel_error(value: float, reference: float) -> float:
    return abs(value - reference) / abs(reference)


def rel_error_ci_bounds(value: float, se: float, reference: float) -> tuple[float, float]:
    low = value - 1.96 * se
    high = value + 1.96 * se
    endpoint_errors = (rel_error(low, reference), rel_error(high, reference))
    if low <= reference <= high:
        return 0.0, max(endpoint_errors)
    return min(endpoint_errors), max(endpoint_errors)


def assert_provenance(result: dict[str, Any], strike: float) -> None:
    expected_float = {
        "K": strike,
        "r": 0.02,
        "delta1": 0.5,
        "delta2": 0.5,
        "v0": 0.114,
        "vp0": 0.110,
        "T": 1.0,
    }
    for key, expected in expected_float.items():
        actual = finite(result[key])
        if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-12):
            raise RuntimeError(f"Unexpected {key}: got {actual}, expected {expected}")
    if int(result["exercise_dates"]) != 12:
        raise RuntimeError(f"Unexpected exercise_dates: {result['exercise_dates']}")
    if int(result["euler_steps"]) != 100:
        raise RuntimeError(f"Unexpected euler_steps: {result['euler_steps']}")
    if int(result["paths"]) != 500000:
        raise RuntimeError(f"Unexpected paths: {result['paths']}")


def run_one(scenario: str, strike: float, ref: float, ref_se: float) -> dict[str, Any]:
    existing = read_rows(OUTPUT_CSV)
    for row in existing:
        if row.get("K") == f"{strike:.0f}" and row.get("euler_steps") == "100" and row.get("paths") == "500000":
            print(f"[skip] K={strike:.0f} already exists", flush=True)
            return row

    env = os.environ.copy()
    env.update(MODEL_ENV)
    env.update(
        {
            "GDMR_STRIKE": f"{strike:.1f}",
            "GDMR_EULER_STEPS": "100",
            "GDMR_LSMC_PATHS": "500000",
            "GDMR_LSMC_LOW_PATHS": "500000",
            "GDMR_LSMC_SEED": "2026",
            "GDMR_LSMC_LOW_SEED": "2103",
            "GDMR_LSMC_ITM_ONLY": "0",
            "GDMR_LSMC_STORE_DIR": str(SCRATCH_DIR / "lsmc_m100_n500k"),
        }
    )
    label = f"lsmc_m100_n500k_K{strike:.0f}"
    log_path = LOGS_DIR / f"{label}.log"
    print(f"[run] K={strike:.0f}, M=100, N=500000", flush=True)
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
        raise RuntimeError(f"LSMC run failed for K={strike:.0f}. See {log_path}")
    result_line = None
    for line in reversed(completed.stdout.splitlines()):
        if line.startswith("RESULT_JSON: "):
            result_line = line[len("RESULT_JSON: ") :]
            break
    if result_line is None:
        raise RuntimeError(f"Missing RESULT_JSON in {log_path}")
    result = json.loads(result_line)
    assert_provenance(result, strike)

    direct = finite(result["lsmc_direct_price"])
    se = finite(result["lsmc_direct_error"])
    low = finite(result["lsmc_low_price"])
    low_se = finite(result["lsmc_low_error"])
    rel_low, rel_high = rel_error_ci_bounds(direct, se, ref)
    row = {
        "study": "lsmc_m100_n500k_against_figure5_benchmark",
        "figure": "main_springer.pdf Figure 5",
        "scenario": scenario,
        "K": f"{strike:.0f}",
        "euler_steps": "100",
        "paths": "500000",
        "low_paths": "500000",
        "seed": int(result["seed"]),
        "low_seed": int(result["low_seed"]),
        "price_direct": f"{direct:.12f}",
        "se_direct": f"{se:.12f}",
        "ci_width_direct": f"{3.92 * se:.12f}",
        "price_low": f"{low:.12f}",
        "se_low": f"{low_se:.12f}",
        "direct_low_gap": f"{abs(direct - low) / abs(direct):.12f}",
        "benchmark_direct_price": f"{ref:.6f}",
        "benchmark_direct_se": f"{ref_se:.6f}",
        "benchmark_euler_steps": "1200",
        "benchmark_paths": "1200000",
        "rel_error_direct": f"{rel_error(direct, ref):.12f}",
        "rel_ci_lower_direct": f"{rel_low:.12f}",
        "rel_ci_upper_direct": f"{rel_high:.12f}",
        "runtime_seconds": f"{runtime:.6f}",
        "r": f"{finite(result['r']):.12g}",
        "delta1": f"{finite(result['delta1']):.12g}",
        "delta2": f"{finite(result['delta2']):.12g}",
        "v0": f"{finite(result['v0']):.12g}",
        "vp0": f"{finite(result['vp0']):.12g}",
        "T": f"{finite(result['T']):.12g}",
        "exercise_dates": int(result["exercise_dates"]),
        "benchmark_engine_sha256": file_hash(BENCHMARK_SCRIPT),
    }
    all_rows = [old for old in existing if old.get("K") != f"{strike:.0f}"]
    all_rows.append(row)
    write_rows(all_rows)
    return row


def main() -> None:
    ensure_dirs()
    for scenario, strike, ref, ref_se in FIGURE5_BENCHMARKS:
        run_one(scenario, strike, ref, ref_se)


if __name__ == "__main__":
    main()
