# Heston paper benchmark: Bermudan put

These files are set up so you can compare against the Heston Bermudan-put results reported in Farahany, Jackson, and Jaimungal (2020).

## Paper parameter block used here

- model: Heston
- payoff: Bermudan put, `(K - S)+`
- `T = 1`
- `K = 10`
- exercise frequency `T / 12`
- `r = 0.02`
- `S0 = 10`
- `v0 = 0.15`
- `kappa = 5`
- `theta = 0.16`
- `eta = 0.9`
- `rho = 0.1`

## Paper numerical setup reflected here

### LSMC

- `N = 500000`
- `M = 1000`
- basis degree = 3
- direct and low estimates are both reported

### Hybrid standalone setup in this folder

- exercise dates = 12
- `M = 1000`
- basis degree = 3
- log-price grid range = [-3, 3]
- finest asset grid resolution = `N_S = 2^9 = 512`
- volatility paths = `N = 10000`
- low-estimator paths = `N_low = 10000`

## Published targets from the paper for the ATM Heston case

- finite-difference reference = 1.4507
- paper LSMC direct = 1.4494
- paper LSMC low = 1.4487
- paper hybrid direct = 1.4530
- paper hybrid low = 1.4529

## Important scope note

The `run_heston_paper_lsmc_put.py` file is parameter-faithful to the paper setup.
The `run_heston_paper_hybrid_put.py` file is a standalone reimplementation using the paper parameters and the finest reported grid resolution. It is designed so you can compare your run against the published targets, but it is not the authors' exact MLMC-FST code path from the article.
