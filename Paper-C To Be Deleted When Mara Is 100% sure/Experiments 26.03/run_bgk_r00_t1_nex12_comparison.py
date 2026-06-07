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
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
BENCHMARK_SCRIPT = THIS_DIR / "LSMC Benchmark" / "run_gdmr_benchmark_put.py"
HYBRID_SCRIPT = THIS_DIR / "Hybrid LSMC-PDE with FFT" / "run_gdmr_hybrid_put.py"
SCRATCH_DIR = THIS_DIR / "_scratch"

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
}

BGK_PRODUCTION_ENV = {
    "GDMR_EXERCISE_DATES": "12",
    "GDMR_EULER_STEPS": "600",
    "GDMR_LSMC_PATHS": "1000000",
    "GDMR_LSMC_LOW_PATHS": "1000000",
    "GDMR_LSMC_SEED": "2026",
    "GDMR_LSMC_LOW_SEED": "2103",
    "GDMR_HYBRID_PATHS": "20000",
    "GDMR_HYBRID_LOW_PATHS": "20000",
    "GDMR_HYBRID_ASSET_POINTS": "181",
    "GDMR_HYBRID_ASSET_LOW_FACTOR": "0.35",
    "GDMR_HYBRID_ASSET_HIGH_FACTOR": "3.00",
    "GDMR_HYBRID_VOL_QUANTILE": "0.997",
    "GDMR_HYBRID_FST_PAD_FACTOR": "4",
    "GDMR_HYBRID_FST_BATCH_SIZE": "256",
    "GDMR_HYBRID_SEED": "2026",
    "GDMR_HYBRID_LOW_SEED": "2103",
}

BGK_SMOKE_ENV = {
    "GDMR_EXERCISE_DATES": "12",
    "GDMR_EULER_STEPS": "600",
    "GDMR_LSMC_PATHS": "20000",
    "GDMR_LSMC_LOW_PATHS": "20000",
    "GDMR_LSMC_SEED": "2026",
    "GDMR_LSMC_LOW_SEED": "2103",
    "GDMR_HYBRID_PATHS": "2000",
    "GDMR_HYBRID_LOW_PATHS": "2000",
    "GDMR_HYBRID_ASSET_POINTS": "181",
    "GDMR_HYBRID_ASSET_LOW_FACTOR": "0.35",
    "GDMR_HYBRID_ASSET_HIGH_FACTOR": "3.00",
    "GDMR_HYBRID_VOL_QUANTILE": "0.997",
    "GDMR_HYBRID_FST_PAD_FACTOR": "4",
    "GDMR_HYBRID_FST_BATCH_SIZE": "256",
    "GDMR_HYBRID_SEED": "2026",
    "GDMR_HYBRID_LOW_SEED": "2103",
}

SCENARIOS = [
    {"scenario": "ATM", "GDMR_S0": "100.0", "GDMR_STRIKE": "100.0", "GDMR_MATURITY": "1.0"},
    {"scenario": "ITM put", "GDMR_S0": "100.0", "GDMR_STRIKE": "110.0", "GDMR_MATURITY": "1.0"},
    {"scenario": "OTM put", "GDMR_S0": "100.0", "GDMR_STRIKE": "90.0", "GDMR_MATURITY": "1.0"},
]

CSV_COLUMNS = [
    "scenario",
    "S0",
    "K",
    "T",
    "benchmark_direct_price",
    "benchmark_direct_error",
    "benchmark_low_price",
    "benchmark_low_error",
    "hybrid_direct_price",
    "hybrid_direct_error",
    "hybrid_low_price",
    "hybrid_low_error",
    "hybrid_direct_rel_error",
    "hybrid_low_rel_error",
    "benchmark_direct_low_gap",
    "hybrid_direct_low_gap",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the BGK Testing-aligned r=0, T=1 gDMR comparison with 12 exercise dates."
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Use reduced path counts while keeping the 12-date experiment setup.",
    )
    return parser.parse_args()


def rel_error(value: float, reference: float) -> float:
    if abs(reference) <= 1e-16:
        return 0.0 if abs(value) <= 1e-16 else float("inf")
    return abs(value - reference) / abs(reference)


def gap_pct(low: float, direct: float) -> float:
    if abs(direct) <= 1e-16:
        return float("inf")
    return (low - direct) / direct


def build_env(smoke: bool) -> dict[str, str]:
    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(BGK_MODEL_ENV)
    env.update(BGK_SMOKE_ENV if smoke else BGK_PRODUCTION_ENV)
    env["GDMR_LSMC_STORE_DIR"] = str(SCRATCH_DIR)
    return env


def run_benchmark(env: dict[str, str]) -> tuple[dict[str, float], str]:
    completed = subprocess.run(
        [sys.executable, str(BENCHMARK_SCRIPT)],
        cwd=str(THIS_DIR),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
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
    return values, completed.stdout


def run_hybrid(env: dict[str, str]) -> tuple[dict[str, float], str]:
    completed = subprocess.run(
        [sys.executable, str(HYBRID_SCRIPT)],
        cwd=str(THIS_DIR),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
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
        raise RuntimeError(
            f"Could not parse RESULT_JSON from {HYBRID_SCRIPT.name}.\n{completed.stdout}"
        )

    raw = json.loads(result_line)
    values = {
        "hybrid_direct_price": float(raw["hybrid_direct_price"]),
        "hybrid_direct_error": float(raw["hybrid_direct_error"]),
        "hybrid_low_price": float(raw["hybrid_low_price"]),
        "hybrid_low_error": float(raw["hybrid_low_error"]),
    }
    return values, completed.stdout


def format_pct(value: float) -> str:
    return f"{100.0 * value:.3f}%"


def headline_table(rows: list[dict[str, float | str]]) -> str:
    header = [
        "| Scenario | `S0` | `K` | Benchmark direct | Benchmark direct SE | Benchmark low | Benchmark low SE | Hybrid direct | Hybrid direct SE | Hybrid low | Hybrid low SE | Hybrid direct rel. err. | Hybrid low rel. err. | Benchmark direct-low gap | Hybrid direct-low gap |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    lines = []
    for row in rows:
        lines.append(
            "| {scenario} | `{S0:.0f}` | `{K:.0f}` | `{benchmark_direct_price:.6f}` | `{benchmark_direct_error:.6f}` | "
            "`{benchmark_low_price:.6f}` | `{benchmark_low_error:.6f}` | `{hybrid_direct_price:.6f}` | "
            "`{hybrid_direct_error:.6f}` | `{hybrid_low_price:.6f}` | `{hybrid_low_error:.6f}` | "
            "`{hybrid_direct_rel_error_pct}` | `{hybrid_low_rel_error_pct}` | `{benchmark_direct_low_gap_pct}` | "
            "`{hybrid_direct_low_gap_pct}` |".format(**row)
        )
    return "\n".join(header + lines)


def write_csv(path: Path, rows: list[dict[str, float | str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in CSV_COLUMNS})


def build_summary(rows: list[dict[str, float | str]], smoke: bool, csv_path: Path) -> str:
    run_label = "smoke" if smoke else "production"
    numerical_block = BGK_SMOKE_ENV if smoke else BGK_PRODUCTION_ENV
    table = headline_table(rows)
    numerical_lines = "\n".join(f"{key}={value}" for key, value in numerical_block.items())
    model_lines = "\n".join(f"{key}={value}" for key, value in BGK_MODEL_ENV.items())

    return "\n".join(
        [
            f"# BGK Testing-aligned gDMR comparison with `r=0.0`, `T=1.0`, `N_ex=12` ({run_label})",
            "",
            "This note records the isolated local comparison suite run from `Experiments 26.03`.",
            "It reproduces the original BGK Testing-aligned gDMR family with the production numerical block kept fixed except that the Bermudan exercise dates are reduced from `100` to `12`.",
            "The `LSMC Benchmark` values are the benchmark reference in every row, and the `Hybrid LSMC-PDE with FFT` values are compared against them.",
            "",
            "## Scenario Summary",
            "",
            table,
            "",
            "## Model Block",
            "",
            "```text",
            model_lines,
            "```",
            "",
            "## Numerical Block",
            "",
            "```text",
            numerical_lines,
            "```",
            "",
            "## Correlation Note",
            "",
            "- The implemented code input uses `GDMR_RHO23=0.59`.",
            "- The screenshot quantity `tilde rho_23=-0.656` is not used as the code correlation input.",
            "",
            "## Saved Outputs",
            "",
            f"- CSV table: `{csv_path.name}`",
            "",
        ]
    )


def maybe_cleanup_scratch(smoke: bool) -> None:
    if smoke:
        return
    if SCRATCH_DIR.exists():
        shutil.rmtree(SCRATCH_DIR)


def main() -> None:
    args = parse_args()
    env_base = build_env(args.smoke)
    rows: list[dict[str, float | str]] = []

    try:
        for scenario in SCENARIOS:
            env = env_base.copy()
            env.update(
                {
                    "GDMR_S0": scenario["GDMR_S0"],
                    "GDMR_STRIKE": scenario["GDMR_STRIKE"],
                    "GDMR_MATURITY": scenario["GDMR_MATURITY"],
                }
            )

            benchmark, _ = run_benchmark(env)
            hybrid, _ = run_hybrid(env)

            benchmark_direct_price = float(benchmark["lsmc_direct_price"])
            benchmark_direct_error = float(benchmark["lsmc_direct_error"])
            benchmark_low_price = float(benchmark["lsmc_low_price"])
            benchmark_low_error = float(benchmark["lsmc_low_error"])
            hybrid_direct_price = float(hybrid["hybrid_direct_price"])
            hybrid_direct_error = float(hybrid["hybrid_direct_error"])
            hybrid_low_price = float(hybrid["hybrid_low_price"])
            hybrid_low_error = float(hybrid["hybrid_low_error"])
            hybrid_direct_rel_error = rel_error(hybrid_direct_price, benchmark_direct_price)
            hybrid_low_rel_error = rel_error(hybrid_low_price, benchmark_low_price)
            benchmark_direct_low_gap = gap_pct(benchmark_low_price, benchmark_direct_price)
            hybrid_direct_low_gap = gap_pct(hybrid_low_price, hybrid_direct_price)

            rows.append(
                {
                    "scenario": scenario["scenario"],
                    "S0": float(scenario["GDMR_S0"]),
                    "K": float(scenario["GDMR_STRIKE"]),
                    "T": float(scenario["GDMR_MATURITY"]),
                    "benchmark_direct_price": benchmark_direct_price,
                    "benchmark_direct_error": benchmark_direct_error,
                    "benchmark_low_price": benchmark_low_price,
                    "benchmark_low_error": benchmark_low_error,
                    "hybrid_direct_price": hybrid_direct_price,
                    "hybrid_direct_error": hybrid_direct_error,
                    "hybrid_low_price": hybrid_low_price,
                    "hybrid_low_error": hybrid_low_error,
                    "hybrid_direct_rel_error": hybrid_direct_rel_error,
                    "hybrid_low_rel_error": hybrid_low_rel_error,
                    "benchmark_direct_low_gap": benchmark_direct_low_gap,
                    "hybrid_direct_low_gap": hybrid_direct_low_gap,
                    "hybrid_direct_rel_error_pct": format_pct(hybrid_direct_rel_error),
                    "hybrid_low_rel_error_pct": format_pct(hybrid_low_rel_error),
                    "benchmark_direct_low_gap_pct": format_pct(benchmark_direct_low_gap),
                    "hybrid_direct_low_gap_pct": format_pct(hybrid_direct_low_gap),
                }
            )

        csv_name = (
            "bgk_r00_t1_nex12_smoke_table.csv"
            if args.smoke
            else "bgk_r00_t1_nex12_comparison_table.csv"
        )
        summary_name = (
            "bgk_r00_t1_nex12_smoke_summary.md"
            if args.smoke
            else "bgk_r00_t1_nex12_comparison_summary.md"
        )
        csv_path = THIS_DIR / csv_name
        summary_path = THIS_DIR / summary_name

        write_csv(csv_path, rows)
        summary_text = build_summary(rows, args.smoke, csv_path)
        summary_path.write_text(summary_text, encoding="utf-8")

        maybe_cleanup_scratch(args.smoke)

        print(headline_table(rows))
        print()
        print(f"Summary saved to: {summary_path.name}")
        print(f"CSV saved to:     {csv_path.name}")
    except Exception:
        raise


if __name__ == "__main__":
    main()
