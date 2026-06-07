# Matched Run Comparison

This file reports one shared run block for both folders in `Code/New Codes`.

## Matched run block

All runs used the following environment settings:

```text
GDMR_EXERCISE_DATES=100
GDMR_EULER_STEPS=600
GDMR_LSMC_PATHS=50000
GDMR_LSMC_LOW_PATHS=50000
GDMR_LSMC_SEED=2026
GDMR_LSMC_LOW_SEED=2103
GDMR_HYBRID_PATHS=5000
GDMR_HYBRID_LOW_PATHS=5000
GDMR_HYBRID_SEED=2026
GDMR_HYBRID_LOW_SEED=2103
GDMR_HYBRID_ASSET_POINTS=181
GDMR_HYBRID_ASSET_LOW_FACTOR=0.35
GDMR_HYBRID_ASSET_HIGH_FACTOR=3.00
GDMR_HYBRID_VOL_QUANTILE=0.995
GDMR_HYBRID_HERMITE_NODES=64
GDMR_HYBRID_FST_PAD_FACTOR=4
GDMR_HYBRID_FST_BATCH_SIZE=256
```

## Execution note

- `gdmr_standalone_version1/run_gdmr_hybrid_put.py` ran directly.
- `gdmr_fst_swap_scripts/run_gdmr_lsmc_put.py` ran directly.
- `gdmr_fst_swap_scripts/run_gdmr_hybrid_put.py` ran directly.
- `gdmr_standalone_version1/run_gdmr_benchmark_put.py` failed on direct Windows execution because of a memmap temp-file cleanup error after pricing. To keep the source untouched, its matched result below was obtained by rerunning the same script code through a runtime-only wrapper that suppresses the cleanup exception.

## Matched outputs

| Folder | Method | Direct price | Direct SE | Low price | Low SE |
| --- | --- | ---: | ---: | ---: | ---: |
| `gdmr_standalone_version1` | LSMC | `6.256484` | `0.035921` | `6.325146` | `0.036035` |
| `gdmr_standalone_version1` | Hybrid | `6.428497` | `0.001539` | `6.165195` | `0.110854` |
| `gdmr_fst_swap_scripts` | LSMC | `6.346069` | `0.035168` | `6.396505` | `0.035355` |
| `gdmr_fst_swap_scripts` | Hybrid | `6.215271` | `0.001814` | `6.196529` | `0.014742` |

## Relative errors

### Hybrid vs LSMC within each folder

| Folder | Direct: `|Hybrid - LSMC| / |LSMC|` | Low: `|Hybrid - LSMC| / |LSMC|` |
| --- | ---: | ---: |
| `gdmr_standalone_version1` | `2.75%` | `2.53%` |
| `gdmr_fst_swap_scripts` | `2.06%` | `3.13%` |

### `version1` vs `fst_swap` for LSMC

| Quantity | Relative error |
| --- | ---: |
| LSMC direct | `1.41%` |
| LSMC low | `1.12%` |

### `version1` vs `fst_swap` for Hybrid

| Quantity | Relative error |
| --- | ---: |
| Hybrid direct | `3.43%` |
| Hybrid low | `0.51%` |

## Direct-low gap as a bias / stability signal

The table below uses:

- absolute gap = `low - direct`
- relative gap = `(low - direct) / direct`

| Folder | Method | Absolute gap | Relative gap |
| --- | --- | ---: | ---: |
| `gdmr_standalone_version1` | LSMC | `+0.068662` | `+1.10%` |
| `gdmr_standalone_version1` | Hybrid | `-0.263302` | `-4.10%` |
| `gdmr_fst_swap_scripts` | LSMC | `+0.050436` | `+0.79%` |
| `gdmr_fst_swap_scripts` | Hybrid | `-0.018742` | `-0.30%` |

## What these numbers suggest

- The two LSMC baselines are fairly close under the matched block, differing by about `1.1%` to `1.4%`. That is small enough to say they are in the same numerical neighborhood, but large enough to confirm that the folders are not using the same benchmark policy.
- The hybrid direct estimates differ more, by about `3.43%`. This is consistent with the folders using different conditional solvers and different low-estimator constructions.
- The hybrid low estimates are much closer across folders, differing by only about `0.51%`.
- The strongest numerical stability signal in this run is the direct-low gap:
- `gdmr_standalone_version1` hybrid has a large `-4.10%` gap
- `gdmr_fst_swap_scripts` hybrid has a much tighter `-0.30%` gap

On this matched run, `gdmr_fst_swap_scripts` looks more internally consistent on the hybrid side.

## Run-source notes

- `gdmr_standalone_version1` values were parsed from the script's fixed labeled stdout.
- `gdmr_fst_swap_scripts` values were parsed from the scripts' `RESULT_JSON` payloads.
- No compare-helper script was used for these numbers.
