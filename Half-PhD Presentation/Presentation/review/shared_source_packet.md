# Shared Source Packet

This packet records the implementation inputs for the six-agent agreement workflow.

## Scope

- Write boundary: `D:\Mara PhD\Half-PhD Presentation` only.
- Read sources:
  - `D:\Mara PhD\Paper A`
  - `D:\Mara PhD\Paper B`
  - `D:\Mara PhD\Paper C`
- Output: professional 30-minute numerics-first Beamer presentation.

## Narrative

Efficient early-exercise option pricing under increasingly rich stochastic-volatility models.

1. Paper A: AES for Heston and double Heston, focusing on exact/nonnegative CIR variance sampling and early-exercise numerical results.
2. Paper B: AEMS/AEMS-SOR for Gatheral DMR, extending the almost-exact philosophy to a non-affine model.
3. Paper C: Hybrid LSMC-PDE for Bermudan GDMR pricing, reducing continuation-value regression difficulty.

## Main Guardrails

- Do not call AES fully exact; only the CIR variance sampling is exact/nonnegative.
- Do not claim AES/AEMS/AEMS-SOR always outperform Euler.
- Treat Paper B exact table percentages as needing QA before being quoted.
- Treat Paper C errors as benchmark-relative deviations against large LSMC references, not exact pricing errors.
- Do not imply Paper C uses AEMS/AEMS-SOR.

## Selected Assets

See `D:\Mara PhD\Half-PhD Presentation\Figures\manifest.csv`.
