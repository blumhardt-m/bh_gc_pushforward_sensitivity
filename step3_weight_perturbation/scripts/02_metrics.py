#!/usr/bin/env python3
"""
02_metrics.py — BH GC Orbit Measure Perturbation Audit (Step 3)

Compute W1(base, eps) for each preregistered epsilon, classify, write results.

Protocol alignment (Sections 9, 10, 12, 13):
- W1 exact algorithm: aggregate duplicates, union support, sequential CDF,
  W1 = sum |F_base - F_eps| * delta_x. No library W1.
- All reductions: explicit Python for-loops. No np.sum, np.cumsum.
- All scalars cast to float64 before use.
- CDF iteration over sorted union array only (no dict key order).
- K3: W1 non-finite → terminate.
- K5: v_p array mismatch across epsilon → terminate.
- Classification per Section 12; nonmonotonicity check across adjacent eps.
- Secondary metrics: mean shift, variance shift, W1/sigma_w.
- Outputs: outputs/metrics.yaml, RESULTS.md (append), logs/artifact_hashes.yaml.
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
OSF_URL = "https://osf.io/dmpes"
REPO_ROOT_ENV = "BH_GC_AUDIT_REPO_ROOT"

# Epsilon key mapping (matches 01_perturb.py)
EPS_KEY = {
    np.float64(0.00): "w_eps_0_00",
    np.float64(0.01): "w_eps_0_01",
    np.float64(0.05): "w_eps_0_05",
    np.float64(0.10): "w_eps_0_10",
}


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


def sequential_sum_arr(arr: np.ndarray) -> np.float64:
    total = np.float64(0.0)
    for i in range(arr.shape[0]):
        total = np.float64(total + np.float64(arr[i]))
    return np.float64(total)


def build_paths(repo_root: Path) -> dict[str, Path]:
    return {
        "REPO_ROOT":         repo_root,
        "INGEST_FILE":       repo_root / "outputs" / "ingest.npz",
        "PERTURBED_FILE":    repo_root / "outputs" / "perturbed_weights.npz",
        "METRICS_FILE":      repo_root / "outputs" / "metrics.yaml",
        "HASH_LOG_FILE":     repo_root / "logs" / "artifact_hashes.yaml",
        "DEVIATIONS_FILE":   repo_root / "DEVIATIONS.md",
        "RESULTS_FILE":      repo_root / "RESULTS.md",
        "OUTPUT_DIR":        repo_root / "outputs",
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
        f"\n## Step 3 Metrics Kill — {kill_code}\n\n"
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


def aggregate_duplicates(vp: np.ndarray, weights: np.ndarray) -> dict:
    """
    Aggregate duplicate float64 v_p values by summing weights.
    Row order preserved per protocol Section 9.
    Returns {float64_value: aggregated_weight}.
    """
    d: dict = {}
    for i in range(vp.shape[0]):
        key = np.float64(vp[i])
        w   = np.float64(weights[i])
        if key in d:
            d[key] = d[key] + w
        else:
            d[key] = w
    return d


def compute_w1(
    vp: np.ndarray,
    w_base: np.ndarray,
    w_eps: np.ndarray,
    paths: dict[str, Path],
    eps_label: str,
) -> np.float64:
    """
    W1(base, eps) via exact protocol algorithm (Section 9).
    Support is identical across measures (vp computed once),
    but aggregation is performed independently per protocol.
    """
    # Step: aggregate duplicates independently for each measure
    dict_base = aggregate_duplicates(vp, w_base)
    dict_eps  = aggregate_duplicates(vp, w_eps)

    # Step: union support (trivially same set since same vp, but algorithm
    # requires independent construction and union per Section 9)
    all_values: dict = {}
    for key in dict_base:
        all_values[key] = True
    for key in dict_eps:
        all_values[key] = True

    all_values_list = list(all_values.keys())
    all_values_list.sort()
    M = len(all_values_list)

    union_support = np.empty(M, dtype=np.float64)
    for k in range(M):
        union_support[k] = np.float64(all_values_list[k])

    # Verify strictly increasing
    for k in range(1, M):
        if not (union_support[k] > union_support[k-1]):
            abort(
                f"K3: union support not strictly increasing at index {k} for eps={eps_label}",
                paths=paths, kill_code="K3",
            )

    # Build weight arrays over union support
    w_union_base = np.empty(M, dtype=np.float64)
    w_union_eps  = np.empty(M, dtype=np.float64)
    for k in range(M):
        xk = union_support[k]
        w_union_base[k] = dict_base[xk] if xk in dict_base else np.float64(0.0)
        w_union_eps[k]  = dict_eps[xk]  if xk in dict_eps  else np.float64(0.0)

    # Sequential CDF accumulation (constraint 3 / Section 9 Step 2)
    F_base = np.empty(M, dtype=np.float64)
    F_eps  = np.empty(M, dtype=np.float64)
    F_base[0] = np.float64(w_union_base[0])
    F_eps[0]  = np.float64(w_union_eps[0])
    for k in range(1, M):
        F_base[k] = F_base[k-1] + np.float64(w_union_base[k])
        F_eps[k]  = F_eps[k-1]  + np.float64(w_union_eps[k])

    # W1 = sum_{k=1}^{M-1} |F_base(x_k) - F_eps(x_k)| * (x_{k+1} - x_k)
    W1 = np.float64(0.0)
    for k in range(M - 1):
        diff = np.float64(abs(np.float64(F_base[k]) - np.float64(F_eps[k])))
        gap  = np.float64(union_support[k+1]) - np.float64(union_support[k])
        W1   = W1 + diff * gap

    if not np.isfinite(W1):
        abort(
            f"K3: W1 is non-finite ({W1}) for eps={eps_label}",
            paths=paths, kill_code="K3",
        )

    return W1, union_support, F_base, F_eps


def weighted_mean(vp: np.ndarray, weights: np.ndarray) -> np.float64:
    mu = np.float64(0.0)
    for i in range(vp.shape[0]):
        mu = mu + np.float64(weights[i]) * np.float64(vp[i])
    return mu


def weighted_var(vp: np.ndarray, weights: np.ndarray, mu: np.float64) -> np.float64:
    var = np.float64(0.0)
    for i in range(vp.shape[0]):
        d = np.float64(vp[i]) - mu
        var = var + np.float64(weights[i]) * d * d
    return var


def classify_epsilon(eps: np.float64, W1: np.float64, sigma_w_base: np.float64) -> str:
    """Section 12 classification for a single epsilon."""
    if eps == np.float64(0.00):
        threshold = np.float64(0.01) * sigma_w_base
        if W1 < threshold:
            return "BASELINE_RECOVERED"
        else:
            return "UNEXPECTED_NONZERO_AT_BASELINE"
    else:
        if W1 == np.float64(0.0):
            return "UNEXPECTED_NULL"
        else:
            return "PERTURBATION_DETECTED"


def main() -> None:
    repo_root = resolve_repo_root()
    paths = build_paths(repo_root)

    # Load ingest output
    if not paths["INGEST_FILE"].exists():
        abort(f"ingest.npz not found: {paths['INGEST_FILE']}", paths=paths, kill_code="K3")
    if not paths["PERTURBED_FILE"].exists():
        abort(f"perturbed_weights.npz not found: {paths['PERTURBED_FILE']}", paths=paths, kill_code="K3")

    ingest_data   = np.load(paths["INGEST_FILE"])
    perturb_data  = np.load(paths["PERTURBED_FILE"])

    vp           = np.asarray(ingest_data["vp"],           dtype=np.float64)
    weights_base = np.asarray(ingest_data["weights_norm"], dtype=np.float64)

    if vp.shape[0] != EXPECTED_N_ROWS:
        abort(f"K5: vp length {vp.shape[0]} != {EXPECTED_N_ROWS}", paths=paths, kill_code="K5")
    if weights_base.shape[0] != EXPECTED_N_ROWS:
        abort(f"vp/weights length mismatch", paths=paths, kill_code="K5")

    out(f"Loaded vp ({vp.shape[0]} rows), base weights")

    # K5: verify all epsilon weight arrays have same length
    for eps in EPSILON_GRID:
        key = EPS_KEY[eps]
        if key not in perturb_data:
            out(f"  Note: {key} absent from perturbed_weights.npz (K2 fired for eps={float(eps):.2f})")
            continue
        w_eps_arr = perturb_data[key]
        if w_eps_arr.shape[0] != EXPECTED_N_ROWS:
            abort(
                f"K5: {key} length {w_eps_arr.shape[0]} != {EXPECTED_N_ROWS}",
                paths=paths, kill_code="K5",
            )

    # Base measure weighted mean and std (over base weights, computed once)
    mu_base  = weighted_mean(vp, weights_base)
    var_base = weighted_var(vp, weights_base, mu_base)
    sigma_base = np.float64(math.sqrt(float(var_base)))
    out(f"Base: mu={float(mu_base):.6f} km/s, sigma={float(sigma_base):.6f} km/s")

    # Per-epsilon metrics
    eps_results: list[dict] = []
    w1_values: list[float] = []
    cdf_data: dict = {}   # for figures: {eps_label: (union_support, F_base, F_eps)}

    for eps in EPSILON_GRID:
        key = EPS_KEY[eps]
        eps_label = f"{float(eps):.2f}"

        if key not in perturb_data:
            out(f"eps={eps_label}: SKIPPED (K2 fired)")
            eps_results.append({
                "epsilon":        float(eps),
                "status":         "K2_SKIPPED",
                "W1":             None,
                "classification": "K2_SKIPPED",
            })
            continue

        w_eps = np.asarray(perturb_data[key], dtype=np.float64)

        # W1 computation
        W1, union_support, F_base, F_eps = compute_w1(vp, weights_base, w_eps, paths, eps_label)
        out(f"eps={eps_label}: W1={float(W1):.6e} km/s")

        # Secondary metrics
        mu_eps  = weighted_mean(vp, w_eps)
        var_eps = weighted_var(vp, w_eps, mu_eps)
        mean_diff = np.float64(abs(float(mu_base) - float(mu_eps)))
        var_diff  = np.float64(abs(float(var_base) - float(var_eps)))
        ratio = W1 / sigma_base if sigma_base > np.float64(0.0) else np.float64(0.0)

        classification = classify_epsilon(eps, W1, sigma_base)
        out(f"  classification: {classification}")

        w1_values.append(float(W1))
        cdf_data[eps_label] = (union_support, F_base, F_eps)

        eps_results.append({
            "epsilon":        float(eps),
            "status":         "OK",
            "W1":             float(W1),
            "sigma_base":     float(sigma_base),
            "tolerance":      float(np.float64(0.01) * sigma_base),
            "ratio":          float(ratio),
            "mu_base":        float(mu_base),
            "mu_eps":         float(mu_eps),
            "mean_diff":      float(mean_diff),
            "var_base":       float(var_base),
            "var_eps":        float(var_eps),
            "var_diff":       float(var_diff),
            "classification": classification,
        })

    # Monotonicity check (Section 12): across adjacent OK eps values
    ok_entries = [(r["epsilon"], r["W1"]) for r in eps_results if r["status"] == "OK" and r["W1"] is not None]
    nonmonotonicity_flags: list[str] = []
    for idx in range(1, len(ok_entries)):
        eps_a, w1_a = ok_entries[idx - 1]
        eps_b, w1_b = ok_entries[idx]
        if eps_a < eps_b and eps_a > 0.0 and eps_b > 0.0:  # only among eps > 0
            if w1_b < 0.99 * w1_a:
                flag = (
                    f"UNEXPECTED_NONMONOTONICITY: W1(eps={eps_b:.2f})={w1_b:.6e} < "
                    f"0.99 * W1(eps={eps_a:.2f})={w1_a:.6e}"
                )
                nonmonotonicity_flags.append(flag)
                append_deviation(paths["DEVIATIONS_FILE"], "02_metrics.py", flag)
                err(f"WARNING — {flag}")
                # Mark in results
                for r in eps_results:
                    if r["epsilon"] == eps_b:
                        r["classification"] = "UNEXPECTED_NONMONOTONICITY"

    # Save metrics.yaml
    paths["OUTPUT_DIR"].mkdir(parents=True, exist_ok=True)
    metrics_out = {
        "timestamp":          utc_timestamp(),
        "protocol_sha256":    EXPECTED_PROTOCOL_SHA,
        "osf_url":            OSF_URL,
        "n_rows":             int(EXPECTED_N_ROWS),
        "mu_base":            float(mu_base),
        "sigma_base":         float(sigma_base),
        "var_base":           float(var_base),
        "epsilon_results":    eps_results,
        "nonmonotonicity":    nonmonotonicity_flags,
    }
    with paths["METRICS_FILE"].open("w", encoding="utf-8") as f:
        yaml.safe_dump(metrics_out, f, sort_keys=False, allow_unicode=True)
    out(f"Saved {paths['METRICS_FILE']}")

    append_artifact_hash(paths["METRICS_FILE"], paths["HASH_LOG_FILE"], repo_root)

    # RESULTS.md structured block
    timestamp_str = utc_timestamp()
    result_lines = [
        f"\n## Result 001 — bh_gc_orbit_measure_perturbation_audit",
        f"",
        f"Date: {timestamp_str[:10]}",
        f"Protocol SHA: {EXPECTED_PROTOCOL_SHA}",
        f"OSF: {OSF_URL}",
        f"",
        f"Base measure: mu_w = {float(mu_base):.6f} km/s, sigma_w = {float(sigma_base):.6f} km/s",
        f"",
    ]

    for r in eps_results:
        eps_str = f"{r['epsilon']:.2f}"
        if r["status"] == "K2_SKIPPED":
            result_lines.append(f"eps={eps_str}: K2 SKIPPED — see DEVIATIONS.md")
        else:
            result_lines.append(f"eps={eps_str}: {r['classification']}")
            result_lines.append(f"  W1           = {r['W1']:.6e} km/s")
            result_lines.append(f"  W1/sigma_w   = {r['ratio']:.6e}")
            result_lines.append(f"  mean_diff    = {r['mean_diff']:.6e} km/s")
            result_lines.append(f"  var_diff     = {r['var_diff']:.6e} (km/s)^2")
        result_lines.append("")

    if nonmonotonicity_flags:
        result_lines.append("Nonmonotonicity flags:")
        for flag in nonmonotonicity_flags:
            result_lines.append(f"  {flag}")
        result_lines.append("")

    # Overall interpretation (Section 17)
    all_ok = all(r["status"] == "OK" for r in eps_results)
    baseline_ok = any(
        r["epsilon"] == 0.00 and r["classification"] == "BASELINE_RECOVERED"
        for r in eps_results
    )
    perturbations_detected = all(
        r["classification"] == "PERTURBATION_DETECTED"
        for r in eps_results
        if r["status"] == "OK" and r["epsilon"] > 0.00
    )

    if all_ok and baseline_ok and perturbations_detected and not nonmonotonicity_flags:
        interp = (
            "Controlled perturbations of the empirical measure induce controlled "
            "divergence in the pushforward distribution, confirming that measure "
            "change — not algebraic reparameterization — is the operative pathway "
            "for non-null behavior in this audit program."
        )
    else:
        interp = (
            "Observed pattern deviates from expectation. Conclusion restricted to "
            "detected failure mode. See classification and DEVIATIONS.md."
        )

    result_lines.append(f"Interpretation: {interp}")
    result_lines.append("")

    append_text(paths["RESULTS_FILE"], "\n".join(result_lines))
    out(f"Appended result block to {paths['RESULTS_FILE']}")

    # Save CDF data for figures (pickle-free: embed in npz)
    # Pass via metrics.yaml path — figures will recompute CDFs from ingest + perturbed
    out("OK — metrics complete")


if __name__ == "__main__":
    main()
