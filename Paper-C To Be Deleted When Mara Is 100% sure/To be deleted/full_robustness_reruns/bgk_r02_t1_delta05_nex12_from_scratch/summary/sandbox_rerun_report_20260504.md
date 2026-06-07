# Sandbox Rerun Report: BGK Robustness Case

This report summarizes the sandbox-only from-scratch rerun for the robustness case `bgk_r02_t1_delta05_nex12`. It is a verification artifact, not manuscript-ready prose.

## Run Metadata
| Item | Value |
| --- | --- |
| Run root | D:\Mara PhD\Paper-C\To be deleted\full_robustness_reruns\bgk_r02_t1_delta05_nex12_from_scratch |
| Created | 2026-05-04 14:05:32 |
| OS | Windows-11-10.0.26200-SP0 |
| Python | 3.12.8 |
| Git commit | a8b88f2 |
| Case | bgk_r02_t1_delta05_nex12 |
| Model | `r=0.02`, `delta1=delta2=0.5`, `T=1`, `N_ex=12` |
| Seeds | `2026 / 2103` |
| Validation | pass |

## Scope

- Benchmark: LSMC, five strikes, `M=1200`, `N=1,200,000`.
- Step sweep: paths `20,000` and `60,000`, steps `24,48,72,96`, LSMC and Hybrid.
- Path sweep: steps `48` and `60`, paths `250` through `60,000`, LSMC and Hybrid.
- Assets: Figure 5-style 48-step figure, 60-step companion figure, representative table, and appendix-style price tables.

## Benchmark Comparison
| K | Sandbox price | Sandbox SE | Prior manuscript price | Difference |
| --- | --- | --- | --- | --- |
| 70 | 3.363539 | 0.009321 | 3.363539 | 0.000000 |
| 80 | 4.961292 | 0.011652 | 4.961218 | 0.000074 |
| 90 | 7.081850 | 0.014051 | 7.082115 | -0.000265 |
| 100 | 9.921166 | 0.016333 | 9.921221 | -0.000055 |
| 110 | 13.857557 | 0.017760 | 13.857272 | 0.000285 |

## Representative Step Sweep
| Paths | Method | M | Price | SE | Rel. error |
| --- | --- | --- | --- | --- | --- |
| 20000 | benchmark | 48 | 11.642443 | 0.137850 | 17.350% |
| 20000 | hybrid | 48 | 11.226218 | 0.042370 | 13.154% |
| 20000 | benchmark | 96 | 11.113477 | 0.136031 | 12.018% |
| 20000 | hybrid | 96 | 10.886517 | 0.042421 | 9.730% |
| 60000 | benchmark | 48 | 11.508319 | 0.080013 | 15.998% |
| 60000 | hybrid | 48 | 11.371116 | 0.024125 | 14.615% |
| 60000 | benchmark | 96 | 10.956686 | 0.076214 | 10.437% |
| 60000 | hybrid | 96 | 10.861039 | 0.024230 | 9.473% |

## Representative Path Sweep
| M | Method | Paths | Price | SE | Rel. error |
| --- | --- | --- | --- | --- | --- |
| 48 | benchmark | 20000 | 11.642443 | 0.137850 | 17.350% |
| 48 | hybrid | 20000 | 11.226218 | 0.042370 | 13.154% |
| 48 | benchmark | 60000 | 11.508319 | 0.080013 | 15.998% |
| 48 | hybrid | 60000 | 11.371116 | 0.024125 | 14.615% |
| 60 | benchmark | 20000 | 11.462118 | 0.137987 | 15.532% |
| 60 | hybrid | 20000 | 11.052725 | 0.043130 | 11.406% |
| 60 | benchmark | 60000 | 11.373201 | 0.078967 | 14.636% |
| 60 | hybrid | 60000 | 11.211493 | 0.024143 | 13.006% |

## Validation Summary
Validation passed with `1245` checks.

## Generated Assets

- `figures/bgk_r02_t1_delta05_nex12_path_sweep_steps48_direct_relative_error.pdf`
- `figures/bgk_r02_t1_delta05_nex12_path_sweep_steps60_direct_relative_error.pdf`
- `tables/bgk_r02_t1_delta05_nex12_path_sweep_steps48_path20k_table.tex`
- `tables/bgk_r02_t1_delta05_nex12_appendix_price_tables.tex`

## Notes

- All generated files are intended to stay under the sandbox root.
- The new pricing engines are separate from the old `run_bgk_*` scripts; manuscript-source CSVs are read only for comparison.
- Hybrid low-estimator values are retained only as diagnostic, legacy-compatible provenance; direct prices are the quantities used in tables, figures, and conclusions.
- Engine hashes are recorded in `D:\Mara PhD\Paper-C\To be deleted\full_robustness_reruns\bgk_r02_t1_delta05_nex12_from_scratch\results\metadata\bgk_r02_t1_delta05_nex12_metadata.json`.
