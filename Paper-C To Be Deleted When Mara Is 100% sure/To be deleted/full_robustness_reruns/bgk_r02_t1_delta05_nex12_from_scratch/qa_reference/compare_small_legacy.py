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


RUN_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = RUN_ROOT.parents[2]
CODE_DIR = RUN_ROOT / "code"
LOG_DIR = RUN_ROOT / "logs" / "jobs" / "qa_reference"
OUT_CSV = RUN_ROOT / "results" / "validation" / "legacy_small_comparison.csv"
QA_CWD = RUN_ROOT / "qa_reference"
NEW_LSMC = CODE_DIR / "lsmc_from_scratch.py"
NEW_HYBRID = CODE_DIR / "hybrid_from_scratch.py"
OLD_ENGINE_DIR = PROJECT_ROOT / "Working Files" / "Final Code" / "More Experiments"
OLD_LSMC = OLD_ENGINE_DIR / "run_bgk_r03_benchmark_put.py"
OLD_HYBRID = OLD_ENGINE_DIR / "run_bgk_r03_hybrid_put.py"

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
    "GDMR_STRIKE": "100.0",
    "GDMR_EULER_STEPS": "24",
    "GDMR_LSMC_PATHS": "400",
    "GDMR_LSMC_LOW_PATHS": "400",
    "GDMR_LSMC_SEED": "2026",
    "GDMR_LSMC_LOW_SEED": "2103",
    "GDMR_HYBRID_PATHS": "300",
    "GDMR_HYBRID_LOW_PATHS": "300",
    "GDMR_HYBRID_SEED": "2026",
    "GDMR_HYBRID_LOW_SEED": "2103",
    "GDMR_HYBRID_ASSET_POINTS": "301",
    "GDMR_HYBRID_ASSET_LOW_FACTOR": "0.30",
    "GDMR_HYBRID_ASSET_HIGH_FACTOR": "3.50",
    "GDMR_HYBRID_VOL_QUANTILE": "0.999",
    "GDMR_HYBRID_FST_PAD_FACTOR": "4",
    "GDMR_HYBRID_FST_BATCH_SIZE": "256",
}

FIELDS = [
    "method",
    "K",
    "euler_steps",
    "paths",
    "low_paths",
    "seed",
    "low_seed",
    "r",
    "delta1",
    "delta2",
    "v0",
    "vp0",
    "T",
    "exercise_dates",
    "legacy_script",
    "scratch_script",
    "legacy_sha256",
    "scratch_sha256",
    "legacy_log",
    "scratch_log",
    "legacy_price",
    "scratch_price",
    "abs_difference",
    "legacy_se",
    "scratch_se",
    "status",
]


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run_script(script: Path, cwd: Path, env_extra: dict[str, str], label: str) -> dict[str, Any]:
    env = os.environ.copy()
    env.update(MODEL_ENV)
    env.update(env_extra)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    cwd.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"{label}.log"
    start = time.perf_counter()
    completed = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    runtime = time.perf_counter() - start
    log_path.write_text(
        completed.stdout + "\n\nSTDERR:\n" + completed.stderr + f"\nRUNTIME_SECONDS: {runtime:.6f}\n",
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise RuntimeError(f"{label} failed; see {log_path}")
    result_line = None
    for line in reversed(completed.stdout.splitlines()):
        if line.startswith("RESULT_JSON: "):
            result_line = line[len("RESULT_JSON: ") :]
            break
    if result_line is None:
        raise RuntimeError(f"{label} missing RESULT_JSON")
    result = json.loads(result_line)
    result["_log_path"] = str(log_path)
    return result


def finite(value: Any) -> float:
    out = float(value)
    if not math.isfinite(out):
        raise RuntimeError(f"Non-finite {value}")
    return out


def write_rows(rows: list[dict[str, Any]]) -> None:
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})


def main() -> None:
    rows: list[dict[str, Any]] = []
    scratch_root = RUN_ROOT / "scratch" / "qa_reference"
    lsmc_old = run_script(
        OLD_LSMC,
        QA_CWD,
        {"GDMR_LSMC_STORE_DIR": str(scratch_root / "old_lsmc")},
        "old_lsmc_small",
    )
    lsmc_new = run_script(
        NEW_LSMC,
        CODE_DIR,
        {"GDMR_LSMC_STORE_DIR": str(scratch_root / "new_lsmc")},
        "new_lsmc_small",
    )
    hybrid_old = run_script(
        OLD_HYBRID,
        QA_CWD,
        {"GDMR_HYBRID_STORE_DIR": str(scratch_root / "old_hybrid")},
        "old_hybrid_small",
    )
    hybrid_new = run_script(
        NEW_HYBRID,
        CODE_DIR,
        {"GDMR_HYBRID_STORE_DIR": str(scratch_root / "new_hybrid")},
        "new_hybrid_small",
    )
    comparisons = [
        ("benchmark", lsmc_old, lsmc_new, "lsmc_direct_price", "lsmc_direct_error", OLD_LSMC, NEW_LSMC),
        ("hybrid", hybrid_old, hybrid_new, "hybrid_direct_price", "hybrid_direct_error", OLD_HYBRID, NEW_HYBRID),
    ]
    any_drift = False
    for method, old, new, price_key, se_key, legacy_script, scratch_script in comparisons:
        legacy_price = finite(old[price_key])
        scratch_price = finite(new[price_key])
        diff = abs(legacy_price - scratch_price)
        status = "match" if diff <= max(1e-8, 1e-6 * abs(legacy_price)) else "drift"
        any_drift = any_drift or status == "drift"
        rows.append(
            {
                "method": method,
                "K": old["K"],
                "euler_steps": old["euler_steps"],
                "paths": old["paths"],
                "low_paths": old["low_paths"],
                "seed": old["seed"],
                "low_seed": old["low_seed"],
                "r": old["r"],
                "delta1": old["delta1"],
                "delta2": old["delta2"],
                "v0": old["v0"],
                "vp0": old["vp0"],
                "T": old["T"],
                "exercise_dates": old["exercise_dates"],
                "legacy_script": str(legacy_script),
                "scratch_script": str(scratch_script),
                "legacy_sha256": file_hash(legacy_script),
                "scratch_sha256": file_hash(scratch_script),
                "legacy_log": old["_log_path"],
                "scratch_log": new["_log_path"],
                "legacy_price": f"{legacy_price:.12f}",
                "scratch_price": f"{scratch_price:.12f}",
                "abs_difference": f"{diff:.12f}",
                "legacy_se": f"{finite(old[se_key]):.12f}",
                "scratch_se": f"{finite(new[se_key]):.12f}",
                "status": status,
            }
        )
    write_rows(rows)
    print(f"[qa_reference] wrote {OUT_CSV}")
    if any_drift:
        raise SystemExit("Legacy/scratch QA comparison drifted; see validation CSV.")


if __name__ == "__main__":
    main()
