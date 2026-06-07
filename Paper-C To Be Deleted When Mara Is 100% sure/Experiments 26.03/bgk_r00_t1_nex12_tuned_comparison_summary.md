# BGK 12-date Tuned Hybrid Comparison

This note keeps the 12-date BGK benchmark fixed and reruns the hybrid with the best common tuning setting found in `bgk_r00_t1_nex12_hybrid_tuning_summary.md`.

## Tuned hybrid setting

- Label: `paths60k_grid301_wide_q999`
- Hybrid paths: `60000`
- Hybrid low paths: `60000`
- Asset points: `301`
- Asset range factors: `0.30` / `3.50`
- Vol truncation quantile: `0.999`

## Scenario summary

| Scenario | K | Benchmark direct | Hybrid direct | Hybrid direct rel. error | Benchmark low | Hybrid low | Hybrid low rel. error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `ATM` | `100` | `11.371204` | `11.359836` | `0.100%` | `11.348587` | `11.320776` | `0.245%` |
| `ITM put` | `110` | `16.637388` | `16.680641` | `0.260%` | `16.627006` | `16.597060` | `0.180%` |
| `OTM put` | `90` | `7.426156` | `7.414778` | `0.153%` | `7.406685` | `7.402772` | `0.053%` |

Saved CSV: `bgk_r00_t1_nex12_tuned_comparison_table.csv`