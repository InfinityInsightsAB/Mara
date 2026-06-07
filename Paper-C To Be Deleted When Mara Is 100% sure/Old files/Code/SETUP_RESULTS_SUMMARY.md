# Bermudan pricing results summary

This note records the current paper benchmark run and the final tuned standalone gDMR run.

## Heston paper benchmark

The `heston_paper_benchmark` folder is kept fixed as the paper-faithful benchmark.

Finite-difference reference: `1.4507`

| Estimator | Published value | Run value | \|Run - FD\| | Run - published |
| --- | ---: | ---: | ---: | ---: |
| LSMC direct | `1.4494` | `1.458896` | `0.008196` | `+0.009496` |
| LSMC low | `1.4487` | `1.452544` | `0.001844` | `+0.003844` |
| Hybrid direct | `1.4530` | `1.452988` | `0.002288` | `-0.000012` |
| Hybrid low | `1.4529` | `1.445493` | `0.005207` | `-0.007407` |

## gDMR standalone

The `gdmr_standalone` Monte Carlo reference is kept fixed, and only the hybrid resolution is tuned.

Final hybrid settings: `N = 30000`, `N_low = 30000`, `N_S = 181`, `N_hermite = 64`

| Estimator | Price | Standard error | Relative error |
| --- | ---: | ---: | ---: |
| LSMC direct | `6.384535` | `0.007943` | reference |
| LSMC low | `6.387249` | `0.007939` | `0.04%` vs LSMC direct |
| Hybrid direct | `6.421758` | `0.000652` | `0.58%` vs LSMC direct |
| Hybrid low | `6.265070` | `0.045711` | `1.87%` vs LSMC direct |

Additional comparison: `Hybrid low` relative error vs `LSMC low` = `1.91%`

## Observations

- `heston_paper_benchmark` remains a fixed benchmark and should be read against the paper's published values, not as a tuning target.
- `gdmr_standalone` uses `LSMC direct` as the practical reference because there is no published finite-difference benchmark for this gDMR case in the project.
- The main levers that improved `Hybrid direct` were higher hybrid path counts, a denser asset grid, and more Hermite nodes.
- The first accuracy tier already brought `Hybrid direct` below the `< 1%` target, so higher tiers were not needed.
