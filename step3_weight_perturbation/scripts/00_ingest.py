#!/usr/bin/env python3
"""
00_ingest.py — BH GC Orbit Measure Perturbation Audit (Step 3)

Implements only the preregistered ingestion step.

Protocol alignment:
- Extract chains_redshift.txt from the published zip archive without
  permanently decompressing the chain into the tracked repo.
- Load columns 1, 2, 10, 12 in file row order.
- Validate K1 conditions.
- Normalize weights by strict sequential accumulation in Python loops.
- Compute N_eff by strict sequential accumulation.
- Compute v_p support once (reused for all epsilon in subsequent scripts).
- Persist deterministic ingestion artifacts only.

This script is intentionally limited to ingestion. It does not proceed to
perturbation, W1, metrics, or figures.

Governance note:
- A GM diagnostic breach auto-appends to DEVIATIONS.md.
- K4 (v_p non-finite or negative) terminates and writes to RESULTS.md.
- A K1 abort auto-appends a structured failure block to RESULTS.md
  before exiting.

Usage:
- Standard: python scripts/00_ingest.py
- Interactive/sandboxed: set BH_GC_AUDIT_REPO_ROOT=/abs/path/to/repo and run
- Self-tests only: python scripts/00_ingest.py --self-test
"""

from __future__ import annotations

import argparse
import hashlib
import io
import math
import os
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
import yaml


CHAIN_MEMBER = "chains_redshift.txt"
EXPECTED_PROTOCOL_SHA = "9dbea01a2e81ff4b21e8c75e15ec73c10d96dfdf69495f6534d22b93e4102fe8"
EXPECTED_ZIP_SHA = "8397176cb6e996c21f64acadc77f470cf5412335a076a8e565e530ff52eb986a"
EXPECTED_N_ROWS = 33079
REPO_ROOT_ENV = "BH_GC_AUDIT_REPO_ROOT"

# Constants (protocol Section 3 / Section 7)
GM_SUN = np.float64(1.32712440018e20)   # m^3 s^-2 (IAU 2012)
YR_S   = np.float64(365.25 * 24.0 * 3600.0)  # seconds per year
PI     = np.float64(math.pi)


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


def is_repo_root(path: Path) -> bool:
    return (
        path.exists()
        and path.is_dir()
        and (path / "STATE.yaml").exists()
        and (path / "protocol" / "PROTOCOL_v1.0.md").exists()
    )


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def sequential_sum(values: Iterable[np.float64]) -> np.float64:
    total = np.float64(0.0)
    for value in values:
        total = np.float64(total + np.float64(value))
    return np.float64(total)


def build_paths(repo_root: Path) -> dict[str, Path]:
    return {
        "REPO_ROOT":       repo_root,
        "STATE_FILE":      repo_root / "STATE.yaml",
        "PROTOCOL_FILE":   repo_root / "protocol" / "PROTOCOL_v1.0.md",
        "DATA_ZIP":        repo_root / "data" / "raw" / "do2019_chains" / "aav8137_data_s3.zip",
        "OUTPUT_DIR":      repo_root / "outputs",
        "LOG_DIR":         repo_root / "logs",
        "OUTPUT_FILE":     repo_root / "outputs" / "ingest.npz",
        "MANIFEST_FILE":   repo_root / "logs" / "ingest_manifest.yaml",
        "HASH_LOG_FILE":   repo_root / "logs" / "artifact_hashes.yaml",
        "DEVIATIONS_FILE": repo_root / "DEVIATIONS.md",
        "RESULTS_FILE":    repo_root / "RESULTS.md",
    }


def append_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(text)


def write_kill_result(results_file: Path, message: str, kill_code: str) -> None:
    timestamp = utc_timestamp()
    block = (
        f"\n## Step 3 Ingest Kill — {kill_code}\n\n"
        f"- Timestamp (UTC): {timestamp}\n"
        f"- Kill criterion: {kill_code}\n"
        f"- Details: {message}\n"
        f"- Protocol SHA-256: {EXPECTED_PROTOCOL_SHA}\n"
        f"- Status: EXECUTION_TERMINATED\n"
    )
    append_text(results_file, block)


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


def abort(message: str, paths: Optional[dict[str, Path]] = None, kill_code: Optional[str] = None) -> None:
    if kill_code and paths is not None:
        write_kill_result(paths["RESULTS_FILE"], message, kill_code)
    err("ABORT — " + str(message))
    raise SystemExit(1)


def _candidate_paths_from_runtime() -> list[Path]:
    candidates: list[Path] = []

    env_root = os.environ.get(REPO_ROOT_ENV)
    if env_root:
        candidates.append(Path(env_root).expanduser().resolve())

    cwd = Path.cwd().resolve()
    candidates.append(cwd)
    candidates.extend(cwd.parents)

    file_obj: Optional[str] = globals().get("__file__")
    if file_obj:
        file_path = Path(file_obj).resolve()
        candidates.append(file_path.parent)
        candidates.append(file_path.parent.parent)
        candidates.extend(file_path.parent.parent.parents)

    deduped: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path)
        if key not in seen:
            seen.add(key)
            deduped.append(path)
    return deduped


def resolve_repo_root(explicit_repo_root: Optional[str] = None) -> Path:
    if explicit_repo_root:
        repo_root = Path(explicit_repo_root).expanduser().resolve()
        if not is_repo_root(repo_root):
            abort(
                "explicit repo root is invalid: "
                f"{repo_root}. Expected STATE.yaml and protocol/PROTOCOL_v1.0.md"
            )
        return repo_root

    candidates = _candidate_paths_from_runtime()
    for candidate in candidates:
        if is_repo_root(candidate):
            return candidate

    candidate_str = "\n".join(f"  - {p}" for p in candidates)
    abort(
        "could not resolve repository root. "
        f"Set {REPO_ROOT_ENV} to the repository path or run from within the repo. "
        "Checked candidates:\n"
        f"{candidate_str}"
    )


def ensure_gate(state_file: Path, protocol_file: Path, paths: dict[str, Path]) -> None:
    if not state_file.exists():
        abort(f"missing STATE.yaml: {state_file}", paths=paths, kill_code="K1")
    if not protocol_file.exists():
        abort(f"missing locked protocol file: {protocol_file}", paths=paths, kill_code="K1")

    with state_file.open("r", encoding="utf-8") as f:
        state = yaml.safe_load(f)

    if not isinstance(state, dict):
        abort("STATE.yaml did not parse to a mapping.", paths=paths, kill_code="K1")

    status = state.get("status")
    if status != "FROZEN_REGISTERED":
        abort(
            f"state.status={status!r}, expected 'FROZEN_REGISTERED'.",
            paths=paths,
            kill_code="K1",
        )

    protocol_sha_state = state.get("protocol_sha256")
    protocol_sha_actual = sha256_file(protocol_file)

    if protocol_sha_actual != EXPECTED_PROTOCOL_SHA:
        abort(
            "protocol file SHA mismatch: "
            f"actual={protocol_sha_actual}, expected={EXPECTED_PROTOCOL_SHA}.",
            paths=paths,
            kill_code="K1",
        )

    if protocol_sha_state != EXPECTED_PROTOCOL_SHA:
        abort(
            "STATE.yaml protocol_sha256 mismatch: "
            f"state={protocol_sha_state}, expected={EXPECTED_PROTOCOL_SHA}.",
            paths=paths,
            kill_code="K1",
        )


def extract_chain_bytes(zip_path: Path, paths: dict[str, Path]) -> tuple[bytes, str]:
    if not zip_path.exists():
        abort(f"K1: zip archive not found: {zip_path}", paths=paths, kill_code="K1")

    zip_sha = sha256_file(zip_path)
    if zip_sha != EXPECTED_ZIP_SHA:
        abort(
            "K1: zip SHA mismatch: "
            f"actual={zip_sha}, expected={EXPECTED_ZIP_SHA}.",
            paths=paths,
            kill_code="K1",
        )

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            if CHAIN_MEMBER not in names:
                abort(
                    "K1: chains_redshift.txt not found in archive. "
                    f"Members present: {names}",
                    paths=paths,
                    kill_code="K1",
                )
            with zf.open(CHAIN_MEMBER, "r") as member:
                return member.read(), zip_sha
    except zipfile.BadZipFile as exc:
        abort(f"K1: invalid zip archive: {exc}", paths=paths, kill_code="K1")


def load_required_columns(
    chain_bytes: bytes, paths: dict[str, Path]
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    try:
        data = np.loadtxt(
            io.BytesIO(chain_bytes),
            dtype=np.float64,
            comments=None,
            usecols=(0, 1, 9, 11),
            ndmin=2,
        )
    except Exception as exc:
        abort(f"K1: failed to parse chains_redshift.txt: {exc}", paths=paths, kill_code="K1")

    if data.shape[0] != EXPECTED_N_ROWS:
        abort(
            "K1: row count mismatch: "
            f"observed={data.shape[0]}, expected={EXPECTED_N_ROWS}.",
            paths=paths,
            kill_code="K1",
        )
    if data.shape[1] != 4:
        abort(
            f"K1: expected 4 loaded columns, got shape {data.shape}.",
            paths=paths,
            kill_code="K1",
        )

    weights_raw = np.asarray(data[:, 0], dtype=np.float64)
    gm_chain    = np.asarray(data[:, 1], dtype=np.float64)
    p_chain     = np.asarray(data[:, 2], dtype=np.float64)
    e_chain     = np.asarray(data[:, 3], dtype=np.float64)
    return weights_raw, gm_chain, p_chain, e_chain


def validate_required_columns(
    weights_raw: np.ndarray,
    gm_chain: np.ndarray,
    p_chain: np.ndarray,
    e_chain: np.ndarray,
    paths: dict[str, Path],
) -> None:
    for name, arr in {
        "weights_raw": weights_raw,
        "gm_chain": gm_chain,
        "p_chain": p_chain,
        "e_chain": e_chain,
    }.items():
        if arr.dtype != np.float64:
            abort(f"K1: {name} dtype is {arr.dtype}, expected float64.", paths=paths, kill_code="K1")
        if not np.isfinite(arr).all():
            abort(f"K1: non-finite values detected in {name}.", paths=paths, kill_code="K1")

    if (weights_raw < np.float64(0.0)).any():
        abort("K1: negative baseline weights detected.", paths=paths, kill_code="K1")

    raw_sum = sequential_sum(weights_raw)
    if not np.isfinite(raw_sum):
        abort("K1: raw weight sum is non-finite.", paths=paths, kill_code="K1")
    if raw_sum <= np.float64(0.0):
        abort(f"K1: raw weight sum must be > 0, got {raw_sum!r}.", paths=paths, kill_code="K1")


def normalize_weights(weights_raw: np.ndarray) -> tuple[np.ndarray, np.float64]:
    raw_sum = sequential_sum(weights_raw)
    weights_norm = np.empty(weights_raw.shape[0], dtype=np.float64)
    for i in range(weights_raw.shape[0]):
        weights_norm[i] = np.float64(weights_raw[i] / raw_sum)
    return weights_norm, np.float64(raw_sum)


def compute_neff(weights_norm: np.ndarray) -> np.float64:
    sum_sq = np.float64(0.0)
    for i in range(weights_norm.shape[0]):
        sum_sq = np.float64(sum_sq + np.float64(weights_norm[i] * weights_norm[i]))
    if not np.isfinite(sum_sq):
        raise ValueError("K1: sum of squared normalized weights is non-finite.")
    if sum_sq <= np.float64(0.0):
        raise ValueError(f"K1: sum of squared normalized weights must be > 0, got {sum_sq!r}.")
    return np.float64(np.float64(1.0) / sum_sq)


def compute_vp_support(
    gm_chain: np.ndarray,
    p_chain: np.ndarray,
    e_chain: np.ndarray,
    paths: dict[str, Path],
) -> np.ndarray:
    """Compute v_p for all rows (protocol Section 7). K4 check applied."""
    n = gm_chain.shape[0]
    vp = np.empty(n, dtype=np.float64)

    four = np.float64(4.0)
    one  = np.float64(1.0)
    thou = np.float64(1000.0)

    for i in range(n):
        GM_SI = np.float64(gm_chain[i]) * np.float64(1e6) * GM_SUN
        P_s   = np.float64(p_chain[i]) * YR_S
        a_m   = (GM_SI * P_s * P_s / (four * PI * PI)) ** (one / np.float64(3.0))
        ei    = np.float64(e_chain[i])
        vp[i] = np.float64(
            math.sqrt(GM_SI * (one + ei) / (a_m * (one - ei))) / thou
        )

    # K4: non-finite or negative
    for i in range(n):
        v = np.float64(vp[i])
        if not np.isfinite(v) or v < np.float64(0.0):
            abort(
                f"K4: vp[{i}] = {v} is non-finite or negative.",
                paths=paths,
                kill_code="K4",
            )

    return vp


def check_vp_diagnostic(vp: np.ndarray, paths: dict[str, Path]) -> list[str]:
    """Warn (not kill) if any v_p > 1e5 km/s."""
    warnings: list[str] = []
    threshold = np.float64(1e5)
    for i in range(vp.shape[0]):
        if np.float64(vp[i]) > threshold:
            msg = f"vp[{i}] = {float(vp[i]):.6g} km/s > 1e5 km/s"
            warnings.append(msg)

    if warnings:
        for w in warnings:
            append_deviation(paths["DEVIATIONS_FILE"], "00_ingest.py",
                             f"WARNING v_p diagnostic (not K4): {w}")
            err(f"WARNING — {w}")

    return warnings


def gm_range(gm_chain: np.ndarray) -> tuple[np.float64, np.float64]:
    current_min = np.float64(gm_chain[0])
    current_max = np.float64(gm_chain[0])
    for i in range(1, gm_chain.shape[0]):
        value = np.float64(gm_chain[i])
        if value < current_min:
            current_min = value
        if value > current_max:
            current_max = value
    return current_min, current_max


def log_gm_diagnostic_if_needed(
    gm_min: np.float64, gm_max: np.float64, paths: dict[str, Path]
) -> None:
    if gm_min < np.float64(0.1) or gm_max > np.float64(100.0):
        message = (
            f"GM diagnostic breach: range [{float(gm_min):.6g}, {float(gm_max):.6g}] "
            "outside [0.1, 100]"
        )
        append_deviation(paths["DEVIATIONS_FILE"], "00_ingest.py", message)
        err("WARNING — " + message + " — logged to DEVIATIONS.md")


def write_manifest(
    manifest_file: Path,
    log_dir: Path,
    weight_sum_raw: np.float64,
    n_eff: np.float64,
    gm_min: np.float64,
    gm_max: np.float64,
    zip_sha: str,
    vp_min: float,
    vp_max: float,
) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "n_rows":          int(EXPECTED_N_ROWS),
        "n_eff":           float(n_eff),
        "weight_sum_raw":  float(weight_sum_raw),
        "gm_min":          float(gm_min),
        "gm_max":          float(gm_max),
        "vp_min_km_s":     vp_min,
        "vp_max_km_s":     vp_max,
        "weights_valid":   True,
        "sha256_zip":      zip_sha,
        "source_member":   CHAIN_MEMBER,
        "protocol_sha256": EXPECTED_PROTOCOL_SHA,
        "timestamp":       utc_timestamp(),
    }
    with manifest_file.open("w", encoding="utf-8") as f:
        yaml.safe_dump(manifest, f, sort_keys=False, allow_unicode=True)


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


def run_self_tests() -> None:
    import tempfile

    arr = np.asarray([0.1, 0.2, 0.3], dtype=np.float64)
    total = sequential_sum(arr)
    assert np.isclose(total, np.float64(0.6)), f"unexpected sequential_sum: {total}"

    weights = np.asarray([1.0, 3.0], dtype=np.float64)
    norm, raw_sum = normalize_weights(weights)
    assert np.isclose(raw_sum, np.float64(4.0)), f"unexpected raw_sum: {raw_sum}"
    assert np.allclose(norm, np.asarray([0.25, 0.75], dtype=np.float64)), f"unexpected norm: {norm}"

    neff = compute_neff(np.asarray([0.5, 0.5], dtype=np.float64))
    assert np.isclose(neff, np.float64(2.0)), f"unexpected neff: {neff}"

    gm_min, gm_max = gm_range(np.asarray([4.0, 2.0, 3.0], dtype=np.float64))
    assert np.isclose(gm_min, np.float64(2.0)), f"unexpected gm_min: {gm_min}"
    assert np.isclose(gm_max, np.float64(4.0)), f"unexpected gm_max: {gm_max}"

    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    _write_line(stdout_buffer, "stdout message")
    _write_line(stderr_buffer, "stderr message")
    assert stdout_buffer.getvalue() == "stdout message\n", stdout_buffer.getvalue()
    assert stderr_buffer.getvalue() == "stderr message\n", stderr_buffer.getvalue()

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir).resolve()
        paths = build_paths(root)
        (root / "protocol").mkdir(parents=True, exist_ok=True)
        (root / "STATE.yaml").write_text(
            "status: FROZEN_REGISTERED\nprotocol_sha256: test\n", encoding="utf-8"
        )
        (root / "protocol" / "PROTOCOL_v1.0.md").write_text("locked\n", encoding="utf-8")
        assert is_repo_root(root), "expected temporary root to be recognized as repo root"
        resolved = resolve_repo_root(str(root))
        assert resolved == root, f"unexpected resolved root: {resolved}"

        append_deviation(paths["DEVIATIONS_FILE"], "00_ingest.py", "test deviation")
        deviation_text = paths["DEVIATIONS_FILE"].read_text(encoding="utf-8")
        assert "test deviation" in deviation_text, deviation_text

        write_kill_result(paths["RESULTS_FILE"], "test kill", "K1")
        results_text = paths["RESULTS_FILE"].read_text(encoding="utf-8")
        assert "Step 3 Ingest Kill — K1" in results_text, results_text

        try:
            abort("forced failure", paths=paths, kill_code="K1")
        except SystemExit as exc:
            assert exc.code == 1, f"unexpected exit code: {exc.code}"
        else:
            raise AssertionError("abort() did not raise SystemExit")

        log_gm_diagnostic_if_needed(np.float64(0.05), np.float64(4.0), paths)
        deviation_text_after_gm = paths["DEVIATIONS_FILE"].read_text(encoding="utf-8")
        assert "GM diagnostic breach" in deviation_text_after_gm, deviation_text_after_gm

    out("SELF-TESTS PASSED")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo-root",
        type=str,
        default=None,
        help="Explicit absolute or relative path to repository root.",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run internal self-tests and exit.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.self_test:
        run_self_tests()
        return

    repo_root = resolve_repo_root(args.repo_root)
    paths = build_paths(repo_root)

    ensure_gate(paths["STATE_FILE"], paths["PROTOCOL_FILE"], paths)

    chain_bytes, zip_sha = extract_chain_bytes(paths["DATA_ZIP"], paths)
    weights_raw, gm_chain, p_chain, e_chain = load_required_columns(chain_bytes, paths)
    validate_required_columns(weights_raw, gm_chain, p_chain, e_chain, paths)

    weights_norm, weight_sum_raw = normalize_weights(weights_raw)
    try:
        n_eff = compute_neff(weights_norm)
    except ValueError as exc:
        abort(str(exc), paths=paths, kill_code="K1")

    gm_min, gm_max = gm_range(gm_chain)
    log_gm_diagnostic_if_needed(gm_min, gm_max, paths)

    # v_p support — computed once, stored for all epsilon
    vp = compute_vp_support(gm_chain, p_chain, e_chain, paths)
    check_vp_diagnostic(vp, paths)

    # Scalar stats on vp for manifest
    vp_min_val = float(vp[0])
    vp_max_val = float(vp[0])
    for i in range(1, vp.shape[0]):
        v = float(vp[i])
        if v < vp_min_val:
            vp_min_val = v
        if v > vp_max_val:
            vp_max_val = v

    paths["OUTPUT_DIR"].mkdir(parents=True, exist_ok=True)
    np.savez(
        paths["OUTPUT_FILE"],
        weights_raw=weights_raw,
        weights_norm=weights_norm,
        gm_chain=gm_chain,
        p_chain=p_chain,
        e_chain=e_chain,
        vp=vp,
    )

    paths["LOG_DIR"].mkdir(parents=True, exist_ok=True)
    write_manifest(
        paths["MANIFEST_FILE"],
        paths["LOG_DIR"],
        weight_sum_raw,
        n_eff,
        gm_min,
        gm_max,
        zip_sha,
        vp_min_val,
        vp_max_val,
    )
    append_artifact_hash(paths["OUTPUT_FILE"],   paths["HASH_LOG_FILE"], repo_root)
    append_artifact_hash(paths["MANIFEST_FILE"], paths["HASH_LOG_FILE"], repo_root)

    out("OK — ingest complete")
    out(f"repo_root={repo_root}")
    out(f"rows={EXPECTED_N_ROWS}")
    out(f"n_eff={float(n_eff):.12f}")
    out(f"weight_sum_raw={float(weight_sum_raw):.17g}")
    out(f"gm_min={float(gm_min):.17g}")
    out(f"gm_max={float(gm_max):.17g}")
    out(f"vp_min={vp_min_val:.6g} km/s")
    out(f"vp_max={vp_max_val:.6g} km/s")


if __name__ == "__main__":
    main()
