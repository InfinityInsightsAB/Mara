# BGK 12-date K=70 put step sweep with matched 60,000 paths and steps 24, 48, 72, 96

This note compares LSMC and the tuned Hybrid LSMC-PDE using the same direct path count for both methods.
The comparison is against the fixed 1200-step benchmark reference already saved in the experiment folder.

## Fixed reference

| Scenario | Reference direct | Reference SE | Reference 95% CI | Reference runtime |
| --- | --- | --- | --- | --- |
| `K=70 put` | `2.699339` | `0.007474` | `[2.684690, 2.713988]` | `285.47 s` |

## Sweep settings

- Euler steps tested: `24, 48, 72, 96`
- LSMC paths: `60000`
- Hybrid paths: `60000`
- Hybrid tuning kept fixed at: asset points `301`, asset range `0.30 / 3.50`, vol quantile `0.999`.

## Results

| Euler steps | Method | Direct price | Direct rel. error | Direct SE | Direct CI width | Runtime |
| --- | --- | --- | --- | --- | --- | --- |
| `24` | `benchmark` | `2.908805` | `7.760%` | `0.035778` | `0.140250` | `0.66 s` |
| `24` | `hybrid` | `2.896303` | `7.297%` | `0.006783` | `0.026589` | `230.72 s` |
| `48` | `benchmark` | `2.801678` | `3.791%` | `0.034296` | `0.134440` | `0.93 s` |
| `48` | `hybrid` | `2.750802` | `1.906%` | `0.006821` | `0.026738` | `230.61 s` |
| `72` | `benchmark` | `2.766338` | `2.482%` | `0.034333` | `0.134585` | `1.21 s` |
| `72` | `hybrid` | `2.722197` | `0.847%` | `0.006908` | `0.027079` | `233.90 s` |
| `96` | `benchmark` | `2.711129` | `0.437%` | `0.033759` | `0.132335` | `1.38 s` |
| `96` | `hybrid` | `2.706466` | `0.264%` | `0.006861` | `0.026897` | `230.50 s` |

Short interpretation:
- Hybrid direct error is lower at steps `24, 48, 72, 96`.
- Total runtime across these four steps is `4.19 s` for LSMC versus `925.73 s` for Hybrid.

Saved CSV: `bgk_r00_t1_nex12_step_sweep_k70_ref1200_direct_samepaths60k_s24487296_table.csv`