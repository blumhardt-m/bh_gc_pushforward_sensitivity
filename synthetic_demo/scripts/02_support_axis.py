#!/usr/bin/env python3
"""
02_support_axis.py — Synthetic Demo

Support-axis analogue: e_tilde_i(delta) = e_i + delta*f_i, fixed weights.
Weights are unchanged. delta_grid derived from delta_max at fractions
{0.00, 0.10, 0.50, 0.90}.

delta_max = min_i min((1-e_i)/|f_i|, e_i/|f_i|)  for |f_i| > 0.
Rows with f_i == 0 are skipped in the delta_max computation (no constraint).
No epsilon-regularization (+1e-12 hack) is used.

Keys in support_axis.npz:
  delta_max              — scalar float64 (1-element array)
  delta_grid             — float64 array, length 4
  weights                — unchanged base weights
  rank_scores_f          — rank scores f_i
  e_delta_<label>        — perturbed eccentricities at each delta
  v_delta_<label>        — pushforward v at each delta
where <label> = float value formatted to 6 decimal places with dots→underscores.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import yaml

GRID_FRACTIONS: list[float] = [0.00, 0.10, 0.50, 0.90]


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


def compute_delta_max(e: np.ndarray, f: np.ndarray) -> np.float64:
    """
    delta_max = min_i { min((1-e_i)/|f_i|, e_i/|f_i|) } for |f_i| > 0.
    Rows with f_i == 0 contribute no constraint and are skipped.
    """
    delta_max: np.float64 | None = None
    for i in range(e.shape[0]):
        abs_f = np.float64(abs(np.float64(f[i])))
        if abs_f == np.float64(0.0):
            continue
        upper = np.float64((np.float64(1.0) - np.float64(e[i])) / abs_f)
        lower = np.float64(np.float64(e[i]) / abs_f)
        local = upper if upper < lower else lower
        if delta_max is None or np.float64(local) < delta_max:
            delta_max = np.float64(local)
    if delta_max is None:
        raise SystemExit("ABORT — delta_max undefined: all f_i are zero")
    return delta_max


def pushforward_v(e: np.ndarray) -> np.ndarray:
    v = np.empty(e.shape[0], dtype=np.float64)
    for i in range(e.shape[0]):
        num  = np.float64(np.float64(1.0) + np.float64(e[i]))
        den  = np.float64(np.float64(1.0) - np.float64(e[i]))
        v[i] = np.float64(np.sqrt(num / den))
    return v


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    base      = np.load(repo_root / "outputs" / "synthetic_base.npz")
    e         = np.asarray(base["e"],             dtype=np.float64)
    w         = np.asarray(base["weights"],       dtype=np.float64)
    f         = np.asarray(base["rank_scores_f"], dtype=np.float64)

    delta_max  = compute_delta_max(e, f)
    delta_grid = np.empty(len(GRID_FRACTIONS), dtype=np.float64)
    for i in range(len(GRID_FRACTIONS)):
        delta_grid[i] = np.float64(np.float64(GRID_FRACTIONS[i]) * delta_max)

    print(f"delta_max = {float(delta_max):.8f}")
    print(f"delta_grid = {[float(d) for d in delta_grid]}")

    payload: dict = {
        "delta_max":    np.asarray([delta_max], dtype=np.float64),
        "delta_grid":   delta_grid,
        "weights":      w,
        "rank_scores_f": f,
    }

    for delta in delta_grid:
        n       = e.shape[0]
        e_tilde = np.empty(n, dtype=np.float64)
        for i in range(n):
            e_tilde[i] = np.float64(np.float64(e[i]) + np.float64(delta) * np.float64(f[i]))
            if not (np.float64(0.0) < np.float64(e_tilde[i]) < np.float64(1.0)):
                raise SystemExit(
                    f"ABORT — domain violation at i={i}, delta={float(delta):.12g}, "
                    f"e_i={float(e[i]):.6f}, f_i={float(f[i]):.6f}, "
                    f"e_tilde={float(e_tilde[i]):.8f}"
                )
        v_tilde = pushforward_v(e_tilde)
        label   = f"{float(delta):0.6f}".replace(".", "_")
        payload[f"e_delta_{label}"] = e_tilde
        payload[f"v_delta_{label}"] = v_tilde

    out_file = repo_root / "outputs" / "support_axis.npz"
    np.savez(out_file, **payload)
    append_artifact_hash(
        out_file,
        repo_root / "logs" / "artifact_hashes.yaml",
        repo_root,
    )
    print("OK — support axis complete")


if __name__ == "__main__":
    main()
