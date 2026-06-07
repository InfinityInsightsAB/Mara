# BGK 12-date K=70 put step sweep with matched 20,000 paths and steps 24, 48, 72, 96

This note compares LSMC and the tuned Hybrid LSMC-PDE using the same direct path count for both methods.
The comparison is against the fixed 1200-step benchmark reference already saved in the experiment folder.

## Fixed reference

| Scenario | Reference direct | Reference SE | Reference 95% CI | Reference runtime |
| --- | --- | --- | --- | --- |
| `K=70 put` | `2.699339` | `0.007474` | `[2.684690, 2.713988]` | `285.47 s` |

## Sweep settings

- Euler steps tested: `24, 48, 72, 96`
- LSMC paths: `20000`
- Hybrid paths: `20000`
- Hybrid tuning kept fixed at: asset points `301`, asset range `0.30 / 3.50`, vol quantile `0.999`.

## Results

| Euler steps | Method | Direct price | Direct rel. error | Direct SE | Direct CI width | Runtime |
| --- | --- | --- | --- | --- | --- | --- |
| `24` | `benchmark` | `2.939875` | `8.911%` | `0.061172` | `0.239794` | `0.35 s` |
| `24` | `hybrid` | `2.881746` | `6.757%` | `0.011822` | `0.046341` | `81.71 s` |
| `48` | `benchmark` | `2.804334` | `3.890%` | `0.059206` | `0.232088` | `0.43 s` |
| `48` | `hybrid` | `2.742245` | `1.589%` | `0.012069` | `0.047312` | `78.10 s` |
| `72` | `benchmark` | `2.739173` | `1.476%` | `0.057802` | `0.226584` | `0.50 s` |
| `72` | `hybrid` | `2.714444` | `0.560%` | `0.012206` | `0.047847` | `78.67 s` |
| `96` | `benchmark` | `2.719517` | `0.748%` | `0.058068` | `0.227627` | `0.57 s` |
| `96` | `hybrid` | `2.731354` | `1.186%` | `0.012124` | `0.047525` | `78.37 s` |

Short interpretation:
- Hybrid direct error is lower at steps `24, 48, 72`.
- LSMC direct error is lower at steps `96`.
- Total runtime across these four steps is `1.85 s` for LSMC versus `316.85 s` for Hybrid.

Saved CSV: `bgk_r00_t1_nex12_step_sweep_k70_ref1200_direct_samepaths20k_s24487296_table.csv`