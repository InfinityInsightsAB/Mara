#!/usr/bin/env python3
from __future__ import annotations

import csv
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
BENCHMARK_SCRIPT = THIS_DIR / "LSMC Benchmark" / "run_gdmr_benchmark_put.py"
SCRATCH_DIR = THIS_DIR / "_scratch_benchmark_k80_k70"
OUTPUT_STEM = "bgk_r00_t1_nex12_benchmark_steps1200_paths1200000_k80_k70"
OUTPUT_TABLE = THIS_DIR / f"{OUTPUT_STEM}_table.csv"
OUTPUT_SUMMARY = THIS_DIR / f"{OUTPUT_STEM}_summary.md"
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
    "GDMR_EULER_STEPS": "1200",
    "GDMR_LSMC_PATHS": "1200000",
    "GDMR_LSMC_LOW_PATHS": "1200000",
    "GDMR_LSMC_SEED": "2026",
    "GDMR_LSMC_LOW_SEED": "2103",
}

SCENARIOS = [
    {"label": "K=80 put", "strike": "80.0", "maturity": "1.0"},
    {"label": "K=70 put", "strike": "70.0", "maturity": "1.0"},
]

CSV_COLUMNS = [
    "scenario",
    "S0",
    "K",
    "T",
    "euler_steps",
    "lsmc_paths",
    "lsmc_low_paths",
    "runtime_seconds",
    "benchmark_direct_price",
    "benchmark_direct_error",
    "benchmark_direct_ci_lower",
    "benchmark_direct_ci_upper",
    "benchmark_low_price",
    "benchmark_low_error",
    "benchmark_low_ci_lower",
    "benchmark_low_ci_upper",
    "benchmark_direct_low_gap",
]


def ci_bounds(value: float, se: float) -> tuple[float, float]:
    half_width = CI_Z * se
    return value - half_width, value + half_width


def gap_pct(low: float, direct: float) -> float:
    if abs(direct) <= 1e-16:
        return float("inf")
    return (low - direct) / direct


def format_pct(value: float) -> str:
    return f"{100.0 * value:.3f}%"


def build_env(strike: str, maturity: str) -> dict[str, str]:
    env = os.environ.copy()
    env.update(BGK_MODEL_ENV)
    env.update(
        {
            "GDMR_STRIKE": strike,
            "GDMR_MATURITY": maturity,
            "GDMR_LSMC_STORE_DIR": str(SCRATCH_DIR),
        }
    )
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


def write_csv(rows: list[dict[str, float | str]]) -> None:
    with OUTPUT_TABLE.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in CSV_COLUMNS})


def build_summary(rows: list[dict[str, float | str]]) -> str:
    table_rows = []
    for row in rows:
        table_rows.append(
            "| "
            + " | ".join(
                [
                    f"`{row['scenario']}`",
                    f"`{float(row['K']):.0f}`",
                    f"`{float(row['benchmark_direct_price']):.6f}`",
                    f"`{float(row['benchmark_direct_error']):.6f}`",
                    f"`[{float(row['benchmark_direct_ci_lower']):.6f}, {float(row['benchmark_direct_ci_upper']):.6f}]`",
                    f"`{float(row['benchmark_low_price']):.6f}`",
                    f"`{float(row['benchmark_low_error']):.6f}`",
                    f"`[{float(row['benchmark_low_ci_lower']):.6f}, {float(row['benchmark_low_ci_upper']):.6f}]`",
                    f"`{format_pct(float(row['benchmark_direct_low_gap']))}`",
                    f"`{float(row['runtime_seconds']):.2f} s`",
                ]
            )
            + " |"
        )

    return "\n".join(
        [
            "# BGK 12-date benchmark-only run for K=80 and K=70",
            "",
            "This note records the isolated LSMC benchmark-only runs for the BGK-style calibrated gDMR model with the same 12-date setup used elsewhere in `Experiments 26.03`.",
            "The only strike changes are `K=80` and `K=70`; all other model and numerical parameters are kept fixed.",
            "",
            "## Scenario Summary",
            "",
            "| Scenario | K | Benchmark direct | Direct SE | Direct 95% CI | Benchmark low | Low SE | Low 95% CI | Direct-low gap | Runtime |",
            "| --- | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: |",
            *table_rows,
            "",
            "## Model Block",
            "",
            "```text",
            "GDMR_S0=100.0",
            "GDMR_V0=0.114",
            "GDMR_VP0=0.110",
            "GDMR_R=0.0",
            "GDMR_KAPPA1=5.5",
            "GDMR_KAPPA2=0.1",
            "GDMR_THETA=0.078",
            "GDMR_XI1=2.689",
            "GDMR_XI2=0.502",
            "GDMR_DELTA1=0.94",
            "GDMR_DELTA2=0.94",
            "GDMR_RHO12=-0.982",
            "GDMR_RHO13=-0.727",
            "GDMR_RHO23=0.59",
            "GDMR_T=1.0",
            "```",
            "",
            "## Numerical Block",
            "",
            "```text",
            "GDMR_EXERCISE_DATES=12",
            "GDMR_EULER_STEPS=1200",
            "GDMR_LSMC_PATHS=1200000",
            "GDMR_LSMC_LOW_PATHS=1200000",
            "GDMR_LSMC_SEED=2026",
            "GDMR_LSMC_LOW_SEED=2103",
            "```",
            "",
            f"Saved CSV: `{OUTPUT_TABLE.name}`",
        ]
    )


def main() -> None:
    rows: list[dict[str, float | str]] = []
    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    try:
        for scenario in SCENARIOS:
            values, runtime_seconds = run_benchmark(build_env(scenario["strike"], scenario["maturity"]))
            direct_ci_lower, direct_ci_upper = ci_bounds(values["lsmc_direct_price"], values["lsmc_direct_error"])
            low_ci_lower, low_ci_upper = ci_bounds(values["lsmc_low_price"], values["lsmc_low_error"])
            rows.append(
                {
                    "scenario": scenario["label"],
                    "S0": 100.0,
                    "K": float(scenario["strike"]),
                    "T": float(scenario["maturity"]),
                    "euler_steps": 1200,
                    "lsmc_paths": 1200000,
                    "lsmc_low_paths": 1200000,
                    "runtime_seconds": runtime_seconds,
                    "benchmark_direct_price": values["lsmc_direct_price"],
                    "benchmark_direct_error": values["lsmc_direct_error"],
                    "benchmark_direct_ci_lower": direct_ci_lower,
                    "benchmark_direct_ci_upper": direct_ci_upper,
                    "benchmark_low_price": values["lsmc_low_price"],
                    "benchmark_low_error": values["lsmc_low_error"],
                    "benchmark_low_ci_lower": low_ci_lower,
                    "benchmark_low_ci_upper": low_ci_upper,
                    "benchmark_direct_low_gap": gap_pct(values["lsmc_low_price"], values["lsmc_direct_price"]),
                }
            )

        write_csv(rows)
        OUTPUT_SUMMARY.write_text(build_summary(rows), encoding="utf-8")
    finally:
        if SCRATCH_DIR.exists():
            shutil.rmtree(SCRATCH_DIR)


if __name__ == "__main__":
    main()
