"""Self-test on a tiny synthetic horizon (16 canonical ticks, 24-tick warm start).

Checks implementation facts only. It does not look at, and says nothing about, the
study outcomes. Run after `run.py smoke` (which writes work/warm-1-smoke.pt).
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cpu_runtime  # noqa: E402

torch = cpu_runtime.install(1)
import run as R  # noqa: E402
import sc1_cpu  # noqa: E402
from gpu_stack.research import e001_semantic_consistency as sc1  # noqa: E402


def check(name: str, ok: bool, detail: str = "") -> None:
    print(("PASS " if ok else "FAIL ") + name + (" " + detail if detail else ""))
    if not ok:
        raise SystemExit(1)


def main() -> None:
    smoke = {"warm_ticks": 24, "canonical_ticks": 16}
    ds = str(R.DATASET_DEFAULT)
    # 1. fixed vs adaptive with no failures: identical endpoint, identical attempted tokens
    runs = {}
    for policy in ("fixed-local-checkpoint-restart", "adaptive-survivor-continuation"):
        runs[policy] = R.execute({"id": "t", "kind": "lc3", "warm_seed": 1, "stream_seed": 5, "stratum_id": "t",
                                  "policy": policy, "failures": [], "interrupted": False, "split": "calibration",
                                  "deps": []}, ds, smoke=smoke)["run"]
    a, b = runs.values()
    check("lc3 no-failure fixed == adaptive final NLL (bitwise)", a["final_held_out_nll"] == b["final_held_out_nll"])
    check("lc3 no-failure equal attempted tokens", a["attempted_tokens"] == b["attempted_tokens"] == 16 * 2048)
    # 2. determinism: same task twice
    again = R.execute({"id": "t", "kind": "lc3", "warm_seed": 1, "stream_seed": 5, "stratum_id": "t",
                       "policy": "fixed-local-checkpoint-restart", "failures": [], "interrupted": False,
                       "split": "calibration", "deps": []}, ds, smoke=smoke)["run"]
    check("lc3 deterministic across repeats", again["final_held_out_nll"] == a["final_held_out_nll"])
    # 3. failure accounting: fixed replays and discards, adaptive does not
    fx = R.execute({"id": "t", "kind": "lc3", "warm_seed": 1, "stream_seed": 5, "stratum_id": "t",
                    "policy": "fixed-local-checkpoint-restart", "failures": [[4, 4]], "interrupted": True,
                    "split": "evaluation", "deps": []}, ds, smoke=smoke)["run"]
    ad = R.execute({"id": "t", "kind": "lc3", "warm_seed": 1, "stream_seed": 5, "stratum_id": "t",
                    "policy": "adaptive-survivor-continuation", "failures": [[4, 4]], "interrupted": True,
                    "split": "evaluation", "deps": []}, ds, smoke=smoke)["run"]
    check("lc3 both reach canonical target", fx["target_reached"] and ad["target_reached"])
    check("lc3 fixed attempted >= adaptive attempted", fx["attempted_tokens"] >= ad["attempted_tokens"])
    check("lc3 canonical tokens equal", fx["canonical_tokens"] == ad["canonical_tokens"] == 16 * 2048)

    # 4. SC1 hook transparency: wrapped constant-LR sync run == direct engine run
    sc = R.load_scenario()
    scn = json.loads(R.SC1_SCENARIO.read_text())
    scn["work_contract"]["canonical_ticks"] = 16
    scn["optimization"]["evaluation_interval_ticks"] = 16
    scn["optimization"]["validation_batches"] = 4
    checkpoint, warm_summary = R._load_warm_for({"warm_seed": 1}, smoke)
    corpora = R._corpora(Path(ds), sc)
    fam = next(f for f in scn["evaluation_families"] if f["family_id"].startswith("E1"))
    fam = json.loads(json.dumps(fam))
    fam["seed"] = 77
    stratum = sc1._prepare_stratum(fam, split="evaluation", wan_round_trip_seconds=0.005)
    cal = [sc1._prepare_stratum(s, split="calibration", wan_round_trip_seconds=0.005) for s in scn["calibration_strata"]]
    env = sc1._calibration_envelope(cal)
    meta = {"checkpoint_sha256": warm_summary["checkpoint_sha256"],
            "reference_local_site_gradient_seconds": 0.1, "reference_local_optimizer_apply_seconds": 0.01}
    direct = sc1._run_policy(scn, corpora, checkpoint, meta, stratum, split="evaluation",
                             policy_id="exact_forward_recovery", calibration_envelope=env)
    hooked = sc1_cpu.run_cell(scn, corpora, checkpoint, warm_summary["checkpoint_sha256"], stratum,
                              policy_id="exact_forward_recovery", cosine=False, ema_decays=[0.9, 0.99],
                              lr0=3e-4, envelope=env)
    check("sc1 EMA hooks do not change training (final NLL bitwise)",
          direct["final_held_out_nll"] == hooked["final_held_out_nll"])
    check("sc1 EMA evaluated once per decay at the final tick", sorted(hooked["ema_final_held_out_nll"]) == ["0.9", "0.99"]
          and hooked["ema_updates"] == 16)
    # restored after run: engine functions are the originals
    check("sc1 engine functions restored", sc1._train_step.__module__ == sc1.__name__)
    cos = sc1_cpu.run_cell(scn, corpora, checkpoint, warm_summary["checkpoint_sha256"], stratum,
                           policy_id="exact_forward_recovery", cosine=True, ema_decays=[],
                           lr0=3e-4, envelope=env)
    check("sc1 cosine run differs from constant-LR run", cos["final_held_out_nll"] != direct["final_held_out_nll"])
    # 5. unit checks
    c = sc1_cpu._Controls(lr0=3e-4, total_ticks=256, cosine=True, ema_decays=[])
    c.tick = 0
    check("cosine lr at tick 0", abs(c.lr() - 3e-4) < 1e-12)
    c.tick = 128
    check("cosine lr at tick 128", abs(c.lr() - 1.5e-4) < 1e-12)
    c.tick = 255
    check("cosine lr at tick 255 small", 0 < c.lr() < 1e-8 * 1e3 and c.lr() < 3e-4 * 1e-3)
    lin = torch.nn.Linear(2, 2, bias=False)
    holder = type("S", (), {"model": lin})()
    ctrl = sc1_cpu._Controls(lr0=1.0, total_ticks=4, cosine=False, ema_decays=[0.5])
    ctrl.primary_site = holder
    with torch.no_grad():
        lin.weight.fill_(0.0)
    ctrl.init_ema(torch)
    with torch.no_grad():
        lin.weight.fill_(1.0)
    ctrl.update_ema(torch)
    ctrl.update_ema(torch)
    check("ema arithmetic (0, then 1,1 at decay .5 -> .75)", abs(float(ctrl.ema[0.5]["weight"][0, 0]) - 0.75) < 1e-6)
    print("ALL PASS")


if __name__ == "__main__":
    main()
