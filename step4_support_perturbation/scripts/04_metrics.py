#!/usr/bin/env python3
"""
04_metrics.py — BH GC Orbit Support Perturbation Audit (Step 4)

Compute W1, decile fractions, directional shift per delta.
Classify H4a–H4c. Check monotonicity.
Write outputs/w1_metrics.yaml, append to RESULTS.md.
Transition STATE.yaml to EXECUTION_COMPLETE.

Protocol alignment (PROTOCOL_v1.0.md, Sections 9–13, 16–18):
- W1 by exact preregistered algorithm (Section 9).
- Decile fractions as primary diagnostic (Section 10).
- Directional shift Δμ(δ) (Section 11).
- H4a–H4c classification (Section 13).
- Monotonicity flag (Section 13).
- State transition to EXECUTION_COMPLETE (Section 16).
- Artifact hashes logged (Section 17).
"""

from __future__ import annotations

import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import yaml


EXPECTED_PROTOCOL_SHA = "e2f4db43da60cbc427b40091af7df7b587b97d7173f69eb7cc07436a606b5cc2"
EXPECTED_N_ROWS       = 33079
REPO_ROOT_ENV         = "BH_GC_AUDIT_REPO_ROOT"

DELTA_GRID_FLOAT: list[float] = [0.000, 0.010, 0.050, 0.090]
DELTA_LABELS: list[str]       = ["0_000", "0_010", "0_050", "0_090"]

# Classification thresholds — locked (Section 13)
W1_FLOOR_KM_S      = np.float64(1e-9)   # km/s
H4A_RATIO_LOW      = np.float64(8.5)
H4A_RATIO_HIGH     = np.float64(9.5)
DECILE_LOW         = np.float64(0.09)
DECILE_HIGH        = np.float64(0.11)
D10_THRESHOLD      = np.float64(0.15)
MONOTONE_THRESHOLD = np.float64(0.99)   # flag if W1(δ_b) < 0.99×W1(δ_a)


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
        "STATE_FILE":      repo_root / "STATE.yaml",
        "INGEST_FILE":     repo_root / "outputs" / "ingest.npz",
        "PERTURB_FILE":    repo_root / "outputs" / "perturbed_support.npz",
        "METRICS_FILE":    repo_root / "outputs" / "w1_metrics.yaml",
        "OUTPUT_DIR":      repo_root / "outputs",
        "LOG_DIR":         repo_root / "logs",
        "HASH_LOG_FILE":   repo_root / "logs" / "artifact_hashes.yaml",
        "DEVIATIONS_FILE": repo_root / "DEVIATIONS.md",
        "RESULTS_FILE":    repo_root / "RESULTS.md",
    }


def append_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(text)


def abort_kill(message: str, kill_code: str, paths: dict[str, Path]) -> None:
    block = (
        f"\n## Step 4 Metrics Kill — {kill_code}\n\n"
        f"- Timestamp (UTC): {utc_timestamp()}\n"
        f"- Kill criterion: {kill_code}\n"
        f"- Details: {message}\n"
        f"- Protocol SHA-256: {EXPECTED_PROTOCOL_SHA}\n"
        f"- Status: EXECUTION_TERMINATED\n"
    )
    append_text(paths["RESULTS_FILE"], block)
    err(f"ABORT {kill_code} — {message}")
    raise SystemExit(1)


def append_artifact_hash(path: Path, hash_log_file: Path, repo_root: Path) -> None:
    import hashlib
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    artifact_hash = h.hexdigest()
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


# ── W1 computation (PROTOCOL_v1.0.md Section 9) ──────────────────────────────

def aggregate_weights(vp: np.ndarray, weights: np.ndarray) -> dict:
    """Aggregate weights by exact float64 key equality."""
    agg: dict = {}
    n = vp.shape[0]
    for i in range(n):
        key = np.float64(vp[i])
        if key in agg:
            agg[key] = np.float64(agg[key] + np.float64(weights[i]))
        else:
            agg[key] = np.float64(weights[i])
    return agg


def compute_w1(
    vp_base:  np.ndarray,
    vp_delta: np.ndarray,
    weights:  np.ndarray,
    paths:    dict[str, Path],
    delta_label: str,
) -> tuple[np.float64, np.ndarray, np.ndarray, np.ndarray]:
    """
    W1(μ_0, μ_δ) per Section 9.
    Returns (w1, union_support, F_base, F_delta).

    Steps:
    1. Aggregate duplicates by exact float64 key equality.
    2. Sorted union support.
    3. Sequential CDF accumulation.
    4. Sequential W1 summation.
    """
    agg_base  = aggregate_weights(vp_base,  weights)
    agg_delta = aggregate_weights(vp_delta, weights)

    # Sorted union support
    union_set: set = set()
    for key in agg_base:
        union_set.add(float(key))
    for key in agg_delta:
        union_set.add(float(key))
    union_list = sorted(union_set)
    M = len(union_list)

    # K5: sanity check
    n_base  = len(agg_base)
    n_delta = len(agg_delta)
    if M < max(n_base, n_delta):
        abort_kill(
            f"K5: union support length {M} < max(n_base={n_base}, n_delta={n_delta}) "
            f"at delta={delta_label}",
            "K5",
            paths,
        )

    union_support = np.empty(M, dtype=np.float64)
    for k in range(M):
        union_support[k] = np.float64(union_list[k])

    # Weights on union support (zero where distribution has no mass)
    w_union_base  = np.empty(M, dtype=np.float64)
    w_union_delta = np.empty(M, dtype=np.float64)
    for k in range(M):
        x = np.float64(union_list[k])
        w_union_base[k]  = agg_base.get(x,  np.float64(0.0))
        w_union_delta[k] = agg_delta.get(x, np.float64(0.0))

    # Sequential CDF accumulation
    F_base  = np.empty(M, dtype=np.float64)
    F_delta = np.empty(M, dtype=np.float64)
    F_base[0]  = np.float64(w_union_base[0])
    F_delta[0] = np.float64(w_union_delta[0])
    for k in range(1, M):
        F_base[k]  = np.float64(F_base[k-1]  + np.float64(w_union_base[k]))
        F_delta[k] = np.float64(F_delta[k-1] + np.float64(w_union_delta[k]))

    # Sequential W1 summation
    w1 = np.float64(0.0)
    for k in range(M - 1):
        w1 = np.float64(
            w1
            + np.float64(abs(np.float64(F_base[k]) - np.float64(F_delta[k])))
            * np.float64(np.float64(union_support[k+1]) - np.float64(union_support[k]))
        )

    if not np.isfinite(w1):
        abort_kill(
            f"K3: W1 is non-finite ({float(w1)}) at delta={delta_label}",
            "K3",
            paths,
        )

    return w1, union_support, F_base, F_delta


# ── Decile localization (PROTOCOL_v1.0.md Section 10) ────────────────────────

def find_quantile_edge(
    union_support: np.ndarray,
    F_base: np.ndarray,
    q: np.float64,
) -> np.float64:
    """First support point where F_base >= q."""
    M = union_support.shape[0]
    for k in range(M):
        if np.float64(F_base[k]) >= q:
            return np.float64(union_support[k])
    return np.float64(union_support[M - 1])


def compute_decile_edges(
    base_union_support: np.ndarray,
    base_F_base: np.ndarray,
) -> np.ndarray:
    """
    9 decile edges from BASE CDF (delta=0). Fixed for all delta.
    edges[d] = first support point where F_base >= (d+1)*0.1, for d=0..8.
    """
    edges = np.empty(9, dtype=np.float64)
    for d in range(9):
        q = np.float64((d + 1) * 0.1)
        edges[d] = find_quantile_edge(base_union_support, base_F_base, q)
    return edges


def compute_decile_fractions(
    edges: np.ndarray,          # 9 edges from delta=0 BASE CDF (fixed)
    union_support: np.ndarray,  # current delta union support
    F_base: np.ndarray,         # current delta base CDF on union support
    F_delta: np.ndarray,        # current delta perturbed CDF on union support
    w1_total: np.float64,
) -> np.ndarray:
    """
    10 decile fractions per Section 10.

    Decile d covers:
      d=0:   x_left < edges[0]          (D1, lowest)
      d=k:   edges[k-1] <= x_left < edges[k]  for 1<=k<=8
      d=9:   x_left >= edges[8]         (D10, highest)

    Per-decile contribution: sum over intervals whose LEFT endpoint falls in decile.
    Fraction = per-decile contribution / w1_total.
    """
    M = union_support.shape[0]
    fractions = np.empty(10, dtype=np.float64)

    for d in range(10):
        contribution = np.float64(0.0)
        for k in range(M - 1):
            x_left = np.float64(union_support[k])
            if d == 0:
                in_decile = x_left < np.float64(edges[0])
            elif d == 9:
                in_decile = x_left >= np.float64(edges[8])
            else:
                in_decile = (
                    np.float64(edges[d - 1]) <= x_left
                    and x_left < np.float64(edges[d])
                )
            if in_decile:
                dx = np.float64(
                    np.float64(union_support[k + 1]) - x_left
                )
                contribution = np.float64(
                    contribution
                    + np.float64(abs(np.float64(F_base[k]) - np.float64(F_delta[k])))
                    * dx
                )
        if w1_total > np.float64(0.0):
            fractions[d] = np.float64(contribution / w1_total)
        else:
            fractions[d] = np.float64(0.0)

    return fractions


# ── Directional shift (PROTOCOL_v1.0.md Section 11) ──────────────────────────

def compute_mu_w(vp: np.ndarray, weights: np.ndarray) -> np.float64:
    """Σ w_i × vp_i, sequential for-loop, float64."""
    n = vp.shape[0]
    total = np.float64(0.0)
    for i in range(n):
        total = np.float64(total + np.float64(weights[i]) * np.float64(vp[i]))
    return total


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    repo_root = resolve_repo_root()
    paths     = build_paths(repo_root)
    out(f"repo_root={repo_root}")

    # Load artifacts
    ingest_path  = paths["INGEST_FILE"]
    perturb_path = paths["PERTURB_FILE"]
    if not ingest_path.exists():
        abort_kill(f"ingest.npz not found at {ingest_path}", "K1", paths)
    if not perturb_path.exists():
        abort_kill(f"perturbed_support.npz not found at {perturb_path}", "K1", paths)

    ingest_data  = np.load(ingest_path)
    perturb_data = np.load(perturb_path)

    vp_base      = np.asarray(ingest_data["vp"],           dtype=np.float64)
    weights_norm = np.asarray(ingest_data["weights_norm"], dtype=np.float64)

    n = vp_base.shape[0]
    if n != EXPECTED_N_ROWS:
        abort_kill(f"vp_base has {n} rows, expected {EXPECTED_N_ROWS}", "K1", paths)

    # Base weighted mean (for Δμ)
    mu_w_base = compute_mu_w(vp_base, weights_norm)

    # ── Pass 1: compute W1, CDFs for all delta ──────────────────────────────

    w1_values:         dict[str, np.float64]  = {}
    all_union_supports: dict[str, np.ndarray] = {}
    all_F_bases:        dict[str, np.ndarray] = {}
    all_F_deltas:       dict[str, np.ndarray] = {}
    delta_mu:           dict[str, np.float64] = {}
    classifications:    dict[str, str]        = {}

    for delta_f, label in zip(DELTA_GRID_FLOAT, DELTA_LABELS):
        delta_str = f"{delta_f:.3f}"
        vp_key    = f"vp_delta_{label}"
        vp_delta  = np.asarray(perturb_data[vp_key], dtype=np.float64)

        out(f"delta={delta_str}: computing W1...")
        w1, union_support, F_base, F_delta = compute_w1(
            vp_base, vp_delta, weights_norm, paths, delta_str
        )
        w1_values[delta_str]          = w1
        all_union_supports[delta_str] = union_support
        all_F_bases[delta_str]        = F_base
        all_F_deltas[delta_str]       = F_delta

        out(f"  W1 = {float(w1):.6e} km/s  (M={len(union_support)} union points)")

        # Per-delta classification
        if delta_f == 0.0:
            if w1 < W1_FLOOR_KM_S:
                classifications[delta_str] = "BASELINE_RECOVERED"
            else:
                classifications[delta_str] = "UNEXPECTED_BASELINE"
        else:
            if w1 >= W1_FLOOR_KM_S:
                classifications[delta_str] = "PERTURBATION_DETECTED"
            else:
                classifications[delta_str] = "BELOW_DETECTION_THRESHOLD"

        # Directional shift
        vp_key_perturb = f"vp_delta_{label}"
        mu_w_delta = compute_mu_w(
            np.asarray(perturb_data[vp_key_perturb], dtype=np.float64),
            weights_norm,
        )
        delta_mu[delta_str] = np.float64(mu_w_delta - mu_w_base)

    # ── Decile edges fixed from delta=0 base CDF ────────────────────────────

    out("computing decile edges from delta=0.000 base CDF...")
    edges = compute_decile_edges(
        all_union_supports["0.000"],
        all_F_bases["0.000"],
    )
    for d in range(9):
        out(f"  edge[{d}] (q={(d+1)*0.1:.1f}) = {float(edges[d]):.4f} km/s")

    # ── Pass 2: decile fractions for all delta ───────────────────────────────

    decile_fracs: dict[str, list] = {}
    for delta_f, label in zip(DELTA_GRID_FLOAT, DELTA_LABELS):
        delta_str = f"{delta_f:.3f}"
        fracs = compute_decile_fractions(
            edges,
            all_union_supports[delta_str],
            all_F_bases[delta_str],
            all_F_deltas[delta_str],
            w1_values[delta_str],
        )
        decile_fracs[delta_str] = [float(fracs[d]) for d in range(10)]
        frac_str = "  ".join(f"D{d+1}={float(fracs[d]):.4f}" for d in range(10))
        out(f"delta={delta_str} deciles: {frac_str}")

    # ── H4a — Nonlinear scaling (ratio test) ────────────────────────────────

    w1_010 = w1_values["0.010"]
    w1_090 = w1_values["0.090"]
    if np.float64(w1_010) > np.float64(0.0):
        ratio = np.float64(w1_090 / w1_010)
    else:
        ratio = np.float64(float("inf"))
    ratio_in_band = bool(H4A_RATIO_LOW <= ratio <= H4A_RATIO_HIGH)
    h4a_class = "FALSIFIED" if ratio_in_band else "CONFIRMED"

    # ── H4b — Non-uniform decile fractions ───────────────────────────────────

    h4b_any_outside = False
    for delta_f in DELTA_GRID_FLOAT:
        if delta_f == 0.0:
            continue
        delta_str = f"{delta_f:.3f}"
        for d in range(10):
            f_val = np.float64(decile_fracs[delta_str][d])
            if not (DECILE_LOW <= f_val <= DECILE_HIGH):
                h4b_any_outside = True
                break
        if h4b_any_outside:
            break
    # H4b CONFIRMED = fractions are non-uniform (some outside band)
    # H4b FALSIFIED = all fractions within band (uniform)
    h4b_class = "CONFIRMED" if h4b_any_outside else "FALSIFIED"

    # ── H4c — D10 localization ───────────────────────────────────────────────

    h4c_satisfied = False
    h4c_d10_vals: dict[str, float] = {}
    for delta_f in DELTA_GRID_FLOAT:
        if delta_f == 0.0:
            continue
        delta_str = f"{delta_f:.3f}"
        d10_frac = np.float64(decile_fracs[delta_str][9])   # index 9 = D10 (highest)
        h4c_d10_vals[delta_str] = float(d10_frac)
        if d10_frac >= D10_THRESHOLD:
            h4c_satisfied = True
    h4c_class = "CONFIRMED" if h4c_satisfied else "FALSIFIED"

    # ── Monotonicity check ───────────────────────────────────────────────────

    monotone_flag = "PASS"
    nonmono_details: list[str] = []
    for idx in range(len(DELTA_GRID_FLOAT) - 1):
        da = DELTA_GRID_FLOAT[idx]
        db = DELTA_GRID_FLOAT[idx + 1]
        wa = w1_values[f"{da:.3f}"]
        wb = w1_values[f"{db:.3f}"]
        if np.float64(wb) < MONOTONE_THRESHOLD * np.float64(wa):
            monotone_flag = "UNEXPECTED_NONMONOTONICITY"
            nonmono_details.append(
                f"W1({db:.3f})={float(wb):.6e} < 0.99*W1({da:.3f})={float(0.99 * float(wa)):.6e}"
            )

    # ── Report ───────────────────────────────────────────────────────────────

    out("")
    out(f"H4a: ratio = {float(ratio):.6f}  →  {h4a_class}")
    out(f"H4b: any_outside_band = {h4b_any_outside}  →  {h4b_class}")
    out(f"H4c: D10_satisfied = {h4c_satisfied}  →  {h4c_class}")
    out(f"Monotonicity: {monotone_flag}")
    if nonmono_details:
        for d in nonmono_details:
            out(f"  {d}")

    # ── Write metrics YAML ───────────────────────────────────────────────────

    metrics = {
        "protocol_sha256": EXPECTED_PROTOCOL_SHA,
        "timestamp":       utc_timestamp(),
        "w1_values_km_s":  {k: float(v) for k, v in w1_values.items()},
        "classifications":  classifications,
        "decile_fractions": decile_fracs,
        "delta_mu_km_s":   {k: float(v) for k, v in delta_mu.items()},
        "decile_edges_km_s": [float(edges[d]) for d in range(9)],
        "h4a": {
            "ratio":          float(ratio),
            "ratio_in_band":  ratio_in_band,
            "band":           [float(H4A_RATIO_LOW), float(H4A_RATIO_HIGH)],
            "classification": h4a_class,
        },
        "h4b": {
            "any_fraction_outside_band": h4b_any_outside,
            "uniform_band":              [float(DECILE_LOW), float(DECILE_HIGH)],
            "classification":            h4b_class,
        },
        "h4c": {
            "d10_satisfied":  h4c_satisfied,
            "d10_values":     h4c_d10_vals,
            "d10_threshold":  float(D10_THRESHOLD),
            "classification": h4c_class,
        },
        "monotonicity": {
            "flag":    monotone_flag,
            "details": nonmono_details,
        },
    }

    paths["OUTPUT_DIR"].mkdir(parents=True, exist_ok=True)
    with paths["METRICS_FILE"].open("w", encoding="utf-8") as f:
        yaml.safe_dump(metrics, f, sort_keys=False, allow_unicode=True)

    append_artifact_hash(paths["METRICS_FILE"], paths["HASH_LOG_FILE"], repo_root)

    # ── Append structured block to RESULTS.md ───────────────────────────────

    w1_block = "\n".join(
        f"- δ={d:.3f}: W1 = {float(w1_values[f'{d:.3f}']):.6e} km/s"
        f"  [{classifications[f'{d:.3f}']}]"
        for d in DELTA_GRID_FLOAT
    )

    decile_block = ""
    for delta_f in DELTA_GRID_FLOAT:
        if delta_f == 0.0:
            continue
        ds = f"{delta_f:.3f}"
        row = "  ".join(f"D{d+1}={decile_fracs[ds][d]:.4f}" for d in range(10))
        decile_block += f"- δ={ds}: {row}\n"
    decile_block = decile_block.rstrip("\n")

    dmu_block = "\n".join(
        f"- δ={d:.3f}: Δμ = {float(delta_mu[f'{d:.3f}']):.4f} km/s"
        for d in DELTA_GRID_FLOAT
    )

    nonmono_str = "; ".join(nonmono_details) if nonmono_details else "none"

    results_block = (
        f"\n"
        f"## Step 4 Execution Results — {utc_timestamp()}\n"
        f"\n"
        f"**Protocol SHA-256:** `{EXPECTED_PROTOCOL_SHA}`  \n"
        f"**OSF preregistration:** https://osf.io/fkx46  \n"
        f"**Status:** EXECUTION_COMPLETE\n"
        f"\n"
        f"### W1 values (km/s) and per-δ classification\n"
        f"\n"
        f"{w1_block}\n"
        f"\n"
        f"### H4a — Nonlinear scaling\n"
        f"\n"
        f"- W1(0.090) / W1(0.010) = {float(ratio):.6f}\n"
        f"- Band [8.5, 9.5]: ratio_in_band = {ratio_in_band}\n"
        f"- **H4a: {h4a_class}**\n"
        f"\n"
        f"### H4b — Non-uniform decile fractions\n"
        f"\n"
        f"- Any decile fraction outside [0.09, 0.11] at δ > 0: {h4b_any_outside}\n"
        f"- **H4b: {h4b_class}**\n"
        f"\n"
        f"### H4c — D10 localization (top decile ≥ 15%)\n"
        f"\n"
        f"- D10 ≥ 0.15 at any δ > 0: {h4c_satisfied}  "
        f"(values: {', '.join(f'δ={k} D10={v:.4f}' for k, v in h4c_d10_vals.items())})\n"
        f"- **H4c: {h4c_class}**\n"
        f"\n"
        f"### Decile fractions (δ > 0)\n"
        f"\n"
        f"{decile_block}\n"
        f"\n"
        f"### Directional shift Δμ(δ)\n"
        f"\n"
        f"{dmu_block}\n"
        f"\n"
        f"### Monotonicity check\n"
        f"\n"
        f"- Flag: {monotone_flag}\n"
        f"- Details: {nonmono_str}\n"
        f"\n"
        f"---\n"
    )
    append_text(paths["RESULTS_FILE"], results_block)

    # ── Transition STATE.yaml to EXECUTION_COMPLETE ──────────────────────────

    state_file = paths["STATE_FILE"]
    with state_file.open("r", encoding="utf-8") as f:
        state = yaml.safe_load(f)
    state["status"]      = "EXECUTION_COMPLETE"
    state["data_opened"] = True
    with state_file.open("w", encoding="utf-8") as f:
        yaml.safe_dump(state, f, sort_keys=False, allow_unicode=True,
                       default_flow_style=False)

    out("OK — metrics complete")
    out(f"artifacts: {paths['METRICS_FILE']}")
    out(f"results:   {paths['RESULTS_FILE']}")


if __name__ == "__main__":
    main()
