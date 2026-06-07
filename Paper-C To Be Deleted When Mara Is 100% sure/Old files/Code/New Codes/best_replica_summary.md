# Best Replica Summary

## Best replica of Farahany

`gdmr_fst_swap_scripts` is the best replica of Farahany's hybrid LSMC-PDE method among the two folders.

Why:

- it uses an FST/FFT conditional solver, which matches the solver family described in Farahany et al. (2020)
- it keeps the low estimator hybrid by simulating fresh volatility paths and recomputing conditional expectations recursively
- on the matched run, its hybrid direct and hybrid low estimates are tighter to each other than in `version1`

Main caveat:

- its LSMC comparison baseline is not the same as `version1`
- so it is not a pure "same benchmark, better PDE solver" swap

## Best current repo-style gDMR implementation

`gdmr_standalone_version1` is the best match to the current repo's manuscript-oriented gDMR branch.

Why:

- it is byte-identical to `Code/gdmr_standalone`, which is already the repo's established gDMR reference branch
- it keeps the manuscript-style truncation, compact-support volatility basis, and pathwise pre-surface regression structure
- its benchmark side is closer to a Tsitsiklis-Van Roy style full-state regression than the more classical Longstaff-Schwartz baseline used in `fst_swap`

Main caveats:

- it does not use Farahany's FST/FFT conditional solver
- its hybrid low estimator is a fresh full-path rollout, not Farahany's hybrid low estimator
- one of its scripts currently fails on direct Windows execution because of the memmap temp cleanup issue

## Best next step

The best next step is not to choose one folder and declare it fully correct. The better move is to combine the strongest parts of both after this audit.

Recommended direction:

- keep `gdmr_standalone_version1` or `Code/gdmr_standalone` as the repo base, because that is the current manuscript-oriented branch
- transplant only the Farahany-closer numerical pieces from `gdmr_fst_swap_scripts`
- keep the comparison baseline fixed while doing that, so future differences really isolate the PDE / hybrid changes

In practice, the next implementation pass should prioritize:

1. fix the Windows memmap cleanup problem in the `version1` benchmark script
2. keep one single LSMC baseline across both branches
3. keep the manuscript-style truncation and basis setup
4. adopt the FST/FFT conditional solver from `fst_swap`
5. adopt the hybrid low-estimator recursion from `fst_swap`
6. rerun the same matched block and only then judge relative error again

## Final recommendation

If your main goal is "follow Farahany first," start from the logic in `gdmr_fst_swap_scripts`.

If your main goal is "stay closest to the current repo/manuscript branch while improving it," start from `gdmr_standalone_version1`.

If I had to choose one practical path forward, I would treat:

- `gdmr_fst_swap_scripts` as the better Farahany replica
- `gdmr_standalone_version1` as the better repo baseline
- the real target as a third combined branch that keeps the repo baseline but replaces the hybrid numerics with the Farahany-closer FST and hybrid-low machinery
