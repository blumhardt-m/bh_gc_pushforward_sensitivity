# RESULTS.md
No entries before OSF preregistration.

## Result 001 — bh_gc_orbit_measure_perturbation_audit

Date: 2026-04-16
Protocol SHA: 9dbea01a2e81ff4b21e8c75e15ec73c10d96dfdf69495f6534d22b93e4102fe8
OSF: https://osf.io/dmpes

Base measure: mu_w = 7603.012888 km/s, sigma_w = 29.817867 km/s

eps=0.00: BASELINE_RECOVERED
  W1           = 4.995999e-13 km/s
  W1/sigma_w   = 1.675505e-14
  mean_diff    = 8.185452e-12 km/s
  var_diff     = 6.480150e-12 (km/s)^2

eps=0.01: PERTURBATION_DETECTED
  W1           = 3.864880e-02 km/s
  W1/sigma_w   = 1.296163e-03
  mean_diff    = 3.864880e-02 km/s
  var_diff     = 9.691978e-02 (km/s)^2

eps=0.05: PERTURBATION_DETECTED
  W1           = 1.928441e-01 km/s
  W1/sigma_w   = 6.467402e-03
  mean_diff    = 1.928441e-01 km/s
  var_diff     = 5.133318e-01 (km/s)^2

eps=0.10: PERTURBATION_DETECTED
  W1           = 3.846931e-01 km/s
  W1/sigma_w   = 1.290143e-02
  mean_diff    = 3.846931e-01 km/s
  var_diff     = 1.097818e+00 (km/s)^2

Interpretation: Controlled perturbations of the empirical measure induce controlled divergence in the pushforward distribution, confirming that measure change — not algebraic reparameterization — is the operative pathway for non-null behavior in this audit program.
