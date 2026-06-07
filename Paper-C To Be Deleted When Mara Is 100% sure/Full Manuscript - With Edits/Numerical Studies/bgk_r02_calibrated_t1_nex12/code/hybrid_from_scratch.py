#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from scratch_hybrid_helpers import GdmrModel, HybridSettings, price_hybrid_put


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "rerun_config.json"


DEFAULT_MODEL_ENV = {
    "GDMR_S0": "100.0",
    "GDMR_V0": "0.114",
    "GDMR_VP0": "0.110",
    "GDMR_R": "0.02",
    "GDMR_KAPPA1": "5.5",
    "GDMR_KAPPA2": "0.1",
    "GDMR_THETA": "0.078",
    "GDMR_XI1": "2.689",
    "GDMR_XI2": "0.502",
    "GDMR_DELTA1": "0.94",
    "GDMR_DELTA2": "0.94",
    "GDMR_RHO12": "-0.982",
    "GDMR_RHO13": "-0.727",
    "GDMR_RHO23": "0.590",
    "GDMR_MATURITY": "1.0",
    "GDMR_EXERCISE_DATES": "12",
}

DEFAULT_HYBRID_ENV = {
    "GDMR_HYBRID_ASSET_POINTS": "301",
    "GDMR_HYBRID_ASSET_LOW_FACTOR": "0.30",
    "GDMR_HYBRID_ASSET_HIGH_FACTOR": "3.50",
    "GDMR_HYBRID_VOL_QUANTILE": "0.999",
    "GDMR_HYBRID_FST_PAD_FACTOR": "4",
    "GDMR_HYBRID_FST_BATCH_SIZE": "256",
    "GDMR_HYBRID_SEED": "2026",
    "GDMR_HYBRID_LOW_SEED": "2103",
}


def load_config_defaults() -> dict[str, str]:
    defaults = dict(DEFAULT_MODEL_ENV)
    defaults.update(DEFAULT_HYBRID_ENV)
    defaults.update(
        {
            "GDMR_STRIKE": "100.0",
            "GDMR_EULER_STEPS": "24",
            "GDMR_HYBRID_PATHS": "100",
            "GDMR_HYBRID_LOW_PATHS": "100",
            "GDMR_HYBRID_RIDGE": "1e-10",
        }
    )

    if not CONFIG_PATH.exists():
        return defaults

    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        config: dict[str, Any] = json.load(handle)

    defaults.update({str(k): str(v) for k, v in config.get("model_env", {}).items()})
    defaults.update({str(k): str(v) for k, v in config.get("hybrid_env", {}).items()})

    seeds = config.get("seeds", {})
    if "direct" in seeds:
        defaults["GDMR_HYBRID_SEED"] = str(seeds["direct"])
    if "low" in seeds:
        defaults["GDMR_HYBRID_LOW_SEED"] = str(seeds["low"])

    smoke = config.get("smoke", {})
    if "strike" in smoke:
        defaults["GDMR_STRIKE"] = str(smoke["strike"])
    if "euler_steps" in smoke:
        defaults["GDMR_EULER_STEPS"] = str(smoke["euler_steps"])
    if "hybrid_paths" in smoke:
        defaults["GDMR_HYBRID_PATHS"] = str(smoke["hybrid_paths"])
        defaults["GDMR_HYBRID_LOW_PATHS"] = str(smoke["hybrid_paths"])

    return defaults


DEFAULTS = load_config_defaults()


def env_str(name: str) -> str:
    return os.environ.get(name, DEFAULTS[name])


def env_int(name: str) -> int:
    return int(env_str(name))


def env_float(name: str) -> float:
    return float(env_str(name))


def build_model() -> GdmrModel:
    return GdmrModel(
        s0=env_float("GDMR_S0"),
        v0=env_float("GDMR_V0"),
        vp0=env_float("GDMR_VP0"),
        r=env_float("GDMR_R"),
        kappa1=env_float("GDMR_KAPPA1"),
        kappa2=env_float("GDMR_KAPPA2"),
        theta=env_float("GDMR_THETA"),
        xi1=env_float("GDMR_XI1"),
        xi2=env_float("GDMR_XI2"),
        delta1=env_float("GDMR_DELTA1"),
        delta2=env_float("GDMR_DELTA2"),
        rho12=env_float("GDMR_RHO12"),
        rho13=env_float("GDMR_RHO13"),
        rho23=env_float("GDMR_RHO23"),
        maturity=env_float("GDMR_MATURITY"),
    )


def build_settings() -> HybridSettings:
    return HybridSettings(
        strike=env_float("GDMR_STRIKE"),
        paths=env_int("GDMR_HYBRID_PATHS"),
        low_paths=env_int("GDMR_HYBRID_LOW_PATHS"),
        exercise_dates=env_int("GDMR_EXERCISE_DATES"),
        euler_steps=env_int("GDMR_EULER_STEPS"),
        asset_points=env_int("GDMR_HYBRID_ASSET_POINTS"),
        asset_low_factor=env_float("GDMR_HYBRID_ASSET_LOW_FACTOR"),
        asset_high_factor=env_float("GDMR_HYBRID_ASSET_HIGH_FACTOR"),
        vol_quantile=env_float("GDMR_HYBRID_VOL_QUANTILE"),
        fst_pad_factor=env_int("GDMR_HYBRID_FST_PAD_FACTOR"),
        fst_batch_size=env_int("GDMR_HYBRID_FST_BATCH_SIZE"),
        seed=env_int("GDMR_HYBRID_SEED"),
        low_seed=env_int("GDMR_HYBRID_LOW_SEED"),
        ridge=env_float("GDMR_HYBRID_RIDGE"),
    )


def main() -> None:
    model = build_model()
    settings = build_settings()
    result = price_hybrid_put(model, settings)

    print("Hybrid LSMC-PDE for a Bermudan put")
    print("Implementation: from-scratch volatility-only gDMR + FFT grid engine")
    print(f"Spot:                           {result['S0']:.2f}")
    print(f"Strike:                         {result['K']:.2f}")
    print(f"Maturity:                       {result['T']:.2f}")
    print(f"Rate:                           {result['r']:.4f}")
    print(f"Training volatility paths:      {result['paths']}")
    print(f"Low-estimator volatility paths: {result['low_paths']}")
    print(f"Exercise dates:                 {result['exercise_dates']}")
    print(f"Euler steps:                    {result['euler_steps']}")
    print(f"Asset grid points:              {result['asset_grid_points']}")
    print(f"FST pad factor:                 {result['fst_pad_factor']}")
    print(f"FST batch size:                 {result['fst_batch_size']}")
    print(f"Vol basis size:                 {result['vol_basis_size']}")
    print(f"Hybrid direct price:            {result['hybrid_direct_price']:.6f}")
    print(f"Hybrid direct error:            {result['hybrid_direct_error']:.6f}")
    print(f"Hybrid low price:               {result['hybrid_low_price']:.6f}")
    print(f"Hybrid low error:               {result['hybrid_low_error']:.6f}")
    print("RESULT_JSON: " + json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
