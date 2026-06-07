from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


RUN_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = RUN_ROOT / "config" / "rerun_config.json"
RESULTS_DIR = RUN_ROOT / "results"
REFERENCE_DIR = RESULTS_DIR / "reference_values"
HIGH_PATH_DIR = RESULTS_DIR / "high_path"
LOG_DIR = RUN_ROOT / "logs" / "high_accuracy"
SCRATCH_DIR = RUN_ROOT / "scratch"
HYBRID_SCRIPT = RUN_ROOT / "code" / "hybrid_from_scratch.py"


def load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def read_benchmarks(case_id: str) -> dict[int, float]:
    path = REFERENCE_DIR / f"{case_id}_benchmark_steps1200_paths1200000_table.csv"
    with path.open("r", newline="", encoding="utf-8") as handle:
        return {int(float(row["K"])): float(row["benchmark_direct_price"]) for row in csv.DictReader(handle)}


def rel_error(price: float, reference: float) -> float:
    return abs(price - reference) / abs(reference)


def rel_ci_bounds(price: float, se: float, reference: float) -> tuple[float, float]:
    ci = 1.96 * se
    low = rel_error(price - ci, reference)
    high = rel_error(price + ci, reference)
    point = rel_error(price, reference)
    if low <= point <= high:
        return low, high
    return min(low, high), max(low, high)


def run_job(config: dict[str, Any], scenario: dict[str, Any], reference: float) -> dict[str, Any]:
    paths = 100_000
    euler_steps = 1200
    env = os.environ.copy()
    env.update({str(k): str(v) for k, v in config["model_env"].items()})
    env.update(
        {
            "GDMR_HYBRID_ASSET_POINTS": "601",
            "GDMR_HYBRID_ASSET_LOW_FACTOR": "0.10",
            "GDMR_HYBRID_ASSET_HIGH_FACTOR": "5.00",
            "GDMR_HYBRID_VOL_QUANTILE": "0.999",
            "GDMR_HYBRID_FST_PAD_FACTOR": "4",
            "GDMR_HYBRID_FST_BATCH_SIZE": "256",
        }
    )
    env["GDMR_STRIKE"] = str(scenario["K"])
    env["GDMR_EULER_STEPS"] = str(euler_steps)
    env["GDMR_HYBRID_PATHS"] = str(paths)
    env["GDMR_HYBRID_LOW_PATHS"] = "1000"
    env["GDMR_HYBRID_SEED"] = str(config["seeds"]["direct"])
    env["GDMR_HYBRID_LOW_SEED"] = str(config["seeds"]["low"])
    env["GDMR_HYBRID_STORE_DIR"] = str(SCRATCH_DIR / f"highaccuracy_hybrid_K{int(scenario['K'])}_M{euler_steps}_N{paths}")

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"hybrid_K{int(scenario['K'])}_M{euler_steps}_N{paths}.log"
    start = time.perf_counter()
    completed = subprocess.run(
        [sys.executable, "-u", str(HYBRID_SCRIPT)],
        cwd=RUN_ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=720_000,
    )
    runtime = time.perf_counter() - start
    log_path.write_text(
        "STDOUT:\n"
        + completed.stdout
        + "\nSTDERR:\n"
        + completed.stderr
        + f"\nEXIT_CODE: {completed.returncode}\n",
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise RuntimeError(f"High-accuracy Hybrid job failed for K={scenario['K']}; see {log_path}")

    result_line = next(line for line in completed.stdout.splitlines() if line.startswith("RESULT_JSON:"))
    result = json.loads(result_line.split(": ", 1)[1])
    price = float(result["hybrid_direct_price"])
    se = float(result["hybrid_direct_error"])
    rel = rel_error(price, reference)
    rel_low, rel_high = rel_ci_bounds(price, se, reference)
    return {
        "scenario": scenario["scenario"],
        "K": int(scenario["K"]),
        "S0": result["S0"],
        "T": result["T"],
        "r": result["r"],
        "v0": result["v0"],
        "vp0": result["vp0"],
        "kappa1": result["kappa1"],
        "kappa2": result["kappa2"],
        "theta": result["theta"],
        "xi1": result["xi1"],
        "xi2": result["xi2"],
        "rho12": result["rho12"],
        "rho13": result["rho13"],
        "rho23": result["rho23"],
        "delta1": result["delta1"],
        "delta2": result["delta2"],
        "exercise_dates": result["exercise_dates"],
        "euler_steps": euler_steps,
        "paths": paths,
        "method": "hybrid",
        "seed": config["seeds"]["direct"],
        "low_seed": config["seeds"]["low"],
        "low_paths": 1000,
        "asset_grid_points": result["asset_grid_points"],
        "asset_low_factor": result["asset_low_factor"],
        "asset_high_factor": result["asset_high_factor"],
        "vol_quantile": result["vol_quantile"],
        "fst_pad_factor": result["fst_pad_factor"],
        "fst_batch_size": result["fst_batch_size"],
        "runtime_seconds": f"{runtime:.6f}",
        "reference_direct_price": f"{reference:.6f}",
        "price_direct": f"{price:.12f}",
        "se_direct": f"{se:.12f}",
        "rel_error_direct": f"{rel:.12f}",
        "rel_ci_lower_direct": f"{rel_low:.12f}",
        "rel_ci_upper_direct": f"{rel_high:.12f}",
        "log_path": str(log_path),
    }


def main() -> None:
    config = load_config()
    case_id = config["case_id"]
    benchmarks = read_benchmarks(case_id)
    rows = []
    for scenario in config["strikes"]:
        strike = int(scenario["K"])
        print(f"[high-accuracy hybrid] K={strike} M=1200 N=100000 grid=601")
        rows.append(run_job(config, scenario, benchmarks[strike]))

    HIGH_PATH_DIR.mkdir(parents=True, exist_ok=True)
    output = HIGH_PATH_DIR / f"{case_id}_hybrid_highaccuracy_steps1200_paths100000_grid601_table.csv"
    fields = list(rows[0].keys())
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"[high-accuracy hybrid] wrote {output}")


if __name__ == "__main__":
    main()
