# Audit of `Code/New Codes`

This folder contains two candidate gDMR Bermudan-put implementations:

- `gdmr_standalone_version1`
- `gdmr_fst_swap_scripts`

This note audits both against:

- `Scientific Papers/Mixing LSMC and PDE Methods to Price Bermudan Options.pdf` as the primary reference for the hybrid algorithm
- `Manuscript/main.tex` and `Manuscript/main.pdf` as the secondary reference for the gDMR model and manuscript-style setup

## Bottom line

- There is no published Farahany gDMR benchmark table to reproduce exactly. Farahany's 2020 paper reports Heston and multidimensional Heston examples, not gDMR.
- `gdmr_standalone_version1` is not a third distinct implementation. Its three main files are byte-identical to the existing `Code/gdmr_standalone` files, confirmed by matching SHA-256 hashes.
- `gdmr_standalone_version1` is closer to the current repo's manuscript-oriented gDMR setup, but it is not the closest replica of Farahany's numerical algorithm.
- `gdmr_fst_swap_scripts` is structurally closer to Farahany on the hybrid-PDE side, because it uses an FST/FFT conditional solver and a hybrid-style low estimator. Its main weakness is that it changes the LSMC comparison baseline.
- Neither folder is a full exact Farahany replica. The main decision is which mismatch matters more:
- `version1`: closer to the repo's established gDMR setup, weaker match to Farahany's numerical hybrid machinery
- `fst_swap`: closer to Farahany's numerical hybrid machinery, weaker match to the repo's established comparison baseline

## What the references require

From Farahany et al. (2020):

- The model class must have one-way coupling, so volatility can be simulated independently of the asset.
- The hybrid algorithm is pathwise in volatility: solve a conditional PDE along each volatility path to get a pre-surface in the asset direction, then regress across volatility states.
- The paper's conditional PDE solver is Fourier space time-stepping (FST/FFT).
- The paper's low estimator stays hybrid: simulate fresh volatility paths and recompute conditional expectations by PDE recursion, instead of rolling out fresh full stock paths.
- The overall algorithm is presented as an extension of Tsitsiklis-Van Roy style regression, not as a pure Longstaff-Schwartz ITM-only benchmark.

From the gDMR manuscript:

- The gDMR state is `(S, v, v')` with autonomous volatility subsystem `(v, v')`.
- The manuscript emphasizes the same pathwise pre-surface plus regression-across-volatility structure.
- The manuscript also emphasizes truncation and compact-support basis functions on a bounded volatility rectangle.
- The current manuscript does not yet give a published numerical benchmark table for gDMR, and its methodology section spells out the direct estimator but not a detailed executable low-estimator recipe.

## Byte-identical check

`gdmr_standalone_version1` matches `Code/gdmr_standalone` exactly for the main three files:

| File | Shared SHA-256 |
| --- | --- |
| `run_gdmr_benchmark_put.py` | `1F6581208C61EBB8...` |
| `run_gdmr_hybrid_put.py` | `A9D232D4AC140A29...` |
| `compare_gdmr_put_prices.py` | `85407A3C53869FF2...` |

So `gdmr_standalone_version1` is effectively a copy of the already-established repo implementation, not an independent new branch.

## Audit by axis

| Axis | Farahany / manuscript expectation | `gdmr_standalone_version1` | `gdmr_fst_swap_scripts` | Verdict |
| --- | --- | --- | --- | --- |
| Model dynamics | gDMR with one-way coupling in `(v, v')` | Matches | Matches | Both match |
| Volatility-path pre-surface | Solve pathwise conditional expectations then regress across volatility | Matches | Matches | Both match |
| Volatility truncation and compact basis | Manuscript-style bounded basis on truncated `D_v` | Matches clearly | Matches clearly | Both match |
| PDE / conditional solver | Farahany paper uses FST/FFT | Uses Gauss-Hermite convolution on log-grid, not FST | Uses explicit FST/FFT convolution batch | `fst_swap` matches better |
| Hybrid direct estimator | Average first-step pre-surface at `S0` | Matches | Matches | Both match |
| Hybrid low estimator | Fresh volatility paths plus recursive PDE recomputation | Uses fresh full `(S, v, v')` paths and policy rollout | Uses fresh volatility paths and recursive hybrid PDE evaluation | `fst_swap` matches better |
| LSMC comparison baseline | Paper is closer to Tsitsiklis-Van Roy style than classic LS alive/ITM filtering | Uses full-state regression on all paths at each step | Uses stopped-path, alive/ITM Longstaff-Schwartz style regression | `version1` is closer here |
| Repo/manuscript continuity | Stay close to the repo's existing gDMR reference branch | Exact copy of `Code/gdmr_standalone` | Alternative branch with larger structural changes | `version1` matches better |

## What matches and what does not

### `gdmr_standalone_version1`

Matches:

- gDMR dynamics and one-way-coupled volatility structure
- manuscript-style truncated volatility basis and pathwise pre-surface regression
- direct-estimator construction from the first-step pre-surface average
- the repo's existing gDMR reference branch exactly

Does not match Farahany numerically:

- it does not use the paper's FST/FFT conditional PDE machinery
- its hybrid low estimator is not the paper's hybrid low estimator
- its benchmark side is closer to a full-state Tsitsiklis-Van Roy recursion than to the Heston benchmark script used elsewhere in the repo

Practical note:

- direct invocation of `run_gdmr_benchmark_put.py` fails on this Windows machine because `tempfile.TemporaryDirectory` tries to delete open memmap files during cleanup
- no source changes were made; the matched result was recovered through a runtime-only wrapper that suppresses the cleanup failure after the same script code finishes the pricing work

### `gdmr_fst_swap_scripts`

Matches:

- gDMR dynamics and one-way coupling
- manuscript-style truncation and volatility basis
- FST/FFT conditional expectation machinery, which is the solver family used in Farahany's paper
- hybrid low-estimator logic based on fresh volatility paths plus recursive PDE recomputation

Does not fully match Farahany or the repo baseline:

- its LSMC comparison script is not just a solver swap; it changes the baseline to a more classical Longstaff-Schwartz alive/ITM design
- this means its headline comparison is not apples-to-apples with `version1` on the LSMC side

## Main interpretation

If the question is "which branch looks most like Farahany's published hybrid algorithm," the answer is `gdmr_fst_swap_scripts`.

If the question is "which branch looks most like the repo's current manuscript-oriented gDMR implementation," the answer is `gdmr_standalone_version1`.

If the question is "which one is correct," the honest answer is:

- both contain real Farahany/manuscript ingredients
- both also contain nontrivial deviations
- correctness cannot be judged by matching a published gDMR target price, because no such Farahany table exists
- the best evidence is therefore structural fidelity plus internal numerical consistency

The matched-run evidence is summarized in `matched_run_comparison.md`, and the recommendation is distilled in `best_replica_summary.md`.
