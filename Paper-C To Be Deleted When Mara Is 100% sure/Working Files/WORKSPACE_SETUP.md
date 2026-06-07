# Workspace Setup

This workspace is organized so the active project lives in `Working Files`,
older material lives in `Old files`, and the reproducible Python environment
is stored at the Paper C root in `.venv`.

## Top Level

- `Working Files/`: active manuscript, package code, final standalone code, and current results
- `Old files/`: legacy code branches, archived templates, reference papers, and scratch material
- `.venv/`: root Python environment for reproducing the active code

## Active Working Layout

- `Working Files/bermudan_pricing/`: installable Python package
- `Working Files/Final Code/`: final standalone scripts and retained results
- `Working Files/Manuscript/`: main paper source and the `Hybrid_LSMC_PDE` variant
- `Working Files/Results Summary/`: current LaTeX result summaries
- `Working Files/requirements.txt`: minimal dependency input
- `Working Files/requirements-lock.txt`: exact installed package versions from the current `.venv`

## Environment

Environment location:

```powershell
C:\MDU PhD\Paper C\.venv
```

Interpreter used for this setup:

```text
Python 3.13.7
```

Create the environment from the Paper C root:

```powershell
& 'C:\Users\marak\AppData\Local\Programs\Python\Launcher\py.exe' -m venv .venv
& '.\.venv\Scripts\python.exe' -m pip install -r '.\Working Files\requirements.txt'
```

Activate it from the Paper C root:

```powershell
.\.venv\Scripts\Activate.ps1
```

Activate it from inside `Working Files`:

```powershell
..\.venv\Scripts\Activate.ps1
```

After activation, common commands from `Working Files` are:

```powershell
python -m bermudan_pricing.main --help
python .\Final Code\compare_gdmr_put_prices.py
python .\Final Code\Experiments\run_gdmr_path_sweep.py --help
```

## Notes

- `Final Code/Revised by ChatGPT Pro Extended Thinking` was preserved unchanged by name.
- The BGK reference note used by `run_gdmr_path_sweep.py` now lives in `Working Files/Final Code/Experiments/References/`.
- Safe temporary artifacts such as `__pycache__`, `*.pyc`, and LaTeX intermediate files were removed.
