# RESULTS.md — BH GC Orbit Support Perturbation Audit

**Protocol SHA-256:** `e2f4db43da60cbc427b40091af7df7b587b97d7173f69eb7cc07436a606b5cc2`  
**OSF preregistration:** pending  
**Status:** pre-execution

Results will be appended here by scripts/04_metrics.py upon execution.
No entries yet.

## Step 4 Execution Results — 2026-04-17T16:39:07+00:00

**Protocol SHA-256:** `e2f4db43da60cbc427b40091af7df7b587b97d7173f69eb7cc07436a606b5cc2`  
**OSF preregistration:** https://osf.io/fkx46  
**Status:** EXECUTION_COMPLETE

### W1 values (km/s) and per-δ classification

- δ=0.000: W1 = 0.000000e+00 km/s  [BASELINE_RECOVERED]
- δ=0.010: W1 = 8.705124e+01 km/s  [PERTURBATION_DETECTED]
- δ=0.050: W1 = 5.865419e+02 km/s  [PERTURBATION_DETECTED]
- δ=0.090: W1 = 1.211723e+03 km/s  [PERTURBATION_DETECTED]

### H4a — Nonlinear scaling

- W1(0.090) / W1(0.010) = 13.919657
- Band [8.5, 9.5]: ratio_in_band = False
- **H4a: CONFIRMED**

### H4b — Non-uniform decile fractions

- Any decile fraction outside [0.09, 0.11] at δ > 0: True
- **H4b: CONFIRMED**

### H4c — D10 localization (top decile ≥ 15%)

- D10 ≥ 0.15 at any δ > 0: True  (values: δ=0.010 D10=0.5253, δ=0.050 D10=0.6422, δ=0.090 D10=0.7104)
- **H4c: CONFIRMED**

### Decile fractions (δ > 0)

- δ=0.010: D1=0.3146  D2=0.0351  D3=0.0162  D4=0.0069  D5=0.0018  D6=0.0077  D7=0.0155  D8=0.0271  D9=0.0499  D10=0.5253
- δ=0.050: D1=0.3289  D2=0.0067  D3=0.0031  D4=0.0014  D5=0.0003  D6=0.0012  D7=0.0026  D8=0.0047  D9=0.0089  D10=0.6422
- δ=0.090: D1=0.2754  D2=0.0033  D3=0.0015  D4=0.0007  D5=0.0002  D6=0.0006  D7=0.0013  D8=0.0023  D9=0.0044  D10=0.7104

### Directional shift Δμ(δ)

- δ=0.000: Δμ = 0.0000 km/s
- δ=0.010: Δμ = 22.0433 km/s
- δ=0.050: Δμ = 187.4151 km/s
- δ=0.090: Δμ = 530.7793 km/s

### Monotonicity check

- Flag: PASS
- Details: none

---

## Step 4 Figure Artifacts — 2026-04-17T16:40:07+00:00

**Protocol SHA-256:** `e2f4db43da60cbc427b40091af7df7b587b97d7173f69eb7cc07436a606b5cc2`

- `fig_w1_vs_delta.pdf`: SHA-256 `12fc756e428d89fc280b782f2477fb0c60d5bf735b315dd416512f7e2407cd25`
- `fig_cdf_comparison.pdf`: SHA-256 `e8b7aa964cb785bee73f9c3aa8e272c967cf0bb0d439d37496ced781f3490035`
- `fig_decile_fractions.pdf`: SHA-256 `9e35f0c4876ac56e42f2abe8851af2b9d9cbf80af96b2de4db05da00c0d178b4`

---
