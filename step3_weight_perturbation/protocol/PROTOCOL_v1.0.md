# Protocol v1.0 — BH GC Orbit Measure Perturbation Audit: Controlled Departure from Invariance

**Status: FROZEN v1.0**
**Parent studies:**
  Step 0: bh_gc_orbit_inference (osf.io/sm7dx)
  Step 1: bh_gc_orbit_estimand_sensitivity (osf.io/uhp5y)
  Step 2: bh_gc_orbit_covariance_audit (osf.io/jmpbe)

---

## 1. Research question

Does a controlled, deterministic perturbation of the weights on a fixed
empirical posterior induce measurable divergence in the pushforward
distribution of periapsis velocity v_p?

Primary question: W1(T#mu, T#mu_epsilon) > 0 ?

where mu is the original weighted empirical posterior and mu_epsilon is the
perturbed posterior obtained by reweighting under a preregistered deterministic
function. The support is identical across all measures; only weights change.

This study is not a significance test. It is a deterministic response audit.

---

## 2. Motivation and relation to prior steps

Steps 0-2 established a complete invariance regime:

  Step 0: structural null — M_BH independent of orbital elements under
    diagonal Gaussian; W1 = 0 by construction.

  Step 1: v_p estimand under diagonal Gaussian; distinct computational
    graphs; W1 = 1.94e-12 km/s (W1/sigma_A = 4.9e-14). Negligible.

  Step 2: v_p estimand on weighted empirical posterior with full covariance;
    W1 = 1.92e-12 km/s (W1/sigma_A = 6.4e-14). Negligible.

Joint conclusion from Steps 0-2: algebraically equivalent reparameterizations
of a fixed measure produce no meaningful pushforward divergence, regardless of
whether the measure is independent Gaussian or a full empirical posterior with
covariance.

This step introduces the first operative non-null pathway: measure change.
Unlike Steps 0-2, the probability mass assigned to support points is modified.
Support is held fixed; weights are changed deterministically. The goal is to
verify that controlled changes in the posterior measure produce corresponding
changes in the pushforward distribution — establishing that the measurement
apparatus is sensitive to measure perturbations before further program steps
are designed.

Note: this study uses only one computational map (Pipeline A, direct
computation of v_p from GM, P, e). The two-pipeline structure of Steps 0-2
is not reproduced here because the object of study is measure change, not
computational graph equivalence (Decision 006).

---

## 3. Data source and foreknowledge

Source: Do et al. 2019 (Science 365, 664), doi:10.1126/science.aav8137
File: aav8137_data_s3.zip (Science Data S3)
SHA256: 8397176cb6e996c21f64acadc77f470cf5412335a076a8e565e530ff52eb986a
Primary chain: chains_redshift.txt
Model: relativistic with free Upsilon

File structure: no header row. Every line is a posterior sample.
N_total = N_samples = 33,079 (verified in Step 2 by direct line count).

N_eff = 10,222 (confirmed in Step 2).

Foreknowledge: column schema, file structure, row count, weight validity,
and N_eff were confirmed in Step 2. No new distributional inspection is
performed prior to freeze. No perturbation parameters are tuned after
observing outputs.

Columns used: 1 (weight), 2 (GM [1e6 solar GM]), 10 (P [yr]), 12 (e)

Unit convention: GM_chain stores values in units of 10^6 * GM_sun.
  GM_SI [m^3 s^-2] = GM_chain * 1e6 * 1.32712440018e20  (IAU 2012)
  yr_s = 365.25 * 24 * 3600  [seconds per year]

---

## 4. Base measure and perturbed measure

Let the original normalized weights be:
  w_i = weight_i / sum_j(weight_j)

The perturbed raw weights are defined by:
  w_tilde_i(epsilon) = w_i * (1 + epsilon * f_i)

with renormalization:
  w_i(epsilon) = w_tilde_i(epsilon) / sum_j(w_tilde_j(epsilon))

The support points v_p_i are identical across all measures. Only weights change.

---

## 5. Perturbation function (locked)

Use a deterministic centered rank-based perturbation on eccentricity e.

Definition:
  1. Rank all rows by e_i in ascending order. Ties broken by original row
     order (smaller row index = lower rank). Ranks r_i in {1, ..., N}.
  2. Centered rank score:
       f_i = (r_i - (N+1)/2) / ((N-1)/2)

Properties:
  - f_i in [-1, 1]
  - monotone increasing in e_i
  - deterministic
  - support-preserving
  - sum_i(w_i * f_i) approximately zero (centered)

Rationale: creates a smooth, interpretable tilt toward high- or
low-eccentricity samples; avoids stochasticity; avoids external model
assumptions; yields controlled departures from the base measure.

Implementation note: all arithmetic in float64. Ranking must be performed
in a deterministic, stable sort in float64. For tied e values, row order
(ascending row index) determines rank.

---

## 6. Epsilon grid (locked)

epsilon in {0.00, 0.01, 0.05, 0.10}

  epsilon = 0.00: sanity check — must recover Step 2 baseline
  epsilon = 0.01: weak perturbation
  epsilon = 0.05: moderate perturbation
  epsilon = 0.10: stronger perturbation

No additional epsilon values may be added after freeze.

Constraint: if any w_tilde_i(epsilon) <= 0 for any row, execution halts
for that epsilon value and a deviation is logged. The chosen grid is
expected not to produce negative raw weights given the centered score and
original weight distribution, but this is verified at runtime.

---

## 7. Estimand

Periapsis velocity (identical to Steps 1-2):

  v_p = sqrt(GM_SI * (1 + e) / (a * (1 - e))) / 1000  [km/s]

  GM_SI = GM_chain * 1e6 * 1.32712440018e20  [m^3 s^-2]
  P_s   = P_chain * 365.25 * 24 * 3600       [seconds]
  a     = (GM_SI * P_s^2 / (4*pi^2))^(1/3)  [metres]

All arithmetic in float64. v_p computed once from the fixed support; the
same v_p_i values are used with all weight vectors.

---

## 8. Pushforward definition

The pushforward of the base measure:
  T#mu = {(v_p_i, w_i)}, i = 1..33079

The pushforward of the perturbed measure at epsilon:
  T#mu_epsilon = {(v_p_i, w_i(epsilon))}, i = 1..33079

Support v_p_i is identical across all epsilon values.
v_p is computed once and reused.

---

## 9. Primary metric: weighted Wasserstein-1 distance

For each epsilon in the grid, compute W1(T#mu, T#mu_epsilon).

Exact algorithm (identical to Step 2, protocol Section 7):

  Preprocessing: for each pushforward, aggregate duplicate float64 v_p
  values by summing weights. Aggregation in original row order, before
  union construction. Equality is exact float64 equality only.

  Step 1: Form sorted union of all unique float64 support values from both
    measures. Sort stable in float64. Strictly increasing result.

  Step 2: For each measure, assign weight 0 to support values absent from
    that measure. Construct cumulative weight functions F_base and F_eps
    by sequential forward accumulation:
      F(x_1) = weight(x_1)
      F(x_k) = F(x_{k-1}) + weight(x_k),  k = 2 to M
    No pre-zero element at x_0.

  Step 3: W1 = sum_{k=1}^{M-1} |F_base(x_k) - F_eps(x_k)| * (x_{k+1} - x_k)

Constraints inherited from Step 2:
  - All reductions by explicit Python for-loops (no np.sum, no np.cumsum)
  - All scalar values cast to numpy.float64 before use
  - CDF iteration over sorted union array only (no dict key iteration)
  - No library Wasserstein implementation

---

## 10. Secondary metrics

For each epsilon, computed descriptively (not for classification):
  |mu_w - mu_w(epsilon)|        [weighted mean shift, km/s]
  |sigma_w^2 - sigma_w^2(eps)|  [weighted variance shift, (km/s)^2]
  W1 / sigma_w                  [normalized discrepancy]

where sigma_w is the weighted standard deviation under the base measure.

---

## 11. Expected pattern

Deterministic expectations:

  epsilon = 0.00: W1 = 0 up to floating-point precision.
    Expected classification: BASELINE_RECOVERED.

  epsilon > 0.00: W1 > 0 is expected.
    The response should be monotone non-decreasing with epsilon, up to
    negligible floating-point irregularity.

This is not a statistical test. It is a verification that the measurement
apparatus detects controlled measure changes.

---

## 12. Classification

For each epsilon:

  BASELINE_RECOVERED: epsilon = 0.00 and W1 < 0.01 * sigma_w
    (sanity check passed — Step 2 baseline reproduced)

  PERTURBATION_DETECTED: epsilon > 0.00 and W1 > 0 numerically
    (measure change induced pushforward divergence)

  UNEXPECTED_NULL: epsilon > 0.00 and W1 = 0.0 exactly in float64
    (unexpected; investigate implementation)

  UNEXPECTED_NONMONOTONICITY: W1(epsilon_b) < 0.99 * W1(epsilon_a)
    for adjacent epsilon_a < epsilon_b in the grid
    (material reversal in monotone response; investigate)

Rationale for 0.99 threshold: at epsilon > 0, W1 will be orders of
magnitude larger than the 1e-12 floating-point floor from Steps 1-2.
An absolute tolerance would be negligible and undetectable at the expected
scale. A 1% relative decline threshold is scale-invariant and interpretable;
it flags only material reversals, not floating-point noise.

---

## 13. Kill criteria

K1: chain not extractable from zip, or any required column (1,2,10,12) non-
    finite, or original weights fail validity check (non-finite, negative,
    or sum <= 0) -> terminate; structured negative result.

K2: perturbed raw weights w_tilde_i(epsilon) non-finite or non-positive for
    any row at any epsilon -> halt execution for that epsilon; log deviation;
    continue with remaining epsilon values if any.

K3: weighted W1 computation fails or produces non-finite result for any
    epsilon -> terminate; log in DEVIATIONS.md.

K4: v_p non-finite or negative for any row -> terminate; log in DEVIATIONS.md.

K5: support mismatch or row-order corruption detected between baseline and
    perturbed runs (v_p arrays differ between epsilon evaluations) ->
    terminate; log in DEVIATIONS.md.

Warning (not kill): v_p > 1e5 km/s for any row -> log warning; continue.

---

## 14. Execution order

1. scripts/00_ingest.py  — extract chain, load cols 1/2/10/12, validate
                           weights, normalize, compute N_eff, compute v_p
                           support (once, reused for all epsilon)
2. scripts/01_perturb.py — compute rank scores f_i, generate w(epsilon)
                           for all preregistered epsilon values, validate
3. scripts/02_metrics.py — compute W1(base, eps) for each epsilon,
                           secondary metrics, classify, write RESULTS.md
4. scripts/03_figures.py — W1 vs epsilon plot, CDF comparison at
                           epsilon=0 and epsilon=0.10, outcome summary

Single-threaded. Steps may not be reordered.

---

## 15. Explicit prohibitions

No change to support points. No resampling. No refitting. No Gaussian
approximation. No adaptive epsilon selection. No post-hoc choice of
perturbation function. No additional metrics or thresholds after freeze.
No stochastic tie-breaking. No library Wasserstein implementation.
No vectorized reductions for weight sums or CDF accumulation.

---

## 16. Planned outputs

  outputs/ingest.npz              — v_p support, base weights, GM, P, e
  outputs/perturbed_weights.npz   — w(epsilon) for all epsilon
  outputs/metrics.yaml            — W1, secondary metrics, classification per epsilon
  outputs/figures/fig1_w1_vs_epsilon.pdf
  outputs/figures/fig2_cdf_comparison.pdf
  outputs/figures/fig3_outcome_summary.pdf
  RESULTS.md                      — structured result block per epsilon
  logs/artifact_hashes.yaml       — SHA256 of all output artifacts

---

## 17. Interpretation

If expected pattern observed:
  Controlled perturbations of the empirical measure induce controlled
  divergence in the pushforward distribution, confirming that measure
  change — not algebraic reparameterization — is the operative pathway
  for non-null behavior in this audit program.

If not observed, conclusion is restricted to the failure mode detected
(unexpected null, nonmonotonicity, or computation error), with no broader
astrophysical inference.

In neither case is any inference made about the astrophysical system.
This study validates the measurement apparatus, not an astrophysical claim.

---

## 18. Preregistration checklist

- [x] Research question (Section 1)
- [x] Motivation and program context (Section 2)
- [x] Data source and foreknowledge (Section 3)
- [x] Base and perturbed measure definitions (Section 4)
- [x] Perturbation function locked (Section 5)
- [x] Epsilon grid locked (Section 6)
- [x] Estimand (Section 7)
- [x] Pushforward definition (Section 8)
- [x] W1 exact algorithm (Section 9)
- [x] Secondary metrics (Section 10)
- [x] Expected pattern (Section 11)
- [x] Classification rules (Section 12)
- [x] Kill criteria K1-K5 (Section 13)
- [x] Execution order (Section 14)
- [x] Prohibitions (Section 15)
- [ ] OSF registration URL (added at freeze)
