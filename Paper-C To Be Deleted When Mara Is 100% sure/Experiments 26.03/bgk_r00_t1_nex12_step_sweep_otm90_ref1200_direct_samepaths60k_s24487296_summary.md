# BGK 12-date OTM put step sweep with matched 60,000 paths and steps 24, 48, 72, 96

This note compares LSMC and the tuned Hybrid LSMC-PDE using the same direct path count for both methods.
The comparison is against the fixed 1200-step benchmark reference already saved in the experiment folder.

## Fixed reference

| Scenario | Reference direct | Reference SE | Reference 95% CI | Reference runtime |
| --- | --- | --- | --- | --- |
| `OTM put` | `7.402999` | `0.012459` | `[7.378579, 7.427419]` | `not recorded in saved reference file` |

## Sweep settings

- Euler steps tested: `24, 48, 72, 96`
- LSMC paths: `60000`
- Hybrid paths: `60000`
- Hybrid tuning kept fixed at: asset points `301`, asset range `0.30 / 3.50`, vol quantile `0.999`.

## Results

| Euler steps | Method | Direct price | Direct rel. error | Direct SE | Direct CI width | Runtime |
| --- | --- | --- | --- | --- | --- | --- |
| `24` | `benchmark` | `7.663824` | `3.523%` | `0.058329` | `0.228650` | `0.70 s` |
| `24` | `hybrid` | `7.679239` | `3.731%` | `0.015020` | `0.058877` | `237.81 s` |
| `48` | `benchmark` | `7.533980` | `1.769%` | `0.057264` | `0.224475` | `0.98 s` |
| `48` | `hybrid` | `7.441944` | `0.526%` | `0.015182` | `0.059512` | `245.20 s` |
| `72` | `benchmark` | `7.503911` | `1.363%` | `0.056750` | `0.222460` | `1.16 s` |
| `72` | `hybrid` | `7.392732` | `0.139%` | `0.015294` | `0.059951` | `240.15 s` |
| `96` | `benchmark` | `7.411275` | `0.112%` | `0.055998` | `0.219512` | `1.40 s` |
| `96` | `hybrid` | `7.369734` | `0.449%` | `0.015259` | `0.059815` | `238.44 s` |

Short interpretation:
- Hybrid direct error is lower at steps `48, 72`.
- LSMC direct error is lower at steps `24, 96`.
- Total runtime across these four steps is `4.24 s` for LSMC versus `961.59 s` for Hybrid.

Saved CSV: `bgk_r00_t1_nex12_step_sweep_otm90_ref1200_direct_samepaths60k_s24487296_table.csv`