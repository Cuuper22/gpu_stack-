"""P001 runner: protocol power audit.

Usage (venv python, repo on PYTHONPATH, no package install):
  PYTHONPATH=<repo> <venv>/bin/python -B experiments/p001-protocol-power-audit/run.py --smoke
  PYTHONPATH=<repo> <venv>/bin/python -B experiments/p001-protocol-power-audit/run.py --full

--smoke uses tiny Monte Carlo sizes and writes results/smoke/. It only proves the code runs.
--full is for stage 2 only (after the protocol is frozen) and writes results/full/.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402
import scipy  # noqa: E402

import audit  # noqa: E402
import gates  # noqa: E402
import inputs as inp  # noqa: E402

EXPECTED_THRESHOLDS = {
    "E003": {"e003-quality-vector-equivalence": 0.2, "e003-run-equivalence": 0.95, "e003-critical-interception": 0.99,
             "e003-clean-false-action": 0.01, "e003-clean-time-tax": 0.02, "e003-clean-energy-tax": 0.02, "e003-redundant-flops": 0.5},
    "E004": {"e004-static-gain": 0.2, "e004-independent-gain": 0.1, "e004-interaction-size": 0.05, "e004-interaction-sign": 0.0,
             "e004-utility-noninferiority": 0.01, "e004-slo-noninferiority": 1.0, "e004-decision-regret": 0.1, "e004-interval-coverage": 0.8},
    "E005": {"e005-ce-gain": 0.25, "e005-task-family-noninferiority": 0.02, "e005-architecture-attribution": 0.5,
             "e005-ranking": 0.7, "e005-selection-regret": 0.1, "e005-search-energy": 0.25},
    "E006": {"e006-firm-load-fraction": 0.2, "e006-isolated-mechanism-gain": 1.5, "e006-delivery-confidence": 0.99, "e006-response-time": 10.0,
             "e006-sustained-delivery": 900.0, "e006-ttft-slo": 1.0, "e006-rebound": 0.05, "e006-request-utility": 0.01},
}


def clean(o):
    """Replace non-finite floats with None so the JSON is valid."""
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (float, np.floating)):
        return float(o) if np.isfinite(o) else None
    if isinstance(o, np.integer):
        return int(o)
    return o


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protocol_check() -> dict:
    """Load the machine-readable protocols and confirm the thresholds this audit assumes."""
    from gpu_stack.research import programs

    out = {}
    for eid, expected in EXPECTED_THRESHOLDS.items():
        proto = getattr(programs, f"{eid}_PROTOCOL")
        found = {f.falsifier_id: f.threshold for f in proto.falsifiers}
        mismatches = {k: (v, found.get(k)) for k, v in expected.items() if found.get(k) != v}
        out[eid] = {"protocol_hash": proto.protocol_hash, "mismatches": mismatches, "n_falsifiers": len(found)}
    return out


def git_head() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--smoke", action="store_true")
    mode.add_argument("--full", action="store_true")
    ap.add_argument("--n-sim", type=int, default=None)
    ap.add_argument("--draws", type=int, default=None)
    ap.add_argument("--seed", type=int, default=20261001)
    ap.add_argument("--out-dir", type=str, default=None, help="override output directory (default results/<mode>)")
    args = ap.parse_args()
    n_sim = args.n_sim or (150 if args.smoke else 10_000)
    draws = args.draws or (300 if args.smoke else 2_000)
    t0 = time.time()

    inputs = inp.load_inputs()
    pc = protocol_check()
    audit_out = audit.run_audit(inputs, n_sim, draws, args.seed)
    table = gates.build(audit_out["modules"], inputs, pc)
    protocol_md = {p: {"path": str(p), "sha256": sha(REPO / p)} for p in (gates.E3, gates.E4, gates.E5, gates.E6)}

    result = {
        "schema": "p001.protocol-power-audit.v1",
        "mode": "smoke" if args.smoke else "full",
        "smoke_note": "n_sim and bootstrap draws are tiny; numbers are NOT results." if args.smoke else None,
        "provenance": {
            "git_head": git_head(), "seed": args.seed, "n_sim": n_sim, "bootstrap_draws": draws,
            "python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__,
            "input_artifacts": inputs["files"], "protocol_markdown": protocol_md,
            "machine_readable_protocol_check": pc,
            "runtime_seconds": None,
        },
        "measured_inputs": inputs["measured"],
        "assumptions": audit_out["assumptions"],
        "protocol_rollup": gates.rollup(table),
        "gate_table": table,
        "modules": audit_out["modules"],
    }
    result["provenance"]["runtime_seconds"] = time.time() - t0
    out_dir = Path(args.out_dir) if args.out_dir else HERE / "results" / result["mode"]
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "results.json").write_text(json.dumps(clean(result), indent=1, sort_keys=True, allow_nan=False), encoding="utf-8")
    (out_dir / "gate_table.json").write_text(json.dumps(clean(table), indent=1, allow_nan=False), encoding="utf-8")
    bad = {k: v["mismatches"] for k, v in pc.items() if v["mismatches"]}
    print(f"{result['mode']}: {len(table)} gates, {time.time() - t0:.1f}s, protocol mismatches: {bad or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
