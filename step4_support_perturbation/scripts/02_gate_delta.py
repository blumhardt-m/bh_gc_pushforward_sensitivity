#!/usr/bin/env python3
"""
02_gate_delta.py — BH GC Orbit Support Perturbation Audit (Step 4)

Pre-execution domain gate: verify that the locked delta grid satisfies
max(delta_grid) < 0.9 * delta_max, where delta_max is computed from the
actual chain data loaded by 00_ingest.py.

Protocol alignment (PROTOCOL_v1.0.md, Sections 5–6):
- Load e_chain from outputs/ingest.npz.
- Compute rank scores f_i via stable argsort and explicit for-loop.
- Compute delta_max = min_i { min((1-e_i)/|f_i|, e_i/|f_i|) } for |f_i| > 0.
- Verify: max(DELTA_GRID) < 0.9 * delta_max.
- Verify: delta_max value matches the preregistered value (0.10776) to 5
  significant figures (sanity check; chain is deterministic).
- Write gate manifest to logs/gate_delta_manifest.yaml.
- Abort with K2 if gate fails.

This script MUST run and pass before 03_perturb_support.py executes.
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


EXPECTED_PROTOCOL_SHA   = "e2f4db43da60cbc427b40091af7df7b587b97d7173f69eb7cc07436a606b5cc2"
EXPECTED_N_ROWS         = 33079
REPO_ROOT_ENV           = "BH_GC_AUDIT_REPO_ROOT"

# Locked delta grid (PROTOCOL_v1.0.md Section 6; Decision 009)
DELTA_GRID: list[np.float64] = [
    np.float64(0.00),
    np.float64(0.010),
    np.float64(0.050),
    np.float64(0.090),
]

# Preregistered gate values (PROTOCOL_v1.0.md Section 6)
PREREGISTERED_DELTA_MAX     = np.float64(0.10776)
PREREGISTERED_CEILING       = np.float64(0.09698)   # 0.9 * delta_max
PREREGISTERED_BINDING_ROW   = 190
PREREGISTERED_BINDING_E     = np.float64(0.89224)
PREREGISTERED_BINDING_F     = np.float64(1.000)
# Tolerance for sanity check against preregistered delta_max
DELTA_MAX_TOL               = np.float64(1e-4)


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
        "REPO_ROOT":        repo_root,
        "INGEST_FILE":      repo_root / "outputs" / "ingest.npz",
        "LOG_DIR":          repo_root / "logs",
        "GATE_MANIFEST":    repo_root / "logs" / "gate_delta_manifest.yaml",
        "HASH_LOG_FILE":    repo_root / "logs" / "artifact_hashes.yaml",
        "DEVIATIONS_FILE":  repo_root / "DEVIATIONS.md",
        "RESULTS_FILE":     repo_root / "RESULTS.md",
    }


def append_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(text)


def abort_k2(message: str, paths: dict[str, Path]) -> None:
    block = (
        f"\n## Step 4 Gate Kill — K2\n\n"
        f"- Timestamp (UTC): {utc_timestamp()}\n"
        f"- Kill criterion: K2\n"
        f"- Details: {message}\n"
        f"- Protocol SHA-256: {EXPECTED_PROTOCOL_SHA}\n"
        f"- Status: EXECUTION_TERMINATED\n"
    )
    append_text(paths["RESULTS_FILE"], block)
    err("ABORT K2 — " + message)
    raise SystemExit(1)


# ── Rank score computation (PROTOCOL_v1.0.md Section 5) ──────────────────────

def compute_rank_scores(e_chain: np.ndarray) -> np.ndarray:
    """
    f_i = (r_i - (N+1)/2) / ((N-1)/2)
    r_i = stable ascending rank of e_i (1-indexed).
    Explicit for-loop assignment.
    """
    n   = e_chain.shape[0]
    mid        = np.float64((n + 1) / 2)
    half_range = np.float64((n - 1) / 2)

    rank = np.empty(n, dtype=np.float64)
    sort_indices = np.argsort(e_chain, kind="stable")
    for k in range(n):
        row_idx = int(sort_indices[k])
        rank[row_idx] = np.float64(k + 1)

    f = np.empty(n, dtype=np.float64)
    for i in range(n):
        f[i] = (np.float64(rank[i]) - mid) / half_range

    return f


# ── Domain gate (PROTOCOL_v1.0.md Section 6) ─────────────────────────────────

def compute_delta_max(
    e_chain: np.ndarray,
    f: np.ndarray,
) -> tuple[np.float64, int]:
    """
    delta_max = min_i { min((1-e_i)/|f_i|, e_i/|f_i|) }  for |f_i| > 0

    Returns (delta_max, binding_row_index).
    """
    n = e_chain.shape[0]
    current_min  = np.float64(math.inf)
    binding_row  = -1

    for i in range(n):
        fi = np.float64(abs(np.float64(f[i])))
        if fi <= np.float64(0.0):
            continue
        ei = np.float64(e_chain[i])
        upper_margin = np.float64((np.float64(1.0) - ei) / fi)
        lower_margin = np.float64(ei / fi)
        row_max = upper_margin if upper_margin < lower_margin else lower_margin
        if row_max < current_min:
            current_min = row_max
            binding_row = i

    return np.float64(current_min), binding_row


# ── Gate manifest ─────────────────────────────────────────────────────────────

def write_gate_manifest(
    paths:         dict[str, Path],
    delta_max:     np.float64,
    binding_row:   int,
    binding_e:     float,
    binding_f:     float,
    ceiling:       np.float64,
    grid_max:      np.float64,
    gate_passed:   bool,
) -> None:
    paths["LOG_DIR"].mkdir(parents=True, exist_ok=True)
    manifest = {
        "protocol_sha256":         EXPECTED_PROTOCOL_SHA,
        "timestamp":               utc_timestamp(),
        "delta_max_computed":      float(delta_max),
        "delta_max_preregistered": float(PREREGISTERED_DELTA_MAX),
        "binding_row":             binding_row,
        "binding_e":               binding_e,
        "binding_f":               binding_f,
        "authorized_ceiling":      float(ceiling),
        "grid_max":                float(grid_max),
        "delta_grid":              [float(d) for d in DELTA_GRID],
        "gate_passed":             gate_passed,
    }
    with paths["GATE_MANIFEST"].open("w", encoding="utf-8") as f:
        yaml.safe_dump(manifest, f, sort_keys=False, allow_unicode=True)


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


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    repo_root = resolve_repo_root()
    paths = build_paths(repo_root)
    out(f"repo_root={repo_root}")

    ingest_path = paths["INGEST_FILE"]
    if not ingest_path.exists():
        abort_k2(f"ingest.npz not found at {ingest_path}; run 00_ingest.py first.", paths)

    data    = np.load(ingest_path)
    e_chain = np.asarray(data["e_chain"], dtype=np.float64)

    if e_chain.shape[0] != EXPECTED_N_ROWS:
        abort_k2(
            f"e_chain has {e_chain.shape[0]} rows, expected {EXPECTED_N_ROWS}.",
            paths,
        )

    # Rank scores
    f = compute_rank_scores(e_chain)

    # Delta_max
    delta_max, binding_row = compute_delta_max(e_chain, f)

    if binding_row < 0:
        abort_k2("no row with |f_i| > 0 found; cannot compute delta_max.", paths)

    binding_e = float(e_chain[binding_row])
    binding_f = float(f[binding_row])
    ceiling   = np.float64(0.9) * delta_max
    grid_max  = np.float64(max(float(d) for d in DELTA_GRID))

    out(f"delta_max={float(delta_max):.5f}")
    out(f"binding_row={binding_row}, e={binding_e:.5f}, f={binding_f:.3f}")
    out(f"authorized_ceiling={float(ceiling):.5f}")
    out(f"grid_max={float(grid_max):.3f}")

    # Sanity check: compare against preregistered delta_max
    delta_max_diff = abs(delta_max - PREREGISTERED_DELTA_MAX)
    if delta_max_diff > DELTA_MAX_TOL:
        msg = (
            f"delta_max sanity check FAILED: computed={float(delta_max):.5f}, "
            f"preregistered={float(PREREGISTERED_DELTA_MAX):.5f}, "
            f"diff={float(delta_max_diff):.6f} > tol={float(DELTA_MAX_TOL):.6f}"
        )
        append_text(
            paths["DEVIATIONS_FILE"],
            f"\n## Auto-logged deviation — 02_gate_delta.py\n\n"
            f"- Timestamp (UTC): {utc_timestamp()}\n"
            f"- Script: 02_gate_delta.py\n"
            f"- Deviation: {msg}\n"
            f"- Logging mode: automatic\n",
        )
        abort_k2(msg, paths)

    # Gate requirement: max(delta_grid) < ceiling
    gate_passed = bool(grid_max < ceiling)
    if not gate_passed:
        msg = (
            f"domain gate FAILED: grid_max={float(grid_max):.4f} >= "
            f"ceiling={float(ceiling):.5f}. "
            "Reduce max(delta_grid) or use a smaller safety margin."
        )
        write_gate_manifest(paths, delta_max, binding_row, binding_e,
                            binding_f, ceiling, grid_max, gate_passed=False)
        append_artifact_hash(paths["GATE_MANIFEST"], paths["HASH_LOG_FILE"], repo_root)
        abort_k2(msg, paths)

    write_gate_manifest(paths, delta_max, binding_row, binding_e,
                        binding_f, ceiling, grid_max, gate_passed=True)
    append_artifact_hash(paths["GATE_MANIFEST"], paths["HASH_LOG_FILE"], repo_root)

    out("GATE PASSED")
    out(f"  delta_max={float(delta_max):.5f}, ceiling={float(ceiling):.5f}, "
        f"grid_max={float(grid_max):.3f}")
    out(f"  Binding row {binding_row}: e={binding_e:.5f}, f={binding_f:+.3f}")
    out(f"  Constraint: (1 - {binding_e:.5f}) / {abs(binding_f):.3f} = "
        f"{(1.0 - binding_e) / abs(binding_f):.5f}")
    out("OK — gate_delta complete")


if __name__ == "__main__":
    main()
