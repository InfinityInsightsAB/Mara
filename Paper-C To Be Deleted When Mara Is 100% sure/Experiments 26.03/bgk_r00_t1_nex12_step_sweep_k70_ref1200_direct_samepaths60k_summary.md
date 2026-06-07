# BGK 12-date K=70 put step sweep with matched 60,000 paths

This note compares LSMC and the tuned Hybrid LSMC-PDE using the same direct path count for both methods.
Direct relative errors are measured against the fixed 1200-step benchmark reference from `bgk_r00_t1_nex12_benchmark_steps1200_paths1200000_k80_k70_table.csv`.

## Fixed reference

| Scenario | Reference direct | Reference SE | Reference 95% CI | Reference runtime |
| --- | --- | --- | --- | --- |
| `K=70 put` | `2.699339` | `0.007474` | `[2.684690, 2.713988]` | `285.47 s` |

## Sweep settings

- Euler steps tested: `12, 24, 48, 72, 120`
- LSMC paths: `60000`
- Hybrid paths: `60000`
- Hybrid tuning kept fixed at: asset points `301`, asset range `0.30 / 3.50`, vol quantile `0.999`.

## Results

| Euler steps | Method | Direct price | Direct SE | Direct 95% CI | Direct rel. error | Rel. error CI | Runtime |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `12` | `benchmark` | `3.132823` | `0.037017` | `[3.060270, 3.205376]` | `16.059%` | `[13.371%, 18.747%]` | `0.53 s` |
| `12` | `hybrid` | `3.151099` | `0.006606` | `[3.138151, 3.164047]` | `16.736%` | `[16.256%, 17.216%]` | `229.58 s` |
| `24` | `benchmark` | `2.908805` | `0.035778` | `[2.838680, 2.978930]` | `7.760%` | `[5.162%, 10.358%]` | `0.74 s` |
| `24` | `hybrid` | `2.896303` | `0.006783` | `[2.883008, 2.909597]` | `7.297%` | `[6.804%, 7.789%]` | `245.04 s` |
| `48` | `benchmark` | `2.801678` | `0.034296` | `[2.734458, 2.868898]` | `3.791%` | `[1.301%, 6.282%]` | `1.03 s` |
| `48` | `hybrid` | `2.750802` | `0.006821` | `[2.737433, 2.764171]` | `1.906%` | `[1.411%, 2.402%]` | `239.68 s` |
| `72` | `benchmark` | `2.766338` | `0.034333` | `[2.699045, 2.833631]` | `2.482%` | `[0.000%, 4.975%]` | `1.24 s` |
| `72` | `hybrid` | `2.722197` | `0.006908` | `[2.708657, 2.735737]` | `0.847%` | `[0.345%, 1.348%]` | `238.82 s` |
| `120` | `benchmark` | `2.693649` | `0.033684` | `[2.627628, 2.759670]` | `0.211%` | `[0.000%, 2.657%]` | `1.72 s` |
| `120` | `hybrid` | `2.693414` | `0.006926` | `[2.679839, 2.706989]` | `0.220%` | `[0.000%, 0.722%]` | `246.13 s` |

Short interpretation:
- Hybrid direct error is lower at steps `24, 48, 72`.
- LSMC direct error is lower at steps `12, 120`.
- Total runtime across the five-step sweep is `5.26 s` for LSMC versus `1199.26 s` for Hybrid.

Saved CSV: `bgk_r00_t1_nex12_step_sweep_k70_ref1200_direct_samepaths60k_table.csv`