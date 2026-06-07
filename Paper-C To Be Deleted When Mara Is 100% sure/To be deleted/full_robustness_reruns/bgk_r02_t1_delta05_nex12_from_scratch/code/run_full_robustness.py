from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


RUN_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = RUN_ROOT / "config" / "rerun_config.json"
CODE_DIR = RUN_ROOT / "code"
RESULTS_DIR = RUN_ROOT / "results"
REFERENCE_DIR = RESULTS_DIR / "reference_values"
PATH_REFERENCE_DIR = REFERENCE_DIR / "path_sweep"
PLOT_DATA_DIR = RESULTS_DIR / "plot_data"
METADATA_DIR = RESULTS_DIR / "metadata"
VALIDATION_DIR = RESULTS_DIR / "validation"
LOG_DIR = RUN_ROOT / "logs" / "jobs"
SCRATCH_DIR = RUN_ROOT / "scratch"
FIGURES_DIR = RUN_ROOT / "figures"
TABLES_DIR = RUN_ROOT / "tables"
SUMMARY_DIR = RUN_ROOT / "summary"

LSMC_SCRIPT = CODE_DIR / "lsmc_from_scratch.py"
HYBRID_SCRIPT = CODE_DIR / "hybrid_from_scratch.py"
ASSET_SCRIPT = CODE_DIR / "build_assets.py"
VALIDATION_SCRIPT = CODE_DIR / "validate_outputs.py"
REPORT_SCRIPT = CODE_DIR / "write_report.py"

CASE_ID = "bgk_r02_t1_delta05_nex12"
BENCHMARK_CSV = REFERENCE_DIR / f"{CASE_ID}_benchmark_steps1200_paths1200000_table.csv"
STEP_CSVS = {
    20_000: REFERENCE_DIR / f"{CASE_ID}_step_sweep_all_ref1200_direct_samepaths20k_s24487296_table.csv",
    60_000: REFERENCE_DIR / f"{CASE_ID}_step_sweep_all_ref1200_direct_samepaths60k_s24487296_table.csv",
}
RUN_MANIFEST = METADATA_DIR / f"{CASE_ID}_run_manifest.csv"
METADATA_JSON = METADATA_DIR / f"{CASE_ID}_metadata.json"
SMOKE_CSV = RESULTS_DIR / "smoke.csv"

BENCHMARK_FIELDS = [
    "scenario",
    "S0",
    "K",
    "T",
    "r",
    "delta1",
    "delta2",
    "exercise_dates",
    "euler_steps",
    "lsmc_paths",
    "lsmc_low_paths",
    "seed",
    "low_seed",
    "benchmark_direct_price",
    "benchmark_direct_error",
    "benchmark_low_price",
    "benchmark_low_error",
    "benchmark_direct_low_gap",
    "runtime_seconds",
    "engine_sha256",
]

STEP_FIELDS = [
    "scenario",
    "K",
    "r",
    "delta1",
    "delta2",
    "exercise_dates",
    "euler_steps",
    "paths",
    "method",
    "seed",
    "low_seed",
    "low_paths",
    "runtime_seconds",
    "reference_direct_price",
    "price_direct",
    "se_direct",
    "ci_width_direct",
    "rel_error_direct",
    "rel_ci_lower_direct",
    "rel_ci_upper_direct",
    "engine_sha256",
]

PATH_FIELDS = [
    "scenario",
    "K",
    "r",
    "delta1",
    "delta2",
    "exercise_dates",
    "euler_steps",
    "paths",
    "method",
    "seed",
    "low_seed",
    "low_paths",
    "runtime_seconds",
    "reference_direct_price",
    "price_direct",
    "se_direct",
    "rel_error_direct",
    "rel_ci_lower_direct",
    "rel_ci_upper_direct",
    "engine_sha256",
]

MANIFEST_FIELDS = [
    "study",
    "scenario",
    "K",
    "euler_steps",
    "paths",
    "method",
    "output_path",
    "runtime_seconds",
]

SMOKE_FIELDS = [
    "method",
    "scenario",
    "K",
    "euler_steps",
    "paths",
    "low_paths",
    "seed",
    "low_seed",
    "price_direct",
    "se_direct",
    "r",
    "delta1",
    "delta2",
    "v0",
    "vp0",
    "T",
    "exercise_dates",
    "runtime_seconds",
    "engine_sha256",
    "scratch_path",
    "log_path",
]


def ensure_dirs() -> None:
    for path in (
        RESULTS_DIR,
        REFERENCE_DIR,
        PATH_REFERENCE_DIR,
        PLOT_DATA_DIR,
        METADATA_DIR,
        VALIDATION_DIR,
        LOG_DIR,
        SCRATCH_DIR,
        FIGURES_DIR,
        TABLES_DIR,
        SUMMARY_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)


def load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def file_hash(path: Path) -> str:
    if not path.exists():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def append_or_replace(
    path: Path,
    fieldnames: list[str],
    row: dict[str, Any],
    key_fields: tuple[str, ...],
    sort_fields: tuple[str, ...],
) -> None:
    rows = read_rows(path)
    rows = [old for old in rows if tuple(str(old.get(k, "")) for k in key_fields) != tuple(str(row.get(k, "")) for k in key_fields)]
    rows.append(row)
    rows.sort(key=lambda item: tuple(sort_value(item.get(field, "")) for field in sort_fields))
    write_rows(path, fieldnames, rows)


def sort_value(value: Any) -> Any:
    try:
        return float(value)
    except (TypeError, ValueError):
        return str(value)


def finite(value: Any) -> float:
    out = float(value)
    if not math.isfinite(out):
        raise RuntimeError(f"Non-finite value {value}")
    return out


def rel_error(value: float, reference: float) -> float:
    if abs(reference) <= 1e-16:
        return float("inf")
    return abs(value - reference) / abs(reference)


def ci_bounds(value: float, se: float) -> tuple[float, float]:
    return value - 1.96 * se, value + 1.96 * se


def rel_error_ci_bounds(value: float, se: float, reference: float) -> tuple[float, float]:
    low, high = ci_bounds(value, se)
    endpoint_errors = (rel_error(low, reference), rel_error(high, reference))
    if low <= reference <= high:
        return 0.0, max(endpoint_errors)
    return min(endpoint_errors), max(endpoint_errors)


def direct_low_gap(low: float, direct: float) -> float:
    if abs(direct) <= 1e-16:
        return float("inf")
    return abs(low - direct) / abs(direct)


def path_csv_path(slug: str, euler_steps: int) -> Path:
    return PATH_REFERENCE_DIR / f"{CASE_ID}_path_sweep_{slug}_steps{euler_steps}_direct_ref1200_paths1200000_table.csv"


def path_json_path(slug: str, euler_steps: int) -> Path:
    return PATH_REFERENCE_DIR / f"{CASE_ID}_path_sweep_{slug}_steps{euler_steps}_direct_ref1200_paths1200000_table.json"


def write_metadata(config: dict[str, Any]) -> None:
    metadata = {
        "case_id": config["case_id"],
        "run_root": str(RUN_ROOT),
        "sandbox_only": True,
        "model_env": config["model_env"],
        "seeds": config["seeds"],
        "hybrid_env": config["hybrid_env"],
        "benchmark": config["benchmark"],
        "step_sweep": config["step_sweep"],
        "path_sweep": config["path_sweep"],
        "engines": {
            "lsmc": str(LSMC_SCRIPT),
            "hybrid": str(HYBRID_SCRIPT),
            "lsmc_sha256": file_hash(LSMC_SCRIPT),
            "hybrid_sha256": file_hash(HYBRID_SCRIPT),
        },
        "created_by": "from-scratch sandbox rerun",
    }
    METADATA_JSON.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def append_manifest(row: dict[str, Any]) -> None:
    append_or_replace(
        RUN_MANIFEST,
        MANIFEST_FIELDS,
        row,
        key_fields=("study", "scenario", "euler_steps", "paths", "method"),
        sort_fields=("study", "K", "euler_steps", "paths", "method"),
    )


def method_script(method: str) -> Path:
    if method == "benchmark":
        return LSMC_SCRIPT
    if method == "hybrid":
        return HYBRID_SCRIPT
    raise ValueError(method)


def method_env_prefix(method: str) -> str:
    return "GDMR_LSMC" if method == "benchmark" else "GDMR_HYBRID"


def job_id(method: str, strike: float, euler_steps: int, paths: int) -> str:
    return f"{method}_K{int(strike)}_M{euler_steps}_N{paths}"


def job_scratch_path(method: str, strike: float, euler_steps: int, paths: int) -> Path:
    return SCRATCH_DIR / job_id(method, strike, euler_steps, paths)


def job_log_path(method: str, strike: float, euler_steps: int, paths: int) -> Path:
    return LOG_DIR / f"{job_id(method, strike, euler_steps, paths)}.log"


def run_engine(config: dict[str, Any], method: str, strike: float, euler_steps: int, paths: int, low_paths: int) -> tuple[dict[str, Any], float, str]:
    script = method_script(method)
    if not script.exists():
        raise FileNotFoundError(f"Missing from-scratch engine: {script}")
    prefix = method_env_prefix(method)
    env = os.environ.copy()
    env.update(config["model_env"])
    if method == "hybrid":
        env.update(config["hybrid_env"])
    env.update(
        {
            "GDMR_STRIKE": f"{strike:.1f}",
            "GDMR_EULER_STEPS": str(euler_steps),
            f"{prefix}_PATHS": str(paths),
            f"{prefix}_LOW_PATHS": str(low_paths),
            f"{prefix}_SEED": config["seeds"]["direct"],
            f"{prefix}_LOW_SEED": config["seeds"]["low"],
        }
    )
    scratch = job_scratch_path(method, strike, euler_steps, paths)
    scratch.mkdir(parents=True, exist_ok=True)
    env[f"{prefix}_STORE_DIR"] = str(scratch)
    log_path = job_log_path(method, strike, euler_steps, paths)
    start = time.perf_counter()
    completed = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(CODE_DIR),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    runtime = time.perf_counter() - start
    log_path.write_text(
        "COMMAND: "
        + " ".join([sys.executable, str(script)])
        + "\n\nSTDOUT:\n"
        + completed.stdout
        + "\n\nSTDERR:\n"
        + completed.stderr
        + f"\n\nEXIT_CODE: {completed.returncode}\nRUNTIME_SECONDS: {runtime:.6f}\n",
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise RuntimeError(f"{method} failed for K={strike:.0f}, M={euler_steps}, N={paths}. See {log_path}")
    result_line = None
    for line in reversed(completed.stdout.splitlines()):
        if line.startswith("RESULT_JSON: "):
            result_line = line[len("RESULT_JSON: ") :]
            break
    if result_line is None:
        raise RuntimeError(f"Missing RESULT_JSON in {log_path}")
    result = json.loads(result_line)
    assert_case_result(config, result, method, strike, euler_steps, paths, low_paths)
    return result, runtime, file_hash(script)


def assert_case_result(
    config: dict[str, Any],
    result: dict[str, Any],
    method: str,
    strike: float,
    euler_steps: int,
    paths: int,
    low_paths: int,
) -> None:
    expected_float = {
        "r": float(config["model_env"]["GDMR_R"]),
        "delta1": float(config["model_env"]["GDMR_DELTA1"]),
        "delta2": float(config["model_env"]["GDMR_DELTA2"]),
        "v0": float(config["model_env"]["GDMR_V0"]),
        "vp0": float(config["model_env"]["GDMR_VP0"]),
        "T": float(config["model_env"]["GDMR_MATURITY"]),
        "K": strike,
    }
    for key, expected in expected_float.items():
        actual = finite(result[key])
        if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-12):
            raise RuntimeError(f"{method} returned unexpected {key}: {actual}, expected {expected}")
    if int(result["exercise_dates"]) != int(config["model_env"]["GDMR_EXERCISE_DATES"]):
        raise RuntimeError(f"{method} returned unexpected exercise_dates: {result['exercise_dates']}")
    if int(result["euler_steps"]) != euler_steps:
        raise RuntimeError(f"{method} returned unexpected euler_steps: {result['euler_steps']}")
    if int(result["paths"]) != paths:
        raise RuntimeError(f"{method} returned unexpected paths: {result['paths']}")
    if int(result["low_paths"]) != low_paths:
        raise RuntimeError(f"{method} returned unexpected low_paths: {result['low_paths']}")


def direct_price_and_se(method: str, result: dict[str, Any]) -> tuple[float, float, float, float]:
    if method == "benchmark":
        return (
            finite(result["lsmc_direct_price"]),
            finite(result["lsmc_direct_error"]),
            finite(result["lsmc_low_price"]),
            finite(result["lsmc_low_error"]),
        )
    return (
        finite(result["hybrid_direct_price"]),
        finite(result["hybrid_direct_error"]),
        finite(result["hybrid_low_price"]),
        finite(result["hybrid_low_error"]),
    )


def benchmark_lookup() -> dict[str, dict[str, float]]:
    rows = read_rows(BENCHMARK_CSV)
    lookup: dict[str, dict[str, float]] = {}
    for row in rows:
        lookup[row["scenario"]] = {
            "K": finite(row["K"]),
            "price": finite(row["benchmark_direct_price"]),
            "se": finite(row["benchmark_direct_error"]),
        }
    return lookup


def run_smoke(config: dict[str, Any], force: bool) -> None:
    rows = [] if force else read_rows(SMOKE_CSV)
    existing = {(row["method"], int(row["K"])) for row in rows}
    strike = float(config["smoke"]["strike"])
    for method, paths_key in (("benchmark", "lsmc_paths"), ("hybrid", "hybrid_paths")):
        key = (method, int(strike))
        if key in existing and not force:
            print(f"[smoke] skip {method}", flush=True)
            continue
        paths = int(config["smoke"][paths_key])
        result, runtime, engine_sha = run_engine(
            config,
            method,
            strike,
            int(config["smoke"]["euler_steps"]),
            paths,
            min(paths, 100),
        )
        price, se, _, _ = direct_price_and_se(method, result)
        row = {
            "method": method,
            "scenario": "ATM",
            "K": int(strike),
            "euler_steps": int(result["euler_steps"]),
            "paths": int(result["paths"]),
            "low_paths": int(result["low_paths"]),
            "seed": int(result["seed"]),
            "low_seed": int(result["low_seed"]),
            "price_direct": f"{price:.12f}",
            "se_direct": f"{se:.12f}",
            "r": result["r"],
            "delta1": result["delta1"],
            "delta2": result["delta2"],
            "v0": result["v0"],
            "vp0": result["vp0"],
            "T": result["T"],
            "exercise_dates": result["exercise_dates"],
            "runtime_seconds": f"{runtime:.6f}",
            "engine_sha256": engine_sha,
            "scratch_path": str(job_scratch_path(method, strike, int(config["smoke"]["euler_steps"]), paths)),
            "log_path": str(job_log_path(method, strike, int(config["smoke"]["euler_steps"]), paths)),
        }
        rows = [old for old in rows if (old["method"], int(old["K"])) != key]
        rows.append(row)
        rows.sort(key=lambda item: item["method"])
        write_rows(SMOKE_CSV, SMOKE_FIELDS, rows)


def run_benchmark(config: dict[str, Any], force: bool) -> None:
    rows = [] if force else read_rows(BENCHMARK_CSV)
    existing = {row["scenario"] for row in rows}
    spec = config["benchmark"]
    for scenario in config["strikes"]:
        name = scenario["scenario"]
        strike = float(scenario["K"])
        if name in existing and not force:
            print(f"[benchmark] skip {name}", flush=True)
            continue
        print(f"[benchmark] run {name}", flush=True)
        result, runtime, engine_sha = run_engine(
            config,
            "benchmark",
            strike,
            int(spec["euler_steps"]),
            int(spec["paths"]),
            int(spec["low_paths"]),
        )
        direct, direct_se, low, low_se = direct_price_and_se("benchmark", result)
        row = {
            "scenario": name,
            "S0": f"{finite(result['S0']):.1f}",
            "K": f"{finite(result['K']):.1f}",
            "T": f"{finite(result['T']):.1f}",
            "r": result["r"],
            "delta1": result["delta1"],
            "delta2": result["delta2"],
            "exercise_dates": int(result["exercise_dates"]),
            "euler_steps": int(result["euler_steps"]),
            "lsmc_paths": int(result["paths"]),
            "lsmc_low_paths": int(result["low_paths"]),
            "seed": int(result["seed"]),
            "low_seed": int(result["low_seed"]),
            "benchmark_direct_price": f"{direct:.6f}",
            "benchmark_direct_error": f"{direct_se:.6f}",
            "benchmark_low_price": f"{low:.6f}",
            "benchmark_low_error": f"{low_se:.6f}",
            "benchmark_direct_low_gap": f"{direct_low_gap(low, direct):.15g}",
            "runtime_seconds": f"{runtime:.6f}",
            "engine_sha256": engine_sha,
        }
        rows = [old for old in rows if old["scenario"] != name]
        rows.append(row)
        rows.sort(key=lambda item: finite(item["K"]))
        write_rows(BENCHMARK_CSV, BENCHMARK_FIELDS, rows)
        append_manifest(
            {
                "study": "benchmark",
                "scenario": name,
                "K": int(strike),
                "euler_steps": int(result["euler_steps"]),
                "paths": int(result["paths"]),
                "method": "benchmark",
                "output_path": str(BENCHMARK_CSV),
                "runtime_seconds": f"{runtime:.6f}",
            }
        )


def run_step_sweep(config: dict[str, Any], force: bool) -> None:
    lookup = benchmark_lookup()
    if len(lookup) != len(config["strikes"]):
        raise RuntimeError("Benchmark references are incomplete; run benchmark first.")
    for path_budget in config["step_sweep"]["paths"]:
        output_path = STEP_CSVS[int(path_budget)]
        rows = [] if force else read_rows(output_path)
        existing = {(row["scenario"], int(row["euler_steps"]), row["method"]) for row in rows}
        for scenario in config["strikes"]:
            name = scenario["scenario"]
            strike = float(scenario["K"])
            reference = lookup[name]["price"]
            for euler_steps in config["step_sweep"]["steps"]:
                for method in config["step_sweep"]["methods"]:
                    key = (name, int(euler_steps), method)
                    if key in existing and not force:
                        print(f"[step {path_budget}] skip {name} M={euler_steps} {method}", flush=True)
                        continue
                    print(f"[step {path_budget}] run {name} M={euler_steps} {method}", flush=True)
                    result, runtime, engine_sha = run_engine(
                        config,
                        method,
                        strike,
                        int(euler_steps),
                        int(path_budget),
                        min(int(path_budget), 1000),
                    )
                    price, se, _, _ = direct_price_and_se(method, result)
                    rel_low, rel_high = rel_error_ci_bounds(price, se, reference)
                    row = {
                        "scenario": name,
                        "K": f"{strike:.1f}",
                        "r": result["r"],
                        "delta1": result["delta1"],
                        "delta2": result["delta2"],
                        "exercise_dates": int(result["exercise_dates"]),
                        "euler_steps": int(euler_steps),
                        "paths": int(path_budget),
                        "method": method,
                        "seed": int(result["seed"]),
                        "low_seed": int(result["low_seed"]),
                        "low_paths": int(result["low_paths"]),
                        "runtime_seconds": f"{runtime:.12g}",
                        "reference_direct_price": f"{reference:.6f}",
                        "price_direct": f"{price:.12f}",
                        "se_direct": f"{se:.12f}",
                        "ci_width_direct": f"{(3.92 * se):.12f}",
                        "rel_error_direct": f"{rel_error(price, reference):.12f}",
                        "rel_ci_lower_direct": f"{rel_low:.12f}",
                        "rel_ci_upper_direct": f"{rel_high:.12f}",
                        "engine_sha256": engine_sha,
                    }
                    append_or_replace(
                        output_path,
                        STEP_FIELDS,
                        row,
                        key_fields=("scenario", "euler_steps", "method"),
                        sort_fields=("K", "euler_steps", "method"),
                    )
                    append_manifest(
                        {
                            "study": f"step_{path_budget}",
                            "scenario": name,
                            "K": int(strike),
                            "euler_steps": int(euler_steps),
                            "paths": int(path_budget),
                            "method": method,
                            "output_path": str(output_path),
                            "runtime_seconds": f"{runtime:.6f}",
                        }
                    )


def run_path_sweep(config: dict[str, Any], force: bool) -> None:
    lookup = benchmark_lookup()
    if len(lookup) != len(config["strikes"]):
        raise RuntimeError("Benchmark references are incomplete; run benchmark first.")
    for scenario in config["strikes"]:
        name = scenario["scenario"]
        strike = float(scenario["K"])
        slug = scenario["slug"]
        reference = lookup[name]["price"]
        for euler_steps in config["path_sweep"]["steps"]:
            output_path = path_csv_path(slug, int(euler_steps))
            if force and output_path.exists():
                output_path.unlink()
            for paths in config["path_sweep"]["paths"]:
                for method in config["path_sweep"]["methods"]:
                    existing = {
                        (int(row["paths"]), row["method"])
                        for row in read_rows(output_path)
                    }
                    key = (int(paths), method)
                    if key in existing and not force:
                        print(f"[path {euler_steps}] skip {name} paths={paths} {method}", flush=True)
                        continue
                    print(f"[path {euler_steps}] run {name} paths={paths} {method}", flush=True)
                    result, runtime, engine_sha = run_engine(
                        config,
                        method,
                        strike,
                        int(euler_steps),
                        int(paths),
                        min(int(paths), 1000),
                    )
                    price, se, _, _ = direct_price_and_se(method, result)
                    rel_low, rel_high = rel_error_ci_bounds(price, se, reference)
                    row = {
                        "scenario": name,
                        "K": f"{strike:.0f}",
                        "r": result["r"],
                        "delta1": result["delta1"],
                        "delta2": result["delta2"],
                        "exercise_dates": int(result["exercise_dates"]),
                        "euler_steps": int(euler_steps),
                        "paths": int(paths),
                        "method": method,
                        "seed": int(result["seed"]),
                        "low_seed": int(result["low_seed"]),
                        "low_paths": int(result["low_paths"]),
                        "runtime_seconds": f"{runtime:.12g}",
                        "reference_direct_price": f"{reference:.6f}",
                        "price_direct": f"{price:.12f}",
                        "se_direct": f"{se:.12f}",
                        "rel_error_direct": f"{rel_error(price, reference):.12f}",
                        "rel_ci_lower_direct": f"{rel_low:.12f}",
                        "rel_ci_upper_direct": f"{rel_high:.12f}",
                        "engine_sha256": engine_sha,
                    }
                    append_or_replace(
                        output_path,
                        PATH_FIELDS,
                        row,
                        key_fields=("paths", "method"),
                        sort_fields=("paths", "method"),
                    )
                    append_manifest(
                        {
                            "study": f"path_{euler_steps}",
                            "scenario": name,
                            "K": int(strike),
                            "euler_steps": int(euler_steps),
                            "paths": int(paths),
                            "method": method,
                            "output_path": str(output_path),
                            "runtime_seconds": f"{runtime:.6f}",
                        }
                    )
            path_json_path(slug, int(euler_steps)).write_text(
                json.dumps(
                    {
                        "case_id": CASE_ID,
                        "scenario": name,
                        "strike": int(strike),
                        "euler_steps": int(euler_steps),
                        "path_grid": config["path_sweep"]["paths"],
                        "methods": config["path_sweep"]["methods"],
                        "reference_direct_price": reference,
                        "model_env": config["model_env"],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )


def run_script(script: Path, *args: str) -> None:
    if not script.exists():
        raise FileNotFoundError(script)
    completed = subprocess.run(
        [sys.executable, str(script), *args],
        cwd=str(CODE_DIR),
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"{script.name} failed with exit code {completed.returncode}")


def clear_outputs() -> None:
    for path in (BENCHMARK_CSV, RUN_MANIFEST, METADATA_JSON, SMOKE_CSV):
        if path.exists():
            path.unlink()
    for path in STEP_CSVS.values():
        if path.exists():
            path.unlink()
    for path in PATH_REFERENCE_DIR.glob(f"{CASE_ID}_path_sweep_*"):
        path.unlink()
    for path in PLOT_DATA_DIR.glob(f"{CASE_ID}_*"):
        if path.is_file():
            path.unlink()
    for path in FIGURES_DIR.glob(f"{CASE_ID}_*"):
        if path.is_file():
            path.unlink()
    for path in TABLES_DIR.glob(f"{CASE_ID}_*"):
        if path.is_file():
            path.unlink()
    for path in VALIDATION_DIR.glob("*"):
        if path.is_file():
            path.unlink()
    for path in SUMMARY_DIR.glob("sandbox_rerun_report_*.md"):
        if path.is_file():
            path.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the from-scratch robustness sandbox rerun.")
    parser.add_argument("--mode", choices=["smoke", "benchmark", "step", "path", "assets", "validate", "report", "full"], default="full")
    parser.add_argument("--force", action="store_true", help="Replace existing output rows/files for selected mode.")
    args = parser.parse_args()

    ensure_dirs()
    config = load_config()
    if args.force and args.mode == "full":
        clear_outputs()
    write_metadata(config)

    if args.mode in ("smoke", "full"):
        run_smoke(config, force=args.force)
    if args.mode in ("benchmark", "full"):
        run_benchmark(config, force=args.force)
    if args.mode in ("step", "full"):
        run_step_sweep(config, force=args.force)
    if args.mode in ("path", "full"):
        run_path_sweep(config, force=args.force)
    if args.mode in ("assets", "full"):
        run_script(ASSET_SCRIPT)
    if args.mode in ("validate", "full"):
        run_script(VALIDATION_SCRIPT)
    if args.mode in ("report", "full"):
        run_script(REPORT_SCRIPT)


if __name__ == "__main__":
    main()
