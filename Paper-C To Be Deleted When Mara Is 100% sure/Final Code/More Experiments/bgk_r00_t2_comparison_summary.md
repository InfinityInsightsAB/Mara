# BGK gDMR Comparison with `r=0.0`, `T=2.0` (production)

This note records the local comparison suite run from `Final Code/More Experiments`.
The `LSMC Benchmark` values are the benchmark reference in every row, and the `Hybrid LSMC-PDE with FFT` values are compared against them.

## Scenario Summary

| Scenario | `S0` | `K` | Benchmark direct | Benchmark direct SE | Benchmark low | Benchmark low SE | Hybrid direct | Hybrid direct SE | Hybrid low | Hybrid low SE | Hybrid direct rel. err. | Hybrid low rel. err. | Benchmark direct-low gap | Hybrid direct-low gap |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ATM | `100` | `100` | `15.537393` | `0.020775` | `15.506461` | `0.020762` | `15.467526` | `0.016108` | `15.621656` | `0.143677` | `0.450%` | `0.743%` | `-0.199%` | `0.996%` |
| ITM put | `100` | `110` | `20.812594` | `0.023205` | `20.791793` | `0.023188` | `20.796618` | `0.019759` | `20.980861` | `0.164665` | `0.077%` | `0.909%` | `-0.100%` | `0.886%` |
| OTM put | `100` | `90` | `11.200789` | `0.017856` | `11.170787` | `0.017829` | `11.160237` | `0.012533` | `11.270917` | `0.120877` | `0.362%` | `0.896%` | `-0.268%` | `0.992%` |

## Model Block

```text
GDMR_S0=100.0
GDMR_V0=0.114
GDMR_VP0=0.110
GDMR_R=0.0
GDMR_KAPPA1=5.5
GDMR_KAPPA2=0.1
GDMR_THETA=0.078
GDMR_XI1=2.689
GDMR_XI2=0.502
GDMR_DELTA1=0.94
GDMR_DELTA2=0.94
GDMR_RHO12=-0.982
GDMR_RHO13=-0.727
GDMR_RHO23=0.59
```

## Numerical Block

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

## Correlation Note

- The implemented code input uses `GDMR_RHO23=0.59`.
- The screenshot quantity `tilde rho_23=-0.656` is not used as the code correlation input.

## Saved Outputs

- CSV table: `bgk_r00_t2_comparison_table.csv`
