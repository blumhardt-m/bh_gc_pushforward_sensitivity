# Appendix A: Minimal synthetic demonstration of axis-dependent pushforward regimes

## A.1 Design

A deterministic grid $e_i \in [0.80, 0.95]$ ($N = 10{,}000$) with uniform weights
$w_i = 1/N$ was constructed. The same rank-based perturbation basis $f_i$ as in the
main audit was applied:

$$f_i = \frac{r_i - (N+1)/2}{(N-1)/2}$$

where $r_i$ is the stable ascending rank of $e_i$. The pushforward map was defined as

$$v(e) = \sqrt{\frac{1+e}{1-e}}$$

which preserves the same tail-amplifying nonlinearity as the astrophysical
periapsis-velocity transformation. Weight perturbations at fixed support and support
perturbations at fixed measure were applied using the same axis logic as in Steps 3
and 4 of the main audit. W1 distances were computed using the same discrete-measure
algorithm: exact support aggregation, sorted union, sequential CDF accumulation, and
interval integration of $|F_0 - F_\delta|$. Decile localization thresholds are
computed once from the baseline distribution and held fixed across all perturbations,
ensuring that localization differences are not induced by perturbation-dependent
rebinning.

## A.2 Results

| Axis | Ratio (W1$_\text{max}$ / W1$_\text{min positive}$) | D10 range | Regime |
|------|------|------|------|
| Weight | 10.00 | $\approx 0.07$ | linear, broadly distributed |
| Support | 15.75 | 0.44 – 0.76 | super-linear, upper-tail concentrated |

Both perturbation classes use the same rank-based basis $f_i$ and identical W1
estimation, so the perturbation axis (weights versus support) is the only structural
difference between the two conditions.

The weight-axis ratio of 10.00 equals the amplitude ratio $\varepsilon_\text{max} /
\varepsilon_\text{min} = 0.10 / 0.01$, confirming exact linearity. The support-axis
ratio of 15.75 exceeds this by a factor of 1.58, indicating super-linear scaling.
Decile localization fractions (D10) are flat at $\approx 7\%$ across all weight-axis
perturbation levels, consistent with broadly distributed divergence. Under support
perturbation, D10 rises from 0.44 to 0.76 as $\delta$ increases, reflecting
concentration of W1 mass in the highest-velocity bin.

## A.3 Interpretation

A minimal synthetic weighted empirical system reproduces the same qualitative contrast
observed in the Galactic Center posterior: linear, broadly distributed response under
weight perturbation and super-linear, upper-tail–concentrated response under support
perturbation. Because the synthetic construction removes dataset-specific posterior
structure — no observational noise, no astrophysical nuisance parameters, no
covariance geometry — this result is consistent with the interpretation that the
observed regime contrast arises from the geometry of the pushforward map under nonlinear transformation rather than
from idiosyncratic features of the empirical sample. The synthetic demonstration does
not constitute an independent audited result and is included only as interpretive
support for the structural mechanism identified in the main analysis.

---

*Figure A1.* Synthetic W1 scaling under orthogonal perturbation axes. Weight
perturbations produce near-linear response, whereas support perturbations produce
super-linear response under the same rank-based perturbation basis.

*Figure A2.* Synthetic decile localization fractions. Weight perturbations produce
broadly distributed W1 contributions ($\text{D10} \approx 0.07$), whereas support
perturbations concentrate divergence in the upper tail ($\text{D10} = 0.44$–$0.76$).
