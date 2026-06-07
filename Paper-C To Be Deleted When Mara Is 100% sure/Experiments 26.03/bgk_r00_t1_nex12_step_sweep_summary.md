# BGK 12-date Euler Step Sweep

This note compares the LSMC benchmark and the tuned Hybrid LSMC-PDE as Euler steps decrease while the Bermudan exercise dates stay fixed at 12.
The reference for relative errors is the fixed benchmark from `bgk_r00_t1_nex12_comparison_table.csv` with `GDMR_EULER_STEPS=600`.

## Fixed model block

```text
GDMR_S0=100.0
GDMR_V0=0.114
GDMR_VP0=0.110
GDMR_R=0.0
GDMR_KAPPA1=5.5
GDMR_KAPPA2=0.1
GDMR_THETA=0.078
GDMR_XI1=2.689
GDMR_XI2=0.502
GDMR_DELTA1=0.94
GDMR_DELTA2=0.94
GDMR_RHO12=-0.982
GDMR_RHO13=-0.727
GDMR_RHO23=0.59
GDMR_EXERCISE_DATES=12
```

## Sweep settings

- Scenarios swept: `ATM, OTM put`
- Euler steps tested: `60`
- Benchmark paths: `1000000`
- Benchmark low paths: `1000000`
- Hybrid paths: `60000`
- Hybrid low paths: `60000`
- Hybrid asset points: `301`
- Hybrid asset range factors: `0.30` / `3.50`
- Hybrid vol quantile: `0.999`

## ATM

- Fixed benchmark direct reference: `11.371204`
- Fixed benchmark low reference: `11.348587`

| Euler steps | Method | Direct price | Direct SE | Direct rel. error | Low price | Low SE | Low rel. error | Runtime |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `60` | `benchmark` | `11.381616` | `0.016633` | `0.092%` | `11.357803` | `0.016600` | `0.081%` | `0.00 s` |
| `60` | `hybrid` | `11.350391` | `0.020589` | `0.183%` | `11.392522` | `0.066910` | `0.387%` | `0.00 s` |

![ATM direct relative error](C:\MDU PhD\Paper C\Experiments 26.03\bgk_r00_t1_nex12_step_sweep_atm_direct_relative_error_with_ci.svg)

![ATM low relative error](C:\MDU PhD\Paper C\Experiments 26.03\bgk_r00_t1_nex12_step_sweep_atm_low_relative_error_with_ci.svg)

## OTM put

- Fixed benchmark direct reference: `7.426156`
- Fixed benchmark low reference: `7.406685`

| Euler steps | Method | Direct price | Direct SE | Direct rel. error | Low price | Low SE | Low rel. error | Runtime |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `60` | `benchmark` | `7.435732` | `0.013785` | `0.129%` | `7.415447` | `0.013747` | `0.118%` | `0.00 s` |
| `60` | `hybrid` | `7.410080` | `0.015228` | `0.216%` | `7.452584` | `0.054621` | `0.620%` | `0.00 s` |

![OTM put direct relative error](C:\MDU PhD\Paper C\Experiments 26.03\bgk_r00_t1_nex12_step_sweep_otm_direct_relative_error_with_ci.svg)

![OTM put low relative error](C:\MDU PhD\Paper C\Experiments 26.03\bgk_r00_t1_nex12_step_sweep_otm_low_relative_error_with_ci.svg)

Saved CSV: `bgk_r00_t1_nex12_step_sweep_table.csv`