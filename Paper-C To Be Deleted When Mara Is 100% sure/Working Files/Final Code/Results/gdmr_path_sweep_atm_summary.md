# ATM put BGK Path Sweep

This experiment reuses only the shipped `Final Code` benchmark and hybrid scripts.

## Setup

- Scenario: `ATM put` with `S0 = 100` and `K = 100`.
- BGK experiment block: `r = 0.0`, `T = 1.0`, `theta = 0.078`, `kappa1 = 5.5`, `kappa2 = 0.1`, `v0 = 0.114`, `vp0 = 0.110`.
- BGK volatility/correlation block: `delta1 = 0.94`, `delta2 = 0.94`, `xi1 = 2.689`, `xi2 = 0.502`, `rho12 = -0.982`, `rho13 = -0.727`, `rho23 = 0.59`.
- Experimental Bermudan exercise dates: `100`.
- Experimental Euler steps for both varying-path curves: `100`.
- Fixed benchmark references were parsed from `bgk_gdmr_comparison.md` instead of rerunning the 1,000,000-path benchmark.
- Path sweep: `50, 250, 500, 1,000, 5,000, 10,000, 20,000, 50,000, 80,000, 100,000`.
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
| 50 | LSMC benchmark | 0.10 s | 19.879832 | 2.939295 | 14.118813 | 25.640851 | 75.489% | -69.509% |
| 50 | Hybrid LSMC-PDE with FFT | 1.60 s | 15.254162 | 0.295000 | 14.675962 | 15.832363 | 34.656% | -39.149% |
| 250 | LSMC benchmark | 0.07 s | 13.870674 | 1.178574 | 11.560668 | 16.180680 | 22.443% | -34.765% |
| 250 | Hybrid LSMC-PDE with FFT | 5.34 s | 12.684056 | 0.104480 | 12.479275 | 12.888837 | 11.968% | -20.894% |
| 500 | LSMC benchmark | 0.08 s | 13.424185 | 0.776062 | 11.903103 | 14.945266 | 18.502% | -21.361% |
| 500 | Hybrid LSMC-PDE with FFT | 11.75 s | 11.350487 | 0.078505 | 11.196617 | 11.504358 | 0.196% | -2.386% |
| 1,000 | LSMC benchmark | 0.09 s | 12.249823 | 0.565278 | 11.141878 | 13.357768 | 8.135% | -12.595% |
| 1,000 | Hybrid LSMC-PDE with FFT | 22.97 s | 11.247129 | 0.056090 | 11.137194 | 11.357065 | 0.716% | -5.806% |
| 5,000 | LSMC benchmark | 0.26 s | 11.998934 | 0.240460 | 11.527631 | 12.470236 | 5.920% | -4.797% |
| 5,000 | Hybrid LSMC-PDE with FFT | 174.97 s | 11.281097 | 0.024631 | 11.232819 | 11.329374 | 0.416% | 2.844% |
| 10,000 | LSMC benchmark | 0.48 s | 11.782279 | 0.165260 | 11.458370 | 12.106188 | 4.008% | -4.734% |
| 10,000 | Hybrid LSMC-PDE with FFT | 335.52 s | 11.339603 | 0.016948 | 11.306385 | 11.372821 | 0.100% | 0.520% |
| 20,000 | LSMC benchmark | 0.74 s | 11.542900 | 0.116958 | 11.313662 | 11.772139 | 1.895% | -0.926% |
| 20,000 | Hybrid LSMC-PDE with FFT | 616.28 s | 11.302260 | 0.011971 | 11.278797 | 11.325724 | 0.230% | 1.699% |
| 50,000 | LSMC benchmark | 2.16 s | 11.395910 | 0.071780 | 11.255221 | 11.536598 | 0.597% | -0.153% |
| 50,000 | Hybrid LSMC-PDE with FFT | 985.18 s | 11.306511 | 0.007410 | 11.291987 | 11.321036 | 0.192% | 0.968% |
| 80,000 | LSMC benchmark | 3.13 s | 11.313535 | 0.056200 | 11.203382 | 11.423688 | 0.130% | 0.981% |
| 80,000 | Hybrid LSMC-PDE with FFT | 1301.54 s | 11.235015 | 0.005827 | 11.223595 | 11.246436 | 0.823% | 0.980% |
| 100,000 | LSMC benchmark | 4.61 s | 11.322506 | 0.050362 | 11.223798 | 11.421215 | 0.051% | 0.721% |
| 100,000 | Hybrid LSMC-PDE with FFT | 1915.44 s | 11.195628 | 0.005193 | 11.185450 | 11.205806 | 1.171% | 1.520% |

## Low sweep vs fixed benchmark low reference

| Paths | Method | Runtime | Price | SE | 95% CI lower | 95% CI upper | Relative error | Direct-low gap |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 50 | LSMC benchmark | 0.10 s | 6.061654 | 1.273957 | 3.564698 | 8.558610 | 46.401% | -69.509% |
| 50 | Hybrid LSMC-PDE with FFT | 1.60 s | 9.282247 | 1.707546 | 5.935457 | 12.629036 | 17.924% | -39.149% |
| 250 | LSMC benchmark | 0.07 s | 9.048553 | 0.865136 | 7.352887 | 10.744219 | 19.991% | -34.765% |
| 250 | Hybrid LSMC-PDE with FFT | 5.34 s | 10.033837 | 1.001703 | 8.070499 | 11.997174 | 11.278% | -20.894% |
| 500 | LSMC benchmark | 0.08 s | 10.556603 | 0.622049 | 9.337386 | 11.775820 | 6.656% | -21.361% |
| 500 | Hybrid LSMC-PDE with FFT | 11.75 s | 11.079658 | 0.664226 | 9.777776 | 12.381541 | 2.031% | -2.386% |
| 1,000 | LSMC benchmark | 0.09 s | 10.707008 | 0.486797 | 9.752885 | 11.661131 | 5.326% | -12.595% |
| 1,000 | Hybrid LSMC-PDE with FFT | 22.97 s | 10.594090 | 0.478139 | 9.656937 | 11.531242 | 6.325% | -5.806% |
| 5,000 | LSMC benchmark | 0.26 s | 11.423382 | 0.231691 | 10.969267 | 11.877497 | 1.008% | -4.797% |
| 5,000 | Hybrid LSMC-PDE with FFT | 174.97 s | 11.601983 | 0.224211 | 11.162529 | 12.041437 | 2.587% | 2.844% |
| 10,000 | LSMC benchmark | 0.48 s | 11.224516 | 0.159721 | 10.911462 | 11.537570 | 0.750% | -4.734% |
| 10,000 | Hybrid LSMC-PDE with FFT | 335.52 s | 11.398554 | 0.165565 | 11.074046 | 11.723062 | 0.789% | 0.520% |
| 20,000 | LSMC benchmark | 0.74 s | 11.435962 | 0.115034 | 11.210494 | 11.661429 | 1.119% | -0.926% |
| 20,000 | Hybrid LSMC-PDE with FFT | 616.28 s | 11.494299 | 0.117132 | 11.264720 | 11.723878 | 1.635% | 1.699% |
| 50,000 | LSMC benchmark | 2.16 s | 11.378491 | 0.071343 | 11.238658 | 11.518323 | 0.611% | -0.153% |
| 50,000 | Hybrid LSMC-PDE with FFT | 985.18 s | 11.415922 | 0.073560 | 11.271745 | 11.560098 | 0.942% | 0.968% |
| 80,000 | LSMC benchmark | 3.13 s | 11.424545 | 0.056132 | 11.314527 | 11.534563 | 1.019% | 0.981% |
| 80,000 | Hybrid LSMC-PDE with FFT | 1301.54 s | 11.345131 | 0.057289 | 11.232845 | 11.457418 | 0.316% | 0.980% |
| 100,000 | LSMC benchmark | 4.61 s | 11.404186 | 0.050229 | 11.305736 | 11.502636 | 0.839% | 0.721% |
| 100,000 | Hybrid LSMC-PDE with FFT | 1915.44 s | 11.365793 | 0.050676 | 11.266468 | 11.465117 | 0.499% | 1.520% |

## Timing summary

- Total scenario runtime: `1:29:42`.
- Slowest run 1: `Hybrid LSMC-PDE with FFT` at `100,000` paths took `1915.44 s`.
- Slowest run 2: `Hybrid LSMC-PDE with FFT` at `80,000` paths took `1301.54 s`.
- Slowest run 3: `Hybrid LSMC-PDE with FFT` at `50,000` paths took `985.18 s`.

## Generated figures

- `gdmr_path_sweep_atm_direct_relative_error.svg`
- `gdmr_path_sweep_atm_low_relative_error.svg`
