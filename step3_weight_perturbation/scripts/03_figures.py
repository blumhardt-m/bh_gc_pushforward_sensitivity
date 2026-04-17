#!/usr/bin/env python3
"""
03_figures.py — BH GC Orbit Measure Perturbation Audit (Step 3)

Produces descriptive figures only. No inference. No new analysis.

PLOTTING IMPLEMENTATION DECISIONS:
  - Backend: matplotlib Agg (non-interactive, headless).
  - fig1: W1 vs epsilon. Scatter + line plot of W1(km/s) against epsilon grid.
    Log scale on y-axis to show range across orders of magnitude.
    Skipped epsilon (K2) plotted as absent. eps=0.00 annotated separately.
  - fig2: Weighted empirical CDFs at eps=0.00 and eps=0.10 (most and least
    similar to base). CDFs recomputed from ingest + perturbed weights using
    the same sequential algorithm as 02_metrics.py. Step function, forward.
    If eps=0.10 was K2-skipped, next available epsilon used.
  - fig3: Text panel showing classification, W1, sigma_w, ratio for each
    epsilon; nonmonotonicity flags if any. No inference beyond Section 17.
  - All PDFs saved to outputs/figures/. Directory created if absent.
  - CDF recomputation is independent of 02_metrics.py; consistency is
    structural (same algorithm, same inputs).
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


def sequential_sum_arr(arr: np.ndarray) -> np.float64:
    total = np.float64(0.0)
    for i in range(arr.shape[0]):
        total = np.float64(total + np.float64(arr[i]))
    return np.float64(total)


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


def compute_cdf_pair(
    vp: np.ndarray, w_base: np.ndarray, w_eps: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Returns (union_support, F_base, F_eps) as float64 arrays."""
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


def main() -> None:
    repo_root = resolve_repo_root()
    fig_dir = repo_root / "outputs" / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    ingest_data  = np.load(repo_root / "outputs" / "ingest.npz")
    perturb_data = np.load(repo_root / "outputs" / "perturbed_weights.npz")
    with (repo_root / "outputs" / "metrics.yaml").open("r", encoding="utf-8") as f:
        metrics = yaml.safe_load(f)

    vp       = np.asarray(ingest_data["vp"],           dtype=np.float64)
    w_base   = np.asarray(ingest_data["weights_norm"], dtype=np.float64)

    eps_results = metrics["epsilon_results"]

    # ── fig1: W1 vs epsilon ──────────────────────────────────────────────────
    eps_vals_ok = []
    w1_vals_ok  = []
    eps_skip    = []

    for r in eps_results:
        if r["status"] == "OK" and r["W1"] is not None:
            eps_vals_ok.append(float(r["epsilon"]))
            w1_vals_ok.append(float(r["W1"]))
        else:
            eps_skip.append(float(r["epsilon"]))

    fig1, ax1 = plt.subplots(figsize=(7, 5))

    if eps_vals_ok:
        ax1.semilogy(eps_vals_ok, w1_vals_ok, "o-", color="steelblue", lw=1.5,
                     markersize=6, label="W1 (computed)")

    if eps_skip:
        for ev in eps_skip:
            ax1.axvline(ev, color="red", lw=1, linestyle=":", alpha=0.7)
        ax1.plot([], [], color="red", linestyle=":", label="K2 skipped")

    ax1.set_xlabel(r"$\varepsilon$")
    ax1.set_ylabel(r"$W_1(\mu_0,\, \mu_\varepsilon)$ (km s$^{-1}$)")
    ax1.set_title("Fig. 1 — W1 vs. epsilon (Step 3 perturbation audit)")
    ax1.legend()
    ax1.grid(True, which="both", alpha=0.3)
    fig1.tight_layout()
    p1 = fig_dir / "fig1_w1_vs_epsilon.pdf"
    fig1.savefig(p1)
    plt.close(fig1)
    out(f"Saved {p1}")

    # ── fig2: CDF comparison at eps=0.00 and eps=0.10 (or fallback) ─────────
    # Determine which epsilon to compare against (prefer 0.10, fallback)
    cdf_eps_target = None
    for eps in [np.float64(0.10), np.float64(0.05), np.float64(0.01)]:
        key = EPS_KEY[eps]
        if key in perturb_data:
            cdf_eps_target = eps
            break

    fig2, ax2 = plt.subplots(figsize=(8, 5))

    # Always plot base CDF
    us_base, F_base_self, _ = compute_cdf_pair(vp, w_base, w_base)
    ax2.step(us_base, F_base_self, where="post",
             color="steelblue", lw=1.5, label=r"$\varepsilon=0.00$ (base)")

    if cdf_eps_target is not None:
        w_cdf_eps = np.asarray(perturb_data[EPS_KEY[cdf_eps_target]], dtype=np.float64)
        us, F_base_c, F_eps_c = compute_cdf_pair(vp, w_base, w_cdf_eps)
        label_eps = f"$\\varepsilon={float(cdf_eps_target):.2f}$"
        ax2.step(us, F_eps_c, where="post",
                 color="darkorange", lw=1.5, linestyle="--", label=label_eps)

    ax2.set_xlabel(r"$v_p$ (km s$^{-1}$)")
    ax2.set_ylabel("Cumulative weighted probability")
    ax2.set_title("Fig. 2 — Weighted empirical CDFs: base vs. perturbed")
    ax2.legend()
    fig2.tight_layout()
    p2 = fig_dir / "fig2_cdf_comparison.pdf"
    fig2.savefig(p2)
    plt.close(fig2)
    out(f"Saved {p2}")

    # ── fig3: outcome summary text panel ─────────────────────────────────────
    sigma_base = float(metrics.get("sigma_base", float("nan")))
    nonmonotonicity = metrics.get("nonmonotonicity", [])

    summary_lines = [
        f"Step 3 — Measure Perturbation Audit",
        f"Protocol SHA: {str(metrics.get('protocol_sha256',''))[:16]}...",
        f"OSF: {metrics.get('osf_url','')}",
        f"n_rows: {metrics.get('n_rows','')}",
        f"sigma_w (base): {sigma_base:.4f} km/s",
        "",
    ]
    for r in eps_results:
        eps_str = f"{r['epsilon']:.2f}"
        if r["status"] == "K2_SKIPPED":
            summary_lines.append(f"eps={eps_str}: K2 SKIPPED")
        else:
            summary_lines.append(
                f"eps={eps_str}: {r['classification']}"
                f"  W1={r['W1']:.3e} km/s"
                f"  ratio={r['ratio']:.3e}"
            )

    if nonmonotonicity:
        summary_lines.append("")
        summary_lines.append("Nonmonotonicity flags:")
        for flag in nonmonotonicity:
            summary_lines.append(f"  {flag}")

    fig3, ax3 = plt.subplots(figsize=(10, 5))
    ax3.axis("off")
    ax3.text(0.04, 0.96, "\n".join(summary_lines),
             transform=ax3.transAxes,
             fontsize=9, verticalalignment="top", fontfamily="monospace",
             bbox=dict(boxstyle="round,pad=0.5", facecolor="lightyellow", alpha=0.8))
    ax3.set_title("Fig. 3 — Outcome summary (bh_gc_orbit_measure_perturbation_audit)")
    fig3.tight_layout()
    p3 = fig_dir / "fig3_outcome_summary.pdf"
    fig3.savefig(p3)
    plt.close(fig3)
    out(f"Saved {p3}")

    out("OK — figures complete")


if __name__ == "__main__":
    main()
