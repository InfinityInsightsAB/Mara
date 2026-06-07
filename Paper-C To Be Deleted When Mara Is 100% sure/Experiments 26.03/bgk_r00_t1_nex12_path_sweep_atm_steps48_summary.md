# BGK 12-date Path Sweep (ATM)

This note compares the LSMC benchmark and the tuned Hybrid LSMC-PDE as path count varies with Euler steps fixed at `48`.
The reference for relative errors is the fixed benchmark from `bgk_r00_t1_nex12_comparison_table.csv` with `GDMR_EULER_STEPS=600`.

- Scenario: `ATM`
- Fixed benchmark direct reference: `11.371204`
- Fixed benchmark low reference: `11.348587`
- Euler steps: `48`
- Path counts tested: `250, 500, 1000, 2000, 5000, 10000, 20000, 40000, 60000`
- Hybrid asset points: `301`
- Hybrid asset range factors: `0.30` / `3.50`
- Hybrid vol quantile: `0.999`

| Paths | Method | Direct price | Direct SE | Direct rel. error | Low price | Low SE | Low rel. error | Runtime |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `250` | `benchmark` | `14.103409` | `1.146073` | `24.027%` | `11.300593` | `1.024923` | `0.423%` | `0.57 s` |
| `250` | `hybrid` | `12.577161` | `0.323112` | `10.605%` | `10.356283` | `0.986215` | `8.744%` | `1.27 s` |
| `500` | `benchmark` | `12.600830` | `0.747838` | `10.814%` | `11.073453` | `0.688727` | `2.424%` | `0.20 s` |
| `500` | `hybrid` | `12.155396` | `0.222722` | `6.896%` | `10.333924` | `0.675884` | `8.941%` | `2.29 s` |
| `1,000` | `benchmark` | `12.044279` | `0.556184` | `5.919%` | `11.215452` | `0.510605` | `1.173%` | `0.21 s` |
| `1,000` | `hybrid` | `11.540800` | `0.168410` | `1.491%` | `11.030211` | `0.495385` | `2.805%` | `4.57 s` |
| `2,000` | `benchmark` | `12.183347` | `0.408285` | `7.142%` | `11.069514` | `0.377007` | `2.459%` | `0.22 s` |
| `2,000` | `hybrid` | `11.096172` | `0.107848` | `2.419%` | `10.960155` | `0.350660` | `3.423%` | `9.38 s` |
| `5,000` | `benchmark` | `11.832667` | `0.253256` | `4.058%` | `11.432290` | `0.245222` | `0.738%` | `0.25 s` |
| `5,000` | `hybrid` | `11.540630` | `0.073624` | `1.490%` | `11.192507` | `0.236721` | `1.375%` | `22.99 s` |
| `10,000` | `benchmark` | `11.561979` | `0.167854` | `1.678%` | `11.252725` | `0.163006` | `0.845%` | `0.28 s` |
| `10,000` | `hybrid` | `11.247761` | `0.050832` | `1.086%` | `11.410692` | `0.159611` | `0.547%` | `41.36 s` |
| `20,000` | `benchmark` | `11.508503` | `0.119290` | `1.207%` | `11.444655` | `0.118795` | `0.847%` | `0.40 s` |
| `20,000` | `hybrid` | `11.362764` | `0.035911` | `0.074%` | `11.562451` | `0.118093` | `1.885%` | `78.62 s` |
| `40,000` | `benchmark` | `11.565093` | `0.084977` | `1.705%` | `11.507013` | `0.084830` | `1.396%` | `0.61 s` |
| `40,000` | `hybrid` | `11.416874` | `0.024962` | `0.402%` | `11.543837` | `0.083914` | `1.720%` | `154.89 s` |
| `60,000` | `benchmark` | `11.496757` | `0.069573` | `1.104%` | `11.463595` | `0.069227` | `1.013%` | `0.91 s` |
| `60,000` | `hybrid` | `11.391168` | `0.020573` | `0.176%` | `11.499922` | `0.067162` | `1.334%` | `233.86 s` |

![ATM direct relative error](C:\MDU PhD\Paper C\Experiments 26.03\bgk_r00_t1_nex12_path_sweep_atm_steps48_direct_relative_error_with_ci.svg)

![ATM low relative error](C:\MDU PhD\Paper C\Experiments 26.03\bgk_r00_t1_nex12_path_sweep_atm_steps48_low_relative_error_with_ci.svg)

Saved CSV: `bgk_r00_t1_nex12_path_sweep_atm_steps48_table.csv`