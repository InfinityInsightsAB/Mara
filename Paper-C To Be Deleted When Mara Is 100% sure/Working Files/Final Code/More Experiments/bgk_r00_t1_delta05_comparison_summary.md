# BGK gDMR Comparison with `r=0.0`, `T=1.0`, `delta1=delta2=0.5` (results)

This note records the local comparison suite run from `Final Code/More Experiments`.
The `LSMC Benchmark` values are the benchmark reference in every row, and the `Hybrid LSMC-PDE with FFT` values are compared against them.

## Scenario Summary

| Scenario | `S0` | `K` | Benchmark direct | Benchmark direct SE | Benchmark low | Benchmark low SE | Hybrid direct | Hybrid direct SE | Hybrid low | Hybrid low SE | Hybrid direct rel. err. | Hybrid low rel. err. | Benchmark direct-low gap | Hybrid direct-low gap |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ATM | `100` | `100` | `10.548060` | `0.018176` | `10.519125` | `0.018145` | `10.484748` | `0.013958` | `10.544421` | `0.125869` | `0.600%` | `0.240%` | `-0.274%` | `0.569%` |
| ITM put | `100` | `110` | `14.719728` | `0.019787` | `14.691320` | `0.019752` | `15.035798` | `0.018057` | `14.798167` | `0.144063` | `2.147%` | `0.727%` | `-0.193%` | `-1.580%` |
| OTM put | `100` | `90` | `7.512186` | `0.015707` | `7.496058` | `0.015683` | `7.415154` | `0.010424` | `7.554493` | `0.105602` | `1.292%` | `0.780%` | `-0.215%` | `1.879%` |

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

- CSV table: `bgk_r00_t1_delta05_comparison_table.csv`
