#!/usr/bin/env python3
"""
04_figures.py — Synthetic Demo

Produce PDFs from synthetic_metrics.yaml.
  results/figure_A1_w1_scaling.pdf    — W1 vs amplitude, both axes
  results/figure_A2_decile_localization.pdf — D10 contrast, both axes
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yaml


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


def main() -> None:
    repo_root   = Path(__file__).resolve().parent.parent
    results_dir = repo_root / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    metrics = yaml.safe_load(
        (repo_root / "outputs" / "synthetic_metrics.yaml").read_text(encoding="utf-8")
    )
    weight_rows  = metrics["weight_rows"]
    support_rows = metrics["support_rows"]
    w_ratio      = metrics["weight_ratio"]
    s_ratio      = metrics["support_ratio"]

    w_amps  = [r["amp"] for r in weight_rows]
    w_w1    = [r["w1"]  for r in weight_rows]
    s_amps  = [r["amp"] for r in support_rows]
    s_w1    = [r["w1"]  for r in support_rows]

    hash_log = repo_root / "logs" / "artifact_hashes.yaml"

    # ── Figure A1: W1 scaling (one panel per axis) ───────────────────────────

    fig, axes = plt.subplots(1, 2, figsize=(9, 4))

    # Weight axis
    ax = axes[0]
    pos_amp = [a for a in w_amps if a > 0]
    w1_ref  = [w_w1[1] * (a / pos_amp[0]) for a in w_amps]   # linear ref from first nonzero
    ax.plot(w_amps, w1_ref,   "k--", lw=1,   label="Linear reference")
    ax.plot(w_amps, w_w1,     "o-",  lw=1.5, ms=6, color="tab:blue",
            label=f"Observed  (ratio={w_ratio:.2f})")
    ax.set_xlabel("Weight-axis amplitude ε")
    ax.set_ylabel("W1")
    ax.set_title("Weight axis: W1 vs ε")
    ax.legend(fontsize=8)
    ax.set_ylim(bottom=0)

    # Support axis
    ax = axes[1]
    pos_s = [a for a in s_amps if a > 0]
    s_ref = [s_w1[1] * (a / pos_s[0]) for a in s_amps]   # linear ref
    ax.plot(s_amps, s_ref,  "k--", lw=1,   label="Linear reference")
    ax.plot(s_amps, s_w1,   "o-",  lw=1.5, ms=6, color="tab:red",
            label=f"Observed  (ratio={s_ratio:.2f})")
    ax.set_xlabel("Support-axis amplitude δ")
    ax.set_ylabel("W1")
    ax.set_title("Support axis: W1 vs δ")
    ax.legend(fontsize=8)
    ax.set_ylim(bottom=0)

    fig.suptitle(
        "Figure A1. Synthetic W1 scaling under orthogonal perturbation axes",
        fontsize=10,
    )
    fig.tight_layout()
    fp1 = results_dir / "figure_A1_w1_scaling.pdf"
    fig.savefig(fp1, format="pdf")
    plt.close(fig)
    append_artifact_hash(fp1, hash_log, repo_root)
    print(f"wrote {fp1.name}  SHA-256: {sha256_file(fp1)}")

    # ── Figure A2: D10 decile contrast ───────────────────────────────────────

    w_d10 = [r["d10"] for r in weight_rows]
    s_d10 = [r["d10"] for r in support_rows]

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(w_amps, w_d10, "o-", lw=1.5, ms=6, color="tab:blue",  label="Weight axis")
    ax.plot(s_amps, s_d10, "o-", lw=1.5, ms=6, color="tab:red",   label="Support axis")
    ax.axhline(0.10, color="k",         lw=0.8, ls="--", label="Uniform baseline (0.10)")
    ax.axhline(0.15, color="firebrick", lw=0.8, ls=":",  label="H4c threshold (0.15)")
    ax.set_xlabel("Perturbation amplitude")
    ax.set_ylabel("D10 fraction of W1")
    ax.set_title(
        "Figure A2. Synthetic decile localization — D10 fraction\n"
        "Weight axis: broadly distributed.  Support axis: upper-tail concentrated."
    )
    ax.legend(fontsize=8)
    fig.tight_layout()
    fp2 = results_dir / "figure_A2_decile_localization.pdf"
    fig.savefig(fp2, format="pdf")
    plt.close(fig)
    append_artifact_hash(fp2, hash_log, repo_root)
    print(f"wrote {fp2.name}  SHA-256: {sha256_file(fp2)}")

    print("OK — synthetic figures complete")


if __name__ == "__main__":
    main()
