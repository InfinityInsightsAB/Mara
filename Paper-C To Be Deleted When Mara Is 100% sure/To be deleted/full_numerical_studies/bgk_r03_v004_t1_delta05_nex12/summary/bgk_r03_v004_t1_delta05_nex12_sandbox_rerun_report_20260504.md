# Sandbox Rerun Report: BGK Positive-Rate Numerical Study

This report summarizes the sandbox-only from-scratch rerun for the numerical-study case `bgk_r03_v004_t1_delta05_nex12`. It is a verification artifact for the standalone numerical-study PDF.

## Run Metadata
| Item | Value |
| --- | --- |
| Run root | D:\Mara PhD\Paper-C\To be deleted\full_numerical_studies\bgk_r03_v004_t1_delta05_nex12 |
| Created | 2026-05-04 22:35:44 |
| OS | Windows-11-10.0.26200-SP0 |
| Python | 3.12.8 |
| Git commit | a8b88f2 |
| Case | bgk_r03_v004_t1_delta05_nex12 |
| Model | `r=0.03`, `v0=vp0=0.04`, `delta1=delta2=0.5`, `T=1`, `N_ex=12` |
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
| 70 | 0.157901 | 0.001152 |
| 80 | 0.741358 | 0.002648 |
| 90 | 2.503886 | 0.004943 |
| 100 | 6.343052 | 0.007586 |
| 110 | 12.571373 | 0.009593 |

## Representative Step Sweep
| Paths | Method | M | Price | SE | Rel. error |
| --- | --- | --- | --- | --- | --- |
| 20000 | benchmark | 48 | 6.370571 | 0.058941 | 0.434% |
| 20000 | hybrid | 48 | 6.390036 | 0.003089 | 0.741% |
| 20000 | benchmark | 96 | 6.384442 | 0.059824 | 0.653% |
| 20000 | hybrid | 96 | 6.375041 | 0.003121 | 0.504% |
| 60000 | benchmark | 48 | 6.370406 | 0.034274 | 0.431% |
| 60000 | hybrid | 48 | 6.395839 | 0.001798 | 0.832% |
| 60000 | benchmark | 96 | 6.380703 | 0.033985 | 0.594% |
| 60000 | hybrid | 96 | 6.384128 | 0.001820 | 0.648% |

## Representative Path Sweep
| M | Method | Paths | Price | SE | Rel. error |
| --- | --- | --- | --- | --- | --- |
| 48 | benchmark | 20000 | 6.370571 | 0.058941 | 0.434% |
| 48 | hybrid | 20000 | 6.390036 | 0.003089 | 0.741% |
| 48 | benchmark | 60000 | 6.370406 | 0.034274 | 0.431% |
| 48 | hybrid | 60000 | 6.395839 | 0.001798 | 0.832% |
| 60 | benchmark | 20000 | 6.389520 | 0.059312 | 0.733% |
| 60 | hybrid | 20000 | 6.381559 | 0.003110 | 0.607% |
| 60 | benchmark | 60000 | 6.382005 | 0.034221 | 0.614% |
| 60 | hybrid | 60000 | 6.391698 | 0.001802 | 0.767% |

## Validation Summary
Validation passed with `1460` checks.

## Generated Assets

- `figures/bgk_r03_v004_t1_delta05_nex12_step_sweep_20k_direct_relative_error.pdf`
- `figures/bgk_r03_v004_t1_delta05_nex12_step_sweep_60k_direct_relative_error.pdf`
- `figures/bgk_r03_v004_t1_delta05_nex12_path_sweep_steps48_direct_relative_error.pdf`
- `figures/bgk_r03_v004_t1_delta05_nex12_path_sweep_steps60_direct_relative_error.pdf`
- `tables/bgk_r03_v004_t1_delta05_nex12_experimental_setting_table.tex`
- `tables/bgk_r03_v004_t1_delta05_nex12_benchmark_reference_table.tex`
- `tables/bgk_r03_v004_t1_delta05_nex12_step_sweep_20k_step72_table.tex`
- `tables/bgk_r03_v004_t1_delta05_nex12_step_sweep_60k_step72_table.tex`
- `tables/bgk_r03_v004_t1_delta05_nex12_path_sweep_steps48_path20k_table.tex`
- `tables/bgk_r03_v004_t1_delta05_nex12_path_sweep_steps60_path20k_table.tex`
- `tables/bgk_r03_v004_t1_delta05_nex12_appendix_price_tables.tex`

## Notes

- All generated files are intended to stay under the sandbox root.
- The new pricing engines are separate from the old `run_bgk_*` scripts; manuscript-source CSVs are read only for comparison.
- Hybrid low-estimator values are retained only as diagnostic, legacy-compatible provenance; direct prices are the quantities used in tables, figures, and conclusions.
- Engine hashes are recorded in `D:\Mara PhD\Paper-C\To be deleted\full_numerical_studies\bgk_r03_v004_t1_delta05_nex12\results\metadata\bgk_r03_v004_t1_delta05_nex12_metadata.json`.
