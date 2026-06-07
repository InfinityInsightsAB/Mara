# BGK 12-date ATM step sweep with matched 60,000 paths and steps 24, 48, 72, 96

This note compares LSMC and the tuned Hybrid LSMC-PDE using the same direct path count for both methods.
The comparison is against the fixed 1200-step benchmark reference already saved in the experiment folder.

## Fixed reference

| Scenario | Reference direct | Reference SE | Reference 95% CI | Reference runtime |
| --- | --- | --- | --- | --- |
| `ATM` | `11.356823` | `0.015058` | `[11.327309, 11.386337]` | `not recorded in saved reference file` |

## Sweep settings

- Euler steps tested: `24, 48, 72, 96`
- LSMC paths: `60000`
- Hybrid paths: `60000`
- Hybrid tuning kept fixed at: asset points `301`, asset range `0.30 / 3.50`, vol quantile `0.999`.

## Results

| Euler steps | Method | Direct price | Direct rel. error | Direct SE | Direct CI width | Runtime |
| --- | --- | --- | --- | --- | --- | --- |
| `24` | `benchmark` | `11.631100` | `2.415%` | `0.069024` | `0.270574` | `0.71 s` |
| `24` | `hybrid` | `11.650940` | `2.590%` | `0.020365` | `0.079830` | `245.87 s` |
| `48` | `benchmark` | `11.496757` | `1.232%` | `0.069573` | `0.272726` | `0.90 s` |
| `48` | `hybrid` | `11.391168` | `0.302%` | `0.020573` | `0.080645` | `236.94 s` |
| `72` | `benchmark` | `11.496193` | `1.227%` | `0.069157` | `0.271095` | `1.25 s` |
| `72` | `hybrid` | `11.332296` | `0.216%` | `0.020668` | `0.081018` | `241.84 s` |
| `96` | `benchmark` | `11.392029` | `0.310%` | `0.067227` | `0.263530` | `1.34 s` |
| `96` | `hybrid` | `11.310017` | `0.412%` | `0.020633` | `0.080879` | `246.58 s` |

Short interpretation:
- Hybrid direct error is lower at steps `48, 72`.
- LSMC direct error is lower at steps `24, 96`.
- Total runtime across these four steps is `4.19 s` for LSMC versus `971.23 s` for Hybrid.

Saved CSV: `bgk_r00_t1_nex12_step_sweep_atm100_ref1200_direct_samepaths60k_s24487296_table.csv`