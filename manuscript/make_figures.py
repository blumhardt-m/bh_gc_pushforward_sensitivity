#!/usr/bin/env python3
"""
make_figures.py — Manuscript figures for the pushforward sensitivity paper.

Produces:
  manuscript/figure_1_scaling.pdf     — W1 scaling contrast (main result)
  manuscript/figure_2_localization.pdf — Decile localization contrast (mechanism)

Data sources:
  Step 3 (weight axis): ../outputs/ and hard-coded audited decile fractions
    (Step 3 localization is in results/localization_table.md, not a machine-readable
    YAML; fractions are transcribed here from the audited table exactly.)
  Step 4 (support axis): ../outputs/w1_metrics.yaml

Color convention (all figures):
  Weight axis: tab:blue
  Support axis: tab:red
  Linear reference: gray dashed
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yaml

# ── Audited Step 3 data (weight perturbation) ─────────────────────────────────
# Source: bh_gc_orbit_measure_perturbation_audit/outputs/metrics.yaml
#         bh_gc_orbit_measure_perturbation_audit/results/localization_table.md
# OSF: osf.io/dmpes

STEP3_EPS  = [0.00,      0.01,     0.05,     0.10    ]
STEP3_W1   = [0.0,       0.038649, 0.192844, 0.384693]   # km/s

# Decile fractions at ε = 0.10 (representative; identical to 3 d.p. for ε=0.01,0.05)
# From audited localization_table.md, column "Fraction of W1", ε=0.10 block.
STEP3_DECILE_FRACS_EPS_010 = [
    0.0905, 0.0984, 0.0958, 0.0988, 0.1017,
    0.0997, 0.0987, 0.1035, 0.1056, 0.1073,
]
STEP3_DECILE_FRACS_EPS_005 = [
    0.0905, 0.0984, 0.0958, 0.0988, 0.1017,
    0.0997, 0.0987, 0.1035, 0.1056, 0.1073,
]
STEP3_DECILE_FRACS_EPS_001 = [
    0.0905, 0.0984, 0.0958, 0.0988, 0.1017,
    0.0997, 0.0987, 0.1035, 0.1056, 0.1073,
]

DECILE_LABELS = [f"D{d+1}" for d in range(10)]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def append_artifact_hash(path: Path, hash_log_file: Path, repo_root: Path) -> None:
    artifact_hash = sha256_file(path)
    existing: dict = {}
    if hash_log_file.exists():
        with hash_log_file.open("r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f)
            if isinstance(loaded, dict):
                existing = loaded
    existing[str(path.resolve().relative_to(repo_root.resolve()))] = artifact_hash
    hash_log_file.parent.mkdir(parents=True, exist_ok=True)
    with hash_log_file.open("w", encoding="utf-8") as f:
        yaml.safe_dump(existing, f, sort_keys=True, allow_unicode=True)


def load_step4(repo_root: Path) -> dict:
    metrics_path = repo_root / "step4_support_perturbation" / "outputs" / "w1_metrics.yaml"
    with metrics_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ── Figure 1: W1 scaling contrast ─────────────────────────────────────────────

def figure_1(step4: dict, out_path: Path) -> None:
    delta_vals  = [0.000, 0.010, 0.050, 0.090]
    step4_w1    = [step4["w1_values_km_s"][f"{d:.3f}"] for d in delta_vals]
    ratio_s4    = step4["h4a"]["ratio"]

    # Linear reference for each panel: anchored at smallest nonzero amplitude
    # Weight axis: slope = W1(0.01) / 0.01
    eps_nonzero  = [e for e in STEP3_EPS if e > 0]
    w1_01        = STEP3_W1[1]                           # W1 at eps=0.01
    w1_ref_w     = [w1_01 * (e / eps_nonzero[0]) for e in STEP3_EPS]

    # Support axis: slope = W1(0.010) / 0.010
    delta_nonzero = [d for d in delta_vals if d > 0]
    w1_d01        = step4_w1[1]                          # W1 at delta=0.010
    w1_ref_s      = [w1_d01 * (d / delta_nonzero[0]) if d > 0 else 0.0
                     for d in delta_vals]

    # Step 3 ratio
    ratio_s3 = STEP3_W1[-1] / STEP3_W1[1]               # W1(0.10) / W1(0.01)

    fig, axes = plt.subplots(1, 2, figsize=(8.5, 3.8))

    # Panel A — Weight axis
    ax = axes[0]
    ax.plot(STEP3_EPS, w1_ref_w, color="gray", lw=1.0, ls="--",
            label="Linear reference")
    ax.plot(STEP3_EPS, STEP3_W1,  color="tab:blue", lw=1.5, ls="-",
            marker="o", ms=6, label="Observed")
    ax.set_xlabel("Weight perturbation amplitude $\\varepsilon$", fontsize=10)
    ax.set_ylabel("$W_1$ (km/s)", fontsize=10)
    ax.set_title("Panel A — Weight perturbation", fontsize=10)
    ax.set_xlim(-0.003, 0.105)
    ax.set_ylim(bottom=0)
    ax.text(0.97, 0.12,
            f"Linear scaling\n$W_1(0.10)/W_1(0.01) = {ratio_s3:.1f}$",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=8.5, color="tab:blue",
            bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="tab:blue", alpha=0.8))
    ax.legend(fontsize=8, loc="upper left")

    # Panel B — Support axis
    ax = axes[1]
    ax.plot(delta_vals, w1_ref_s, color="gray", lw=1.0, ls="--",
            label="Linear reference")
    ax.plot(delta_vals, step4_w1, color="tab:red", lw=1.5, ls="-",
            marker="o", ms=6, label="Observed")
    ax.set_xlabel("Support perturbation amplitude $\\delta$", fontsize=10)
    ax.set_ylabel("$W_1$ (km/s)", fontsize=10)
    ax.set_title("Panel B — Support perturbation", fontsize=10)
    ax.set_xlim(-0.003, 0.095)
    ax.set_ylim(bottom=0)
    ax.text(0.97, 0.12,
            f"Super-linear scaling\n$W_1(0.090)/W_1(0.010) = {ratio_s4:.1f}$",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=8.5, color="tab:red",
            bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="tab:red", alpha=0.8))
    ax.legend(fontsize=8, loc="upper left")

    fig.suptitle(
        "Figure 1. Scaling of weighted $W_1$ under orthogonal perturbation axes.",
        fontsize=10, y=1.01,
    )
    fig.tight_layout()
    fig.savefig(out_path, format="pdf", bbox_inches="tight")
    plt.close(fig)


# ── Figure 2: Decile localization contrast ─────────────────────────────────────

def figure_2(step4: dict, out_path: Path) -> None:
    fracs_s4_010 = step4["decile_fractions"]["0.010"]
    fracs_s4_050 = step4["decile_fractions"]["0.050"]
    fracs_s4_090 = step4["decile_fractions"]["0.090"]

    x = list(range(10))

    # Common y-axis ceiling across both panels
    y_max = max(
        max(STEP3_DECILE_FRACS_EPS_010),
        max(fracs_s4_090),
    )
    y_top = min(1.0, y_max * 1.08)

    fig, axes = plt.subplots(1, 2, figsize=(8.5, 4.2), sharey=False)

    # Panel A — Weight axis (ε = 0.10, representative)
    ax = axes[0]
    ax.bar(x, STEP3_DECILE_FRACS_EPS_010, color="tab:blue", alpha=0.85,
           edgecolor="white", linewidth=0.4, label="$\\varepsilon = 0.10$")
    ax.axhline(0.10, color="gray", lw=0.9, ls="--", label="Uniform (10%)")
    ax.set_xticks(x)
    ax.set_xticklabels(DECILE_LABELS, fontsize=8)
    ax.set_xlabel("Decile (D1 = lowest $v_p$, D10 = highest)", fontsize=10)
    ax.set_ylabel("Fraction of total $W_1$", fontsize=10)
    ax.set_ylim(0, y_top)
    ax.set_title("Panel A — Weight perturbation", fontsize=10)
    ax.text(0.50, 0.90, "Approximately uniform contribution",
            transform=ax.transAxes, ha="center", va="top",
            fontsize=8.5, color="tab:blue",
            bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="tab:blue", alpha=0.8))
    ax.legend(fontsize=8, loc="upper left")

    # Panel B — Support axis (δ = 0.090 primary; lighter for δ = 0.010, 0.050)
    ax = axes[1]
    ax.bar(x, fracs_s4_010, color="tab:red", alpha=0.25,
           edgecolor="none", label="$\\delta = 0.010$")
    ax.bar(x, fracs_s4_050, color="tab:red", alpha=0.45,
           edgecolor="none", label="$\\delta = 0.050$")
    ax.bar(x, fracs_s4_090, color="tab:red", alpha=0.85,
           edgecolor="white", linewidth=0.4, label="$\\delta = 0.090$")
    ax.axhline(0.10, color="gray", lw=0.9, ls="--")
    ax.set_xticks(x)
    ax.set_xticklabels(DECILE_LABELS, fontsize=8)
    ax.set_xlabel("Decile (D1 = lowest $v_p$, D10 = highest)", fontsize=10)
    ax.set_ylabel("Fraction of total $W_1$", fontsize=10)
    ax.set_ylim(0, y_top)
    ax.set_title("Panel B — Support perturbation", fontsize=10)
    d10_val = fracs_s4_090[9]
    ax.text(0.50, 0.90,
            f"Upper-tail concentration\nD10 = {d10_val:.2f} at $\\delta = 0.090$",
            transform=ax.transAxes, ha="center", va="top",
            fontsize=8.5, color="tab:red",
            bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="tab:red", alpha=0.8))
    ax.legend(fontsize=8, loc="upper left")

    fig.suptitle(
        "Figure 2. Decile localization of $W_1$ contributions.",
        fontsize=10, y=1.01,
    )
    fig.tight_layout()
    fig.savefig(out_path, format="pdf", bbox_inches="tight")
    plt.close(fig)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    repo_root    = Path(__file__).resolve().parent.parent
    ms_dir       = repo_root / "manuscript"
    hash_log     = ms_dir / "artifact_hashes.yaml"

    step4 = load_step4(repo_root)

    fp1 = ms_dir / "figure_1_scaling.pdf"
    figure_1(step4, fp1)
    append_artifact_hash(fp1, hash_log, repo_root)
    print(f"wrote {fp1.name}  SHA-256: {sha256_file(fp1)}")

    fp2 = ms_dir / "figure_2_localization.pdf"
    figure_2(step4, fp2)
    append_artifact_hash(fp2, hash_log, repo_root)
    print(f"wrote {fp2.name}  SHA-256: {sha256_file(fp2)}")

    print("OK — manuscript figures complete")


if __name__ == "__main__":
    main()
