# gDMR standalone Bermudan put scripts

This folder contains a working three-script setup for the generalized Gatheral double mean-reverting model from `main.pdf`:

- `run_gdmr_benchmark_put.py`
  Standard LSMC benchmark with direct and low estimators.
- `run_gdmr_hybrid_put.py`
  Hybrid LSMC-PDE implementation using the one-way-coupled volatility structure.
- `compare_gdmr_put_prices.py`
  Runs both scripts, prints a comparison, and saves an SVG plot plus a markdown summary.

## Important scope note

`main.pdf` gives the gDMR model, the conditional-PDE representation, and the hybrid regression structure, but it does **not** provide a published numerical benchmark table like the Heston tables in Farahany et al. (2020).

So this folder uses a **working default parameter block** for gDMR rather than a paper-published benchmark block.

## Default model block

- `S0 = 100`
- `v0 = 0.04`
- `vp0 = 0.04`
- `r = 0.03`
- `kappa1 = 2.0`
- `kappa2 = 1.0`
- `theta = 0.04`
- `xi1 = 0.35`
- `xi2 = 0.20`
- `delta1 = 0.5`
- `delta2 = 0.5`
- `rho12 = 0.20`
- `rho13 = 0.10`
- `rho23 = 0.10`

## Default option/numerical block

- Bermudan put
- `K = 100`
- `T = 1`
- `N_ex = 100`
- `M = 600`

## Default LSMC block

- `N = 1_000_000`
- degree-3 state basis
- basis size `16`

## Default hybrid block

- `N = 30_000`
- `N_low = 30_000`
- `N_S = 181`
- degree-3 compact-support volatility basis
- basis size `10`
- `N_hermite = 64`

## Environment overrides

Both scripts accept environment-variable overrides.
Examples:

```bash
GDMR_LSMC_PATHS=200000 python run_gdmr_benchmark_put.py
GDMR_HYBRID_PATHS=10000 GDMR_HYBRID_LOW_PATHS=10000 python run_gdmr_hybrid_put.py
GDMR_LSMC_PATHS=50000 GDMR_LSMC_LOW_PATHS=50000 GDMR_HYBRID_PATHS=5000 GDMR_HYBRID_LOW_PATHS=5000 python compare_gdmr_put_prices.py
```
