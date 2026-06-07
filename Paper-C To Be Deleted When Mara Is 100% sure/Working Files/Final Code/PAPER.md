# PAPER.md

This note is the exact manuscript-to-code gap report for the final package in
`Final Code`.

It answers four questions:

1. What the final code actually implements
2. What `Manuscript/main.pdf` already contains
3. What is still missing from `main.pdf`
4. Exactly where each missing block should be inserted

All page references below come from `Manuscript/main.aux`, so they match the
current compiled `main.pdf`.

## Final Code: What It Implements

The final package implements:

- Bermudan put pricing
- under the gDMR model
- with the repo/original gDMR LSMC benchmark
- and a Farahany-style hybrid LSMC-PDE method

The final package uses these numerical ingredients:

- full-state LSMC benchmark on `(S, v, v')`
- one-way-coupled volatility simulation
- pathwise pre-surfaces on an asset grid
- regression across volatility states
- Bermudan backward recursion
- FST/FFT one-step conditional solver on the log-asset grid
- hybrid low estimator using fresh volatility paths only

So the final package is fully about:

- gDMR
- Bermudan options
- hybrid LSMC-PDE
- Farahany-style conditional Fourier/PDE solving

## What `main.pdf` Already Has

### Page 3: gDMR model and one-way coupling

Already present:

- equation `(1)` for the gDMR dynamics
- the one-way coupling remark

Anchors:

- `eq:gdmr` -> page `3`
- `rem:one-way` -> page `3`

This part already matches the final code conceptually.

### Pages 4-5: conditional PDE reduction

Already present:

- the orthogonalization step
- the projection coefficients
- the conditional PDE representation

Anchors:

- `sec:conditional_pde` -> page `4`
- `eq:proj-coeffs` -> page `4`
- `eq:sigperp` -> page `4`
- `eq:orth` -> page `4`
- `eq:logS`, `eq:logS-orth`, `eq:Zshift`, `eq:Ydyn` -> page `5`
- `lem:cond-PDE` -> page `5`

This is the correct continuous-time foundation for the final one-dimensional
conditional solver.

### Page 7: hybrid methodology skeleton

Already present:

- the methodology section
- discretization
- the asset-grid pre-surface idea

Anchors:

- `sec:methodology` -> page `7`
- `eq:presurface` -> page `7`

### Page 8: regression and direct estimator

Already present:

- the regression equation
- the completed continuation surface
- the Bermudan max recursion
- the time-zero direct estimator

Anchors:

- `eq:regression` -> page `8`
- subsection `7.3 Time-zero estimators (direct and low)` -> page `8`
- `sec:conclusion` -> page `8`

So the manuscript already has the correct high-level structure. What is missing
is the executable numerical bridge to the final code.

## Exact Missing Pieces

## Missing Piece 1: the exact truncated volatility basis used by the final code

### Where it is missing

- `main.pdf` page `7`
- `main.tex` lines `592-597`
- current text: the manuscript says to choose basis functions on a truncated
  volatility domain, but it never states the actual basis used in code

### Exact insertion point

Insert this block:

- after `main.tex:597`
- before `main.tex:599` (`\subsection{Algorithm overview}`)

### What should be added

```text
On the truncation box

    D_v = [0, v_max] x [0, v'_max],

define the normalized variables

    y = v / v_max,
    z = v' / v'_max,

and use the compact-support cubic basis

    phi(v, v')
    = 1_{D_v}(v, v')
      (1, y, z, y^2, yz, z^2, y^3, y^2 z, y z^2, z^3).
```

### Why it is needed

The final hybrid code does not use an abstract unspecified basis. It uses this
specific 10-term truncated cubic basis on `(v, v')`. If the paper is supposed
to match the code exactly, this basis must be written down.

## Missing Piece 2: the discrete one-step path statistics used by the solver

### Where it is missing

- `main.pdf` page `7`
- around `main.tex:607-618`
- current text defines the pre-surface in equation `(11)`, then jumps directly
  to "solve a one-dimensional conditional PDE in log-space"

### Exact insertion point

Insert this block:

- after `main.tex:618`
- before `main.tex:620`

That means:

- keep the current equation `(11)`
- keep the sentence that says a conditional PDE is solved in log-space
- then insert the discrete path-statistics block
- then continue to the regression paragraph at line `620`

### What should be added

```text
For each sampled volatility path segment j over [t_n, t_{n+1}], define

    A_n^(j) = integral_{t_n}^{t_{n+1}} (r - 1/2 v_t^(j)) dt,

    B_n^(j) = sigma_perp^2 integral_{t_n}^{t_{n+1}} v_t^(j) dt,

    Z_n^(j) = integral_{t_n}^{t_{n+1}}
              sqrt(v_t^(j)) (beta_2 dW_t^(2,j) + beta_3 dW_t^(3,j)).

Then, conditional on the sampled volatility path segment, the one-step
log-price update is

    X_{t_{n+1}} = y + A_n^(j) + Z_n^(j) + sqrt(B_n^(j)) xi,

where xi ~ N(0,1).
```

### Why it is needed

The final code carries each volatility path segment into the one-step solver
through the finite-dimensional statistics:

- `a_stats`
- `b_stats`
- `z_stats`

The manuscript currently has the continuous derivation on pages `4-5`, but it
does not state this discrete numerical bridge on page `7`.

## Missing Piece 3: the explicit FST/FFT conditional solver

### Where it is missing

- `main.pdf` page `7`
- around `main.tex:617-618`
- current text says:
  "Equation (11) is evaluated ... by solving a one-dimensional conditional PDE
  in log-space; see Section~\ref{sec:numerics}."

### Exact problem

There is no actual labeled numerical section destination for `sec:numerics` in
`main.aux`. So the manuscript points to a numerical implementation section that
is not currently there.

### Exact insertion point

Insert a new short subsection or paragraph block:

- after the new discrete-statistics block above
- still before `main.tex:620`

So the order on page `7` should become:

1. equation `(11)` pre-surface
2. short reminder sentence about the conditional PDE
3. discrete statistics block
4. FST/FFT conditional solver block
5. regression paragraph beginning at line `620`

### What should be added

```text
For each sampled path j, define the one-step conditional value

    u_n^(j)(y)
    = E^Q[
        g(Y_{t_{n+1}} + Z_n^(j), v_{t_{n+1}}^(j), (v')_{t_{n+1}}^(j))
        | Y_{t_n} = y, [v^(j), (v')^(j)]_{t_n}^{t_{n+1}}
      ].

This solves the one-dimensional conditional PDE

    partial_t u
    + a_n^(j)(t) partial_y u
    + (1/2) b_n^(j)(t) partial_yy u
    = 0,

with terminal condition

    u(t_{n+1}, y)
    = g(y + Z_n^(j), v_{t_{n+1}}^(j), (v')_{t_{n+1}}^(j)).

In Fourier space, define the characteristic exponent

    Psi_n^(j)(omega)
    = i omega Z_n^(j)
      + i omega integral_{t_n}^{t_{n+1}} a_n^(j)(s) ds
      - (1/2) omega^2 integral_{t_n}^{t_{n+1}} b_n^(j)(s) ds.

The Farahany-style FST recursion is then

    u_n^(j) = F^{-1}( F[g_{n+1}^(j)] exp(Psi_n^(j)) ).
```

### Why it is needed

This is the central numerical step used by the final hybrid code. Without it,
the manuscript says what kind of PDE must be solved, but it does not say how
the final code actually solves it.

## Missing Piece 4: the hybrid low estimator

### Where it is missing

- `main.pdf` page `8`
- `main.tex:636-648`
- current text defines the subsection "Time-zero estimators (direct and low)"
  but only writes the direct estimator

### Exact insertion point

Insert this block:

- after `main.tex:648`
- before `main.tex:650` (`\section{Conclusion}`)

### What should be added

```text
Define the learned continuation rule by

    C_hat_n^N(s, v, v')
    = a_n^N(s) . phi(v, v').

Define the induced stopping rule

    tau_hat^(j)
    = inf { t_n : h_n(S_{t_n}) >= C_hat_n^N(S_{t_n}, v_{t_n}^(j), (v')_{t_n}^(j)) } ^ T.

Then define the low estimator

    V_hat_{l,0}(s_i)
    = (1 / N_low) sum_{j=1}^{N_low}
      E^Q[
        exp(-r tau_hat^(j)) h_{tau_hat^(j)}(S_{tau_hat^(j)})
        | S_0 = s_i, [v^(j), (v')^(j)]_0^T
      ].

For the implemented hybrid recursion, define

    U_M^(j)(s) = h_M(s),

and for n = M-1, ..., 0,

    U_n^(j)(s) =
      h_n(s),
        if h_n(s) >= C_hat_n^N(s, v_{t_n}^(j), (v')_{t_n}^(j)),

      exp(-r Delta t_n)
      E^Q[
        U_{n+1}^(j)(S_{t_{n+1}})
        | S_{t_n} = s, [v^(j), (v')^(j)]_{t_n}^{t_{n+1}}
      ],
        otherwise.
```

### Why it is needed

The final code uses a genuine hybrid low estimator:

- fresh volatility paths only
- learned continuation policy from the training stage
- fresh one-step conditional solves under that policy

This is one of the most important missing parts of the manuscript.

## Missing Piece 5: explicit algorithm boxes

### Where it is missing

- `main.pdf` page `8`
- after the low-estimator material that should be added
- before the conclusion on page `8`

### Exact insertion point

Insert the algorithm boxes:

- after the new low-estimator equations
- before `main.tex:650`

### What should be added

#### Algorithm A: training and direct estimator

```text
1. Simulate N training volatility paths.
2. For each Bermudan step and each path, compute the pathwise pre-surface on the asset grid.
3. Regress across volatility states to get a_n^N(s_i).
4. Apply the Bermudan max recursion backward.
5. Average the first-step pre-surfaces to form the direct estimator.
```

#### Algorithm B: hybrid low estimator

```text
1. Simulate N_low fresh volatility paths.
2. Evaluate the learned continuation rule along those paths.
3. Recompute the one-step conditional problem under the induced policy.
4. Propagate the backward policy value U_n^(j).
5. Average across fresh paths to form the low estimator.
```

### Why it is needed

The prose on pages `7-8` is mathematically aligned with the final method, but
the execution order is still implicit. These two algorithm boxes would make the
paper reproducible.

## Exact Page-and-Location Map

| Missing item | PDF page | Current manuscript location | Exact insertion rule |
| --- | ---: | --- | --- |
| Exact truncated basis | 7 | `main.tex:592-597` | Insert after line `597`, before line `599` |
| Discrete path statistics | 7 | `main.tex:607-618` around equation `(11)` | Insert after line `618`, before line `620` |
| FST/FFT solver block | 7 | same region as above | Insert after the new statistics block, still before line `620` |
| Hybrid low estimator | 8 | `main.tex:636-648` | Insert after line `648`, before line `650` |
| Training/direct algorithm box | 8 | after new low-estimator block | Insert before line `650` |
| Fresh-path low algorithm box | 8 | after new low-estimator block | Insert before line `650` |

## Code-to-Manuscript Comparison Summary

What the final code already matches:

- gDMR dynamics: yes
- one-way coupling: yes
- conditional PDE reduction: yes
- pre-surface and regression structure: yes
- Bermudan recursion: yes
- direct estimator: yes

What the manuscript does not yet state explicitly enough:

- the actual discrete path statistics used by the implemented one-step solver
- the actual FST/FFT recursion
- the hybrid low-estimator equations
- the exact compact-support basis used in code
- explicit algorithm boxes

## Bottom Line

The paper is already structurally aligned with the final code, but not yet
numerically explicit enough to reproduce it exactly.

If you want `main.pdf` to match `Final Code` exactly, the manuscript must be
expanded:

- on page `7`, in two places inside Section `7`
- on page `8`, immediately after the direct estimator and before the conclusion

That is the precise gap between the current manuscript and the final packaged
code.
