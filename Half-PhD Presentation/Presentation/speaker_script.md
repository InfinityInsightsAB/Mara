# Half-PhD Seminar Speaker Script

This script follows the pasted page-by-page instructions. Current compiled main deck: 30 slides. Backup prompts are retained below.

The main-slide timings sum to about 28:30. The transition addendum below adds about 1:40 of planned speaking, giving a target main-talk time close to 30 minutes before questions.

## Main Slides

### Slide 1 - Title
Time: 20 seconds

Today I present one numerical line across three papers. Papers A and B focus on reducing simulation bias in stochastic volatility models. Paper C keeps the stochastic-volatility setting but attacks the continuation-value regression problem directly.

### Slide 2 - Roadmap
Time: 55 seconds

This is the structure of the talk. Paper A starts with Heston-type models, where the variance has a CIR transition that can be sampled exactly. Paper B asks whether that almost-exact idea still helps in Gatheral's double mean-reverting model. Paper C then changes the question: instead of only improving paths, can we reduce the continuation-value regression itself?

### Slide 3 - Bermudan and American Pricing
Time: 1 minute 5 seconds

For early-exercise options, the essential object is the comparison between immediate exercise and continuation. The problem is not only to simulate future paths. We also have to estimate a conditional expectation at every exercise date, and small errors in that conditional expectation can change the exercise decision.

### Slide 4 - Two Numerical Difficulties
Time: 55 seconds

The two numerical difficulties are separated here. First, variance simulation: Euler-type schemes can produce negative variance values and discretization bias. Second, continuation regression: in multifactor stochastic volatility, plain LSMC must learn a high-dimensional conditional expectation from paths. Papers A and B address the first difficulty. Paper C addresses the second.

### Slide 5 - Model Hierarchy
Time: 55 seconds

This slide fixes the model hierarchy. Paper A is built on Heston and double Heston, where variance factors are CIR-type. Paper B moves to Gatheral DMR, where the current variance mean-reverts to a stochastic long-run variance. Paper C keeps this double mean-reverting structure but allows the CEV-type generalized version.

### Slide 6 - Paper A Thesis
Time: 55 seconds

Paper A takes the almost-exact simulation idea and applies it to early-exercise pricing. The important point is that Bermudan pricing naturally gives us exercise intervals. If we can simulate one step per interval accurately, then we avoid adding many artificial substeps just to control Euler bias.

### Slide 7 - Paper A Derivation
Time: 1 minute 25 seconds

This is the core mechanism. By applying Ito's lemma to the log price and decomposing the correlated Brownian motions, the correlated variance-driver terms in the stock equation can be connected to the variance updates. The variance endpoints are sampled from noncentral chi-square CIR transitions, so the variance remains nonnegative without reflection or truncation. The method is almost exact rather than fully exact because the remaining orthogonal Brownian integrals are still approximated.

### Slide 8 - Paper A Bermudan Result
Time: 1 minute 10 seconds

These are Bermudan Heston experiments with 40 and 60 exercise dates. The key comparison is that AES is already accurate when the simulation step is matched to the exercise interval. The at-the-money and in-the-money cases behave most consistently. The out-of-the-money case is more variable, so I do not overclaim uniform dominance.

### Slide 9 - Paper A: American Put Experiment
Time: 50 seconds

Say: "I add one American option experiment because it shows that the AES benefit is not only a Bermudan-grid effect. In the double Heston American put test, using the same small number of time steps, AES stays close to the reference value in all three cases, while Euler is visibly below the reference. This supports the message that exact CIR variance sampling can materially improve the path simulation component of early-exercise pricing."

### Slide 10 - Paper A Efficiency
Time: 1 minute

This slide is about efficiency. The point is not that AES is always cheaper per step. The point is that Euler often needs many more steps to reach similar accuracy. Once Euler is forced to refine the time grid, AES can become better in accuracy, computation time, and memory.

### Slide 11 - Paper A Double Heston Result
Time: 40 seconds

This slide is now a compact recap of the same American put evidence under double Heston. I would not repeat the full table explanation. I would use it to reinforce one point: at a very small step count, exact nonnegative variance sampling helps when naive Euler struggles.

### Slide 12 - Paper A Transition
Time: 45 seconds

The limitation is important. Paper A works very naturally because Heston-type variance factors have CIR transitions. But Gatheral DMR is less convenient: the current variance mean-reverts to another stochastic variance level. Paper B asks how much of the almost-exact idea survives there.

### Slide 13 - Paper B Problem
Time: 55 seconds

Gatheral DMR introduces a stochastic long-run variance level. This gives more volatility flexibility, but it removes the clean affine structure that made Heston-type simulation easier. The numerical issue is that \(v'\) can be treated as CIR, but the joint pair \((v,v')\) cannot simply be sampled exactly.

### Slide 14 - Paper B Method
Time: 55 seconds

AEMS is not a fully exact scheme. It is a mixed scheme. The long-run variance \(v'\) is still sampled using a CIR transition. The current variance \(v\) is updated by a Milstein-style correction. Then the log-price update uses the correlation structure, as in Paper A, to reduce the discretization error coming from the variance driver.

### Slide 15 - Paper B Derivation
Time: 1 minute 20 seconds

This is the key algebraic step in Paper B. The Cholesky decomposition expresses the correlated Brownian motions through independent ones. Then the variance equation is rearranged so that part of the shared Brownian contribution can be absorbed through the variance update. The point is the logic of the construction, not reading every term in the formula.

### Slide 16 - Paper B Derivation: AEMS-SOR Second-Order Correction
Time: 60 seconds

Say: "This slide is the second-order refinement. The left formula is the general second-order discretization; applying it to the current variance equation produces the AEMS-SOR variance step on the right. The important point for the talk is not every correction term; it is that AEMS-SOR is AEMS plus higher-order correction terms, which can improve weak convergence, but does not make it universally best in every numerical experiment."

### Slide 17 - Paper B American Vanilla
Time: 1 minute 10 seconds

For American vanilla puts, the at-the-money case is the most sensitive because the exercise decision is close to the continuation boundary. The figure shows that the AEMS-based schemes are competitive and often reduce relative error compared with Euler-Maruyama as the time grid is refined. I present this as a numerical pattern across the tested time steps, not as a universal ranking.

### Slide 18 - Paper B Forward Volatility Swap
Time: 1 minute

The forward volatility swap is the cleanest Paper B comparison because it has an analytical benchmark. Here AEMS performs well for a payoff that depends directly on the variance dynamics. The important nuance is that the second-order refinement is not automatically best. Higher formal order does not dominate in every payoff and maturity regime.

### Slide 19 - Paper B Basket Stability
Time: 55 seconds

This basket option experiment is not an accuracy benchmark. It is a stability experiment. The Euler-Maruyama outputs fluctuate more across independent runs, while AEMS and AEMS-SOR are visibly steadier. Since there is no analytical benchmark on this slide, the correct claim is stability evidence rather than a direct true-error comparison.

### Slide 20 - Paper B Transition
Time: 45 seconds

The conclusion of Paper B is deliberately balanced. AEMS and AEMS-SOR improve the simulation picture, but not uniformly for every payoff and maturity. More importantly, even after improving the paths, early-exercise pricing still has the high-dimensional continuation regression problem. That is the entry point for Paper C.

### Slide 21 - Paper C Problem
Time: 55 seconds

In Paper C the model is GDMR, so the state contains the asset, the current variance, and the stochastic long-run variance. Plain LSMC has to regress over all three coordinates. But the variance subsystem is one-way coupled: we can simulate \(v\) and \(v'\) without first knowing the asset path. Paper C uses exactly that structure.

### Slide 22 - Paper C: Hybrid Decomposition of the Continuation Value
Time: 60 seconds

Say: "The continuation value is split into an inner and an outer problem. Inside one exercise interval we condition on the variance Brownian drivers. That fixes the variance path and the correlated part of the stock Brownian motion, so the remaining stock-price problem is one-dimensional and can be evaluated by the conditional PDE or FFT step. Then the outer expectation over the current variance state is what we approximate by least-squares regression. This is the key idea behind the method: do not regress over the full stock and variance state if the stock direction can be handled conditionally."

### Slide 23 - Paper C Algorithm
Time: 1 minute 10 seconds

The main idea is to condition on the variance Brownian drivers. Once those are fixed, the asset Brownian motion can be decomposed into a part explained by the variance drivers and one residual independent Brownian component. Conditional on the variance path, the log-price step is Gaussian. Therefore the asset direction can be propagated by FFT/PDE, and regression is needed only over the variance state.

### Slide 24 - Paper C Recursion
Time: 1 minute 15 seconds

The backward recursion is still the usual Bermudan recursion. At maturity, the value is the payoff. Moving backward, each variance path gives a pre-surface on the asset grid. Then, for each asset grid point, we regress those pre-surfaces over the variance variables only. Finally, the exercise decision is the maximum of payoff and continuation.

### Slide 25 - Paper C Path-Budget Result
Time: 1 minute 20 seconds

This figure fixes 60 Euler steps and varies the number of paths. The hybrid estimator gives visibly lower relative errors in the low- and moderate-path regimes. The errors are benchmark-relative: they are computed against large-simulation plain LSMC reference prices, not exact prices.

### Slide 26 - Paper C Path-Budget Result at 48 Steps
Time: 1 minute 10 seconds

This figure repeats the path-budget comparison with 48 Euler steps. The same qualitative pattern appears: the hybrid estimator is most useful when the path budget is small or moderate. The blue curves are plain LSMC, the orange curves are Hybrid LSMC-PDE, and the vertical bars show empirical variability across runs.

### Slide 27 - Paper C Time-Step Sensitivity
Time: 1 minute 10 seconds

This slide fixes the path count at 20,000 and changes the Euler time grid. The hybrid estimator is usually centered at lower benchmark-relative errors across the tested step counts. The interpretation is that the conditional PDE step reduces the dimension of the continuation regression, with the clearest benefit when sampling noise is still important.

### Slide 28 - Synthesis
Time: 1 minute

The synthesis is that the three papers are not separate numerical experiments. They form a progression. Paper A uses CIR structure to reduce Heston simulation bias. Paper B adapts that idea to a non-affine DMR setting. Paper C uses one-way coupling to reduce the continuation-value regression dimension. The common theme is structural computation: use the model to decide where numerical effort should go.

### Slide 29 - Papers
Time: 30 seconds

This slide records the three papers behind the talk. Paper A is the Heston and double Heston AES work, Paper B is the Gatheral DMR AEMS and AEMS-SOR work, and Paper C is the Hybrid LSMC-PDE work currently under review.

### Slide 30 - Thank You
Time: 10 seconds

Thank you for your attention.

## Main-Talk Transition Addendum

Use these short transitions only if needed to keep the 29-slide version close to the requested 30-minute speaking length. They do not replace the slide scripts above.

### After Slide 7
Additional time: 20 seconds

Before moving to the figures, keep the distinction fixed: the variance endpoint is the exact part, while the asset update is still an approximation. The numerical question is whether this exact variance component is enough to improve early-exercise pricing in low-step regimes.

### After Slide 12
Additional time: 20 seconds

This is the point where the talk moves from a convenient square-root variance structure to a less convenient double mean-reverting structure. The next paper keeps the simulation question, but removes some of the Heston structure that made the first construction natural.

### After Slide 20
Additional time: 25 seconds

At this stage, the path-simulation story is stronger, but the early-exercise algorithm still has to decide whether to exercise or continue. That decision is controlled by a conditional expectation, so improving paths alone cannot be the whole story.

### Before Slide 28
Additional time: 35 seconds

The last comparison is not meant to say that one numerical method is universally best. The point is more structural: when the difficult part is variance simulation, use transition structure; when the difficult part is regression dimension, condition on the variance path and move the asset direction out of the regression.

## Backup Prompts

### Backup 1 - Common Bermudan Recursion
Time if used: 45 seconds

This is the common Bermudan recursion used throughout the talk. At each exercise date the value is the maximum of payoff and discounted conditional continuation value.

### Backup 2 - Exact CIR Variance Sampling
Time if used: 45 seconds

For a CIR variance process, the transition over one time step is a scaled noncentral chi-square distribution. This is the exact and nonnegative part used by AES and inherited by the AEMS philosophy.

### Backup 3 - Paper A Double Heston Simulation Step
Time if used: 1 minute

The double Heston extension repeats the same idea factor by factor. Each CIR variance coordinate is sampled from its transition law, and each correlated variance-driver integral is replaced by an endpoint term. The remaining independent log-price integrals are approximated.

### Backup 4 - Paper A American Heston Relative Errors
Time if used: 1 minute

These are the American Heston experiments. They support the same message as the Bermudan slide: AES remains accurate when the variance process is difficult, including cases where the Feller condition does not hold.

### Backup 5 - Paper B Numerical Interpretation
Time if used: 45 seconds

This is the caution slide for Paper B. Some Paper B figures are best used qualitatively unless the relative errors are recomputed from the underlying tables and the benchmark type is stated precisely.

### Backup 6 - Paper B AEMS One-Step Update
Time if used: 1 minute 10 seconds

The first variance line samples \(v'\) from a CIR transition. The second line updates \(v\) using a Milstein correction. The log-price update then uses the simulated \(v_{n+1}-v_n\) increment to absorb one correlated driver, leaving the remaining Brownian terms to be approximated.

### Backup 7 - Paper B Barrier Put Results
Time if used: 1 minute

The barrier option results show that the ranking of EM, AEMS, and AEMS-SOR depends on moneyness and maturity. The useful claim is not uniform dominance; it is that the AEMS family is competitive and often more stable.

### Backup 8 - Paper C Variance Well-Posedness
Time if used: 45 seconds

The variance well-posedness result justifies simulating the nonnegative GDMR variance subsystem under the stated parameter range. It supports the hybrid construction, but it is not the main result I emphasize in the 30-minute talk.

### Backup 9 - Paper C Path-Budget Sweep at 48 Steps
Time if used: 45 seconds

This is the same path-budget comparison at 48 Euler steps. The pattern remains that the hybrid method is most useful at low and moderate path counts.

### Backup 10 - Paper C Step Sweep at 60,000 Paths
Time if used: 45 seconds

This is the time-step sweep at 60,000 paths. At this larger path count, both methods are more stable, and the remaining differences are mainly benchmark-relative numerical differences.
