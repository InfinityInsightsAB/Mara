#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np


THIS_DIR = Path(__file__).resolve().parent
BENCHMARK_SCRIPT = THIS_DIR / "LSMC Benchmark" / "run_gdmr_benchmark_put.py"
HYBRID_SCRIPT = THIS_DIR / "Hybrid LSMC-PDE with FFT" / "run_gdmr_hybrid_put.py"
SCRATCH_DIR = THIS_DIR / "_scratch"

BASELINE_TABLE = THIS_DIR / "bgk_r00_t1_nex12_comparison_table.csv"
SUMMARY_PATH = THIS_DIR / "bgk_r00_t1_nex12_step_sweep_summary.md"
TABLE_PATH = THIS_DIR / "bgk_r00_t1_nex12_step_sweep_table.csv"
OUTPUT_STEM = "bgk_r00_t1_nex12_step_sweep"
CI_Z = 1.96

BENCHMARK_PATTERNS = {
    "lsmc_direct_price": r"LSMC direct price:\s*([0-9eE+\-.]+)",
    "lsmc_direct_error": r"LSMC direct error:\s*([0-9eE+\-.]+)",
    "lsmc_low_price": r"LSMC low price:\s*([0-9eE+\-.]+)",
    "lsmc_low_error": r"LSMC low error:\s*([0-9eE+\-.]+)",
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

SCENARIOS = [
    {"slug": "atm", "label": "ATM", "GDMR_S0": "100.0", "GDMR_STRIKE": "100.0", "GDMR_MATURITY": "1.0"},
    {"slug": "itm", "label": "ITM put", "GDMR_S0": "100.0", "GDMR_STRIKE": "110.0", "GDMR_MATURITY": "1.0"},
    {"slug": "otm", "label": "OTM put", "GDMR_S0": "100.0", "GDMR_STRIKE": "90.0", "GDMR_MATURITY": "1.0"},
]

SCENARIO_LOOKUP = {scenario["slug"]: scenario for scenario in SCENARIOS}

DEFAULT_STEP_COUNTS = [12, 24, 48, 72, 120, 240, 600]

BENCHMARK_SWEEP_ENV = {
    "GDMR_LSMC_PATHS": "1000000",
    "GDMR_LSMC_LOW_PATHS": "1000000",
    "GDMR_LSMC_SEED": "2026",
    "GDMR_LSMC_LOW_SEED": "2103",
}

HYBRID_SWEEP_ENV = {
    "GDMR_HYBRID_PATHS": "60000",
    "GDMR_HYBRID_LOW_PATHS": "60000",
    "GDMR_HYBRID_ASSET_POINTS": "301",
    "GDMR_HYBRID_ASSET_LOW_FACTOR": "0.30",
    "GDMR_HYBRID_ASSET_HIGH_FACTOR": "3.50",
    "GDMR_HYBRID_VOL_QUANTILE": "0.999",
    "GDMR_HYBRID_FST_PAD_FACTOR": "4",
    "GDMR_HYBRID_FST_BATCH_SIZE": "256",
    "GDMR_HYBRID_SEED": "2026",
    "GDMR_HYBRID_LOW_SEED": "2103",
}

CSV_COLUMNS = [
    "scenario",
    "euler_steps",
    "method",
    "runtime_seconds",
    "benchmark_direct_reference",
    "benchmark_low_reference",
    "price_direct",
    "se_direct",
    "rel_error_direct",
    "rel_ci_lower_direct",
    "rel_ci_upper_direct",
    "price_low",
    "se_low",
    "rel_error_low",
    "rel_ci_lower_low",
    "rel_ci_upper_low",
    "direct_low_gap",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a 12-date Euler-step sweep for the BGK LSMC benchmark and tuned Hybrid LSMC-PDE."
    )
    parser.add_argument(
        "--scenarios",
        nargs="*",
        choices=sorted(SCENARIO_LOOKUP),
        default=["atm", "otm"],
        help="Scenario slugs to sweep. Defaults to atm and otm.",
    )
    parser.add_argument(
        "--steps",
        nargs="*",
        type=int,
        default=DEFAULT_STEP_COUNTS,
        help="Euler step counts to test. Defaults to a curated 7-point grid.",
    )
    return parser.parse_args()


def rel_error(value: float, reference: float) -> float:
    scale = abs(reference)
    if scale <= 1e-16:
        return 0.0 if abs(value) <= 1e-16 else float("inf")
    return abs(value - reference) / scale


def gap_pct(low: float, direct: float) -> float:
    if abs(direct) <= 1e-16:
        return float("inf")
    return (low - direct) / direct


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


def format_pct(value: float) -> str:
    return f"{100.0 * value:.3f}%"


def format_steps(value: int) -> str:
    return f"{value:d}"


def load_baseline_reference() -> dict[str, dict[str, float]]:
    if not BASELINE_TABLE.exists():
        raise FileNotFoundError(
            f"Missing baseline table {BASELINE_TABLE.name}. Run the 12-date comparison first."
        )
    data: dict[str, dict[str, float]] = {}
    with BASELINE_TABLE.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            data[row["scenario"]] = {
                "benchmark_direct_price": float(row["benchmark_direct_price"]),
                "benchmark_direct_error": float(row["benchmark_direct_error"]),
                "benchmark_low_price": float(row["benchmark_low_price"]),
                "benchmark_low_error": float(row["benchmark_low_error"]),
            }
    return data


def run_benchmark(env: dict[str, str]) -> tuple[dict[str, float], float]:
    started = os.times()[4]
    completed = subprocess.run(
        [sys.executable, str(BENCHMARK_SCRIPT)],
        cwd=str(THIS_DIR),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    elapsed = os.times()[4] - started
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
    started = os.times()[4]
    completed = subprocess.run(
        [sys.executable, str(HYBRID_SCRIPT)],
        cwd=str(THIS_DIR),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    elapsed = os.times()[4] - started
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
    values = {
        "hybrid_direct_price": float(raw["hybrid_direct_price"]),
        "hybrid_direct_error": float(raw["hybrid_direct_error"]),
        "hybrid_low_price": float(raw["hybrid_low_price"]),
        "hybrid_low_error": float(raw["hybrid_low_error"]),
    }
    return values, elapsed


def build_env(step_count: int, scenario: dict[str, str], method: str) -> dict[str, str]:
    env = os.environ.copy()
    env.update(BGK_MODEL_ENV)
    env.update(
        {
            "GDMR_S0": scenario["GDMR_S0"],
            "GDMR_STRIKE": scenario["GDMR_STRIKE"],
            "GDMR_MATURITY": scenario["GDMR_MATURITY"],
            "GDMR_EULER_STEPS": str(step_count),
        }
    )
    if method == "benchmark":
        SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
        env.update(BENCHMARK_SWEEP_ENV)
        env["GDMR_LSMC_STORE_DIR"] = str(SCRATCH_DIR)
    elif method == "hybrid":
        env.update(HYBRID_SWEEP_ENV)
    else:
        raise ValueError(f"Unknown method {method!r}")
    return env


def method_row(
    scenario_label: str,
    step_count: int,
    method: str,
    runtime_seconds: float,
    direct_price: float,
    direct_se: float,
    low_price: float,
    low_se: float,
    benchmark_reference: dict[str, float],
) -> dict[str, float | str]:
    direct_reference = benchmark_reference["benchmark_direct_price"]
    low_reference = benchmark_reference["benchmark_low_price"]
    direct_rel_error = rel_error(direct_price, direct_reference)
    low_rel_error = rel_error(low_price, low_reference)
    direct_rel_ci_lower, direct_rel_ci_upper = rel_error_ci_bounds(direct_price, direct_se, direct_reference)
    low_rel_ci_lower, low_rel_ci_upper = rel_error_ci_bounds(low_price, low_se, low_reference)
    return {
        "scenario": scenario_label,
        "euler_steps": step_count,
        "method": method,
        "runtime_seconds": runtime_seconds,
        "benchmark_direct_reference": direct_reference,
        "benchmark_low_reference": low_reference,
        "price_direct": direct_price,
        "se_direct": direct_se,
        "rel_error_direct": direct_rel_error,
        "rel_ci_lower_direct": direct_rel_ci_lower,
        "rel_ci_upper_direct": direct_rel_ci_upper,
        "price_low": low_price,
        "se_low": low_se,
        "rel_error_low": low_rel_error,
        "rel_ci_lower_low": low_rel_ci_lower,
        "rel_ci_upper_low": low_rel_ci_upper,
        "direct_low_gap": gap_pct(low_price, direct_price),
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


def figure_path(scenario_slug: str, estimator_key: str) -> Path:
    return THIS_DIR / f"{OUTPUT_STEM}_{scenario_slug}_{estimator_key}_relative_error_with_ci.svg"


def render_relative_error_figure(
    output_path: Path,
    scenario: dict[str, str],
    scenario_rows: list[dict[str, float | str]],
    estimator_key: str,
) -> None:
    width = 1260
    height = 800
    font = "Segoe UI, Arial, sans-serif"
    left = 115
    right = 1150
    top = 250
    bottom = 620
    chart_width = right - left
    chart_height = bottom - top
    legend_y = 210

    estimator_label = "direct" if estimator_key == "direct" else "low"
    reference_label = "benchmark direct" if estimator_key == "direct" else "benchmark low"
    title = f"{scenario['label']}: {estimator_label.capitalize()} relative error vs fixed benchmark"

    y_max = max(
        0.005,
        max(
            float(row[f"rel_ci_upper_{estimator_key}"])
            for row in scenario_rows
        ) * 1.15,
    )

    step_values = sorted({int(row["euler_steps"]) for row in scenario_rows})
    x_min = min(step_values)
    x_max = max(step_values)

    def x_of(step_count: float) -> float:
        if x_max == x_min:
            return left + chart_width / 2.0
        return left + (step_count - x_min) / (x_max - x_min) * chart_width

    def y_of(value: float) -> float:
        return bottom - value / y_max * chart_height

    method_styles = [
        ("benchmark", "#1d4ed8", "LSMC benchmark"),
        ("hybrid", "#d97706", "Hybrid LSMC-PDE"),
    ]

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f3efe7"/>',
        '<rect x="30" y="28" width="1200" height="744" rx="28" fill="#fffdf9" stroke="#ddd4c6"/>',
        f'<text x="72" y="88" font-family="{font}" font-size="31" font-weight="700" fill="#17202a">{title}</text>',
        f'<text x="72" y="118" font-family="{font}" font-size="15" fill="#475569">Fixed benchmark reference is the 12-date, 600-step benchmark value from bgk_r00_t1_nex12_comparison_table.csv.</text>',
        f'<text x="72" y="146" font-family="{font}" font-size="14" fill="#64748b">Hybrid uses the tuned setting: 60,000 paths, 301 asset points, range 0.30 to 3.50, vol quantile 0.999.</text>',
        f'<text x="72" y="174" font-family="{font}" font-size="14" fill="#64748b">Relative errors are measured against the fixed {reference_label} reference while Euler steps vary and exercise dates stay at 12.</text>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" stroke="#334155" stroke-width="1.6"/>',
        f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="#334155" stroke-width="1.6"/>',
    ]

    y_ticks = np.linspace(0.0, y_max, 6)
    for tick in y_ticks:
        y = y_of(float(tick))
        lines.append(f'<line x1="{left}" y1="{y:.2f}" x2="{right}" y2="{y:.2f}" stroke="#ece5d8" stroke-width="1"/>')
        lines.append(
            f'<text x="{left - 12}" y="{y + 5:.2f}" text-anchor="end" font-family="{font}" font-size="12" fill="#64748b">{100.0 * tick:.2f}%</text>'
        )

    for step_count in step_values:
        x = x_of(float(step_count))
        lines.append(f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" y2="{bottom}" stroke="#f3eee4" stroke-width="1"/>')
        lines.append(
            f'<text x="{x:.2f}" y="{bottom + 24}" text-anchor="middle" font-family="{font}" font-size="11" fill="#64748b">{step_count}</text>'
        )

    lines.append(
        f'<text x="{left - 78}" y="{top + chart_height / 2:.2f}" transform="rotate(-90 {left - 78} {top + chart_height / 2:.2f})" font-family="{font}" font-size="13" fill="#475569">Relative error</text>'
    )
    lines.append(
        f'<text x="{(left + right) / 2:.2f}" y="{bottom + 52}" text-anchor="middle" font-family="{font}" font-size="13" fill="#475569">Euler steps</text>'
    )

    for legend_index, (method_key, color, label) in enumerate(method_styles):
        x0 = 72 + 330 * legend_index
        lines.append(f'<line x1="{x0}" y1="{legend_y}" x2="{x0 + 34}" y2="{legend_y}" stroke="{color}" stroke-width="4"/>')
        lines.append(f'<circle cx="{x0 + 17}" cy="{legend_y}" r="5.5" fill="{color}" stroke="#fffdf9" stroke-width="2"/>')
        lines.append(f'<text x="{x0 + 46}" y="{legend_y + 5}" font-family="{font}" font-size="14" fill="#334155">{label}</text>')

        method_rows = [row for row in scenario_rows if row["method"] == method_key]
        polyline = []
        for row in method_rows:
            polyline.append(
                f"{x_of(float(row['euler_steps'])):.2f},{y_of(float(row[f'rel_error_{estimator_key}'])):.2f}"
            )
        lines.append(
            f'<polyline fill="none" stroke="{color}" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round" points="{" ".join(polyline)}"/>'
        )
        for row in method_rows:
            x = x_of(float(row["euler_steps"]))
            y = y_of(float(row[f"rel_error_{estimator_key}"]))
            y_low = y_of(float(row[f"rel_ci_lower_{estimator_key}"]))
            y_high = y_of(float(row[f"rel_ci_upper_{estimator_key}"]))
            lines.append(
                f'<line x1="{x:.2f}" y1="{y_high:.2f}" x2="{x:.2f}" y2="{y_low:.2f}" stroke="{color}" stroke-width="2.0" opacity="0.82"/>'
            )
            lines.append(
                f'<line x1="{x - 6:.2f}" y1="{y_high:.2f}" x2="{x + 6:.2f}" y2="{y_high:.2f}" stroke="{color}" stroke-width="2.0" opacity="0.82"/>'
            )
            lines.append(
                f'<line x1="{x - 6:.2f}" y1="{y_low:.2f}" x2="{x + 6:.2f}" y2="{y_low:.2f}" stroke="{color}" stroke-width="2.0" opacity="0.82"/>'
            )
            lines.append(
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5.8" fill="{color}" stroke="#fffdf9" stroke-width="2"/>'
            )

    lines.append("</svg>")
    output_path.write_text("\n".join(lines), encoding="utf-8")


def build_summary(
    rows: list[dict[str, float | str]],
    baseline_reference: dict[str, dict[str, float]],
    selected_scenarios: list[dict[str, str]],
    step_counts: list[int],
) -> str:
    lines = [
        "# BGK 12-date Euler Step Sweep",
        "",
        "This note compares the LSMC benchmark and the tuned Hybrid LSMC-PDE as Euler steps decrease while the Bermudan exercise dates stay fixed at 12.",
        "The reference for relative errors is the fixed benchmark from `bgk_r00_t1_nex12_comparison_table.csv` with `GDMR_EULER_STEPS=600`.",
        "",
        "## Fixed model block",
        "",
        "```text",
    ]
    lines.extend(f"{key}={value}" for key, value in BGK_MODEL_ENV.items())
    lines.extend(
        [
            "```",
            "",
            "## Sweep settings",
            "",
            f"- Scenarios swept: `{', '.join(scenario['label'] for scenario in selected_scenarios)}`",
            f"- Euler steps tested: `{', '.join(str(value) for value in step_counts)}`",
            f"- Benchmark paths: `{BENCHMARK_SWEEP_ENV['GDMR_LSMC_PATHS']}`",
            f"- Benchmark low paths: `{BENCHMARK_SWEEP_ENV['GDMR_LSMC_LOW_PATHS']}`",
            f"- Hybrid paths: `{HYBRID_SWEEP_ENV['GDMR_HYBRID_PATHS']}`",
            f"- Hybrid low paths: `{HYBRID_SWEEP_ENV['GDMR_HYBRID_LOW_PATHS']}`",
            f"- Hybrid asset points: `{HYBRID_SWEEP_ENV['GDMR_HYBRID_ASSET_POINTS']}`",
            f"- Hybrid asset range factors: `{HYBRID_SWEEP_ENV['GDMR_HYBRID_ASSET_LOW_FACTOR']}` / `{HYBRID_SWEEP_ENV['GDMR_HYBRID_ASSET_HIGH_FACTOR']}`",
            f"- Hybrid vol quantile: `{HYBRID_SWEEP_ENV['GDMR_HYBRID_VOL_QUANTILE']}`",
            "",
        ]
    )

    for scenario in selected_scenarios:
        scenario_rows = [row for row in rows if row["scenario"] == scenario["label"]]
        reference = baseline_reference[scenario["label"]]
        lines.extend(
            [
                f"## {scenario['label']}",
                "",
                f"- Fixed benchmark direct reference: `{reference['benchmark_direct_price']:.6f}`",
                f"- Fixed benchmark low reference: `{reference['benchmark_low_price']:.6f}`",
                "",
            ]
        )
        table_rows = []
        for row in sorted(scenario_rows, key=lambda item: (int(item["euler_steps"]), str(item["method"]))):
            table_rows.append(
                [
                    f"`{int(row['euler_steps'])}`",
                    f"`{row['method']}`",
                    f"`{float(row['price_direct']):.6f}`",
                    f"`{float(row['se_direct']):.6f}`",
                    f"`{format_pct(float(row['rel_error_direct']))}`",
                    f"`{float(row['price_low']):.6f}`",
                    f"`{float(row['se_low']):.6f}`",
                    f"`{format_pct(float(row['rel_error_low']))}`",
                    f"`{float(row['runtime_seconds']):.2f} s`",
                ]
            )
        lines.append(
            markdown_table(
                [
                    "Euler steps",
                    "Method",
                    "Direct price",
                    "Direct SE",
                    "Direct rel. error",
                    "Low price",
                    "Low SE",
                    "Low rel. error",
                    "Runtime",
                ],
                table_rows,
            )
        )
        lines.extend(
            [
                "",
                f"![{scenario['label']} direct relative error]({figure_path(scenario['slug'], 'direct')})",
                "",
                f"![{scenario['label']} low relative error]({figure_path(scenario['slug'], 'low')})",
                "",
            ]
        )

    lines.extend(
        [
            f"Saved CSV: `{TABLE_PATH.name}`",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    selected_scenarios = [SCENARIO_LOOKUP[slug] for slug in args.scenarios]
    step_counts = sorted(set(args.steps))
    baseline_reference = load_baseline_reference()
    rows: list[dict[str, float | str]] = []
    try:
        for scenario in selected_scenarios:
            reference = baseline_reference[scenario["label"]]
            for step_count in step_counts:
                benchmark_env = build_env(step_count, scenario, "benchmark")
                benchmark, benchmark_runtime = run_benchmark(benchmark_env)
                rows.append(
                    method_row(
                        scenario["label"],
                        step_count,
                        "benchmark",
                        benchmark_runtime,
                        benchmark["lsmc_direct_price"],
                        benchmark["lsmc_direct_error"],
                        benchmark["lsmc_low_price"],
                        benchmark["lsmc_low_error"],
                        reference,
                    )
                )

                hybrid_env = build_env(step_count, scenario, "hybrid")
                hybrid, hybrid_runtime = run_hybrid(hybrid_env)
                rows.append(
                    method_row(
                        scenario["label"],
                        step_count,
                        "hybrid",
                        hybrid_runtime,
                        hybrid["hybrid_direct_price"],
                        hybrid["hybrid_direct_error"],
                        hybrid["hybrid_low_price"],
                        hybrid["hybrid_low_error"],
                        reference,
                    )
                )

        write_csv(TABLE_PATH, rows)
        for scenario in selected_scenarios:
            scenario_rows = [row for row in rows if row["scenario"] == scenario["label"]]
            render_relative_error_figure(figure_path(scenario["slug"], "direct"), scenario, scenario_rows, "direct")
            render_relative_error_figure(figure_path(scenario["slug"], "low"), scenario, scenario_rows, "low")
        SUMMARY_PATH.write_text(
            build_summary(rows, baseline_reference, selected_scenarios, step_counts),
            encoding="utf-8",
        )
    finally:
        if SCRATCH_DIR.exists():
            shutil.rmtree(SCRATCH_DIR)

    print("Step sweep completed.")
    print(f"Summary: {SUMMARY_PATH.name}")
    print(f"Table:   {TABLE_PATH.name}")


if __name__ == "__main__":
    main()
