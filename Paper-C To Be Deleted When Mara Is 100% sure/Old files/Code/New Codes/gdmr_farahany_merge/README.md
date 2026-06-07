# gDMR Farahany Merge

This folder exists to merge two different strengths that already exist elsewhere in the repo:

- the repo's current "normal/original" gDMR LSMC benchmark branch
- the Farahany-leaning FST/FFT gDMR hybrid branch

## Why this folder exists

You were right about the big picture: both branches still price Bermudan options under the gDMR model.

So the difference is **not**:

- model family
- payoff style
- Bermudan exercise setting

The difference is the **numerical method** used to reach that price.

## What is different between the branches

### Same problem

Both branches do all of the following:

- price a Bermudan put
- use the gDMR model
- work under the same basic parameter block

### Different numerical method

The current repo manuscript branch:

- uses the repo benchmark LSMC logic
- uses the older Gauss-Hermite-style hybrid script in `gdmr_standalone`
- uses an out-of-sample full-path rollout for the hybrid low estimator

The `gdmr_fst_swap_scripts` branch:

- keeps the hybrid on gDMR Bermudan pricing
- replaces the conditional solver with an FST/FFT method
- keeps the hybrid low estimator hybrid by simulating fresh volatility paths only
- also changes the plain-LSMC comparison file inside that branch

That last point is the key reason a merge folder is useful:

- you want the **repo benchmark LSMC** to remain the headline benchmark
- you also want the **Farahany-style FST hybrid**

This folder gives you exactly that combination.

## Files in this folder

- `run_gdmr_benchmark_put.py`
  Wrapper around the repo benchmark logic, with a Windows-safe cleanup patch.
- `run_gdmr_hybrid_put.py`
  Wrapper around the Farahany-style FST hybrid branch.
- `compare_gdmr_put_prices.py`
  Compares the repo LSMC benchmark against the FST hybrid, using `LSMC direct` as the headline reference.

## What this folder is for

Use this folder when you want:

- the manuscript/repo benchmark definition to stay fixed
- the hybrid side to move closer to Farahany
- one clean branch where "same product/model" and "same numerical benchmark" are no longer mixed across folders
