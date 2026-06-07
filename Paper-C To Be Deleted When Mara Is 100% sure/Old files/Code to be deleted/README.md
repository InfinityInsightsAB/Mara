# Corrected Bermudan pricing package

This package is split into two folders.

- `my_setup/`
  Corrected versions of your three standalone scripts under your current gDMR setup.
- `paper_setup/`
  Standalone scripts configured with the Heston Bermudan-put parameters reported in Farahany, Jackson, and Jaimungal (2020), so you can compare your runs against the published numbers.

## What was corrected

1. The original comparison treated a single LSMC number as a "Monte Carlo reference". The paper does not do that. The paper compares LSMC and hybrid estimates against a finite-difference reference.
2. The original `run_monte_carlo_put.py` produced only one LSMC estimate. The paper and thesis procedures use a direct/high estimate and an independent low estimate.
3. The original hybrid low-estimator logic allowed exercise at time zero. The corrected low-estimator excludes time-zero exercise.
4. The original scripts mixed Bermudan exercise dates with Euler time steps. The corrected versions separate those quantities.
5. The original user setup was not the paper setup. Your scripts were written for a gDMR model, while the paper's direct comparison example is the standard Heston Bermudan put.
6. The paper-sized LSMC run is memory-sensitive. The corrected Monte Carlo implementation stores only exercise-date states instead of every Euler step.

## Included files

- `my_setup/run_monte_carlo_put.py`
- `my_setup/run_hybrid_put.py`
- `my_setup/compare_put_prices.py`
- `my_setup/README.md`
- `paper_setup/run_monte_carlo_put.py`
- `paper_setup/run_hybrid_put.py`
- `paper_setup/compare_put_prices.py`
- `paper_setup/README.md`

## Important note on the paper setup

The `paper_setup` folder uses the paper's Heston Bermudan-put parameters and the published target values for comparison.
The LSMC file is parameter-faithful to the paper setup.
The hybrid file is a standalone paper-parameter reimplementation at the finest reported grid resolution. It is intended for comparison against the published article values, but it is not the paper authors' exact MLMC-FST implementation.
