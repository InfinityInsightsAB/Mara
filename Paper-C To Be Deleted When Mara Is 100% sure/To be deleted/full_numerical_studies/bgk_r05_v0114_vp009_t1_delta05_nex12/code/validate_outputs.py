from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any


RUN_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = RUN_ROOT / "config" / "rerun_config.json"
RESULTS_DIR = RUN_ROOT / "results"
REFERENCE_DIR = RESULTS_DIR / "reference_values"
PATH_REFERENCE_DIR = REFERENCE_DIR / "path_sweep"
PLOT_DATA_DIR = RESULTS_DIR / "plot_data"
METADATA_DIR = RESULTS_DIR / "metadata"
VALIDATION_DIR = RESULTS_DIR / "validation"
TABLE_DIR = RUN_ROOT / "tables"
FIGURE_DIR = RUN_ROOT / "figures"
SUMMARY_DIR = RUN_ROOT / "summary"
TEX_DIR = RUN_ROOT / "tex"


def configured_case_id() -> str:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))["case_id"]


CASE_ID = configured_case_id()
BENCHMARK_CSV = REFERENCE_DIR / f"{CASE_ID}_benchmark_steps1200_paths1200000_table.csv"
RUN_MANIFEST = METADATA_DIR / f"{CASE_ID}_run_manifest.csv"
ASSET_MANIFEST = METADATA_DIR / f"{CASE_ID}_asset_manifest.csv"
SMOKE_CSV = RESULTS_DIR / "smoke.csv"
VALIDATION_JSON = VALIDATION_DIR / "validation_summary.json"
VALIDATION_CSV = VALIDATION_DIR / "validation_checks.csv"


def load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise AssertionError(f"Missing required file: {path}")
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def finite(value: Any) -> float:
    out = float(value)
    if not math.isfinite(out):
        raise AssertionError(f"Non-finite value: {value}")
    return out


def rel_error(value: float, reference: float) -> float:
    if abs(reference) <= 1e-16:
        return float("inf")
    return abs(value - reference) / abs(reference)


def rel_error_ci_bounds(price: float, se: float, reference: float) -> tuple[float, float]:
    low = price - 1.96 * se
    high = price + 1.96 * se
    endpoints = (rel_error(low, reference), rel_error(high, reference))
    if low <= reference <= high:
        return 0.0, max(endpoints)
    return min(endpoints), max(endpoints)


def check(condition: bool, name: str, details: str, rows: list[dict[str, str]]) -> None:
    status = "pass" if condition else "fail"
    rows.append({"check": name, "status": status, "details": details})
    if not condition:
        raise AssertionError(f"{name}: {details}")


def path_under_run_root(path_text: str) -> bool:
    if not path_text:
        return True
    try:
        path = Path(path_text)
        if not path.is_absolute():
            path = (RUN_ROOT / path).resolve()
        else:
            path = path.resolve()
        return path == RUN_ROOT.resolve() or RUN_ROOT.resolve() in path.parents
    except OSError:
        return False


def benchmark_lookup(rows: list[dict[str, str]]) -> dict[str, float]:
    return {row["scenario"]: finite(row["benchmark_direct_price"]) for row in rows}


def validate_case_row(row: dict[str, str], config: dict[str, Any]) -> None:
    expected = {
        "S0": float(config["model_env"]["GDMR_S0"]),
        "T": float(config["model_env"]["GDMR_MATURITY"]),
        "r": float(config["model_env"]["GDMR_R"]),
        "v0": float(config["model_env"]["GDMR_V0"]),
        "vp0": float(config["model_env"]["GDMR_VP0"]),
        "kappa1": float(config["model_env"]["GDMR_KAPPA1"]),
        "kappa2": float(config["model_env"]["GDMR_KAPPA2"]),
        "theta": float(config["model_env"]["GDMR_THETA"]),
        "xi1": float(config["model_env"]["GDMR_XI1"]),
        "xi2": float(config["model_env"]["GDMR_XI2"]),
        "rho12": float(config["model_env"]["GDMR_RHO12"]),
        "rho13": float(config["model_env"]["GDMR_RHO13"]),
        "rho23": float(config["model_env"]["GDMR_RHO23"]),
        "delta1": float(config["model_env"]["GDMR_DELTA1"]),
        "delta2": float(config["model_env"]["GDMR_DELTA2"]),
        "exercise_dates": float(config["model_env"]["GDMR_EXERCISE_DATES"]),
    }
    for key, value in expected.items():
        if key not in row or row[key] == "":
            raise AssertionError(f"Missing required model field: {key}")
        actual = finite(row[key])
        if not math.isclose(actual, value, rel_tol=0.0, abs_tol=1e-12):
            raise AssertionError(f"Unexpected {key}: {actual} != {value}")


def validate_rel_row(row: dict[str, str], reference: float, tolerance: float = 5e-10) -> None:
    price = finite(row["price_direct"])
    se = finite(row["se_direct"])
    if price < 0 or se < 0:
        raise AssertionError("negative price or SE")
    expected = rel_error(price, reference)
    actual = finite(row["rel_error_direct"])
    if abs(expected - actual) > tolerance:
        raise AssertionError(f"relative error mismatch {actual} vs {expected}")
    rel_low, rel_high = rel_error_ci_bounds(price, se, reference)
    if "rel_ci_lower_direct" not in row or row["rel_ci_lower_direct"] == "":
        raise AssertionError("missing relative CI lower bound")
    if "rel_ci_upper_direct" not in row or row["rel_ci_upper_direct"] == "":
        raise AssertionError("missing relative CI upper bound")
    if abs(finite(row["rel_ci_lower_direct"]) - rel_low) > tolerance:
        raise AssertionError("relative CI lower mismatch")
    if abs(finite(row["rel_ci_upper_direct"]) - rel_high) > tolerance:
        raise AssertionError("relative CI upper mismatch")


def split_path_field(value: str) -> list[str]:
    return [part for part in value.split(";") if part.strip()]


def path_exists(path_text: str) -> bool:
    path = Path(path_text)
    if not path.is_absolute():
        path = RUN_ROOT / path
    return path.exists()


def path_csv_path(slug: str, euler_steps: int) -> Path:
    return PATH_REFERENCE_DIR / f"{CASE_ID}_path_sweep_{slug}_steps{euler_steps}_direct_ref1200_paths1200000_table.csv"


def step_csv_path(paths: int) -> Path:
    return REFERENCE_DIR / f"{CASE_ID}_step_sweep_all_ref1200_direct_samepaths{paths//1000}k_s24487296_table.csv"


def validate() -> dict[str, Any]:
    config = load_config()
    checks: list[dict[str, str]] = []
    check(config["case_id"] == CASE_ID, "config case id", config["case_id"], checks)

    metadata_path = METADATA_DIR / f"{CASE_ID}_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    check(metadata.get("case_id") == CASE_ID, "metadata case id", str(metadata.get("case_id")), checks)
    for field, expected in config["model_env"].items():
        check(str(metadata.get("model_env", {}).get(field)) == str(expected), f"metadata {field}", str(metadata.get("model_env", {}).get(field)), checks)

    smoke_rows = read_rows(SMOKE_CSV)
    check(len(smoke_rows) == 2, "smoke row count", f"{len(smoke_rows)} rows", checks)
    for row in smoke_rows:
        validate_case_row(row, config)
        check(int(row["low_paths"]) == 100, "smoke low path policy", row["low_paths"], checks)
        check(int(row["seed"]) == int(config["seeds"]["direct"]), "smoke direct seed", row["seed"], checks)
        check(int(row["low_seed"]) == int(config["seeds"]["low"]), "smoke low seed", row["low_seed"], checks)
        for field in ("scratch_path", "log_path"):
            check(path_under_run_root(row[field]), f"smoke {field} under sandbox", row[field], checks)
            check(path_exists(row[field]), f"smoke {field} exists", row[field], checks)

    benchmark_rows = read_rows(BENCHMARK_CSV)
    check(len(benchmark_rows) == 5, "benchmark row count", f"{len(benchmark_rows)} rows", checks)
    expected_strikes = {int(item["K"]) for item in config["strikes"]}
    got_strikes = {int(float(row["K"])) for row in benchmark_rows}
    check(got_strikes == expected_strikes, "benchmark strikes", str(got_strikes), checks)
    for row in benchmark_rows:
        validate_case_row(row, config)
        check(int(row["euler_steps"]) == int(config["benchmark"]["euler_steps"]), "benchmark M", row["euler_steps"], checks)
        check(int(row["lsmc_paths"]) == int(config["benchmark"]["paths"]), "benchmark paths", row["lsmc_paths"], checks)
        check(int(row["lsmc_low_paths"]) == int(config["benchmark"]["low_paths"]), "benchmark low paths", row["lsmc_low_paths"], checks)
        finite(row["benchmark_direct_price"])
        finite(row["benchmark_direct_error"])
        finite(row["benchmark_low_price"])
        finite(row["benchmark_low_error"])

    lookup = benchmark_lookup(benchmark_rows)
    for path_budget in config["step_sweep"]["paths"]:
        rows = read_rows(step_csv_path(int(path_budget)))
        check(len(rows) == 40, f"step rows {path_budget}", f"{len(rows)} rows", checks)
        keys = {(int(float(row["K"])), int(row["euler_steps"]), row["method"]) for row in rows}
        expected = {
            (int(item["K"]), int(step), method)
            for item in config["strikes"]
            for step in config["step_sweep"]["steps"]
            for method in config["step_sweep"]["methods"]
        }
        check(keys == expected, f"step grid {path_budget}", f"{len(keys)} keys", checks)
        for row in rows:
            validate_case_row(row, config)
            check(int(row["paths"]) == int(path_budget), "step path budget", row["paths"], checks)
            check(int(row["low_paths"]) == min(int(path_budget), 1000), "step low path policy", row["low_paths"], checks)
            ref = lookup[row["scenario"]]
            if not math.isclose(finite(row["reference_direct_price"]), ref, rel_tol=0.0, abs_tol=5e-7):
                raise AssertionError("step reference mismatch")
            validate_rel_row(row, ref)

    for scenario in config["strikes"]:
        for euler_steps in config["path_sweep"]["steps"]:
            sidecar = PATH_REFERENCE_DIR / f"{CASE_ID}_path_sweep_{scenario['slug']}_steps{euler_steps}_direct_ref1200_paths1200000_table.json"
            sidecar_data = json.loads(sidecar.read_text(encoding="utf-8"))
            check(sidecar_data.get("case_id") == CASE_ID, f"path JSON case id {scenario['slug']} {euler_steps}", str(sidecar_data.get("case_id")), checks)
            check(sidecar_data.get("model_env") == config["model_env"], f"path JSON model env {scenario['slug']} {euler_steps}", str(sidecar_data.get("model_env")), checks)
            rows = read_rows(path_csv_path(scenario["slug"], int(euler_steps)))
            check(len(rows) == 18, f"path rows {scenario['slug']} {euler_steps}", f"{len(rows)} rows", checks)
            keys = {(int(row["paths"]), row["method"]) for row in rows}
            expected = {
                (int(paths), method)
                for paths in config["path_sweep"]["paths"]
                for method in config["path_sweep"]["methods"]
            }
            check(keys == expected, f"path grid {scenario['slug']} {euler_steps}", f"{len(keys)} keys", checks)
            ref = lookup[scenario["scenario"]]
            for row in rows:
                validate_case_row(row, config)
                check(int(row["low_paths"]) == min(int(row["paths"]), 1000), "path low path policy", row["low_paths"], checks)
                if not math.isclose(finite(row["reference_direct_price"]), ref, rel_tol=0.0, abs_tol=5e-7):
                    raise AssertionError("path reference mismatch")
                validate_rel_row(row, ref)

    for manifest_path in (RUN_MANIFEST, ASSET_MANIFEST):
        rows = read_rows(manifest_path)
        check(len(rows) > 0, f"{manifest_path.name} nonempty", f"{len(rows)} rows", checks)
        for row in rows:
            if "destination_path" in row and row["destination_path"]:
                check(CASE_ID in Path(row["destination_path"]).name or row["kind"] in {"table"}, "asset case id", row["destination_path"], checks)
            for field in ("output_path", "destination_path", "source_path"):
                if field in row and row[field]:
                    for path_text in split_path_field(row[field]):
                        check(path_under_run_root(path_text), f"{field} under sandbox", path_text, checks)
                        if field in ("output_path", "destination_path", "source_path"):
                            check(path_exists(path_text), f"{field} exists", path_text, checks)

    expected_figures = {
        FIGURE_DIR / f"{CASE_ID}_path_sweep_steps{step}_direct_relative_error.{ext}"
        for step in config["path_sweep"]["steps"]
        for ext in ("pdf", "png", "eps")
    }
    expected_figures.update(
        FIGURE_DIR / f"{CASE_ID}_step_sweep_{int(path_budget)//1000}k_direct_relative_error.{ext}"
        for path_budget in config["step_sweep"]["paths"]
        for ext in ("pdf", "png", "eps")
    )
    for figure in expected_figures:
        check(figure.exists(), f"expected figure exists {figure.name}", str(figure), checks)
        check(figure.stat().st_size > 1000, f"figure nonempty {figure.name}", str(figure.stat().st_size), checks)

    expected_tables = {
        TABLE_DIR / f"{CASE_ID}_experimental_setting_table.tex",
        TABLE_DIR / f"{CASE_ID}_benchmark_reference_table.tex",
        TABLE_DIR / f"{CASE_ID}_step_sweep_20k_step72_table.tex",
        TABLE_DIR / f"{CASE_ID}_step_sweep_60k_step72_table.tex",
        TABLE_DIR / f"{CASE_ID}_path_sweep_steps48_path20k_table.tex",
        TABLE_DIR / f"{CASE_ID}_path_sweep_steps60_path20k_table.tex",
        TABLE_DIR / f"{CASE_ID}_appendix_price_tables.tex",
    }
    for table in expected_tables:
        check(table.exists(), f"expected table exists {table.name}", str(table), checks)
        check(table.stat().st_size > 100, f"table nonempty {table.name}", str(table.stat().st_size), checks)

    generated_case_files = (
        list(REFERENCE_DIR.glob("*.csv"))
        + list(PATH_REFERENCE_DIR.glob("*.csv"))
        + list(PATH_REFERENCE_DIR.glob("*.json"))
        + list(PLOT_DATA_DIR.glob("*.csv"))
        + list(FIGURE_DIR.glob("*"))
        + list(TABLE_DIR.glob("*.tex"))
    )
    for artifact in generated_case_files:
        if artifact.is_file() and artifact.suffix.lower() in {".csv", ".pdf", ".png", ".eps", ".tex", ".json"}:
            check(CASE_ID in artifact.name, "no mixed-case artifact", artifact.name, checks)
    forbidden_text = (
        "bgk_r02_calibrated_t1_nex12",
        "bgk_r03_v004",
        "bgk_r02_t1_delta05_nex12",
        "calibrated positive-rate",
        '"GDMR_R": "0"',
        '"GDMR_R": "0.00"',
        '"GDMR_R": "0.02"',
        '"GDMR_R": "0.03"',
        '"GDMR_VP0": "0.110"',
        '"GDMR_KAPPA1": "5.5"',
        '"GDMR_THETA": "0.078"',
        '"GDMR_XI1": "2.689"',
        '"GDMR_DELTA1": "0.94"',
        '"GDMR_DELTA2": "0.94"',
        '"GDMR_RHO12": "-0.982"',
        '"GDMR_V0": "0.04"',
        '"GDMR_R": "0.0"',
        r"\(r=0\)",
        r"$r=0$",
        "$r$ & 0 \\\\",
        "$r$ & 0.00 \\\\",
        "$r$ & 0.02 \\\\",
        "$r$ & 0.03 \\\\",
        "$\\delta_1$ & 0.94 \\\\",
        "$\\delta_2$ & 0.94 \\\\",
    )
    text_artifacts = (
        list(REFERENCE_DIR.glob("*.csv"))
        + list(PATH_REFERENCE_DIR.glob("*.csv"))
        + list(PATH_REFERENCE_DIR.glob("*.json"))
        + list(PLOT_DATA_DIR.glob("*.csv"))
        + list(TABLE_DIR.glob("*.tex"))
        + [metadata_path]
    )
    optional_text_artifacts = [
        SUMMARY_DIR / f"{CASE_ID}_sandbox_rerun_report_20260504.md",
        TEX_DIR / f"main_numerical_study_{CASE_ID}.tex",
    ]
    text_artifacts += [path for path in optional_text_artifacts if path.exists()]
    for artifact in text_artifacts:
        content = artifact.read_text(encoding="utf-8", errors="ignore")
        hits = [token for token in forbidden_text if token in content]
        check(not hits, f"no stale tokens {artifact.name}", ",".join(hits), checks)

    return {
        "status": "pass",
        "run_root": str(RUN_ROOT),
        "checks": checks,
        "num_checks": len(checks),
    }


def main() -> None:
    VALIDATION_DIR.mkdir(parents=True, exist_ok=True)
    try:
        summary = validate()
    except Exception as exc:
        summary = {"status": "fail", "run_root": str(RUN_ROOT), "error": str(exc)}
        VALIDATION_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        raise
    VALIDATION_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_rows(VALIDATION_CSV, ["check", "status", "details"], summary["checks"])
    print(f"[validate] {summary['status']} with {summary['num_checks']} checks")


if __name__ == "__main__":
    main()
