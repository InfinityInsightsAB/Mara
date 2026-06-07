# Summary

This file summarizes the main experiment results currently stored in `Final Code/More Experiments`.
Smoke runs are kept as validation artifacts in the folder, but they are intentionally omitted from this summary.

Operational artifacts such as runner scripts, `_scratch`, and inaccessible `tmp...` directories are intentionally excluded.

## BGK `r=0.03`, `T=1`

This family uses the BGK model block with `GDMR_R=0.03` and `GDMR_MATURITY=1.0`.

### Results

| Scenario | `S0` | `K` | `T` | Benchmark direct | Benchmark direct SE | Benchmark low | Benchmark low SE | Hybrid direct | Hybrid direct SE | Hybrid low | Hybrid low SE | Hybrid direct rel. err. | Hybrid low rel. err. | Benchmark direct-low gap | Hybrid direct-low gap |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ATM | `100` | `100` | `1` | `10.373824` | `0.014582` | `10.354497` | `0.014565` | `10.286746` | `0.011403` | `10.376803` | `0.100545` | `0.839%` | `0.215%` | `-0.186%` | `+0.875%` |
| ITM put | `100` | `110` | `1` | `15.367020` | `0.015981` | `15.356918` | `0.015966` | `15.311325` | `0.015193` | `15.437225` | `0.113611` | `0.362%` | `0.523%` | `-0.066%` | `+0.822%` |
| OTM put | `100` | `90` | `1` | `6.708403` | `0.012260` | `6.690326` | `0.012249` | `6.690825` | `0.008034` | `6.757117` | `0.083687` | `0.262%` | `0.998%` | `-0.269%` | `+0.991%` |

Observations:
- ATM: hybrid direct rel. err. `0.839%`, hybrid low rel. err. `0.215%`, benchmark direct-low gap `-0.186%`, hybrid direct-low gap `+0.875%`.
- ITM put: hybrid direct rel. err. `0.362%`, hybrid low rel. err. `0.523%`, benchmark direct-low gap `-0.066%`, hybrid direct-low gap `+0.822%`.
- OTM put: hybrid direct rel. err. `0.262%`, hybrid low rel. err. `0.998%`, benchmark direct-low gap `-0.269%`, hybrid direct-low gap `+0.991%`.

Files used:
- `bgk_r03_comparison_table.csv`

## BGK `r=0`, `T=2`

This family uses the BGK model block with `GDMR_R=0.0` and `GDMR_MATURITY=2.0`.

### Results

| Scenario | `S0` | `K` | `T` | Benchmark direct | Benchmark direct SE | Benchmark low | Benchmark low SE | Hybrid direct | Hybrid direct SE | Hybrid low | Hybrid low SE | Hybrid direct rel. err. | Hybrid low rel. err. | Benchmark direct-low gap | Hybrid direct-low gap |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ATM | `100` | `100` | `2` | `15.537393` | `0.020775` | `15.506461` | `0.020762` | `15.467526` | `0.016108` | `15.621656` | `0.143677` | `0.450%` | `0.743%` | `-0.199%` | `+0.996%` |
| ITM put | `100` | `110` | `2` | `20.812594` | `0.023205` | `20.791793` | `0.023188` | `20.796618` | `0.019759` | `20.980861` | `0.164665` | `0.077%` | `0.909%` | `-0.100%` | `+0.886%` |
| OTM put | `100` | `90` | `2` | `11.200789` | `0.017856` | `11.170787` | `0.017829` | `11.160237` | `0.012533` | `11.270917` | `0.120877` | `0.362%` | `0.896%` | `-0.268%` | `+0.992%` |

Observations:
- ATM: hybrid direct rel. err. `0.450%`, hybrid low rel. err. `0.743%`, benchmark direct-low gap `-0.199%`, hybrid direct-low gap `+0.996%`.
- ITM put: hybrid direct rel. err. `0.077%`, hybrid low rel. err. `0.909%`, benchmark direct-low gap `-0.100%`, hybrid direct-low gap `+0.886%`.
- OTM put: hybrid direct rel. err. `0.362%`, hybrid low rel. err. `0.896%`, benchmark direct-low gap `-0.268%`, hybrid direct-low gap `+0.992%`.

Files used:
- `bgk_r00_t2_comparison_table.csv`

## BGK `r=0`, `T=1`, `delta1=delta2=0.5`

This family uses the BGK model block with `GDMR_R=0.0`, `GDMR_MATURITY=1.0`, and equal deltas `GDMR_DELTA1=GDMR_DELTA2=0.5`.

### Results

| Scenario | `S0` | `K` | `T` | Benchmark direct | Benchmark direct SE | Benchmark low | Benchmark low SE | Hybrid direct | Hybrid direct SE | Hybrid low | Hybrid low SE | Hybrid direct rel. err. | Hybrid low rel. err. | Benchmark direct-low gap | Hybrid direct-low gap |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ATM | `100` | `100` | `1` | `10.548060` | `0.018176` | `10.519125` | `0.018145` | `10.484748` | `0.013958` | `10.544421` | `0.125869` | `0.600%` | `0.240%` | `-0.274%` | `+0.569%` |
| ITM put | `100` | `110` | `1` | `14.719728` | `0.019787` | `14.691320` | `0.019752` | `15.035798` | `0.018057` | `14.798167` | `0.144063` | `2.147%` | `0.727%` | `-0.193%` | `-1.580%` |
| OTM put | `100` | `90` | `1` | `7.512186` | `0.015707` | `7.496058` | `0.015683` | `7.415154` | `0.010424` | `7.554493` | `0.105602` | `1.292%` | `0.780%` | `-0.215%` | `+1.879%` |

Observations:
- ATM: hybrid direct rel. err. `0.600%`, hybrid low rel. err. `0.240%`, benchmark direct-low gap `-0.274%`, hybrid direct-low gap `+0.569%`.
- ITM put: hybrid direct rel. err. `2.147%`, hybrid low rel. err. `0.727%`, benchmark direct-low gap `-0.193%`, hybrid direct-low gap `-1.580%`.
- OTM put: hybrid direct rel. err. `1.292%`, hybrid low rel. err. `0.780%`, benchmark direct-low gap `-0.215%`, hybrid direct-low gap `+1.879%`.

Files used:
- `bgk_r00_t1_delta05_comparison_table.csv`
