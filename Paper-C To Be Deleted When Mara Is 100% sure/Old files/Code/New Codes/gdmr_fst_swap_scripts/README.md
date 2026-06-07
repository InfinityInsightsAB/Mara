# gDMR FST/FFT Hybrid Prototype

This folder already satisfies the three headline requirements you care about:

- gDMR model
- Bermudan option pricing
- Farahany-style FST/FFT conditional solver on the hybrid side

So the issue is not that this folder prices the wrong product. The issue is that it is not yet the same **numerical branch** as the current repo/manuscript gDMR setup.

## What this folder already does

- `run_gdmr_hybrid_put.py` uses an FST/FFT conditional solver on the log-price grid.
- Its hybrid low estimator remains hybrid: it simulates fresh volatility paths and recursively re-solves the conditional one-step problem.
- That is the main reason this folder is the most Farahany-like hybrid branch in the repo right now.

## Why it still differs from the current manuscript branch

The difference is not the model or payoff. Both branches still price a Bermudan put under gDMR. The difference is the **algorithmic internals**:

- the plain-LSMC benchmark implementation is different
- the hybrid low-estimator construction is different
- this folder is a solver/algorithm prototype, not yet the manuscript-merge branch

More concretely:

- the repo benchmark branch uses the `Code/gdmr_standalone` LSMC benchmark
- this folder also contains its own LSMC file, but that LSMC is a different implementation
- on the strong benchmark block (`1,000,000` training and low paths, `100` exercise dates, `600` Euler steps), the repo LSMC and this folder's LSMC are **not** numerically identical

Diagnostic comparison at that strong block:

| LSMC branch | Direct | Low |
| --- | ---: | ---: |
| Repo benchmark (`Code/gdmr_standalone`) | `6.294204` | `6.309298` |
| This folder's LSMC | `6.399922` | `6.403215` |

Relative difference:

- direct: `1.68%`
- low: `1.49%`

That is why "use normal/original LSMC as benchmark" still requires a design choice: there are two different plain-LSMC paths in the repo.

## Role of this folder

Treat this folder as:

- the Farahany-leaning hybrid prototype
- the place to tune the FST/FFT hybrid against the repo benchmark
- not yet the final merged manuscript branch

The detailed tuning results are recorded in `tuning_results.md`.
