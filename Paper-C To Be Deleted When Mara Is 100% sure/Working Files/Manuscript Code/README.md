# Manuscript Code

This folder is the manuscript-specific reproducibility workspace for the numerical-results program. It is separate from the broader project code so that the material used for the paper can be organized, audited, and regenerated without ambiguity.

## Role of This Folder

`Manuscript Code` is the canonical location for:

- manuscript-specific standalone scripts
- copied reusable benchmark and study results
- provenance notes for reused material
- local plot-data and table staging
- Python-generated manuscript figures
- reproducibility documentation for the numerical section

## Current Workflow

The current manuscript workflow is Python-first for figure generation and manuscript-local for any missing numerical source tables.

- Saved numerical results may be reused.
- Reused results are copied into `reference_values\`.
- If a required manuscript source table is missing from the saved bundle, it may be computed locally by a standalone script in this folder.
- Lightweight manuscript-specific scripts normalize those saved results into local plot-data and table assets.
- Python figure scripts regenerate publication figures from the local stored inputs.
- Overleaf consumes the exported figure assets and table snippets.

## Current Scripts

The current manuscript-code entry points are:

- `build_reused_step_sweep_assets.py`
  - stages saved benchmark and matched-path step-sweep inputs
  - writes local plot-data files
  - writes local and Overleaf-facing table assets
  - records a machine-readable manifest
- `generate_step_sweep_figures.py`
  - reads local stored plot-data files
  - regenerates the matched `20k` and `60k` publication figures in Python
  - exports `.pdf` and `.eps`
  - records a machine-readable figure manifest
- `prepare_path_sweep_sources.py`
  - stages exact saved path-sweep inputs where available
  - reuses saved `20k` and `60k` step-48 overlap points where they coincide with the path-sweep design
  - computes missing path-sweep source tables into the local manuscript workspace
  - writes per-source provenance sidecars in JSON
- `build_reused_path_sweep_assets.py`
  - normalizes the local path-sweep source bundle into plot-data and LaTeX tables
  - writes local and Overleaf-facing table assets
  - records a machine-readable path-sweep staging manifest
- `generate_path_sweep_figures.py`
  - reads local stored plot-data files
  - regenerates the fixed-step path-sweep publication figures in Python
  - exports `.pdf` and `.eps`
  - records a machine-readable figure manifest
- `run_bgk_r02_t1_delta05_nex12_experiments.py`
  - runs the case-specific numerical robustness setting `bgk_r02_t1_delta05_nex12`
  - sets `r = 0.02`, `T = 1`, `delta1 = delta2 = 0.5`, and `12` Bermudan exercise dates
  - preserves the manuscript calibrated gDMR block, five-strike contract set, direct-price reporting, and confidence-interval output
  - delegates benchmark and hybrid pricing to the flexible engines in `Working Files\Final Code\More Experiments`
  - writes benchmark, step-sweep, and path-sweep source tables into the canonical `reference_values\` layout
- `build_bgk_r02_t1_delta05_nex12_assets.py`
  - validates the complete robustness source bundle
  - writes case-prefixed plot-data, table, figure, and appendix assets
  - exports those assets into `Working Files\Manuscript Overleaf`

The Python environment requirements for the present figure pipeline are listed in:

- `requirements.txt`

## Intended Folder Layout

This folder is intended to contain manuscript-specific material only. The working structure is:

- `README.md`
  - orientation and workflow description
- `PROVENANCE.md`
  - reuse tracking and source-to-destination mapping
- `requirements.txt`
  - Python plotting dependencies for manuscript figures
- `reference_values\`
  - copied benchmark tables, summaries, reusable study inputs, and manuscript-local source tables
- `outputs\`
  - manifests and local plot-data derived from manuscript-specific scripts
- `figures\`
  - Python-generated local figure assets
- `tables\`
  - local table assets generated for manuscript use

The current path-sweep source bundle lives in:

- `reference_values\path_sweep\`
  - one standardized source table per strike and fixed-step configuration
  - one JSON sidecar per source table describing whether the table was copied, mixed, or locally computed

The `bgk_r02_t1_delta05_nex12` robustness workflow uses this command schema:

```powershell
python "Working Files\Manuscript Code\run_bgk_r02_t1_delta05_nex12_experiments.py" --mode smoke
python "Working Files\Manuscript Code\run_bgk_r02_t1_delta05_nex12_experiments.py" --mode benchmark
python "Working Files\Manuscript Code\run_bgk_r02_t1_delta05_nex12_experiments.py" --mode step
python "Working Files\Manuscript Code\run_bgk_r02_t1_delta05_nex12_experiments.py" --mode path
python "Working Files\Manuscript Code\build_bgk_r02_t1_delta05_nex12_assets.py"
```

The production benchmark uses `1200` Euler steps and `1,200,000` paths. The fixed-path step sweeps use `20,000` and `60,000` paths over steps `24,48,72,96`. The raw path-sweep source bundle uses paths `250,500,1000,2000,5000,10000,20000,40000,60000`; manuscript-facing plot-data and appendix tables report the seven-point grid `250,1000,5000,10000,20000,40000,60000`, matching the active numerical section.

## Relation to the Rest of the Project

This folder is the manuscript-specific endpoint, not the first place where earlier experiments were stored.

The primary reference source for reusable saved numerical material is:

- `C:\MDU PhD\Paper C\Experiments 26.03`

The secondary reference source for standalone-script conventions and documentation patterns is:

- `C:\MDU PhD\Paper C\Working Files\Final Code`

No result should be treated as manuscript-ready merely because it exists in those folders. Reusable material must be copied into `Manuscript Code` before manuscript use and logged in `PROVENANCE.md`.

## Local Reproducibility Standard

Reproducibility in this folder includes figure regeneration and, where required, manuscript-local regeneration of missing source tables.

- Saved CSV inputs are not the endpoint.
- Manuscript figures must be regenerated from Python code inside this folder.
- Figure scripts must consume local stored inputs from the manuscript workspace.
- Overleaf-facing figure assets are exports, not the source of truth.
- Any missing numerical source tables computed for the manuscript must also be written into this folder.

## Code Standard for This Folder

Any future code placed here must be:

- standalone
- simple to run
- reproducible
- manuscript-specific
- written without code comments

Later scripts should make their file logic transparent and should write outputs into clearly named local folders.

## Current Numerical Program

The manuscript numerical program is locked to the calibrated gDMR setting with:

- `S0 = 100`
- `v0 = 0.114`
- `v0' = 0.110`
- `r = 0`
- `T = 1`
- `12` Bermudan exercise dates
- strikes `70, 80, 90, 100, 110`

The benchmark policy is:

- plain LSMC
- `1200` Euler steps
- `1,200,000` paths
- `95%` confidence intervals

The manuscript reporting policy is:

- direct prices only
- confidence-interval information mandatory

## Reuse Policy

Reusable saved results should be preferred over unnecessary recomputation, provided that:

- the source is clearly identified
- the numerical setting matches the locked manuscript specification or can be cleanly rebased to it
- the copied result is registered in `PROVENANCE.md`
- any figure based on the result is regenerated by manuscript-specific Python code

If a required value or study is missing, it should be computed by a standalone manuscript-side script in this folder rather than approximated from partial evidence.
