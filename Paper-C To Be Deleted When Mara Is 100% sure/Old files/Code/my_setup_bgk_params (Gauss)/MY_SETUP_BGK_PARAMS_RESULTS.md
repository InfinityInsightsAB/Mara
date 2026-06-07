# BGK Parameters in `my_setup_bgk_params`

This folder is a copy of `Code/my_setup_delta_075`, but it keeps that older
methodology and only swaps in the BGK-style parameter block.

So this branch is:

- Longstaff-Schwartz Monte Carlo as the benchmark
- Gauss-Hermite hybrid LSMC-PDE as the hybrid method
- not the newer FST/Farahany branch

## Screenshot Notation -> Code Notation

| Screenshot symbol | Code name | Value used |
| --- | --- | ---: |
| `theta` | `theta` | `0.078` |
| `kappa_1` | `kappa1` | `5.5` |
| `kappa_2` | `kappa2` | `0.1` |
| `v_0` | `v0` | `0.114` |
| `v'_0` | `vp0` | `0.110` |
| `alpha_1` | `delta1` | `0.94` |
| `alpha_2` | `delta2` | `0.94` |
| `xi_1` | `xi1` | `2.689` |
| `xi_2` | `xi2` | `0.502` |
| `rho_12 = tilde rho_12` | `rho12` | `-0.982` |
| `rho_13 = tilde rho_13` | `rho13` | `-0.727` |
| `rho_23` | `rho23` | `0.59` |

Important note:

- `tilde rho_23 = -0.656` was **not** used as the code input.
- The actual Brownian correlation triple used by this copied setup is:
  `rho12 = -0.982`, `rho13 = -0.727`, `rho23 = 0.59`.

## Contract Assumptions

| Quantity | Value |
| --- | ---: |
| `S0` | `100.0` |
| `T` | `1.0` |
| `r` | `0.0` |
| Payoff | Bermudan put |

Scenario strikes:

- ITM put: `K=110`
- ATM put: `K=100`
- OTM put: `K=90`

## Numerical Run Block

All three runs used the same numerical block:

```text
GDMR_S0=100
GDMR_MATURITY=1
GDMR_EXERCISE_DATES=100
GDMR_EULER_STEPS=600
GDMR_LSMC_PATHS=1000000
GDMR_LSMC_SEED=2026
GDMR_LSMC_LOW_SEED=2103
GDMR_HYBRID_PATHS=20000
GDMR_HYBRID_LOW_PATHS=20000
GDMR_HYBRID_ASSET_POINTS=181
GDMR_HYBRID_HERMITE_NODES=64
GDMR_HYBRID_ASSET_LOW_FACTOR=0.35
GDMR_HYBRID_ASSET_HIGH_FACTOR=3.00
GDMR_HYBRID_VOL_QUANTILE=0.997
GDMR_HYBRID_SEED=2026
GDMR_HYBRID_LOW_SEED=2103
```

Note:

- This copied branch does not expose a separate `GDMR_LSMC_LOW_PATHS` input.
- Its LSMC low estimator remains tied to the main LSMC path count.

## Scenario Results

| Scenario | `S0` | `K` | Benchmark direct | Benchmark direct SE | Benchmark low | Benchmark low SE | Hybrid direct | Hybrid direct SE | Hybrid low | Hybrid low SE | Hybrid direct rel. err. | Hybrid low rel. err. | Benchmark direct-low gap | Hybrid direct-low gap |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ITM put | `100` | `110` | `16.597246` | `0.017589` | `16.612028` | `0.017574` | `16.758325` | `0.015292` | `16.717166` | `0.132848` | `0.971%` | `0.633%` | `+0.089%` | `-0.246%` |
| ATM put | `100` | `100` | `11.348264` | `0.015679` | `11.345645` | `0.015661` | `11.368795` | `0.011842` | `11.430247` | `0.114106` | `0.181%` | `0.746%` | `-0.023%` | `+0.541%` |
| OTM put | `100` | `90` | `7.425066` | `0.013177` | `7.403862` | `0.013146` | `7.416214` | `0.008521` | `7.430183` | `0.092815` | `0.119%` | `0.356%` | `-0.286%` | `+0.188%` |

## Generated Graphs

The copied compare workflow was updated so each scenario writes a stable SVG:

- `compare_put_prices_itm.svg`
- `compare_put_prices_atm.svg`
- `compare_put_prices_otm.svg`

`compare_put_prices.svg` remains as the last-run generic snapshot.

## Short Interpretation

- Under the BGK parameter block, this older Gauss-Hermite hybrid stays within
  `1%` of the LSMC direct benchmark in all three scenarios.
- The tightest direct match is the OTM case at `0.119%`, followed by ATM at
  `0.181%`.
- The ITM case is the loosest of the three, but it still stays just under the
  `1%` direct target at `0.971%`.
- The hybrid low estimator remains reasonably close to the benchmark low
  estimator, but its reported standard error is much larger in every scenario.
- Compared with the newer BGK Testing branch, this copied setup is answering a
  different question: how the BGK parameter block behaves inside the older
  `my_setup_delta_075` Gauss-Hermite methodology rather than inside the newer
  FST-style hybrid workflow.
