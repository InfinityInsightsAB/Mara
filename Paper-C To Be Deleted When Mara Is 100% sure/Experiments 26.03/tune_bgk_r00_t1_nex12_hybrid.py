#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
HYBRID_SCRIPT = THIS_DIR / "Hybrid LSMC-PDE with FFT" / "run_gdmr_hybrid_put.py"
BASELINE_TABLE = THIS_DIR / "bgk_r00_t1_nex12_comparison_table.csv"
TUNING_TABLE = THIS_DIR / "bgk_r00_t1_nex12_hybrid_tuning_table.csv"
TUNING_SUMMARY = THIS_DIR / "bgk_r00_t1_nex12_hybrid_tuning_summary.md"
TUNED_TABLE = THIS_DIR / "bgk_r00_t1_nex12_tuned_comparison_table.csv"
TUNED_SUMMARY = THIS_DIR / "bgk_r00_t1_nex12_tuned_comparison_summary.md"

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
    "GDMR_EULER_STEPS": "600",
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

FOCUS_SCENARIOS = {"ATM", "OTM put"}

CANDIDATES = [
    {
        "label": "baseline_20k_181",
        "paths": 20000,
        "low_paths": 20000,
        "asset_points": 181,
        "asset_low_factor": 0.35,
        "asset_high_factor": 3.00,
        "vol_quantile": 0.997,
    },
    {
        "label": "paths40k_grid181",
        "paths": 40000,
        "low_paths": 40000,
        "asset_points": 181,
        "asset_low_factor": 0.35,
        "asset_high_factor": 3.00,
        "vol_quantile": 0.997,
    },
    {
        "label": "paths40k_grid241",
        "paths": 40000,
        "low_paths": 40000,
        "asset_points": 241,
        "asset_low_factor": 0.35,
        "asset_high_factor": 3.00,
        "vol_quantile": 0.997,
    },
    {
        "label": "paths60k_grid241",
        "paths": 60000,
        "low_paths": 60000,
        "asset_points": 241,
        "asset_low_factor": 0.35,
        "asset_high_factor": 3.00,
        "vol_quantile": 0.997,
    },
    {
        "label": "paths60k_grid301",
        "paths": 60000,
        "low_paths": 60000,
        "asset_points": 301,
        "asset_low_factor": 0.35,
        "asset_high_factor": 3.00,
        "vol_quantile": 0.997,
    },
    {
        "label": "paths60k_grid301_wide_q999",
        "paths": 60000,
        "low_paths": 60000,
        "asset_points": 301,
        "asset_low_factor": 0.30,
        "asset_high_factor": 3.50,
        "vol_quantile": 0.999,
    },
]

TUNING_COLUMNS = [
    "setting",
    "scenario",
    "S0",
    "K",
    "T",
    "paths",
    "low_paths",
    "asset_points",
    "asset_low_factor",
    "asset_high_factor",
    "vol_quantile",
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
    "hybrid_direct_low_gap",
]

COMPARISON_COLUMNS = [
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


def rel_error(value: float, reference: float) -> float:
    if abs(reference) <= 1e-16:
        return 0.0 if abs(value) <= 1e-16 else float("inf")
    return abs(value - reference) / abs(reference)


def gap_pct(low: float, direct: float) -> float:
    if abs(direct) <= 1e-16:
        return float("inf")
    return (low - direct) / direct


def format_pct(value: float) -> str:
    return f"{100.0 * value:.3f}%"


def load_baseline_rows() -> dict[str, dict[str, float | str]]:
    if not BASELINE_TABLE.exists():
        raise FileNotFoundError(
            f"Missing baseline table {BASELINE_TABLE.name}. Run the baseline 12-date comparison first."
        )

    rows: dict[str, dict[str, float | str]] = {}
    with BASELINE_TABLE.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for raw_row in reader:
            row: dict[str, float | str] = {"scenario": raw_row["scenario"]}
            for key, value in raw_row.items():
                if key == "scenario":
                    continue
                row[key] = float(value)
            rows[str(raw_row["scenario"])] = row
    return rows


def run_hybrid(env: dict[str, str]) -> dict[str, float]:
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
        raise RuntimeError(f"Could not parse RESULT_JSON from {HYBRID_SCRIPT.name}.\n{completed.stdout}")

    raw = json.loads(result_line)
    return {
        "hybrid_direct_price": float(raw["hybrid_direct_price"]),
        "hybrid_direct_error": float(raw["hybrid_direct_error"]),
        "hybrid_low_price": float(raw["hybrid_low_price"]),
        "hybrid_low_error": float(raw["hybrid_low_error"]),
    }


def candidate_env(candidate: dict[str, float | int | str], scenario: dict[str, str]) -> dict[str, str]:
    env = os.environ.copy()
    env.update(BGK_MODEL_ENV)
    env.update(
        {
            "GDMR_S0": scenario["GDMR_S0"],
            "GDMR_STRIKE": scenario["GDMR_STRIKE"],
            "GDMR_MATURITY": scenario["GDMR_MATURITY"],
            "GDMR_HYBRID_PATHS": str(candidate["paths"]),
            "GDMR_HYBRID_LOW_PATHS": str(candidate["low_paths"]),
            "GDMR_HYBRID_ASSET_POINTS": str(candidate["asset_points"]),
            "GDMR_HYBRID_ASSET_LOW_FACTOR": f"{float(candidate['asset_low_factor']):.2f}",
            "GDMR_HYBRID_ASSET_HIGH_FACTOR": f"{float(candidate['asset_high_factor']):.2f}",
            "GDMR_HYBRID_VOL_QUANTILE": f"{float(candidate['vol_quantile']):.3f}",
        }
    )
    return env


def write_csv(path: Path, rows: list[dict[str, float | str]], columns: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in columns})


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def build_tuning_summary(
    tuning_rows: list[dict[str, float | str]],
    focus_scores: list[dict[str, float | str]],
    best_candidate: dict[str, float | int | str],
) -> str:
    focus_table_rows = []
    for score in focus_scores:
        focus_table_rows.append(
            [
                f"`{score['setting']}`",
                f"`{score['atm_direct_rel_error_pct']}`",
                f"`{score['otm_direct_rel_error_pct']}`",
                f"`{score['max_focus_direct_rel_error_pct']}`",
                f"`{score['avg_focus_direct_rel_error_pct']}`",
            ]
        )

    detail_rows = []
    for row in tuning_rows:
        detail_rows.append(
            [
                f"`{row['setting']}`",
                f"`{row['scenario']}`",
                f"`{int(float(row['paths'])):,}`",
                f"`{int(float(row['asset_points']))}`",
                f"`{float(row['asset_low_factor']):.2f}`",
                f"`{float(row['asset_high_factor']):.2f}`",
                f"`{float(row['vol_quantile']):.3f}`",
                f"`{float(row['hybrid_direct_price']):.6f}`",
                f"`{float(row['hybrid_direct_error']):.6f}`",
                f"`{format_pct(float(row['hybrid_direct_rel_error']))}`",
                f"`{float(row['hybrid_low_price']):.6f}`",
                f"`{float(row['hybrid_low_error']):.6f}`",
                f"`{format_pct(float(row['hybrid_low_rel_error']))}`",
            ]
        )

    return "\n".join(
        [
            "# BGK 12-date Hybrid Tuning",
            "",
            "This note tunes the hybrid side only for the 12-date BGK Testing-aligned experiment.",
            "Benchmark values are reused from `bgk_r00_t1_nex12_comparison_table.csv`, so only the hybrid configuration changes here.",
            "",
            "## Candidate scorecard on failing scenarios",
            "",
            markdown_table(
                [
                    "Setting",
                    "ATM direct rel. error",
                    "OTM direct rel. error",
                    "Max focus direct rel. error",
                    "Average focus direct rel. error",
                ],
                focus_table_rows,
            ),
            "",
            "## Best common setting",
            "",
            f"- Label: `{best_candidate['label']}`",
            f"- Hybrid paths: `{best_candidate['paths']}`",
            f"- Hybrid low paths: `{best_candidate['low_paths']}`",
            f"- Asset points: `{best_candidate['asset_points']}`",
            f"- Asset range factors: `{float(best_candidate['asset_low_factor']):.2f}` / `{float(best_candidate['asset_high_factor']):.2f}`",
            f"- Vol truncation quantile: `{float(best_candidate['vol_quantile']):.3f}`",
            "",
            "## Detailed scenario results",
            "",
            markdown_table(
                [
                    "Setting",
                    "Scenario",
                    "Paths",
                    "Asset points",
                    "Low factor",
                    "High factor",
                    "Vol q",
                    "Hybrid direct",
                    "Hybrid direct SE",
                    "Direct rel. error",
                    "Hybrid low",
                    "Hybrid low SE",
                    "Low rel. error",
                ],
                detail_rows,
            ),
            "",
            f"Saved CSV: `{TUNING_TABLE.name}`",
        ]
    )


def build_tuned_summary(
    comparison_rows: list[dict[str, float | str]],
    best_candidate: dict[str, float | int | str],
) -> str:
    table_rows = []
    for row in comparison_rows:
        table_rows.append(
            [
                f"`{row['scenario']}`",
                f"`{float(row['K']):.0f}`",
                f"`{float(row['benchmark_direct_price']):.6f}`",
                f"`{float(row['hybrid_direct_price']):.6f}`",
                f"`{format_pct(float(row['hybrid_direct_rel_error']))}`",
                f"`{float(row['benchmark_low_price']):.6f}`",
                f"`{float(row['hybrid_low_price']):.6f}`",
                f"`{format_pct(float(row['hybrid_low_rel_error']))}`",
            ]
        )

    return "\n".join(
        [
            "# BGK 12-date Tuned Hybrid Comparison",
            "",
            "This note keeps the 12-date BGK benchmark fixed and reruns the hybrid with the best common tuning setting found in `bgk_r00_t1_nex12_hybrid_tuning_summary.md`.",
            "",
            "## Tuned hybrid setting",
            "",
            f"- Label: `{best_candidate['label']}`",
            f"- Hybrid paths: `{best_candidate['paths']}`",
            f"- Hybrid low paths: `{best_candidate['low_paths']}`",
            f"- Asset points: `{best_candidate['asset_points']}`",
            f"- Asset range factors: `{float(best_candidate['asset_low_factor']):.2f}` / `{float(best_candidate['asset_high_factor']):.2f}`",
            f"- Vol truncation quantile: `{float(best_candidate['vol_quantile']):.3f}`",
            "",
            "## Scenario summary",
            "",
            markdown_table(
                [
                    "Scenario",
                    "K",
                    "Benchmark direct",
                    "Hybrid direct",
                    "Hybrid direct rel. error",
                    "Benchmark low",
                    "Hybrid low",
                    "Hybrid low rel. error",
                ],
                table_rows,
            ),
            "",
            f"Saved CSV: `{TUNED_TABLE.name}`",
        ]
    )


def main() -> None:
    baseline_rows = load_baseline_rows()
    tuning_rows: list[dict[str, float | str]] = []

    for candidate in CANDIDATES:
        for scenario in SCENARIOS:
            if scenario["scenario"] not in FOCUS_SCENARIOS:
                continue
            env = candidate_env(candidate, scenario)
            hybrid = run_hybrid(env)
            benchmark = baseline_rows[scenario["scenario"]]

            tuning_rows.append(
                {
                    "setting": str(candidate["label"]),
                    "scenario": scenario["scenario"],
                    "S0": float(scenario["GDMR_S0"]),
                    "K": float(scenario["GDMR_STRIKE"]),
                    "T": float(scenario["GDMR_MATURITY"]),
                    "paths": int(candidate["paths"]),
                    "low_paths": int(candidate["low_paths"]),
                    "asset_points": int(candidate["asset_points"]),
                    "asset_low_factor": float(candidate["asset_low_factor"]),
                    "asset_high_factor": float(candidate["asset_high_factor"]),
                    "vol_quantile": float(candidate["vol_quantile"]),
                    "benchmark_direct_price": float(benchmark["benchmark_direct_price"]),
                    "benchmark_direct_error": float(benchmark["benchmark_direct_error"]),
                    "benchmark_low_price": float(benchmark["benchmark_low_price"]),
                    "benchmark_low_error": float(benchmark["benchmark_low_error"]),
                    "hybrid_direct_price": hybrid["hybrid_direct_price"],
                    "hybrid_direct_error": hybrid["hybrid_direct_error"],
                    "hybrid_low_price": hybrid["hybrid_low_price"],
                    "hybrid_low_error": hybrid["hybrid_low_error"],
                    "hybrid_direct_rel_error": rel_error(
                        hybrid["hybrid_direct_price"],
                        float(benchmark["benchmark_direct_price"]),
                    ),
                    "hybrid_low_rel_error": rel_error(
                        hybrid["hybrid_low_price"],
                        float(benchmark["benchmark_low_price"]),
                    ),
                    "hybrid_direct_low_gap": gap_pct(
                        hybrid["hybrid_low_price"],
                        hybrid["hybrid_direct_price"],
                    ),
                }
            )

    write_csv(TUNING_TABLE, tuning_rows, TUNING_COLUMNS)

    focus_scores: list[dict[str, float | str]] = []
    for candidate in CANDIDATES:
        candidate_rows = [row for row in tuning_rows if row["setting"] == candidate["label"]]
        atm_row = next(row for row in candidate_rows if row["scenario"] == "ATM")
        otm_row = next(row for row in candidate_rows if row["scenario"] == "OTM put")
        atm_error = float(atm_row["hybrid_direct_rel_error"])
        otm_error = float(otm_row["hybrid_direct_rel_error"])
        max_error = max(atm_error, otm_error)
        avg_error = 0.5 * (atm_error + otm_error)
        focus_scores.append(
            {
                "setting": str(candidate["label"]),
                "atm_direct_rel_error": atm_error,
                "otm_direct_rel_error": otm_error,
                "max_focus_direct_rel_error": max_error,
                "avg_focus_direct_rel_error": avg_error,
                "atm_direct_rel_error_pct": format_pct(atm_error),
                "otm_direct_rel_error_pct": format_pct(otm_error),
                "max_focus_direct_rel_error_pct": format_pct(max_error),
                "avg_focus_direct_rel_error_pct": format_pct(avg_error),
            }
        )

    best_score = min(
        focus_scores,
        key=lambda row: (
            float(row["max_focus_direct_rel_error"]),
            float(row["avg_focus_direct_rel_error"]),
        ),
    )
    best_candidate = next(candidate for candidate in CANDIDATES if candidate["label"] == best_score["setting"])

    TUNING_SUMMARY.write_text(
        build_tuning_summary(tuning_rows, focus_scores, best_candidate),
        encoding="utf-8",
    )

    comparison_rows: list[dict[str, float | str]] = []
    for scenario in SCENARIOS:
        env = candidate_env(best_candidate, scenario)
        hybrid = run_hybrid(env)
        benchmark = baseline_rows[scenario["scenario"]]
        comparison_rows.append(
            {
                "scenario": scenario["scenario"],
                "S0": float(scenario["GDMR_S0"]),
                "K": float(scenario["GDMR_STRIKE"]),
                "T": float(scenario["GDMR_MATURITY"]),
                "benchmark_direct_price": float(benchmark["benchmark_direct_price"]),
                "benchmark_direct_error": float(benchmark["benchmark_direct_error"]),
                "benchmark_low_price": float(benchmark["benchmark_low_price"]),
                "benchmark_low_error": float(benchmark["benchmark_low_error"]),
                "hybrid_direct_price": hybrid["hybrid_direct_price"],
                "hybrid_direct_error": hybrid["hybrid_direct_error"],
                "hybrid_low_price": hybrid["hybrid_low_price"],
                "hybrid_low_error": hybrid["hybrid_low_error"],
                "hybrid_direct_rel_error": rel_error(
                    hybrid["hybrid_direct_price"],
                    float(benchmark["benchmark_direct_price"]),
                ),
                "hybrid_low_rel_error": rel_error(
                    hybrid["hybrid_low_price"],
                    float(benchmark["benchmark_low_price"]),
                ),
                "benchmark_direct_low_gap": gap_pct(
                    float(benchmark["benchmark_low_price"]),
                    float(benchmark["benchmark_direct_price"]),
                ),
                "hybrid_direct_low_gap": gap_pct(
                    hybrid["hybrid_low_price"],
                    hybrid["hybrid_direct_price"],
                ),
            }
        )

    write_csv(TUNED_TABLE, comparison_rows, COMPARISON_COLUMNS)
    TUNED_SUMMARY.write_text(
        build_tuned_summary(comparison_rows, best_candidate),
        encoding="utf-8",
    )

    print("Hybrid tuning completed.")
    print(f"Tuning summary: {TUNING_SUMMARY.name}")
    print(f"Tuning table:   {TUNING_TABLE.name}")
    print(f"Best setting:   {best_candidate['label']}")
    print(f"Tuned summary:  {TUNED_SUMMARY.name}")
    print(f"Tuned table:    {TUNED_TABLE.name}")


if __name__ == "__main__":
    main()
