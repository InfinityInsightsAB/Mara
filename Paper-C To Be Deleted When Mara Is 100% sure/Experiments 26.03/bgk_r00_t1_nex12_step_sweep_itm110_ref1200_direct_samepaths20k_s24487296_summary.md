# BGK 12-date ITM put step sweep with matched 20,000 paths and steps 24, 48, 72, 96

This note compares LSMC and the tuned Hybrid LSMC-PDE using the same direct path count for both methods.
The comparison is against the fixed 1200-step benchmark reference already saved in the experiment folder.

## Fixed reference

| Scenario | Reference direct | Reference SE | Reference 95% CI | Reference runtime |
| --- | --- | --- | --- | --- |
| `ITM put` | `16.645784` | `0.017243` | `[16.611988, 16.679580]` | `not recorded in saved reference file` |

## Sweep settings

- Euler steps tested: `24, 48, 72, 96`
- LSMC paths: `20000`
- Hybrid paths: `20000`
- Hybrid tuning kept fixed at: asset points `301`, asset range `0.30 / 3.50`, vol quantile `0.999`.

## Results

| Euler steps | Method | Direct price | Direct rel. error | Direct SE | Direct CI width | Runtime |
| --- | --- | --- | --- | --- | --- | --- |
| `24` | `benchmark` | `17.073508` | `2.570%` | `0.134578` | `0.527546` | `1.17 s` |
| `24` | `hybrid` | `16.890067` | `1.468%` | `0.044810` | `0.175654` | `76.83 s` |
| `48` | `benchmark` | `16.849004` | `1.221%` | `0.135565` | `0.531415` | `0.46 s` |
| `48` | `hybrid` | `16.683788` | `0.228%` | `0.045516` | `0.178423` | `76.35 s` |
| `72` | `benchmark` | `16.774434` | `0.773%` | `0.134824` | `0.528510` | `0.43 s` |
| `72` | `hybrid` | `16.618575` | `0.163%` | `0.045393` | `0.177942` | `76.22 s` |
| `96` | `benchmark` | `16.739208` | `0.561%` | `0.136608` | `0.535503` | `0.60 s` |
| `96` | `hybrid` | `16.713479` | `0.407%` | `0.045520` | `0.178438` | `76.91 s` |

Short interpretation:
- Hybrid direct error is lower at steps `24, 48, 72, 96`.
- Total runtime across these four steps is `2.66 s` for LSMC versus `306.30 s` for Hybrid.

Saved CSV: `bgk_r00_t1_nex12_step_sweep_itm110_ref1200_direct_samepaths20k_s24487296_table.csv`