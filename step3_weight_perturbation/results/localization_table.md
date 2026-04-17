# W1 Contribution Localization by v_p Decile

**Supplementary diagnostic — bh_gc_orbit_measure_perturbation_audit (Step 3)**  
Decile boundaries defined by base-CDF quantiles (F_base = 0.1k for k=1..9).  
Per-decile W1 contribution = sum of |F_base − F_eps| × Δx over intervals in decile.  
All arithmetic in float64, explicit loops.

## Structural Interpretation

For ε > 0, decile fractions range 9.1–10.7% against a 10.0% uniform baseline,
with a slight monotone gradient from D1 (low v_p) to D10 (high v_p). Critically,
the per-decile fractions are identical to three decimal places across all three
nonzero ε values (0.01, 0.05, 0.10). This ε-invariance of the fractional
distribution is the signature of an **approximately affine deformation of the
cumulative distribution**: the CDF difference F_base(x) − F_ε(x) scales as a
nearly constant multiple of ε at every quantile level. Equivalently, the
perturbation induces a coherent, distributed shift of probability mass across the
entire support rather than concentrating transport in any particular region.

The slight upward gradient (D1: 9.1% → D10: 10.7%) reflects the eccentricity
basis of the perturbation: tilting weight toward high-e samples shifts the CDF
slightly more in the upper tail, where v_p is largest. This gradient is small
(~1.6 percentage points over the full support range) and does not qualify as
localized in any meaningful sense.

**Consequence for artifact claims:** Tail-driven artifacts under rank-linear
weight perturbation are ruled out. The W1 signal is driven by small, coherent
transport distributed across the entire support, not by mass transport over long
distances in a narrow region.

**Scope of this statement:** Applies to rank-linear weight perturbation on this
posterior only. Support deformation or non-linear weight transformations are
expected to produce different localization profiles and are not covered here.

### ε = 0.00  (W1 = 4.995999e-13 km/s)

| Decile | v_p range (km/s)              | W1 contribution (km/s) | Fraction of W1 |
|--------|-------------------------------|------------------------|----------------|
| D01    | [7288.85, 7564.58] | 1.3848e-15               | 0.0028         |
| D02    | [7564.58, 7577.89] | 2.7489e-15               | 0.0055         |
| D03    | [7577.89, 7587.19] | 3.4583e-15               | 0.0069         |
| D04    | [7587.19, 7595.34] | 5.1989e-15               | 0.0104         |
| D05    | [7595.34, 7602.88] | 6.0190e-15               | 0.0120         |
| D06    | [7602.88, 7610.35] | 7.4568e-15               | 0.0149         |
| D07    | [7610.35, 7618.31] | 8.8408e-15               | 0.0177         |
| D08    | [7618.31, 7627.90] | 1.0648e-14               | 0.0213         |
| D09    | [7627.90, 7641.41] | 1.4994e-14               | 0.0300         |
| D10    | [7641.41, 8000.91] | 4.3885e-13               | 0.8784         |

### ε = 0.01  (W1 = 3.864880e-02 km/s)

| Decile | v_p range (km/s)              | W1 contribution (km/s) | Fraction of W1 |
|--------|-------------------------------|------------------------|----------------|
| D01    | [7288.85, 7564.58] | 3.4992e-03               | 0.0905         |
| D02    | [7564.58, 7577.89] | 3.8012e-03               | 0.0984         |
| D03    | [7577.89, 7587.19] | 3.7024e-03               | 0.0958         |
| D04    | [7587.19, 7595.34] | 3.8188e-03               | 0.0988         |
| D05    | [7595.34, 7602.88] | 3.9303e-03               | 0.1017         |
| D06    | [7602.88, 7610.35] | 3.8541e-03               | 0.0997         |
| D07    | [7610.35, 7618.31] | 3.8155e-03               | 0.0987         |
| D08    | [7618.31, 7627.90] | 4.0001e-03               | 0.1035         |
| D09    | [7627.90, 7641.41] | 4.0798e-03               | 0.1056         |
| D10    | [7641.41, 8000.91] | 4.1474e-03               | 0.1073         |

### ε = 0.05  (W1 = 1.928441e-01 km/s)

| Decile | v_p range (km/s)              | W1 contribution (km/s) | Fraction of W1 |
|--------|-------------------------------|------------------------|----------------|
| D01    | [7288.85, 7564.58] | 1.7460e-02               | 0.0905         |
| D02    | [7564.58, 7577.89] | 1.8967e-02               | 0.0984         |
| D03    | [7577.89, 7587.19] | 1.8474e-02               | 0.0958         |
| D04    | [7587.19, 7595.34] | 1.9055e-02               | 0.0988         |
| D05    | [7595.34, 7602.88] | 1.9611e-02               | 0.1017         |
| D06    | [7602.88, 7610.35] | 1.9231e-02               | 0.0997         |
| D07    | [7610.35, 7618.31] | 1.9038e-02               | 0.0987         |
| D08    | [7618.31, 7627.90] | 1.9959e-02               | 0.1035         |
| D09    | [7627.90, 7641.41] | 2.0357e-02               | 0.1056         |
| D10    | [7641.41, 8000.91] | 2.0694e-02               | 0.1073         |

### ε = 0.10  (W1 = 3.846931e-01 km/s)

| Decile | v_p range (km/s)              | W1 contribution (km/s) | Fraction of W1 |
|--------|-------------------------------|------------------------|----------------|
| D01    | [7288.85, 7564.58] | 3.4829e-02               | 0.0905         |
| D02    | [7564.58, 7577.89] | 3.7835e-02               | 0.0984         |
| D03    | [7577.89, 7587.19] | 3.6852e-02               | 0.0958         |
| D04    | [7587.19, 7595.34] | 3.8011e-02               | 0.0988         |
| D05    | [7595.34, 7602.88] | 3.9121e-02               | 0.1017         |
| D06    | [7602.88, 7610.35] | 3.8362e-02               | 0.0997         |
| D07    | [7610.35, 7618.31] | 3.7978e-02               | 0.0987         |
| D08    | [7618.31, 7627.90] | 3.9815e-02               | 0.1035         |
| D09    | [7627.90, 7641.41] | 4.0609e-02               | 0.1056         |
| D10    | [7641.41, 8000.91] | 4.1281e-02               | 0.1073         |
