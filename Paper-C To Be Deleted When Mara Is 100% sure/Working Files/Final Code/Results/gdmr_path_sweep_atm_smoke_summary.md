# ATM put BGK Path Sweep

This experiment reuses only the shipped `Final Code` benchmark and hybrid scripts.

## Setup

- Scenario: `ATM put` with `S0 = 100` and `K = 100`.
- BGK experiment block: `r = 0.0`, `T = 1.0`, `theta = 0.078`, `kappa1 = 5.5`, `kappa2 = 0.1`, `v0 = 0.114`, `vp0 = 0.110`.
- BGK volatility/correlation block: `delta1 = 0.94`, `delta2 = 0.94`, `xi1 = 2.689`, `xi2 = 0.502`, `rho12 = -0.982`, `rho13 = -0.727`, `rho23 = 0.59`.
- Experimental Bermudan exercise dates: `100`.
- Experimental Euler steps for both varying-path curves: `100`.
- Fixed benchmark references were parsed from `bgk_gdmr_comparison.md` instead of rerunning the 1,000,000-path benchmark.
- Path sweep: `50, 250, 500`.
- Benchmark seeds for the varying-path curve: `2026` and `2103`.
- Hybrid seeds for the varying-path curve: `2026` and `2103`.

## Fixed benchmark reference

| Estimator | Price | SE | 95% CI lower | 95% CI upper | Direct-low gap |
| --- | --- | --- | --- | --- | --- |
| Direct | 11.328264 | 0.015868 | 11.297163 | 11.359365 | -0.167% |
| Low | 11.309356 | 0.015856 | 11.278278 | 11.340434 | -0.167% |

## Hybrid settings kept fixed

- Asset grid points: `181`.
- Asset range factors: `0.35` to `3.00`.
- Volatility truncation quantile: `0.997`.
- FST pad factor: `4`.
- FST batch size: `256`.

## Direct sweep vs fixed benchmark direct reference

| Paths | Method | Runtime | Price | SE | 95% CI lower | 95% CI upper | Relative error | Direct-low gap |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 50 | LSMC benchmark | 0.08 s | 19.879832 | 2.939295 | 14.118813 | 25.640851 | 75.489% | -69.509% |
| 50 | Hybrid LSMC-PDE with FFT | 1.70 s | 15.254162 | 0.295000 | 14.675962 | 15.832363 | 34.656% | -39.149% |
| 250 | LSMC benchmark | 0.06 s | 13.870674 | 1.178574 | 11.560668 | 16.180680 | 22.443% | -34.765% |
| 250 | Hybrid LSMC-PDE with FFT | 5.50 s | 12.684056 | 0.104480 | 12.479275 | 12.888837 | 11.968% | -20.894% |
| 500 | LSMC benchmark | 0.09 s | 13.424185 | 0.776062 | 11.903103 | 14.945266 | 18.502% | -21.361% |
| 500 | Hybrid LSMC-PDE with FFT | 11.76 s | 11.350487 | 0.078505 | 11.196617 | 11.504358 | 0.196% | -2.386% |

## Low sweep vs fixed benchmark low reference

| Paths | Method | Runtime | Price | SE | 95% CI lower | 95% CI upper | Relative error | Direct-low gap |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 50 | LSMC benchmark | 0.08 s | 6.061654 | 1.273957 | 3.564698 | 8.558610 | 46.401% | -69.509% |
| 50 | Hybrid LSMC-PDE with FFT | 1.70 s | 9.282247 | 1.707546 | 5.935457 | 12.629036 | 17.924% | -39.149% |
| 250 | LSMC benchmark | 0.06 s | 9.048553 | 0.865136 | 7.352887 | 10.744219 | 19.991% | -34.765% |
| 250 | Hybrid LSMC-PDE with FFT | 5.50 s | 10.033837 | 1.001703 | 8.070499 | 11.997174 | 11.278% | -20.894% |
| 500 | LSMC benchmark | 0.09 s | 10.556603 | 0.622049 | 9.337386 | 11.775820 | 6.656% | -21.361% |
| 500 | Hybrid LSMC-PDE with FFT | 11.76 s | 11.079658 | 0.664226 | 9.777776 | 12.381541 | 2.031% | -2.386% |

## Timing summary

- Total scenario runtime: `0:00:19`.
- Slowest run 1: `Hybrid LSMC-PDE with FFT` at `500` paths took `11.76 s`.
- Slowest run 2: `Hybrid LSMC-PDE with FFT` at `250` paths took `5.50 s`.
- Slowest run 3: `Hybrid LSMC-PDE with FFT` at `50` paths took `1.70 s`.

## Generated figures

- `gdmr_path_sweep_atm_smoke_direct_relative_error.svg`
- `gdmr_path_sweep_atm_smoke_low_relative_error.svg`
