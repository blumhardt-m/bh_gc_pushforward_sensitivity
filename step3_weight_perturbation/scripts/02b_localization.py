#!/usr/bin/env python3
"""
02b_localization.py — BH GC Orbit Measure Perturbation Audit (Step 3)
SUPPLEMENTARY DIAGNOSTIC — post-execution, outside frozen protocol.

Purpose: Localize W1 contributions by v_p decile to distinguish global
shift from tail-driven effects. Prevents artifact claims by identifying
which regions of the v_p support drive the observed divergence.

Governance note:
- This script is supplementary. It is NOT part of the frozen protocol
  (PROTOCOL_v1.0.md, Section 15 prohibits additional metrics after freeze).
- It does not modify outputs/, RESULTS.md, or artifact_hashes.yaml.
- It does not affect classification or any preregistered metric.
- Outputs go to: outputs/supplementary/ and results/localization_table.md

Algorithm:
- Recompute CDFs from ingest.npz and perturbed_weights.npz using the
  same sequential algorithm as 02_metrics.py (independent recomputation).
- Decile boundaries: quantile-based from base CDF (F_base = 0.1k for k=1..9).
- Per-decile W1 contribution: sum of |F_base[k] - F_eps[k]| * delta_x
  over all intervals k whose left endpoint falls in that decile.
- All arithmetic in float64. Explicit Python loops. No np.sum, np.cumsum.
"""

from __future__ import annotations

import math
import os
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import yaml

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


EXPECTED_N_ROWS = 33079
EPSILON_GRID = [
    np.float64(0.00),
    np.float64(0.01),
    np.float64(0.05),
    np.float64(0.10),
]
EPS_KEY = {
    np.float64(0.00): "w_eps_0_00",
    np.float64(0.01): "w_eps_0_01",
    np.float64(0.05): "w_eps_0_05",
    np.float64(0.10): "w_eps_0_10",
}
N_DECILES = 10
REPO_ROOT_ENV = "BH_GC_AUDIT_REPO_ROOT"


def _write_line(stream, msg: str) -> None:
    stream.write(str(msg) + "\n")
    flush = getattr(stream, "flush", None)
    if callable(flush):
        flush()


def out(msg: str) -> None:
    _write_line(sys.stdout, msg)


def resolve_repo_root() -> Path:
    env_root = os.environ.get(REPO_ROOT_ENV)
    if env_root:
        p = Path(env_root).expanduser().resolve()
        if p.exists():
            return p
    cwd = Path.cwd().resolve()
    for candidate in [cwd] + list(cwd.parents):
        if (candidate / "STATE.yaml").exists() and (candidate / "protocol" / "PROTOCOL_v1.0.md").exists():
            return candidate
    file_obj: Optional[str] = globals().get("__file__")
    if file_obj:
        fp = Path(file_obj).resolve()
        for candidate in [fp.parent, fp.parent.parent] + list(fp.parent.parent.parents):
            if (candidate / "STATE.yaml").exists() and (candidate / "protocol" / "PROTOCOL_v1.0.md").exists():
                return candidate
    raise SystemExit("could not resolve repository root")


# ── CDF utilities (reimplement — independent of 02_metrics.py) ────────────────

def aggregate_duplicates(vp: np.ndarray, weights: np.ndarray) -> dict:
    d: dict = {}
    for i in range(vp.shape[0]):
        key = np.float64(vp[i])
        w   = np.float64(weights[i])
        if key in d:
            d[key] = d[key] + w
        else:
            d[key] = w
    return d


def compute_cdf_arrays(
    vp: np.ndarray, w_base: np.ndarray, w_eps: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Returns (union_support, F_base, F_eps)."""
    dict_base = aggregate_duplicates(vp, w_base)
    dict_eps  = aggregate_duplicates(vp, w_eps)

    all_values: dict = {}
    for key in dict_base:
        all_values[key] = True
    for key in dict_eps:
        all_values[key] = True

    all_values_list = sorted(all_values.keys())
    M = len(all_values_list)

    union_support = np.empty(M, dtype=np.float64)
    for k in range(M):
        union_support[k] = np.float64(all_values_list[k])

    w_union_base = np.empty(M, dtype=np.float64)
    w_union_eps  = np.empty(M, dtype=np.float64)
    for k in range(M):
        xk = union_support[k]
        w_union_base[k] = dict_base[xk] if xk in dict_base else np.float64(0.0)
        w_union_eps[k]  = dict_eps[xk]  if xk in dict_eps  else np.float64(0.0)

    F_base = np.empty(M, dtype=np.float64)
    F_eps  = np.empty(M, dtype=np.float64)
    F_base[0] = np.float64(w_union_base[0])
    F_eps[0]  = np.float64(w_union_eps[0])
    for k in range(1, M):
        F_base[k] = F_base[k-1] + np.float64(w_union_base[k])
        F_eps[k]  = F_eps[k-1]  + np.float64(w_union_eps[k])

    return union_support, F_base, F_eps


# ── Decile localization ────────────────────────────────────────────────────────

def find_quantile_edge(
    union_support: np.ndarray, F_base: np.ndarray, q: np.float64
) -> np.float64:
    """First support point where F_base >= q."""
    for k in range(union_support.shape[0]):
        if np.float64(F_base[k]) >= q:
            return np.float64(union_support[k])
    return np.float64(union_support[-1])


def compute_decile_edges(
    union_support: np.ndarray, F_base: np.ndarray, n_deciles: int
) -> list[np.float64]:
    """
    Return n_deciles + 1 edge values: [v_min, q_0.1, q_0.2, ..., q_0.9, v_max].
    Edges are quantile boundaries from F_base.
    """
    edges: list[np.float64] = [np.float64(union_support[0])]
    for d in range(1, n_deciles):
        q = np.float64(d) / np.float64(n_deciles)
        edges.append(find_quantile_edge(union_support, F_base, q))
    edges.append(np.float64(union_support[-1]))
    return edges


def compute_decile_contributions(
    union_support: np.ndarray,
    F_base: np.ndarray,
    F_eps: np.ndarray,
    n_deciles: int = N_DECILES,
) -> tuple[list, list, np.float64]:
    """
    Partition the W1 integrand into n_deciles bins defined by base-CDF quantiles.

    Returns:
        decile_edges: list of n_deciles+1 float64 v_p boundaries
        per_decile:   list of n_deciles float64 W1 contributions
        total_w1:     float64 total W1 (sum over all intervals)
    """
    M = union_support.shape[0]
    decile_edges = compute_decile_edges(union_support, F_base, n_deciles)

    per_decile = [np.float64(0.0)] * n_deciles
    total_w1   = np.float64(0.0)

    for k in range(M - 1):
        contrib = (
            np.float64(abs(np.float64(F_base[k]) - np.float64(F_eps[k])))
            * (np.float64(union_support[k+1]) - np.float64(union_support[k]))
        )
        total_w1 = total_w1 + contrib

        # Assign to decile: left endpoint of interval
        xk = np.float64(union_support[k])
        assigned = False
        for d in range(n_deciles - 1):
            if xk >= decile_edges[d] and xk < decile_edges[d + 1]:
                per_decile[d] = per_decile[d] + contrib
                assigned = True
                break
        if not assigned:
            # Falls in last decile [edge_{n-1}, edge_n]
            per_decile[n_deciles - 1] = per_decile[n_deciles - 1] + contrib

    return decile_edges, per_decile, total_w1


# ── Output formatting ──────────────────────────────────────────────────────────

def format_localization_table(
    eps: float,
    decile_edges: list,
    per_decile: list,
    total_w1: np.float64,
) -> str:
    n = len(per_decile)
    lines = [
        f"### ε = {eps:.2f}  (W1 = {float(total_w1):.6e} km/s)",
        "",
        "| Decile | v_p range (km/s)              | W1 contribution (km/s) | Fraction of W1 |",
        "|--------|-------------------------------|------------------------|----------------|",
    ]
    for d in range(n):
        lo = float(decile_edges[d])
        hi = float(decile_edges[d + 1])
        contrib = float(per_decile[d])
        frac    = contrib / float(total_w1) if float(total_w1) > 0.0 else 0.0
        lines.append(
            f"| D{d+1:02d}    | [{lo:.2f}, {hi:.2f}] "
            f"| {contrib:.4e}               | {frac:.4f}         |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    repo_root = resolve_repo_root()
    out(f"repo_root={repo_root}")

    ingest_data  = np.load(repo_root / "outputs" / "ingest.npz")
    perturb_data = np.load(repo_root / "outputs" / "perturbed_weights.npz")
    with (repo_root / "outputs" / "metrics.yaml").open("r", encoding="utf-8") as f:
        metrics = yaml.safe_load(f)

    vp     = np.asarray(ingest_data["vp"],           dtype=np.float64)
    w_base = np.asarray(ingest_data["weights_norm"], dtype=np.float64)

    supp_dir = repo_root / "outputs" / "supplementary"
    supp_dir.mkdir(parents=True, exist_ok=True)

    all_results: dict = {}  # eps_label -> (decile_edges, per_decile, total_w1)
    md_lines = [
        "# W1 Contribution Localization by v_p Decile",
        "",
        "**Supplementary diagnostic — bh_gc_orbit_measure_perturbation_audit (Step 3)**",
        "Decile boundaries defined by base-CDF quantiles (F_base = 0.1k for k=1..9).",
        "Per-decile W1 contribution = sum of |F_base - F_eps| × Δx over intervals in decile.",
        "All arithmetic in float64, explicit loops.",
        "",
    ]

    for eps in EPSILON_GRID:
        key = EPS_KEY[eps]
        eps_label = f"{float(eps):.2f}"

        if key not in perturb_data:
            out(f"eps={eps_label}: absent (K2 skipped)")
            md_lines.append(f"### ε = {float(eps):.2f}: K2 SKIPPED\n")
            continue

        w_eps = np.asarray(perturb_data[key], dtype=np.float64)
        union_support, F_base, F_eps = compute_cdf_arrays(vp, w_base, w_eps)
        decile_edges, per_decile, total_w1 = compute_decile_contributions(
            union_support, F_base, F_eps, N_DECILES
        )

        all_results[eps_label] = (decile_edges, per_decile, total_w1)
        table_str = format_localization_table(float(eps), decile_edges, per_decile, total_w1)
        md_lines.append(table_str)

        out(f"eps={eps_label}: W1={float(total_w1):.6e} km/s")
        out(f"  per-decile fractions: "
            + " | ".join(
                f"D{d+1}:{float(per_decile[d])/float(total_w1):.3f}"
                for d in range(N_DECILES)
                if float(total_w1) > 0.0
            ))

    # Save markdown table
    localization_md = repo_root / "results" / "localization_table.md"
    with localization_md.open("w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
    out(f"Saved {localization_md}")

    # Figure: stacked bar chart of decile fractions for each epsilon > 0
    eps_labels_nonzero = [
        label for label in [f"{float(e):.2f}" for e in EPSILON_GRID]
        if label != "0.00" and label in all_results
    ]

    if eps_labels_nonzero:
        n_eps = len(eps_labels_nonzero)
        fig, axes = plt.subplots(1, n_eps, figsize=(4 * n_eps, 5), sharey=True)
        if n_eps == 1:
            axes = [axes]

        for ax, eps_label in zip(axes, eps_labels_nonzero):
            decile_edges, per_decile, total_w1 = all_results[eps_label]
            fracs = [float(per_decile[d]) / float(total_w1) if float(total_w1) > 0.0 else 0.0
                     for d in range(N_DECILES)]
            decile_labels = [f"D{d+1}" for d in range(N_DECILES)]
            colors = plt.cm.RdYlBu_r(np.linspace(0.1, 0.9, N_DECILES))

            bars = ax.bar(decile_labels, fracs, color=colors, edgecolor="grey", lw=0.5)
            ax.set_title(f"ε = {eps_label}", fontsize=11)
            ax.set_xlabel("v_p decile (base CDF)")
            if ax is axes[0]:
                ax.set_ylabel("Fraction of W1")
            ax.set_ylim(0, 1)
            ax.axhline(1.0 / N_DECILES, color="black", lw=0.8, linestyle="--",
                       label="Uniform" if ax is axes[0] else None)
            ax.tick_params(axis="x", labelsize=7)

        handles = [
            plt.Line2D([0], [0], color="black", lw=0.8, linestyle="--",
                       label="Uniform (1/10)")
        ]
        fig.legend(handles=handles, loc="upper right", fontsize=8)
        fig.suptitle("W1 Contribution Localization by v_p Decile\n"
                     "(bh_gc_orbit_measure_perturbation_audit)", fontsize=10)
        fig.tight_layout()

        fig_path = repo_root / "outputs" / "supplementary" / "fig_supp_localization.pdf"
        fig.savefig(fig_path)
        plt.close(fig)
        out(f"Saved {fig_path}")

    out("OK — localization complete")


if __name__ == "__main__":
    main()
