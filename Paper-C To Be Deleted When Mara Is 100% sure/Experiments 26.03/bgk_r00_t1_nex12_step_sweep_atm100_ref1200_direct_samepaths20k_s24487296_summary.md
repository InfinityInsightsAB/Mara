# BGK 12-date ATM step sweep with matched 20,000 paths and steps 24, 48, 72, 96

This note compares LSMC and the tuned Hybrid LSMC-PDE using the same direct path count for both methods.
The comparison is against the fixed 1200-step benchmark reference already saved in the experiment folder.

## Fixed reference

| Scenario | Reference direct | Reference SE | Reference 95% CI | Reference runtime |
| --- | --- | --- | --- | --- |
| `ATM` | `11.356823` | `0.015058` | `[11.327309, 11.386337]` | `not recorded in saved reference file` |

## Sweep settings

- Euler steps tested: `24, 48, 72, 96`
- LSMC paths: `20000`
- Hybrid paths: `20000`
- Hybrid tuning kept fixed at: asset points `301`, asset range `0.30 / 3.50`, vol quantile `0.999`.

## Results

| Euler steps | Method | Direct price | Direct rel. error | Direct SE | Direct CI width | Runtime |
| --- | --- | --- | --- | --- | --- | --- |
| `24` | `benchmark` | `11.813959` | `4.025%` | `0.118495` | `0.464500` | `0.35 s` |
| `24` | `hybrid` | `11.584064` | `2.001%` | `0.035230` | `0.138103` | `80.88 s` |
| `48` | `benchmark` | `11.508503` | `1.336%` | `0.119290` | `0.467617` | `0.45 s` |
| `48` | `hybrid` | `11.362764` | `0.052%` | `0.035911` | `0.140771` | `80.39 s` |
| `72` | `benchmark` | `11.464532` | `0.948%` | `0.117430` | `0.460326` | `0.46 s` |
| `72` | `hybrid` | `11.302836` | `0.475%` | `0.035909` | `0.140765` | `78.05 s` |
| `96` | `benchmark` | `11.549213` | `1.694%` | `0.119243` | `0.467433` | `0.53 s` |
| `96` | `hybrid` | `11.376381` | `0.172%` | `0.035998` | `0.141113` | `78.38 s` |

Short interpretation:
- Hybrid direct error is lower at steps `24, 48, 72, 96`.
- Total runtime across these four steps is `1.79 s` for LSMC versus `317.70 s` for Hybrid.

Saved CSV: `bgk_r00_t1_nex12_step_sweep_atm100_ref1200_direct_samepaths20k_s24487296_table.csv`