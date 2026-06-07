# Sandbox Rerun Report: BGK Positive-Rate Numerical Study

This report summarizes the sandbox-only from-scratch rerun for the numerical-study case `bgk_r02_calibrated_t1_nex12`. It is a verification artifact for the standalone numerical-study PDF.

## Run Metadata
| Item | Value |
| --- | --- |
| Run root | D:\Mara PhD\Paper-C\To be deleted\full_numerical_studies\bgk_r02_calibrated_t1_nex12 |
| Created | 2026-05-05 01:17:31 |
| OS | Windows-11-10.0.26200-SP0 |
| Python | 3.12.8 |
| Git commit | a8b88f2 |
| Case | bgk_r02_calibrated_t1_nex12 |
| Model | `r=0.02`, calibrated parameters, `delta1=delta2=0.94`, `T=1`, `N_ex=12` |
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
| 70 | 2.522851 | 0.007103 |
| 80 | 4.298933 | 0.009345 |
| 90 | 6.942119 | 0.011774 |
| 100 | 10.682037 | 0.014105 |
| 110 | 15.743520 | 0.015757 |

## Representative Step Sweep
| Paths | Method | M | Price | SE | Rel. error |
| --- | --- | --- | --- | --- | --- |
| 20000 | benchmark | 48 | 10.806834 | 0.110628 | 1.168% |
| 20000 | hybrid | 48 | 10.672650 | 0.035082 | 0.088% |
| 20000 | benchmark | 96 | 10.836790 | 0.113075 | 1.449% |
| 20000 | hybrid | 96 | 10.679411 | 0.035151 | 0.025% |
| 60000 | benchmark | 48 | 10.800117 | 0.064903 | 1.105% |
| 60000 | hybrid | 48 | 10.715101 | 0.020089 | 0.310% |
| 60000 | benchmark | 96 | 10.711736 | 0.063147 | 0.278% |
| 60000 | hybrid | 96 | 10.638747 | 0.020195 | 0.405% |

## Representative Path Sweep
| M | Method | Paths | Price | SE | Rel. error |
| --- | --- | --- | --- | --- | --- |
| 48 | benchmark | 20000 | 10.806834 | 0.110628 | 1.168% |
| 48 | hybrid | 20000 | 10.672650 | 0.035082 | 0.088% |
| 48 | benchmark | 60000 | 10.800117 | 0.064903 | 1.105% |
| 48 | hybrid | 60000 | 10.715101 | 0.020089 | 0.310% |
| 60 | benchmark | 20000 | 10.909701 | 0.114168 | 2.131% |
| 60 | hybrid | 20000 | 10.609574 | 0.035827 | 0.678% |
| 60 | benchmark | 60000 | 10.823474 | 0.065297 | 1.324% |
| 60 | hybrid | 60000 | 10.676809 | 0.020105 | 0.049% |

## Validation Summary
Validation passed with `1460` checks.

## Generated Assets

- `figures/bgk_r02_calibrated_t1_nex12_step_sweep_20k_direct_relative_error.pdf`
- `figures/bgk_r02_calibrated_t1_nex12_step_sweep_60k_direct_relative_error.pdf`
- `figures/bgk_r02_calibrated_t1_nex12_path_sweep_steps48_direct_relative_error.pdf`
- `figures/bgk_r02_calibrated_t1_nex12_path_sweep_steps60_direct_relative_error.pdf`
- `tables/bgk_r02_calibrated_t1_nex12_experimental_setting_table.tex`
- `tables/bgk_r02_calibrated_t1_nex12_benchmark_reference_table.tex`
- `tables/bgk_r02_calibrated_t1_nex12_step_sweep_20k_step72_table.tex`
- `tables/bgk_r02_calibrated_t1_nex12_step_sweep_60k_step72_table.tex`
- `tables/bgk_r02_calibrated_t1_nex12_path_sweep_steps48_path20k_table.tex`
- `tables/bgk_r02_calibrated_t1_nex12_path_sweep_steps60_path20k_table.tex`
- `tables/bgk_r02_calibrated_t1_nex12_appendix_price_tables.tex`

## Notes

- All generated files are intended to stay under the sandbox root.
- The new pricing engines are separate from the old `run_bgk_*` scripts; manuscript-source CSVs are read only for comparison.
- Hybrid low-estimator values are retained only as diagnostic, legacy-compatible provenance; direct prices are the quantities used in tables, figures, and conclusions.
- Engine hashes are recorded in `D:\Mara PhD\Paper-C\To be deleted\full_numerical_studies\bgk_r02_calibrated_t1_nex12\results\metadata\bgk_r02_calibrated_t1_nex12_metadata.json`.
