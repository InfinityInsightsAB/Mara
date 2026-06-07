# BGK gDMR Comparison with `r=0.0`, `T=1.0`, `delta1=delta2=0.5` (smoke)

This note records the local comparison suite run from `Final Code/More Experiments`.
The `LSMC Benchmark` values are the benchmark reference in every row, and the `Hybrid LSMC-PDE with FFT` values are compared against them.

## Scenario Summary

| Scenario | `S0` | `K` | Benchmark direct | Benchmark direct SE | Benchmark low | Benchmark low SE | Hybrid direct | Hybrid direct SE | Hybrid low | Hybrid low SE | Hybrid direct rel. err. | Hybrid low rel. err. | Benchmark direct-low gap | Hybrid direct-low gap |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ATM | `100` | `100` | `11.550637` | `0.139220` | `11.425474` | `0.137844` | `10.930410` | `0.098686` | `10.667451` | `0.394221` | `5.370%` | `6.634%` | `-1.084%` | `-2.406%` |
| ITM put | `100` | `110` | `15.826569` | `0.155728` | `15.574421` | `0.153692` | `15.376699` | `0.126530` | `14.812481` | `0.450648` | `2.843%` | `4.892%` | `-1.593%` | `-3.669%` |
| OTM put | `100` | `90` | `8.345080` | `0.118317` | `8.266285` | `0.117075` | `7.795071` | `0.074023` | `7.604091` | `0.328802` | `6.591%` | `8.011%` | `-0.944%` | `-2.450%` |

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
GDMR_DELTA1=0.5
GDMR_DELTA2=0.5
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

- CSV table: `bgk_r00_t1_delta05_smoke_table.csv`
