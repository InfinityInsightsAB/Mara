#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
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
SCRATCH_DIR = THIS_DIR / "_scratch_step_sweep_k80_k70_ref1200_direct"

OUTPUT_STEM = "bgk_r00_t1_nex12_step_sweep_k80_k70_ref1200_direct"
SUMMARY_PATH = THIS_DIR / f"{OUTPUT_STEM}_summary.md"
TABLE_PATH = THIS_DIR / f"{OUTPUT_STEM}_table.csv"
CI_Z = 1.96

STEP_COUNTS = [12, 24, 48, 72, 120]

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
    {"slug": "k80", "label": "K=80 put", "GDMR_STRIKE": "80.0", "GDMR_MATURITY": "1.0"},
    {"slug": "k70", "label": "K=70 put", "GDMR_STRIKE": "70.0", "GDMR_MATURITY": "1.0"},
]

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
    if not REFERENCE_TABLE.exists():
        raise FileNotFoundError(
            f"Missing fixed reference table {REFERENCE_TABLE.name}. Run the K=80 / K=70 benchmark references first."
        )
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


def build_env(step_count: int, scenario: dict[str, str], method: str) -> dict[str, str]:
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
        SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
        env.update(BENCHMARK_SWEEP_ENV)
        env["GDMR_LSMC_STORE_DIR"] = str(SCRATCH_DIR)
    elif method == "hybrid":
        env.update(HYBRID_SWEEP_ENV)
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
    values = {
        "hybrid_direct_price": float(raw["hybrid_direct_price"]),
        "hybrid_direct_error": float(raw["hybrid_direct_error"]),
    }
    return values, elapsed


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


def write_csv(rows: list[dict[str, float | str]]) -> None:
    with TABLE_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in CSV_COLUMNS})


def direct_figure_path(scenario_slug: str) -> Path:
    return THIS_DIR / f"bgk_r00_t1_nex12_step_sweep_{scenario_slug}_ref1200_direct_relative_error_with_ci.svg"


def runtime_figure_path(scenario_slug: str) -> Path:
    return THIS_DIR / f"bgk_r00_t1_nex12_step_sweep_{scenario_slug}_ref1200_runtime.svg"


def render_direct_error_figure(
    output_path: Path,
    scenario: dict[str, str],
    scenario_rows: list[dict[str, float | str]],
    reference: dict[str, float],
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

    y_max = max(0.005, max(float(row["rel_ci_upper_direct"]) for row in scenario_rows) * 1.15)
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
        ("benchmark", "#1d4ed8", "LSMC"),
        ("hybrid", "#d97706", "Hybrid LSMC-PDE"),
    ]

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f3efe7"/>',
        '<rect x="30" y="28" width="1200" height="744" rx="28" fill="#fffdf9" stroke="#ddd4c6"/>',
        f'<text x="72" y="88" font-family="{font}" font-size="31" font-weight="700" fill="#17202a">{scenario["label"]}: Direct relative error vs fixed 1200-step benchmark</text>',
        f'<text x="72" y="118" font-family="{font}" font-size="15" fill="#475569">Fixed direct reference comes from {REFERENCE_TABLE.name} with 1200 Euler steps and 1,200,000 benchmark paths.</text>',
        f'<text x="72" y="146" font-family="{font}" font-size="14" fill="#64748b">Reference direct price: {reference["benchmark_direct_price"]:.6f} with SE {reference["benchmark_direct_error"]:.6f}.</text>',
        f'<text x="72" y="174" font-family="{font}" font-size="14" fill="#64748b">Hybrid uses 60,000 paths, 301 asset points, range 0.30 to 3.50, and vol quantile 0.999 while Euler steps vary.</text>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" stroke="#334155" stroke-width="1.6"/>',
        f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="#334155" stroke-width="1.6"/>',
    ]

    for tick_index in range(6):
        tick = y_max * tick_index / 5.0
        y = y_of(tick)
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
                f"{x_of(float(row['euler_steps'])):.2f},{y_of(float(row['rel_error_direct'])):.2f}"
            )
        lines.append(
            f'<polyline fill="none" stroke="{color}" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round" points="{" ".join(polyline)}"/>'
        )
        for row in method_rows:
            x = x_of(float(row["euler_steps"]))
            y = y_of(float(row["rel_error_direct"]))
            y_low = y_of(float(row["rel_ci_lower_direct"]))
            y_high = y_of(float(row["rel_ci_upper_direct"]))
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


def render_runtime_figure(
    output_path: Path,
    scenario: dict[str, str],
    scenario_rows: list[dict[str, float | str]],
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

    runtime_values = [max(float(row["runtime_seconds"]), 1e-6) for row in scenario_rows]
    min_runtime = min(runtime_values)
    max_runtime = max(runtime_values)
    log_min = math.floor(math.log10(min_runtime))
    log_max = math.ceil(math.log10(max_runtime))

    step_values = sorted({int(row["euler_steps"]) for row in scenario_rows})
    x_min = min(step_values)
    x_max = max(step_values)

    def x_of(step_count: float) -> float:
        if x_max == x_min:
            return left + chart_width / 2.0
        return left + (step_count - x_min) / (x_max - x_min) * chart_width

    def y_of(seconds: float) -> float:
        clipped = max(seconds, 10 ** log_min)
        if log_max == log_min:
            return bottom - chart_height / 2.0
        return bottom - (math.log10(clipped) - log_min) / (log_max - log_min) * chart_height

    method_styles = [
        ("benchmark", "#1d4ed8", "LSMC"),
        ("hybrid", "#d97706", "Hybrid LSMC-PDE"),
    ]

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f3efe7"/>',
        '<rect x="30" y="28" width="1200" height="744" rx="28" fill="#fffdf9" stroke="#ddd4c6"/>',
        f'<text x="72" y="88" font-family="{font}" font-size="31" font-weight="700" fill="#17202a">{scenario["label"]}: Runtime vs Euler steps</text>',
        f'<text x="72" y="118" font-family="{font}" font-size="15" fill="#475569">Runtime is measured wall-clock time in seconds for the direct-and-low run behind each method output.</text>',
        f'<text x="72" y="146" font-family="{font}" font-size="14" fill="#64748b">The vertical axis uses a log scale so the benchmark and hybrid curves remain visible together.</text>',
        f'<text x="72" y="174" font-family="{font}" font-size="14" fill="#64748b">Benchmark uses 1,000,000 paths; Hybrid uses 60,000 paths with the tuned OTM numerical setting.</text>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" stroke="#334155" stroke-width="1.6"/>',
        f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="#334155" stroke-width="1.6"/>',
    ]

    tick_values = [10 ** exponent for exponent in range(log_min, log_max + 1)]
    for tick in tick_values:
        y = y_of(tick)
        lines.append(f'<line x1="{left}" y1="{y:.2f}" x2="{right}" y2="{y:.2f}" stroke="#ece5d8" stroke-width="1"/>')
        label = f"{tick:.3f}" if tick < 1 else f"{tick:.0f}"
        lines.append(
            f'<text x="{left - 12}" y="{y + 5:.2f}" text-anchor="end" font-family="{font}" font-size="12" fill="#64748b">{label}</text>'
        )

    for step_count in step_values:
        x = x_of(float(step_count))
        lines.append(f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" y2="{bottom}" stroke="#f3eee4" stroke-width="1"/>')
        lines.append(
            f'<text x="{x:.2f}" y="{bottom + 24}" text-anchor="middle" font-family="{font}" font-size="11" fill="#64748b">{step_count}</text>'
        )

    lines.append(
        f'<text x="{left - 78}" y="{top + chart_height / 2:.2f}" transform="rotate(-90 {left - 78} {top + chart_height / 2:.2f})" font-family="{font}" font-size="13" fill="#475569">Runtime (seconds, log scale)</text>'
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
                f"{x_of(float(row['euler_steps'])):.2f},{y_of(float(row['runtime_seconds'])):.2f}"
            )
        lines.append(
            f'<polyline fill="none" stroke="{color}" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round" points="{" ".join(polyline)}"/>'
        )
        for row in method_rows:
            x = x_of(float(row["euler_steps"]))
            y = y_of(float(row["runtime_seconds"]))
            lines.append(
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5.8" fill="{color}" stroke="#fffdf9" stroke-width="2"/>'
            )

    lines.append("</svg>")
    output_path.write_text("\n".join(lines), encoding="utf-8")


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def build_interpretation(scenario_rows: list[dict[str, float | str]]) -> list[str]:
    benchmark_rows = {
        int(row["euler_steps"]): row for row in scenario_rows if row["method"] == "benchmark"
    }
    hybrid_rows = {
        int(row["euler_steps"]): row for row in scenario_rows if row["method"] == "hybrid"
    }
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
        lines.append(
            f"- Hybrid direct error is lower at steps `{', '.join(str(step) for step in hybrid_better)}`."
        )
    if benchmark_better:
        lines.append(
            f"- LSMC direct error is lower at steps `{', '.join(str(step) for step in benchmark_better)}`."
        )
    if not lines:
        lines.append("- The direct relative errors are tied at the recorded precision across the tested steps.")
    lines.append(
        f"- Total runtime across the five-step sweep is `{benchmark_runtime_total:.2f} s` for LSMC versus `{hybrid_runtime_total:.2f} s` for Hybrid."
    )
    return lines


def build_summary(
    rows: list[dict[str, float | str]],
    reference_map: dict[str, dict[str, float]],
) -> str:
    lines = [
        "# BGK 12-date OTM K=80 / K=70 step sweep using 1200-step benchmark references",
        "",
        "This note compares LSMC and the tuned Hybrid LSMC-PDE for the OTM strikes `K=80` and `K=70` while Euler steps vary.",
        "Direct relative errors are measured against the fixed benchmark references from `bgk_r00_t1_nex12_benchmark_steps1200_paths1200000_k80_k70_table.csv`.",
        "",
        "## Fixed reference table",
        "",
    ]

    reference_rows = []
    for scenario in SCENARIOS:
        reference = reference_map[scenario["label"]]
        reference_rows.append(
            [
                f"`{scenario['label']}`",
                f"`{float(scenario['GDMR_STRIKE']):.0f}`",
                f"`{reference['benchmark_direct_price']:.6f}`",
                f"`{reference['benchmark_direct_error']:.6f}`",
                f"`[{reference['benchmark_direct_ci_lower']:.6f}, {reference['benchmark_direct_ci_upper']:.6f}]`",
                f"`{reference['runtime_seconds']:.2f} s`",
            ]
        )
    lines.append(
        markdown_table(
            ["Scenario", "K", "Reference direct", "Reference SE", "Reference 95% CI", "Reference runtime"],
            reference_rows,
        )
    )
    lines.extend(
        [
            "",
            "## Fixed model block",
            "",
            "```text",
        ]
    )
    lines.extend(f"{key}={value}" for key, value in BGK_MODEL_ENV.items())
    lines.extend(
        [
            "```",
            "",
            "## Sweep settings",
            "",
            f"- Euler steps tested: `{', '.join(str(step) for step in STEP_COUNTS)}`",
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

    for scenario in SCENARIOS:
        scenario_rows = [row for row in rows if row["scenario"] == scenario["label"]]
        lines.extend(
            [
                f"## {scenario['label']}",
                "",
                f"- Fixed direct reference: `{reference_map[scenario['label']]['benchmark_direct_price']:.6f}`",
                f"- Fixed direct reference SE: `{reference_map[scenario['label']]['benchmark_direct_error']:.6f}`",
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
                    f"`[{float(row['direct_ci_lower']):.6f}, {float(row['direct_ci_upper']):.6f}]`",
                    f"`{format_pct(float(row['rel_error_direct']))}`",
                    f"`[{format_pct(float(row['rel_ci_lower_direct']))}, {format_pct(float(row['rel_ci_upper_direct']))}]`",
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
                    "Direct 95% CI",
                    "Direct rel. error",
                    "Rel. error CI",
                    "Runtime",
                ],
                table_rows,
            )
        )
        lines.extend(
            [
                "",
                f"![{scenario['label']} direct relative error]({direct_figure_path(scenario['slug'])})",
                "",
                f"![{scenario['label']} runtime]({runtime_figure_path(scenario['slug'])})",
                "",
                "Short interpretation:",
                *build_interpretation(scenario_rows),
                "",
            ]
        )

    lines.append(f"Saved CSV: `{TABLE_PATH.name}`")
    return "\n".join(lines)


def main() -> None:
    reference_map = load_reference_map()
    rows: list[dict[str, float | str]] = []
    success = False
    try:
        for scenario in SCENARIOS:
            reference = reference_map[scenario["label"]]
            for step_count in STEP_COUNTS:
                benchmark, benchmark_runtime = run_benchmark(build_env(step_count, scenario, "benchmark"))
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

                hybrid, hybrid_runtime = run_hybrid(build_env(step_count, scenario, "hybrid"))
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

        write_csv(rows)
        for scenario in SCENARIOS:
            scenario_rows = [row for row in rows if row["scenario"] == scenario["label"]]
            render_direct_error_figure(
                direct_figure_path(scenario["slug"]),
                scenario,
                scenario_rows,
                reference_map[scenario["label"]],
            )
            render_runtime_figure(runtime_figure_path(scenario["slug"]), scenario, scenario_rows)
        SUMMARY_PATH.write_text(build_summary(rows, reference_map), encoding="utf-8")
        success = True
    finally:
        if success and SCRATCH_DIR.exists():
            shutil.rmtree(SCRATCH_DIR)

    print("K=80 / K=70 direct step sweep completed.")
    print(f"Summary: {SUMMARY_PATH.name}")
    print(f"Table:   {TABLE_PATH.name}")


if __name__ == "__main__":
    main()
