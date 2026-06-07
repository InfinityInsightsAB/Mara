# Corrected Bermudan pricing package

This package is split into two folders.

- `gdmr_standalone/`
  Standalone gDMR scripts for the LSMC-versus-hybrid Bermudan put comparison under your manuscript setup.
- `heston_paper_benchmark/`
  Standalone Heston paper-parameter scripts for benchmarking LSMC and hybrid Bermudan put prices against the published numbers.

The standalone code now uses a math-style naming convention in the scripts:

- `S0` for the initial spot
- `K` for strike
- `T` for maturity
- `N` for paths
- `M` for Euler steps
- `N_ex`, `N_low`, and `N_S` for exercise dates, low-estimator paths, and asset-grid size

## What was corrected

1. The original comparison treated a single LSMC number as a "Monte Carlo reference". The paper does not do that. The paper compares LSMC and hybrid estimates against a finite-difference reference.
2. The original standalone LSMC script produced only one LSMC estimate. The paper and thesis procedures use a direct/high estimate and an independent low estimate.
3. The original hybrid low-estimator logic allowed exercise at time zero. The corrected low-estimator excludes time-zero exercise.
4. The original scripts mixed Bermudan exercise dates with Euler time steps. The corrected versions separate those quantities.
5. The original user setup was not the paper setup. Your scripts were written for a gDMR model, while the paper's direct comparison example is the standard Heston Bermudan put.
6. The paper-sized LSMC run is memory-sensitive. The corrected Monte Carlo implementation stores only exercise-date states instead of every Euler step.

## Included files

- `gdmr_standalone/run_gdmr_lsmc_put.py`
- `gdmr_standalone/run_gdmr_hybrid_put.py`
- `gdmr_standalone/compare_gdmr_put_prices.py`
- `gdmr_standalone/gdmr_standalone_README.md`
- `gdmr_standalone/gdmr_code_explanation.md`
- `gdmr_standalone/gdmr_results_and_improvements.md`
- `SETUP_RESULTS_SUMMARY.md`
- `heston_paper_benchmark/run_heston_paper_lsmc_put.py`
- `heston_paper_benchmark/run_heston_paper_hybrid_put.py`
- `heston_paper_benchmark/compare_heston_paper_put_prices.py`
- `heston_paper_benchmark/heston_paper_benchmark_README.md`

## Important note on the paper setup

The `heston_paper_benchmark` folder uses the paper's Heston Bermudan-put parameters and the published target values for comparison.
The LSMC file is parameter-faithful to the paper setup.
The hybrid file is a standalone paper-parameter reimplementation at the finest reported grid resolution. It is intended for comparison against the published article values, but it is not the paper authors' exact MLMC-FST implementation.
