#!/usr/bin/env python3
"""
ATM-first BGK path sweep for the self-contained final gDMR package.

This experiment reuses the shipped benchmark and hybrid scripts without
modifying them. It runs one scenario at a time, uses the BGK parameter block
for the varying-path experiments, and takes the fixed benchmark reference from
the retained markdown note in Experiments/References.
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import re
import time
import uuid
from pathlib import Path
from typing import Any

import numpy as np


THIS_DIR = Path(__file__).resolve().parent
FINAL_CODE_DIR = THIS_DIR.parent
BENCHMARK_SCRIPT = FINAL_CODE_DIR / "LSMC Benchmark" / "run_gdmr_benchmark_put.py"
HYBRID_SCRIPT = FINAL_CODE_DIR / "Hybrid LSMC-PDE with FFT" / "run_gdmr_hybrid_put.py"
RESULTS_DIR = FINAL_CODE_DIR / "Results"
BGK_REFERENCE_NOTE = THIS_DIR / "References" / "bgk_gdmr_comparison.md"

DEFAULT_PATH_COUNTS = [50, 250, 500, 1000, 5000, 10000, 20000, 50000, 80000, 100000]
CI_Z = 1.96

SCENARIOS = {
    "atm": {"slug": "atm", "label": "ATM put", "reference_row": "ATM", "strike": 100.0},
    "itm": {"slug": "itm", "label": "ITM put", "reference_row": "ITM put", "strike": 110.0},
    "otm": {"slug": "otm", "label": "OTM put", "reference_row": "OTM put", "strike": 90.0},
}

BGK_MODEL_DEFAULTS = {
    "S0": 100.0,
    "v0": 0.114,
    "vp0": 0.110,
    "r": 0.0,
    "kappa1": 5.5,
    "kappa2": 0.1,
    "theta": 0.078,
    "xi1": 2.689,
    "xi2": 0.502,
    "delta1": 0.94,
    "delta2": 0.94,
    "rho12": -0.982,
    "rho13": -0.727,
    "rho23": 0.59,
    "option_type": "put",
    "T": 1.0,
}

BENCHMARK_EXPERIMENT_DEFAULTS = {
    "N_ex": 100,
    "M": 100,
    "seed": 2026,
    "low_seed": 2103,
    "basis_degree": 3,
    "basis_size": 16,
    "ridge_lambda": 1e-10,
    "store_dir": None,
}

HYBRID_EXPERIMENT_DEFAULTS = {
    "N_ex": 100,
    "M": 100,
    "N_S": 181,
    "asset_low_factor": 0.35,
    "asset_high_factor": 3.00,
    "vol_truncation_quantile": 0.997,
    "fst_pad_factor": 4,
    "fst_batch_size": 256,
    "seed": 2026,
    "low_seed": 2103,
    "vol_basis_degree": 3,
    "ridge_lambda": 1e-10,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one BGK path-sweep scenario using the Final Code scripts."
    )
    parser.add_argument(
        "--scenario",
        choices=sorted(SCENARIOS),
        default="atm",
        help="Scenario slug to run. Defaults to atm.",
    )
    parser.add_argument(
        "--paths",
        type=int,
        nargs="*",
        default=DEFAULT_PATH_COUNTS,
        help="Path counts to sweep. Defaults to the curated 10-value ATM-first list.",
    )
    parser.add_argument(
        "--output-stem",
        default=None,
        help="Optional output stem. Defaults to gdmr_path_sweep_<scenario>.",
    )
    parser.add_argument(
        "--from-summary",
        default=None,
        help="Rebuild figures from an existing summary markdown file instead of rerunning the sweep.",
    )
    return parser.parse_args()


def load_module(script_path: Path, prefix: str) -> Any:
    module_name = f"{prefix}_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def strip_markdown_code(value: str) -> str:
    return value.replace("`", "").strip()


def parse_md_float(value: str) -> float:
    cleaned = strip_markdown_code(value).replace(",", "").replace("%", "")
    return float(cleaned)


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


def format_price(value: float) -> str:
    return f"{value:.6f}"


def format_paths(value: int) -> str:
    return f"{value:,}"


def format_pct(value: float) -> str:
    return f"{100.0 * value:.3f}%"


def format_seconds(value: float) -> str:
    return f"{value:.2f} s"


def format_hms(value: float) -> str:
    total_seconds = int(round(value))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:d}:{minutes:02d}:{seconds:02d}"


def set_module_values(module: Any, mapping: dict[str, Any]) -> None:
    for name, value in mapping.items():
        setattr(module, name, value)


def parse_bgk_reference_row(reference_row: str) -> dict[str, float | str]:
    text = BGK_REFERENCE_NOTE.read_text(encoding="utf-8")
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if not cells or cells[0] != reference_row:
            continue
        if len(cells) < 15:
            raise RuntimeError(f"Unexpected BGK table shape for row {reference_row!r}.")
        direct_price = parse_md_float(cells[3])
        direct_se = parse_md_float(cells[4])
        low_price = parse_md_float(cells[5])
        low_se = parse_md_float(cells[6])
        parsed = {
            "scenario": cells[0],
            "spot": parse_md_float(cells[1]),
            "strike": parse_md_float(cells[2]),
            "direct_price": direct_price,
            "direct_se": direct_se,
            "low_price": low_price,
            "low_se": low_se,
            "reported_direct_low_gap_pct": parse_md_float(cells[13]) / 100.0,
        }
        computed_gap = gap_pct(low_price, direct_price)
        if abs(computed_gap - float(parsed["reported_direct_low_gap_pct"])) > 5e-6:
            raise RuntimeError(
                f"Parsed BGK row {reference_row!r} is inconsistent with its direct-low gap."
            )
        return parsed
    raise RuntimeError(f"Could not find BGK reference row {reference_row!r} in {BGK_REFERENCE_NOTE}.")


def configure_benchmark(module: Any, strike: float, paths: int) -> None:
    config: dict[str, Any] = {}
    config.update(BGK_MODEL_DEFAULTS)
    config.update(BENCHMARK_EXPERIMENT_DEFAULTS)
    config.update({"K": strike, "N": paths, "N_low": paths})
    set_module_values(module, config)

    module.exercise_indices = np.rint(np.linspace(0.0, module.M, module.N_ex + 1)).astype(np.int32)
    module.exercise_indices[0] = 0
    module.exercise_indices[-1] = module.M
    module.interval_steps = np.diff(module.exercise_indices)
    module.exercise_times = module.T * module.exercise_indices / float(module.M)
    module.internal_steps = module.M / float(module.N_ex)
    module.corr = np.array(
        [
            [1.0, module.rho12, module.rho13],
            [module.rho12, 1.0, module.rho23],
            [module.rho13, module.rho23, 1.0],
        ],
        dtype=np.float64,
    )
    module.chol = np.linalg.cholesky(module.corr).astype(np.float32)


def configure_hybrid(module: Any, strike: float, paths: int) -> None:
    config: dict[str, Any] = {}
    config.update(BGK_MODEL_DEFAULTS)
    config.update(HYBRID_EXPERIMENT_DEFAULTS)
    config.update({"K": strike, "N": paths, "N_low": paths})
    set_module_values(module, config)

    module.exercise_indices = np.rint(np.linspace(0.0, module.M, module.N_ex + 1)).astype(np.int32)
    module.exercise_indices[0] = 0
    module.exercise_indices[-1] = module.M
    module.interval_steps = np.diff(module.exercise_indices)
    module.exercise_times = module.T * module.exercise_indices / float(module.M)
    module.internal_steps = module.M / float(module.N_ex)
    module.corr23 = np.array(
        [
            [1.0, module.rho23],
            [module.rho23, 1.0],
        ],
        dtype=np.float64,
    )
    module.chol23 = np.linalg.cholesky(module.corr23).astype(np.float32)


def run_benchmark(strike: float, paths: int) -> dict[str, float | int]:
    module = load_module(BENCHMARK_SCRIPT, "gdmr_benchmark")
    configure_benchmark(module, strike, paths)
    started = time.perf_counter()
    direct_price, direct_se, coeff_steps = module.lsmc_direct_and_coefficients()
    low_price, low_se = module.lsmc_low_estimator(coeff_steps)
    elapsed = time.perf_counter() - started
    return {
        "paths": paths,
        "direct_price": float(direct_price),
        "direct_se": float(direct_se),
        "low_price": float(low_price),
        "low_se": float(low_se),
        "runtime_seconds": elapsed,
    }


def run_hybrid(strike: float, paths: int) -> dict[str, float | int]:
    module = load_module(HYBRID_SCRIPT, "gdmr_hybrid")
    configure_hybrid(module, strike, paths)
    started = time.perf_counter()
    results = module.hybrid_prices()
    elapsed = time.perf_counter() - started
    return {
        "paths": paths,
        "direct_price": float(results["hybrid_direct_price"]),
        "direct_se": float(results["hybrid_direct_error"]),
        "low_price": float(results["hybrid_low_price"]),
        "low_se": float(results["hybrid_low_error"]),
        "runtime_seconds": elapsed,
        "asset_grid_points": int(results["asset_grid_points"]),
        "asset_low_factor": float(results["asset_low_factor"]),
        "asset_high_factor": float(results["asset_high_factor"]),
        "vol_quantile": float(results["vol_quantile"]),
        "fst_pad_factor": int(results["fst_pad_factor"]),
        "fst_batch_size": int(results["fst_batch_size"]),
    }


def summarize_estimator(price: float, se: float, reference_price: float) -> dict[str, float]:
    ci_lower, ci_upper = ci_bounds(price, se)
    return {
        "price": price,
        "se": se,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "rel_error": rel_error(price, reference_price),
    }


def build_method_summary(
    method_name: str,
    raw_result: dict[str, float | int],
    reference_direct: float,
    reference_low: float,
) -> dict[str, Any]:
    direct = summarize_estimator(
        float(raw_result["direct_price"]),
        float(raw_result["direct_se"]),
        reference_direct,
    )
    low = summarize_estimator(
        float(raw_result["low_price"]),
        float(raw_result["low_se"]),
        reference_low,
    )
    return {
        "method": method_name,
        "paths": int(raw_result["paths"]),
        "runtime_seconds": float(raw_result["runtime_seconds"]),
        "direct": direct,
        "low": low,
        "direct_low_gap": gap_pct(low["price"], direct["price"]),
    }


def scenario_reference_summary(reference_row: dict[str, float | str]) -> dict[str, Any]:
    direct = summarize_estimator(
        float(reference_row["direct_price"]),
        float(reference_row["direct_se"]),
        float(reference_row["direct_price"]),
    )
    low = summarize_estimator(
        float(reference_row["low_price"]),
        float(reference_row["low_se"]),
        float(reference_row["low_price"]),
    )
    return {
        "scenario": reference_row["scenario"],
        "spot": float(reference_row["spot"]),
        "strike": float(reference_row["strike"]),
        "direct": direct,
        "low": low,
        "direct_low_gap": gap_pct(low["price"], direct["price"]),
    }


def run_scenario(scenario_key: str, path_counts: list[int]) -> dict[str, Any]:
    scenario = SCENARIOS[scenario_key]
    strike = float(scenario["strike"])
    reference_row = parse_bgk_reference_row(str(scenario["reference_row"]))
    reference = scenario_reference_summary(reference_row)

    scenario_started = time.perf_counter()
    sweep_rows: list[dict[str, Any]] = []
    hybrid_settings: dict[str, Any] | None = None

    print(
        f"Running {scenario['label']} BGK path sweep with Euler {BENCHMARK_EXPERIMENT_DEFAULTS['M']} "
        f"for paths {', '.join(format_paths(value) for value in path_counts)}"
    )
    print(
        "Using fixed reference from bgk_gdmr_comparison.md: "
        f"direct={reference['direct']['price']:.6f}, low={reference['low']['price']:.6f}"
    )

    for paths in path_counts:
        print(f"  {scenario['label']}: {format_paths(paths)} paths")
        benchmark_raw = run_benchmark(strike, paths)
        hybrid_raw = run_hybrid(strike, paths)

        if hybrid_settings is None:
            hybrid_settings = {
                "asset_grid_points": hybrid_raw["asset_grid_points"],
                "asset_low_factor": hybrid_raw["asset_low_factor"],
                "asset_high_factor": hybrid_raw["asset_high_factor"],
                "vol_quantile": hybrid_raw["vol_quantile"],
                "fst_pad_factor": hybrid_raw["fst_pad_factor"],
                "fst_batch_size": hybrid_raw["fst_batch_size"],
            }

        sweep_rows.append(
            {
                "paths": paths,
                "benchmark": build_method_summary(
                    "LSMC benchmark",
                    benchmark_raw,
                    reference["direct"]["price"],
                    reference["low"]["price"],
                ),
                "hybrid": build_method_summary(
                    "Hybrid LSMC-PDE with FFT",
                    hybrid_raw,
                    reference["direct"]["price"],
                    reference["low"]["price"],
                ),
            }
        )

    total_elapsed = time.perf_counter() - scenario_started
    if hybrid_settings is None:
        raise RuntimeError("Hybrid settings were not recorded.")

    return {
        "slug": scenario["slug"],
        "label": scenario["label"],
        "strike": strike,
        "reference": reference,
        "hybrid_settings": hybrid_settings,
        "sweep": sweep_rows,
        "total_runtime_seconds": total_elapsed,
    }


def markdown_table(headers: list[str], rows: list[tuple[str, ...]]) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return lines


def parse_markdown_table(text: str, section_heading: str) -> tuple[list[str], list[list[str]]]:
    heading = f"## {section_heading}"
    start = text.find(heading)
    if start < 0:
        raise RuntimeError(f"Could not find section heading {section_heading!r}.")
    section_text = text[start + len(heading):]
    table_lines: list[str] = []
    collecting = False
    for raw_line in section_text.splitlines():
        line = raw_line.strip()
        if not line:
            if collecting:
                break
            continue
        if line.startswith("|"):
            collecting = True
            table_lines.append(line)
            continue
        if collecting:
            break
    if len(table_lines) < 3:
        raise RuntimeError(f"Could not parse markdown table under section {section_heading!r}.")
    headers = [cell.strip() for cell in table_lines[0].strip("|").split("|")]
    rows = [
        [cell.strip() for cell in line.strip("|").split("|")]
        for line in table_lines[2:]
    ]
    return headers, rows


def parse_existing_summary(summary_path: Path) -> dict[str, Any]:
    text = summary_path.read_text(encoding="utf-8")
    title_match = re.search(r"^#\s+(.+?)\s+BGK Path Sweep\s*$", text, re.MULTILINE)
    if title_match is None:
        raise RuntimeError(f"Could not parse scenario label from {summary_path}.")
    label = title_match.group(1).strip()

    scenario_match = re.search(
        r"Scenario:\s+`(.+?)`\s+with\s+`S0 = ([0-9.]+)`\s+and\s+`K = ([0-9.]+)`",
        text,
    )
    if scenario_match is None:
        raise RuntimeError(f"Could not parse scenario setup from {summary_path}.")
    strike = float(scenario_match.group(3))

    _, reference_rows = parse_markdown_table(text, "Fixed benchmark reference")
    reference_lookup = {row[0]: row for row in reference_rows}
    direct_ref = reference_lookup["Direct"]
    low_ref = reference_lookup["Low"]
    reference = {
        "direct": {
            "price": parse_md_float(direct_ref[1]),
            "se": parse_md_float(direct_ref[2]),
            "ci_lower": parse_md_float(direct_ref[3]),
            "ci_upper": parse_md_float(direct_ref[4]),
            "rel_error": 0.0,
        },
        "low": {
            "price": parse_md_float(low_ref[1]),
            "se": parse_md_float(low_ref[2]),
            "ci_lower": parse_md_float(low_ref[3]),
            "ci_upper": parse_md_float(low_ref[4]),
            "rel_error": 0.0,
        },
        "direct_low_gap": parse_md_float(direct_ref[5]) / 100.0,
    }

    _, direct_rows = parse_markdown_table(text, "Direct sweep vs fixed benchmark direct reference")
    _, low_rows = parse_markdown_table(text, "Low sweep vs fixed benchmark low reference")

    points_by_path: dict[int, dict[str, Any]] = {}
    method_key_lookup = {
        "LSMC benchmark": "benchmark",
        "Hybrid LSMC-PDE with FFT": "hybrid",
    }

    for row in direct_rows:
        paths = int(parse_md_float(row[0]))
        method_key = method_key_lookup[row[1]]
        entry = points_by_path.setdefault(paths, {"paths": paths})
        method_entry = entry.setdefault(
            method_key,
            {
                "method": row[1],
                "paths": paths,
                "runtime_seconds": 0.0,
                "direct": {},
                "low": {},
                "direct_low_gap": 0.0,
            },
        )
        method_entry["runtime_seconds"] = parse_md_float(row[2].replace(" s", ""))
        method_entry["direct"] = {
            "price": parse_md_float(row[3]),
            "se": parse_md_float(row[4]),
            "ci_lower": parse_md_float(row[5]),
            "ci_upper": parse_md_float(row[6]),
            "rel_error": parse_md_float(row[7]) / 100.0,
        }
        method_entry["direct_low_gap"] = parse_md_float(row[8]) / 100.0

    for row in low_rows:
        paths = int(parse_md_float(row[0]))
        method_key = method_key_lookup[row[1]]
        entry = points_by_path.setdefault(paths, {"paths": paths})
        method_entry = entry.setdefault(
            method_key,
            {
                "method": row[1],
                "paths": paths,
                "runtime_seconds": 0.0,
                "direct": {},
                "low": {},
                "direct_low_gap": 0.0,
            },
        )
        method_entry["runtime_seconds"] = parse_md_float(row[2].replace(" s", ""))
        method_entry["low"] = {
            "price": parse_md_float(row[3]),
            "se": parse_md_float(row[4]),
            "ci_lower": parse_md_float(row[5]),
            "ci_upper": parse_md_float(row[6]),
            "rel_error": parse_md_float(row[7]) / 100.0,
        }
        method_entry["direct_low_gap"] = parse_md_float(row[8]) / 100.0

    scenario_result = {
        "slug": summary_path.stem.removeprefix("gdmr_path_sweep_").removesuffix("_summary"),
        "label": label,
        "strike": strike,
        "reference": reference,
        "sweep": [],
    }

    for paths in sorted(points_by_path):
        point = points_by_path[paths]
        for method_key in ("benchmark", "hybrid"):
            method_entry = point[method_key]
            for estimator_key, reference_key in (("direct", "direct"), ("low", "low")):
                estimator = method_entry[estimator_key]
                rel_low, rel_high = rel_error_ci_bounds(
                    estimator["price"],
                    estimator["se"],
                    scenario_result["reference"][reference_key]["price"],
                )
                estimator["rel_ci_lower"] = rel_low
                estimator["rel_ci_upper"] = rel_high
        scenario_result["sweep"].append(point)

    return scenario_result


def direct_rows_for_markdown(scenario_result: dict[str, Any]) -> list[tuple[str, ...]]:
    rows: list[tuple[str, ...]] = []
    for point in scenario_result["sweep"]:
        for method_key in ("benchmark", "hybrid"):
            method = point[method_key]
            direct = method["direct"]
            rows.append(
                (
                    format_paths(point["paths"]),
                    method["method"],
                    format_seconds(method["runtime_seconds"]),
                    format_price(direct["price"]),
                    format_price(direct["se"]),
                    format_price(direct["ci_lower"]),
                    format_price(direct["ci_upper"]),
                    format_pct(direct["rel_error"]),
                    format_pct(method["direct_low_gap"]),
                )
            )
    return rows


def low_rows_for_markdown(scenario_result: dict[str, Any]) -> list[tuple[str, ...]]:
    rows: list[tuple[str, ...]] = []
    for point in scenario_result["sweep"]:
        for method_key in ("benchmark", "hybrid"):
            method = point[method_key]
            low = method["low"]
            rows.append(
                (
                    format_paths(point["paths"]),
                    method["method"],
                    format_seconds(method["runtime_seconds"]),
                    format_price(low["price"]),
                    format_price(low["se"]),
                    format_price(low["ci_lower"]),
                    format_price(low["ci_upper"]),
                    format_pct(low["rel_error"]),
                    format_pct(method["direct_low_gap"]),
                )
            )
    return rows


def slowest_runs(scenario_result: dict[str, Any], count: int = 3) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    for point in scenario_result["sweep"]:
        for method_key in ("benchmark", "hybrid"):
            method = point[method_key]
            runs.append(
                {
                    "paths": point["paths"],
                    "method": method["method"],
                    "runtime_seconds": method["runtime_seconds"],
                }
            )
    return sorted(runs, key=lambda item: item["runtime_seconds"], reverse=True)[:count]


def write_markdown_report(output_path: Path, scenario_result: dict[str, Any]) -> None:
    reference = scenario_result["reference"]
    hybrid_settings = scenario_result["hybrid_settings"]
    lines: list[str] = []
    lines.append(f"# {scenario_result['label']} BGK Path Sweep")
    lines.append("")
    lines.append(
        "This experiment reuses only the shipped `Final Code` benchmark and hybrid scripts."
    )
    lines.append("")
    lines.append("## Setup")
    lines.append("")
    lines.append(
        f"- Scenario: `{scenario_result['label']}` with `S0 = {BGK_MODEL_DEFAULTS['S0']:.0f}` and `K = {scenario_result['strike']:.0f}`."
    )
    lines.append(
        f"- BGK experiment block: `r = {BGK_MODEL_DEFAULTS['r']:.1f}`, `T = {BGK_MODEL_DEFAULTS['T']:.1f}`, "
        f"`theta = {BGK_MODEL_DEFAULTS['theta']:.3f}`, `kappa1 = {BGK_MODEL_DEFAULTS['kappa1']:.1f}`, "
        f"`kappa2 = {BGK_MODEL_DEFAULTS['kappa2']:.1f}`, `v0 = {BGK_MODEL_DEFAULTS['v0']:.3f}`, "
        f"`vp0 = {BGK_MODEL_DEFAULTS['vp0']:.3f}`."
    )
    lines.append(
        f"- BGK volatility/correlation block: `delta1 = {BGK_MODEL_DEFAULTS['delta1']:.2f}`, "
        f"`delta2 = {BGK_MODEL_DEFAULTS['delta2']:.2f}`, `xi1 = {BGK_MODEL_DEFAULTS['xi1']:.3f}`, "
        f"`xi2 = {BGK_MODEL_DEFAULTS['xi2']:.3f}`, `rho12 = {BGK_MODEL_DEFAULTS['rho12']:.3f}`, "
        f"`rho13 = {BGK_MODEL_DEFAULTS['rho13']:.3f}`, `rho23 = {BGK_MODEL_DEFAULTS['rho23']:.2f}`."
    )
    lines.append(
        f"- Experimental Bermudan exercise dates: `{BENCHMARK_EXPERIMENT_DEFAULTS['N_ex']}`."
    )
    lines.append(
        f"- Experimental Euler steps for both varying-path curves: `{BENCHMARK_EXPERIMENT_DEFAULTS['M']}`."
    )
    lines.append(
        "- Fixed benchmark references were parsed from "
        f"`{BGK_REFERENCE_NOTE.name}` instead of rerunning the 1,000,000-path benchmark."
    )
    lines.append(
        "- Path sweep: `"
        + ", ".join(format_paths(point["paths"]) for point in scenario_result["sweep"])
        + "`."
    )
    lines.append(
        f"- Benchmark seeds for the varying-path curve: `{BENCHMARK_EXPERIMENT_DEFAULTS['seed']}` and `{BENCHMARK_EXPERIMENT_DEFAULTS['low_seed']}`."
    )
    lines.append(
        f"- Hybrid seeds for the varying-path curve: `{HYBRID_EXPERIMENT_DEFAULTS['seed']}` and `{HYBRID_EXPERIMENT_DEFAULTS['low_seed']}`."
    )
    lines.append("")
    lines.append("## Fixed benchmark reference")
    lines.append("")
    lines.extend(
        markdown_table(
            ["Estimator", "Price", "SE", "95% CI lower", "95% CI upper", "Direct-low gap"],
            [
                (
                    "Direct",
                    format_price(reference["direct"]["price"]),
                    format_price(reference["direct"]["se"]),
                    format_price(reference["direct"]["ci_lower"]),
                    format_price(reference["direct"]["ci_upper"]),
                    format_pct(reference["direct_low_gap"]),
                ),
                (
                    "Low",
                    format_price(reference["low"]["price"]),
                    format_price(reference["low"]["se"]),
                    format_price(reference["low"]["ci_lower"]),
                    format_price(reference["low"]["ci_upper"]),
                    format_pct(reference["direct_low_gap"]),
                ),
            ],
        )
    )
    lines.append("")
    lines.append("## Hybrid settings kept fixed")
    lines.append("")
    lines.append(f"- Asset grid points: `{hybrid_settings['asset_grid_points']}`.")
    lines.append(
        f"- Asset range factors: `{hybrid_settings['asset_low_factor']:.2f}` to `{hybrid_settings['asset_high_factor']:.2f}`."
    )
    lines.append(f"- Volatility truncation quantile: `{hybrid_settings['vol_quantile']:.3f}`.")
    lines.append(f"- FST pad factor: `{hybrid_settings['fst_pad_factor']}`.")
    lines.append(f"- FST batch size: `{hybrid_settings['fst_batch_size']}`.")
    lines.append("")
    lines.append("## Direct sweep vs fixed benchmark direct reference")
    lines.append("")
    lines.extend(
        markdown_table(
            ["Paths", "Method", "Runtime", "Price", "SE", "95% CI lower", "95% CI upper", "Relative error", "Direct-low gap"],
            direct_rows_for_markdown(scenario_result),
        )
    )
    lines.append("")
    lines.append("## Low sweep vs fixed benchmark low reference")
    lines.append("")
    lines.extend(
        markdown_table(
            ["Paths", "Method", "Runtime", "Price", "SE", "95% CI lower", "95% CI upper", "Relative error", "Direct-low gap"],
            low_rows_for_markdown(scenario_result),
        )
    )
    lines.append("")
    lines.append("## Timing summary")
    lines.append("")
    lines.append(f"- Total scenario runtime: `{format_hms(scenario_result['total_runtime_seconds'])}`.")
    for rank, run in enumerate(slowest_runs(scenario_result), start=1):
        lines.append(
            f"- Slowest run {rank}: `{run['method']}` at `{format_paths(run['paths'])}` paths took `{format_seconds(run['runtime_seconds'])}`."
        )
    lines.append("")
    lines.append("## Generated figures")
    lines.append("")
    stem = output_path.stem.removesuffix("_summary")
    lines.append(f"- `{stem}_direct_relative_error.svg`")
    lines.append(f"- `{stem}_direct_relative_error_with_ci.svg`")
    lines.append(f"- `{stem}_low_relative_error.svg`")
    lines.append(f"- `{stem}_low_relative_error_with_ci.svg`")
    lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")


def build_series_points(scenario_result: dict[str, Any], method_key: str, estimator_key: str) -> list[dict[str, float]]:
    points: list[dict[str, float]] = []
    for point in scenario_result["sweep"]:
        estimator = point[method_key][estimator_key]
        points.append(
            {
                "paths": float(point["paths"]),
                "rel_error": float(estimator["rel_error"]),
            }
        )
    return points


def render_relative_error_figure(
    output_path: Path,
    scenario_result: dict[str, Any],
    estimator_key: str,
    include_ci: bool,
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

    reference_label = "benchmark direct" if estimator_key == "direct" else "benchmark low"
    title = "Direct relative error" if estimator_key == "direct" else "Low relative error"
    y_max = max(
        0.005,
        max(
            point[method_key][estimator_key]["rel_ci_upper"]
            if include_ci
            else point[method_key][estimator_key]["rel_error"]
            for point in scenario_result["sweep"]
            for method_key in ("benchmark", "hybrid")
        )
        * 1.15,
    )

    path_values = [float(point["paths"]) for point in scenario_result["sweep"]]
    log_min = math.log10(min(path_values))
    log_max = math.log10(max(path_values))
    tick_values = path_values

    def x_of(paths: float) -> float:
        return left + (math.log10(paths) - log_min) / (log_max - log_min) * chart_width

    def y_of(value: float) -> float:
        return bottom - value / y_max * chart_height

    benchmark_points = build_series_points(scenario_result, "benchmark", estimator_key)
    hybrid_points = build_series_points(scenario_result, "hybrid", estimator_key)

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f3efe7"/>',
        '<rect x="30" y="28" width="1200" height="744" rx="28" fill="#fffdf9" stroke="#ddd4c6"/>',
        f'<text x="72" y="88" font-family="{font}" font-size="31" font-weight="700" fill="#17202a">{scenario_result["label"]}: {title}</text>',
        f'<text x="72" y="118" font-family="{font}" font-size="15" fill="#475569">Reference taken from bgk_gdmr_comparison.md; varying-path experiment curves use Euler 100 in the unchanged Final Code scripts.</text>',
        f'<text x="72" y="146" font-family="{font}" font-size="14" fill="#64748b">BGK setup with S0 = {BGK_MODEL_DEFAULTS["S0"]:.0f}, K = {scenario_result["strike"]:.0f}, exercise dates = {BENCHMARK_EXPERIMENT_DEFAULTS["N_ex"]}, path axis shown on log scale.</text>',
        f'<text x="72" y="174" font-family="{font}" font-size="14" fill="#64748b">Relative errors are measured against the fixed {scenario_result["label"]} {reference_label} reference value from the BGK note.' + (" Pointwise 95% CI bars shown." if include_ci else " Point estimates only.") + '</text>',
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

    for tick in tick_values:
        x = x_of(float(tick))
        lines.append(f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" y2="{bottom}" stroke="#f3eee4" stroke-width="1"/>')
        lines.append(
            f'<text x="{x:.2f}" y="{bottom + 24}" text-anchor="end" transform="rotate(-35 {x:.2f} {bottom + 24})" font-family="{font}" font-size="11" fill="#64748b">{format_paths(int(tick))}</text>'
        )

    lines.append(
        f'<text x="{left - 78}" y="{top + chart_height / 2:.2f}" transform="rotate(-90 {left - 78} {top + chart_height / 2:.2f})" font-family="{font}" font-size="13" fill="#475569">Relative error</text>'
    )
    lines.append(
        f'<text x="{(left + right) / 2:.2f}" y="{bottom + 52}" text-anchor="middle" font-family="{font}" font-size="13" fill="#475569">Number of paths (log scale)</text>'
    )

    legend = [
        ("benchmark", "#1d4ed8", "LSMC benchmark", benchmark_points),
        ("hybrid", "#d97706", "Hybrid LSMC-PDE with FFT", hybrid_points),
    ]
    for legend_index, (method_key, color, label, series) in enumerate(legend):
        x0 = 72 + 350 * legend_index
        lines.append(f'<line x1="{x0}" y1="{legend_y}" x2="{x0 + 34}" y2="{legend_y}" stroke="{color}" stroke-width="4"/>')
        lines.append(f'<circle cx="{x0 + 17}" cy="{legend_y}" r="5.5" fill="{color}" stroke="#fffdf9" stroke-width="2"/>')
        lines.append(f'<text x="{x0 + 46}" y="{legend_y + 5}" font-family="{font}" font-size="14" fill="#334155">{label}</text>')

        polyline = []
        for point in series:
            polyline.append(f"{x_of(point['paths']):.2f},{y_of(point['rel_error']):.2f}")
        lines.append(
            f'<polyline fill="none" stroke="{color}" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round" points="{" ".join(polyline)}"/>'
        )
        for point in series:
            if include_ci:
                estimator = next(
                    row[method_key][estimator_key]
                    for row in scenario_result["sweep"]
                    if float(row["paths"]) == point["paths"]
                )
                y_low = y_of(estimator["rel_ci_lower"])
                y_high = y_of(estimator["rel_ci_upper"])
                x = x_of(point["paths"])
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
                f'<circle cx="{x_of(point["paths"]):.2f}" cy="{y_of(point["rel_error"]):.2f}" r="5.8" fill="{color}" stroke="#fffdf9" stroke-width="2"/>'
            )

    lines.append("</svg>")
    output_path.write_text("\n".join(lines), encoding="utf-8")


def render_single_method_estimator_figure(
    output_path: Path,
    scenario_result: dict[str, Any],
    method_key: str,
    estimator_key: str,
    include_ci: bool,
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

    method_label = "LSMC benchmark" if method_key == "benchmark" else "Hybrid LSMC-PDE with FFT"
    color = "#1d4ed8" if method_key == "benchmark" else "#d97706"
    estimator_label = "direct" if estimator_key == "direct" else "low"
    reference_label = "benchmark direct" if estimator_key == "direct" else "benchmark low"
    title = f'{scenario_result["label"]}: {method_label} {estimator_label} relative error'
    y_max = max(
        0.005,
        max(
            point[method_key][estimator_key]["rel_ci_upper"]
            if include_ci
            else point[method_key][estimator_key]["rel_error"]
            for point in scenario_result["sweep"]
        )
        * 1.15,
    )

    path_values = [float(point["paths"]) for point in scenario_result["sweep"]]
    log_min = math.log10(min(path_values))
    log_max = math.log10(max(path_values))
    tick_values = path_values
    series = build_series_points(scenario_result, method_key, estimator_key)

    def x_of(paths: float) -> float:
        return left + (math.log10(paths) - log_min) / (log_max - log_min) * chart_width

    def y_of(value: float) -> float:
        return bottom - value / y_max * chart_height

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f3efe7"/>',
        '<rect x="30" y="28" width="1200" height="744" rx="28" fill="#fffdf9" stroke="#ddd4c6"/>',
        f'<text x="72" y="88" font-family="{font}" font-size="31" font-weight="700" fill="#17202a">{title}</text>',
        f'<text x="72" y="118" font-family="{font}" font-size="15" fill="#475569">Reference taken from bgk_gdmr_comparison.md; only the {method_label} {estimator_label} curve is shown here.</text>',
        f'<text x="72" y="146" font-family="{font}" font-size="14" fill="#64748b">BGK ATM setup with S0 = {BGK_MODEL_DEFAULTS["S0"]:.0f}, K = {scenario_result["strike"]:.0f}, exercise dates = {BENCHMARK_EXPERIMENT_DEFAULTS["N_ex"]}, Euler steps = {BENCHMARK_EXPERIMENT_DEFAULTS["M"]}.</text>',
        f'<text x="72" y="174" font-family="{font}" font-size="14" fill="#64748b">Relative errors are measured against the fixed {scenario_result["label"]} {reference_label} reference.' + (" Pointwise 95% CI bars shown." if include_ci else " Point estimates only.") + '</text>',
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

    for tick in tick_values:
        x = x_of(float(tick))
        lines.append(f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" y2="{bottom}" stroke="#f3eee4" stroke-width="1"/>')
        lines.append(
            f'<text x="{x:.2f}" y="{bottom + 24}" text-anchor="end" transform="rotate(-35 {x:.2f} {bottom + 24})" font-family="{font}" font-size="11" fill="#64748b">{format_paths(int(tick))}</text>'
        )

    lines.append(
        f'<text x="{left - 78}" y="{top + chart_height / 2:.2f}" transform="rotate(-90 {left - 78} {top + chart_height / 2:.2f})" font-family="{font}" font-size="13" fill="#475569">Relative error</text>'
    )
    lines.append(
        f'<text x="{(left + right) / 2:.2f}" y="{bottom + 52}" text-anchor="middle" font-family="{font}" font-size="13" fill="#475569">Number of paths (log scale)</text>'
    )

    lines.append(f'<line x1="72" y1="{legend_y}" x2="106" y2="{legend_y}" stroke="{color}" stroke-width="4"/>')
    lines.append(f'<circle cx="89" cy="{legend_y}" r="5.5" fill="{color}" stroke="#fffdf9" stroke-width="2"/>')
    lines.append(f'<text x="118" y="{legend_y + 5}" font-family="{font}" font-size="14" fill="#334155">{method_label}</text>')

    polyline = []
    for point in series:
        polyline.append(f"{x_of(point['paths']):.2f},{y_of(point['rel_error']):.2f}")
    lines.append(
        f'<polyline fill="none" stroke="{color}" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round" points="{" ".join(polyline)}"/>'
    )

    for point in scenario_result["sweep"]:
        estimator = point[method_key][estimator_key]
        x = x_of(float(point["paths"]))
        y = y_of(float(estimator["rel_error"]))
        if include_ci:
            y_low = y_of(float(estimator["rel_ci_lower"]))
            y_high = y_of(float(estimator["rel_ci_upper"]))
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


def build_output_paths(output_stem: str) -> dict[str, Path]:
    return {
        "markdown": RESULTS_DIR / f"{output_stem}_summary.md",
        "direct_figure": RESULTS_DIR / f"{output_stem}_direct_relative_error.svg",
        "direct_figure_ci": RESULTS_DIR / f"{output_stem}_direct_relative_error_with_ci.svg",
        "low_figure": RESULTS_DIR / f"{output_stem}_low_relative_error.svg",
        "low_figure_ci": RESULTS_DIR / f"{output_stem}_low_relative_error_with_ci.svg",
        "benchmark_direct_only": RESULTS_DIR / f"{output_stem}_benchmark_direct_relative_error.svg",
        "benchmark_direct_only_ci": RESULTS_DIR / f"{output_stem}_benchmark_direct_relative_error_with_ci.svg",
        "benchmark_low_only_ci": RESULTS_DIR / f"{output_stem}_benchmark_low_relative_error_with_ci.svg",
        "hybrid_direct_only": RESULTS_DIR / f"{output_stem}_hybrid_direct_relative_error.svg",
        "hybrid_direct_only_ci": RESULTS_DIR / f"{output_stem}_hybrid_direct_relative_error_with_ci.svg",
        "hybrid_low_only_ci": RESULTS_DIR / f"{output_stem}_hybrid_low_relative_error_with_ci.svg",
    }


def main() -> None:
    args = parse_args()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    path_counts = sorted(set(args.paths))
    output_stem = args.output_stem or f"gdmr_path_sweep_{args.scenario}"
    output_paths = build_output_paths(output_stem)

    if args.from_summary is not None:
        summary_path = Path(args.from_summary)
        scenario_result = parse_existing_summary(summary_path)
    else:
        scenario_result = run_scenario(args.scenario, path_counts)
        for point in scenario_result["sweep"]:
            for method_key in ("benchmark", "hybrid"):
                for estimator_key, reference_key in (("direct", "direct"), ("low", "low")):
                    estimator = point[method_key][estimator_key]
                    rel_low, rel_high = rel_error_ci_bounds(
                        estimator["price"],
                        estimator["se"],
                        scenario_result["reference"][reference_key]["price"],
                    )
                    estimator["rel_ci_lower"] = rel_low
                    estimator["rel_ci_upper"] = rel_high
        write_markdown_report(output_paths["markdown"], scenario_result)

    render_relative_error_figure(output_paths["direct_figure"], scenario_result, "direct", include_ci=False)
    render_relative_error_figure(output_paths["direct_figure_ci"], scenario_result, "direct", include_ci=True)
    render_relative_error_figure(output_paths["low_figure"], scenario_result, "low", include_ci=False)
    render_relative_error_figure(output_paths["low_figure_ci"], scenario_result, "low", include_ci=True)
    render_single_method_estimator_figure(output_paths["benchmark_direct_only"], scenario_result, "benchmark", "direct", include_ci=False)
    render_single_method_estimator_figure(output_paths["benchmark_direct_only_ci"], scenario_result, "benchmark", "direct", include_ci=True)
    render_single_method_estimator_figure(output_paths["benchmark_low_only_ci"], scenario_result, "benchmark", "low", include_ci=True)
    render_single_method_estimator_figure(output_paths["hybrid_direct_only"], scenario_result, "hybrid", "direct", include_ci=False)
    render_single_method_estimator_figure(output_paths["hybrid_direct_only_ci"], scenario_result, "hybrid", "direct", include_ci=True)
    render_single_method_estimator_figure(output_paths["hybrid_low_only_ci"], scenario_result, "hybrid", "low", include_ci=True)

    print("Path sweep completed.")
    if args.from_summary is None:
        print(f"Markdown summary: {output_paths['markdown']}")
    print(f"Direct relative error figure: {output_paths['direct_figure']}")
    print(f"Direct relative error figure with CI: {output_paths['direct_figure_ci']}")
    print(f"Low relative error figure: {output_paths['low_figure']}")
    print(f"Low relative error figure with CI: {output_paths['low_figure_ci']}")
    print(f"Benchmark direct-only figure: {output_paths['benchmark_direct_only']}")
    print(f"Benchmark direct-only figure with CI: {output_paths['benchmark_direct_only_ci']}")
    print(f"Benchmark low-only figure with CI: {output_paths['benchmark_low_only_ci']}")
    print(f"Hybrid direct-only figure: {output_paths['hybrid_direct_only']}")
    print(f"Hybrid direct-only figure with CI: {output_paths['hybrid_direct_only_ci']}")
    print(f"Hybrid low-only figure with CI: {output_paths['hybrid_low_only_ci']}")


if __name__ == "__main__":
    main()
