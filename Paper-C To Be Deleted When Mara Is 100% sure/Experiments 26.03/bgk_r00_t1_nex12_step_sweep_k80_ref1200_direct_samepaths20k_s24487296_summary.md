# BGK 12-date K=80 put step sweep with matched 20,000 paths and steps 24, 48, 72, 96

This note compares LSMC and the tuned Hybrid LSMC-PDE using the same direct path count for both methods.
The comparison is against the fixed 1200-step benchmark reference already saved in the experiment folder.

## Fixed reference

| Scenario | Reference direct | Reference SE | Reference 95% CI | Reference runtime |
| --- | --- | --- | --- | --- |
| `K=80 put` | `4.596899` | `0.009874` | `[4.577546, 4.616252]` | `312.99 s` |

## Sweep settings

- Euler steps tested: `24, 48, 72, 96`
- LSMC paths: `20000`
- Hybrid paths: `20000`
- Hybrid tuning kept fixed at: asset points `301`, asset range `0.30 / 3.50`, vol quantile `0.999`.

## Results

| Euler steps | Method | Direct price | Direct rel. error | Direct SE | Direct CI width | Runtime |
| --- | --- | --- | --- | --- | --- | --- |
| `24` | `benchmark` | `4.939152` | `7.445%` | `0.080613` | `0.316003` | `0.38 s` |
| `24` | `hybrid` | `4.817993` | `4.810%` | `0.018118` | `0.071023` | `81.11 s` |
| `48` | `benchmark` | `4.743693` | `3.193%` | `0.077914` | `0.305423` | `0.45 s` |
| `48` | `hybrid` | `4.635146` | `0.832%` | `0.018497` | `0.072507` | `79.17 s` |
| `72` | `benchmark` | `4.672537` | `1.645%` | `0.076738` | `0.300813` | `0.49 s` |
| `72` | `hybrid` | `4.597431` | `0.012%` | `0.018645` | `0.073089` | `78.68 s` |
| `96` | `benchmark` | `4.676959` | `1.742%` | `0.076453` | `0.299696` | `0.62 s` |
| `96` | `hybrid` | `4.627596` | `0.668%` | `0.018625` | `0.073010` | `78.89 s` |

Short interpretation:
- Hybrid direct error is lower at steps `24, 48, 72, 96`.
- Total runtime across these four steps is `1.94 s` for LSMC versus `317.85 s` for Hybrid.

Saved CSV: `bgk_r00_t1_nex12_step_sweep_k80_ref1200_direct_samepaths20k_s24487296_table.csv`