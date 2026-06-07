# gDMR code explanation

This note explains the standalone Bermudan put code in `gdmr_standalone` for the generalized Gatheral double mean-reverting (gDMR) model.

## Model

Under the risk-neutral measure $Q$, the code uses

$$
dS_t = r S_t\,dt + S_t \sqrt{v_t}\,dW_t^{(1)},
$$
$$
dv_t = \kappa_1 (v'_t - v_t)\,dt + \xi_1 v_t^{\delta_1}\,dW_t^{(2)},
$$
$$
dv'_t = \kappa_2 (\theta - v'_t)\,dt + \xi_2 (v'_t)^{\delta_2}\,dW_t^{(3)}.
$$

The Bermudan put payoff is

$$
h(s) = (K-s)^+.
$$

The option can be exercised on a Bermudan grid

$$
0 = t_0 < t_1 < \cdots < t_{N_{\mathrm{ex}}} = T.
$$

## Method 1: LSMC

The Monte Carlo file simulates the full state $(S_{t_n}, v_{t_n}, v'_{t_n})$ on the Bermudan dates.

At each exercise date, it regresses the discounted future cashflow on a polynomial state basis built from

$$
\frac{S}{K}, \qquad \frac{v}{v_0}, \qquad \frac{v'}{v'_0}, \qquad \frac{h(S)}{K}.
$$

The code uses linear, quadratic, cubic, and mixed terms. If $x$ is the basis row and $\beta_n$ is the fitted coefficient vector, then the continuation value is approximated by

$$
\widehat C_n \approx x \cdot \beta_n.
$$

The direct estimator is the average discounted payoff obtained from the backward Longstaff-Schwartz exercise rule.

The low estimator uses the fitted continuation rule on an independent simulation and computes

$$
\widehat V_{\mathrm{low}} = \frac{1}{N}\sum_{j=1}^{N} e^{-r\tau_j} h(S_{\tau_j}^{(j)}),
$$

where $\tau_j$ is the stopping time induced by the fitted policy.

### Ridge regression used in the code

If $X$ is the design matrix and $y$ is the regression target, the code uses

$$
\hat\beta = \arg\min_{\beta}\left(\|X\beta-y\|_2^2 + \lambda \|\beta\|_2^2\right),
$$

with solution

$$
\hat\beta = (X^\top X + \lambda I)^{-1} X^\top y.
$$

If the linear system is singular, the code falls back to least squares.

## Method 2: Hybrid LSMC-PDE

The hybrid file simulates only the volatility factors $(v_t, v'_t)$ on each Bermudan interval.

For each path $j$ and each interval $[t_n, t_{n+1}]$, it computes the pathwise statistics

$$
A_n^j = \int_{t_n}^{t_{n+1}}\left(r-\tfrac12 v_s^j\right)ds,
$$
$$
B_n^j = \sigma_\perp^2 \int_{t_n}^{t_{n+1}} v_s^j\,ds,
$$
$$
Z_n^j = \int_{t_n}^{t_{n+1}} \sqrt{v_s^j}\left(\beta_2\,dW_s^{(2),j}+\beta_3\,dW_s^{(3),j}\right).
$$

Then, on the asset grid $s_1,\dots,s_{N_S}$, it computes the pre-surface

$$
\widehat C_n^j(s_i)
= e^{-r\Delta t_n}
\mathbb E\!\left[
\widehat V_{n+1}(S_{t_{n+1}}, v_{t_{n+1}}^j, (v'_{t_{n+1}})^j)
\mid S_{t_n}=s_i,\; (v^j,(v')^j)
\right].
$$

The continuation surface is approximated by regression across volatility states:

$$
\widehat C_n(s,v,v') \approx a_n(s)\cdot \phi(v,v'),
$$

where $\phi$ is a truncated polynomial basis on a compact rectangle

$$
D_v = [0,\bar v]\times[0,\bar v'].
$$

The direct estimator is built from the average first-step pre-surface at $S_0$.

The low estimator uses the fitted continuation rule on independent full paths and stops when

$$
h(S_{t_n}) \ge \widehat C_n(S_{t_n}, v_{t_n}, v'_{t_n}).
$$

## Default parameters

### Common model and option parameters

| Parameter | Value |
| --- | ---: |
| `S0` | `100` |
| `K` | `100` |
| `T` | `1` |
| `r` | `0.03` |
| `v0` | `0.04` |
| `vp0` | `0.04` |
| `kappa1` | `2.0` |
| `kappa2` | `1.0` |
| `theta` | `0.04` |
| `xi1` | `0.35` |
| `xi2` | `0.20` |
| `delta1` | `0.5` |
| `delta2` | `0.5` |
| `rho12` | `0.20` |
| `rho13` | `0.10` |
| `rho23` | `0.10` |
| `N_ex` | `100` |
| `M` | `600` |

### LSMC settings

| Parameter | Value |
| --- | ---: |
| `N` | `1000000` |
| basis degree | `3` |
| basis size | `16` |
| seed | `2026` |
| low seed | `2103` |
| $\lambda$ | `1e-10` |

### Hybrid settings

| Parameter | Value |
| --- | ---: |
| `N` | `30000` |
| `N_low` | `30000` |
| `N_S` | `181` |
| `N_hermite` | `64` |
| asset low factor | `0.35` |
| asset high factor | `3.00` |
| truncation quantile | `0.995` |
| vol basis degree | `3` |
| vol basis size | `10` |
| seed | `2026` |
| low seed | `2103` |
| $\lambda$ | `1e-10` |

## Verified result

### LSMC result

| Estimator | Price | Standard error |
| --- | ---: | ---: |
| direct | `6.384535` | `0.007943` |
| low | `6.387249` | `0.007939` |

### Hybrid result

| Estimator | Price | Standard error |
| --- | ---: | ---: |
| direct | `6.421758` | `0.000652` |
| low | `6.265070` | `0.045711` |

### Comparison

| Quantity | Value |
| --- | ---: |
| Hybrid direct relative error vs LSMC direct | `0.58%` |
| Hybrid low relative error vs LSMC direct | `1.87%` |
| Hybrid low relative error vs LSMC low | `1.91%` |
| LSMC low relative gap vs LSMC direct | `0.04%` |

These are the current default parameters in the code and they are the verified settings that put `Hybrid direct` below `1%` relative error versus `LSMC direct`.
