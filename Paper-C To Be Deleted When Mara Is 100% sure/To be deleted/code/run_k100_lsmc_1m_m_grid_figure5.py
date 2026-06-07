from __future__ import annotations

import argparse
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

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parents[0]
ENGINE_DIR = ROOT / "benchmark_code_exact"
BENCHMARK_SCRIPT = ENGINE_DIR / "run_bgk_r03_benchmark_put.py"
RESULTS_DIR = ROOT / "results"
LOGS_DIR = ROOT / "logs"
SCRATCH_DIR = ROOT / "scratch"
FIGURES_DIR = ROOT / "figures"
SUMMARY_DIR = ROOT / "summary"

CASE_ID = "bgk_r02_t1_delta05_nex12"
OUTPUT_PREFIX = "k100_lsmc_1m_m_grid_against_figure5_benchmark"
OUTPUT_CSV = RESULTS_DIR / f"{OUTPUT_PREFIX}.csv"
OUTPUT_JSON = RESULTS_DIR / f"{OUTPUT_PREFIX}_metadata.json"

FIGURE5_BENCHMARK_CSV = (
    PROJECT_ROOT
    / "Working Files"
    / "Manuscript Code"
    / "reference_values"
    / f"{CASE_ID}_benchmark_steps1200_paths1200000_table.csv"
)

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

K = 100.0
PATHS = 1_000_000
LOW_PATHS = 1_000
SEED = 2026
LOW_SEED = 2103
M_GRID = [500, 750, 1200]

FIELDS = [
    "case_id",
    "scenario",
    "K",
    "euler_steps",
    "paths",
    "low_paths",
    "seed",
    "low_seed",
    "price_direct",
    "se_direct",
    "ci_lower_direct",
    "ci_upper_direct",
    "figure5_benchmark_direct_price",
    "figure5_benchmark_direct_se",
    "figure5_benchmark_euler_steps",
    "figure5_benchmark_paths",
    "rel_error_direct",
    "rel_error_pct",
    "rel_ci_lower_direct",
    "rel_ci_upper_direct",
    "yerr_minus_pct",
    "yerr_plus_pct",
    "price_low",
    "se_low",
    "runtime_seconds",
    "r",
    "delta1",
    "delta2",
    "v0",
    "vp0",
    "T",
    "exercise_dates",
    "benchmark_engine_sha256",
    "code_path",
    "log_path",
]


def ensure_dirs() -> None:
    for path in (RESULTS_DIR, LOGS_DIR, SCRATCH_DIR, FIGURES_DIR, SUMMARY_DIR):
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
    rows = sorted(rows, key=lambda row: int(row["euler_steps"]))
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


def figure5_k100_benchmark() -> dict[str, float]:
    for row in read_rows(FIGURE5_BENCHMARK_CSV):
        if int(float(row["K"])) == 100:
            return {
                "price": finite(row["benchmark_direct_price"]),
                "se": finite(row["benchmark_direct_error"]),
                "euler_steps": float(row["euler_steps"]),
                "paths": float(row["lsmc_paths"]),
            }
    raise RuntimeError(f"Could not find K=100 benchmark in {FIGURE5_BENCHMARK_CSV}")


def existing_row(euler_steps: int) -> dict[str, str] | None:
    for row in read_rows(OUTPUT_CSV):
        if int(row.get("euler_steps", -1)) == euler_steps:
            return row
    return None


def assert_result(result: dict[str, Any], euler_steps: int) -> None:
    expected_float = {
        "K": K,
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
    if int(result["euler_steps"]) != euler_steps:
        raise RuntimeError(f"Unexpected euler_steps: {result['euler_steps']}")
    if int(result["paths"]) != PATHS:
        raise RuntimeError(f"Unexpected paths: {result['paths']}")
    if int(result["low_paths"]) != LOW_PATHS:
        raise RuntimeError(f"Unexpected low_paths: {result['low_paths']}")
    if int(result["exercise_dates"]) != 12:
        raise RuntimeError(f"Unexpected exercise_dates: {result['exercise_dates']}")
    if int(result["seed"]) != SEED or int(result["low_seed"]) != LOW_SEED:
        raise RuntimeError("Unexpected seeds")


def run_one(euler_steps: int, reference: dict[str, float], force: bool) -> dict[str, Any]:
    if not force:
        row = existing_row(euler_steps)
        if row is not None:
            print(f"[skip] M={euler_steps} already exists", flush=True)
            return row

    env = os.environ.copy()
    env.update(MODEL_ENV)
    env.update(
        {
            "GDMR_STRIKE": f"{K:.1f}",
            "GDMR_EULER_STEPS": str(euler_steps),
            "GDMR_LSMC_PATHS": str(PATHS),
            "GDMR_LSMC_LOW_PATHS": str(LOW_PATHS),
            "GDMR_LSMC_SEED": str(SEED),
            "GDMR_LSMC_LOW_SEED": str(LOW_SEED),
            "GDMR_LSMC_STORE_DIR": str(SCRATCH_DIR / OUTPUT_PREFIX),
        }
    )
    log_path = LOGS_DIR / f"{OUTPUT_PREFIX}_M{euler_steps}.log"
    print(f"[run] K=100, M={euler_steps}, N={PATHS}", flush=True)
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
        raise RuntimeError(f"Run failed for M={euler_steps}. See {log_path}")
    result_line = None
    for line in reversed(completed.stdout.splitlines()):
        if line.startswith("RESULT_JSON: "):
            result_line = line[len("RESULT_JSON: ") :]
            break
    if result_line is None:
        raise RuntimeError(f"Missing RESULT_JSON in {log_path}")
    result = json.loads(result_line)
    assert_result(result, euler_steps)

    price = finite(result["lsmc_direct_price"])
    se = finite(result["lsmc_direct_error"])
    ref_price = reference["price"]
    rel_low, rel_high = rel_error_ci_bounds(price, se, ref_price)
    rel = rel_error(price, ref_price)
    return {
        "case_id": CASE_ID,
        "scenario": "ATM",
        "K": f"{K:.0f}",
        "euler_steps": euler_steps,
        "paths": PATHS,
        "low_paths": LOW_PATHS,
        "seed": SEED,
        "low_seed": LOW_SEED,
        "price_direct": f"{price:.12f}",
        "se_direct": f"{se:.12f}",
        "ci_lower_direct": f"{price - 1.96 * se:.12f}",
        "ci_upper_direct": f"{price + 1.96 * se:.12f}",
        "figure5_benchmark_direct_price": f"{ref_price:.6f}",
        "figure5_benchmark_direct_se": f"{reference['se']:.6f}",
        "figure5_benchmark_euler_steps": f"{int(reference['euler_steps'])}",
        "figure5_benchmark_paths": f"{int(reference['paths'])}",
        "rel_error_direct": f"{rel:.12f}",
        "rel_error_pct": f"{100.0 * rel:.6f}",
        "rel_ci_lower_direct": f"{rel_low:.12f}",
        "rel_ci_upper_direct": f"{rel_high:.12f}",
        "yerr_minus_pct": f"{100.0 * (rel - rel_low):.6f}",
        "yerr_plus_pct": f"{100.0 * (rel_high - rel):.6f}",
        "price_low": f"{finite(result['lsmc_low_price']):.12f}",
        "se_low": f"{finite(result['lsmc_low_error']):.12f}",
        "runtime_seconds": f"{runtime:.6f}",
        "r": result["r"],
        "delta1": result["delta1"],
        "delta2": result["delta2"],
        "v0": result["v0"],
        "vp0": result["vp0"],
        "T": result["T"],
        "exercise_dates": result["exercise_dates"],
        "benchmark_engine_sha256": file_hash(BENCHMARK_SCRIPT),
        "code_path": str(BENCHMARK_SCRIPT),
        "log_path": str(log_path),
    }


def validate_rows(rows: list[dict[str, Any]], reference: dict[str, float]) -> None:
    if sorted(int(row["euler_steps"]) for row in rows) != M_GRID:
        raise RuntimeError("Missing M-grid rows")
    for row in rows:
        for key in ("price_direct", "se_direct", "rel_error_direct", "rel_ci_lower_direct", "rel_ci_upper_direct"):
            finite(row[key])
        if int(row["paths"]) != PATHS:
            raise RuntimeError("Unexpected paths in output row")
        if int(float(row["figure5_benchmark_direct_price"]) * 1_000_000) != int(reference["price"] * 1_000_000):
            raise RuntimeError("Unexpected reference price")


def render_figure(rows: list[dict[str, Any]], reference: dict[str, float]) -> dict[str, str]:
    rows = sorted(rows, key=lambda row: int(row["euler_steps"]))
    x = [int(row["euler_steps"]) for row in rows]
    y = [finite(row["rel_error_pct"]) for row in rows]
    yerr = [
        [finite(row["yerr_minus_pct"]) for row in rows],
        [finite(row["yerr_plus_pct"]) for row in rows],
    ]

    plt.rcParams.update(
        {
            "font.family": "STIXGeneral",
            "mathtext.fontset": "stix",
            "font.size": 11,
            "axes.titlesize": 12,
            "axes.labelsize": 11,
            "axes.linewidth": 0.8,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "legend.fontsize": 10,
            "figure.dpi": 300,
            "savefig.dpi": 300,
        }
    )
    fig, ax = plt.subplots(figsize=(6.6, 4.2), constrained_layout=True)
    ax.errorbar(
        x,
        y,
        yerr=yerr,
        fmt="o-",
        color="#1f4e79",
        linewidth=1.5,
        markersize=5.4,
        capsize=3.2,
        elinewidth=1.0,
        markeredgewidth=0.8,
        label="LSMC",
    )
    ax.axhline(0.0, color="#555555", linewidth=0.8)
    ax.set_title(r"$K=100$, $N=1{,}000{,}000$")
    ax.set_xlabel("Euler Steps")
    ax.set_ylabel("Relative Error (%)")
    ax.set_xticks(x)
    ax.set_xlim(min(x) - 70, max(x) + 70)
    upper = max(1.0, max(yi + err for yi, err in zip(y, yerr[1])) * 1.25)
    ax.set_ylim(0, upper)
    ax.grid(True, which="major", color="#d8d8d8", linewidth=0.6)
    ax.set_facecolor("white")
    ax.legend(loc="upper right", frameon=False)
    ax.text(
        0.02,
        0.96,
        "Benchmark: Figure 5 LSMC reference, 1200 steps, 1.2M paths",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9.5,
    )
    ax.text(
        0.02,
        0.88,
        r"Case: $r=0.02$, $\delta_1=\delta_2=0.5$",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9.5,
    )

    paths = {
        "pdf": str(FIGURES_DIR / f"{OUTPUT_PREFIX}.pdf"),
        "png": str(FIGURES_DIR / f"{OUTPUT_PREFIX}.png"),
        "eps": str(FIGURES_DIR / f"{OUTPUT_PREFIX}.eps"),
    }
    fig.savefig(paths["pdf"], bbox_inches="tight")
    fig.savefig(paths["png"], bbox_inches="tight")
    fig.savefig(paths["eps"], format="eps", bbox_inches="tight")
    plt.close(fig)
    return paths


def write_metadata(rows: list[dict[str, Any]], figure_paths: dict[str, str], reference: dict[str, float]) -> None:
    metadata = {
        "case_id": CASE_ID,
        "purpose": "K=100 LSMC direct relative error against Figure 5 benchmark for M=500,750,1200 and N=1,000,000.",
        "benchmark_source": str(FIGURE5_BENCHMARK_CSV),
        "benchmark": reference,
        "engine": str(BENCHMARK_SCRIPT),
        "engine_sha256": file_hash(BENCHMARK_SCRIPT),
        "outputs": {
            "csv": str(OUTPUT_CSV),
            "figures": figure_paths,
        },
        "rows": rows,
    }
    OUTPUT_JSON.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Rerun rows even if they already exist.")
    args = parser.parse_args()
    ensure_dirs()
    reference = figure5_k100_benchmark()
    rows = [run_one(euler_steps, reference, force=args.force) for euler_steps in M_GRID]
    write_rows(rows)
    validate_rows(rows, reference)
    figure_paths = render_figure(rows, reference)
    write_metadata(rows, figure_paths, reference)
    print(f"[done] wrote {OUTPUT_CSV}", flush=True)
    for kind, path in figure_paths.items():
        print(f"[done] wrote {kind}: {path}", flush=True)


if __name__ == "__main__":
    main()
