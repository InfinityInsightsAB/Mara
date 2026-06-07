# BGK gDMR Comparison with `r=0.03` (smoke)

This note records the local comparison suite run from `Final Code/More Experimens`.
The `LSMC Benchmark` values are the benchmark reference in every row, and the `Hybrid LSMC-PDE with FFT` values are compared against them.

## Scenario Summary

| Scenario | `S0` | `K` | Benchmark direct | Benchmark direct SE | Benchmark low | Benchmark low SE | Hybrid direct | Hybrid direct SE | Hybrid low | Hybrid low SE | Hybrid direct rel. err. | Hybrid low rel. err. | Benchmark direct-low gap | Hybrid direct-low gap |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ATM | `100` | `100` | `10.564509` | `0.109169` | `10.477819` | `0.108100` | `10.196112` | `0.079589` | `9.922017` | `0.322614` | `3.487%` | `5.305%` | `-0.821%` | `-2.688%` |
| ITM put | `100` | `110` | `15.506694` | `0.120756` | `15.393568` | `0.120292` | `15.151041` | `0.106684` | `14.933162` | `0.361721` | `2.294%` | `2.991%` | `-0.730%` | `-1.438%` |
| OTM put | `100` | `90` | `6.874711` | `0.090511` | `6.815769` | `0.089314` | `6.616517` | `0.056010` | `6.499540` | `0.266469` | `3.756%` | `4.640%` | `-0.857%` | `-1.768%` |

## Model Block

```text
GDMR_S0=100.0
GDMR_V0=0.114
GDMR_VP0=0.110
GDMR_R=0.03
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

- CSV table: `bgk_r03_smoke_table.csv`
