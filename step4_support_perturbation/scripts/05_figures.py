#!/usr/bin/env python3
"""
05_figures.py — BH GC Orbit Support Perturbation Audit (Step 4)

Produce figures from preregistered results.
All PDFs only. Hashes logged to artifact_hashes.yaml. RESULTS.md appended.

Figures produced:
  figures/fig_w1_vs_delta.pdf    — W1 vs δ with linear reference line
  figures/fig_cdf_comparison.pdf — CDF overlay at each δ (4 panels)
  figures/fig_decile_fractions.pdf — Decile fraction bar chart (δ > 0)

Protocol alignment: Sections 14, 17, 18.
No new metrics, thresholds, or analyses introduced here.
"""

from __future__ import annotations

import hashlib
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import yaml


EXPECTED_PROTOCOL_SHA = "e2f4db43da60cbc427b40091af7df7b587b97d7173f69eb7cc07436a606b5cc2"
REPO_ROOT_ENV         = "BH_GC_AUDIT_REPO_ROOT"

DELTA_GRID_FLOAT: list[float] = [0.000, 0.010, 0.050, 0.090]
DELTA_LABELS: list[str]       = ["0_000", "0_010", "0_050", "0_090"]


# ── I/O helpers ───────────────────────────────────────────────────────────────

def _write_line(stream, msg: str) -> None:
    stream.write(str(msg) + "\n")
    flush = getattr(stream, "flush", None)
    if callable(flush):
        flush()

def out(msg: str) -> None:
    _write_line(sys.stdout, msg)

def err(msg: str) -> None:
    _write_line(sys.stderr, msg)

def utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


# ── Repository root resolution ────────────────────────────────────────────────

def is_repo_root(path: Path) -> bool:
    return (
        path.exists()
        and path.is_dir()
        and (path / "STATE.yaml").exists()
        and (path / "protocol" / "PROTOCOL_v1.0.md").exists()
    )


def resolve_repo_root() -> Path:
    env_root = os.environ.get(REPO_ROOT_ENV)
    if env_root:
        p = Path(env_root).expanduser().resolve()
        if p.exists():
            return p
    cwd = Path.cwd().resolve()
    for candidate in [cwd] + list(cwd.parents):
        if is_repo_root(candidate):
            return candidate
    file_obj: Optional[str] = globals().get("__file__")
    if file_obj:
        fp = Path(file_obj).resolve()
        for candidate in [fp.parent, fp.parent.parent] + list(fp.parent.parent.parents):
            if is_repo_root(candidate):
                return candidate
    raise SystemExit("could not resolve repository root")


def build_paths(repo_root: Path) -> dict[str, Path]:
    return {
        "REPO_ROOT":       repo_root,
        "INGEST_FILE":     repo_root / "outputs" / "ingest.npz",
        "PERTURB_FILE":    repo_root / "outputs" / "perturbed_support.npz",
        "METRICS_FILE":    repo_root / "outputs" / "w1_metrics.yaml",
        "FIGURES_DIR":     repo_root / "figures",
        "HASH_LOG_FILE":   repo_root / "logs" / "artifact_hashes.yaml",
        "RESULTS_FILE":    repo_root / "RESULTS.md",
    }


def append_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(text)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def append_artifact_hash(path: Path, hash_log_file: Path, repo_root: Path) -> str:
    artifact_hash = sha256_file(path)
    existing: dict = {}
    if hash_log_file.exists():
        with hash_log_file.open("r", encoding="utf-8") as fh:
            loaded = yaml.safe_load(fh)
            if isinstance(loaded, dict):
                existing = loaded
    relative_key = str(path.resolve().relative_to(repo_root.resolve()))
    existing[relative_key] = artifact_hash
    with hash_log_file.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(existing, fh, sort_keys=True, allow_unicode=True)
    return artifact_hash


# ── CDF helper ────────────────────────────────────────────────────────────────

def build_cdf(vp: np.ndarray, weights: np.ndarray):
    """
    Build (x, F) CDF arrays for plotting, consistent with W1 algorithm.
    Aggregate by exact float64 key, sort, accumulate.
    """
    agg: dict = {}
    n = vp.shape[0]
    for i in range(n):
        key = np.float64(vp[i])
        if key in agg:
            agg[key] = np.float64(agg[key] + np.float64(weights[i]))
        else:
            agg[key] = np.float64(weights[i])
    sorted_keys = sorted(float(k) for k in agg.keys())
    M = len(sorted_keys)
    x = np.empty(M, dtype=np.float64)
    F = np.empty(M, dtype=np.float64)
    for k in range(M):
        x[k] = np.float64(sorted_keys[k])
        w = agg[np.float64(sorted_keys[k])]
        F[k] = np.float64(w)
    # sequential CDF accumulation
    for k in range(1, M):
        F[k] = np.float64(F[k-1] + F[k])
    return x, F


# ── Figure 1: W1 vs delta ─────────────────────────────────────────────────────

def fig_w1_vs_delta(metrics: dict, fig_path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    deltas     = [d for d in DELTA_GRID_FLOAT if d > 0.0]
    w1_vals    = [metrics["w1_values_km_s"][f"{d:.3f}"] for d in deltas]
    w1_010     = metrics["w1_values_km_s"]["0.010"]
    ratio      = metrics["h4a"]["ratio"]
    h4a_class  = metrics["h4a"]["classification"]

    # Linear reference: W1_ref(δ) = W1(0.010) × (δ / 0.010)
    delta_arr  = np.linspace(0, 0.095, 200)
    w1_ref     = [w1_010 * (d / 0.010) if d > 0 else 0.0 for d in delta_arr]

    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.plot(delta_arr, w1_ref, "k--", lw=1, label="Linear reference (×δ/0.010 from W1(0.010))")
    ax.plot(deltas, w1_vals, "o-", color="tab:blue", lw=1.5, ms=6,
            label=f"Observed W1  (ratio={ratio:.2f})")
    ax.set_xlabel("δ (eccentricity rank perturbation)")
    ax.set_ylabel("W1(μ₀, μ_δ)  [km/s]")
    ax.set_title(
        f"Step 4 — W1 vs δ\nH4a: {h4a_class}  (ratio={ratio:.3f}, band [8.5, 9.5])"
    )
    ax.legend(fontsize=8)
    ax.set_xlim(-0.002, 0.095)
    ax.set_ylim(bottom=0)
    fig.tight_layout()
    fig.savefig(fig_path, format="pdf")
    plt.close(fig)


# ── Figure 2: CDF comparison ──────────────────────────────────────────────────

def fig_cdf_comparison(
    vp_base: np.ndarray,
    perturb_data,
    weights_norm: np.ndarray,
    fig_path: Path,
) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=(10, 7), sharex=False)
    axes_flat = [axes[0][0], axes[0][1], axes[1][0], axes[1][1]]

    x_base, F_base = build_cdf(vp_base, weights_norm)

    for ax, (delta_f, label) in zip(axes_flat, zip(DELTA_GRID_FLOAT, DELTA_LABELS)):
        vp_key   = f"vp_delta_{label}"
        vp_delta = np.asarray(perturb_data[vp_key], dtype=np.float64)
        x_d, F_d = build_cdf(vp_delta, weights_norm)

        ax.plot(x_base, F_base, "k-",        lw=1.0, label="Base (δ=0)")
        ax.plot(x_d,    F_d,    "tab:red",   lw=0.8, label=f"Perturbed (δ={delta_f:.3f})",
                alpha=0.85)
        ax.set_xlabel("v_p  [km/s]", fontsize=8)
        ax.set_ylabel("CDF",        fontsize=8)
        ax.set_title(f"δ = {delta_f:.3f}", fontsize=9)
        ax.legend(fontsize=7)
        ax.tick_params(labelsize=7)

    fig.suptitle("Step 4 — CDF comparison at each δ", fontsize=11)
    fig.tight_layout()
    fig.savefig(fig_path, format="pdf")
    plt.close(fig)


# ── Figure 3: Decile fractions ────────────────────────────────────────────────

def fig_decile_fractions(metrics: dict, fig_path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    deltas_pos = [d for d in DELTA_GRID_FLOAT if d > 0.0]
    n_deltas   = len(deltas_pos)
    n_deciles  = 10
    decile_labels = [f"D{d+1}" for d in range(n_deciles)]

    colors = ["tab:blue", "tab:orange", "tab:green"]
    x      = np.arange(n_deciles)
    width  = 0.25

    h4b_class = metrics["h4b"]["classification"]
    h4c_class = metrics["h4c"]["classification"]

    fig, ax = plt.subplots(figsize=(10, 5))
    for j, delta_f in enumerate(deltas_pos):
        delta_str = f"{delta_f:.3f}"
        fracs = metrics["decile_fractions"][delta_str]
        offset = (j - 1) * width
        ax.bar(
            x + offset, fracs, width,
            label=f"δ={delta_str}",
            color=colors[j],
            alpha=0.8,
            edgecolor="white",
            linewidth=0.4,
        )

    ax.axhline(0.09, color="k", lw=0.8, ls="--", label="Uniform band [0.09, 0.11]")
    ax.axhline(0.11, color="k", lw=0.8, ls="--")
    ax.axhline(0.15, color="firebrick", lw=0.8, ls=":", label="H4c D10 threshold (0.15)")

    ax.set_xticks(x)
    ax.set_xticklabels(decile_labels)
    ax.set_xlabel("Decile (D1 = lowest v_p, D10 = highest)")
    ax.set_ylabel("Fraction of total W1")
    ax.set_title(
        f"Step 4 — Decile fractions of W1\n"
        f"H4b: {h4b_class}  |  H4c: {h4c_class}"
    )
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(fig_path, format="pdf")
    plt.close(fig)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    repo_root = resolve_repo_root()
    paths     = build_paths(repo_root)
    out(f"repo_root={repo_root}")

    # Load artifacts
    for key in ("INGEST_FILE", "PERTURB_FILE", "METRICS_FILE"):
        if not paths[key].exists():
            err(f"ABORT — required file not found: {paths[key]}")
            raise SystemExit(1)

    ingest_data  = np.load(paths["INGEST_FILE"])
    perturb_data = np.load(paths["PERTURB_FILE"])
    with paths["METRICS_FILE"].open("r", encoding="utf-8") as f:
        metrics = yaml.safe_load(f)

    vp_base      = np.asarray(ingest_data["vp"],           dtype=np.float64)
    weights_norm = np.asarray(ingest_data["weights_norm"], dtype=np.float64)

    paths["FIGURES_DIR"].mkdir(parents=True, exist_ok=True)

    figure_hashes: dict[str, str] = {}

    # Figure 1
    fp1 = paths["FIGURES_DIR"] / "fig_w1_vs_delta.pdf"
    out(f"writing {fp1.name}...")
    fig_w1_vs_delta(metrics, fp1)
    figure_hashes[fp1.name] = append_artifact_hash(fp1, paths["HASH_LOG_FILE"], repo_root)
    out(f"  SHA-256: {figure_hashes[fp1.name]}")

    # Figure 2
    fp2 = paths["FIGURES_DIR"] / "fig_cdf_comparison.pdf"
    out(f"writing {fp2.name}...")
    fig_cdf_comparison(vp_base, perturb_data, weights_norm, fp2)
    figure_hashes[fp2.name] = append_artifact_hash(fp2, paths["HASH_LOG_FILE"], repo_root)
    out(f"  SHA-256: {figure_hashes[fp2.name]}")

    # Figure 3
    fp3 = paths["FIGURES_DIR"] / "fig_decile_fractions.pdf"
    out(f"writing {fp3.name}...")
    fig_decile_fractions(metrics, fp3)
    figure_hashes[fp3.name] = append_artifact_hash(fp3, paths["HASH_LOG_FILE"], repo_root)
    out(f"  SHA-256: {figure_hashes[fp3.name]}")

    # Append figure block to RESULTS.md
    hash_lines = "\n".join(
        f"- `{name}`: SHA-256 `{h}`"
        for name, h in figure_hashes.items()
    )
    fig_block = (
        f"\n"
        f"## Step 4 Figure Artifacts — {utc_timestamp()}\n"
        f"\n"
        f"**Protocol SHA-256:** `{EXPECTED_PROTOCOL_SHA}`\n"
        f"\n"
        f"{hash_lines}\n"
        f"\n"
        f"---\n"
    )
    append_text(paths["RESULTS_FILE"], fig_block)

    out("OK — figures complete")


if __name__ == "__main__":
    main()
