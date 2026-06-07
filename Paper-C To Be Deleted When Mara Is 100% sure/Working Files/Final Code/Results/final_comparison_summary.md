# Final Code Results Summary

This is the single curated result note for the final self-contained package in
`Final Code`.

## Final Package Purpose

The packaged method is:

- Bermudan put pricing
- under the gDMR model
- with the repo/original LSMC benchmark
- and a Farahany-style hybrid LSMC-PDE implementation that uses an FST/FFT
  conditional solver and a hybrid low estimator

## Headline Comparison

| Quantity | Final benchmark LSMC | Final hybrid FST |
| --- | ---: | ---: |
| Direct price | `6.294204` | `6.300429` |
| Direct SE | `0.008024` | `0.000976` |
| Low price | `6.309298` | `6.271978` |
| Low SE | `0.008035` | `0.006975` |
| Direct relative error | `0.000%` | `0.099%` |
| Low relative error | `0.000%` | `0.592%` |
| Direct-low gap | `+0.240%` | `-0.452%` |

## Final Shipped Hybrid Setting

The final package ships with the tuned Farahany-style volatility truncation
default `GDMR_HYBRID_VOL_QUANTILE=0.997`.

The headline under-`1%` comparison uses the following hybrid block:

```text
GDMR_EXERCISE_DATES=100
GDMR_EULER_STEPS=600
GDMR_HYBRID_PATHS=20000
GDMR_HYBRID_LOW_PATHS=20000
GDMR_HYBRID_ASSET_POINTS=181
GDMR_HYBRID_ASSET_LOW_FACTOR=0.35
GDMR_HYBRID_ASSET_HIGH_FACTOR=3.00
GDMR_HYBRID_VOL_QUANTILE=0.997
GDMR_HYBRID_FST_PAD_FACTOR=4
GDMR_HYBRID_FST_BATCH_SIZE=256
GDMR_HYBRID_SEED=2026
GDMR_HYBRID_LOW_SEED=2103
```

The benchmark reference uses:

```text
GDMR_EXERCISE_DATES=100
GDMR_EULER_STEPS=600
GDMR_LSMC_PATHS=1000000
GDMR_LSMC_LOW_PATHS=1000000
GDMR_LSMC_SEED=2026
GDMR_LSMC_LOW_SEED=2103
```

## Why This Is The Final Retained Result

- It keeps the benchmark definition fixed to the repo/original gDMR LSMC branch.
- It keeps the hybrid solver in the Farahany-style FST/FFT family.
- It gets the hybrid direct estimate below `1%` relative error against the
  benchmark direct estimate.
- The key numerical improvement was using a slightly less aggressive volatility
  truncation cap in the compact-support volatility basis.

## Short Takeaway

The final packaged hybrid does not change the product, the gDMR model, or the
hybrid LSMC-PDE algorithm family. The retained improvement comes from the
numerical truncation choice used by the volatility basis, and the final tuned
setting gives a direct relative error of `0.099%` against the repo/original
benchmark.
