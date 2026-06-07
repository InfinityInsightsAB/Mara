# Equal-delta gDMR experiment: `delta1 = delta2 = 0.75`

This note records a new standalone `gdmr_standalone` experiment using the same tuned numerical setup as the current default run, but with

- `delta1 = 0.75`
- `delta2 = 0.75`

The experiment code lives in `Code/my_setup_delta_075/`.

## Setup

All parameters were kept the same as the current tuned `gdmr_standalone` run except for the two delta values.

| Quantity | Value |
| --- | ---: |
| `S0` | `100` |
| `K` | `100` |
| `T` | `1` |
| `r` | `0.03` |
| `v0` | `0.04` |
| `vp0` | `0.04` |
| `kappa1` | `2.0` |
| `kappa2` | `1.0` |
| `theta` | `0.04` |
| `xi1` | `0.35` |
| `xi2` | `0.20` |
| `rho12` | `0.20` |
| `rho13` | `0.10` |
| `rho23` | `0.10` |
| `delta1` | `0.75` |
| `delta2` | `0.75` |
| `N_ex` | `100` |
| `M` | `600` |
| LSMC `N` | `1000000` |
| Hybrid `N` | `30000` |
| Hybrid `N_low` | `30000` |
| Hybrid `N_S` | `181` |
| Hybrid `N_hermite` | `64` |

## Results

| Estimator | Price | Standard error | Relative error |
| --- | ---: | ---: | ---: |
| LSMC direct | `6.653560` | `0.007822` | reference |
| LSMC low | `6.655062` | `0.007819` | `0.02%` vs LSMC direct |
| Hybrid direct | `6.696152` | `0.000375` | `0.64%` vs LSMC direct |
| Hybrid low | `6.545257` | `0.045080` | `1.63%` vs LSMC direct |

Additional comparison:

| Quantity | Value |
| --- | ---: |
| Hybrid low relative error vs LSMC low | `1.65%` |
| `1%` direct target met | `yes` |

Strike-specific comparison plots are saved as `Code/my_setup_delta_075/compare_put_prices_itm.svg`, `Code/my_setup_delta_075/compare_put_prices_atm.svg`, and `Code/my_setup_delta_075/compare_put_prices_otm.svg`.

## Comparison with the current `delta = 0.50` setup

For reference, the current tuned `gdmr_standalone` default uses `delta1 = delta2 = 0.50`.

| Estimator | `delta = 0.50` | `delta = 0.75` | Change |
| --- | ---: | ---: | ---: |
| LSMC direct | `6.384535` | `6.653560` | `+0.269025` |
| LSMC low | `6.387249` | `6.655062` | `+0.267813` |
| Hybrid direct | `6.421758` | `6.696152` | `+0.274394` |
| Hybrid low | `6.265070` | `6.545257` | `+0.280187` |

## Observations

- Moving from `delta1 = delta2 = 0.50` to `delta1 = delta2 = 0.75` increased all four Bermudan put estimates.
- The direct estimators remained very close: the hybrid direct price stayed within `0.64%` of the LSMC direct reference.
- The low estimators also remained reasonably aligned, with the hybrid low estimate about `1.63%` below the LSMC direct reference.
- Under the same path and grid settings, this new equal-delta case still satisfies the `1%` direct-error target.

## ITM and OTM strike tests

Using the same `delta1 = delta2 = 0.75` setup, I also ran one in-the-money put and one out-of-the-money put by changing only the strike:

- ITM put: `K = 110`, `S0 = 100`
- ATM put: `K = 100`, `S0 = 100`
- OTM put: `K = 90`, `S0 = 100`

All other model, path, grid, and seed settings were kept the same.

| Case | Strike | LSMC direct | LSMC low | Hybrid direct | Hybrid low | Hybrid direct rel. error | Hybrid low rel. vs LSMC direct | `1%` target met |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| ITM put | `110` | `12.735850` | `12.734082` | `12.767870` | `12.634384` | `0.25%` | `0.80%` | `yes` |
| ATM put | `100` | `6.653560` | `6.655062` | `6.696152` | `6.545257` | `0.64%` | `1.63%` | `yes` |
| OTM put | `90` | `2.743578` | `2.734472` | `2.791426` | `2.668242` | `1.74%` | `2.75%` | `no` |

Additional relative errors:

| Case | Hybrid low rel. vs LSMC low | LSMC low rel. vs LSMC direct |
| --- | ---: | ---: |
| ITM put | `0.78%` | `0.01%` |
| ATM put | `1.65%` | `0.02%` |
| OTM put | `2.42%` | `0.33%` |

### Strike-test observations

- The ITM put remained very well aligned: the hybrid direct estimate was only `0.25%` above the LSMC direct reference.
- The ATM put also remained within target, with a `0.64%` hybrid direct relative error.
- The OTM put was clearly harder under the same numerical setup: the hybrid direct relative error rose to `1.74%`.
- The low estimators also spread out more in the OTM case than in the ITM case.
- For `delta1 = delta2 = 0.75`, the current tuned hybrid resolution looks more reliable for ITM and ATM puts than for the OTM put.
