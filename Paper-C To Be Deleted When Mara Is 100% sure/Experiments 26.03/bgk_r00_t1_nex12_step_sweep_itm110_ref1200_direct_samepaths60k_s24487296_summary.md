# BGK 12-date ITM put step sweep with matched 60,000 paths and steps 24, 48, 72, 96

This note compares LSMC and the tuned Hybrid LSMC-PDE using the same direct path count for both methods.
The comparison is against the fixed 1200-step benchmark reference already saved in the experiment folder.

## Fixed reference

| Scenario | Reference direct | Reference SE | Reference 95% CI | Reference runtime |
| --- | --- | --- | --- | --- |
| `ITM put` | `16.645784` | `0.017243` | `[16.611988, 16.679580]` | `not recorded in saved reference file` |

## Sweep settings

- Euler steps tested: `24, 48, 72, 96`
- LSMC paths: `60000`
- Hybrid paths: `60000`
- Hybrid tuning kept fixed at: asset points `301`, asset range `0.30 / 3.50`, vol quantile `0.999`.

## Results

| Euler steps | Method | Direct price | Direct rel. error | Direct SE | Direct CI width | Runtime |
| --- | --- | --- | --- | --- | --- | --- |
| `24` | `benchmark` | `16.966400` | `1.926%` | `0.079271` | `0.310742` | `0.73 s` |
| `24` | `hybrid` | `16.973104` | `1.966%` | `0.025929` | `0.101642` | `244.71 s` |
| `48` | `benchmark` | `16.729168` | `0.501%` | `0.079542` | `0.311805` | `1.04 s` |
| `48` | `hybrid` | `16.718825` | `0.439%` | `0.026147` | `0.102497` | `242.28 s` |
| `72` | `benchmark` | `16.785116` | `0.837%` | `0.080321` | `0.314858` | `1.18 s` |
| `72` | `hybrid` | `16.653809` | `0.048%` | `0.026208` | `0.102736` | `238.75 s` |
| `96` | `benchmark` | `16.705637` | `0.360%` | `0.077739` | `0.304737` | `1.45 s` |
| `96` | `hybrid` | `16.632334` | `0.081%` | `0.026164` | `0.102563` | `236.16 s` |

Short interpretation:
- Hybrid direct error is lower at steps `48, 72, 96`.
- LSMC direct error is lower at steps `24`.
- Total runtime across these four steps is `4.40 s` for LSMC versus `961.90 s` for Hybrid.

Saved CSV: `bgk_r00_t1_nex12_step_sweep_itm110_ref1200_direct_samepaths60k_s24487296_table.csv`