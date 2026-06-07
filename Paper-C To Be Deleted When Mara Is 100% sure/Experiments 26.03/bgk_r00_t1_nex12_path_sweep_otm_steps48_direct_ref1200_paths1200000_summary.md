# BGK 12-date OTM put Direct Path Sweep Rebased to the 1200-step Benchmark

This note reuses the saved OTM put path sweep with Euler steps fixed at `48` and recomputes only the direct relative error.
The updated reference is the benchmark-only run with `GDMR_EULER_STEPS=1200`, `GDMR_LSMC_PATHS=1200000`, and `GDMR_LSMC_LOW_PATHS=1200000`.

- Scenario: `OTM put`
- Fixed benchmark direct reference: `7.402999`
- Fixed benchmark direct reference SE: `0.012459`
- Euler steps in the path sweep: `48`
- Path counts tested: `250, 500, 1000, 2000, 5000, 10000, 20000, 40000, 60000`

| Paths | Method | Direct price | Direct SE | Direct rel. error | Runtime |
| --- | --- | --- | --- | --- | --- |
| `250` | `benchmark` | `9.218305` | `0.949228` | `24.521%` | `0.25 s` |
| `250` | `hybrid` | `8.425518` | `0.245621` | `13.812%` | `1.19 s` |
| `500` | `benchmark` | `8.199723` | `0.611181` | `10.762%` | `0.21 s` |
| `500` | `hybrid` | `8.060138` | `0.163373` | `8.877%` | `2.18 s` |
| `1,000` | `benchmark` | `7.983426` | `0.481296` | `7.840%` | `0.20 s` |
| `1,000` | `hybrid` | `7.618089` | `0.125093` | `2.905%` | `4.26 s` |
| `2,000` | `benchmark` | `8.062020` | `0.336072` | `8.902%` | `0.21 s` |
| `2,000` | `hybrid` | `7.157395` | `0.078782` | `3.318%` | `7.95 s` |
| `5,000` | `benchmark` | `7.761964` | `0.206435` | `4.849%` | `0.24 s` |
| `5,000` | `hybrid` | `7.563095` | `0.054566` | `2.163%` | `19.46 s` |
| `10,000` | `benchmark` | `7.615982` | `0.139783` | `2.877%` | `0.27 s` |
| `10,000` | `hybrid` | `7.338671` | `0.037448` | `0.869%` | `38.47 s` |
| `20,000` | `benchmark` | `7.563898` | `0.098998` | `2.173%` | `0.35 s` |
| `20,000` | `hybrid` | `7.421371` | `0.026580` | `0.248%` | `77.48 s` |
| `40,000` | `benchmark` | `7.537930` | `0.069539` | `1.823%` | `0.68 s` |
| `40,000` | `hybrid` | `7.454272` | `0.018404` | `0.693%` | `154.11 s` |
| `60,000` | `benchmark` | `7.533980` | `0.057264` | `1.769%` | `0.84 s` |
| `60,000` | `hybrid` | `7.441944` | `0.015182` | `0.526%` | `228.79 s` |

![OTM put direct relative error rebased to 1200-step benchmark](C:\MDU PhD\Paper C\Experiments 26.03\bgk_r00_t1_nex12_path_sweep_otm_steps48_direct_ref1200_paths1200000_relative_error_with_ci.svg)

Saved CSV: `bgk_r00_t1_nex12_path_sweep_otm_steps48_direct_ref1200_paths1200000_table.csv`