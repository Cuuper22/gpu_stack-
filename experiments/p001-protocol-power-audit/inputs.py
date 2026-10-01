"""Measured inputs for the P001 audit, read from already-published E001/E002 artifacts.

Every number returned here is traceable to a file and field. Nothing is invented.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
E1 = "experiments/e001-beyond-one-datacenter/results/"
E2 = "experiments/e002-power-waveform-shaping/results/"
FILES = {
    "lc3": E1 + "equal-work-v1.json",
    "lc1": E1 + "learning-calibration-v1.json",
    "sc1": E1 + "semantic-consistency-v1.json",
    "pw2": E2 + "checkpoint-energy-v2.json",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _load(key: str):
    return json.loads((REPO / FILES[key]).read_text(encoding="utf-8"))


def _sd(x) -> float:
    return float(np.std(np.asarray(x, dtype=float), ddof=1))


def load_inputs() -> dict:
    lc3, sc1, pw2 = _load("lc3"), _load("sc1"), _load("pw2")
    out: dict = {"files": {k: {"path": v, "sha256": sha256(REPO / v)} for k, v in FILES.items()}}

    s = lc3["summary"]
    nll = s["paired_adaptive_minus_fixed_nll"]["values"]
    en_lc3 = s["adaptive_to_fixed_device_energy_ratio"]["values"]
    flop = s["paired_attempted_flop_savings"]["values"]
    p = pw2["summary"]
    en_pw2_sc = p["sparse_continuation_salvage"]["device_energy_ratio"]["values"]
    en_pw2_dc = p["lc3_corner_reproduction"]["dense_continue_to_sparse_restart_energy_ratio"]["values"]
    inter = p["primary_total_interaction"]["values"]
    nll_pw2 = p["sparse_continuation_salvage"]["nll_difference"]["values"]

    # SC1: per-run table, seed-to-seed spread of the exact-sync arm, and exact-equivalence check
    runs = [r for r in sc1["runs"] if r.get("final_held_out_nll") is not None]
    sync = {r["family_or_stratum_id"]: r for r in runs if r["policy_id"] == "synchronous_restart"}
    fwd = {r["family_or_stratum_id"]: r for r in runs if r["policy_id"] == "exact_forward_recovery"}
    sync_nll = [r["final_held_out_nll"] for r in sync.values()]
    sync_fwd_absdiff = max(abs(sync[k]["final_held_out_nll"] - fwd[k]["final_held_out_nll"]) for k in sync)
    table: dict = {}
    for r in runs:
        m = r["modeled_infrastructure"]
        table.setdefault(r["family_or_stratum_id"], {})[r["policy_id"]] = {
            "nll": r["final_held_out_nll"],
            "bytes": m["inter_site_payload_bytes"],
            "completion_s": m["completion_seconds"],
            "split": r["split"],
        }
    ev = {k: v for k, v in table.items() if v["synchronous_restart"]["split"] == "evaluation"}
    pe = sc1["summary"]["paired_effect_intervals"]
    wm = sc1["runs"][0]["modeled_infrastructure"]

    out["measured"] = {
        "lc3_nll_pair_values": nll,
        "lc3_nll_pair_sd": _sd(nll),
        "pw2_nll_equals_lc3_values": bool(np.allclose(nll, nll_pw2, rtol=0, atol=1e-12)),
        "lc3_energy_ratio_values_instantaneous_meter": en_lc3,
        "lc3_energy_ratio_sd_instantaneous_meter": _sd(en_lc3),
        "pw2_energy_ratio_sparse_continue_values": en_pw2_sc,
        "pw2_energy_ratio_sparse_continue_sd": _sd(en_pw2_sc),
        "pw2_energy_ratio_dense_continue_values": en_pw2_dc,
        "pw2_energy_ratio_dense_continue_sd": _sd(en_pw2_dc),
        "pw2_total_interaction_values": inter,
        "pw2_total_interaction_mean_over_sd": float(np.mean(inter) / _sd(inter)),
        "lc3_attempted_flop_saving_values": flop,
        "lc3_replay_quantum_fraction": 16384 / 540672,
        "sc1_sync_final_nll_by_stratum": sync_nll,
        "sc1_sync_final_nll_seed_sd": _sd(sync_nll),
        "sc1_exact_arms_max_abs_nll_difference_sync_vs_forward": float(sync_fwd_absdiff),
        "sc1_paired_nll_diff_values": pe["adaptive_minus_comparator_final_nll"]["values"],
        "sc1_paired_nll_diff_sd": _sd(pe["adaptive_minus_comparator_final_nll"]["values"]),
        "sc1_paired_payload_ratio_values": pe["adaptive_to_comparator_inter_site_payload_ratio"]["values"],
        "sc1_paired_time_ratio_values": pe["adaptive_to_comparator_modeled_completion_time_ratio"]["values"],
        "sc1_paired_regret_values": pe["adaptive_normalized_oracle_regret"]["values"],
        "sc1_gradient_payload_bytes_per_exchange": wm["gradient_payload_bytes_per_exchange"],
        "sc1_state_payload_bytes_per_exchange": wm["state_payload_bytes_per_exchange"],
    }
    # Arithmetic floors from the six evaluation families, using only available actions.
    floors = {}
    for fam, pol in ev.items():
        per = pol["periodic_local"]
        acts = {k: v for k, v in pol.items() if k in ("synchronous_restart", "exact_forward_recovery", "delayed_one_step", "periodic_local")}
        floors[fam] = {
            "periodic_bytes": per["bytes"],
            "min_action_bytes": min(v["bytes"] for v in acts.values()),
            "floor_payload_ratio_vs_periodic": min(v["bytes"] for v in acts.values()) / per["bytes"],
            "floor_payload_ratio_vs_sync": min(v["bytes"] for v in acts.values()) / pol["synchronous_restart"]["bytes"],
            "whole_policy_time_floor_ratio": min(v["completion_s"] for v in pol.values() if v.get("completion_s")) / per["completion_s"],
        }
    out["sc1_floors"] = floors
    out["sc1_floor_summary"] = {
        "payload_ratio_vs_periodic_min_over_families": min(f["floor_payload_ratio_vs_periodic"] for f in floors.values()),
        "payload_ratio_vs_sync_min_over_families": min(f["floor_payload_ratio_vs_sync"] for f in floors.values()),
        "time_floor_median_over_families": float(np.median([f["whole_policy_time_floor_ratio"] for f in floors.values()])),
        "time_floor_min_over_families": min(f["whole_policy_time_floor_ratio"] for f in floors.values()),
        "periodic_over_sync_bytes_ratio": 32 * wm["state_payload_bytes_per_exchange"] / (256 * wm["gradient_payload_bytes_per_exchange"]),
    }
    sd = out["measured"]["sc1_sync_final_nll_seed_sd"]
    out["measured"]["lc3_nll_pairs_in_clean_sd_units"] = [v / sd for v in nll]
    return out
