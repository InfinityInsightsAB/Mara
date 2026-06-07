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

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
ENGINE_DIR = ROOT / "engine"
RESULTS_DIR = ROOT / "results"
LOGS_DIR = ROOT / "logs"
SUMMARY_DIR = ROOT / "summary"
SCRATCH_DIR = ROOT / "scratch"

BENCHMARK_SCRIPT = ENGINE_DIR / "run_bgk_r03_benchmark_put.py"
HYBRID_SCRIPT = ENGINE_DIR / "run_bgk_r03_hybrid_put.py"

MANUSCRIPT_STEP_CSV = (
    Path("D:/Mara PhD/Paper-C/Working Files/Manuscript Code/reference_values")
    / "bgk_r02_t1_delta05_nex12_step_sweep_all_ref1200_direct_samepaths60k_s24487296_table.csv"
)
MANUSCRIPT_BENCHMARK_CSV = (
    Path("D:/Mara PhD/Paper-C/Working Files/Manuscript Code/reference_values")
    / "bgk_r02_t1_delta05_nex12_benchmark_steps1200_paths1200000_table.csv"
)

CASE_ID = "bgk_r02_t1_delta05_nex12_diagnostic"

MODEL_ENV = {
    "GDMR_S0": "100.0",
    "GDMR_V0": "0.114",
    "GDMR_VP0": "0.110",
    "GDMR_R": "0.02",
    "GDMR_KAPPA1": "5.5",
    "GDMR_KAPPA2": "0.1",
    "GDMR_THETA": "0.078",
    "GDMR_XI1": "2.689",
    "GDMR_XI2": "0.502",
    "GDMR_DELTA1": "0.5",
    "GDMR_DELTA2": "0.5",
    "GDMR_RHO12": "-0.982",
    "GDMR_RHO13": "-0.727",
    "GDMR_RHO23": "0.59",
    "GDMR_MATURITY": "1.0",
    "GDMR_EXERCISE_DATES": "12",
}

BASE_SEEDS = (2026, 2103)
K_VALUES = [70.0, 100.0, 110.0]


def ensure_dirs() -> None:
    for path in (RESULTS_DIR, LOGS_DIR, SUMMARY_DIR, SCRATCH_DIR):
        path.mkdir(parents=True, exist_ok=True)


def file_hash(path: Path) -> str:
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
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def append_or_replace(path: Path, fieldnames: list[str], key_fields: list[str], row: dict[str, Any]) -> None:
    rows = read_rows(path)
    key = tuple(str(row[field]) for field in key_fields)
    kept = [old for old in rows if tuple(str(old.get(field, "")) for field in key_fields) != key]
    kept.append({field: row.get(field, "") for field in fieldnames})
    kept.sort(key=lambda item: tuple(str(item.get(field, "")) for field in key_fields))
    write_rows(path, fieldnames, kept)


def finite_float(value: Any) -> float:
    out = float(value)
    if not math.isfinite(out):
        raise RuntimeError(f"Non-finite value: {value}")
    return out


def rel_error(value: float, reference: float) -> float:
    if abs(reference) <= 1e-16:
        return 0.0 if abs(value) <= 1e-16 else float("inf")
    return abs(value - reference) / abs(reference)


def direct_low_gap(direct: float, low: float) -> float:
    if abs(direct) <= 1e-16:
        return float("inf")
    return abs(direct - low) / abs(direct)


def common_env(extra: dict[str, str]) -> dict[str, str]:
    env = os.environ.copy()
    env.update(MODEL_ENV)
    env.update(
        {
            "GDMR_LSMC_STORE_DIR": str(SCRATCH_DIR / "lsmc_memmaps"),
            "GDMR_LSMC_SEED": str(BASE_SEEDS[0]),
            "GDMR_LSMC_LOW_SEED": str(BASE_SEEDS[1]),
            "GDMR_HYBRID_SEED": str(BASE_SEEDS[0]),
            "GDMR_HYBRID_LOW_SEED": str(BASE_SEEDS[1]),
            "GDMR_HYBRID_FST_BATCH_SIZE": "256",
            "GDMR_HYBRID_FST_PAD_FACTOR": "4",
        }
    )
    env.update(extra)
    return env


def parse_result_json(stdout: str, script_name: str) -> dict[str, Any]:
    for line in reversed(stdout.splitlines()):
        if line.startswith("RESULT_JSON: "):
            return json.loads(line[len("RESULT_JSON: ") :])
    raise RuntimeError(f"Could not parse RESULT_JSON from {script_name}")


def run_engine(script: Path, env_extra: dict[str, str], label: str) -> tuple[dict[str, Any], float]:
    env = common_env(env_extra)
    start = time.perf_counter()
    completed = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(ENGINE_DIR),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    runtime = time.perf_counter() - start
    log_path = LOGS_DIR / f"{label}.log"
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
        raise RuntimeError(f"{script.name} failed. See {log_path}")
    result = parse_result_json(completed.stdout, script.name)
    assert_provenance(result)
    return result, runtime


def assert_provenance(result: dict[str, Any]) -> None:
    expected = {
        "r": 0.02,
        "delta1": 0.5,
        "delta2": 0.5,
        "T": 1.0,
        "v0": 0.114,
        "vp0": 0.110,
    }
    for key, value in expected.items():
        actual = finite_float(result[key])
        if not math.isclose(actual, value, rel_tol=0.0, abs_tol=1e-12):
            raise RuntimeError(f"Unexpected provenance {key}: got {actual}, expected {value}")
    if int(result["exercise_dates"]) != 12:
        raise RuntimeError(f"Unexpected exercise_dates: {result['exercise_dates']}")


def engine_hashes() -> dict[str, str]:
    return {
        "benchmark_engine_sha256": file_hash(BENCHMARK_SCRIPT),
        "hybrid_engine_sha256": file_hash(HYBRID_SCRIPT),
    }


def write_provenance() -> None:
    payload = {
        "case_id": CASE_ID,
        "root": str(ROOT),
        "model_env": MODEL_ENV,
        "engine_hashes": engine_hashes(),
        "created_by": "delta05_diagnostic_runner.py",
        "note": "All outputs are sandbox-local under To be deleted.",
    }
    (RESULTS_DIR / "provenance.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


LSMC_FIELDS = [
    "study",
    "K",
    "euler_steps",
    "paths",
    "low_paths",
    "seed",
    "low_seed",
    "policy",
    "price_direct",
    "se_direct",
    "ci_width_direct",
    "price_low",
    "se_low",
    "direct_low_gap",
    "runtime_seconds",
    "r",
    "delta1",
    "delta2",
    "v0",
    "vp0",
    "T",
    "exercise_dates",
    "benchmark_engine_sha256",
]


def lsmc_row(study: str, result: dict[str, Any], runtime: float) -> dict[str, Any]:
    direct = finite_float(result["lsmc_direct_price"])
    low = finite_float(result["lsmc_low_price"])
    se = finite_float(result["lsmc_direct_error"])
    return {
        "study": study,
        "K": f"{finite_float(result['K']):.0f}",
        "euler_steps": int(result["euler_steps"]),
        "paths": int(result["paths"]),
        "low_paths": int(result["low_paths"]),
        "seed": int(result["seed"]),
        "low_seed": int(result["low_seed"]),
        "policy": result.get("lsmc_policy", "all_paths"),
        "price_direct": f"{direct:.12f}",
        "se_direct": f"{se:.12f}",
        "ci_width_direct": f"{3.92 * se:.12f}",
        "price_low": f"{low:.12f}",
        "se_low": f"{finite_float(result['lsmc_low_error']):.12f}",
        "direct_low_gap": f"{direct_low_gap(direct, low):.12f}",
        "runtime_seconds": f"{runtime:.6f}",
        "r": f"{finite_float(result['r']):.12g}",
        "delta1": f"{finite_float(result['delta1']):.12g}",
        "delta2": f"{finite_float(result['delta2']):.12g}",
        "v0": f"{finite_float(result['v0']):.12g}",
        "vp0": f"{finite_float(result['vp0']):.12g}",
        "T": f"{finite_float(result['T']):.12g}",
        "exercise_dates": int(result["exercise_dates"]),
        "benchmark_engine_sha256": engine_hashes()["benchmark_engine_sha256"],
    }


def run_lsmc_once(
    *,
    study: str,
    strike: float,
    steps: int,
    paths: int,
    low_paths: int,
    seed: int,
    low_seed: int,
    policy: str,
    output_csv: Path,
) -> dict[str, Any]:
    existing = read_rows(output_csv)
    key = (f"{strike:.0f}", str(steps), str(paths), str(seed), policy, study)
    for row in existing:
        row_key = (
            row.get("K", ""),
            row.get("euler_steps", ""),
            row.get("paths", ""),
            row.get("seed", ""),
            row.get("policy", ""),
            row.get("study", ""),
        )
        if row_key == key:
            print(f"[skip] LSMC {study} K={strike:.0f} M={steps} N={paths} seed={seed} {policy}", flush=True)
            return row

    label = f"lsmc_{study}_K{strike:.0f}_M{steps}_N{paths}_seed{seed}_{policy}".replace(".", "p")
    print(f"[run] LSMC {study} K={strike:.0f} M={steps} N={paths} seed={seed} {policy}", flush=True)
    result, runtime = run_engine(
        BENCHMARK_SCRIPT,
        {
            "GDMR_STRIKE": f"{strike:.1f}",
            "GDMR_EULER_STEPS": str(steps),
            "GDMR_LSMC_PATHS": str(paths),
            "GDMR_LSMC_LOW_PATHS": str(low_paths),
            "GDMR_LSMC_SEED": str(seed),
            "GDMR_LSMC_LOW_SEED": str(low_seed),
            "GDMR_LSMC_ITM_ONLY": "1" if policy == "itm_only" else "0",
        },
        label,
    )
    row = lsmc_row(study, result, runtime)
    append_or_replace(
        output_csv,
        LSMC_FIELDS,
        ["study", "K", "euler_steps", "paths", "seed", "policy"],
        row,
    )
    return row


def run_smoke() -> None:
    smoke_csv = RESULTS_DIR / "smoke.csv"
    row = run_lsmc_once(
        study="smoke",
        strike=100.0,
        steps=48,
        paths=1000,
        low_paths=1000,
        seed=2026,
        low_seed=2103,
        policy="all_paths",
        output_csv=smoke_csv,
    )
    if (
        row.get("r") != "0.02"
        or row.get("delta1") != "0.5"
        or row.get("delta2") != "0.5"
        or row.get("exercise_dates") not in ("12", 12)
    ):
        raise RuntimeError("Smoke provenance check failed.")


def manuscript_known_point() -> tuple[float | None, float | None]:
    if not MANUSCRIPT_STEP_CSV.exists():
        return None, None
    for row in read_rows(MANUSCRIPT_STEP_CSV):
        if row.get("scenario") == "ATM" and row.get("method") == "benchmark" and row.get("euler_steps") == "48":
            return float(row["price_direct"]), float(row["se_direct"])
    return None, None


def run_parity() -> None:
    parity_csv = RESULTS_DIR / "parity.csv"
    row = run_lsmc_once(
        study="parity",
        strike=100.0,
        steps=48,
        paths=60000,
        low_paths=60000,
        seed=2026,
        low_seed=2103,
        policy="all_paths",
        output_csv=parity_csv,
    )
    old_price, old_se = manuscript_known_point()
    direct = float(row["price_direct"])
    parity_rows = read_rows(parity_csv)
    for item in parity_rows:
        if item.get("study") == "parity":
            item["manuscript_price_direct"] = "" if old_price is None else f"{old_price:.12f}"
            item["manuscript_se_direct"] = "" if old_se is None else f"{old_se:.12f}"
            item["abs_price_difference_from_manuscript"] = "" if old_price is None else f"{abs(direct - old_price):.12f}"
    fields = LSMC_FIELDS + ["manuscript_price_direct", "manuscript_se_direct", "abs_price_difference_from_manuscript"]
    write_rows(parity_csv, fields, parity_rows)


def low_budget(paths: int) -> int:
    return min(paths, 200000)


def run_lsmc_convergence() -> None:
    output_csv = RESULTS_DIR / "lsmc_convergence.csv"
    base_steps = [48, 96, 240, 600, 1200]
    base_paths = [60000, 200000, 600000]
    seed_plan = [(2026, 2103)]

    for strike in K_VALUES:
        for paths in base_paths:
            for steps in base_steps:
                if strike != 100.0 and paths == 600000 and steps not in (48, 1200):
                    continue
                if strike != 100.0 and paths == 200000 and steps not in (48, 600, 1200):
                    continue
                run_lsmc_once(
                    study="convergence",
                    strike=strike,
                    steps=steps,
                    paths=paths,
                    low_paths=low_budget(paths),
                    seed=seed_plan[0][0],
                    low_seed=seed_plan[0][1],
                    policy="all_paths",
                    output_csv=output_csv,
                )
                build_summary()

    for seed, low_seed in [(3026, 3103), (4026, 4103)]:
        for steps in base_steps:
            run_lsmc_once(
                study="convergence_seed_replication",
                strike=100.0,
                steps=steps,
                paths=60000,
                low_paths=60000,
                seed=seed,
                low_seed=low_seed,
                policy="all_paths",
                output_csv=output_csv,
            )
            build_summary()


def run_policy() -> None:
    output_csv = RESULTS_DIR / "policy_diagnostic.csv"
    for strike in K_VALUES:
        for steps in [48, 96, 600, 1200]:
            for policy in ["all_paths", "itm_only"]:
                run_lsmc_once(
                    study="policy",
                    strike=strike,
                    steps=steps,
                    paths=60000,
                    low_paths=60000,
                    seed=2026,
                    low_seed=2103,
                    policy=policy,
                    output_csv=output_csv,
                )
                build_summary()
    for steps in [48, 1200]:
        for policy in ["all_paths", "itm_only"]:
            run_lsmc_once(
                study="policy_large_anchor",
                strike=100.0,
                steps=steps,
                paths=200000,
                low_paths=200000,
                seed=2026,
                low_seed=2103,
                policy=policy,
                output_csv=output_csv,
            )
            build_summary()


EULER_FIELDS = [
    "K_list",
    "euler_steps",
    "paths",
    "seed",
    "neg_raw_v_rate",
    "neg_raw_vp_rate",
    "zero_v_rate",
    "zero_vp_rate",
    "terminal_v_mean",
    "terminal_v_q01",
    "terminal_v_q50",
    "terminal_v_q99",
    "terminal_vp_mean",
    "terminal_spot_mean",
    "european_put_k70",
    "european_put_k100",
    "european_put_k110",
    "se_put_k100",
    "runtime_seconds",
    "r",
    "delta1",
    "delta2",
    "v0",
    "vp0",
    "T",
    "exercise_dates",
]


def run_euler_forward_one(steps: int, paths: int = 500000, seed: int = 2026, chunk: int = 25000) -> dict[str, Any]:
    output_csv = RESULTS_DIR / "euler_boundary.csv"
    for row in read_rows(output_csv):
        if row.get("euler_steps") == str(steps) and row.get("paths") == str(paths) and row.get("seed") == str(seed):
            print(f"[skip] Euler boundary M={steps} N={paths}", flush=True)
            return row

    print(f"[run] Euler boundary M={steps} N={paths}", flush=True)
    start = time.perf_counter()
    S0 = 100.0
    v0 = 0.114
    vp0 = 0.110
    r = 0.02
    kappa1 = 5.5
    kappa2 = 0.1
    theta = 0.078
    xi1 = 2.689
    xi2 = 0.502
    delta1 = 0.5
    delta2 = 0.5
    T = 1.0
    rho12 = -0.982
    rho13 = -0.727
    rho23 = 0.59
    corr = np.array([[1.0, rho12, rho13], [rho12, 1.0, rho23], [rho13, rho23, 1.0]], dtype=np.float64)
    chol = np.linalg.cholesky(corr).astype(np.float32)
    dt = T / float(steps)
    sqrt_dt = math.sqrt(dt)
    rng = np.random.default_rng(seed)

    total_small_steps = 0
    neg_v = 0
    neg_vp = 0
    zero_v = 0
    zero_vp = 0
    terminal_v_values: list[np.ndarray] = []
    terminal_vp_sum = 0.0
    terminal_spot_sum = 0.0
    payoff_sums = {70.0: 0.0, 100.0: 0.0, 110.0: 0.0}
    payoff_sq_sum_100 = 0.0
    done = 0

    while done < paths:
        n = min(chunk, paths - done)
        spot = np.full(n, S0, dtype=np.float32)
        v = np.full(n, v0, dtype=np.float32)
        vp = np.full(n, vp0, dtype=np.float32)
        for _ in range(steps):
            z = rng.standard_normal((n, 3), dtype=np.float32) @ chol.T
            z1 = z[:, 0]
            z2 = z[:, 1]
            z3 = z[:, 2]
            v_pos = np.maximum(v, 0.0)
            vp_pos = np.maximum(vp, 0.0)

            vp_raw = vp_pos + kappa2 * (theta - vp_pos) * dt
            vp_raw += xi2 * np.power(vp_pos, delta2) * sqrt_dt * z3
            neg_vp += int(np.count_nonzero(vp_raw < 0.0))
            vp = np.maximum(vp_raw, 0.0).astype(np.float32)

            v_raw = v_pos + kappa1 * (vp_pos - v_pos) * dt
            v_raw += xi1 * np.power(v_pos, delta1) * sqrt_dt * z2
            neg_v += int(np.count_nonzero(v_raw < 0.0))
            v = np.maximum(v_raw, 0.0).astype(np.float32)

            zero_v += int(np.count_nonzero(v <= 0.0))
            zero_vp += int(np.count_nonzero(vp <= 0.0))
            total_small_steps += n

            log_move = (r - 0.5 * v_pos) * dt + np.sqrt(v_pos) * sqrt_dt * z1
            spot = spot * np.exp(log_move)

        discount = math.exp(-r * T)
        for strike in payoff_sums:
            payoff = discount * np.maximum(strike - spot.astype(np.float64), 0.0)
            payoff_sums[strike] += float(np.sum(payoff))
            if strike == 100.0:
                payoff_sq_sum_100 += float(np.sum(payoff * payoff))
        terminal_v_values.append(v.astype(np.float64))
        terminal_vp_sum += float(np.sum(vp.astype(np.float64)))
        terminal_spot_sum += float(np.sum(spot.astype(np.float64)))
        done += n

    terminal_v = np.concatenate(terminal_v_values)
    mean_100 = payoff_sums[100.0] / paths
    var_100 = max(payoff_sq_sum_100 / paths - mean_100 * mean_100, 0.0)
    runtime = time.perf_counter() - start
    row = {
        "K_list": "70,100,110",
        "euler_steps": steps,
        "paths": paths,
        "seed": seed,
        "neg_raw_v_rate": f"{neg_v / total_small_steps:.12f}",
        "neg_raw_vp_rate": f"{neg_vp / total_small_steps:.12f}",
        "zero_v_rate": f"{zero_v / total_small_steps:.12f}",
        "zero_vp_rate": f"{zero_vp / total_small_steps:.12f}",
        "terminal_v_mean": f"{float(np.mean(terminal_v)):.12f}",
        "terminal_v_q01": f"{float(np.quantile(terminal_v, 0.01)):.12f}",
        "terminal_v_q50": f"{float(np.quantile(terminal_v, 0.50)):.12f}",
        "terminal_v_q99": f"{float(np.quantile(terminal_v, 0.99)):.12f}",
        "terminal_vp_mean": f"{terminal_vp_sum / paths:.12f}",
        "terminal_spot_mean": f"{terminal_spot_sum / paths:.12f}",
        "european_put_k70": f"{payoff_sums[70.0] / paths:.12f}",
        "european_put_k100": f"{mean_100:.12f}",
        "european_put_k110": f"{payoff_sums[110.0] / paths:.12f}",
        "se_put_k100": f"{math.sqrt(var_100 / paths):.12f}",
        "runtime_seconds": f"{runtime:.6f}",
        "r": "0.02",
        "delta1": "0.5",
        "delta2": "0.5",
        "v0": "0.114",
        "vp0": "0.110",
        "T": "1.0",
        "exercise_dates": 12,
    }
    append_or_replace(output_csv, EULER_FIELDS, ["euler_steps", "paths", "seed"], row)
    return row


def run_euler_boundary() -> None:
    for steps in [24, 48, 96, 240, 600, 1200]:
        run_euler_forward_one(steps)
        build_summary()


HYBRID_FIELDS = [
    "study",
    "K",
    "euler_steps",
    "paths",
    "low_paths",
    "seed",
    "low_seed",
    "grid_label",
    "asset_grid_points",
    "asset_low_factor",
    "asset_high_factor",
    "vol_quantile",
    "price_direct",
    "se_direct",
    "price_low",
    "se_low",
    "runtime_seconds",
    "r",
    "delta1",
    "delta2",
    "v0",
    "vp0",
    "T",
    "exercise_dates",
    "hybrid_engine_sha256",
]


def run_hybrid_once(strike: float, steps: int, paths: int, grid: dict[str, str]) -> dict[str, Any]:
    output_csv = RESULTS_DIR / "hybrid_sensitivity.csv"
    grid_label = grid["label"]
    for row in read_rows(output_csv):
        if (
            row.get("K") == f"{strike:.0f}"
            and row.get("euler_steps") == str(steps)
            and row.get("paths") == str(paths)
            and row.get("grid_label") == grid_label
        ):
            print(f"[skip] Hybrid K={strike:.0f} M={steps} N={paths} {grid_label}", flush=True)
            return row
    print(f"[run] Hybrid K={strike:.0f} M={steps} N={paths} {grid_label}", flush=True)
    label = f"hybrid_K{strike:.0f}_M{steps}_N{paths}_{grid_label}"
    result, runtime = run_engine(
        HYBRID_SCRIPT,
        {
            "GDMR_STRIKE": f"{strike:.1f}",
            "GDMR_EULER_STEPS": str(steps),
            "GDMR_HYBRID_PATHS": str(paths),
            "GDMR_HYBRID_LOW_PATHS": str(min(paths, 1000)),
            "GDMR_HYBRID_ASSET_POINTS": grid["asset_points"],
            "GDMR_HYBRID_ASSET_LOW_FACTOR": grid["asset_low"],
            "GDMR_HYBRID_ASSET_HIGH_FACTOR": grid["asset_high"],
            "GDMR_HYBRID_VOL_QUANTILE": grid["vol_quantile"],
        },
        label,
    )
    row = {
        "study": "hybrid_sensitivity",
        "K": f"{finite_float(result['K']):.0f}",
        "euler_steps": int(result["euler_steps"]),
        "paths": int(result["paths"]),
        "low_paths": int(result["low_paths"]),
        "seed": int(result["seed"]),
        "low_seed": int(result["low_seed"]),
        "grid_label": grid_label,
        "asset_grid_points": int(result["asset_grid_points"]),
        "asset_low_factor": f"{finite_float(result['asset_low_factor']):.12g}",
        "asset_high_factor": f"{finite_float(result['asset_high_factor']):.12g}",
        "vol_quantile": f"{finite_float(result['vol_quantile']):.12g}",
        "price_direct": f"{finite_float(result['hybrid_direct_price']):.12f}",
        "se_direct": f"{finite_float(result['hybrid_direct_error']):.12f}",
        "price_low": f"{finite_float(result['hybrid_low_price']):.12f}",
        "se_low": f"{finite_float(result['hybrid_low_error']):.12f}",
        "runtime_seconds": f"{runtime:.6f}",
        "r": f"{finite_float(result['r']):.12g}",
        "delta1": f"{finite_float(result['delta1']):.12g}",
        "delta2": f"{finite_float(result['delta2']):.12g}",
        "v0": f"{finite_float(result['v0']):.12g}",
        "vp0": f"{finite_float(result['vp0']):.12g}",
        "T": f"{finite_float(result['T']):.12g}",
        "exercise_dates": int(result["exercise_dates"]),
        "hybrid_engine_sha256": engine_hashes()["hybrid_engine_sha256"],
    }
    append_or_replace(output_csv, HYBRID_FIELDS, ["K", "euler_steps", "paths", "grid_label"], row)
    return row


def run_hybrid_sensitivity() -> None:
    grids = [
        {"label": "default", "asset_points": "301", "asset_low": "0.30", "asset_high": "3.50", "vol_quantile": "0.999"},
        {"label": "expanded", "asset_points": "601", "asset_low": "0.15", "asset_high": "6.00", "vol_quantile": "0.9995"},
        {"label": "wide", "asset_points": "301", "asset_low": "0.15", "asset_high": "6.00", "vol_quantile": "0.999"},
        {"label": "q995", "asset_points": "301", "asset_low": "0.30", "asset_high": "3.50", "vol_quantile": "0.995"},
    ]
    for steps in [48, 96, 240]:
        for grid in grids:
            run_hybrid_once(100.0, steps, 20000, grid)
            build_summary()
    for steps in [48, 96]:
        run_hybrid_once(100.0, steps, 60000, grids[0])
        build_summary()
    for strike in [70.0, 110.0]:
        for steps in [48, 96]:
            run_hybrid_once(strike, steps, 20000, grids[0])
            build_summary()


def latex_escape(value: Any) -> str:
    text = str(value)
    return (
        text.replace("\\", "\\textbackslash{}")
        .replace("_", "\\_")
        .replace("%", "\\%")
        .replace("&", "\\&")
    )


def fmt_num(value: Any, digits: int = 3) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return ""


def select_lsmc_summary_rows() -> list[dict[str, str]]:
    rows = read_rows(RESULTS_DIR / "lsmc_convergence.csv")
    selected: list[dict[str, str]] = []
    for row in rows:
        if row.get("study") not in ("convergence", "convergence_seed_replication"):
            continue
        k = row.get("K")
        steps = row.get("euler_steps")
        paths = row.get("paths")
        seed = row.get("seed")
        if k == "100" and paths in ("60000", "200000", "600000"):
            selected.append(row)
        elif seed == "2026" and paths == "60000" and steps in ("48", "1200"):
            selected.append(row)
    return selected[:24]


def estimate_conclusion() -> str:
    euler = read_rows(RESULTS_DIR / "euler_boundary.csv")
    policy = read_rows(RESULTS_DIR / "policy_diagnostic.csv")
    hybrid = read_rows(RESULTS_DIR / "hybrid_sensitivity.csv")
    lsmc = read_rows(RESULTS_DIR / "lsmc_convergence.csv")
    parts: list[str] = []
    if euler:
        by_m = {int(row["euler_steps"]): float(row["european_put_k100"]) for row in euler if row.get("european_put_k100")}
        if 48 in by_m and 1200 in by_m:
            parts.append(
                f"The forward European K=100 diagnostic moves from {by_m[48]:.3f} at M=48 to {by_m[1200]:.3f} at M=1200, so a large component appears before Bermudan regression."
            )
    if lsmc:
        rows = [row for row in lsmc if row.get("K") == "100" and row.get("paths") == "60000" and row.get("seed") == "2026"]
        by_m = {int(row["euler_steps"]): float(row["price_direct"]) for row in rows}
        if 48 in by_m and 1200 in by_m:
            parts.append(f"Plain LSMC K=100 similarly changes from {by_m[48]:.3f} at M=48 to {by_m[1200]:.3f} at M=1200.")
    if policy:
        pairs: list[float] = []
        for all_row in policy:
            if all_row.get("policy") != "all_paths":
                continue
            for itm_row in policy:
                if (
                    itm_row.get("policy") == "itm_only"
                    and itm_row.get("K") == all_row.get("K")
                    and itm_row.get("euler_steps") == all_row.get("euler_steps")
                    and itm_row.get("paths") == all_row.get("paths")
                ):
                    pairs.append(abs(float(itm_row["price_direct"]) - float(all_row["price_direct"])))
        if pairs:
            parts.append(f"The largest observed all-path versus ITM-only LSMC policy difference is {max(pairs):.3f}.")
    if hybrid:
        rows = [row for row in hybrid if row.get("K") == "100" and row.get("euler_steps") == "48" and row.get("paths") == "20000"]
        values = [float(row["price_direct"]) for row in rows]
        if len(values) >= 2:
            parts.append(f"The K=100, M=48 Hybrid grid sensitivity range is {max(values) - min(values):.3f}.")
    if not parts:
        return "The diagnostic run is in progress; completed rows are reported below."
    return " ".join(parts)


def table_rows(headers: list[str], rows: list[list[Any]]) -> str:
    lines = ["\\begin{tabular}{" + "l" * len(headers) + "}", "\\hline"]
    lines.append(" & ".join(headers) + " \\\\")
    lines.append("\\hline")
    for row in rows:
        lines.append(" & ".join(latex_escape(value) for value in row) + " \\\\")
    lines.append("\\hline")
    lines.append("\\end{tabular}")
    return "\n".join(lines)


def build_summary() -> None:
    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
    tex_path = SUMMARY_DIR / "delta05_diagnostic_summary.tex"
    lsmc_rows = select_lsmc_summary_rows()
    policy_rows = read_rows(RESULTS_DIR / "policy_diagnostic.csv")[:24]
    euler_rows = read_rows(RESULTS_DIR / "euler_boundary.csv")
    hybrid_rows = read_rows(RESULTS_DIR / "hybrid_sensitivity.csv")[:24]
    parity_rows = read_rows(RESULTS_DIR / "parity.csv")

    lsmc_table = table_rows(
        ["K", "M", "N", "seed", "price", "SE", "low", "gap"],
        [
            [
                row.get("K", ""),
                row.get("euler_steps", ""),
                row.get("paths", ""),
                row.get("seed", ""),
                fmt_num(row.get("price_direct"), 3),
                fmt_num(row.get("se_direct"), 3),
                fmt_num(row.get("price_low"), 3),
                fmt_num(row.get("direct_low_gap"), 4),
            ]
            for row in lsmc_rows
        ],
    )
    policy_table = table_rows(
        ["K", "M", "N", "policy", "price", "SE", "low"],
        [
            [
                row.get("K", ""),
                row.get("euler_steps", ""),
                row.get("paths", ""),
                row.get("policy", ""),
                fmt_num(row.get("price_direct"), 3),
                fmt_num(row.get("se_direct"), 3),
                fmt_num(row.get("price_low"), 3),
            ]
            for row in policy_rows
        ],
    )
    euler_table = table_rows(
        ["M", "N", "neg v", "zero v", "Eur K=100", "SE", "v q50"],
        [
            [
                row.get("euler_steps", ""),
                row.get("paths", ""),
                fmt_num(row.get("neg_raw_v_rate"), 4),
                fmt_num(row.get("zero_v_rate"), 4),
                fmt_num(row.get("european_put_k100"), 3),
                fmt_num(row.get("se_put_k100"), 3),
                fmt_num(row.get("terminal_v_q50"), 3),
            ]
            for row in euler_rows
        ],
    )
    hybrid_table = table_rows(
        ["K", "M", "N", "grid", "price", "SE", "low", "q"],
        [
            [
                row.get("K", ""),
                row.get("euler_steps", ""),
                row.get("paths", ""),
                row.get("grid_label", ""),
                fmt_num(row.get("price_direct"), 3),
                fmt_num(row.get("se_direct"), 3),
                fmt_num(row.get("price_low"), 3),
                row.get("vol_quantile", ""),
            ]
            for row in hybrid_rows
        ],
    )
    parity_text = "No parity row is available yet."
    if parity_rows:
        row = parity_rows[0]
        parity_text = (
            "Sandbox parity for K=100, M=48, N=60000 gives "
            + fmt_num(row.get("price_direct"), 6)
            + "; manuscript CSV gives "
            + fmt_num(row.get("manuscript_price_direct"), 6)
            + "; absolute difference "
            + fmt_num(row.get("abs_price_difference_from_manuscript"), 6)
            + "."
        )

    body = r"""\documentclass{article}
\usepackage[margin=1in]{geometry}
\usepackage{booktabs}
\usepackage{array}
\begin{document}
\section*{Delta 0.5 diagnostic summary}
\noindent \textbf{Case.} $r=0.02$, $\delta_1=\delta_2=0.5$, $T=1$, $N_{\mathrm{ex}}=12$, $v_0=0.114$, $v'_0=0.110$. All files were generated under \texttt{D:/Mara PhD/Paper-C/To be deleted}.

\paragraph{Current conclusion.}
""" + latex_escape(estimate_conclusion()) + r"""

\paragraph{Parity check.}
""" + latex_escape(parity_text) + r"""

\paragraph{LSMC convergence.}
""" + lsmc_table + r"""

\paragraph{All-path versus ITM-only LSMC.}
""" + policy_table + r"""

\paragraph{Euler boundary and terminal-payoff diagnostic.}
""" + euler_table + r"""

\paragraph{Hybrid-PDE grid sensitivity.}
""" + hybrid_table + r"""

\paragraph{Recommendation.}
If the Euler and LSMC rows continue to move materially as $M$ increases while path-count and policy changes are small, the large errors should be treated as time-discretization bias from the full-truncation Euler scheme in the square-root case, not as a benchmark-file mismatch. In that case the manuscript should either use a finer-step robustness design or reframe this parameter set as a stress test of the time discretization.

\end{document}
"""
    tex_path.write_text(body, encoding="utf-8")


def compile_summary() -> None:
    tex_path = SUMMARY_DIR / "delta05_diagnostic_summary.tex"
    if not tex_path.exists():
        return
    try:
        subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", tex_path.name],
            cwd=str(SUMMARY_DIR),
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass


def run_all() -> None:
    write_provenance()
    try:
        run_smoke()
        build_summary()
        run_parity()
        build_summary()
        run_lsmc_convergence()
        run_policy()
        run_euler_boundary()
        run_hybrid_sensitivity()
    finally:
        build_summary()
        compile_summary()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run isolated delta=0.5 diagnostics.")
    parser.add_argument(
        "--mode",
        choices=["all", "smoke", "parity", "euler", "lsmc", "policy", "hybrid", "summary"],
        default="all",
    )
    return parser.parse_args()


def main() -> None:
    ensure_dirs()
    args = parse_args()
    if args.mode == "smoke":
        write_provenance()
        run_smoke()
    elif args.mode == "parity":
        write_provenance()
        run_parity()
    elif args.mode == "euler":
        write_provenance()
        run_euler_boundary()
    elif args.mode == "lsmc":
        write_provenance()
        run_lsmc_convergence()
    elif args.mode == "policy":
        write_provenance()
        run_policy()
    elif args.mode == "hybrid":
        write_provenance()
        run_hybrid_sensitivity()
    elif args.mode == "summary":
        build_summary()
        compile_summary()
    else:
        run_all()
    build_summary()
    compile_summary()


if __name__ == "__main__":
    main()
