# Code Algorithm vs `main.pdf` Algorithm

This note compares:

- the implemented code algorithm in `Code/New Codes/gdmr_fst_swap_scripts/run_gdmr_hybrid_put.py`
- the manuscript algorithm in `Manuscript/main.pdf`

The manuscript is the primary source throughout. Page anchors follow the current compiled manuscript mapping in `Manuscript/main.aux`:

- `main.pdf`, Section `5`, page `4`: `Conditional PDE representation`
- `main.pdf`, Section `7`, page `7`: `A hybrid LSMC-PDE methodology for the gDMR model`

For precise manuscript anchoring, this note also uses:

- `Manuscript/main.tex:300-340`
- `Manuscript/main.tex:545-563`
- `Manuscript/main.tex:575-648`

The SIAM paper is cited only where `main.pdf` is intentionally higher level, mainly to make the FST link explicit.

## Manuscript algorithm

1. Choose a Bermudan exercise grid `\pi = {0=t_0<...<t_M=T}`, an asset grid `\mathscr S = {s_1,...,s_{N_S}}`, and a truncated volatility-domain basis `\phi` so that continuation values are approximated by `c_n(s,v,v') \approx a_n(s) \cdot \phi(v,v')`.  
   Anchors: `main.pdf` p.`7`, Sec.`7`; `main.tex:583-597`.

2. Simulate autonomous volatility path segments `[(v_t^j,(v')_t^j)]_{t_n}^{t_{n+1}}` for each Monte Carlo sample. The methodology is explicitly one-way coupled: volatility evolves independently of the current asset level.  
   Anchors: `main.pdf` p.`7`, Sec.`7`; `main.tex:577-581`, `main.tex:601-605`.

3. Reduce each one-step continuation problem to a one-dimensional conditional problem in the asset/log-price direction by orthogonalizing the asset Brownian motion against the volatility drivers. The manuscript introduces the projection vector `beta = Sigma_{23}^{-1}(rho12, rho13)^T` for this reduction.  
   Anchors: `main.pdf` p.`4`, Sec.`5`; `main.tex:300-340`.

4. For each simulated volatility-path segment and each asset-grid point, compute the pathwise conditional continuation value, called the pre-surface,
   `\widehat C_n^j(s_i) = e^{-r \Delta t_n} E[\widehat V_{n+1} | S_{t_n}=s_i, [(v^j,(v')^j)]_{t_n}^{t_{n+1}}]`.  
   Anchors: `main.pdf` p.`7`, Sec.`7`; `main.tex:606-618`.

5. At each fixed asset-grid point `s_i`, regress the pre-surface values across the volatility states at time `t_n` to obtain the coefficient vector `a_n^N(s_i)`, then form the completed continuation surface
   `\widehat C_n^N(s_i,v,v') = a_n^N(s_i) \cdot \phi(v,v')`.  
   Anchors: `main.pdf` p.`7`, Sec.`7`; `main.tex:620-629`.

6. Apply the Bermudan backward recursion
   `\widehat V_n^N(s_i,v,v') = max{ h_n(s_i), \widehat C_n^N(s_i,v,v') }`
   and continue backward for `n = M-1, ..., 1`.  
   Anchors: `main.pdf` p.`7`, Sec.`7`; `main.tex:630-634`.

7. At time zero, estimate the continuation value by averaging the first-step pre-surface values and define the direct estimator by taking the maximum of immediate exercise and that averaged continuation value.  
   Anchors: `main.pdf` p.`7`, Sec.`7`; `main.tex:636-647`.

8. Impose truncation and compact-support conditions so the regression problem is well defined, and use the fact that the conditional expectation depends on the volatility-path segment only through a finite-dimensional statistic. This is the convergence alignment used to invoke the Farahany et al. theorem.  
   Anchors: `main.tex:545-563`; see also `main.pdf` p.`7`, Sec.`7`.

## Code algorithm

1. Set model parameters, Bermudan/time grids, asset-grid size, truncation quantile, and FFT controls from environment variables, then build the exercise-date schedule and interval structure.  
   Code: `run_gdmr_hybrid_put.py:63-100`.

2. Compute the projection coefficients `beta2`, `beta3`, and the residual variance term `sigma_perp_sq` used to separate the asset move into a volatility-path-dependent shift plus an independent Gaussian variance term.  
   Code: `run_gdmr_hybrid_put.py:111-118`.

3. Simulate only the volatility factors and accumulate the per-step path statistics `a_stats`, `b_stats`, and `z_stats` that parameterize the one-step conditional expectation for each Bermudan interval.  
   Code: `run_gdmr_hybrid_put.py:172-228`.

4. Build the numerical truncation rectangle using volatility quantiles and build the log-spaced asset grid on which the conditional solver runs.  
   Code: `run_gdmr_hybrid_put.py:232-242`.

5. Evaluate the one-step conditional expectation with `fst_conditional_expectation_batch`, which applies a padded FFT convolution on the log-asset grid, with a direct interpolation fallback for tiny variances.  
   Code: `run_gdmr_hybrid_put.py:284-370`.

6. Run the backward hybrid recursion: for each step, compute the pre-surface, regress it across volatility states using `vol_basis` and `ridge_regression_all`, then apply `max(payoff, continuation)` to get the next value surface.  
   Code: `run_gdmr_hybrid_put.py:376-415`.

7. Build the direct estimator from the averaged first-step pre-surface evaluated at `S0`, then compare it with immediate exercise.  
   Code: `run_gdmr_hybrid_put.py:417-428`.

8. Build the hybrid low estimator from fresh volatility paths only, recursively recomputing one-step conditional expectations under the fitted policy and excluding time-zero exercise.  
   Code: `run_gdmr_hybrid_put.py:433-479`.

## Exact connections

| Code block | Code location | Manuscript location | Connection | Status |
| --- | --- | --- | --- | --- |
| `projection_coefficients` | `run_gdmr_hybrid_put.py:111-118` | `main.pdf` p.`4`, Sec.`5`; `main.tex:322-340` | The code implements the manuscript's orthogonalization step by converting the correlation structure into projection coefficients `beta2`, `beta3` used in the conditional one-dimensional representation. | `Implementation detail of manuscript step` |
| `simulate_volatility_statistics` | `run_gdmr_hybrid_put.py:172-228` | `main.pdf` p.`4`, Sec.`5`; `main.pdf` p.`7`, Sec.`7`; `main.tex:301-307`, `main.tex:556-563`, `main.tex:601-618` | The code stores per-interval path statistics `a_stats`, `b_stats`, and `z_stats`, which are the concrete numerical form of the finite-dimensional pathwise information the manuscript says the hybrid step depends on. | `Implementation detail of manuscript step` |
| `fst_conditional_expectation_batch` | `run_gdmr_hybrid_put.py:305-370` | `main.pdf` p.`4`, Sec.`5`; `main.pdf` p.`7`, Sec.`7`; `main.tex:305-307`, `main.tex:617-618` | The manuscript says the one-step continuation reduces to a one-dimensional conditional PDE in log-space; this code block is the concrete numerical solver for that step. | `Implementation detail of manuscript step` |
| `vol_basis` + regression | `run_gdmr_hybrid_put.py:122-168`, `run_gdmr_hybrid_put.py:410-414` | `main.pdf` p.`7`, Sec.`7`; `main.tex:592-596`, `main.tex:620-629`, `main.tex:545-546` | The code implements the manuscript's truncated volatility basis and least-squares regression across volatility states to obtain the completed continuation surface. | `Direct match` |
| backward `max(payoff, continuation)` | `run_gdmr_hybrid_put.py:414-415` | `main.pdf` p.`7`, Sec.`7`; `main.tex:630-634` | This is the manuscript's Bermudan recursion written directly in code. | `Direct match` |
| direct estimator block | `run_gdmr_hybrid_put.py:417-428` | `main.pdf` p.`7`, Sec.`7`; `main.tex:636-647` | The code averages the first-step pre-surface at `S0` and then compares it with immediate exercise, exactly matching the manuscript direct-estimator construction. | `Direct match` |
| low estimator block | `run_gdmr_hybrid_put.py:433-479` | `main.pdf` p.`7`, Sec.`7`; `main.tex:636-648` | The manuscript flags direct and low time-zero estimators at a high level; the code specializes that into a recursive fresh-volatility-path policy-evaluation routine. | `Code-specific specialization` |

## Where code is more specific than `main.pdf`

- Padded FFT implementation details: the manuscript says "solve a one-dimensional conditional PDE in log-space," but it does not spell out constant-edge padding, FFT-array sizing, or the interpolation fallback for tiny variances. Those details live in `run_gdmr_hybrid_put.py:284-370`. The supporting FST-specific anchor is `_tmp_paper.txt`, p.`208`, Sec.`2.4.3`.

- Batch FFT execution: the manuscript does not specify batched execution over path blocks. The code does this explicitly with `batch_size` and chunked FFTs in `run_gdmr_hybrid_put.py:337-360`.

- Exact compact-support basis monomials: the manuscript says to choose basis functions `\phi` on a truncated volatility domain, but the exact basis used in code is the polynomial feature set in `run_gdmr_hybrid_put.py:122-144`.

- Quantile-based truncation caps: the manuscript imposes truncation and compact-support conditions, but it does not prescribe quantile-based caps. The code turns that requirement into `v_cap` and `vp_cap` via `run_gdmr_hybrid_put.py:232-235`.

- Low-estimator recursion mechanics: `main.pdf` is higher level about the low estimator, while the code makes the recursion explicit in `run_gdmr_hybrid_put.py:441-479`. The closest algorithmic support is `_tmp_paper.txt`, p.`236`, `Algorithm 2`, with `Algorithm 1` on the same page for the direct-estimator counterpart.

## Bottom line

- The overall structure is the same in both places: pre-surface first, regression across volatility states second, Bermudan max recursion third, and a direct estimator built from the first-step pre-surface average.
- The code is a faithful gDMR specialization of the manuscript's hybrid LSMC-PDE methodology, especially in its use of one-way-coupled volatility simulation, pathwise conditional continuation values, and completed continuation surfaces.
- The code is more specific than `main.pdf` about how the one-step conditional PDE is solved numerically; the padded FST/FFT machinery comes from supporting paper detail rather than explicit manuscript prose alone.
- The volatility truncation logic in code is a numerical realization of the manuscript's compact-support truncation requirement, not a model change.
- Therefore tuning `GDMR_HYBRID_VOL_QUANTILE` changes the numerical truncation rectangle used by the regression basis, not the product, not the gDMR model, and not the hybrid algorithm family described in the manuscript.
