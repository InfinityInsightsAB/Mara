from __future__ import annotations

import argparse
import csv
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


CASE_ID = "bgk_r02_t1_delta05_nex12"

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parents[1]
ENGINE_DIR = PROJECT_ROOT / "Working Files" / "Final Code" / "More Experiments"
BENCHMARK_SCRIPT = ENGINE_DIR / "run_bgk_r03_benchmark_put.py"
HYBRID_SCRIPT = ENGINE_DIR / "run_bgk_r03_hybrid_put.py"

REFERENCE_DIR = ROOT / "reference_values"
PATH_REFERENCE_DIR = REFERENCE_DIR / "path_sweep"
OUTPUT_DIR = ROOT / "outputs"
SMOKE_DIR = OUTPUT_DIR / CASE_ID
SCRATCH_DIR = ROOT / "_scratch" / CASE_ID

BENCHMARK_CSV = REFERENCE_DIR / f"{CASE_ID}_benchmark_steps1200_paths1200000_table.csv"
STEP_CSVS = {
    20_000: REFERENCE_DIR / f"{CASE_ID}_step_sweep_all_ref1200_direct_samepaths20k_s24487296_table.csv",
    60_000: REFERENCE_DIR / f"{CASE_ID}_step_sweep_all_ref1200_direct_samepaths60k_s24487296_table.csv",
}
RUN_MANIFEST = OUTPUT_DIR / f"{CASE_ID}_run_manifest.csv"
METADATA_JSON = OUTPUT_DIR / f"{CASE_ID}_metadata.json"

SCENARIOS = [
    ("K=70 put", 70.0, "k70"),
    ("K=80 put", 80.0, "k80"),
    ("OTM put", 90.0, "k90"),
    ("ATM", 100.0, "k100"),
    ("ITM put", 110.0, "k110"),
]
STEP_SWEEP_STEPS = [24, 48, 72, 96]
STEP_SWEEP_PATHS = [20_000, 60_000]
PATH_SWEEP_STEPS = [48, 60]
PATH_SWEEP_PATHS = [250, 500, 1000, 2000, 5000, 10000, 20000, 40000, 60000]

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

HYBRID_ENV = {
    "GDMR_HYBRID_ASSET_POINTS": "301",
    "GDMR_HYBRID_ASSET_LOW_FACTOR": "0.30",
    "GDMR_HYBRID_ASSET_HIGH_FACTOR": "3.50",
    "GDMR_HYBRID_VOL_QUANTILE": "0.999",
    "GDMR_HYBRID_FST_PAD_FACTOR": "4",
    "GDMR_HYBRID_FST_BATCH_SIZE": "256",
    "GDMR_HYBRID_SEED": "2026",
    "GDMR_HYBRID_LOW_SEED": "2103",
}

LSMC_ENV = {
    "GDMR_LSMC_SEED": "2026",
    "GDMR_LSMC_LOW_SEED": "2103",
}

BENCHMARK_FIELDS = [
    "scenario",
    "S0",
    "K",
    "T",
    "r",
    "delta1",
    "delta2",
    "exercise_dates",
    "euler_steps",
    "lsmc_paths",
    "lsmc_low_paths",
    "seed",
    "low_seed",
    "benchmark_direct_price",
    "benchmark_direct_error",
    "benchmark_low_price",
    "benchmark_low_error",
    "benchmark_direct_low_gap",
]

STEP_FIELDS = [
    "scenario",
    "K",
    "r",
    "delta1",
    "delta2",
    "exercise_dates",
    "euler_steps",
    "paths",
    "method",
    "seed",
    "low_seed",
    "runtime_seconds",
    "reference_direct_price",
    "price_direct",
    "se_direct",
    "ci_width_direct",
    "rel_error_direct",
]

PATH_FIELDS = [
    "scenario",
    "K",
    "r",
    "delta1",
    "delta2",
    "exercise_dates",
    "euler_steps",
    "paths",
    "method",
    "seed",
    "low_seed",
    "runtime_seconds",
    "reference_direct_price",
    "price_direct",
    "se_direct",
    "rel_error_direct",
    "rel_ci_lower_direct",
    "rel_ci_upper_direct",
]

MANIFEST_FIELDS = [
    "study",
    "scenario",
    "K",
    "euler_steps",
    "paths",
    "method",
    "output_path",
    "runtime_seconds",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run manuscript numerical experiments for bgk_r02_t1_delta05_nex12."
    )
    parser.add_argument(
        "--mode",
        choices=["smoke", "benchmark", "step", "path", "full"],
        default="smoke",
        help="Experiment block to run.",
    )
    parser.add_argument("--force", action="store_true", help="Recompute rows that already exist.")
    parser.add_argument("--strike", type=float, help="Restrict to one strike.")
    parser.add_argument("--steps", type=int, nargs="*", help="Restrict to selected Euler step counts.")
    parser.add_argument("--paths", type=int, nargs="*", help="Restrict to selected path counts.")
    return parser.parse_args()


def ensure_dirs() -> None:
    for path in (REFERENCE_DIR, PATH_REFERENCE_DIR, OUTPUT_DIR, SMOKE_DIR, SCRATCH_DIR):
        path.mkdir(parents=True, exist_ok=True)


def write_metadata() -> None:
    metadata = {
        "case_id": CASE_ID,
        "model_env": MODEL_ENV,
        "hybrid_env": HYBRID_ENV,
        "lsmc_env": LSMC_ENV,
        "benchmark": {"euler_steps": 1200, "paths": 1_200_000},
        "step_sweep": {"paths": STEP_SWEEP_PATHS, "steps": STEP_SWEEP_STEPS},
        "path_sweep": {
            "source_paths": PATH_SWEEP_PATHS,
            "reported_paths": [250, 1000, 5000, 10000, 20000, 40000, 60000],
            "steps": PATH_SWEEP_STEPS,
        },
        "note": "Manuscript reporting uses direct prices only. Low-estimator fields are retained only for benchmark provenance.",
    }
    METADATA_JSON.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def append_manifest(row: dict[str, Any]) -> None:
    exists = RUN_MANIFEST.exists()
    with RUN_MANIFEST.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerow({key: row.get(key, "") for key in MANIFEST_FIELDS})


def rel_error(value: float, reference: float) -> float:
    if abs(reference) <= 1e-16:
        return 0.0 if abs(value) <= 1e-16 else float("inf")
    return abs(value - reference) / abs(reference)


def ci_bounds(value: float, se: float) -> tuple[float, float]:
    half_width = 1.96 * se
    return value - half_width, value + half_width


def rel_error_ci_bounds(value: float, se: float, reference: float) -> tuple[float, float]:
    low, high = ci_bounds(value, se)
    endpoint_errors = (rel_error(low, reference), rel_error(high, reference))
    if low <= reference <= high:
        return 0.0, max(endpoint_errors)
    return min(endpoint_errors), max(endpoint_errors)


def assert_case_result(
    result: dict[str, Any],
    *,
    strike: float,
    euler_steps: int,
    paths: int,
) -> None:
    expected_float = {
        "r": float(MODEL_ENV["GDMR_R"]),
        "delta1": float(MODEL_ENV["GDMR_DELTA1"]),
        "delta2": float(MODEL_ENV["GDMR_DELTA2"]),
        "T": float(MODEL_ENV["GDMR_MATURITY"]),
        "K": strike,
    }
    for key, expected in expected_float.items():
        actual = float(result[key])
        if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-12):
            raise RuntimeError(f"Unexpected {key}: got {actual}, expected {expected}")

    expected_int = {
        "exercise_dates": int(MODEL_ENV["GDMR_EXERCISE_DATES"]),
        "euler_steps": euler_steps,
        "paths": paths,
    }
    for key, expected in expected_int.items():
        actual = int(result[key])
        if actual != expected:
            raise RuntimeError(f"Unexpected {key}: got {actual}, expected {expected}")


def result_provenance_fields(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "r": f"{float(result['r']):.12g}",
        "delta1": f"{float(result['delta1']):.12g}",
        "delta2": f"{float(result['delta2']):.12g}",
        "exercise_dates": int(result["exercise_dates"]),
        "seed": int(result["seed"]),
        "low_seed": int(result["low_seed"]),
    }


def direct_low_gap(low: float, direct: float) -> float:
    if abs(direct) <= 1e-16:
        return float("inf")
    return abs(low - direct) / abs(direct)


def run_engine(script: Path, env_updates: dict[str, str]) -> tuple[dict[str, Any], float]:
    env = os.environ.copy()
    env.update(MODEL_ENV)
    env.update(LSMC_ENV)
    env.update(HYBRID_ENV)
    env.update(env_updates)
    env["GDMR_LSMC_STORE_DIR"] = str(SCRATCH_DIR)

    start = time.perf_counter()
    completed = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(ENGINE_DIR),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    runtime = time.perf_counter() - start
    if completed.returncode != 0:
        raise RuntimeError(
            f"{script.name} failed with exit code {completed.returncode}\n"
            f"STDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
        )
    result_line = None
    for line in reversed(completed.stdout.splitlines()):
        if line.startswith("RESULT_JSON: "):
            result_line = line[len("RESULT_JSON: ") :]
            break
    if result_line is None:
        raise RuntimeError(f"Could not parse RESULT_JSON from {script.name}\n{completed.stdout}")
    return json.loads(result_line), runtime


def scenario_filter(args: argparse.Namespace) -> list[tuple[str, float, str]]:
    if args.strike is None:
        return SCENARIOS
    return [item for item in SCENARIOS if int(item[1]) == int(args.strike)]


def load_benchmark_lookup() -> dict[str, dict[str, float]]:
    rows = load_rows(BENCHMARK_CSV)
    lookup: dict[str, dict[str, float]] = {}
    for row in rows:
        lookup[row["scenario"]] = {
            "K": float(row["K"]),
            "price": float(row["benchmark_direct_price"]),
            "se": float(row["benchmark_direct_error"]),
        }
    return lookup


def run_benchmark(args: argparse.Namespace) -> None:
    rows = [] if args.force else load_rows(BENCHMARK_CSV)
    existing = {row["scenario"] for row in rows}
    for scenario, strike, _ in scenario_filter(args):
        if scenario in existing and not args.force:
            print(f"[benchmark] skip existing {scenario}", flush=True)
            continue
        print(f"[benchmark] run {scenario}, K={strike:.0f}", flush=True)
        result, runtime = run_engine(
            BENCHMARK_SCRIPT,
            {
                "GDMR_STRIKE": f"{strike:.1f}",
                "GDMR_EULER_STEPS": "1200",
                "GDMR_LSMC_PATHS": "1200000",
                "GDMR_LSMC_LOW_PATHS": "1200000",
            },
        )
        assert_case_result(result, strike=strike, euler_steps=1200, paths=1_200_000)
        direct = float(result["lsmc_direct_price"])
        low = float(result["lsmc_low_price"])
        row = {
            "scenario": scenario,
            "S0": f"{float(result['S0']):.1f}",
            "K": f"{float(result['K']):.1f}",
            "T": f"{float(result['T']):.1f}",
            **result_provenance_fields(result),
            "euler_steps": int(result["euler_steps"]),
            "lsmc_paths": int(result["paths"]),
            "lsmc_low_paths": int(result["low_paths"]),
            "benchmark_direct_price": f"{direct:.6f}",
            "benchmark_direct_error": f"{float(result['lsmc_direct_error']):.6f}",
            "benchmark_low_price": f"{low:.6f}",
            "benchmark_low_error": f"{float(result['lsmc_low_error']):.6f}",
            "benchmark_direct_low_gap": f"{direct_low_gap(low, direct):.15g}",
        }
        rows = [old for old in rows if old["scenario"] != scenario]
        rows.append(row)
        rows.sort(key=lambda item: float(item["K"]))
        write_rows(BENCHMARK_CSV, BENCHMARK_FIELDS, rows)
        append_manifest(
            {
                "study": "benchmark",
                "scenario": scenario,
                "K": int(strike),
                "euler_steps": 1200,
                "paths": 1_200_000,
                "method": "benchmark",
                "output_path": str(BENCHMARK_CSV),
                "runtime_seconds": f"{runtime:.6f}",
            }
        )


def method_result(method: str, euler_steps: int, paths: int, strike: float) -> tuple[dict[str, Any], float]:
    common = {
        "GDMR_STRIKE": f"{strike:.1f}",
        "GDMR_EULER_STEPS": str(euler_steps),
    }
    low_paths = str(min(paths, 1000))
    if method == "benchmark":
        return run_engine(
            BENCHMARK_SCRIPT,
            common
            | {
                "GDMR_LSMC_PATHS": str(paths),
                "GDMR_LSMC_LOW_PATHS": low_paths,
            },
        )
    return run_engine(
        HYBRID_SCRIPT,
        common
        | {
            "GDMR_HYBRID_PATHS": str(paths),
            "GDMR_HYBRID_LOW_PATHS": low_paths,
        },
    )


def direct_price_and_se(method: str, result: dict[str, Any]) -> tuple[float, float]:
    if method == "benchmark":
        return float(result["lsmc_direct_price"]), float(result["lsmc_direct_error"])
    return float(result["hybrid_direct_price"]), float(result["hybrid_direct_error"])


def reusable_step_row(
    *,
    scenario: str,
    euler_steps: int,
    paths: int,
    method: str,
) -> tuple[float, float] | None:
    if euler_steps != 48 or paths not in STEP_CSVS:
        return None
    for row in load_rows(STEP_CSVS[paths]):
        if row["scenario"] == scenario and int(row["euler_steps"]) == euler_steps and row["method"] == method:
            return float(row["price_direct"]), float(row["se_direct"])
    return None


def run_step_sweep(args: argparse.Namespace) -> None:
    lookup = load_benchmark_lookup()
    if len(lookup) < len(SCENARIOS):
        raise RuntimeError("Benchmark references are incomplete; run --mode benchmark first.")
    selected_steps = args.steps if args.steps else STEP_SWEEP_STEPS
    selected_paths = args.paths if args.paths else STEP_SWEEP_PATHS
    for path_budget in selected_paths:
        output_path = STEP_CSVS[path_budget]
        rows = [] if args.force else load_rows(output_path)
        existing = {
            (row["scenario"], int(row["euler_steps"]), row["method"])
            for row in rows
        }
        for scenario, strike, _ in scenario_filter(args):
            reference = lookup[scenario]["price"]
            for euler_steps in selected_steps:
                for method in ("benchmark", "hybrid"):
                    key = (scenario, euler_steps, method)
                    if key in existing and not args.force:
                        print(f"[step {path_budget}] skip existing {scenario} M={euler_steps} {method}", flush=True)
                        continue
                    print(f"[step {path_budget}] run {scenario}, M={euler_steps}, {method}", flush=True)
                    result, runtime = method_result(method, euler_steps, path_budget, strike)
                    assert_case_result(result, strike=strike, euler_steps=euler_steps, paths=path_budget)
                    price, se = direct_price_and_se(method, result)
                    row = {
                        "scenario": scenario,
                        "K": f"{strike:.1f}",
                        **result_provenance_fields(result),
                        "euler_steps": euler_steps,
                        "paths": path_budget,
                        "method": method,
                        "runtime_seconds": f"{runtime:.12g}",
                        "reference_direct_price": f"{reference:.6f}",
                        "price_direct": f"{price:.15g}",
                        "se_direct": f"{se:.15g}",
                        "ci_width_direct": f"{(3.92 * se):.15g}",
                        "rel_error_direct": f"{rel_error(price, reference):.15g}",
                    }
                    rows = [
                        old
                        for old in rows
                        if (old["scenario"], int(old["euler_steps"]), old["method"]) != key
                    ]
                    rows.append(row)
                    rows.sort(key=lambda item: (float(item["K"]), int(item["euler_steps"]), item["method"]))
                    write_rows(output_path, STEP_FIELDS, rows)
                    append_manifest(
                        {
                            "study": "step",
                            "scenario": scenario,
                            "K": int(strike),
                            "euler_steps": euler_steps,
                            "paths": path_budget,
                            "method": method,
                            "output_path": str(output_path),
                            "runtime_seconds": f"{runtime:.6f}",
                        }
                    )


def path_csv_path(slug: str, euler_steps: int) -> Path:
    return PATH_REFERENCE_DIR / f"{CASE_ID}_path_sweep_{slug}_steps{euler_steps}_direct_ref1200_paths1200000_table.csv"


def path_json_path(slug: str, euler_steps: int) -> Path:
    return PATH_REFERENCE_DIR / f"{CASE_ID}_path_sweep_{slug}_steps{euler_steps}_direct_ref1200_paths1200000_table.json"


def run_path_sweep(args: argparse.Namespace) -> None:
    lookup = load_benchmark_lookup()
    if len(lookup) < len(SCENARIOS):
        raise RuntimeError("Benchmark references are incomplete; run --mode benchmark first.")
    selected_steps = args.steps if args.steps else PATH_SWEEP_STEPS
    selected_paths = args.paths if args.paths else PATH_SWEEP_PATHS
    for scenario, strike, slug in scenario_filter(args):
        reference = lookup[scenario]["price"]
        for euler_steps in selected_steps:
            output_path = path_csv_path(slug, euler_steps)
            rows = [] if args.force else load_rows(output_path)
            existing = {
                (int(row["paths"]), row["method"])
                for row in rows
            }
            for paths in selected_paths:
                for method in ("benchmark", "hybrid"):
                    key = (paths, method)
                    if key in existing and not args.force:
                        print(f"[path {euler_steps}] skip existing {scenario} paths={paths} {method}", flush=True)
                        continue
                    reusable = reusable_step_row(
                        scenario=scenario,
                        euler_steps=euler_steps,
                        paths=paths,
                        method=method,
                    )
                    if reusable is None:
                        print(f"[path {euler_steps}] run {scenario}, paths={paths}, {method}", flush=True)
                        result, runtime = method_result(method, euler_steps, paths, strike)
                        assert_case_result(result, strike=strike, euler_steps=euler_steps, paths=paths)
                        price, se = direct_price_and_se(method, result)
                        provenance = result_provenance_fields(result)
                    else:
                        print(f"[path {euler_steps}] reuse step row {scenario}, paths={paths}, {method}", flush=True)
                        price, se = reusable
                        runtime = 0.0
                        provenance = {
                            "r": MODEL_ENV["GDMR_R"],
                            "delta1": MODEL_ENV["GDMR_DELTA1"],
                            "delta2": MODEL_ENV["GDMR_DELTA2"],
                            "exercise_dates": int(MODEL_ENV["GDMR_EXERCISE_DATES"]),
                            "seed": LSMC_ENV["GDMR_LSMC_SEED"] if method == "benchmark" else HYBRID_ENV["GDMR_HYBRID_SEED"],
                            "low_seed": LSMC_ENV["GDMR_LSMC_LOW_SEED"] if method == "benchmark" else HYBRID_ENV["GDMR_HYBRID_LOW_SEED"],
                        }
                    rel_low, rel_high = rel_error_ci_bounds(price, se, reference)
                    row = {
                        "scenario": scenario,
                        "K": f"{strike:.0f}",
                        **provenance,
                        "euler_steps": euler_steps,
                        "paths": paths,
                        "method": method,
                        "runtime_seconds": f"{runtime:.12g}",
                        "reference_direct_price": f"{reference:.6f}",
                        "price_direct": f"{price:.12f}",
                        "se_direct": f"{se:.12f}",
                        "rel_error_direct": f"{rel_error(price, reference):.12f}",
                        "rel_ci_lower_direct": f"{rel_low:.12f}",
                        "rel_ci_upper_direct": f"{rel_high:.12f}",
                    }
                    rows = [
                        old for old in rows if (int(old["paths"]), old["method"]) != key
                    ]
                    rows.append(row)
                    rows.sort(key=lambda item: (int(item["paths"]), item["method"]))
                    write_rows(output_path, PATH_FIELDS, rows)
                    append_manifest(
                        {
                            "study": "path",
                            "scenario": scenario,
                            "K": int(strike),
                            "euler_steps": euler_steps,
                            "paths": paths,
                            "method": method,
                            "output_path": str(output_path),
                            "runtime_seconds": f"{runtime:.6f}",
                        }
                    )
            metadata = {
                "case_id": CASE_ID,
                "scenario": scenario,
                "strike": strike,
                "euler_steps": euler_steps,
                "path_grid": selected_paths,
                "methods": ["benchmark", "hybrid"],
                "reference_direct_price": reference,
                "model_env": MODEL_ENV,
            }
            path_json_path(slug, euler_steps).write_text(
                json.dumps(metadata, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )


def run_smoke(args: argparse.Namespace) -> None:
    smoke_csv = SMOKE_DIR / f"{CASE_ID}_smoke_table.csv"
    smoke_metadata = SMOKE_DIR / f"{CASE_ID}_smoke_metadata.json"
    rows: list[dict[str, Any]] = []
    smoke_scenario = ("ATM", 100.0, "k100")
    scenario, strike, _ = smoke_scenario
    for method in ("benchmark", "hybrid"):
        result, runtime = method_result(method, 24, 250 if method == "benchmark" else 100, strike)
        price, se = direct_price_and_se(method, result)
        rows.append(
            {
                "case_id": CASE_ID,
                "scenario": scenario,
                "K": int(strike),
                "method": method,
                "r": result["r"],
                "delta1": result["delta1"],
                "delta2": result["delta2"],
                "exercise_dates": result["exercise_dates"],
                "euler_steps": result["euler_steps"],
                "paths": result["paths"],
                "direct_price": f"{price:.12f}",
                "direct_se": f"{se:.12f}",
                "runtime_seconds": f"{runtime:.6f}",
            }
        )
    write_rows(
        smoke_csv,
        [
            "case_id",
            "scenario",
            "K",
            "method",
            "r",
            "delta1",
            "delta2",
            "exercise_dates",
            "euler_steps",
            "paths",
            "direct_price",
            "direct_se",
            "runtime_seconds",
        ],
        rows,
    )
    smoke_metadata.write_text(
        json.dumps({"case_id": CASE_ID, "rows": rows, "model_env": MODEL_ENV}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Smoke output: {smoke_csv}", flush=True)
    print(f"Smoke metadata: {smoke_metadata}", flush=True)


def main() -> None:
    args = parse_args()
    ensure_dirs()
    write_metadata()
    if args.mode == "smoke":
        run_smoke(args)
        return
    if args.mode in ("benchmark", "full"):
        run_benchmark(args)
    if args.mode in ("step", "full"):
        run_step_sweep(args)
    if args.mode in ("path", "full"):
        run_path_sweep(args)


if __name__ == "__main__":
    main()
