# BGK 12-date ATM Direct Path Sweep Rebased to the 1200-step Benchmark

This note reuses the saved ATM path sweep with Euler steps fixed at `48` and recomputes only the direct relative error.
The updated reference is the ATM benchmark-only run with `GDMR_EULER_STEPS=1200`, `GDMR_LSMC_PATHS=1200000`, and `GDMR_LSMC_LOW_PATHS=1200000`.

- Scenario: `ATM`
- Fixed benchmark direct reference: `11.356823`
- Fixed benchmark direct reference SE: `0.015058`
- Euler steps in the path sweep: `48`
- Path counts tested: `250, 500, 1000, 2000, 5000, 10000, 20000, 40000, 60000`

| Paths | Method | Direct price | Direct SE | Direct rel. error | Runtime |
| --- | --- | --- | --- | --- | --- |
| `250` | `benchmark` | `14.103409` | `1.146073` | `24.184%` | `0.57 s` |
| `250` | `hybrid` | `12.577161` | `0.323112` | `10.745%` | `1.27 s` |
| `500` | `benchmark` | `12.600830` | `0.747838` | `10.954%` | `0.20 s` |
| `500` | `hybrid` | `12.155396` | `0.222722` | `7.032%` | `2.29 s` |
| `1,000` | `benchmark` | `12.044279` | `0.556184` | `6.053%` | `0.21 s` |
| `1,000` | `hybrid` | `11.540800` | `0.168410` | `1.620%` | `4.57 s` |
| `2,000` | `benchmark` | `12.183347` | `0.408285` | `7.278%` | `0.22 s` |
| `2,000` | `hybrid` | `11.096172` | `0.107848` | `2.295%` | `9.38 s` |
| `5,000` | `benchmark` | `11.832667` | `0.253256` | `4.190%` | `0.25 s` |
| `5,000` | `hybrid` | `11.540630` | `0.073624` | `1.618%` | `22.99 s` |
| `10,000` | `benchmark` | `11.561979` | `0.167854` | `1.806%` | `0.28 s` |
| `10,000` | `hybrid` | `11.247761` | `0.050832` | `0.960%` | `41.36 s` |
| `20,000` | `benchmark` | `11.508503` | `0.119290` | `1.336%` | `0.40 s` |
| `20,000` | `hybrid` | `11.362764` | `0.035911` | `0.052%` | `78.62 s` |
| `40,000` | `benchmark` | `11.565093` | `0.084977` | `1.834%` | `0.61 s` |
| `40,000` | `hybrid` | `11.416874` | `0.024962` | `0.529%` | `154.89 s` |
| `60,000` | `benchmark` | `11.496757` | `0.069573` | `1.232%` | `0.91 s` |
| `60,000` | `hybrid` | `11.391168` | `0.020573` | `0.302%` | `233.86 s` |

![ATM direct relative error rebased to 1200-step benchmark](C:\MDU PhD\Paper C\Experiments 26.03\bgk_r00_t1_nex12_path_sweep_atm_steps48_direct_ref1200_paths1200000_relative_error_with_ci.svg)

Saved CSV: `bgk_r00_t1_nex12_path_sweep_atm_steps48_direct_ref1200_paths1200000_table.csv`