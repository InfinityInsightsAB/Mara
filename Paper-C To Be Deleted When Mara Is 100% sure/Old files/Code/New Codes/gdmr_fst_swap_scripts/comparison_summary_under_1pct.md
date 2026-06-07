# gDMR FST Comparison Summary

Date: `2026-03-19`

## Headline result

Target benchmark: the repo's current "normal/original" gDMR LSMC benchmark from `Code/gdmr_standalone`, not this folder's local alternate-LSMC file.

| Quantity | Repo benchmark LSMC | Best FST hybrid run |
| --- | ---: | ---: |
| Direct price | `6.294204` | `6.300429` |
| Direct SE | `0.008024` | `0.000976` |
| Low price | `6.309298` | `6.271978` |
| Low SE | `0.008035` | `0.006975` |
| Direct relative error | `0.000%` | `0.099%` |
| Low relative error | `0.000%` | `0.592%` |
| Direct-low gap | `+0.240%` | `-0.452%` |

## Best setting

The cleanest under-`1%` result was obtained by changing only the volatility truncation setting:

| Setting | Value |
| --- | ---: |
| `GDMR_EXERCISE_DATES` | `100` |
| `GDMR_EULER_STEPS` | `600` |
| `GDMR_HYBRID_PATHS` | `20000` |
| `GDMR_HYBRID_LOW_PATHS` | `20000` |
| `GDMR_HYBRID_ASSET_POINTS` | `181` |
| `GDMR_HYBRID_ASSET_LOW_FACTOR` | `0.35` |
| `GDMR_HYBRID_ASSET_HIGH_FACTOR` | `3.00` |
| `GDMR_HYBRID_VOL_QUANTILE` | `0.997` |
| `GDMR_HYBRID_FST_PAD_FACTOR` | `4` |
| `GDMR_HYBRID_FST_BATCH_SIZE` | `256` |
| `GDMR_HYBRID_SEED` | `2026` |
| `GDMR_HYBRID_LOW_SEED` | `2103` |

## What changed the result

Cheap pilot sweeps showed:

| Change tested | Effect on direct price |
| --- | --- |
| `FST_PAD_FACTOR: 4 -> 8` | Almost no effect |
| Wider asset grid / wider asset range | Little to no improvement |
| `VOL_QUANTILE: 0.995 -> 0.997` | Main improvement lever |

## Confirmation sweep at `20k`

| Run | `VOL_QUANTILE` | Hybrid direct | Direct rel. err. | Hybrid low | Low rel. err. |
| --- | ---: | ---: | ---: | ---: | ---: |
| Baseline old tuning | `0.9950` | `6.221352` | `1.157%` | `6.191730` | `1.863%` |
| Tuned | `0.9965` | `6.279978` | `0.226%` | `6.250192` | `0.937%` |
| Tuned best direct match | `0.9970` | `6.300429` | `0.099%` | `6.271978` | `0.592%` |
| Tuned | `0.9975` | `6.320810` | `0.423%` | `6.293987` | `0.243%` |

## Short takeaway

- We did get the FST branch below `1%`.
- The main fix was not the asset grid or the FFT padding.
- The main fix was a less aggressive volatility truncation cap for the compact-support volatility basis.
- The recommended setting is `GDMR_HYBRID_VOL_QUANTILE=0.997`.
