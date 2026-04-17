#!/usr/bin/env python3
"""
03_metrics.py — Synthetic Demo

Compute W1 and decile fractions for both perturbation axes.
W1 algorithm: duplicate aggregation → sorted union → sequential CDF → interval sum.
Decile edges fixed from the baseline distribution; reused for both axes.

Outputs:
  outputs/synthetic_metrics.yaml
  results/appendix_tables.md
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
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


# ── W1 algorithm (same machinery as main audit) ───────────────────────────────

def aggregate_weights(x: np.ndarray, w: np.ndarray) -> dict:
    """Aggregate weights by exact float64 key equality."""
    agg: dict = {}
    for i in range(x.shape[0]):
        key = np.float64(x[i])
        if key in agg:
            agg[key] = np.float64(agg[key] + np.float64(w[i]))
        else:
            agg[key] = np.float64(w[i])
    return agg


def sorted_union(agg_a: dict, agg_b: dict) -> np.ndarray:
    """Sorted union of support points from two aggregated dicts."""
    union_set: set = set()
    for key in agg_a:
        union_set.add(float(key))
    for key in agg_b:
        union_set.add(float(key))
    union_list = sorted(union_set)
    u = np.empty(len(union_list), dtype=np.float64)
    for k in range(len(union_list)):
        u[k] = np.float64(union_list[k])
    return u


def cdf_on_union(agg: dict, u: np.ndarray) -> np.ndarray:
    """Sequential CDF accumulation of agg on the union support u."""
    # Weights on union
    M = u.shape[0]
    w_u = np.empty(M, dtype=np.float64)
    for k in range(M):
        key    = np.float64(u[k])
        w_u[k] = agg.get(key, np.float64(0.0))
    # Sequential CDF
    F    = np.empty(M, dtype=np.float64)
    F[0] = np.float64(w_u[0])
    for k in range(1, M):
        F[k] = np.float64(F[k-1] + np.float64(w_u[k]))
    return F


def compute_w1(
    x_base:  np.ndarray,
    w_base:  np.ndarray,
    x_delta: np.ndarray,
    w_delta: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.float64]:
    """
    W1(μ_base, μ_delta).
    1. Aggregate by exact float64 key equality.
    2. Sorted union support.
    3. Sequential CDF on union.
    4. Sequential interval sum.
    Returns (union_support, F_base, F_delta, w1).
    """
    agg_base  = aggregate_weights(x_base,  w_base)
    agg_delta = aggregate_weights(x_delta, w_delta)
    u         = sorted_union(agg_base, agg_delta)
    F_base    = cdf_on_union(agg_base,  u)
    F_delta   = cdf_on_union(agg_delta, u)

    w1 = np.float64(0.0)
    for k in range(u.shape[0] - 1):
        gap = np.float64(abs(np.float64(F_base[k]) - np.float64(F_delta[k])))
        dx  = np.float64(np.float64(u[k+1]) - np.float64(u[k]))
        w1  = np.float64(w1 + gap * dx)
    return u, F_base, F_delta, w1


# ── Decile localization ────────────────────────────────────────────────────────

def compute_decile_edges(u: np.ndarray, F_base: np.ndarray) -> np.ndarray:
    """
    9 decile edges from the BASELINE CDF (fixed; reused for all perturbation levels).
    edges[j] = first support point where F_base >= (j+1)*0.1.
    """
    edges = np.empty(9, dtype=np.float64)
    for j in range(9):
        q   = np.float64((j + 1) * 0.1)
        idx = 0
        while idx < F_base.shape[0] and np.float64(F_base[idx]) < q:
            idx += 1
        if idx >= u.shape[0]:
            idx = u.shape[0] - 1
        edges[j] = np.float64(u[idx])
    return edges


def compute_decile_fractions(
    edges:   np.ndarray,   # 9 edges from BASELINE CDF — fixed, never updated
    u:       np.ndarray,   # current union support
    F_base:  np.ndarray,   # base CDF on current union
    F_delta: np.ndarray,   # perturbed CDF on current union
    w1:      np.float64,
) -> np.ndarray:
    """
    10 decile fractions.
    Interval left-endpoint assignment uses the fixed baseline edges.
    Decile 0 = D1 (lowest); decile 9 = D10 (highest).
    """
    contrib = np.empty(10, dtype=np.float64)
    for j in range(10):
        contrib[j] = np.float64(0.0)

    if w1 == np.float64(0.0):
        return contrib

    for k in range(u.shape[0] - 1):
        left  = np.float64(u[k])
        right = np.float64(u[k+1])
        gap   = np.float64(abs(np.float64(F_base[k]) - np.float64(F_delta[k])))
        piece = np.float64(gap * np.float64(right - left))

        # Assign left endpoint to a decile using fixed baseline edges
        decile_idx = 9   # default: D10 (highest)
        for j in range(9):
            if left < np.float64(edges[j]):
                decile_idx = j
                break
        contrib[decile_idx] = np.float64(contrib[decile_idx] + piece)

    out = np.empty(10, dtype=np.float64)
    for j in range(10):
        out[j] = np.float64(contrib[j] / w1)
    return out


# ── Appendix table writer ─────────────────────────────────────────────────────

def write_appendix_tables(path: Path, payload: dict) -> None:
    lines = [
        "# Appendix synthetic demonstration tables",
        "",
        "## Weight-axis summary",
        "",
        "| eps | W1 | D10 |",
        "|---:|---:|---:|",
    ]
    for row in payload["weight_rows"]:
        lines.append(f"| {row['amp']:.6g} | {row['w1']:.12g} | {row['d10']:.12g} |")
    lines += [
        "",
        "## Support-axis summary",
        "",
        "| delta | W1 | D10 |",
        "|---:|---:|---:|",
    ]
    for row in payload["support_rows"]:
        lines.append(f"| {row['amp']:.12g} | {row['w1']:.12g} | {row['d10']:.12g} |")
    lines += [
        "",
        f"- Weight-axis ratio (largest/smallest positive): {payload['weight_ratio']:.12g}",
        f"- Support-axis ratio (largest/smallest positive): {payload['support_ratio']:.12g}",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    repo_root    = Path(__file__).resolve().parent.parent
    base         = np.load(repo_root / "outputs" / "synthetic_base.npz")
    weight_axis  = np.load(repo_root / "outputs" / "weight_axis.npz")
    support_axis = np.load(repo_root / "outputs" / "support_axis.npz")

    v_base  = np.asarray(base["v_base"],  dtype=np.float64)
    weights = np.asarray(base["weights"], dtype=np.float64)

    # Baseline CDF — used to fix decile edges for both axes
    u0, F0_base, _, _ = compute_w1(v_base, weights, v_base, weights)
    edges = compute_decile_edges(u0, F0_base)
    print(f"decile edges (baseline): {[f'{float(edges[j]):.4f}' for j in range(9)]}")

    # ── Weight axis ───────────────────────────────────────────────────────────

    weight_rows = []
    eps_grid    = np.asarray(weight_axis["eps_grid"], dtype=np.float64)
    for eps in eps_grid:
        key    = f"weights_eps_{float(eps):0.3f}".replace(".", "_")
        w_eps  = np.asarray(weight_axis[key], dtype=np.float64)
        # Base distribution is (v_base, base weights); perturbed is (v_base, w_eps)
        u, Fb, Fd, w1 = compute_w1(v_base, weights, v_base, w_eps)
        fracs = compute_decile_fractions(edges, u, Fb, Fd, w1)
        weight_rows.append({
            "amp": float(eps),
            "w1":  float(w1),
            "d10": float(fracs[9]),
        })
        print(f"weight eps={float(eps):.3f}  W1={float(w1):.6e}  D10={float(fracs[9]):.4f}")

    # ── Support axis ──────────────────────────────────────────────────────────

    support_rows = []
    delta_grid   = np.asarray(support_axis["delta_grid"], dtype=np.float64)
    for delta in delta_grid:
        key     = f"v_delta_{float(delta):0.6f}".replace(".", "_")
        v_delta = np.asarray(support_axis[key], dtype=np.float64)
        # Base distribution is (v_base, weights); perturbed is (v_delta, weights)
        u, Fb, Fd, w1 = compute_w1(v_base, weights, v_delta, weights)
        fracs = compute_decile_fractions(edges, u, Fb, Fd, w1)
        support_rows.append({
            "amp": float(delta),
            "w1":  float(w1),
            "d10": float(fracs[9]),
        })
        print(f"support delta={float(delta):.6f}  W1={float(w1):.6e}  D10={float(fracs[9]):.4f}")

    # ── Ratios ────────────────────────────────────────────────────────────────

    positive_weight  = [r for r in weight_rows  if r["amp"] > 0.0]
    positive_support = [r for r in support_rows if r["amp"] > 0.0]
    weight_ratio  = np.float64(positive_weight[-1]["w1"]  / positive_weight[0]["w1"])
    support_ratio = np.float64(positive_support[-1]["w1"] / positive_support[0]["w1"])

    print(f"weight-axis  ratio = {float(weight_ratio):.4f}")
    print(f"support-axis ratio = {float(support_ratio):.4f}")

    # ── Write outputs ─────────────────────────────────────────────────────────

    payload = {
        "weight_rows":    weight_rows,
        "support_rows":   support_rows,
        "weight_ratio":   float(weight_ratio),
        "support_ratio":  float(support_ratio),
    }

    out_yaml = repo_root / "outputs" / "synthetic_metrics.yaml"
    with out_yaml.open("w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, sort_keys=False, allow_unicode=True)

    out_md = repo_root / "results" / "appendix_tables.md"
    write_appendix_tables(out_md, payload)

    hash_log = repo_root / "logs" / "artifact_hashes.yaml"
    append_artifact_hash(out_yaml, hash_log, repo_root)
    append_artifact_hash(out_md,   hash_log, repo_root)
    print("OK — synthetic metrics complete")


if __name__ == "__main__":
    main()
