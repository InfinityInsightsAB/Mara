# BGK 12-date OTM K=80 / K=70 step sweep using 1200-step benchmark references

This note compares LSMC and the tuned Hybrid LSMC-PDE for the OTM strikes `K=80` and `K=70` while Euler steps vary.
Direct relative errors are measured against the fixed benchmark references from `bgk_r00_t1_nex12_benchmark_steps1200_paths1200000_k80_k70_table.csv`.

## Fixed reference table

| Scenario | K | Reference direct | Reference SE | Reference 95% CI | Reference runtime |
| --- | --- | --- | --- | --- | --- |
| `K=80 put` | `80` | `4.596899` | `0.009874` | `[4.577546, 4.616252]` | `312.99 s` |
| `K=70 put` | `70` | `2.699339` | `0.007474` | `[2.684690, 2.713988]` | `285.47 s` |

## Fixed model block

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
GDMR_EXERCISE_DATES=12
```

## Sweep settings

- Euler steps tested: `12, 24, 48, 72, 120`
- Benchmark paths: `1000000`
- Benchmark low paths: `1000000`
- Hybrid paths: `60000`
- Hybrid low paths: `60000`
- Hybrid asset points: `301`
- Hybrid asset range factors: `0.30` / `3.50`
- Hybrid vol quantile: `0.999`

## K=80 put

- Fixed direct reference: `4.596899`
- Fixed direct reference SE: `0.009874`

| Euler steps | Method | Direct price | Direct SE | Direct 95% CI | Direct rel. error | Rel. error CI | Runtime |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `12` | `benchmark` | `5.175336` | `0.011853` | `[5.152104, 5.198568]` | `12.583%` | `[12.078%, 13.089%]` | `9.46 s` |
| `12` | `hybrid` | `5.196682` | `0.010103` | `[5.176881, 5.216483]` | `13.048%` | `[12.617%, 13.478%]` | `218.57 s` |
| `24` | `benchmark` | `4.828087` | `0.011268` | `[4.806002, 4.850172]` | `5.029%` | `[4.549%, 5.510%]` | `10.91 s` |
| `24` | `hybrid` | `4.844432` | `0.010426` | `[4.823998, 4.864866]` | `5.385%` | `[4.940%, 5.829%]` | `240.06 s` |
| `48` | `benchmark` | `4.652622` | `0.010974` | `[4.631113, 4.674131]` | `1.212%` | `[0.744%, 1.680%]` | `15.44 s` |
| `48` | `hybrid` | `4.648764` | `0.010520` | `[4.628144, 4.669385]` | `1.128%` | `[0.680%, 1.577%]` | `236.47 s` |
| `72` | `benchmark` | `4.606658` | `0.010862` | `[4.585368, 4.627948]` | `0.212%` | `[0.000%, 0.675%]` | `20.53 s` |
| `72` | `hybrid` | `4.610083` | `0.010629` | `[4.589249, 4.630917]` | `0.287%` | `[0.000%, 0.740%]` | `234.13 s` |
| `120` | `benchmark` | `4.592270` | `0.010835` | `[4.571033, 4.613507]` | `0.101%` | `[0.000%, 0.563%]` | `29.52 s` |
| `120` | `hybrid` | `4.575419` | `0.010643` | `[4.554559, 4.596279]` | `0.467%` | `[0.013%, 0.921%]` | `233.60 s` |

![K=80 put direct relative error](C:\MDU PhD\Paper C\Experiments 26.03\bgk_r00_t1_nex12_step_sweep_k80_ref1200_direct_relative_error_with_ci.svg)

![K=80 put runtime](C:\MDU PhD\Paper C\Experiments 26.03\bgk_r00_t1_nex12_step_sweep_k80_ref1200_runtime.svg)

Short interpretation:
- Hybrid direct error is lower at steps `48`.
- LSMC direct error is lower at steps `12, 24, 72, 120`.
- Total runtime across the five-step sweep is `85.86 s` for LSMC versus `1162.83 s` for Hybrid.

## K=70 put

- Fixed direct reference: `2.699339`
- Fixed direct reference SE: `0.007474`

| Euler steps | Method | Direct price | Direct SE | Direct 95% CI | Direct rel. error | Rel. error CI | Runtime |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `12` | `benchmark` | `3.111403` | `0.009020` | `[3.093724, 3.129082]` | `15.265%` | `[14.610%, 15.920%]` | `8.45 s` |
| `12` | `hybrid` | `3.151099` | `0.006606` | `[3.138151, 3.164047]` | `16.736%` | `[16.256%, 17.216%]` | `220.01 s` |
| `24` | `benchmark` | `2.872252` | `0.008584` | `[2.855427, 2.889077]` | `6.406%` | `[5.782%, 7.029%]` | `10.90 s` |
| `24` | `hybrid` | `2.896303` | `0.006783` | `[2.883008, 2.909597]` | `7.297%` | `[6.804%, 7.789%]` | `235.24 s` |
| `48` | `benchmark` | `2.739336` | `0.008305` | `[2.723058, 2.755614]` | `1.482%` | `[0.879%, 2.085%]` | `15.66 s` |
| `48` | `hybrid` | `2.750802` | `0.006821` | `[2.737433, 2.764171]` | `1.906%` | `[1.411%, 2.402%]` | `233.17 s` |
| `72` | `benchmark` | `2.707194` | `0.008222` | `[2.691079, 2.723309]` | `0.291%` | `[0.000%, 0.888%]` | `20.00 s` |
| `72` | `hybrid` | `2.722197` | `0.006908` | `[2.708657, 2.735737]` | `0.847%` | `[0.345%, 1.348%]` | `233.83 s` |
| `120` | `benchmark` | `2.698996` | `0.008204` | `[2.682916, 2.715076]` | `0.013%` | `[0.000%, 0.608%]` | `29.53 s` |
| `120` | `hybrid` | `2.693414` | `0.006926` | `[2.679839, 2.706989]` | `0.220%` | `[0.000%, 0.722%]` | `235.48 s` |

![K=70 put direct relative error](C:\MDU PhD\Paper C\Experiments 26.03\bgk_r00_t1_nex12_step_sweep_k70_ref1200_direct_relative_error_with_ci.svg)

![K=70 put runtime](C:\MDU PhD\Paper C\Experiments 26.03\bgk_r00_t1_nex12_step_sweep_k70_ref1200_runtime.svg)

Short interpretation:
- LSMC direct error is lower at steps `12, 24, 48, 72, 120`.
- Total runtime across the five-step sweep is `84.54 s` for LSMC versus `1157.72 s` for Hybrid.

Saved CSV: `bgk_r00_t1_nex12_step_sweep_k80_k70_ref1200_direct_table.csv`