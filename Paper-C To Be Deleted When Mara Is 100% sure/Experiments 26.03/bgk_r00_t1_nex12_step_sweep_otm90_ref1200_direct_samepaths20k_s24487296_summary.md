# BGK 12-date OTM put step sweep with matched 20,000 paths and steps 24, 48, 72, 96

This note compares LSMC and the tuned Hybrid LSMC-PDE using the same direct path count for both methods.
The comparison is against the fixed 1200-step benchmark reference already saved in the experiment folder.

## Fixed reference

| Scenario | Reference direct | Reference SE | Reference 95% CI | Reference runtime |
| --- | --- | --- | --- | --- |
| `OTM put` | `7.402999` | `0.012459` | `[7.378579, 7.427419]` | `not recorded in saved reference file` |

## Sweep settings

- Euler steps tested: `24, 48, 72, 96`
- LSMC paths: `20000`
- Hybrid paths: `20000`
- Hybrid tuning kept fixed at: asset points `301`, asset range `0.30 / 3.50`, vol quantile `0.999`.

## Results

| Euler steps | Method | Direct price | Direct rel. error | Direct SE | Direct CI width | Runtime |
| --- | --- | --- | --- | --- | --- | --- |
| `24` | `benchmark` | `7.819243` | `5.623%` | `0.100936` | `0.395669` | `0.31 s` |
| `24` | `hybrid` | `7.633807` | `3.118%` | `0.026034` | `0.102055` | `81.19 s` |
| `48` | `benchmark` | `7.563898` | `2.173%` | `0.098998` | `0.388072` | `0.49 s` |
| `48` | `hybrid` | `7.421371` | `0.248%` | `0.026580` | `0.104195` | `82.72 s` |
| `72` | `benchmark` | `7.535388` | `1.788%` | `0.098666` | `0.386771` | `0.50 s` |
| `72` | `hybrid` | `7.372034` | `0.418%` | `0.026674` | `0.104563` | `78.74 s` |
| `96` | `benchmark` | `7.550651` | `1.994%` | `0.098457` | `0.385951` | `0.54 s` |
| `96` | `hybrid` | `7.421711` | `0.253%` | `0.026721` | `0.104748` | `78.47 s` |

Short interpretation:
- Hybrid direct error is lower at steps `24, 48, 72, 96`.
- Total runtime across these four steps is `1.85 s` for LSMC versus `321.12 s` for Hybrid.

Saved CSV: `bgk_r00_t1_nex12_step_sweep_otm90_ref1200_direct_samepaths20k_s24487296_table.csv`