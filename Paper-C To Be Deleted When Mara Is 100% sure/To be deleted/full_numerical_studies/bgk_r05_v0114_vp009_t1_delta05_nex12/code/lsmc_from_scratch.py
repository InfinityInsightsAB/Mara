#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path

from scratch_lsmc_helpers import BASIS_DEGREE, BASIS_SIZE, GDMRParameters, LSMCSettings, price_plain_lsmc


THIS_DIR = Path(__file__).resolve().parent


def env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    return int(value)


def env_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    if value is None:
        return default
    return float(value)


def load_inputs() -> tuple[GDMRParameters, LSMCSettings]:
    params = GDMRParameters(
        s0=env_float("GDMR_S0", 100.0),
        v0=env_float("GDMR_V0", 0.114),
        vp0=env_float("GDMR_VP0", 0.09),
        r=env_float("GDMR_R", 0.05),
        kappa1=env_float("GDMR_KAPPA1", 2.0),
        kappa2=env_float("GDMR_KAPPA2", 0.1),
        theta=env_float("GDMR_THETA", 0.09),
        xi1=env_float("GDMR_XI1", 4.0),
        xi2=env_float("GDMR_XI2", 0.502),
        delta1=env_float("GDMR_DELTA1", 0.5),
        delta2=env_float("GDMR_DELTA2", 0.5),
        rho12=env_float("GDMR_RHO12", -0.3),
        rho13=env_float("GDMR_RHO13", -0.727),
        rho23=env_float("GDMR_RHO23", 0.590),
    )
    paths = env_int("GDMR_LSMC_PATHS", 1_200_000)
    settings = LSMCSettings(
        strike=env_float("GDMR_STRIKE", 100.0),
        maturity=env_float("GDMR_MATURITY", 1.0),
        paths=paths,
        low_paths=env_int("GDMR_LSMC_LOW_PATHS", paths),
        exercise_dates=env_int("GDMR_EXERCISE_DATES", 12),
        euler_steps=env_int("GDMR_EULER_STEPS", 1200),
        seed=env_int("GDMR_LSMC_SEED", 2026),
        low_seed=env_int("GDMR_LSMC_LOW_SEED", 2103),
        ridge=env_float("GDMR_LSMC_RIDGE", 1e-10),
        scratch_root=Path(os.environ.get("GDMR_LSMC_STORE_DIR", str(THIS_DIR / "_scratch"))),
        chunk_size=env_int("GDMR_LSMC_CHUNK_SIZE", 200_000),
    )
    return params, settings


def main() -> None:
    params, settings = load_inputs()
    results = price_plain_lsmc(params, settings)

    print("Plain LSMC from-scratch Bermudan put engine")
    print("Model: generalized Gatheral double mean-reverting (gDMR)")
    print(f"Spot:                 {results['S0']:.2f}")
    print(f"Strike:               {results['K']:.2f}")
    print(f"Maturity:             {results['T']:.2f}")
    print(f"Rate:                 {results['r']:.4f}")
    print(f"Training paths:       {results['paths']}")
    print(f"Low-estimator paths:  {results['low_paths']}")
    print(f"Exercise dates:       {results['exercise_dates']}")
    print(f"Euler steps:          {results['euler_steps']}")
    print(f"Basis degree:         {BASIS_DEGREE}")
    print(f"Basis size:           {BASIS_SIZE}")
    print(f"State dtype:          {results['state_dtype']}")
    print(f"Seed:                 {results['seed']}")
    print(f"Low seed:             {results['low_seed']}")
    print(f"Scratch root:         {results['scratch_root']}")
    print(f"LSMC direct price:    {results['lsmc_direct_price']:.6f}")
    print(f"LSMC direct error:    {results['lsmc_direct_error']:.6f}")
    print(f"LSMC low price:       {results['lsmc_low_price']:.6f}")
    print(f"LSMC low error:       {results['lsmc_low_error']:.6f}")
    print("RESULT_JSON: " + json.dumps(results, sort_keys=True))


if __name__ == "__main__":
    main()
