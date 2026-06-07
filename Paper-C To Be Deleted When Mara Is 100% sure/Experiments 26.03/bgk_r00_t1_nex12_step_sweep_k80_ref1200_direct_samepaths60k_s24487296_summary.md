# BGK 12-date K=80 put step sweep with matched 60,000 paths and steps 24, 48, 72, 96

This note compares LSMC and the tuned Hybrid LSMC-PDE using the same direct path count for both methods.
The comparison is against the fixed 1200-step benchmark reference already saved in the experiment folder.

## Fixed reference

| Scenario | Reference direct | Reference SE | Reference 95% CI | Reference runtime |
| --- | --- | --- | --- | --- |
| `K=80 put` | `4.596899` | `0.009874` | `[4.577546, 4.616252]` | `312.99 s` |

## Sweep settings

- Euler steps tested: `24, 48, 72, 96`
- LSMC paths: `60000`
- Hybrid paths: `60000`
- Hybrid tuning kept fixed at: asset points `301`, asset range `0.30 / 3.50`, vol quantile `0.999`.

## Results

| Euler steps | Method | Direct price | Direct rel. error | Direct SE | Direct CI width | Runtime |
| --- | --- | --- | --- | --- | --- | --- |
| `24` | `benchmark` | `4.842198` | `5.336%` | `0.046816` | `0.183519` | `0.65 s` |
| `24` | `hybrid` | `4.844432` | `5.385%` | `0.010426` | `0.040868` | `247.32 s` |
| `48` | `benchmark` | `4.728836` | `2.870%` | `0.045527` | `0.178466` | `0.91 s` |
| `48` | `hybrid` | `4.648764` | `1.128%` | `0.010520` | `0.041240` | `236.51 s` |
| `72` | `benchmark` | `4.662578` | `1.429%` | `0.044924` | `0.176102` | `1.17 s` |
| `72` | `hybrid` | `4.610083` | `0.287%` | `0.010629` | `0.041668` | `230.58 s` |
| `96` | `benchmark` | `4.621292` | `0.531%` | `0.044631` | `0.174954` | `1.39 s` |
| `96` | `hybrid` | `4.589202` | `0.167%` | `0.010591` | `0.041516` | `230.07 s` |

Short interpretation:
- Hybrid direct error is lower at steps `48, 72, 96`.
- LSMC direct error is lower at steps `24`.
- Total runtime across these four steps is `4.12 s` for LSMC versus `944.48 s` for Hybrid.

Saved CSV: `bgk_r00_t1_nex12_step_sweep_k80_ref1200_direct_samepaths60k_s24487296_table.csv`