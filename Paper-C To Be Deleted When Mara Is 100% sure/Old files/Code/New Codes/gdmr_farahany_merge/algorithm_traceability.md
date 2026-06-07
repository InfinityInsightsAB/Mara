# Algorithm Traceability For `gdmr_farahany_merge`

This note explains the exact algorithm used in the merged folder, where each
piece comes from, and why both `Manuscript/main.pdf` and Farahany's paper are
needed to understand the implementation.

## What The Merged Folder Actually Is

The merged folder does not invent a new product or model. It combines:

- the repo benchmark branch for the plain LSMC reference
- the Farahany-style FST/FFT hybrid branch for the conditional solver

So all branches still price a Bermudan put under the gDMR model. What changes
across folders is the numerical method, not the product definition.

## File-Origin Map

| File in this folder | Role | Origin |
| --- | --- | --- |
| `run_gdmr_benchmark_put.py` | Windows-safe benchmark entrypoint | wrapper around `Code/gdmr_standalone/run_gdmr_benchmark_put.py` |
| `run_gdmr_hybrid_put.py` | merged-folder hybrid entrypoint | wrapper around `Code/New Codes/gdmr_fst_swap_scripts/run_gdmr_hybrid_put.py` |
| `compare_gdmr_put_prices.py` | merged-folder benchmark-vs-hybrid comparison | local compare logic for this merged workflow |

The benchmark wrapper changes only cleanup behavior on Windows. The hybrid
wrapper does not change the FST hybrid logic; it forwards execution to the FST
branch.

## Exact Algorithm Used In The Merged Folder

The executable hybrid algorithm lives in
`Code/New Codes/gdmr_fst_swap_scripts/run_gdmr_hybrid_put.py`. In merged-folder
terms, the algorithm is:

1. Fix the gDMR model under risk-neutral dynamics, with autonomous volatility
   subsystem `(v, v')` and one-way coupling into the asset.
   Source:
   `Manuscript/main.pdf`, section `Stochastic basis and generalized gDMR dynamics`.
   Local traceability:
   `Manuscript/main.tex`, lines `177-199`.

2. Use the one-way coupling to simulate volatility paths independently of the
   asset path. In code this is the role of `simulate_volatility_statistics`,
   which stores the volatility paths and the conditional Gaussian statistics
   needed later for the asset expectation.
   Code anchor:
   `Code/New Codes/gdmr_fst_swap_scripts/run_gdmr_hybrid_put.py`, lines `172-228`.
   Source logic:
   manuscript one-way coupling plus Farahany's conditional decomposition.

3. Build a one-dimensional asset grid in log-space and initialize terminal
   Bermudan values with the payoff.
   Source:
   `Manuscript/main.pdf`, subsection `Discretization`.
   Local traceability:
   `Manuscript/main.tex`, lines `585-597`.
   Code anchors:
   `build_asset_grid` at lines `239-242` and terminal initialization at
   lines `378-392`.

4. For each exercise date, compute a pathwise pre-surface over the asset grid by
   conditioning on a sampled volatility path segment and evaluating the
   conditional expectation for all asset-grid points.
   Source:
   `Manuscript/main.pdf`, subsection `Algorithm overview`.
   Local traceability:
   `Manuscript/main.tex`, lines `601-619`.
   Farahany source:
   section `2.3.1`, local traceability in `_farahany_tmp.txt`, lines `193-207`.
   Code anchors:
   `fst_conditional_expectation_batch` at lines `305-370` and its use in the
   backward induction at lines `394-408`.

5. Regress those pathwise pre-surface values across the volatility states to
   obtain a completed continuation surface over volatility space.
   Source:
   `Manuscript/main.pdf`, subsection `Algorithm overview`.
   Local traceability:
   `Manuscript/main.tex`, lines `620-629`.
   Farahany source:
   section `2.3.2`, local traceability in `_farahany_tmp.txt`, lines `208-223`.
   Code anchors:
   `vol_basis` at lines `122-144`, `ridge_regression_all` at lines `148-168`,
   and regression use at lines `410-413`.

6. Apply the Bermudan recursion by taking the maximum of immediate exercise and
   continuation value on the asset grid, then step backward in time.
   Source:
   `Manuscript/main.pdf`, subsection `Algorithm overview`.
   Local traceability:
   `Manuscript/main.tex`, lines `630-634`.
   Farahany source:
   section `2.3.3`, local traceability in `_farahany_tmp.txt`, lines `226-227`.
   Code anchor:
   line `414`.

7. At time zero, form the direct estimator by averaging the first-step
   pre-surface samples and comparing against immediate exercise.
   Source:
   `Manuscript/main.pdf`, subsection `Time-zero estimators (direct and low)`.
   Local traceability:
   `Manuscript/main.tex`, lines `638-648`.
   Farahany source:
   section `2.3.4`, local traceability in `_farahany_tmp.txt`, lines `310-323`.
   Code anchors:
   lines `417-428`.

8. Form the hybrid low estimator using fresh volatility paths only. For each
   fresh volatility path, recompute the pathwise conditional pre-surface, apply
   the previously learned continuation policy, and propagate the held/exercised
   value backward.
   Source:
   Farahany section `2.3.5`.
   Local traceability:
   `_farahany_tmp.txt`, lines `324-339` and `340-370`.
   Code anchors:
   lines `431-479`.

9. Evaluate each conditional expectation in step 4 and step 8 by solving the
   one-step conditional PDE in Fourier space with an FFT/FST recursion on the
   log-price grid.
   Source:
   Farahany sections `2.4.2` and `2.4.3`.
   Local traceability:
   `_farahany_tmp.txt`, lines `543-689`.
   Code anchors:
   lines `282-370`.

## Source Map: Manuscript Versus Farahany

| Algorithm part | `main.pdf` / `main.tex` | Farahany paper / `_farahany_tmp.txt` | Why it matters here |
| --- | --- | --- | --- |
| gDMR model and one-way coupling | `Stochastic basis and generalized gDMR dynamics`; `main.tex:177-199` | cited conceptually by manuscript | tells us why volatility can be simulated independently |
| Discretization and pre-surface idea | `A hybrid LSMC-PDE methodology for the gDMR model`; `main.tex:575-619` | sections `2.3.1` and `2.3.2`; `_farahany_tmp.txt:193-223` | gives the hybrid structure used by the merged folder |
| Regression/completed surface | `main.tex:620-633` | `_farahany_tmp.txt:208-227` | defines how pathwise pre-surfaces become a full continuation rule |
| Direct estimator | `main.tex:638-648` | `_farahany_tmp.txt:310-323` | explains why the time-zero direct estimate is usually biased high |
| Low estimator | heading exists at `main.tex:636`, but the detailed low-estimator construction is not written out before the manuscript ends | `_farahany_tmp.txt:324-370` | Farahany provides the executable hybrid lower-bound construction |
| Conditional PDE and Fourier solution | manuscript says solve a conditional PDE in log-space, but does not spell out the FST formula | `_farahany_tmp.txt:543-689` | Farahany gives the actual Fourier/PDE recursion used by the FST branch |
| Full pseudocode skeleton | manuscript gives a methodology description, not step-numbered pseudocode | Appendix A Algorithms `1` and `2`; `_farahany_tmp.txt:3615-3689` | Farahany provides the clearest end-to-end procedural structure |

## Why Both Sources Are Needed

`Manuscript/main.pdf` is the correct source for the gDMR-specific problem
statement:

- it defines the gDMR dynamics
- it explains the one-way coupling that justifies the mixed MC-PDE approach
- it states the manuscript's hybrid methodology and direct estimator in the gDMR
  setting

Farahany's paper is needed for the executable numerical details that the
manuscript does not fully spell out:

- the hybrid low-estimator recursion
- the conditional PDE written in Fourier form
- the discrete FFT/FST recursion
- the Appendix A pseudocode structure

In short:

- `main.pdf` tells us what the gDMR version of the method is trying to do
- Farahany tells us exactly how to execute the hybrid low estimator and FST
  conditional solver

## Where `main.pdf` Is Not Fully Executable By Itself

There are two especially important gaps if one tries to code directly from the
manuscript alone.

### 1. The low estimator is not fully written out

The manuscript includes the subsection heading
`Time-zero estimators (direct and low)` at `Manuscript/main.tex:636`, and it
does define the direct estimator at lines `638-648`. However, the document then
ends the methodology section without a detailed low-estimator construction.

That missing construction is exactly what Farahany section `2.3.5` supplies.

### 2. The manuscript says "solve a conditional PDE" but does not give the FST recursion

The manuscript says the pre-surface is computed by solving a one-dimensional
conditional PDE in log-space; see `Manuscript/main.tex:617-618`. That is the
right conceptual statement, but it is not yet an executable FFT recipe.

Farahany sections `2.4.2` and `2.4.3` provide the missing numerical step:

- the conditional PDE in Fourier space
- the characteristic exponent
- the FFT-based recursion `u_n = FFT^{-1}[ FFT[g_{n+1}] exp(Psi_{n,n+1}) ]`

That is the reason the merged folder uses the FST branch as its hybrid engine.

## Code-Level Audit Note

From a source-guided reading of
`Code/New Codes/gdmr_fst_swap_scripts/run_gdmr_hybrid_put.py`, I did not find a
clear conceptual mismatch with the Farahany-style algorithm in the parts that
matter most:

- pathwise pre-surface construction is present
- regression across volatility state is present
- time-zero direct estimator is present
- hybrid low estimator with fresh volatility paths only is present
- FST/FFT conditional expectation is present

The main implementation-level differences from the paper are practical
numerical choices rather than obvious algorithmic contradictions:

- the code uses a two-factor volatility basis `(v, v')` because gDMR has two
  volatility states
- the regression uses ridge regularization for stability
- the FFT step uses constant-edge padding and interpolation guards
- the truncation caps and asset-domain factors are implementation parameters

So the remaining `~1.08%` gap observed in the frozen iteration should be read as
an unresolved numerical gap, not as proof of a clear source-level algorithm bug.
