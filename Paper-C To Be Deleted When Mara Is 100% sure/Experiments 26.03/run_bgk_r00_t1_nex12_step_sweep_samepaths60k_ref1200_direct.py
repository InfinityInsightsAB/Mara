#!/usr/bin/env python3
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


THIS_DIR = Path(__file__).resolve().parent
BENCHMARK_SCRIPT = THIS_DIR / "LSMC Benchmark" / "run_gdmr_benchmark_put.py"
HYBRID_SCRIPT = THIS_DIR / "Hybrid LSMC-PDE with FFT" / "run_gdmr_hybrid_put.py"
REFERENCE_TABLE = THIS_DIR / "bgk_r00_t1_nex12_benchmark_steps1200_paths1200000_k80_k70_table.csv"
CI_Z = 1.96
STEP_COUNTS = [12, 24, 48, 72, 120]
MATCHED_PATHS = 60000

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
}

SCENARIOS = {
    "k80": {"slug": "k80", "label": "K=80 put", "GDMR_STRIKE": "80.0", "GDMR_MATURITY": "1.0"},
    "k70": {"slug": "k70", "label": "K=70 put", "GDMR_STRIKE": "70.0", "GDMR_MATURITY": "1.0"},
}

CSV_COLUMNS = [
    "scenario",
    "K",
    "euler_steps",
    "method",
    "runtime_seconds",
    "reference_direct_price",
    "reference_direct_error",
    "price_direct",
    "se_direct",
    "direct_ci_lower",
    "direct_ci_upper",
    "rel_error_direct",
    "rel_ci_lower_direct",
    "rel_ci_upper_direct",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the BGK 12-date K=80 or K=70 direct step sweep with the same 60,000 paths for both methods."
    )
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), required=True)
    return parser.parse_args()


def output_stem(scenario_slug: str) -> str:
    return f"bgk_r00_t1_nex12_step_sweep_{scenario_slug}_ref1200_direct_samepaths60k"


def summary_path(scenario_slug: str) -> Path:
    return THIS_DIR / f"{output_stem(scenario_slug)}_summary.md"


def table_path(scenario_slug: str) -> Path:
    return THIS_DIR / f"{output_stem(scenario_slug)}_table.csv"


def scratch_dir(scenario_slug: str) -> Path:
    return THIS_DIR / f"_scratch_{output_stem(scenario_slug)}"


def ci_bounds(value: float, se: float) -> tuple[float, float]:
    half_width = CI_Z * se
    return value - half_width, value + half_width


def rel_error(value: float, reference: float) -> float:
    scale = abs(reference)
    if scale <= 1e-16:
        return 0.0 if abs(value) <= 1e-16 else float("inf")
    return abs(value - reference) / scale


def rel_error_ci_bounds(value: float, se: float, reference: float) -> tuple[float, float]:
    low_value, high_value = ci_bounds(value, se)
    endpoint_errors = (
        rel_error(low_value, reference),
        rel_error(high_value, reference),
    )
    if low_value <= reference <= high_value:
        return 0.0, max(endpoint_errors)
    return min(endpoint_errors), max(endpoint_errors)


def format_pct(value: float) -> str:
    return f"{100.0 * value:.3f}%"


def load_reference_map() -> dict[str, dict[str, float]]:
    data: dict[str, dict[str, float]] = {}
    with REFERENCE_TABLE.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            data[row["scenario"]] = {
                "benchmark_direct_price": float(row["benchmark_direct_price"]),
                "benchmark_direct_error": float(row["benchmark_direct_error"]),
                "benchmark_direct_ci_lower": float(row["benchmark_direct_ci_lower"]),
                "benchmark_direct_ci_upper": float(row["benchmark_direct_ci_upper"]),
                "runtime_seconds": float(row["runtime_seconds"]),
            }
    return data


def build_env(step_count: int, scenario: dict[str, str], method: str, run_scratch_dir: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.update(BGK_MODEL_ENV)
    env.update(
        {
            "GDMR_STRIKE": scenario["GDMR_STRIKE"],
            "GDMR_MATURITY": scenario["GDMR_MATURITY"],
            "GDMR_EULER_STEPS": str(step_count),
        }
    )
    if method == "benchmark":
        run_scratch_dir.mkdir(parents=True, exist_ok=True)
        env.update(
            {
                "GDMR_LSMC_PATHS": str(MATCHED_PATHS),
                "GDMR_LSMC_LOW_PATHS": str(MATCHED_PATHS),
                "GDMR_LSMC_SEED": "2026",
                "GDMR_LSMC_LOW_SEED": "2103",
                "GDMR_LSMC_STORE_DIR": str(run_scratch_dir),
            }
        )
    elif method == "hybrid":
        env.update(
            {
                "GDMR_HYBRID_PATHS": str(MATCHED_PATHS),
                "GDMR_HYBRID_LOW_PATHS": str(MATCHED_PATHS),
                "GDMR_HYBRID_ASSET_POINTS": "301",
                "GDMR_HYBRID_ASSET_LOW_FACTOR": "0.30",
                "GDMR_HYBRID_ASSET_HIGH_FACTOR": "3.50",
                "GDMR_HYBRID_VOL_QUANTILE": "0.999",
                "GDMR_HYBRID_FST_PAD_FACTOR": "4",
                "GDMR_HYBRID_FST_BATCH_SIZE": "256",
                "GDMR_HYBRID_SEED": "2026",
                "GDMR_HYBRID_LOW_SEED": "2103",
            }
        )
    else:
        raise ValueError(f"Unknown method {method!r}")
    return env


def run_benchmark(env: dict[str, str]) -> tuple[dict[str, float], float]:
    started = time.perf_counter()
    completed = subprocess.run(
        [sys.executable, str(BENCHMARK_SCRIPT)],
        cwd=str(THIS_DIR),
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
    return values, elapsed


def run_hybrid(env: dict[str, str]) -> tuple[dict[str, float], float]:
    started = time.perf_counter()
    completed = subprocess.run(
        [sys.executable, str(HYBRID_SCRIPT)],
        cwd=str(THIS_DIR),
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
    return {
        "hybrid_direct_price": float(raw["hybrid_direct_price"]),
        "hybrid_direct_error": float(raw["hybrid_direct_error"]),
    }, elapsed


def method_row(
    scenario: dict[str, str],
    step_count: int,
    method: str,
    runtime_seconds: float,
    direct_price: float,
    direct_se: float,
    reference: dict[str, float],
) -> dict[str, float | str]:
    direct_ci_lower, direct_ci_upper = ci_bounds(direct_price, direct_se)
    rel_ci_lower_direct, rel_ci_upper_direct = rel_error_ci_bounds(
        direct_price,
        direct_se,
        reference["benchmark_direct_price"],
    )
    return {
        "scenario": scenario["label"],
        "K": float(scenario["GDMR_STRIKE"]),
        "euler_steps": step_count,
        "method": method,
        "runtime_seconds": runtime_seconds,
        "reference_direct_price": reference["benchmark_direct_price"],
        "reference_direct_error": reference["benchmark_direct_error"],
        "price_direct": direct_price,
        "se_direct": direct_se,
        "direct_ci_lower": direct_ci_lower,
        "direct_ci_upper": direct_ci_upper,
        "rel_error_direct": rel_error(direct_price, reference["benchmark_direct_price"]),
        "rel_ci_lower_direct": rel_ci_lower_direct,
        "rel_ci_upper_direct": rel_ci_upper_direct,
    }


def write_csv(path: Path, rows: list[dict[str, float | str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in CSV_COLUMNS})


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def build_interpretation(rows: list[dict[str, float | str]]) -> list[str]:
    benchmark_rows = {int(row["euler_steps"]): row for row in rows if row["method"] == "benchmark"}
    hybrid_rows = {int(row["euler_steps"]): row for row in rows if row["method"] == "hybrid"}
    hybrid_better = []
    benchmark_better = []
    for step_count in STEP_COUNTS:
        benchmark_error = float(benchmark_rows[step_count]["rel_error_direct"])
        hybrid_error = float(hybrid_rows[step_count]["rel_error_direct"])
        if hybrid_error < benchmark_error:
            hybrid_better.append(step_count)
        elif benchmark_error < hybrid_error:
            benchmark_better.append(step_count)

    benchmark_runtime_total = sum(float(benchmark_rows[step]["runtime_seconds"]) for step in STEP_COUNTS)
    hybrid_runtime_total = sum(float(hybrid_rows[step]["runtime_seconds"]) for step in STEP_COUNTS)

    lines = []
    if hybrid_better:
        lines.append(f"- Hybrid direct error is lower at steps `{', '.join(str(step) for step in hybrid_better)}`.")
    if benchmark_better:
        lines.append(f"- LSMC direct error is lower at steps `{', '.join(str(step) for step in benchmark_better)}`.")
    lines.append(
        f"- Total runtime across the five-step sweep is `{benchmark_runtime_total:.2f} s` for LSMC versus `{hybrid_runtime_total:.2f} s` for Hybrid."
    )
    return lines


def build_summary(
    scenario: dict[str, str],
    rows: list[dict[str, float | str]],
    reference: dict[str, float],
) -> str:
    headers = [
        "Euler steps",
        "Method",
        "Direct price",
        "Direct SE",
        "Direct 95% CI",
        "Direct rel. error",
        "Rel. error CI",
        "Runtime",
    ]
    table_rows = []
    for row in rows:
        table_rows.append(
            [
                f"`{int(row['euler_steps'])}`",
                f"`{row['method']}`",
                f"`{float(row['price_direct']):.6f}`",
                f"`{float(row['se_direct']):.6f}`",
                f"`[{float(row['direct_ci_lower']):.6f}, {float(row['direct_ci_upper']):.6f}]`",
                f"`{format_pct(float(row['rel_error_direct']))}`",
                f"`[{format_pct(float(row['rel_ci_lower_direct']))}, {format_pct(float(row['rel_ci_upper_direct']))}]`",
                f"`{float(row['runtime_seconds']):.2f} s`",
            ]
        )

    lines = [
        f"# BGK 12-date {scenario['label']} step sweep with matched 60,000 paths",
        "",
        "This note compares LSMC and the tuned Hybrid LSMC-PDE using the same direct path count for both methods.",
        f"Direct relative errors are measured against the fixed 1200-step benchmark reference from `{REFERENCE_TABLE.name}`.",
        "",
        "## Fixed reference",
        "",
        markdown_table(
            ["Scenario", "Reference direct", "Reference SE", "Reference 95% CI", "Reference runtime"],
            [[
                f"`{scenario['label']}`",
                f"`{reference['benchmark_direct_price']:.6f}`",
                f"`{reference['benchmark_direct_error']:.6f}`",
                f"`[{reference['benchmark_direct_ci_lower']:.6f}, {reference['benchmark_direct_ci_upper']:.6f}]`",
                f"`{reference['runtime_seconds']:.2f} s`",
            ]],
        ),
        "",
        "## Sweep settings",
        "",
        f"- Euler steps tested: `{', '.join(str(step) for step in STEP_COUNTS)}`",
        f"- LSMC paths: `{MATCHED_PATHS}`",
        f"- Hybrid paths: `{MATCHED_PATHS}`",
        "- Hybrid tuning kept fixed at: asset points `301`, asset range `0.30 / 3.50`, vol quantile `0.999`.",
        "",
        "## Results",
        "",
        markdown_table(headers, table_rows),
        "",
        "Short interpretation:",
        *build_interpretation(rows),
        "",
        f"Saved CSV: `{table_path(scenario['slug']).name}`",
    ]
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    scenario = SCENARIOS[args.scenario]
    reference = load_reference_map()[scenario["label"]]
    rows: list[dict[str, float | str]] = []
    run_scratch_dir = scratch_dir(scenario["slug"])
    success = False
    try:
        for step_count in STEP_COUNTS:
            benchmark, benchmark_runtime = run_benchmark(build_env(step_count, scenario, "benchmark", run_scratch_dir))
            rows.append(
                method_row(
                    scenario,
                    step_count,
                    "benchmark",
                    benchmark_runtime,
                    benchmark["lsmc_direct_price"],
                    benchmark["lsmc_direct_error"],
                    reference,
                )
            )
            hybrid, hybrid_runtime = run_hybrid(build_env(step_count, scenario, "hybrid", run_scratch_dir))
            rows.append(
                method_row(
                    scenario,
                    step_count,
                    "hybrid",
                    hybrid_runtime,
                    hybrid["hybrid_direct_price"],
                    hybrid["hybrid_direct_error"],
                    reference,
                )
            )
            print(
                f"{scenario['label']} step {step_count}: "
                f"LSMC {benchmark['lsmc_direct_price']:.6f} +/- {benchmark['lsmc_direct_error']:.6f}, "
                f"Hybrid {hybrid['hybrid_direct_price']:.6f} +/- {hybrid['hybrid_direct_error']:.6f}",
                flush=True,
            )

        rows.sort(key=lambda item: (int(item["euler_steps"]), str(item["method"])))
        write_csv(table_path(scenario["slug"]), rows)
        summary_path(scenario["slug"]).write_text(build_summary(scenario, rows, reference), encoding="utf-8")
        success = True
    finally:
        if success and run_scratch_dir.exists():
            shutil.rmtree(run_scratch_dir)

    print(f"Summary: {summary_path(scenario['slug']).name}")
    print(f"Table:   {table_path(scenario['slug']).name}")


if __name__ == "__main__":
    main()
