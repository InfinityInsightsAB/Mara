# Results and improvements for `Code/my_setup`

This note records what was improved in the standalone gDMR setup and what results were obtained after tuning.

## What changed

### Monte Carlo / LSMC

- increased the default reference run to `1000000` paths and `600` Euler steps
- kept the Bermudan grid at `100` exercise dates
- upgraded the regression basis to a degree-3 paper-style family
- kept both `direct` and `low` estimates
- fixed the Windows memmap cleanup issue so the script and comparison now run cleanly

### Hybrid LSMC-PDE

- kept the article-style pathwise hybrid structure
- used a degree-3 volatility basis in `(v, v')`
- added manuscript-style truncation on a compact volatility rectangle `D_v`
- tuned the default hybrid configuration to:
  - `20000` volatility paths
  - `20000` low paths
  - `161` asset grid points
  - `48` Hermite nodes
  - asset-grid factors `0.35` to `3.00`
- kept the hybrid `direct` estimate based on the first-step pre-surface average
- kept the hybrid `low` estimate as an independent out-of-sample policy rollout

### Comparison

- `compare_put_prices.py` now uses `LSMC direct` as the headline reference
- it prints:
  - hybrid direct relative error vs `LSMC direct`
  - hybrid low relative error vs `LSMC direct`
  - hybrid low relative error vs `LSMC low`
  - LSMC low relative gap vs `LSMC direct`
- it saves a cleaner SVG with:
  - one point for each estimator
  - standard-error bars
  - a horizontal `LSMC direct` reference line
  - a pass/fail box for the `2%` direct-error target

## Tuning path

The large LSMC reference run was:

- LSMC direct = `6.384535`
- LSMC low = `6.387249`
- LSMC direct error = `0.007943`
- LSMC low error = `0.007939`

Hybrid runs during tuning:

| Run | Key settings | Hybrid direct | Hybrid low | Direct rel. error vs LSMC direct |
| --- | --- | ---: | ---: | ---: |
| Tier 1 | `10000` paths, `121` grid, `48` nodes, wide grid | `7.335311` | `6.621170` | `14.89%` |
| Tier 2 | `20000` paths, `161` grid, `48` nodes, wide grid | `6.987310` | `6.511937` | `9.44%` |
| Tier 3 | `40000` paths, `201` grid, `64` nodes, wide grid | `6.804899` | `6.424076` | `6.58%` |
| Truncated Tier 2 | `20000` paths, `161` grid, `48` nodes, truncation added, wide grid | `6.756928` | `6.281426` | `5.84%` |
| Final default | `20000` paths, `161` grid, `48` nodes, truncation + tighter grid | `6.486941` | `6.279662` | `1.60%` |

## Final result

The final default standalone comparison gives:

- LSMC direct = `6.384535`
- LSMC low = `6.387249`
- Hybrid direct = `6.486941`
- Hybrid low = `6.279662`
- Hybrid direct relative error vs LSMC direct = `1.60%`
- Hybrid low relative error vs LSMC direct = `1.64%`
- Hybrid low relative error vs LSMC low = `1.68%`
- LSMC low relative gap vs LSMC direct = `0.04%`

## Takeaway

The main improvements that mattered were:

1. strengthening the Monte Carlo reference run
2. using a richer paper-style basis
3. adding manuscript-style volatility truncation in the hybrid regression
4. tightening the hybrid asset grid around the strike

The final `my_setup` default now gives close prices for the two methods and meets the `2%` direct-error target.
