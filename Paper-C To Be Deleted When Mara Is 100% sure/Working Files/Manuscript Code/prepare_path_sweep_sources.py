from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parents[1]
EXPERIMENT_DIR = PROJECT_ROOT / "Experiments 26.03"
SOURCE_DIR = ROOT / "reference_values" / "path_sweep"
SCRATCH_ROOT = ROOT / "outputs" / "_path_sweep_scratch"

BENCHMARK_SCRIPT = EXPERIMENT_DIR / "LSMC Benchmark" / "run_gdmr_benchmark_put.py"
HYBRID_SCRIPT = EXPERIMENT_DIR / "Hybrid LSMC-PDE with FFT" / "run_gdmr_hybrid_put.py"

BENCHMARK_SOURCE_FILENAMES = {
    "benchmark_main": "bgk_r00_t1_nex12_benchmark_steps1200_paths1200000_table.csv",
    "benchmark_tail": "bgk_r00_t1_nex12_benchmark_steps1200_paths1200000_k80_k70_table.csv",
}

STEP_SWEEP_SOURCE_FILENAMES = {
    20000: "bgk_r00_t1_nex12_step_sweep_all_ref1200_direct_samepaths20k_s24487296_table.csv",
    60000: "bgk_r00_t1_nex12_step_sweep_all_ref1200_direct_samepaths60k_s24487296_table.csv",
}

FULL_SAVED_PATH_SWEEPS = {
    ("k90", 48): "bgk_r00_t1_nex12_path_sweep_otm_steps48_direct_ref1200_paths1200000_table.csv",
    ("k100", 48): "bgk_r00_t1_nex12_path_sweep_atm_steps48_direct_ref1200_paths1200000_table.csv",
}

DEFAULT_PATH_COUNTS = [250, 500, 1000, 2000, 5000, 10000, 20000, 40000, 60000]
CI_Z = 1.96

BENCHMARK_PATTERNS = {
    "lsmc_direct_price": r"LSMC direct price:\s*([0-9eE+\-.]+)",
    "lsmc_direct_error": r"LSMC direct error:\s*([0-9eE+\-.]+)",
}

BGK_MODEL_ENV = {
    "GDMR_S0": "100.0",
    "GDMR_V0": "0.114",
    "GDMR_VP0": "0.110",
    "GDMR_R": "0.0",
    "GDMR_KAPPA1": "5.5",
    "GDMR_KAPPA2": "0.1",
    "GDMR_THETA": "0.078",
    "GDMR_XI1": "2.689",
    "GDMR_XI2": "0.502",
    "GDMR_DELTA1": "0.94",
    "GDMR_DELTA2": "0.94",
    "GDMR_RHO12": "-0.982",
    "GDMR_RHO13": "-0.727",
    "GDMR_RHO23": "0.59",
    "GDMR_EXERCISE_DATES": "12",
    "GDMR_MATURITY": "1.0",
}

HYBRID_TUNED_ENV = {
    "GDMR_HYBRID_ASSET_POINTS": "301",
    "GDMR_HYBRID_ASSET_LOW_FACTOR": "0.30",
    "GDMR_HYBRID_ASSET_HIGH_FACTOR": "3.50",
    "GDMR_HYBRID_VOL_QUANTILE": "0.999",
    "GDMR_HYBRID_FST_PAD_FACTOR": "4",
    "GDMR_HYBRID_FST_BATCH_SIZE": "256",
    "GDMR_HYBRID_SEED": "2026",
    "GDMR_HYBRID_LOW_SEED": "2103",
}

SCENARIOS = {
    "k70": {"display": "K=70", "benchmark_label": "K=70 put", "strike": 70.0},
    "k80": {"display": "K=80", "benchmark_label": "K=80 put", "strike": 80.0},
    "k90": {"display": "K=90", "benchmark_label": "OTM put", "strike": 90.0},
    "k100": {"display": "K=100", "benchmark_label": "ATM", "strike": 100.0},
    "k110": {"display": "K=110", "benchmark_label": "ITM put", "strike": 110.0},
}

CSV_COLUMNS = [
    "scenario",
    "K",
    "euler_steps",
    "paths",
    "method",
    "runtime_seconds",
    "reference_direct_price",
    "price_direct",
    "se_direct",
    "rel_error_direct",
    "rel_ci_lower_direct",
    "rel_ci_upper_direct",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare manuscript-local path-sweep source tables with saved-result reuse and local recomputation."
    )
    parser.add_argument(
        "--scenario",
        choices=sorted(SCENARIOS),
        required=True,
        help="Scenario slug to prepare.",
    )
    parser.add_argument(
        "--steps",
        type=int,
        nargs="+",
        default=[48, 60],
        help="Euler steps to prepare. Defaults to 48 and 60.",
    )
    parser.add_argument(
        "--paths",
        type=int,
        nargs="*",
        default=DEFAULT_PATH_COUNTS,
        help="Path counts to include. Defaults to the manuscript grid.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recompute or recopy even if the local source file already exists.",
    )
    return parser.parse_args()


def ensure_dirs() -> None:
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    SCRATCH_ROOT.mkdir(parents=True, exist_ok=True)


def external_source_path(filename: str) -> Path:
    return EXPERIMENT_DIR / filename


def output_csv_path(scenario_slug: str, euler_steps: int) -> Path:
    stem = f"bgk_r00_t1_nex12_path_sweep_{scenario_slug}_steps{euler_steps}_direct_ref1200_paths1200000_table"
    return SOURCE_DIR / f"{stem}.csv"


def output_meta_path(scenario_slug: str, euler_steps: int) -> Path:
    stem = f"bgk_r00_t1_nex12_path_sweep_{scenario_slug}_steps{euler_steps}_direct_ref1200_paths1200000_table"
    return SOURCE_DIR / f"{stem}.json"


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, float | int | str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_meta(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def rel_error(value: float, reference: float) -> float:
    scale = abs(reference)
    if scale <= 1e-16:
        return 0.0 if abs(value) <= 1e-16 else float("inf")
    return abs(value - reference) / scale


def ci_bounds(value: float, se: float) -> tuple[float, float]:
    half_width = CI_Z * se
    return value - half_width, value + half_width


def rel_error_ci_bounds(value: float, se: float, reference: float) -> tuple[float, float]:
    low_value, high_value = ci_bounds(value, se)
    endpoint_errors = (
        rel_error(low_value, reference),
        rel_error(high_value, reference),
    )
    if low_value <= reference <= high_value:
        return 0.0, max(endpoint_errors)
    return min(endpoint_errors), max(endpoint_errors)


def benchmark_lookup() -> dict[str, float]:
    lookup: dict[str, float] = {}
    for key in ("benchmark_main", "benchmark_tail"):
        for row in load_csv_rows(external_source_path(BENCHMARK_SOURCE_FILENAMES[key])):
            lookup[row["scenario"]] = float(row["benchmark_direct_price"])
    return lookup


def build_env(scenario_slug: str, euler_steps: int, paths: int, method: str, scratch_dir: Path) -> dict[str, str]:
    scenario = SCENARIOS[scenario_slug]
    env = os.environ.copy()
    env.update(BGK_MODEL_ENV)
    env.update(
        {
            "GDMR_STRIKE": f"{scenario['strike']:.1f}",
            "GDMR_EULER_STEPS": str(euler_steps),
        }
    )
    if method == "benchmark":
        env.update(
            {
                "GDMR_LSMC_PATHS": str(paths),
                "GDMR_LSMC_LOW_PATHS": str(paths),
                "GDMR_LSMC_SEED": "2026",
                "GDMR_LSMC_LOW_SEED": "2103",
                "GDMR_LSMC_STORE_DIR": str(scratch_dir),
            }
        )
    else:
        env.update(HYBRID_TUNED_ENV)
        env.update(
            {
                "GDMR_HYBRID_PATHS": str(paths),
                "GDMR_HYBRID_LOW_PATHS": str(paths),
            }
        )
    return env


def run_benchmark(env: dict[str, str]) -> tuple[float, float]:
    started = time.perf_counter()
    completed = subprocess.run(
        [sys.executable, str(BENCHMARK_SCRIPT)],
        cwd=str(EXPERIMENT_DIR),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    elapsed = time.perf_counter() - started
    if completed.returncode != 0:
        raise RuntimeError(
            f"{BENCHMARK_SCRIPT.name} failed with exit code {completed.returncode}.\n"
            f"STDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
        )
    values: dict[str, float] = {}
    for key, pattern in BENCHMARK_PATTERNS.items():
        match = re.search(pattern, completed.stdout)
        if match is None:
            raise RuntimeError(
                f"Could not parse {key} from {BENCHMARK_SCRIPT.name} output.\n{completed.stdout}"
            )
        values[key] = float(match.group(1))
    return values["lsmc_direct_price"], values["lsmc_direct_error"], elapsed


def run_hybrid(env: dict[str, str]) -> tuple[float, float]:
    started = time.perf_counter()
    completed = subprocess.run(
        [sys.executable, str(HYBRID_SCRIPT)],
        cwd=str(EXPERIMENT_DIR),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    elapsed = time.perf_counter() - started
    if completed.returncode != 0:
        raise RuntimeError(
            f"{HYBRID_SCRIPT.name} failed with exit code {completed.returncode}.\n"
            f"STDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
        )
    result_line = None
    for line in completed.stdout.splitlines()[::-1]:
        if line.startswith("RESULT_JSON: "):
            result_line = line[len("RESULT_JSON: "):]
            break
    if result_line is None:
        raise RuntimeError(f"Could not parse RESULT_JSON from {HYBRID_SCRIPT.name}.\n{completed.stdout}")
    raw = json.loads(result_line)
    return float(raw["hybrid_direct_price"]), float(raw["hybrid_direct_error"]), elapsed


def normalized_row(
    scenario_slug: str,
    euler_steps: int,
    paths: int,
    method: str,
    runtime_seconds: float,
    reference_direct_price: float,
    price_direct: float,
    se_direct: float,
) -> dict[str, float | int | str]:
    rel = rel_error(price_direct, reference_direct_price)
    rel_low, rel_high = rel_error_ci_bounds(price_direct, se_direct, reference_direct_price)
    return {
        "scenario": SCENARIOS[scenario_slug]["benchmark_label"],
        "K": int(SCENARIOS[scenario_slug]["strike"]),
        "euler_steps": euler_steps,
        "paths": paths,
        "method": method,
        "runtime_seconds": f"{runtime_seconds:.12f}",
        "reference_direct_price": f"{reference_direct_price:.6f}",
        "price_direct": f"{price_direct:.12f}",
        "se_direct": f"{se_direct:.12f}",
        "rel_error_direct": f"{rel:.12f}",
        "rel_ci_lower_direct": f"{rel_low:.12f}",
        "rel_ci_upper_direct": f"{rel_high:.12f}",
    }


def load_saved_full_rows(scenario_slug: str, euler_steps: int, path_counts: set[int]) -> tuple[list[dict[str, float | int | str]], list[str]]:
    filename = FULL_SAVED_PATH_SWEEPS.get((scenario_slug, euler_steps))
    if filename is None:
        return [], []
    source_path = external_source_path(filename)
    scenario = SCENARIOS[scenario_slug]
    rows: list[dict[str, float | int | str]] = []
    for row in load_csv_rows(source_path):
        paths = int(row["paths"])
        if paths not in path_counts:
            continue
        rows.append(
            normalized_row(
                scenario_slug,
                euler_steps,
                paths,
                row["method"],
                float(row["runtime_seconds"]),
                float(row["reference_direct_price"]),
                float(row["price_direct"]),
                float(row["se_direct"]),
            )
        )
    return rows, [str(source_path)]


def load_saved_overlap_rows(
    scenario_slug: str,
    euler_steps: int,
    path_counts: set[int],
    reference_direct_price: float,
) -> tuple[list[dict[str, float | int | str]], list[str]]:
    if euler_steps != 48:
        return [], []
    scenario_label = SCENARIOS[scenario_slug]["benchmark_label"]
    rows: list[dict[str, float | int | str]] = []
    sources: list[str] = []
    for paths, filename in STEP_SWEEP_SOURCE_FILENAMES.items():
        if paths not in path_counts:
            continue
        source_path = external_source_path(filename)
        for row in load_csv_rows(source_path):
            if row["scenario"] != scenario_label:
                continue
            if int(float(row["euler_steps"])) != euler_steps:
                continue
            rows.append(
                normalized_row(
                    scenario_slug,
                    euler_steps,
                    paths,
                    row["method"],
                    float(row["runtime_seconds"]),
                    reference_direct_price,
                    float(row["price_direct"]),
                    float(row["se_direct"]),
                )
            )
        sources.append(str(source_path))
    return rows, sources


def compute_row(
    scenario_slug: str,
    euler_steps: int,
    paths: int,
    method: str,
    reference_direct_price: float,
    scratch_dir: Path,
) -> dict[str, float | int | str]:
    scratch_dir.mkdir(parents=True, exist_ok=True)
    env = build_env(scenario_slug, euler_steps, paths, method, scratch_dir)
    if method == "benchmark":
        price_direct, se_direct, runtime_seconds = run_benchmark(env)
    else:
        price_direct, se_direct, runtime_seconds = run_hybrid(env)
    return normalized_row(
        scenario_slug,
        euler_steps,
        paths,
        method,
        runtime_seconds,
        reference_direct_price,
        price_direct,
        se_direct,
    )


def prepare_combo(
    scenario_slug: str,
    euler_steps: int,
    path_counts: list[int],
    reference_lookup: dict[str, float],
    force: bool,
) -> None:
    output_csv = output_csv_path(scenario_slug, euler_steps)
    output_meta = output_meta_path(scenario_slug, euler_steps)
    if output_csv.exists() and output_meta.exists() and not force:
        print(f"Skipping existing {output_csv.name}")
        return

    requested_paths = sorted(set(path_counts))
    requested_path_set = set(requested_paths)
    reference_direct_price = reference_lookup[SCENARIOS[scenario_slug]["benchmark_label"]]

    rows, sources = load_saved_full_rows(scenario_slug, euler_steps, requested_path_set)
    reused_paths = sorted({int(row["paths"]) for row in rows})
    computed_paths: list[int] = []

    if not rows:
        overlap_rows, overlap_sources = load_saved_overlap_rows(
            scenario_slug,
            euler_steps,
            requested_path_set,
            reference_direct_price,
        )
        rows.extend(overlap_rows)
        sources.extend(overlap_sources)
        reused_paths = sorted({int(row["paths"]) for row in rows})

        scratch_dir = SCRATCH_ROOT / f"{scenario_slug}_steps{euler_steps}"
        scratch_dir.mkdir(parents=True, exist_ok=True)
        try:
            existing_keys = {(int(row["paths"]), str(row["method"])) for row in rows}
            for paths in requested_paths:
                for method in ("benchmark", "hybrid"):
                    if (paths, method) in existing_keys:
                        continue
                    rows.append(
                        compute_row(
                            scenario_slug,
                            euler_steps,
                            paths,
                            method,
                            reference_direct_price,
                            scratch_dir / f"{method}_{paths}",
                        )
                    )
                    computed_paths.append(paths)
        finally:
            if scratch_dir.exists():
                shutil.rmtree(scratch_dir)

    rows.sort(key=lambda item: (int(item["paths"]), str(item["method"])))
    write_csv(output_csv, rows)

    if rows and len(reused_paths) == len(requested_paths):
        reuse_mode = "reused_directly"
    elif reused_paths:
        reuse_mode = "mixed_saved_and_computed"
    else:
        reuse_mode = "computed_locally"

    meta = {
        "scenario_slug": scenario_slug,
        "scenario_label": SCENARIOS[scenario_slug]["benchmark_label"],
        "display_label": SCENARIOS[scenario_slug]["display"],
        "strike": SCENARIOS[scenario_slug]["strike"],
        "euler_steps": euler_steps,
        "path_counts": requested_paths,
        "reuse_mode": reuse_mode,
        "source_paths": sorted(set(sources)),
        "reused_paths": reused_paths,
        "computed_paths": sorted(set(computed_paths)),
        "output_csv": str(output_csv),
        "benchmark_reference_price": reference_direct_price,
        "benchmark_source_paths": [
            str(external_source_path(BENCHMARK_SOURCE_FILENAMES["benchmark_main"])),
            str(external_source_path(BENCHMARK_SOURCE_FILENAMES["benchmark_tail"])),
        ],
        "benchmark_script": str(BENCHMARK_SCRIPT),
        "hybrid_script": str(HYBRID_SCRIPT),
    }
    write_meta(output_meta, meta)
    print(f"Prepared {output_csv.name}")


def main() -> None:
    args = parse_args()
    ensure_dirs()
    reference_lookup = benchmark_lookup()
    for euler_steps in sorted(set(args.steps)):
        prepare_combo(
            args.scenario,
            euler_steps,
            args.paths,
            reference_lookup,
            args.force,
        )


if __name__ == "__main__":
    main()
