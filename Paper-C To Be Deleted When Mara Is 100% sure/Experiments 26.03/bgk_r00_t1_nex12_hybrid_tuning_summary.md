# BGK 12-date Hybrid Tuning

This note tunes the hybrid side only for the 12-date BGK Testing-aligned experiment.
Benchmark values are reused from `bgk_r00_t1_nex12_comparison_table.csv`, so only the hybrid configuration changes here.

## Candidate scorecard on failing scenarios

| Setting | ATM direct rel. error | OTM direct rel. error | Max focus direct rel. error | Average focus direct rel. error |
| --- | --- | --- | --- | --- |
| `baseline_20k_181` | `1.103%` | `1.754%` | `1.754%` | `1.429%` |
| `paths40k_grid181` | `0.075%` | `0.318%` | `0.318%` | `0.196%` |
| `paths40k_grid241` | `0.058%` | `0.304%` | `0.304%` | `0.181%` |
| `paths60k_grid241` | `0.210%` | `0.274%` | `0.274%` | `0.242%` |
| `paths60k_grid301` | `0.211%` | `0.282%` | `0.282%` | `0.246%` |
| `paths60k_grid301_wide_q999` | `0.100%` | `0.153%` | `0.153%` | `0.127%` |

## Best common setting

- Label: `paths60k_grid301_wide_q999`
- Hybrid paths: `60000`
- Hybrid low paths: `60000`
- Asset points: `301`
- Asset range factors: `0.30` / `3.50`
- Vol truncation quantile: `0.999`

## Detailed scenario results

| Setting | Scenario | Paths | Asset points | Low factor | High factor | Vol q | Hybrid direct | Hybrid direct SE | Direct rel. error | Hybrid low | Hybrid low SE | Low rel. error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `baseline_20k_181` | `ATM` | `20,000` | `181` | `0.35` | `3.00` | `0.997` | `11.245782` | `0.035693` | `1.103%` | `11.311579` | `0.112662` | `0.326%` |
| `baseline_20k_181` | `OTM put` | `20,000` | `181` | `0.35` | `3.00` | `0.997` | `7.295876` | `0.026473` | `1.754%` | `7.376273` | `0.092352` | `0.411%` |
| `paths40k_grid181` | `ATM` | `40,000` | `181` | `0.35` | `3.00` | `0.997` | `11.362711` | `0.024720` | `0.075%` | `11.351279` | `0.083484` | `0.024%` |
| `paths40k_grid181` | `OTM put` | `40,000` | `181` | `0.35` | `3.00` | `0.997` | `7.402577` | `0.018317` | `0.318%` | `7.425260` | `0.067152` | `0.251%` |
| `paths40k_grid241` | `ATM` | `40,000` | `241` | `0.35` | `3.00` | `0.997` | `11.364577` | `0.024719` | `0.058%` | `11.353291` | `0.083476` | `0.041%` |
| `paths40k_grid241` | `OTM put` | `40,000` | `241` | `0.35` | `3.00` | `0.997` | `7.403555` | `0.018317` | `0.304%` | `7.426645` | `0.067147` | `0.269%` |
| `paths60k_grid241` | `ATM` | `60,000` | `241` | `0.35` | `3.00` | `0.997` | `11.347323` | `0.020574` | `0.210%` | `11.292775` | `0.066585` | `0.492%` |
| `paths60k_grid241` | `OTM put` | `60,000` | `241` | `0.35` | `3.00` | `0.997` | `7.405782` | `0.015303` | `0.274%` | `7.391481` | `0.054108` | `0.205%` |
| `paths60k_grid301` | `ATM` | `60,000` | `301` | `0.35` | `3.00` | `0.997` | `11.347210` | `0.020574` | `0.211%` | `11.293849` | `0.066591` | `0.482%` |
| `paths60k_grid301` | `OTM put` | `60,000` | `301` | `0.35` | `3.00` | `0.997` | `7.405221` | `0.015303` | `0.282%` | `7.392519` | `0.054114` | `0.191%` |
| `paths60k_grid301_wide_q999` | `ATM` | `60,000` | `301` | `0.30` | `3.50` | `0.999` | `11.359836` | `0.020646` | `0.100%` | `11.320776` | `0.067608` | `0.245%` |
| `paths60k_grid301_wide_q999` | `OTM put` | `60,000` | `301` | `0.30` | `3.50` | `0.999` | `7.414778` | `0.015362` | `0.153%` | `7.402772` | `0.055072` | `0.053%` |

Saved CSV: `bgk_r00_t1_nex12_hybrid_tuning_table.csv`