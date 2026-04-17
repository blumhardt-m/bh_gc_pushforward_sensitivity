#!/usr/bin/env python3
"""
01_weight_axis.py — Synthetic Demo

Weight-axis analogue: w_i(eps) ∝ w_i(1 + eps*f_i), fixed support.
Support (v_base) is unchanged; only the measure is reweighted.

Keys in weight_axis.npz:
  eps_grid               — float64 array
  v_base                 — float64 array (reference support, unchanged)
  weights_eps_0_000      — normalized weights at eps=0.000
  weights_eps_0_010      — normalized weights at eps=0.010
  weights_eps_0_050      — normalized weights at eps=0.050
  weights_eps_0_100      — normalized weights at eps=0.100
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import yaml

EPS_GRID: list[float] = [0.00, 0.01, 0.05, 0.10]


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


def sequential_sum(values: np.ndarray) -> np.float64:
    total = np.float64(0.0)
    for i in range(values.shape[0]):
        total = np.float64(total + np.float64(values[i]))
    return total


def perturb_weights(
    weights: np.ndarray,
    f: np.ndarray,
    eps: float,
) -> np.ndarray:
    eps64  = np.float64(eps)
    n      = weights.shape[0]
    tilted = np.empty(n, dtype=np.float64)
    for i in range(n):
        tilted[i] = np.float64(np.float64(weights[i]) * (np.float64(1.0) + eps64 * np.float64(f[i])))
        if tilted[i] < np.float64(0.0):
            raise SystemExit(f"ABORT — negative perturbed weight at i={i}, eps={eps}")
    denom = sequential_sum(tilted)
    if not np.isfinite(denom) or denom <= np.float64(0.0):
        raise SystemExit(f"ABORT — invalid weight normalization at eps={eps}")
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        out[i] = np.float64(tilted[i] / denom)
    return out


def main() -> None:
    repo_root  = Path(__file__).resolve().parent.parent
    base       = np.load(repo_root / "outputs" / "synthetic_base.npz")
    weights    = np.asarray(base["weights"],      dtype=np.float64)
    f          = np.asarray(base["rank_scores_f"], dtype=np.float64)
    v          = np.asarray(base["v_base"],        dtype=np.float64)

    payload: dict = {
        "eps_grid": np.asarray(EPS_GRID, dtype=np.float64),
        "v_base":   v,
    }
    for eps in EPS_GRID:
        key = f"weights_eps_{eps:0.3f}".replace(".", "_")
        payload[key] = perturb_weights(weights, f, eps)

    out_file = repo_root / "outputs" / "weight_axis.npz"
    np.savez(out_file, **payload)
    append_artifact_hash(
        out_file,
        repo_root / "logs" / "artifact_hashes.yaml",
        repo_root,
    )
    print("OK — weight axis complete")


if __name__ == "__main__":
    main()
