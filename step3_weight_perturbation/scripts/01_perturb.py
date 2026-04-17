#!/usr/bin/env python3
"""
01_perturb.py — BH GC Orbit Measure Perturbation Audit (Step 3)

Computes rank-based perturbation weights for each preregistered epsilon.

Protocol alignment (Section 5, 6):
- Rank rows by e_i ascending; ties by original row index (stable).
- Centered rank score: f_i = (r_i - (N+1)/2) / ((N-1)/2)
- Perturbed raw weights: w_tilde_i(eps) = w_i * (1 + eps * f_i)
- Renormalize by sequential accumulation.
- K2: if any w_tilde_i <= 0 for a given eps, halt that eps, log deviation,
  continue with remaining eps values.
- All arithmetic in float64. Explicit Python loops. No vectorized reductions.

Outputs:
- outputs/perturbed_weights.npz: w_eps_0_00, w_eps_0_01, w_eps_0_05, w_eps_0_10
- logs/artifact_hashes.yaml updated
"""

from __future__ import annotations

import hashlib
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import yaml


EXPECTED_PROTOCOL_SHA = "9dbea01a2e81ff4b21e8c75e15ec73c10d96dfdf69495f6534d22b93e4102fe8"
EXPECTED_N_ROWS = 33079
EPSILON_GRID = [
    np.float64(0.00),
    np.float64(0.01),
    np.float64(0.05),
    np.float64(0.10),
]
REPO_ROOT_ENV = "BH_GC_AUDIT_REPO_ROOT"


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


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def sequential_sum(arr: np.ndarray) -> np.float64:
    total = np.float64(0.0)
    for i in range(arr.shape[0]):
        total = np.float64(total + np.float64(arr[i]))
    return np.float64(total)


def build_paths(repo_root: Path) -> dict[str, Path]:
    return {
        "REPO_ROOT":         repo_root,
        "INGEST_FILE":       repo_root / "outputs" / "ingest.npz",
        "PERTURBED_FILE":    repo_root / "outputs" / "perturbed_weights.npz",
        "HASH_LOG_FILE":     repo_root / "logs" / "artifact_hashes.yaml",
        "DEVIATIONS_FILE":   repo_root / "DEVIATIONS.md",
        "RESULTS_FILE":      repo_root / "RESULTS.md",
    }


def append_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(text)


def append_deviation(deviations_file: Path, script_name: str, message: str) -> None:
    timestamp = utc_timestamp()
    entry = (
        f"\n## Auto-logged deviation — {script_name}\n\n"
        f"- Timestamp (UTC): {timestamp}\n"
        f"- Script: {script_name}\n"
        f"- Deviation: {message}\n"
        f"- Logging mode: automatic\n"
    )
    append_text(deviations_file, entry)


def write_kill_result(results_file: Path, message: str, kill_code: str) -> None:
    timestamp = utc_timestamp()
    block = (
        f"\n## Step 3 Perturb Kill — {kill_code}\n\n"
        f"- Timestamp (UTC): {timestamp}\n"
        f"- Kill criterion: {kill_code}\n"
        f"- Details: {message}\n"
        f"- Protocol SHA-256: {EXPECTED_PROTOCOL_SHA}\n"
        f"- Status: EXECUTION_TERMINATED\n"
    )
    append_text(results_file, block)


def abort(message: str, paths: Optional[dict[str, Path]] = None, kill_code: Optional[str] = None) -> None:
    if kill_code and paths is not None:
        write_kill_result(paths["RESULTS_FILE"], message, kill_code)
    err("ABORT — " + str(message))
    raise SystemExit(1)


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

    abort("could not resolve repository root.")


def append_artifact_hash(path: Path, hash_log_file: Path, repo_root: Path) -> None:
    artifact_hash = sha256_file(path)
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


def compute_rank_scores(e_chain: np.ndarray) -> np.ndarray:
    """
    Rank rows by e_i ascending; ties by original row index (stable).
    Ranks r_i in {1, ..., N}.
    Centered rank score: f_i = (r_i - (N+1)/2) / ((N-1)/2)
    All arithmetic in float64.
    """
    n = e_chain.shape[0]

    # Build list of (e_i, row_index) for stable sort: sort by e_i, then row_index for ties.
    # Implemented as argsort with stable algorithm.
    # np.argsort with stable kind preserves order for equal keys → row-index tie-breaking.
    sort_indices = np.argsort(e_chain, kind="stable")
    # sort_indices[rank_0_based] = original_row_index
    # So row sort_indices[k] has rank (k+1) in 1-based.

    rank = np.empty(n, dtype=np.float64)
    for k in range(n):
        row_idx = int(sort_indices[k])
        rank[row_idx] = np.float64(k + 1)   # 1-based rank

    N = np.float64(n)
    half_range = (N - np.float64(1.0)) / np.float64(2.0)   # (N-1)/2
    mid        = (N + np.float64(1.0)) / np.float64(2.0)   # (N+1)/2

    f = np.empty(n, dtype=np.float64)
    for i in range(n):
        f[i] = (np.float64(rank[i]) - mid) / half_range

    return f


def perturb_weights(
    weights_norm: np.ndarray,
    f: np.ndarray,
    eps: np.float64,
    paths: dict[str, Path],
) -> Optional[np.ndarray]:
    """
    Compute perturbed and renormalized weights for given epsilon.
    Returns None if K2 fires (non-positive raw weight).
    K2 halt: per-epsilon, not full termination.
    """
    n = weights_norm.shape[0]

    # Raw perturbed weights: w_tilde_i = w_i * (1 + eps * f_i)
    w_tilde = np.empty(n, dtype=np.float64)
    for i in range(n):
        w_tilde[i] = np.float64(weights_norm[i]) * (np.float64(1.0) + eps * np.float64(f[i]))

    # K2 check: non-finite or non-positive
    for i in range(n):
        v = np.float64(w_tilde[i])
        if not np.isfinite(v):
            msg = f"K2: w_tilde[{i}] is non-finite ({v}) at eps={float(eps):.2f}"
            append_deviation(paths["DEVIATIONS_FILE"], "01_perturb.py", msg)
            err(f"K2 HALT (eps={float(eps):.2f}) — {msg}")
            return None
        if v <= np.float64(0.0):
            msg = f"K2: w_tilde[{i}] = {v} <= 0 at eps={float(eps):.2f}"
            append_deviation(paths["DEVIATIONS_FILE"], "01_perturb.py", msg)
            err(f"K2 HALT (eps={float(eps):.2f}) — {msg}")
            return None

    # Renormalize by sequential accumulation
    tilde_sum = sequential_sum(w_tilde)
    if not np.isfinite(tilde_sum) or tilde_sum <= np.float64(0.0):
        msg = f"K2: perturbed weight sum invalid ({tilde_sum}) at eps={float(eps):.2f}"
        append_deviation(paths["DEVIATIONS_FILE"], "01_perturb.py", msg)
        err(f"K2 HALT (eps={float(eps):.2f}) — {msg}")
        return None

    w_eps = np.empty(n, dtype=np.float64)
    for i in range(n):
        w_eps[i] = np.float64(w_tilde[i]) / tilde_sum

    return w_eps


def main() -> None:
    repo_root = resolve_repo_root()
    paths = build_paths(repo_root)

    # Load ingest output
    if not paths["INGEST_FILE"].exists():
        abort(f"ingest.npz not found: {paths['INGEST_FILE']}", paths=paths, kill_code="K1")

    data = np.load(paths["INGEST_FILE"])
    weights_norm = np.asarray(data["weights_norm"], dtype=np.float64)
    e_chain      = np.asarray(data["e_chain"],      dtype=np.float64)

    if weights_norm.shape[0] != EXPECTED_N_ROWS:
        abort(
            f"weights_norm length {weights_norm.shape[0]} != {EXPECTED_N_ROWS}",
            paths=paths, kill_code="K1",
        )

    out(f"Loaded ingest.npz: {weights_norm.shape[0]} rows")

    # Compute rank scores (once, shared across all epsilon)
    f = compute_rank_scores(e_chain)
    out(f"Rank scores: min={float(f.min()):.6f}, max={float(f.max()):.6f}")

    # Compute perturbed weights for each epsilon
    eps_key_map = {
        np.float64(0.00): "w_eps_0_00",
        np.float64(0.01): "w_eps_0_01",
        np.float64(0.05): "w_eps_0_05",
        np.float64(0.10): "w_eps_0_10",
    }

    results: dict[str, np.ndarray] = {}
    k2_fired_any = False

    for eps in EPSILON_GRID:
        key = eps_key_map[eps]
        out(f"Computing perturbed weights for eps={float(eps):.2f} ...")
        w_eps = perturb_weights(weights_norm, f, eps, paths)
        if w_eps is None:
            k2_fired_any = True
            out(f"  K2 fired for eps={float(eps):.2f} — skipped")
        else:
            results[key] = w_eps
            # Verify sum ≈ 1
            wsum = sequential_sum(w_eps)
            out(f"  eps={float(eps):.2f}: weight sum = {float(wsum):.17g}")

    if not results:
        abort(
            "K2 fired for all epsilon values — no perturbed weights produced.",
            paths=paths, kill_code="K2",
        )

    if k2_fired_any:
        out("WARNING: K2 fired for at least one epsilon. Continuing with remaining.")

    # Save perturbed_weights.npz
    paths["PERTURBED_FILE"].parent.mkdir(parents=True, exist_ok=True)
    np.savez(paths["PERTURBED_FILE"], **results)
    out(f"Saved {paths['PERTURBED_FILE']}")

    # Artifact hash
    paths["HASH_LOG_FILE"].parent.mkdir(parents=True, exist_ok=True)
    append_artifact_hash(paths["PERTURBED_FILE"], paths["HASH_LOG_FILE"], repo_root)

    out("OK — perturb complete")
    out(f"epsilon values produced: {list(results.keys())}")


if __name__ == "__main__":
    main()
