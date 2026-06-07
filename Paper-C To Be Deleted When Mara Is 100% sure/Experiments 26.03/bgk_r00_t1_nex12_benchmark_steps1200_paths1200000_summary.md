# BGK Testing-aligned gDMR benchmark with `r=0.0`, `T=1.0`, `N_ex=12`, `N_steps=1200`, `N_paths=1200000`

This note records the isolated `LSMC Benchmark` run for the BGK Testing-aligned gDMR family from `Experiments 26.03`.
It keeps the same `12` Bermudan exercise dates used in the local experiment suite and increases the Euler steps to `1200` with `1,200,000` benchmark paths for both the direct and low estimators.

## Scenario Summary

| Scenario | `S0` | `K` | Benchmark direct | Benchmark direct SE | Benchmark low | Benchmark low SE | Benchmark direct-low gap |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ATM | `100` | `100` | `11.356823` | `0.015058` | `11.322354` | `0.015030` | `0.304%` |
| ITM put | `100` | `110` | `16.645784` | `0.017243` | `16.616607` | `0.017233` | `0.175%` |
| OTM put | `100` | `90` | `7.402999` | `0.012459` | `7.381181` | `0.012444` | `0.295%` |

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
GDMR_T=1.0
```

## Numerical Block

```text
GDMR_EXERCISE_DATES=12
GDMR_EULER_STEPS=1200
GDMR_LSMC_PATHS=1200000
GDMR_LSMC_LOW_PATHS=1200000
GDMR_LSMC_SEED=2026
GDMR_LSMC_LOW_SEED=2103
```

## Saved Outputs

- CSV table: `bgk_r00_t1_nex12_benchmark_steps1200_paths1200000_table.csv`
