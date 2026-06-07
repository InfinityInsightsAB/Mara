# Final-Code Path Sweep Summary

This experiment reuses only the shipped `Final Code` benchmark and hybrid scripts.

## Common setup

- Spot `S0 = 100` and maturity `T = 1.0`.
- Bermudan exercise dates: `100`.
- Euler steps: `600`.
- LSMC benchmark seeds: `2026` and `2103`.
- Hybrid seeds: `2026` and `2103`.
- Path sweep: `250, 500`.
- Fixed reference for each scenario: unmodified LSMC benchmark with `2,000` paths.
- Direct tables use the scenario-specific benchmark direct reference.
- Low tables use the scenario-specific benchmark low reference.
- Uncertainty is reported as standard error and normal-approximation `95%` confidence intervals.

## Hybrid settings kept fixed

- Asset grid points: `181`.
- Asset range factors: `0.35` to `3.00`.
- Volatility truncation quantile: `0.997`.
- FST pad factor: `4`.
- FST batch size: `256`.

## ATM put (`K = 100`)

### Benchmark reference

| Estimator | Paths | Price | SE | 95% CI lower | 95% CI upper | Direct-low gap |
| --- | --- | --- | --- | --- | --- | --- |
| Direct | 2,000 | 6.556090 | 0.185595 | 6.192323 | 6.919857 | -6.234% |
| Low | 2,000 | 6.147378 | 0.175207 | 5.803971 | 6.490784 | -6.234% |

### Direct sweep vs benchmark direct reference

| Paths | Method | Price | SE | 95% CI lower | 95% CI upper | Relative error | Direct-low gap |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 250 | LSMC benchmark | 6.868708 | 0.579952 | 5.732003 | 8.005413 | 4.768% | -32.095% |
| 250 | Hybrid LSMC-PDE with FFT | 6.263707 | 0.010575 | 6.242980 | 6.284434 | 4.460% | -0.231% |
| 500 | LSMC benchmark | 7.196388 | 0.402452 | 6.407582 | 7.985193 | 9.766% | -18.478% |
| 500 | Hybrid LSMC-PDE with FFT | 6.266692 | 0.007136 | 6.252704 | 6.280679 | 4.414% | -0.197% |

### Low sweep vs benchmark low reference

| Paths | Method | Price | SE | 95% CI lower | 95% CI upper | Relative error | Direct-low gap |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 250 | LSMC benchmark | 4.664222 | 0.437147 | 3.807413 | 5.521030 | 24.127% | -32.095% |
| 250 | Hybrid LSMC-PDE with FFT | 6.249228 | 0.056294 | 6.138891 | 6.359565 | 1.657% | -0.231% |
| 500 | LSMC benchmark | 5.866617 | 0.348070 | 5.184400 | 6.548833 | 4.567% | -18.478% |
| 500 | Hybrid LSMC-PDE with FFT | 6.254365 | 0.041754 | 6.172527 | 6.336204 | 1.740% | -0.197% |

## Generated figures

- `gdmr_path_sweep_smoke_direct_relative_error.svg`
- `gdmr_path_sweep_smoke_direct_relative_error_with_ci.svg`
- `gdmr_path_sweep_smoke_low_relative_error.svg`
- `gdmr_path_sweep_smoke_low_relative_error_with_ci.svg`
