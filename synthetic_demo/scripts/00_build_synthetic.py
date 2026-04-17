#!/usr/bin/env python3
"""
00_build_synthetic.py — Synthetic Demo

Build deterministic baseline: e-grid, uniform weights, rank scores, v_base.
Pushforward: v(e) = sqrt((1+e)/(1-e)).
All arithmetic in float64 explicit loops.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import yaml

N = 10_000
E_MIN = np.float64(0.80)
E_MAX = np.float64(0.95)


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


def build_e_grid() -> np.ndarray:
    e = np.empty(N, dtype=np.float64)
    span  = np.float64(E_MAX - E_MIN)
    denom = np.float64(N - 1)
    for i in range(N):
        frac = np.float64(i) / denom
        e[i] = np.float64(E_MIN + frac * span)
    return e


def build_uniform_weights() -> np.ndarray:
    w     = np.empty(N, dtype=np.float64)
    value = np.float64(np.float64(1.0) / np.float64(N))
    for i in range(N):
        w[i] = value
    return w


def build_rank_scores(e: np.ndarray) -> np.ndarray:
    n     = e.shape[0]
    order = np.argsort(e, kind="stable")
    rank  = np.empty(n, dtype=np.float64)
    for k in range(n):
        rank[int(order[k])] = np.float64(k + 1)
    mid        = np.float64((n + 1) / 2)
    half_range = np.float64((n - 1) / 2)
    f = np.empty(n, dtype=np.float64)
    for i in range(n):
        f[i] = np.float64((np.float64(rank[i]) - mid) / half_range)
    return f


def pushforward_v(e: np.ndarray) -> np.ndarray:
    v = np.empty(e.shape[0], dtype=np.float64)
    for i in range(e.shape[0]):
        num  = np.float64(np.float64(1.0) + np.float64(e[i]))
        den  = np.float64(np.float64(1.0) - np.float64(e[i]))
        v[i] = np.float64(np.sqrt(num / den))
    return v


def main() -> None:
    repo_root   = Path(__file__).resolve().parent.parent
    outputs_dir = repo_root / "outputs"
    logs_dir    = repo_root / "logs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    e = build_e_grid()
    w = build_uniform_weights()
    f = build_rank_scores(e)
    v = pushforward_v(e)

    out_file = outputs_dir / "synthetic_base.npz"
    np.savez(
        out_file,
        e=e,
        weights=w,
        rank_scores_f=f,
        v_base=v,
        n_samples=np.asarray([N],     dtype=np.int64),
        e_min=np.asarray([E_MIN],     dtype=np.float64),
        e_max=np.asarray([E_MAX],     dtype=np.float64),
    )

    manifest = {
        "n_samples":   N,
        "e_min":       float(E_MIN),
        "e_max":       float(E_MAX),
        "weights":     "uniform",
        "pushforward": "sqrt((1+e)/(1-e))",
        "randomness":  "none",
    }
    manifest_file = logs_dir / "run_manifest.yaml"
    with manifest_file.open("w", encoding="utf-8") as fobj:
        yaml.safe_dump(manifest, fobj, sort_keys=False, allow_unicode=True)

    hash_log_file = logs_dir / "artifact_hashes.yaml"
    append_artifact_hash(out_file,      hash_log_file, repo_root)
    append_artifact_hash(manifest_file, hash_log_file, repo_root)
    print("OK — built synthetic base")


if __name__ == "__main__":
    main()
