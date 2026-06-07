# BGK Testing-aligned gDMR comparison with `r=0.0`, `T=1.0`, `N_ex=12` (smoke)

This note records the isolated local comparison suite run from `Experiments 26.03`.
It reproduces the original BGK Testing-aligned gDMR family with the production numerical block kept fixed except that the Bermudan exercise dates are reduced from `100` to `12`.
The `LSMC Benchmark` values are the benchmark reference in every row, and the `Hybrid LSMC-PDE with FFT` values are compared against them.

## Scenario Summary

| Scenario | `S0` | `K` | Benchmark direct | Benchmark direct SE | Benchmark low | Benchmark low SE | Hybrid direct | Hybrid direct SE | Hybrid low | Hybrid low SE | Hybrid direct rel. err. | Hybrid low rel. err. | Benchmark direct-low gap | Hybrid direct-low gap |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ATM | `100` | `100` | `11.356561` | `0.118632` | `11.671608` | `0.119163` | `11.510342` | `0.115753` | `11.287133` | `0.366118` | `1.354%` | `3.294%` | `2.774%` | `-1.939%` |
| ITM put | `100` | `110` | `16.707010` | `0.134027` | `16.920123` | `0.133878` | `16.819009` | `0.146128` | `16.705293` | `0.431871` | `0.670%` | `1.270%` | `1.276%` | `-0.676%` |
| OTM put | `100` | `90` | `7.388515` | `0.098202` | `7.560039` | `0.098304` | `7.573821` | `0.086412` | `7.367058` | `0.299991` | `2.508%` | `2.553%` | `2.321%` | `-2.730%` |

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
GDMR_EXERCISE_DATES=12
GDMR_EULER_STEPS=600
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

- CSV table: `bgk_r00_t1_nex12_smoke_table.csv`
