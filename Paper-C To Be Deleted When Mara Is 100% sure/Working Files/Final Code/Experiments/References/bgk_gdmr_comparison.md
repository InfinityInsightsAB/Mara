# BGK gDMR Comparison

This note records the BGK-style parameter tests built from the self-contained
`Final Code` package and copied into `Code/BGK Testing`.

The implementation keeps the `Final Code` notation and environment-variable
interface, but replaces the default model block with the parameters shown in
the provided screenshots.

## What Was Copied Into `BGK Testing`

The local BGK test package contains:

- `LSMC Benchmark/run_gdmr_benchmark_put.py`
- `Hybrid LSMC-PDE with FFT/run_gdmr_hybrid_put.py`
- `compare_gdmr_put_prices.py`

These were copied from `Final Code` and then modified so the BGK defaults are
local to `Code/BGK Testing`.

## Screenshot Notation -> Final-Code Notation

| Screenshot symbol | Final-Code name | Value used |
| --- | --- | ---: |
| `theta` | `GDMR_THETA` | `0.078` |
| `kappa_1` | `GDMR_KAPPA1` | `5.5` |
| `kappa_2` | `GDMR_KAPPA2` | `0.1` |
| `v_0` | `GDMR_V0` | `0.114` |
| `v'_0` | `GDMR_VP0` | `0.110` |
| `alpha_1` | `GDMR_DELTA1` | `0.94` |
| `alpha_2` | `GDMR_DELTA2` | `0.94` |
| `xi_1` | `GDMR_XI1` | `2.689` |
| `xi_2` | `GDMR_XI2` | `0.502` |
| `rho_12 = tilde rho_12` | `GDMR_RHO12` | `-0.982` |
| `rho_13 = tilde rho_13` | `GDMR_RHO13` | `-0.727` |
| `rho_23` | `GDMR_RHO23` | `0.59` |

Important note:

- The screenshot also shows `tilde rho_23 = -0.656`.
- That quantity was **not** plugged into the current code as `GDMR_RHO23`.
- The actual code run used `GDMR_RHO23 = 0.59`.
- Reason: the current `Final Code`-style implementation expects the actual
  correlation triple `(rho12, rho13, rho23)` for the Brownian correlation
  matrix, not a transformed `tilde rho_23` quantity.

## Contract-Side Assumptions

The screenshots give the model-side parameter block, but not the full
contract-side setup. This test used:

| Quantity | Value |
| --- | ---: |
| `GDMR_R` | `0.0` |
| `GDMR_S0` | `100.0` |
| `GDMR_MATURITY` | `1.0` |
| Payoff | Bermudan put |

Strike is varied by scenario:

- ATM: `GDMR_STRIKE=100`
- ITM put: `GDMR_STRIKE=110`
- OTM put: `GDMR_STRIKE=90`

## Correlation Admissibility Check

The chosen actual-code correlation triple is:

```text
rho12 = -0.982
rho13 = -0.727
rho23 = 0.59
```

Its correlation-matrix determinant is positive:

```text
det = 0.00146552
```

So this block is admissible for the current implementation.

## Numerical Run Block

All production runs use the same numerical block:

```text
GDMR_EXERCISE_DATES=100
GDMR_EULER_STEPS=600
GDMR_LSMC_PATHS=1000000
GDMR_LSMC_LOW_PATHS=1000000
GDMR_LSMC_SEED=2026
GDMR_LSMC_LOW_SEED=2103
GDMR_HYBRID_PATHS=20000
GDMR_HYBRID_LOW_PATHS=20000
GDMR_HYBRID_ASSET_POINTS=181
GDMR_HYBRID_ASSET_LOW_FACTOR=0.35
GDMR_HYBRID_ASSET_HIGH_FACTOR=3.00
GDMR_HYBRID_VOL_QUANTILE=0.997
GDMR_HYBRID_FST_PAD_FACTOR=4
GDMR_HYBRID_FST_BATCH_SIZE=256
GDMR_HYBRID_SEED=2026
GDMR_HYBRID_LOW_SEED=2103
```

## Scenario Summary

| Scenario | `S0` | `K` | Benchmark direct | Benchmark direct SE | Benchmark low | Benchmark low SE | Hybrid direct | Hybrid direct SE | Hybrid low | Hybrid low SE | Hybrid direct rel. err. | Hybrid low rel. err. | Benchmark direct-low gap | Hybrid direct-low gap |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ATM | `100` | `100` | `11.328264` | `0.015868` | `11.309356` | `0.015856` | `11.237388` | `0.011841` | `11.313915` | `0.113156` | `0.802%` | `0.040%` | `-0.167%` | `+0.681%` |
| ITM put | `100` | `110` | `16.599891` | `0.017849` | `16.585665` | `0.017835` | `16.583247` | `0.015360` | `16.683974` | `0.132462` | `0.100%` | `0.593%` | `-0.086%` | `+0.607%` |
| OTM put | `100` | `90` | `7.378255` | `0.013249` | `7.353952` | `0.013230` | `7.328060` | `0.008486` | `7.387622` | `0.092269` | `0.680%` | `0.458%` | `-0.329%` | `+0.813%` |

## Final Interpretation

- Under the BGK screenshot parameter block, the hybrid stays within `1%` of the
  benchmark direct estimator in all three tested strike scenarios.
- The strongest match is the ITM put case with `K=110`, where the hybrid direct
  estimate is only `0.10%` away from the benchmark direct estimate.
- The OTM put case with `K=90` also stays comfortably below `1%` direct error
  at `0.68%`.
- Across ATM, ITM, and OTM, the hybrid low estimator is still close to the
  benchmark low estimator, but its reported standard error remains much larger
  than the benchmark low standard error.
- The direct-low gap is consistently slightly positive for the hybrid and
  slightly negative for the benchmark, which is a stable pattern across all
  three strike scenarios in this BGK setup.

## Implementation Note

To make the non-ATM strike tests valid, the BGK hybrid copy was updated to read
`GDMR_S0`, `GDMR_STRIKE`, and `GDMR_MATURITY` from the environment, matching
the benchmark script and compare-script workflow. Without that fix, the hybrid
script stayed at `K=100` even when the benchmark was run with another strike.
