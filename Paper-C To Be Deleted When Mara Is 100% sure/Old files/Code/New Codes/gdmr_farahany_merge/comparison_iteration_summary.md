# Merged-Folder Comparison Iteration Summary

This file freezes the merged-folder iteration at the point requested by the user.
No additional benchmark or hybrid runs were performed after the results recorded here.

## Benchmark Block

The benchmark is the repo-style LSMC benchmark run through
`run_gdmr_benchmark_put.py`, which wraps `Code/gdmr_standalone/run_gdmr_benchmark_put.py`
with a Windows-safe cleanup patch but does not change the pricing logic.

### Benchmark environment

```text
GDMR_EXERCISE_DATES=100
GDMR_EULER_STEPS=600
GDMR_LSMC_PATHS=1000000
GDMR_LSMC_LOW_PATHS=1000000
GDMR_LSMC_SEED=2026
GDMR_LSMC_LOW_SEED=2103
```

### Benchmark results

| Metric | Value |
| --- | ---: |
| LSMC direct price | 6.294204 |
| LSMC direct SE | 0.008024 |
| LSMC low price | 6.309298 |
| LSMC low SE | 0.008035 |
| Benchmark direct-low gap | +0.240% |

The sub-1% target for the hybrid direct price corresponds to a threshold of
approximately `6.231262` against the fixed benchmark `LSMC direct = 6.294204`.

## Rows Tested In Order

The merged-folder sweep was resumed directly in the previously best-performing
region around `20000` paths. The table below lists all merged-folder hybrid rows
that were actually run and retained before the sweep was stopped.

| Row | Hybrid paths | Hybrid low paths | Asset points | Low factor | High factor | Pad factor | Hybrid direct | Hybrid direct SE | Hybrid low | Hybrid low SE | Direct rel. err. vs LSMC direct | Low rel. err. vs LSMC low | Hybrid direct-low gap |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| S1-A | 20000 | 20000 | 201 | 0.35 | 3.00 | 4 | 6.224560 | 0.000873 | 6.195277 | 0.007339 | 1.107% | 1.807% | -0.470% |
| S1-B | 20000 | 20000 | 241 | 0.35 | 3.00 | 4 | 6.223839 | 0.000874 | 6.194614 | 0.007341 | 1.118% | 1.818% | -0.470% |
| S1-D | 20000 | 20000 | 281 | 0.35 | 3.00 | 4 | 6.222782 | 0.000874 | 6.193397 | 0.007343 | 1.135% | 1.837% | -0.472% |
| S2-C | 20000 | 20000 | 201 | 0.35 | 2.75 | 4 | 6.223005 | 0.000874 | 6.193576 | 0.007342 | 1.131% | 1.834% | -0.473% |
| S2-D | 20000 | 20000 | 201 | 0.35 | 2.50 | 4 | 6.223594 | 0.000874 | 6.194190 | 0.007341 | 1.122% | 1.824% | -0.472% |
| S2-E | 20000 | 20000 | 201 | 0.30 | 3.00 | 4 | 6.226058 | 0.000873 | 6.196817 | 0.007337 | 1.083% | 1.783% | -0.470% |
| S2-B | 20000 | 20000 | 201 | 0.32 | 2.75 | 4 | 6.221697 | 0.000874 | 6.192266 | 0.007344 | 1.152% | 1.855% | -0.473% |

## Best Row

| Metric | Value |
| --- | ---: |
| Row label | S2-E |
| Hybrid paths | 20000 |
| Hybrid low paths | 20000 |
| Asset points | 201 |
| Low factor | 0.30 |
| High factor | 3.00 |
| Pad factor | 4 |
| Hybrid direct | 6.226058 |
| Hybrid direct SE | 0.000873 |
| Hybrid low | 6.196817 |
| Hybrid low SE | 0.007337 |
| Direct rel. err. vs LSMC direct | 1.083% |
| Low rel. err. vs LSMC low | 1.783% |
| Hybrid direct-low gap | -0.470% |

## Pass/Fail Against the 1% Target

- Target metric: `|Hybrid direct - LSMC direct| / |LSMC direct| <= 1%`
- Current best row: `S2-E`
- Outcome: not reached
- Remaining price gap to the 1% threshold: about `0.005204`
- Remaining percentage-point gap to the 1% target: about `0.083%`

## Final Chosen Environment Block

This is the best merged-folder row obtained before the sweep was stopped.

```text
GDMR_EXERCISE_DATES=100
GDMR_EULER_STEPS=600
GDMR_HYBRID_PATHS=20000
GDMR_HYBRID_LOW_PATHS=20000
GDMR_HYBRID_ASSET_POINTS=201
GDMR_HYBRID_ASSET_LOW_FACTOR=0.30
GDMR_HYBRID_ASSET_HIGH_FACTOR=3.00
GDMR_HYBRID_VOL_QUANTILE=0.995
GDMR_HYBRID_FST_PAD_FACTOR=4
GDMR_HYBRID_FST_BATCH_SIZE=256
GDMR_HYBRID_SEED=2026
GDMR_HYBRID_LOW_SEED=2103
```

## Short Conclusion

Within the merged folder, the Farahany-style FST hybrid can be pushed close to
the repo benchmark, but the retained runs here stop at `1.083%` direct relative
error rather than crossing below `1%`. The best improvement in this frozen
iteration came from lowering the asset-grid lower bound from `0.35` to `0.30`
while keeping `20000` training paths, `20000` low-estimator paths, `201` asset
points, and `pad=4`.

## Notes On What Was Not Run

- No further rows were run after the user requested the sweep to stop.
- The merged-folder comparison script was not rerun after the stop request.
- The earlier broader FST-side sweep remains documented in
  `Code/New Codes/gdmr_fst_swap_scripts/tuning_results.md`.
