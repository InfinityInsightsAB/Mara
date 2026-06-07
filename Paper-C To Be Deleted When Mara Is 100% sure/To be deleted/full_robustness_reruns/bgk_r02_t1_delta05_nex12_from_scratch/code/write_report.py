from __future__ import annotations

import csv
import json
import math
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


RUN_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = RUN_ROOT.parents[2]
CONFIG_PATH = RUN_ROOT / "config" / "rerun_config.json"
RESULTS_DIR = RUN_ROOT / "results"
REFERENCE_DIR = RESULTS_DIR / "reference_values"
PATH_REFERENCE_DIR = REFERENCE_DIR / "path_sweep"
METADATA_DIR = RESULTS_DIR / "metadata"
VALIDATION_JSON = RESULTS_DIR / "validation" / "validation_summary.json"
SUMMARY_DIR = RUN_ROOT / "summary"
FIGURE_DIR = RUN_ROOT / "figures"
TABLE_DIR = RUN_ROOT / "tables"
CASE_ID = "bgk_r02_t1_delta05_nex12"
BENCHMARK_CSV = REFERENCE_DIR / f"{CASE_ID}_benchmark_steps1200_paths1200000_table.csv"
REPORT_MD = SUMMARY_DIR / "sandbox_rerun_report_20260504.md"
MANUSCRIPT_CODE_DIR = PROJECT_ROOT / "Working Files" / "Manuscript Code"


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_required_rows(path: Path, expected_rows: int | None = None) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Required report input is missing: {path}")
    rows = read_rows(path)
    if not rows:
        raise RuntimeError(f"Required report input is empty: {path}")
    if expected_rows is not None and len(rows) != expected_rows:
        raise RuntimeError(f"Required report input has {len(rows)} rows, expected {expected_rows}: {path}")
    return rows


def finite(value: Any) -> float:
    out = float(value)
    if not math.isfinite(out):
        return float("nan")
    return out


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_required_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required report input is missing: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not data:
        raise RuntimeError(f"Required report JSON is empty: {path}")
    return data


def fmt(value: float, digits: int = 6) -> str:
    if math.isnan(value):
        return "NA"
    return f"{value:.{digits}f}"


def md_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    out.extend("| " + " | ".join(row) + " |" for row in rows)
    return out


def compare_benchmark_rows() -> list[list[str]]:
    sandbox = read_required_rows(BENCHMARK_CSV, expected_rows=5)
    prior = read_rows(MANUSCRIPT_CODE_DIR / "reference_values" / f"{CASE_ID}_benchmark_steps1200_paths1200000_table.csv")
    prior_by_k = {int(float(row["K"])): row for row in prior}
    rows: list[list[str]] = []
    for row in sorted(sandbox, key=lambda item: finite(item["K"])):
        k = int(float(row["K"]))
        price = finite(row["benchmark_direct_price"])
        se = finite(row["benchmark_direct_error"])
        prior_price = finite(prior_by_k.get(k, {}).get("benchmark_direct_price", "nan"))
        diff = price - prior_price if not math.isnan(prior_price) else float("nan")
        rows.append([str(k), fmt(price), fmt(se), fmt(prior_price), fmt(diff)])
    return rows


def summarize_step(path_budget: int) -> list[list[str]]:
    rows = read_required_rows(
        REFERENCE_DIR / f"{CASE_ID}_step_sweep_all_ref1200_direct_samepaths{path_budget//1000}k_s24487296_table.csv",
        expected_rows=40,
    )
    selected = [
        row
        for row in rows
        if int(float(row["K"])) == 100 and int(row["euler_steps"]) in (48, 96)
    ]
    selected.sort(key=lambda row: (int(row["euler_steps"]), row["method"]))
    return [
        [
            str(path_budget),
            row["method"],
            row["euler_steps"],
            fmt(finite(row["price_direct"])),
            fmt(finite(row["se_direct"])),
            f"{100.0 * finite(row['rel_error_direct']):.3f}%",
        ]
        for row in selected
    ]


def summarize_path(euler_steps: int) -> list[list[str]]:
    path = PATH_REFERENCE_DIR / f"{CASE_ID}_path_sweep_k100_steps{euler_steps}_direct_ref1200_paths1200000_table.csv"
    rows = [
        row
        for row in read_required_rows(path, expected_rows=18)
        if int(row["paths"]) in (20_000, 60_000) and row["method"] in ("benchmark", "hybrid")
    ]
    rows.sort(key=lambda row: (int(row["paths"]), row["method"]))
    return [
        [
            str(euler_steps),
            row["method"],
            row["paths"],
            fmt(finite(row["price_direct"])),
            fmt(finite(row["se_direct"])),
            f"{100.0 * finite(row['rel_error_direct']):.3f}%",
        ]
        for row in rows
    ]


def git_info() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode == 0:
        return completed.stdout.strip()
    return "unavailable"


def require_full_rerun_inputs(config: dict[str, Any], validation: dict[str, Any]) -> None:
    if validation.get("status") != "pass":
        raise RuntimeError(f"Cannot write final report because validation status is {validation.get('status', 'missing')!r}.")
    required_files = [
        BENCHMARK_CSV,
        REFERENCE_DIR / f"{CASE_ID}_step_sweep_all_ref1200_direct_samepaths20k_s24487296_table.csv",
        REFERENCE_DIR / f"{CASE_ID}_step_sweep_all_ref1200_direct_samepaths60k_s24487296_table.csv",
        FIGURE_DIR / f"{CASE_ID}_path_sweep_steps48_direct_relative_error.pdf",
        FIGURE_DIR / f"{CASE_ID}_path_sweep_steps60_direct_relative_error.pdf",
        TABLE_DIR / f"{CASE_ID}_path_sweep_steps48_path20k_table.tex",
        TABLE_DIR / f"{CASE_ID}_appendix_price_tables.tex",
        METADATA_DIR / f"{CASE_ID}_asset_manifest.csv",
    ]
    for scenario in config["strikes"]:
        for euler_steps in config["path_sweep"]["steps"]:
            required_files.append(
                PATH_REFERENCE_DIR / f"{CASE_ID}_path_sweep_{scenario['slug']}_steps{euler_steps}_direct_ref1200_paths1200000_table.csv"
            )
    missing = [path for path in required_files if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing report inputs:\n" + "\n".join(str(path) for path in missing))


def main() -> None:
    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
    config = load_required_json(CONFIG_PATH)
    validation = load_required_json(VALIDATION_JSON)
    require_full_rerun_inputs(config, validation)
    metadata = load_json(METADATA_DIR / f"{CASE_ID}_metadata.json")
    lines: list[str] = []
    lines.append("# Sandbox Rerun Report: BGK Robustness Case")
    lines.append("")
    lines.append("This report summarizes the sandbox-only from-scratch rerun for the robustness case `bgk_r02_t1_delta05_nex12`. It is a verification artifact, not manuscript-ready prose.")
    lines.append("")
    lines.append("## Run Metadata")
    lines.extend(
        md_table(
            ["Item", "Value"],
            [
                ["Run root", str(RUN_ROOT)],
                ["Created", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                ["OS", platform.platform()],
                ["Python", sys.version.split()[0]],
                ["Git commit", git_info()],
                ["Case", config.get("case_id", CASE_ID)],
                ["Model", "`r=0.02`, `delta1=delta2=0.5`, `T=1`, `N_ex=12`"],
                ["Seeds", "`2026 / 2103`"],
                ["Validation", validation.get("status", "missing")],
            ],
        )
    )
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append("- Benchmark: LSMC, five strikes, `M=1200`, `N=1,200,000`.")
    lines.append("- Step sweep: paths `20,000` and `60,000`, steps `24,48,72,96`, LSMC and Hybrid.")
    lines.append("- Path sweep: steps `48` and `60`, paths `250` through `60,000`, LSMC and Hybrid.")
    lines.append("- Assets: Figure 5-style 48-step figure, 60-step companion figure, representative table, and appendix-style price tables.")
    lines.append("")
    lines.append("## Benchmark Comparison")
    lines.extend(md_table(["K", "Sandbox price", "Sandbox SE", "Prior manuscript price", "Difference"], compare_benchmark_rows()))
    lines.append("")
    lines.append("## Representative Step Sweep")
    step_rows = summarize_step(20_000) + summarize_step(60_000)
    lines.extend(md_table(["Paths", "Method", "M", "Price", "SE", "Rel. error"], step_rows))
    lines.append("")
    lines.append("## Representative Path Sweep")
    path_rows = summarize_path(48) + summarize_path(60)
    lines.extend(md_table(["M", "Method", "Paths", "Price", "SE", "Rel. error"], path_rows))
    lines.append("")
    lines.append("## Validation Summary")
    lines.append(f"Validation passed with `{validation.get('num_checks')}` checks.")
    lines.append("")
    lines.append("## Generated Assets")
    lines.append("")
    lines.append("- `figures/bgk_r02_t1_delta05_nex12_path_sweep_steps48_direct_relative_error.pdf`")
    lines.append("- `figures/bgk_r02_t1_delta05_nex12_path_sweep_steps60_direct_relative_error.pdf`")
    lines.append("- `tables/bgk_r02_t1_delta05_nex12_path_sweep_steps48_path20k_table.tex`")
    lines.append("- `tables/bgk_r02_t1_delta05_nex12_appendix_price_tables.tex`")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- All generated files are intended to stay under the sandbox root.")
    lines.append("- The new pricing engines are separate from the old `run_bgk_*` scripts; manuscript-source CSVs are read only for comparison.")
    lines.append("- Hybrid low-estimator values are retained only as diagnostic, legacy-compatible provenance; direct prices are the quantities used in tables, figures, and conclusions.")
    if metadata:
        lines.append(f"- Engine hashes are recorded in `{METADATA_DIR / (CASE_ID + '_metadata.json')}`.")
    lines.append("")
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"[report] wrote {REPORT_MD}")


if __name__ == "__main__":
    main()
