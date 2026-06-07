# BGK 12-date benchmark-only run for K=80 and K=70

This note records the isolated LSMC benchmark-only runs for the BGK-style calibrated gDMR model with the same 12-date setup used elsewhere in `Experiments 26.03`.
The only strike changes are `K=80` and `K=70`; all other model and numerical parameters are kept fixed.

## Scenario Summary

| Scenario | K | Benchmark direct | Direct SE | Direct 95% CI | Benchmark low | Low SE | Low 95% CI | Direct-low gap | Runtime |
| --- | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: |
| `K=80 put` | `80` | `4.596899` | `0.009874` | `[4.577546, 4.616252]` | `4.585755` | `0.009860` | `[4.566429, 4.605081]` | `-0.242%` | `312.99 s` |
| `K=70 put` | `70` | `2.699339` | `0.007474` | `[2.684690, 2.713988]` | `2.692367` | `0.007465` | `[2.677736, 2.706998]` | `-0.258%` | `285.47 s` |

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

Saved CSV: `bgk_r00_t1_nex12_benchmark_steps1200_paths1200000_k80_k70_table.csv`