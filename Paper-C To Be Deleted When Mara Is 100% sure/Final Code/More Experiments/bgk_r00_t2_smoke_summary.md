# BGK gDMR Comparison with `r=0.0`, `T=2.0` (smoke)

This note records the local comparison suite run from `Final Code/More Experiments`.
The `LSMC Benchmark` values are the benchmark reference in every row, and the `Hybrid LSMC-PDE with FFT` values are compared against them.

## Scenario Summary

| Scenario | `S0` | `K` | Benchmark direct | Benchmark direct SE | Benchmark low | Benchmark low SE | Hybrid direct | Hybrid direct SE | Hybrid low | Hybrid low SE | Hybrid direct rel. err. | Hybrid low rel. err. | Benchmark direct-low gap | Hybrid direct-low gap |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ATM | `100` | `100` | `15.780367` | `0.151181` | `15.708977` | `0.150707` | `15.301085` | `0.113295` | `14.589760` | `0.434853` | `3.037%` | `7.125%` | `-0.452%` | `-4.649%` |
| ITM put | `100` | `110` | `21.025804` | `0.171661` | `20.946485` | `0.171200` | `20.620736` | `0.138654` | `19.691469` | `0.500400` | `1.927%` | `5.992%` | `-0.377%` | `-4.506%` |
| OTM put | `100` | `90` | `11.404303` | `0.128685` | `11.406096` | `0.128864` | `10.963437` | `0.088376` | `10.477757` | `0.365338` | `3.866%` | `8.139%` | `0.016%` | `-4.430%` |

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
GDMR_EXERCISE_DATES=20
GDMR_EULER_STEPS=120
GDMR_LSMC_PATHS=20000
GDMR_LSMC_LOW_PATHS=20000
GDMR_LSMC_SEED=2026
GDMR_LSMC_LOW_SEED=2103
GDMR_HYBRID_PATHS=2000
GDMR_HYBRID_LOW_PATHS=2000
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

- CSV table: `bgk_r00_t2_smoke_table.csv`
