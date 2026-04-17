#!/usr/bin/env python3
"""
03_perturb_support.py — BH GC Orbit Support Perturbation Audit (Step 4)

Apply deterministic support perturbation to eccentricity and recompute v_p.

Protocol alignment (PROTOCOL_v1.0.md, Sections 5–8, 14):
- Load e_chain, gm_chain, p_chain, weights_norm from outputs/ingest.npz.
- Compute rank scores f_i (same algorithm as 02_gate_delta.py).
- For each delta in DELTA_GRID:
    - Compute ẽ_i(delta) = e_i + delta * f_i
    - Validate domain K2: ẽ_i(delta) in (0, 1) for all i
    - Recompute v_p(delta)_i from (GM_i, P_i, ẽ_i(delta))
    - Validate K4: v_p(delta)_i non-finite or negative
- Save perturbed_support.npz: keys vp_delta_{label} and e_delta_{label}
- K2 or K4 aborts halt that delta; subsequent delta values are not computed.

Weights are UNCHANGED: w̃_i = w_i for all i and all delta.

Physical constants (PROTOCOL_v1.0.md Section 3):
  GM_SUN = 1.32712440018e20 m³ s⁻²
  YR_S   = 31557600.0 s yr⁻¹  (365.25 × 24 × 3600)
  PI     = math.pi
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

# Locked delta grid (PROTOCOL_v1.0.md Section 6; Decision 009)
DELTA_GRID: list[np.float64] = [
    np.float64(0.00),
    np.float64(0.010),
    np.float64(0.050),
    np.float64(0.090),
]

DELTA_KEY = {
    np.float64(0.00):  "vp_delta_0_000",
    np.float64(0.010): "vp_delta_0_010",
    np.float64(0.050): "vp_delta_0_050",
    np.float64(0.090): "vp_delta_0_090",
}
E_KEY = {
    np.float64(0.00):  "e_delta_0_000",
    np.float64(0.010): "e_delta_0_010",
    np.float64(0.050): "e_delta_0_050",
    np.float64(0.090): "e_delta_0_090",
}

# Physical constants
GM_SUN = np.float64(1.32712440018e20)
YR_S   = np.float64(365.25 * 24.0 * 3600.0)
PI     = np.float64(math.pi)


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
        "REPO_ROOT":         repo_root,
        "INGEST_FILE":       repo_root / "outputs" / "ingest.npz",
        "OUTPUT_FILE":       repo_root / "outputs" / "perturbed_support.npz",
        "OUTPUT_DIR":        repo_root / "outputs",
        "LOG_DIR":           repo_root / "logs",
        "HASH_LOG_FILE":     repo_root / "logs" / "artifact_hashes.yaml",
        "DEVIATIONS_FILE":   repo_root / "DEVIATIONS.md",
        "RESULTS_FILE":      repo_root / "RESULTS.md",
        "GATE_MANIFEST":     repo_root / "logs" / "gate_delta_manifest.yaml",
    }


def append_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(text)


def abort_kill(message: str, kill_code: str, paths: dict[str, Path],
               delta_label: Optional[str] = None) -> None:
    label_str = f" (delta={delta_label})" if delta_label else ""
    block = (
        f"\n## Step 4 Perturbation Kill — {kill_code}{label_str}\n\n"
        f"- Timestamp (UTC): {utc_timestamp()}\n"
        f"- Kill criterion: {kill_code}\n"
        f"- Details: {message}\n"
        f"- Protocol SHA-256: {EXPECTED_PROTOCOL_SHA}\n"
        f"- Status: EXECUTION_TERMINATED\n"
    )
    append_text(paths["RESULTS_FILE"], block)
    err(f"ABORT {kill_code} — {message}")
    raise SystemExit(1)


# ── Rank score computation (PROTOCOL_v1.0.md Section 5) ──────────────────────

def compute_rank_scores(e_chain: np.ndarray) -> np.ndarray:
    """
    f_i = (r_i - (N+1)/2) / ((N-1)/2)
    r_i = stable ascending rank of e_i (1-indexed).
    Explicit for-loop; no vectorized sort or assignment.
    """
    n          = e_chain.shape[0]
    mid        = np.float64((n + 1) / 2)
    half_range = np.float64((n - 1) / 2)

    rank         = np.empty(n, dtype=np.float64)
    sort_indices = np.argsort(e_chain, kind="stable")
    for k in range(n):
        row_idx        = int(sort_indices[k])
        rank[row_idx]  = np.float64(k + 1)

    f = np.empty(n, dtype=np.float64)
    for i in range(n):
        f[i] = (np.float64(rank[i]) - mid) / half_range

    return f


# ── Support perturbation and v_p recomputation ────────────────────────────────

def compute_perturbed_vp(
    e_chain:  np.ndarray,
    gm_si:    np.ndarray,   # pre-computed GM_SI_i array (m³ s⁻²); invariant across δ
    a_m:      np.ndarray,   # pre-computed a_m_i array (m);    invariant across δ
    f:        np.ndarray,
    delta:    np.float64,
    paths:    dict[str, Path],
) -> tuple[np.ndarray, np.ndarray]:
    """
    1. Compute ẽ_i = e_i + delta * f_i.
    2. Validate K2: ẽ_i in (0, 1) for all i (per-row, per-delta; immediate abort).
    3. Recompute v_p from pre-cached (GM_SI_i, a_m_i) and ẽ_i (protocol Section 8).
    4. Validate K4: v_p non-finite or negative (per-row).

    Returns (e_perturbed, vp_perturbed), both float64 arrays.
    gm_si and a_m are computed once in main() and passed here; they do not vary with δ.
    """
    n           = e_chain.shape[0]
    e_pert      = np.empty(n, dtype=np.float64)
    delta_label = f"{float(delta):.3f}"

    one  = np.float64(1.0)
    thou = np.float64(1000.0)

    # Step 1 & 2: perturb e, per-row K2 check
    for i in range(n):
        ei        = np.float64(e_chain[i])
        fi        = np.float64(f[i])
        e_pert[i] = ei + np.float64(delta) * fi
        if not (np.float64(0.0) < np.float64(e_pert[i]) < np.float64(1.0)):
            abort_kill(
                f"K2: e_pert[{i}] = {float(e_pert[i]):.6f} out of (0, 1) "
                f"at delta={float(delta):.3f} (e_i={float(ei):.6f}, f_i={float(fi):.6f})",
                "K2",
                paths,
                delta_label=delta_label,
            )

    # Step 3 & 4: recompute v_p using cached GM_SI and a_m; per-row K4 check
    vp_pert = np.empty(n, dtype=np.float64)
    for i in range(n):
        GM_SI_i = np.float64(gm_si[i])
        a_m_i   = np.float64(a_m[i])
        ei      = np.float64(e_pert[i])
        vp_pert[i] = np.float64(
            math.sqrt(GM_SI_i * (one + ei) / (a_m_i * (one - ei))) / thou
        )
        v = np.float64(vp_pert[i])
        if not np.isfinite(v) or v < np.float64(0.0):
            abort_kill(
                f"K4: vp_pert[{i}] = {float(v):.6g} km/s non-finite or negative "
                f"at delta={float(delta):.3f}",
                "K4",
                paths,
                delta_label=delta_label,
            )

    return e_pert, vp_pert


# ── Artifact logging ───────────────────────────────────────────────────────────

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
        with hash_log_file.open("r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f)
            if isinstance(loaded, dict):
                existing = loaded
    relative_key = str(path.resolve().relative_to(repo_root.resolve()))
    existing[relative_key] = artifact_hash
    with hash_log_file.open("w", encoding="utf-8") as f:
        yaml.safe_dump(existing, f, sort_keys=True, allow_unicode=True)


# ── Gate manifest check ───────────────────────────────────────────────────────

def check_gate_passed(paths: dict[str, Path]) -> None:
    """Abort if 02_gate_delta.py has not been run or if it did not pass."""
    gate_path = paths["GATE_MANIFEST"]
    if not gate_path.exists():
        abort_kill(
            "gate_delta_manifest.yaml not found; run 02_gate_delta.py before this script.",
            "K2",
            paths,
        )
    with gate_path.open("r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)
    if not isinstance(manifest, dict) or not manifest.get("gate_passed", False):
        abort_kill(
            "gate_delta_manifest.yaml reports gate_passed=False; "
            "execution is not authorized.",
            "K2",
            paths,
        )


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    repo_root = resolve_repo_root()
    paths = build_paths(repo_root)
    out(f"repo_root={repo_root}")

    # Require gate to have passed
    check_gate_passed(paths)

    ingest_path = paths["INGEST_FILE"]
    if not ingest_path.exists():
        abort_kill(
            f"ingest.npz not found at {ingest_path}; run 00_ingest.py first.",
            "K1",
            paths,
        )

    data          = np.load(ingest_path)
    e_chain       = np.asarray(data["e_chain"],       dtype=np.float64)
    gm_chain      = np.asarray(data["gm_chain"],      dtype=np.float64)
    p_chain       = np.asarray(data["p_chain"],       dtype=np.float64)
    weights_norm  = np.asarray(data["weights_norm"],  dtype=np.float64)

    if e_chain.shape[0] != EXPECTED_N_ROWS:
        abort_kill(
            f"e_chain has {e_chain.shape[0]} rows, expected {EXPECTED_N_ROWS}.",
            "K1",
            paths,
        )

    # Rank scores (same algorithm as 02_gate_delta.py)
    f = compute_rank_scores(e_chain)

    # Cache GM_SI and a_m (both depend only on GM and P, which are invariant across δ)
    n      = e_chain.shape[0]
    gm_si  = np.empty(n, dtype=np.float64)
    a_m    = np.empty(n, dtype=np.float64)
    four   = np.float64(4.0)
    one    = np.float64(1.0)
    for i in range(n):
        gm_si[i] = np.float64(gm_chain[i]) * np.float64(1e6) * GM_SUN
        P_s      = np.float64(p_chain[i]) * YR_S
        a_m[i]   = np.float64(
            (np.float64(gm_si[i]) * P_s * P_s / (four * PI * PI)) ** (one / np.float64(3.0))
        )

    # Perturb and recompute v_p for each delta
    results_e:  dict[str, np.ndarray] = {}
    results_vp: dict[str, np.ndarray] = {}

    for delta in DELTA_GRID:
        delta_label = f"{float(delta):.3f}"
        out(f"delta={delta_label}: computing...")
        e_pert, vp_pert = compute_perturbed_vp(
            e_chain, gm_si, a_m, f, delta, paths
        )
        e_key  = E_KEY[delta]
        vp_key = DELTA_KEY[delta]
        results_e[e_key]   = e_pert
        results_vp[vp_key] = vp_pert

        # Quick summary stats for log
        e_min  = float(e_pert[0])
        e_max  = float(e_pert[0])
        vp_min = float(vp_pert[0])
        vp_max = float(vp_pert[0])
        for i in range(1, n):
            ev = float(e_pert[i])
            vv = float(vp_pert[i])
            if ev < e_min:
                e_min = ev
            if ev > e_max:
                e_max = ev
            if vv < vp_min:
                vp_min = vv
            if vv > vp_max:
                vp_max = vv
        out(f"  e_pert range=[{e_min:.5f}, {e_max:.5f}]")
        out(f"  vp_pert range=[{vp_min:.4f}, {vp_max:.4f}] km/s")

    # Save combined output
    save_dict = {}
    save_dict.update(results_e)
    save_dict.update(results_vp)
    # Metadata: unchanged weights, rank scores, and explicit delta grid
    # (delta grid allows downstream scripts to iterate without hardcoding DELTA_GRID)
    save_dict["weights_norm"]  = weights_norm
    save_dict["rank_scores_f"] = f
    save_dict["delta_grid"]    = np.array([float(d) for d in DELTA_GRID], dtype=np.float64)

    paths["OUTPUT_DIR"].mkdir(parents=True, exist_ok=True)
    np.savez(paths["OUTPUT_FILE"], **save_dict)

    append_artifact_hash(paths["OUTPUT_FILE"], paths["HASH_LOG_FILE"], repo_root)

    out(f"Saved {paths['OUTPUT_FILE']}")
    out("OK — perturb_support complete")


if __name__ == "__main__":
    main()
