# Decomposition of Pushforward Sensitivity by Perturbation Axis in Galactic Center Orbit Inference

Code, execution scripts, and results for the manuscript of the same title. The paper demonstrates that sensitivity of a derived astrophysical quantity (periapsis velocity) to perturbations of a weighted empirical posterior depends qualitatively on the perturbation axis—weight perturbations versus support perturbations—even when both perturbations use an identical rank-based basis and are evaluated under the same metric. All results are preregistered, deterministic, and exactly reproducible from the artifacts in this repository.

## Preregistration

Both execution steps are archived on OSF with locked protocols:

- Step 3 (weight perturbation): https://osf.io/dmpes
- Step 4 (support perturbation): https://osf.io/fkx46

OSF holds the canonical preregistration and timestamped archive. This repository provides execution scripts and accessibility.

## Repository structure

```
manuscript/          LaTeX source, figures, bibliography
step3_weight_perturbation/
  protocol/          Locked protocol (SHA-verified)
  scripts/           Execution scripts 00–03
  outputs/           Audited outputs: metrics.yaml, figures
  results/           RESULTS.md, localization_table.md
  logs/              artifact_hashes.yaml
step4_support_perturbation/
  protocol/          Locked protocol (SHA-verified)
  scripts/           Execution scripts 00, 02–05
  outputs/           Audited outputs: w1_metrics.yaml
  results/           RESULTS.md
  logs/              artifact_hashes.yaml
synthetic_demo/
  scripts/           Appendix A reproduction scripts 00–04
  outputs/           synthetic_metrics.yaml
  results/           appendix_A.md, figures A1–A2
  logs/              artifact_hashes.yaml
```

## Reproducibility

All results are deterministic given the input data. To reproduce:

**Step 3 (weight perturbation):**
```
cd step3_weight_perturbation
python scripts/00_ingest.py
python scripts/01_perturb.py
python scripts/02_metrics.py
python scripts/02b_localization.py
python scripts/03_figures.py
```

**Step 4 (support perturbation):**
```
cd step4_support_perturbation
python scripts/00_ingest.py
python scripts/02_gate_delta.py
python scripts/03_perturb_support.py
python scripts/04_metrics.py
python scripts/05_figures.py
```

**Appendix A (synthetic demonstration):**
```
cd synthetic_demo
python scripts/00_build_synthetic.py
python scripts/01_weight_axis.py
python scripts/02_support_axis.py
python scripts/03_metrics.py
python scripts/04_figures.py
```

**Manuscript figures:**
```
cd manuscript
python make_figures.py
```
Requires `../step4_support_perturbation/outputs/w1_metrics.yaml`.

## Data provenance

Input posterior samples are from the supplementary data of:

> Do, T. et al. (2019). Relativistic redshift of the star S0-2 orbiting the Galactic Center supermassive black hole. *Science*, 365, 664–668. https://doi.org/10.1126/science.aav8137

The supplementary archive `aav8137_data_s3.zip` is available from the journal. Place it at `step3_weight_perturbation/data/raw/do2019_chains/` and `step4_support_perturbation/data/raw/do2019_chains/` before running the ingest scripts.

## Dependencies

Python 3.9+, numpy, matplotlib, pyyaml. No additional packages required. All numerical algorithms are implemented directly in the scripts with no external statistical library dependencies for the core W1 computation.

Tested with: Python 3.13.11, numpy 2.4.3, matplotlib 3.10.8, pyyaml 6.0.3.

## License

Code: MIT License (see `LICENSE`).
Manuscript text: the authors retain copyright pending journal assignment.

## Citation

Manuscript submitted to MNRAS. Citation information will be updated on acceptance.
