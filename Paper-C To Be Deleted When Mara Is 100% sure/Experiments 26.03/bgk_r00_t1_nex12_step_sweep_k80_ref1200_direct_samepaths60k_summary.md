# BGK 12-date K=80 put step sweep with matched 60,000 paths

This note compares LSMC and the tuned Hybrid LSMC-PDE using the same direct path count for both methods.
Direct relative errors are measured against the fixed 1200-step benchmark reference from `bgk_r00_t1_nex12_benchmark_steps1200_paths1200000_k80_k70_table.csv`.

## Fixed reference

| Scenario | Reference direct | Reference SE | Reference 95% CI | Reference runtime |
| --- | --- | --- | --- | --- |
| `K=80 put` | `4.596899` | `0.009874` | `[4.577546, 4.616252]` | `312.99 s` |

## Sweep settings

- Euler steps tested: `12, 24, 48, 72, 120`
- LSMC paths: `60000`
- Hybrid paths: `60000`
- Hybrid tuning kept fixed at: asset points `301`, asset range `0.30 / 3.50`, vol quantile `0.999`.

## Results

| Euler steps | Method | Direct price | Direct SE | Direct 95% CI | Direct rel. error | Rel. error CI | Runtime |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `12` | `benchmark` | `5.233201` | `0.048990` | `[5.137181, 5.329221]` | `13.842%` | `[11.753%, 15.931%]` | `1.35 s` |
| `12` | `hybrid` | `5.196682` | `0.010103` | `[5.176881, 5.216483]` | `13.048%` | `[12.617%, 13.478%]` | `213.21 s` |
| `24` | `benchmark` | `4.842198` | `0.046816` | `[4.750439, 4.933957]` | `5.336%` | `[3.340%, 7.332%]` | `0.71 s` |
| `24` | `hybrid` | `4.844432` | `0.010426` | `[4.823998, 4.864866]` | `5.385%` | `[4.940%, 5.829%]` | `238.82 s` |
| `48` | `benchmark` | `4.728836` | `0.045527` | `[4.639603, 4.818069]` | `2.870%` | `[0.929%, 4.811%]` | `1.29 s` |
| `48` | `hybrid` | `4.648764` | `0.010520` | `[4.628144, 4.669385]` | `1.128%` | `[0.680%, 1.577%]` | `254.98 s` |
| `72` | `benchmark` | `4.662578` | `0.044924` | `[4.574527, 4.750629]` | `1.429%` | `[0.000%, 3.344%]` | `1.24 s` |
| `72` | `hybrid` | `4.610083` | `0.010629` | `[4.589249, 4.630917]` | `0.287%` | `[0.000%, 0.740%]` | `244.96 s` |
| `120` | `benchmark` | `4.563772` | `0.044208` | `[4.477124, 4.650420]` | `0.721%` | `[0.000%, 2.606%]` | `1.62 s` |
| `120` | `hybrid` | `4.575419` | `0.010643` | `[4.554559, 4.596279]` | `0.467%` | `[0.013%, 0.921%]` | `243.00 s` |

Short interpretation:
- Hybrid direct error is lower at steps `12, 48, 72, 120`.
- LSMC direct error is lower at steps `24`.
- Total runtime across the five-step sweep is `6.21 s` for LSMC versus `1194.97 s` for Hybrid.

Saved CSV: `bgk_r00_t1_nex12_step_sweep_k80_ref1200_direct_samepaths60k_table.csv`