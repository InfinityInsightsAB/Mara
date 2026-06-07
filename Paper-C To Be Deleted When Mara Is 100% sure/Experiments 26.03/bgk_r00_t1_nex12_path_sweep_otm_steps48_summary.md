# BGK 12-date Path Sweep (OTM put)

This note compares the LSMC benchmark and the tuned Hybrid LSMC-PDE as path count varies with Euler steps fixed at `48`.
The reference for relative errors is the fixed benchmark from `bgk_r00_t1_nex12_comparison_table.csv` with `GDMR_EULER_STEPS=600`.

- Scenario: `OTM put`
- Fixed benchmark direct reference: `7.426156`
- Fixed benchmark low reference: `7.406685`
- Euler steps: `48`
- Path counts tested: `250, 500, 1000, 2000, 5000, 10000, 20000, 40000, 60000`
- Hybrid asset points: `301`
- Hybrid asset range factors: `0.30` / `3.50`
- Hybrid vol quantile: `0.999`

| Paths | Method | Direct price | Direct SE | Direct rel. error | Low price | Low SE | Low rel. error | Runtime |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `250` | `benchmark` | `9.218305` | `0.949228` | `24.133%` | `6.391398` | `0.774347` | `13.708%` | `0.25 s` |
| `250` | `hybrid` | `8.425518` | `0.245621` | `13.457%` | `6.583299` | `0.775684` | `11.117%` | `1.19 s` |
| `500` | `benchmark` | `8.199723` | `0.611181` | `10.417%` | `7.615355` | `0.624656` | `2.817%` | `0.21 s` |
| `500` | `hybrid` | `8.060138` | `0.163373` | `8.537%` | `6.492280` | `0.533105` | `12.346%` | `2.18 s` |
| `1,000` | `benchmark` | `7.983426` | `0.481296` | `7.504%` | `7.172338` | `0.427047` | `3.164%` | `0.20 s` |
| `1,000` | `hybrid` | `7.618089` | `0.125093` | `2.585%` | `6.884014` | `0.398167` | `7.057%` | `4.26 s` |
| `2,000` | `benchmark` | `8.062020` | `0.336072` | `8.562%` | `7.249362` | `0.309465` | `2.124%` | `0.21 s` |
| `2,000` | `hybrid` | `7.157395` | `0.078782` | `3.619%` | `7.035459` | `0.284823` | `5.012%` | `7.95 s` |
| `5,000` | `benchmark` | `7.761964` | `0.206435` | `4.522%` | `7.505349` | `0.201077` | `1.332%` | `0.24 s` |
| `5,000` | `hybrid` | `7.563095` | `0.054566` | `1.844%` | `7.313557` | `0.190601` | `1.257%` | `19.46 s` |
| `10,000` | `benchmark` | `7.615982` | `0.139783` | `2.556%` | `7.348599` | `0.135946` | `0.784%` | `0.27 s` |
| `10,000` | `hybrid` | `7.338671` | `0.037448` | `1.178%` | `7.528029` | `0.132650` | `1.638%` | `38.47 s` |
| `20,000` | `benchmark` | `7.563898` | `0.098998` | `1.855%` | `7.507729` | `0.098144` | `1.364%` | `0.35 s` |
| `20,000` | `hybrid` | `7.421371` | `0.026580` | `0.064%` | `7.559585` | `0.096290` | `2.064%` | `77.48 s` |
| `40,000` | `benchmark` | `7.537930` | `0.069539` | `1.505%` | `7.537382` | `0.069474` | `1.765%` | `0.68 s` |
| `40,000` | `hybrid` | `7.454272` | `0.018404` | `0.379%` | `7.577899` | `0.068113` | `2.312%` | `154.11 s` |
| `60,000` | `benchmark` | `7.533980` | `0.057264` | `1.452%` | `7.487236` | `0.056980` | `1.088%` | `0.84 s` |
| `60,000` | `hybrid` | `7.441944` | `0.015182` | `0.213%` | `7.524645` | `0.054907` | `1.593%` | `228.79 s` |

![OTM put direct relative error](C:\MDU PhD\Paper C\Experiments 26.03\bgk_r00_t1_nex12_path_sweep_otm_steps48_direct_relative_error_with_ci.svg)

![OTM put low relative error](C:\MDU PhD\Paper C\Experiments 26.03\bgk_r00_t1_nex12_path_sweep_otm_steps48_low_relative_error_with_ci.svg)

Saved CSV: `bgk_r00_t1_nex12_path_sweep_otm_steps48_table.csv`