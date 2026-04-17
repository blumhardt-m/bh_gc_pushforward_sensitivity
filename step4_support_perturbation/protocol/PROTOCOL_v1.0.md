# PROTOCOL v1.0 — Step 4: Support Perturbation Audit

**Project:** bh_gc_orbit_support_perturbation_audit  
**Step:** 4 of the BH GC Orbit Pushforward Invariance Audit program  
**Parent study:** bh_gc_orbit_measure_perturbation_audit (Step 3, osf.io/dmpes)  
**Proposed title:** "Pushforward Sensitivity Under Support Deformation: Structural Contrast with Measure Reweighting"  
**Status:** FROZEN_REGISTERED (pending OSF confirmation)  
**Protocol version:** 1.0  

---

## Section 1 — Scientific Objective

Step 3 characterized the weight-perturbation axis: rank-linear reweighting on fixed
support produces linear W1 scaling in ε and globally distributed CDF deformation.
This protocol tests the orthogonal axis: deterministic support deformation at fixed
weights.

The primary object is the structural contrast between the two perturbation types.

Preregistered hypotheses:

- **H4a:** Nonlinear scaling — FALSIFIED if W1(0.090)/W1(0.010) ∈ [8.5, 9.5]; CONFIRMED otherwise
- **H4b:** Per-decile W1 fractions are non-uniform (any fraction outside [0.09, 0.11])
- **H4c:** D10 fraction ≥ 15% for at least one δ > 0

---

## Section 2 — Data Source

Do et al. (2019, *Science* 365, 664–668, doi:10.1126/science.aav8137), supplementary
archive `aav8137_data_s3.zip`, file `chains_redshift.txt`.

Archive SHA-256: `8397176cb6e996c21f64acadc77f470cf5412335a076a8e565e530ff52eb986a`

Columns loaded (zero-indexed): 0 (weight), 1 (GM/M☉ × 10⁶), 9 (period, years), 11 (eccentricity)  
Expected row count: 33,079  
No preprocessing beyond what is specified here.

---

## Section 3 — Physical Constants

All constants fixed at the values used in Steps 1–3. No deviation permitted.

| Symbol  | Value                            | Units          | Source   |
|---------|----------------------------------|----------------|----------|
| GM_SUN  | 1.32712440018 × 10²⁰             | m³ s⁻²         | IAU 2012 |
| YR_S    | 365.25 × 24 × 3600 = 31,557,600  | s yr⁻¹         | Julian year |
| π       | math.pi (Python standard library) | —             | —        |

---

## Section 4 — Weight Normalization (Ingestion)

Weights are loaded from column 0 and normalized by sequential accumulation in
a Python for-loop. No `np.sum`, `np.cumsum`, `np.dot`, or vectorized reduction.

```
raw_sum = 0.0  (float64)
for i in range(N):
    raw_sum += float64(weights_raw[i])
for i in range(N):
    weights_norm[i] = float64(weights_raw[i] / raw_sum)
```

K1 kill: `raw_sum` non-finite or ≤ 0; any `weights_norm[i]` non-finite or < 0.

---

## Section 5 — Rank Score Definition (Locked)

The perturbation amplitude per sample is the centered rank score of eccentricity:

```
r_i  = stable ascending rank of e_i  (rank ∈ {1, …, N}, ties by row order)
f_i  = (r_i − (N+1)/2) / ((N−1)/2)
```

Computed as:
```python
sort_indices = np.argsort(e_chain, kind="stable")
for k in range(N):
    row_idx = int(sort_indices[k])
    rank[row_idx] = float64(k + 1)
mid        = float64((N + 1) / 2)
half_range = float64((N - 1) / 2)
for i in range(N):
    f[i] = (float64(rank[i]) - mid) / half_range
```

Properties: f_i ∈ [−1, 1]; Σ w_i f_i ≈ 0 under the base measure.

This rank score is identical to the Step 3 perturbation basis. The symmetry
is deliberate (isolates weight-versus-support as the sole axis difference)
but does not carry through to the functional level (see Section 7).

---

## Section 6 — Domain Gate (Preregistered)

The perturbed eccentricity must satisfy ẽ_i(δ) ∈ (0, 1) for all i at all δ on the grid.

The data-derived bound is:

```
δ_max = min_i { min( (1 − e_i)/|f_i|,  e_i/|f_i| ) }   for |f_i| > 0
```

Precomputed from the actual Do+2019 posterior (N = 33,079):

| Quantity             | Value    |
|----------------------|----------|
| δ_max                | 0.10776  |
| Binding row          | i = 190  |
| Binding e_i          | 0.89224  |
| Binding f_i          | +1.000   |
| Binding constraint   | (1 − 0.89224) / 1.000 = 0.10776 |
| Authorized ceiling   | 0.9 × δ_max = 0.09698 |

**Gate requirement:** max(δ_grid) < 0.09698.

Script `02_gate_delta.py` MUST verify this gate on every execution:

1. Recompute δ_max from chain data; verify |δ_max_computed − 0.10776| < 1×10⁻⁴.
   If this sanity check fails, abort K2 and append to DEVIATIONS.md.
   (The chain is deterministic; a mismatch indicates data or code corruption.)
2. Check max(δ_grid) < ceiling. If this fails, abort K2.
3. Write gate manifest to `logs/gate_delta_manifest.yaml` (pass or fail).
   `03_perturb_support.py` reads this manifest and refuses to execute unless
   `gate_passed: true` is recorded.

If the gate fails, the run is aborted with K2 and logged to DEVIATIONS.md.

---

## Section 7 — Support Perturbation Form

The perturbation modifies eccentricity at fixed weights:

```
ẽ_i(δ) = e_i + δ × f_i
```

Weights are **unchanged**: `w̃_i = w_i` for all i and all δ.

This is the orthogonal axis to Step 3, where support was fixed (`vp_i` unchanged)
and weights were modified (`w̃_i = w_i(1 + ε f_i)`). The input-level symmetry
(same rank score f_i, same perturbation structure) is intentional. The functional
asymmetry (linear v_p response in Step 3 vs. nonlinear v_p map in Step 4) is
the scientific object.

The perturbation does NOT use any affine-dilation form (e.g., ẽ_i = e_i + δ(e_i − μ_e)).
Only the rank-score form above is authorized.

---

## Section 8 — v_p Recomputation

For each δ, recompute periapsis velocity from the perturbed eccentricity:

```
GM_SI_i = GM_chain_i × 1e6 × GM_SUN          (m³ s⁻²)
P_s_i   = P_chain_i × YR_S                    (s)
a_m_i   = (GM_SI_i × P_s_i² / (4π²))^(1/3)   (m)
vp(δ)_i = sqrt(GM_SI_i × (1 + ẽ_i(δ)) / (a_m_i × (1 − ẽ_i(δ)))) / 1000   (km/s)
```

Computed in an explicit Python for-loop (no vectorization). `GM_SI_i` and `a_m_i`
depend only on GM and P, which are unchanged; both are computed once and cached as
arrays before the δ loop. The ẽ_i(δ) term is substituted fresh for each δ.
The caching is an implementation optimization only; results must be identical to
evaluating the formula from scratch per δ.

K4 kill: any `vp(δ)_i` non-finite or < 0.

---

## Section 9 — W1 Computation

Primary metric: W1(μ_0, μ_δ), where:

- μ_0 = Σ w_i δ(vp_i)   (base pushforward; vp_i from original e_i)
- μ_δ = Σ w_i δ(vp(δ)_i) (perturbed pushforward; same weights, perturbed support)

Algorithm (identical to Steps 1–3):

1. **Aggregate duplicates.** For each distribution, sum weights of identical
   support points by exact float64 key equality (dict keyed by `np.float64(vp[i])`).

2. **Sorted union support.** Form the union of all support points from both
   distributions. Sort ascending into array `union_support`.

3. **Sequential CDF accumulation.** For each distribution, build CDF arrays
   `F_base`, `F_delta` by sequential for-loop:
   ```python
   F_base[0] = w_union_base[0]
   for k in range(1, M):
       F_base[k] = F_base[k-1] + w_union_base[k]
   ```
   (and analogously for F_delta)

4. **W1 summation.** Sequential for-loop:
   ```python
   w1 = float64(0.0)
   for k in range(M - 1):
       w1 += abs(float64(F_base[k]) - float64(F_delta[k])) \
             * (float64(union_support[k+1]) - float64(union_support[k]))
   ```

No library W1 implementation (scipy.stats.wasserstein_distance or similar) is
permitted. No `np.sum`, `np.cumsum`, or vectorized reduction.

K3 kill: W1 result non-finite.

---

## Section 10 — Decile Localization (Preregistered Primary Diagnostic)

W1 is the primary metric (Section 9). Decile localization fractions are
preregistered primary diagnostics: they drive H4b and H4c classification directly.
Unlike Step 3 (where localization was supplementary), this diagnostic is specified
in the locked protocol and its results are binding on hypothesis classification.

Algorithm:

1. Decile boundaries: quantile edges from base CDF (F_base = 0.1k for k = 1…9).
   Edges computed by `find_quantile_edge`: first support point where F_base ≥ q.

2. Per-decile W1 contribution: sum of `|F_base[k] − F_delta[k]| × Δx` over all
   intervals whose left endpoint falls in that decile.

3. Fraction: per-decile contribution divided by total W1.

Decile boundaries are fixed by the BASE distribution (δ = 0 vp values) and do
not change across δ values.

Computed in explicit Python for-loops. All arithmetic in float64.

---

## Section 11 — Secondary Metric: Directional Shift

For each δ, compute the signed weighted mean shift:

```
μ_w(δ)  = Σ w_i × vp(δ)_i   (sequential for-loop, float64)
Δμ(δ)   = μ_w(δ) − μ_w(0)
```

This metric is descriptive: it does not affect H4a–H4c classifications. It is
reported as-is regardless of sign or magnitude.

---

## Section 12 — Kill Criteria

| Code | Condition | Action |
|------|-----------|--------|
| K1   | Chain non-extractable; invalid or non-positive weights; row count mismatch | Abort; write RESULTS.md block; append DEVIATIONS.md |
| K2   | ẽ_i(δ) ∉ (0, 1) for any i at any δ; gate ceiling violated | Abort for that δ; write RESULTS.md block |
| K3   | W1 result non-finite | Abort; write RESULTS.md block |
| K4   | vp(δ)_i non-finite or < 0 for any i, δ | Abort; write RESULTS.md block |
| K5   | Union support length inconsistent with input sizes | Abort; write RESULTS.md block |

K2 and K4 aborts are per-δ: halt the current δ and log, do not continue to
subsequent δ values.

---

## Section 13 — Classification Rules

**Per-δ classification:**

| Condition | Classification |
|-----------|----------------|
| δ = 0, W1 < 1×10⁻⁹ km/s | BASELINE_RECOVERED |
| δ = 0, W1 ≥ 1×10⁻⁹ km/s | UNEXPECTED_BASELINE |
| δ > 0, W1 ≥ 1×10⁻⁹ km/s | PERTURBATION_DETECTED |
| δ > 0, W1 < 1×10⁻⁹ km/s | BELOW_DETECTION_THRESHOLD |

**Hypothesis classifications:**

| Hypothesis | Falsification condition | Classification |
|------------|-------------------------|----------------|
| H4a | W1(0.090)/W1(0.010) ∈ [8.5, 9.5] | FALSIFIED; otherwise CONFIRMED |
| H4b | All decile fractions ∈ [0.09, 0.11] at all δ > 0 | FALSIFIED; otherwise CONFIRMED |
| H4c | D10 fraction < 0.15 at all δ > 0 | FALSIFIED; otherwise CONFIRMED |

All classifications are independent. No post-hoc reclassification is permitted.

**Monotonicity check:** Flag UNEXPECTED_NONMONOTONICITY if W1(δ_b) < 0.99 × W1(δ_a)
for any adjacent pair δ_a < δ_b. This does not abort execution but is logged and
reported.

---

## Section 14 — Script Sequence

| Script | Purpose |
|--------|---------|
| `00_ingest.py` | Load chain, validate K1, normalize weights, compute v_p (from original e), save ingest.npz |
| `02_gate_delta.py` | Compute rank scores f_i; verify δ_max gate; abort if gate fails |
| `03_perturb_support.py` | For each δ: compute ẽ_i(δ), recompute vp(δ), validate K2/K4, save perturbed_support.npz |
| `04_metrics.py` | Compute W1, decile fractions, Δμ per δ; classify H4a–H4c; write RESULTS.md |
| `05_figures.py` | Produce PDFs: W1 vs δ, CDF comparison, decile bar chart, text summary |

**Artifact contracts (locked):**

| File | Description |
|------|-------------|
| `outputs/ingest.npz` | Keys: `weights_raw`, `weights_norm`, `gm_chain`, `p_chain`, `e_chain`, `vp` |
| `logs/gate_delta_manifest.yaml` | Gate pass/fail, δ_max, binding row, ceiling, grid_max |
| `outputs/perturbed_support.npz` | All δ values in one file. Keys: `vp_delta_0_000`, `vp_delta_0_010`, `vp_delta_0_050`, `vp_delta_0_090` (v_p arrays, km/s, float64); `e_delta_0_000`, `e_delta_0_010`, `e_delta_0_050`, `e_delta_0_090` (perturbed eccentricity arrays, float64); `weights_norm` (unchanged base weights, float64); `rank_scores_f` (f_i array, float64); `delta_grid` (1-D float64 array, length 4, values [0.000, 0.010, 0.050, 0.090]) |

Scripts 04 and 05 are not provided in this draft; their interfaces are specified
above. Scripts must be finalized and their SHAs logged in artifact_hashes.yaml
before execution.

---

## Section 15 — Execution Constraints (Hard)

1. Single execution pass. No iteration, reruns, or parameter adjustment after
   data are opened.

2. δ grid locked at {0.00, 0.010, 0.050, 0.090}. No additional values added.

3. Perturbation form locked: ẽ_i(δ) = e_i + δ × f_i. No substitution.

4. All aggregates (weight sums, CDF values, W1, means) computed by explicit
   Python for-loops in float64. No `np.sum`, `np.cumsum`, `np.dot`, or
   equivalent vectorized reduction.

5. No additional metrics, diagnostics, or post-hoc analyses after protocol freeze,
   except as explicitly listed in Sections 10 and 11.

6. No expression tree optimization, symbolic algebra, or algebraic simplification
   is permitted for any computation in this protocol. Specifically:
   - Rank score f_i (Section 5): assign via explicit argsort + two for-loops.
   - Perturbed eccentricity ẽ_i(δ) (Section 7): evaluate as `e_i + delta * f_i` per row.
   - K2 domain check (Section 12): test `0 < e_pert[i] < 1` per row in a for-loop.
   - v_p recomputation (Section 8): evaluate the square-root formula per row; do not
     factor, rearrange, or substitute the expression symbolically.
   Each must be evaluated as written in its respective section.

7. H4a–H4c thresholds (ratio band [8.5, 9.5], uniform band [0.09, 0.11], D10
   threshold 0.15) are locked here. They may not be adjusted after protocol freeze.

---

## Section 16 — State Transitions

| State | Condition |
|-------|-----------|
| DRAFT | Before OSF preregistration |
| FROZEN_REGISTERED | After OSF registration with SHA-256 confirmation |
| EXECUTION_COMPLETE | After single execution; data_opened = true |

Scripts check `STATE.yaml` status at startup. Execution requires FROZEN_REGISTERED.
RESULTS.md is appended (not overwritten) by scripts 04 and 05.

---

## Section 17 — Artifact Logging

Each output file's SHA-256 is appended to `logs/artifact_hashes.yaml` immediately
after the file is written, using the same `append_artifact_hash` function pattern
as Steps 1–3. Any deviation from expected SHA values is logged to DEVIATIONS.md.

---

## Section 18 — Governance

- This protocol is frozen at SHA-256 lock (to be computed upon finalization).
- DEVIATIONS.md records any departure from this protocol. No deviation is
  silently corrected.
- RESULTS.md records a structured block per execution, including all W1 values,
  classifications, and H4a–H4c outcomes.
- No result is excluded from reporting. If a kill criterion fires, that kill
  is reported as the result.
- Post-hoc reclassification is prohibited. Report exact observed values.
