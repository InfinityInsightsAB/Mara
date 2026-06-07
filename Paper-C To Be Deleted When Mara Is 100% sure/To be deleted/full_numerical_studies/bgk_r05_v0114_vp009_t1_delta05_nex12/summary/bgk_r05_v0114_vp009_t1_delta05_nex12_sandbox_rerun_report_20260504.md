# Sandbox Rerun Report: BGK Positive-Rate Square-Root Numerical Study

This report summarizes the sandbox-only from-scratch rerun for the numerical-study case `bgk_r05_v0114_vp009_t1_delta05_nex12`. It is a verification artifact for the standalone numerical-study PDF.

## Run Metadata
| Item | Value |
| --- | --- |
| Run root | D:\Mara PhD\Paper-C\To be deleted\full_numerical_studies\bgk_r05_v0114_vp009_t1_delta05_nex12 |
| Created | 2026-05-05 03:31:18 |
| OS | Windows-11-10.0.26200-SP0 |
| Python | 3.12.8 |
| Git commit | a8b88f2 |
| Case | bgk_r05_v0114_vp009_t1_delta05_nex12 |
| Model | `r=0.05`, `v0=0.114`, `vp0=0.09`, `delta1=delta2=0.5`, `T=1`, `N_ex=12` |
| Seeds | `2026 / 2103` |
| Validation | pass |

## Scope

- Benchmark: LSMC, five strikes, `M=1200`, `N=1,200,000`.
- Step sweep: paths `20,000` and `60,000`, steps `24,48,72,96`, LSMC and Hybrid.
- Path sweep: steps `48` and `60`, paths `250` through `60,000`, LSMC and Hybrid.
- Assets: step-sweep and path-sweep figures, representative tables, benchmark/setup tables, and appendix-style price tables.

## Benchmark Prices
| K | Sandbox price | Sandbox SE |
| --- | --- | --- |
| 70 | 3.734195 | 0.010500 |
| 80 | 5.384271 | 0.012928 |
| 90 | 7.683607 | 0.015509 |
| 100 | 10.959943 | 0.018058 |
| 110 | 15.732048 | 0.019990 |

## Representative Step Sweep
| Paths | Method | M | Price | SE | Rel. error |
| --- | --- | --- | --- | --- | --- |
| 20000 | benchmark | 48 | 13.290796 | 0.153720 | 21.267% |
| 20000 | hybrid | 48 | 12.825020 | 0.043987 | 17.017% |
| 20000 | benchmark | 96 | 12.512404 | 0.148981 | 14.165% |
| 20000 | hybrid | 96 | 12.291007 | 0.042447 | 12.145% |
| 60000 | benchmark | 48 | 13.111671 | 0.088533 | 19.633% |
| 60000 | hybrid | 48 | 12.956535 | 0.025244 | 18.217% |
| 60000 | benchmark | 96 | 12.507570 | 0.085873 | 14.121% |
| 60000 | hybrid | 96 | 12.295240 | 0.024597 | 12.183% |

## Representative Path Sweep
| M | Method | Paths | Price | SE | Rel. error |
| --- | --- | --- | --- | --- | --- |
| 48 | benchmark | 20000 | 13.290796 | 0.153720 | 21.267% |
| 48 | hybrid | 20000 | 12.825020 | 0.043987 | 17.017% |
| 48 | benchmark | 60000 | 13.111671 | 0.088533 | 19.633% |
| 48 | hybrid | 60000 | 12.956535 | 0.025244 | 18.217% |
| 60 | benchmark | 20000 | 13.075526 | 0.152583 | 19.303% |
| 60 | hybrid | 20000 | 12.606509 | 0.044328 | 15.023% |
| 60 | benchmark | 60000 | 12.973010 | 0.087903 | 18.367% |
| 60 | hybrid | 60000 | 12.735603 | 0.025040 | 16.201% |

## Validation Summary
Validation passed with `1462` checks.

## Generated Assets

- `figures/bgk_r05_v0114_vp009_t1_delta05_nex12_step_sweep_20k_direct_relative_error.pdf`
- `figures/bgk_r05_v0114_vp009_t1_delta05_nex12_step_sweep_60k_direct_relative_error.pdf`
- `figures/bgk_r05_v0114_vp009_t1_delta05_nex12_path_sweep_steps48_direct_relative_error.pdf`
- `figures/bgk_r05_v0114_vp009_t1_delta05_nex12_path_sweep_steps60_direct_relative_error.pdf`
- `tables/bgk_r05_v0114_vp009_t1_delta05_nex12_experimental_setting_table.tex`
- `tables/bgk_r05_v0114_vp009_t1_delta05_nex12_benchmark_reference_table.tex`
- `tables/bgk_r05_v0114_vp009_t1_delta05_nex12_step_sweep_20k_step72_table.tex`
- `tables/bgk_r05_v0114_vp009_t1_delta05_nex12_step_sweep_60k_step72_table.tex`
- `tables/bgk_r05_v0114_vp009_t1_delta05_nex12_path_sweep_steps48_path20k_table.tex`
- `tables/bgk_r05_v0114_vp009_t1_delta05_nex12_path_sweep_steps60_path20k_table.tex`
- `tables/bgk_r05_v0114_vp009_t1_delta05_nex12_appendix_price_tables.tex`

## Notes

- All generated files are intended to stay under the sandbox root.
- The new pricing engines are separate from the old `run_bgk_*` scripts; all reported values in this study come from the sandbox rerun.
- Hybrid low-estimator values are retained only as diagnostic, legacy-compatible provenance; direct prices are the quantities used in tables, figures, and conclusions.
- Engine hashes are recorded in `D:\Mara PhD\Paper-C\To be deleted\full_numerical_studies\bgk_r05_v0114_vp009_t1_delta05_nex12\results\metadata\bgk_r05_v0114_vp009_t1_delta05_nex12_metadata.json`.
