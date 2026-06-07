# Bermudan Hybrid LSMC-PDE Project

This repository is organized to keep your manuscript, your method/model code, and a Farahany-style reference workflow clearly separated.

## Directory layout

- `Manuscript/`: LaTeX paper source (`main.tex`, `references.bib`).
- `bermudan_pricing/core/`: shared primitives for all experiments.
  - `config.py`: model/option/solver dataclasses.
  - `sim.py`: gDMR path simulation and orthogonal decomposition helpers.
  - `numerics.py`: asset grid, basis, ridge regression helper.
  - `results.py`: shared result containers.
- `bermudan_pricing/methods/hybrid/`: mixed LSMC-PDE implementation (our working method).
- `bermudan_pricing/methods/lsmc_baseline/`: ordinary LSMC baseline under the same model.
- `bermudan_pricing/reference/`: reproducibility layer that reproduces the Farahany-style workflow.
- `bermudan_pricing/experiments/`: comparison utilities (hybrid vs standard LSMC).
- `Heston` reference benchmark script under `bermudan_pricing/reference/heston_benchmark.py` to recreate Table 9/10-type outputs from the paper.
- compatibility aliases at package root:
  - `bermudan_pricing/config.py`
  - `bermudan_pricing/model.py`
  - `bermudan_pricing/pde.py`
  - `bermudan_pricing/lsmc_pde.py`

## Setup

```powershell
python -m venv .venv
. .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run demos

- Hybrid only:

```powershell
py -m bermudan_pricing.main --method hybrid
```

- Standard LSMC only:

```powershell
py -m bermudan_pricing.main --method lsmc
```

- Compare both methods with identical model/setup:

```powershell
py -m bermudan_pricing.experiments.compare_methods --paths 800 --steps 10 --nodes 14 --seed 2026
```

- Recreate the Heston paper benchmark rows (Table 9 and 10 values) with the Farahany settings:

```powershell
py -m bermudan_pricing.reference.heston_benchmark --paths 5000 --steps 12 --nodes 16 --seed 2026 --vol-degree 3 --state-degree 3
```

Options of interest for the reference workflow:

- `--v-integral-mode left|midpoint|trapezoid` controls how the variance integral over each step is approximated.
- `--low-mode average_pre|policy` chooses the Heston hybrid low estimator construction.
- `--low-paths <int>` enables a separate out-of-sample low-path run (defaults to `0`, i.e. reuse `paths`).

## Notes

- `--method compare` in `bermudan_pricing.main` will also run both methods and print a direct diff.
- `bermudan_pricing/reference/farahany_style.py` is intentionally isolated as the "recreate Farahany prices" layer for verification.
- Never modify `Hybrid_LSMC_PDE` unless the user specifically asks for changes to it; it reflects the user's writing style and is user-maintained.
- You can later extend this layout by adding:
  - more model variants under `bermudan_pricing/core` or `.../methods`,
  - experiment scripts under `bermudan_pricing/experiments`,
  - article-specific notes under `Manuscript`.
