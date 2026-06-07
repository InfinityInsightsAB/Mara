# gDMR FST Algorithm And Provenance Note

## Important note about `mail.pdf`

There is no file literally named `mail.pdf` anywhere under `C:\MDU PhD\Paper C`.

So for the provenance below, I used the closest source files that are actually present in the workspace:

1. `Scientific Papers/Mixing LSMC and PDE Methods to Price Bermudan Options.pdf`
2. `_tmp_paper.txt`
   This is an extracted text version of the same SIAM paper and includes visible page markers.
3. `Manuscript/main.tex`
   This is the gDMR-specific adaptation already written for this repo.

## Exact source locations

| Source | Exact location | What is there | Why it matters here |
| --- | --- | --- | --- |
| Farahany-Jackson-Jaimungal paper | `_tmp_paper.txt`, page `204-205`, section `2.3` | Hybrid algorithm overview: pre-surface, regression across volatility, direct estimator, lower estimator | This is the main algorithm skeleton used by this folder |
| Same paper | `_tmp_paper.txt`, page `208`, section `2.4.3` | FST recursion `u_n = FFT^{-1}[FFT[g_{n+1}] exp(Psi_{n,n+1})]` | This is the source of the FST/FFT conditional solver idea |
| Same paper | `_tmp_paper.txt`, page `236`, `Algorithm 1` | Exercise-boundary / direct-estimator pseudocode | This matches the backward direct-estimator workflow |
| Same paper | `_tmp_paper.txt`, page `236`, `Algorithm 2` | Lower-estimator pseudocode with fresh volatility paths and PDE recomputation | This matches the hybrid low-estimator logic in this folder |
| gDMR manuscript | `Manuscript/main.tex:575-648` | gDMR methodology section: pre-surface, regression, completed surface, Bermudan recursion, direct estimator | This is the gDMR-specific restatement of the hybrid method |
| gDMR manuscript | `Manuscript/main.tex:300-340` | One-step conditional PDE setup and orthogonalization | This is the gDMR-specific justification for reducing to a one-dimensional conditional problem |
| gDMR manuscript | `Manuscript/main.tex:545-563` | Truncation + convergence alignment with Farahany et al. | This explains why the compact-support/truncation choice is a legitimate numerical lever |

## The exact algorithm used in `gdmr_fst_swap_scripts`

Below is the implementation-to-source mapping for `run_gdmr_hybrid_put.py`.

### 1. Bermudan setup and one-way-coupled volatility simulation

Code:

- `run_gdmr_hybrid_put.py:63-100`
- `run_gdmr_hybrid_put.py:172-228`

Source:

- `Manuscript/main.tex:575-581`
- `Manuscript/main.tex:601-618`

Meaning:

- The code simulates only the volatility factors pathwise on each Bermudan interval.
- For each interval it stores the path statistics needed to evaluate the one-step conditional expectation.

### 2. Orthogonalization / projection coefficients

Code:

- `run_gdmr_hybrid_put.py:111-118`
- `run_gdmr_hybrid_put.py:210-212`

Source:

- `Manuscript/main.tex:322-340`

Meaning:

- The manuscript derives coefficients `beta_2`, `beta_3` from the correlation projection.
- The code uses those coefficients together with `sigma_perp_sq` to split the asset move into:
  - a volatility-path-dependent shift term
  - an independent Gaussian variance term

### 3. Pre-surface construction

Code:

- `run_gdmr_hybrid_put.py:394-408`

Source:

- `_tmp_paper.txt`, page `204-205`, section `2.3.1`
- `Manuscript/main.tex:606-618`

Meaning:

- For each volatility path and each Bermudan step, the code computes the conditional continuation values over the full asset grid.
- This is exactly the "pre-surface" idea in the paper and manuscript.

### 4. FST / FFT conditional solver

Code:

- `run_gdmr_hybrid_put.py:284-370`

Source:

- `_tmp_paper.txt`, page `208`, section `2.4.3`

Meaning:

- The paper states the conditional PDE Fourier recursion in FST form.
- This folder implements that idea directly as a padded FFT convolution on the log-asset grid.
- This is the main reason this folder is the most Farahany-like hybrid branch in the repo.

### 5. Regression across volatility states

Code:

- `run_gdmr_hybrid_put.py:122-168`
- `run_gdmr_hybrid_put.py:410-414`

Source:

- `_tmp_paper.txt`, page `204-205`, section `2.3.2`
- `Manuscript/main.tex:620-633`

Meaning:

- The code regresses the pre-surface values across volatility states using a compact-support polynomial basis.
- The output is a completed continuation surface over volatility space.

### 6. Bermudan backward recursion

Code:

- `run_gdmr_hybrid_put.py:414-415`

Source:

- `_tmp_paper.txt`, page `204-205`, section `2.3.3`
- `Manuscript/main.tex:630-634`

Meaning:

- After regression, the code applies the Bermudan max operator:
  `V_n = max(payoff, continuation)`.

### 7. Direct estimator at time zero

Code:

- `run_gdmr_hybrid_put.py:417-428`

Source:

- `_tmp_paper.txt`, page `205`, section `2.3.4`
- `_tmp_paper.txt`, page `236`, `Algorithm 1`
- `Manuscript/main.tex:636-647`

Meaning:

- The direct estimator is the average first-step pre-surface at `S0`, then compared with immediate exercise.
- That is exactly the paper's direct-estimator construction.

### 8. Hybrid low estimator

Code:

- `run_gdmr_hybrid_put.py:433-479`

Source:

- `_tmp_paper.txt`, page `205`, section `2.3.5`
- `_tmp_paper.txt`, page `236`, `Algorithm 2`

Meaning:

- The low estimator uses fresh independent volatility paths only.
- Along those paths, the code recomputes one-step conditional expectations recursively and applies the fitted continuation-vs-payoff decision.
- Time-zero exercise is intentionally excluded, which is consistent with the policy-evaluation construction used here.

## What is exact, and what is adapted

### Exact in spirit

- Pre-surface first, regression second.
- Regression across volatility states, not across the full `(S, v, v')` state.
- Direct estimator from the first-step pre-surface average.
- Low estimator from fresh volatility-path simulation with recursive conditional solves.
- FST/FFT conditional expectation machinery.

### Adapted to this repo

- The paper is written for a general stochastic-volatility setting; this repo specializes it to the one-asset gDMR model.
- The paper writes the conditional step as a PDE/Fourier problem; this code implements the one-dimensional step as a padded FFT convolution on a log-price grid.
- The volatility basis and truncation rectangle are repo choices consistent with the manuscript's compact-support/truncation setup.

## Why `VOL_QUANTILE` mattered in tuning

The paper/manuscript framework requires compact-support truncation for the volatility basis.
In this code that truncation is implemented numerically by

- `run_gdmr_hybrid_put.py:232-235`
- `run_gdmr_hybrid_put.py:495`

So changing `GDMR_HYBRID_VOL_QUANTILE` does not change the product or the hybrid algorithm family.
It changes the numerical truncation rectangle used by the volatility basis.

That is why tuning `VOL_QUANTILE` from `0.995` to `0.997` was a defensible numerical adjustment rather than a model change.
