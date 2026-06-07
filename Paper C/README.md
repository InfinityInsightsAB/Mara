# Paper C Reproducibility Package

This folder contains the manuscript files, the four figures used in the manuscript, the numerical data behind those figures, and the Python code used to reproduce them. All paths are relative to this `Paper C` folder, so you can copy the folder anywhere and run the same commands from inside it.

## Folder Contents

- `Code/` contains the Python files used to rerun the plain LSMC calculation, rerun the Hybrid LSMC-PDE calculation, reproduce the numerical experiments comparing the two methods, and rebuild the paper figures.
- `Raw data/` contains the CSV files used by the figures, including the plain LSMC reference values, step-sweep results, path-sweep results, and plot-ready data.
- `Figures/` contains the four PDF figures included in the manuscript.
- `Manuscript/` contains the LaTeX manuscript files and the compiled manuscript PDF.
- `requirements.txt` lists the Python packages needed to run the code.

## Python Setup

Use Python 3.10 or newer. Python 3.12 was used when this package was checked.

Open a terminal in your own copy of the `Paper C` folder. If the path contains spaces, keep the quotation marks.

Windows PowerShell:

```powershell
cd "C:\path\to\Paper C"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, run this in the same terminal and activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

macOS or Linux:

```bash
cd "/path/to/Paper C"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The `.venv` folder is created only for your machine. It does not need to be shared.

## Rebuild the Manuscript Figures

This is the simplest reproducibility check. It uses the existing CSV files in `Raw data/` and rebuilds the four PDF figures in `Figures/`. It does not recompute option prices.

Windows:

```powershell
python "Code\bgk_r02_calibrated_t1_nex12\code\build_assets.py"
```

macOS or Linux:

```bash
python "Code/bgk_r02_calibrated_t1_nex12/code/build_assets.py"
```

This should create or update:

- `Figures/step_sweep_20k_direct_relative_error.pdf`
- `Figures/step_sweep_60k_direct_relative_error.pdf`
- `Figures/path_sweep_steps48_direct_relative_error.pdf`
- `Figures/path_sweep_steps60_direct_relative_error.pdf`

The same figure-building step can also be run through:

```powershell
python "Code\bgk_r02_calibrated_t1_nex12\code\run_full_robustness.py" --mode assets
```

## Optional Numerical Reruns

The stored CSV files are enough to rebuild the figures. The commands below are only needed if you want to recompute Bermudan put prices under the Gatheral Double Mean-Reverting stochastic volatility model.

```powershell
python "Code\bgk_r02_calibrated_t1_nex12\code\run_full_robustness.py" --mode smoke
```

Runs a small check that both numerical methods can run.

```powershell
python "Code\bgk_r02_calibrated_t1_nex12\code\run_full_robustness.py" --mode benchmark
```

Recomputes the plain LSMC reference values for the five strikes. The reference calculation uses 1,200 Euler steps and 1,200,000 Monte Carlo paths.

```powershell
python "Code\bgk_r02_calibrated_t1_nex12\code\run_full_robustness.py" --mode step
```

Recomputes the step-sweep experiment. This keeps the Monte Carlo path budget fixed at 20,000 or 60,000 paths and varies the number of Euler time steps.

```powershell
python "Code\bgk_r02_calibrated_t1_nex12\code\run_full_robustness.py" --mode path
```

Recomputes the path-sweep experiment. This keeps the Euler discretization fixed at 48 or 60 steps and varies the number of Monte Carlo paths.

```powershell
python "Code\bgk_r02_calibrated_t1_nex12\code\run_full_robustness.py" --mode full
```

Runs the smoke check, the benchmark reference calculation, the step sweep, the path sweep, and the figure rebuilding step. This can take a long time because it recomputes the large Monte Carlo calculations.

Use `--force` only if you intentionally want to replace existing output files:

```powershell
python "Code\bgk_r02_calibrated_t1_nex12\code\run_full_robustness.py" --mode full --force
```

On macOS or Linux, use the same commands with `/` instead of `\` in the file paths.

## Code Files

`Code/bgk_r02_calibrated_t1_nex12/config/rerun_config.json` stores the numerical setup for this case. It gives the GDMR model parameters, strikes, seeds, Hybrid LSMC-PDE grid settings, reference run size, step-sweep grid, path-sweep grid, and smoke-test settings.

`Code/bgk_r02_calibrated_t1_nex12/code/build_assets.py` reads the CSV files in `Raw data/` and rebuilds the four PDF figures used in the manuscript. It checks that the required inputs are present, prepares plot-ready CSV files where needed, and writes the final figure files to `Figures/`.

`Code/bgk_r02_calibrated_t1_nex12/code/run_full_robustness.py` is the main script for repeating the numerical experiments. It reads the case settings, runs the plain LSMC and Hybrid LSMC-PDE scripts for the selected experiment, writes the resulting CSV files into `Raw data/`, and can call `build_assets.py` to rebuild the figures.

`Code/bgk_r02_calibrated_t1_nex12/code/lsmc_from_scratch.py` runs one plain Longstaff-Schwartz Monte Carlo calculation. It reads the model and run settings from environment variables, calls the LSMC helper code, and prints the direct and low estimates with standard errors in a machine-readable `RESULT_JSON` line.

`Code/bgk_r02_calibrated_t1_nex12/code/scratch_lsmc_helpers.py` contains the mathematical implementation of the plain LSMC method. It simulates the GDMR state variables, builds the Bermudan exercise grid, fits continuation values by regression, and computes the direct and low estimators with standard errors.

`Code/bgk_r02_calibrated_t1_nex12/code/hybrid_from_scratch.py` runs one Hybrid LSMC-PDE calculation. It reads the model and run settings, calls the hybrid helper code, and prints the direct and low estimates with standard errors in a machine-readable `RESULT_JSON` line.

`Code/bgk_r02_calibrated_t1_nex12/code/scratch_hybrid_helpers.py` contains the mathematical implementation of the Hybrid LSMC-PDE method. It simulates the volatility factors, builds the conditional asset-price grid, evaluates the conditional expectation step using Fourier methods, fits continuation values over the volatility state, and returns the hybrid direct and low estimates.

## Numerical Meaning of the Main Outputs

The benchmark CSV stores the plain LSMC reference values computed with the largest run settings. These values are used as the reference point for the relative-error plots.

The step-sweep CSVs compare plain LSMC and Hybrid LSMC-PDE estimates across different Euler time-step counts while keeping the number of simulated paths fixed.

The path-sweep CSVs compare plain LSMC and Hybrid LSMC-PDE estimates across different numbers of simulated paths while keeping the Euler time-step count fixed.

The figures plot relative errors against the stored reference values, so rebuilding the figures does not require rerunning the expensive simulations.

## Python Packages

The required packages are listed in `requirements.txt`:

```txt
numpy>=1.26
matplotlib>=3.8
```
