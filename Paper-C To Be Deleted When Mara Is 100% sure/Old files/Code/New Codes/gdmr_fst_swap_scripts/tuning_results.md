# FST Hybrid Tuning Results

This note tunes the FST/FFT hybrid in this folder against the repo's current "normal/original" gDMR LSMC benchmark from `Code/gdmr_standalone`.

## Fixed benchmark block

```text
GDMR_EXERCISE_DATES=100
GDMR_EULER_STEPS=600
GDMR_LSMC_PATHS=1000000
GDMR_LSMC_LOW_PATHS=1000000
GDMR_LSMC_SEED=2026
GDMR_LSMC_LOW_SEED=2103
```

## Repo benchmark result

The repo benchmark was run from `Code/gdmr_standalone/run_gdmr_benchmark_put.py`.

Because that script still has the Windows memmap temp cleanup issue, it was run through a no-source-change runtime cleanup wrapper. The pricing logic itself was unchanged.

| Quantity | Value |
| --- | ---: |
| LSMC direct | `6.294204` |
| LSMC direct SE | `0.008024` |
| LSMC low | `6.309298` |
| LSMC low SE | `0.008035` |
| LSMC direct-low gap | `+0.24%` |

## Diagnostic alternate-LSMC result from this folder

This is **not** the headline benchmark. It is included only to show why this folder and the repo branch are not the same numerical baseline.

| Quantity | Value |
| --- | ---: |
| This folder's LSMC direct | `6.399922` |
| This folder's LSMC low | `6.403215` |
| Relative difference vs repo benchmark direct | `1.68%` |
| Relative difference vs repo benchmark low | `1.49%` |

## Hybrid sweep

Fixed hybrid settings across all rows:

```text
GDMR_EXERCISE_DATES=100
GDMR_EULER_STEPS=600
GDMR_HYBRID_ASSET_LOW_FACTOR=0.35
GDMR_HYBRID_ASSET_HIGH_FACTOR=3.00
GDMR_HYBRID_VOL_QUANTILE=0.995
GDMR_HYBRID_FST_PAD_FACTOR=4
GDMR_HYBRID_FST_BATCH_SIZE=256
GDMR_HYBRID_SEED=2026
GDMR_HYBRID_LOW_SEED=2103
```

| Row | Paths | Low paths | Asset points | Hybrid direct | Direct SE | Hybrid low | Low SE | Direct rel. err vs repo LSMC direct | Low rel. err vs repo LSMC low | Hybrid direct-low gap |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A | `10000` | `10000` | `181` | `6.212782` | `0.001255` | `6.167904` | `0.010456` | `1.294%` | `2.241%` | `-0.722%` |
| B | `20000` | `20000` | `181` | `6.221352` | `0.000874` | `6.191730` | `0.007345` | `1.157%` | `1.863%` | `-0.476%` |
| C | `30000` | `30000` | `181` | `6.212668` | `0.000716` | `6.190681` | `0.005990` | `1.295%` | `1.880%` | `-0.354%` |
| D | `30000` | `30000` | `201` | `6.215905` | `0.000715` | `6.194107` | `0.005986` | `1.244%` | `1.826%` | `-0.351%` |
| E | `40000` | `40000` | `201` | `6.219912` | `0.000614` | `6.196955` | `0.005154` | `1.180%` | `1.781%` | `-0.369%` |

## Best run

No row reached the `<= 1%` direct-error target versus the repo LSMC direct benchmark.

Best available row:

| Row | Why it is best | Direct rel. err | Low rel. err | Hybrid direct-low gap |
| --- | --- | ---: | ---: | ---: |
| B | Lowest direct relative error | `1.157%` | `1.863%` | `-0.476%` |

## Interpretation

- The FST hybrid clearly stabilized as path counts increased, with direct standard error shrinking from `0.001255` to `0.000614`.
- However, the direct price did not keep moving monotonically toward the repo benchmark. The sweep appears to plateau around `1.16%` to `1.30%` direct relative error.
- Increasing the asset grid from `181` to `201` helped only modestly.
- The hybrid direct-low gap became much tighter than the older matched run, staying within about `-0.35%` to `-0.72%`, which is a good sign for internal consistency.

## Conclusion

This folder already looks like the correct **Farahany-style hybrid direction**, but under this exact sweep it did **not** hit the `1%` direct-error target against the repo benchmark. The best observed result was Row B at `1.157%`.

That means the next improvement step should not be "change the product/model." It should be one of:

- push the FST hybrid further with still larger path counts or a richer grid/basis
- change the benchmark definition if the repo LSMC branch is not the intended headline benchmark
- merge the repo benchmark branch and the FST hybrid branch into one clean folder so comparisons are no longer split across branches
