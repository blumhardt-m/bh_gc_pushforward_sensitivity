# Decomposition of Pushforward Sensitivity by Perturbation Axis in Galactic Center Orbit Inference

---

## Abstract

Derived quantities in astrophysical inference pipelines are often treated as stable
summaries of posterior structure, yet sensitivity to underlying perturbations is rarely
characterized in a controlled manner. In Galactic Center orbit inference, periapsis
velocity is a nonlinear function of orbital parameters and is routinely used in
downstream physical interpretation. A preregistered, deterministic perturbation audit
evaluates sensitivity of this derived quantity under two orthogonal perturbation axes
applied to a weighted empirical posterior: weight perturbations at fixed support and
support perturbations of eccentricity at fixed empirical measure.

Both perturbation classes use an identical rank-structured basis and are evaluated with
the same weighted Wasserstein-1 (W1) metric, isolating the perturbation axis as the
sole structural difference. Weight perturbations produce linear scaling of W1 and
approximately uniform localization of divergence across the velocity distribution. In
contrast, support perturbations produce super-linear scaling
($W_1(0.090)/W_1(0.010) = 13.92$) and strong upper-tail concentration, with the top
decile contributing 52–71% of total divergence. Localization is computed using fixed
baseline thresholds, ensuring invariance to perturbation-induced support expansion.

All perturbations, thresholds, and evaluation criteria were preregistered and executed
without deviation. Results establish that sensitivity of derived quantities can differ
qualitatively by perturbation axis, even under identical perturbation structure and
evaluation. This finding has direct implications for robustness assessment of
orbit inference pipelines and other astrophysical analyses involving nonlinear
transformations of posterior distributions.

---

## 1. Introduction

Inference pipelines in astrophysics frequently map posterior distributions over model
parameters to derived physical quantities used for interpretation and downstream
analysis. In Galactic Center orbit studies, posterior samples over orbital elements are
transformed into quantities such as periapsis velocity, which are then used to assess
dynamical constraints and relativistic effects. These transformations are nonlinear, and
sensitivity of derived quantities to perturbations in the underlying posterior is
typically assessed only through aggregate uncertainty summaries.

Aggregate summaries do not distinguish between structural sources of sensitivity. In
particular, changes in posterior weights and changes in the support of the distribution
represent distinct perturbation modes that propagate differently through nonlinear
transformations. Without controlled perturbation, these effects are confounded and
stability of derived quantities cannot be attributed to specific mechanisms.

A controlled perturbation framework is introduced to isolate these modes. A weighted
empirical posterior from Galactic Center orbit inference is subjected to two
preregistered perturbation classes: weight perturbations at fixed support and support
perturbations of eccentricity at fixed empirical measure. Both perturbations use an
identical rank-based structure, ensuring that observed differences arise from the
perturbation axis rather than from the perturbation basis or numerical procedure.
Sensitivity is quantified using the weighted Wasserstein-1 distance between pushforward
distributions of periapsis velocity.

The resulting comparison reveals qualitatively distinct regimes. Weight perturbations
produce linear scaling of divergence and approximately uniform contributions across the
velocity distribution. Support perturbations produce super-linear scaling and strong
concentration of divergence in the high-velocity tail. Localization is computed using
fixed baseline thresholds derived from the unperturbed distribution, preventing
perturbation-dependent rebinning artifacts.

The objective of this study is not to establish general laws of sensitivity, but to
demonstrate, within a realistic inference pipeline, that pushforward behavior depends
critically on the perturbation axis. This has direct implications for robustness
assessment in orbit inference and more broadly for astrophysical analyses involving
nonlinear transformations of posterior distributions.

---

## 2. Related work

Stability and sensitivity of Bayesian posteriors have been studied extensively in the
context of inverse problems and uncertainty quantification. Prior work has established
conditions under which posterior distributions exhibit continuity or Lipschitz stability
under perturbations of priors, likelihoods, or data, often measured in total variation,
Hellinger, or Wasserstein distance (Stuart 2010; Sprungk 2020). These results formalize
robustness at the level of the posterior distribution but typically do not address how
such perturbations propagate through nonlinear transformations to derived quantities.

Pushforward measures provide the natural framework for analyzing transformed
distributions, and Wasserstein distances have been used to compare such measures under
deterministic mappings (Villani 2009; Santambrogio 2015). Existing work characterizes
continuity properties of pushforward distributions and establishes bounds on their
sensitivity under perturbations of the input measure. However, these analyses generally
treat perturbations in aggregate and do not distinguish between structurally different
classes of perturbation.

In astrophysics, uncertainty propagation through nonlinear inference pipelines is widely
recognized as an important practical issue, particularly in contexts where derived
quantities depend sensitively on underlying parameters (Do et al. 2019). Prior studies
have examined how observational and model uncertainties propagate through such pipelines,
but systematic characterization of sensitivity structure at the level of transformed
posterior distributions remains limited.

The present study builds on these foundations by introducing a controlled perturbation
framework that isolates weight and support perturbations under a shared basis, enabling
empirical characterization of axis-dependent pushforward sensitivity within an
astrophysical inference pipeline.

---

## 3. Data and baseline construction

The analysis uses a weighted empirical posterior from Galactic Center orbit inference.
Posterior samples provide values of orbital parameters including eccentricity and
gravitational parameter $GM$, together with associated weights.

Periapsis velocity is computed deterministically from orbital parameters:

$$v_p = \sqrt{\frac{GM(1+e)}{a(1-e)}}$$

where the semi-major axis $a$ is derived from the orbital period and gravitational
parameter. All transformations are deterministic and applied once to construct the
baseline pushforward distribution.

Baseline statistics are computed using weighted empirical measures. No resampling or
stochastic approximation is used.

---

## 4. Perturbation framework

### 3.1 Rank-based perturbation basis

A rank-based score is constructed from ascending order of eccentricity:

$$f_i = \frac{r_i - (N+1)/2}{(N-1)/2}$$

This score defines a deterministic perturbation direction that is symmetric and bounded
in $[-1, 1]$.

### 3.2 Weight perturbation (Step 3)

Weight perturbations are applied at fixed support:

$$w_i(\varepsilon) \propto w_i(1 + \varepsilon f_i)$$

with normalization applied after perturbation. Support points remain unchanged. The
perturbation amplitude grid is $\varepsilon \in \{0.00, 0.01, 0.05, 0.10\}$.

### 3.3 Support perturbation (Step 4)

Support perturbations are applied to eccentricity at fixed weights:

$$\tilde{e}_i(\delta) = e_i + \delta f_i$$

Weights remain fixed. The perturbation is applied deterministically to each sample; no
resampling or stochastic modification of support is performed. Domain constraints
$0 < \tilde{e}_i < 1$ are enforced for all samples at all $\delta$. The perturbation amplitude grid is
$\delta \in \{0.000, 0.010, 0.050, 0.090\}$, with grid maximum set below a preregistered
domain ceiling ($0.090 < 0.097$).

### 3.4 Axis isolation

Both perturbation classes use the same rank-based basis $f_i$ and identical W1
estimation. The perturbation axis (weights versus support) is therefore the only
structural difference between conditions.

---

## 5. Metrics

### 4.1 Weighted Wasserstein-1 distance

Sensitivity is quantified using weighted W1 distance between pushforward distributions.
The algorithm follows a discrete-measure formulation: duplicate-support aggregation by
exact floating-point key equality, sorted union support, sequential CDF accumulation,
and interval integration of absolute CDF differences. This corresponds to the
1-Wasserstein distance between discrete weighted measures under the $L^1$ ground
metric, evaluated exactly via cumulative distribution functions on the union support.
No library implementation is used. The same implementation is applied identically to
both perturbation axes.

### 4.2 Localization

Localization is quantified using decile contributions to total W1. The support is
partitioned into ten equal-probability bins defined by quantiles of the baseline
distribution. Per-decile W1 contribution is the sum of $|F_0(x) - F_\delta(x)| \,
\Delta x$ over all intervals whose left endpoint falls within that bin.

Decile thresholds are computed once from the baseline distribution and held fixed across
all perturbations. This ensures that localization differences are not induced by
perturbation-dependent rebinning.

---

## 6. Results

### 5.1 Weight perturbation

Weight perturbations produce linear scaling of W1 with perturbation amplitude. The
ratio $W_1(0.10)/W_1(0.01) = 9.95$ matches the amplitude ratio of 10, confirming
linear response to within numerical precision.

Decile contributions are approximately uniform, ranging from 9.1% to 10.7% across all
ten bins (Table 1, Figure 2 left). The distribution of localization fractions is
invariant across perturbation amplitude: fractions at $\varepsilon = 0.01$, $0.05$, and
$0.10$ are identical to three decimal places. This invariance is the signature of a
coherent, globally distributed deformation of the cumulative distribution.

### 5.2 Support perturbation

Support perturbations produce super-linear scaling of W1. The ratio
$W_1(0.090)/W_1(0.010) = 13.92$ substantially exceeds the linear prediction of 9
(Figure 1 right).

Decile contributions are strongly concentrated in the top decile, which accounts for
52% of total W1 at $\delta = 0.010$, rising to 71% at $\delta = 0.090$ (Figure 2
right). The remaining nine deciles collectively contribute less than 30% of total
divergence. This concentration intensifies with perturbation amplitude, reflecting
progressive amplification at high eccentricity where $v_p(e)$ is most sensitive.

A secondary contribution of 27–33% is observed in the lowest decile. This reflects
asymmetric transport under the rank-based perturbation, which shifts low-eccentricity
samples toward lower $v_p$. The dominant feature of the localization pattern remains
upper-tail concentration.

In Figure 1, the support-perturbation curve departs systematically above the linear
reference, in contrast to the weight-perturbation curve, which lies on the reference
line across all amplitudes.

### 5.3 Regime contrast

The two perturbation axes produce qualitatively distinct regimes under the same basis
and evaluation metric:

| Quantity | Weight axis | Support axis |
|---|---|---|
| W1 scaling | Linear ($\times$10.0 per decade) | Super-linear ($\times$13.9) |
| D10 fraction | $\approx 0.107$ | 0.525–0.710 |
| D1 fraction | $\approx 0.091$ | 0.275–0.329 |
| Localization character | Broadly distributed | Upper-tail concentrated |

**Figure 1.** Scaling of weighted Wasserstein-1 distance under orthogonal perturbation
axes. Left: weight perturbations at fixed support produce linear scaling with
perturbation amplitude. Right: support perturbations at fixed measure produce
super-linear scaling. Dashed lines show linear reference scaling anchored at the
smallest non-zero perturbation. Both panels use identical rank-based perturbation
structure; the perturbation axis is the only difference.

**Figure 2.** Decile localization of $W_1$ contributions. Left: weight perturbations
produce approximately uniform contributions across deciles. Right: support perturbations
concentrate divergence in the upper tail, with the top decile contributing the majority
of total $W_1$. Decile thresholds are computed from the baseline distribution and held
fixed across all perturbations.

---

## 7. Interpretation

The observed regime contrast is consistent with nonlinear amplification in the
pushforward map $v_p(e)$, which increases sensitivity near $e \to 1$. Weight
perturbations redistribute mass without altering the nonlinear mapping, producing
linear and broadly distributed effects. Support perturbations move samples along the
nonlinear map, producing amplified and localized effects proportional to local gradient
magnitude.

No analytic derivation is claimed. The mechanism is presented as a consistency
explanation for the observed scaling and localization, supported by the synthetic
demonstration in Appendix A.

---

## 8. Scope and limitations

Results apply to:

- the specific posterior structure used (Do et al. 2019, Science 365, 664)
- the periapsis velocity transformation defined in Section 2
- the defined perturbation classes at the specified amplitude grids

No claim is made regarding:

- universal behavior across all posteriors or transformations
- invariance of the regime contrast under alternative perturbation bases
- general robustness of derived quantities in other inference pipelines

---

## 9. Conclusion

A preregistered perturbation audit demonstrates that pushforward sensitivity depends
qualitatively on perturbation axis. Weight perturbations produce linear, globally
distributed divergence. Support perturbations produce super-linear, tail-concentrated
divergence. This distinction arises under identical perturbation bases and evaluation
metrics, isolating the perturbation axis as the determining factor.

These findings provide a structured method for diagnosing robustness of derived
quantities in astrophysical inference pipelines and highlight the importance of
distinguishing perturbation modes in sensitivity analysis.

---

## Appendix A: Minimal synthetic demonstration of axis-dependent pushforward regimes

*(See* `bh_gc_pushforward_synthetic_demo/results/appendix_A.md`*.)*

---

## Data availability

Preregistered protocols, execution scripts, and results are available at:

- Step 3 (weight perturbation): osf.io/dmpes
- Step 4 (support perturbation): osf.io/fkx46

All results in this manuscript can be reproduced deterministically from the
preregistered protocols and released execution artifacts.
