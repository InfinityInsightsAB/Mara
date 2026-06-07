# BGK 12-date Step-Sweep Recalled Results Note

This note preserves the main conclusions from the earlier broad Euler step sweep for the BGK 12-date experiment after the shared `bgk_r00_t1_nex12_step_sweep_summary.md` and `bgk_r00_t1_nex12_step_sweep_table.csv` files were later reused for a targeted `60`-step rerun.

## Original broad sweep setup

- Model family: BGK-style calibrated gDMR with `r=0`, `T=1`, `delta1=delta2=0.94`
- Bermudan exercise dates: `12`
- Focus scenarios: `ATM` and `OTM put`
- Intended Euler step grid in the step-sweep runner: `12, 24, 48, 72, 120, 240, 600`
- Main question: whether the tuned Hybrid LSMC-PDE direct estimator is more robust than plain LSMC when the Euler grid is made coarse

## Recalled conclusions from the earlier broad sweep

- There was a clear hybrid advantage in the **direct estimator** at very coarse Euler step counts.
- For both `ATM` and `OTM put`, the hybrid direct relative error was lower than the benchmark direct relative error at `12`, `24`, and `48` steps.
- The benchmark caught up and became better again around `72+` steps.
- The strongest qualitative takeaway was that, with fixed `12` exercise dates, the tuned Hybrid LSMC-PDE looked more robust than plain LSMC when the Euler grid was made very coarse, especially in the direct estimator.

## Recalled exact examples from the earlier broad sweep

These figures were explicitly recorded in the working notes from the earlier run:

- `ATM`, direct error at `24` steps:
  - benchmark `2.733%`
  - hybrid `2.460%`
- `OTM put`, direct error at `24` steps:
  - benchmark `3.590%`
  - hybrid `3.408%`
- `ATM`, direct error at `48` steps:
  - benchmark `0.409%`
  - hybrid `0.176%`
- `OTM put`, direct error at `48` steps:
  - benchmark `0.469%`
  - hybrid `0.213%`

## Later preserved targeted rerun at 60 steps

The current on-disk `bgk_r00_t1_nex12_step_sweep_summary.md` and `bgk_r00_t1_nex12_step_sweep_table.csv` preserve a later targeted rerun at `60` steps:

- `ATM`, direct error at `60` steps:
  - benchmark `0.092%`
  - hybrid `0.183%`
- `OTM put`, direct error at `60` steps:
  - benchmark `0.129%`
  - hybrid `0.216%`

This later preserved `60`-step point is consistent with the earlier qualitative conclusion that the crossover occurs after the very coarse-grid region.

## File-status note

- The step-sweep runner remains available as `run_bgk_r00_t1_nex12_step_sweep.py`.
- The default step list in the runner still shows the intended broader grid:
  - `12, 24, 48, 72, 120, 240, 600`
- The currently saved `bgk_r00_t1_nex12_step_sweep_summary.md`, `bgk_r00_t1_nex12_step_sweep_table.csv`, and `*_step_sweep_*.svg` files correspond to the later targeted `60`-step rerun rather than the full earlier multi-step sweep.

## Practical interpretation

The restored story from this experiment is:

- the tuned Hybrid LSMC-PDE had a meaningful direct-error advantage over plain LSMC when the Euler grid was very coarse;
- this advantage was visible for both `ATM` and `OTM put` at `24` and `48` steps;
- the advantage did not persist once the Euler grid was refined into the `60` to `72+` range.
