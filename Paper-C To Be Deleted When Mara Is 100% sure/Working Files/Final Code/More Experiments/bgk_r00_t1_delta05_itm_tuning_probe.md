# BGK `r=0`, `T=1`, `delta1=delta2=0.5` Hybrid Tuning Probe

This note saves the partial tuning results available so far for the ITM put
scenario only:

- `S0=100`
- `K=110`
- `T=1`
- `r=0`
- `delta1=delta2=0.5`

The benchmark reference is the production LSMC result already saved in
`bgk_r00_t1_delta05_comparison_table.csv`.

## Benchmark Reference

| Quantity | Value |
| --- | ---: |
| Benchmark direct price | `14.719728` |
| Benchmark direct SE | `0.019787` |
| Benchmark low price | `14.691320` |
| Benchmark low SE | `0.019752` |

## ITM Hybrid Probe Results

| Hybrid setting | Paths | Low paths | Asset points | Asset low factor | Asset high factor | Vol quantile | Direct price | Direct SE | Low price | Low SE | Direct rel. err. | Low rel. err. |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline production | `20000` | `20000` | `181` | `0.35` | `3.00` | `0.997` | `15.035798` | `0.018057` | `14.798167` | `0.144063` | `2.147%` | `0.727%` |
| Increased paths + grid | `40000` | `40000` | `241` | `0.35` | `3.00` | `0.997` | `15.042663` | `0.012459` | `14.810332` | `0.103725` | `2.194%` | `0.810%` |
| Increased paths + wider grid + higher quantile | `40000` | `40000` | `301` | `0.30` | `3.50` | `0.999` | `15.151278` | `0.012445` | `14.830387` | `0.105159` | `2.932%` | `0.947%` |

## Current Takeaway

- The two heavier hybrid settings tested so far did not improve the ITM direct
  relative error against the benchmark.
- The `40000 / 241` setting slightly reduced Monte Carlo standard error but
  moved the direct estimate slightly farther from the benchmark mean.
- The `40000 / 301 / q=0.999` setting moved the direct estimate farther away
  again, so it is not a good upgrade candidate for this case.
- These are partial results only; ATM and OTM were not rerun for the heavier
  settings in this probe.
