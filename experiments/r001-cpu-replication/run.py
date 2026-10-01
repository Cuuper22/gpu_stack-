"""R001 runner: CPU replication of E001-LC3 (Q1) and the SC1 averaging control (Q2).

Usage (PY = venv python, run from anywhere):
  PYTHONPATH=<repo> $PY experiments/r001-cpu-replication/run.py fetch
  PYTHONPATH=<repo> $PY experiments/r001-cpu-replication/run.py smoke
  PYTHONPATH=<repo> $PY experiments/r001-cpu-replication/run.py all        # stage 2 only
  PYTHONPATH=<repo> $PY experiments/r001-cpu-replication/run.py task <task_id>

Every task writes one JSON under results/raw/ and is skipped if that file exists
(resumable). Heavy intermediates (warm checkpoints, dataset) go under work/, which
is not meant to be committed. No evaluation outcome is printed during `all` except
the one-line task log (run id, seconds); analysis is analyze.py, run after the
calibration file exists.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import copy
import hashlib
import json
import multiprocessing as mp
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cpu_runtime  # noqa: E402

REPO = cpu_runtime.REPO
WORK = HERE / "work"
TINY = bool(os.environ.get("R001_TINY"))      # dry-run of the orchestrator on a 16-tick horizon
RESULTS = WORK / "tiny" if TINY else HERE / "results"
RAW = RESULTS / "raw"
SCENARIO_PATH = HERE / "scenario.json"
DATASET_DEFAULT = WORK / "0000.parquet"
SC1_SCENARIO = REPO / "experiments" / "e001-beyond-one-datacenter" / "semantic-consistency-scenario-v1.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_scenario() -> dict:
    return json.loads(SCENARIO_PATH.read_text())


def git_head() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# ----------------------------------------------------------------------------- tasks

def build_tasks(sc: dict, level: str = "L0") -> list[dict]:
    """Ordered task list. priority: lower runs first. level selects evaluation seeds / optional arms."""
    lv = sc["levels"][level]
    eval_seeds = list(lv["evaluation_warm_seeds"])
    tasks: list[dict] = []
    cal_seeds = list(lv["calibration_warm_seeds"])
    for tier, warm_seeds in ((0, cal_seeds), (1, eval_seeds)):
        for w in warm_seeds:
            tasks.append({"id": f"warm-{w}", "kind": "warm", "warm_seed": w, "deps": [], "prio": tier * 10})
    for item in (i for i in sc["lc3"]["calibration"] if i["warm_seed"] in cal_seeds):
        w = item["warm_seed"]
        for k, stream in enumerate(item["stream_seeds"]):
            policies = ["fixed-local-checkpoint-restart"] + (["adaptive-survivor-continuation"] if k == 0 else [])
            for policy in policies:
                tasks.append({"id": f"lc3cal-{w}-{stream}-{policy_short(policy)}", "kind": "lc3", "warm_seed": w,
                              "stream_seed": stream, "stratum_id": f"cal-{stream}", "policy": policy,
                              "failures": [], "interrupted": False, "split": "calibration",
                              "deps": [f"warm-{w}"], "prio": 1})
    for cell in (c for c in sc["sc1"]["calibration_cells"] if c["warm_seed"] in cal_seeds):
        for arm in sc["sc1"]["calibration_arms"]:
            tasks.append({"id": f"sc1-{cell['cell_id']}-{arm_short(arm)}", "kind": "sc1", "cell": cell, "arm": arm,
                          "split": "calibration", "deps": [f"warm-{cell['warm_seed']}"], "prio": 2})
    for pair in (p for p in sc["lc3"]["evaluation_pairs"] if p["warm_seed"] in eval_seeds):
        for policy in ("fixed-local-checkpoint-restart", "adaptive-survivor-continuation"):
            tasks.append({"id": f"lc3-{pair['pair_id']}-{policy_short(policy)}", "kind": "lc3",
                          "warm_seed": pair["warm_seed"], "stream_seed": pair["stream_seed"],
                          "stratum_id": pair["pair_id"], "policy": policy, "failures": pair["failures"],
                          "interrupted": True, "split": "evaluation",
                          "deps": [f"warm-{pair['warm_seed']}"], "prio": 12})
    for cell in (c for c in sc["sc1"]["evaluation_cells"] if c["warm_seed"] in eval_seeds):
        for arm in sc["sc1"]["evaluation_arms"]:
            if arm in sc["sc1"]["optional_arms"] and not lv["optional_arms"]:
                continue
            tasks.append({"id": f"sc1-{cell['cell_id']}-{arm_short(arm)}", "kind": "sc1", "cell": cell, "arm": arm,
                          "split": "evaluation", "deps": [f"warm-{cell['warm_seed']}"],
                          "optional": arm in sc["sc1"]["optional_arms"],
                          "prio": 20 if arm in sc["sc1"]["optional_arms"] else 13})
    return tasks


def policy_short(policy: str) -> str:
    return "fixed" if policy.startswith("fixed") else "adaptive"


def arm_short(arm: str) -> str:
    return arm.replace("exact_forward_recovery", "sync").replace("periodic_local", "local").replace("+cosine", "-cos")


def out_path(task_id: str) -> Path:
    return RAW / f"{task_id}.json"


# ----------------------------------------------------------------------------- worker side

_CACHE: dict = {}


def _corpora(dataset: Path, sc: dict):
    if "corpora" not in _CACHE:
        from gpu_stack.research import e001_learning_calibration as lc1
        _CACHE["corpora"] = lc1._load_byte_corpora(dataset, sc["dataset"])
    return _CACHE["corpora"]


def _engine_scenario(sc: dict, ticks_override: dict | None = None) -> dict:
    opt = dict(sc["optimization"])
    opt["warm_start_seed"] = 0
    opt["warm_start_ticks"] = sc["warm_start"]["ticks"]
    opt["warm_start_late_window_start_tick"] = sc["warm_start"]["ticks"] - 256
    opt["warm_start_max_window_nll_improvement"] = sc["warm_start"]["max_late_window_nll_improvement"]
    if ticks_override:
        opt.update(ticks_override)
    return {"model": sc["model"], "optimization": opt, "dataset": sc["dataset"]}


def _load_warm(warm_seed: int):
    import torch
    from gpu_stack.research import e001_learning_calibration as lc1
    data = torch.load(WORK / f"warm-{warm_seed}.pt", weights_only=False)
    return lc1._Checkpoint(**data["checkpoint"]), data["summary"]


def execute(task: dict, dataset: str, smoke: dict | None = None) -> dict:
    torch = cpu_runtime.install(num_threads=1)
    sc = load_scenario()
    dataset_path = Path(dataset)
    started = time.perf_counter()
    started_at = now()
    kind = task["kind"]
    if kind == "warm":
        import lc3_cpu
        corpora = _corpora(dataset_path, sc)
        scenario = _engine_scenario(sc)
        ticks = (smoke or {}).get("warm_ticks")
        checkpoint, summary = lc3_cpu.build_warm_checkpoint(
            scenario, corpora, int(task["warm_seed"]), ticks=ticks,
            progress_every=0 if smoke else 1024,
        )
        WORK.mkdir(parents=True, exist_ok=True)
        torch.save({"checkpoint": {
            "model_state": checkpoint.model_state, "optimizer_state": checkpoint.optimizer_state,
            "logical_tick": checkpoint.logical_tick, "merge_count": checkpoint.merge_count,
            "checkpoint_bytes": checkpoint.checkpoint_bytes}, "summary": summary},
            WORK / f"warm-{task['warm_seed']}{'-smoke' if smoke else ''}.pt")
        payload = {"summary": summary}
    elif kind == "lc3":
        import lc3_cpu
        corpora = _corpora(dataset_path, sc)
        override = {"canonical_target_ticks": (smoke or {}).get("canonical_ticks", 256)}
        if smoke:
            override["maximum_opportunity_ticks"] = 4 * smoke["canonical_ticks"]
        scenario = _engine_scenario(sc, override)
        checkpoint, warm_summary = _load_warm_for(task, smoke)
        arm = {"policy_id": task["policy"], "interrupted": bool(task["interrupted"])}
        stratum = {"stratum_id": task["stratum_id"], "seed": int(task["stream_seed"]),
                   "failures": task["failures"]}
        run = lc3_cpu._run_equal_work_arm(scenario, corpora, checkpoint, stratum, arm, split=task["split"])
        run["warm_summary_late_stage_gate_passed"] = warm_summary["late_window"]["late_stage_gate_passed"]
        payload = {"run": run}
    elif kind == "sc1":
        import sc1_cpu
        from gpu_stack.research import e001_semantic_consistency as sc1
        corpora = _corpora(dataset_path, sc)
        sc1_scn = json.loads(SC1_SCENARIO.read_text())
        sc1_scn["optimization"]["evaluation_interval_ticks"] = sc["sc1"]["overrides"]["evaluation_interval_ticks"]
        sc1_scn["optimization"]["validation_batches"] = sc["sc1"]["overrides"]["validation_batches"]
        if smoke:
            sc1_scn["work_contract"]["canonical_ticks"] = smoke["canonical_ticks"]
            sc1_scn["optimization"]["evaluation_interval_ticks"] = smoke["canonical_ticks"]
            sc1_scn["optimization"]["validation_batches"] = smoke.get("validation_batches", 4)
        checkpoint, warm_summary = _load_warm_for(task, smoke)
        cell = task["cell"]
        families = {f["family_id"]: f for f in sc1_scn["evaluation_families"]}
        families.update({f["stratum_id"]: f for f in sc1_scn["calibration_strata"]})
        stratum_src = copy.deepcopy(families[cell["family_id"]])
        stratum_src["seed"] = int(cell["stream_seed"])
        if smoke:  # compress the stress timeline to the smoke horizon: keep the first segments only
            for seg in stratum_src["segments"]:
                seg["start_tick"] = min(seg["start_tick"], smoke["canonical_ticks"] - 1)
                seg["end_tick"] = min(seg["end_tick"], smoke["canonical_ticks"] * 4)
        stratum = sc1._prepare_stratum(stratum_src, split=task["split"], wan_round_trip_seconds=0.005)
        cal = [sc1._prepare_stratum(s, split="calibration", wan_round_trip_seconds=0.005)
               for s in sc1_scn["calibration_strata"]]
        envelope = sc1._calibration_envelope(cal)
        base_arm = task["arm"].replace("+cosine", "")
        record = sc1_cpu.run_cell(
            sc1_scn, corpora, checkpoint, warm_summary["checkpoint_sha256"], stratum,
            policy_id=base_arm, cosine=task["arm"].endswith("+cosine"),
            ema_decays=sc["sc1"]["ema_decays"], lr0=float(sc["optimization"]["learning_rate"]),
            envelope=envelope, split=task["split"],
        )
        record["task_arm"] = task["arm"]
        payload = {"run": record}
    else:
        raise ValueError(kind)
    return {
        "task_id": task["id"], "kind": kind, "task": {k: v for k, v in task.items() if k != "deps"},
        "started_at": started_at, "finished_at": now(),
        "runtime_seconds": time.perf_counter() - started, "pid": os.getpid(), **payload,
    }


def _load_warm_for(task: dict, smoke: dict | None):
    import torch
    from gpu_stack.research import e001_learning_calibration as lc1
    seed = task["warm_seed"] if "warm_seed" in task else task["cell"]["warm_seed"]
    path = WORK / f"warm-{seed}{'-smoke' if smoke else ''}.pt"
    data = torch.load(path, weights_only=False)
    return lc1._Checkpoint(**data["checkpoint"]), data["summary"]


def worker(task: dict, dataset: str) -> str:
    result = execute(task, dataset, smoke={"warm_ticks": 24, "canonical_ticks": 16} if TINY else None)
    RAW.mkdir(parents=True, exist_ok=True)
    tmp = out_path(task["id"]).with_suffix(".tmp")
    tmp.write_text(json.dumps(result))
    tmp.rename(out_path(task["id"]))
    return task["id"]


# ----------------------------------------------------------------------------- orchestration

def manifest(sc: dict, dataset: Path) -> dict:
    engines = {name: sha256_file(REPO / "gpu_stack" / "research" / name) for name in (
        "e001_learning_calibration.py", "e001_lc2_quality_target.py",
        "e001_lc3_equal_work.py", "e001_semantic_consistency.py")}
    mine = {p.name: sha256_file(p) for p in sorted(HERE.glob("*.py"))}
    import torch
    return {
        "study_id": sc["study_id"], "git_head": git_head(), "started_at": now(),
        "scenario_sha256": sha256_file(SCENARIO_PATH),
        "protocol_sha256": sha256_file(HERE / "protocol.md") if (HERE / "protocol.md").exists() else None,
        "dataset_sha256": sha256_file(dataset), "dataset_expected_sha256": sc["dataset"]["sha256"],
        "engine_sha256": engines, "study_code_sha256": mine,
        "calibration_warm_seeds_all": sc["calibration_warm_seeds"], "evaluation_warm_seeds_all": sc["evaluation_warm_seeds"],
        "torch_version": torch.__version__, "python": platform.python_version(),
        "cpu": platform.processor() or "see /proc/cpuinfo", "cpu_count": os.cpu_count(),
        "threads_per_worker": 1, "workers": sc["optimization"]["workers"],
    }


def run_all(dataset: Path, workers: int, level: str, deadline_seconds: float | None = None) -> None:
    sc = load_scenario()
    if sha256_file(dataset) != sc["dataset"]["sha256"]:
        raise SystemExit("dataset sha256 mismatch")
    RAW.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    man = manifest(sc, dataset)
    man["level"] = level
    man["level_definition"] = sc["levels"][level]
    (RESULTS / "manifest.json").write_text(json.dumps(man, indent=1))
    tasks = build_tasks(sc, level)
    done = {t["id"] for t in tasks if out_path(t["id"]).exists()}
    pending = [t for t in tasks if t["id"] not in done]
    t0 = time.perf_counter()
    ctx = mp.get_context("spawn")
    running: dict = {}
    with cf.ProcessPoolExecutor(max_workers=workers, mp_context=ctx) as pool:
        while pending or running:
            ready = sorted((t for t in pending if all(d in done for d in t["deps"])), key=lambda t: t["prio"])
            if deadline_seconds is not None and time.perf_counter() - t0 > deadline_seconds:
                # stop launching; only optional tasks may be dropped, anything else is reported as unfinished
                dropped = [t["id"] for t in pending if t.get("optional")]
                if dropped:
                    print(f"deadline reached; optional tasks not launched: {len(dropped)}", flush=True)
                    (RESULTS / "not_launched.json").write_text(json.dumps(dropped))
                    pending[:] = [t for t in pending if not t.get("optional")]
                    ready = [t for t in ready if not t.get("optional")]
            while ready and len(running) < workers:
                t = ready.pop(0)
                pending.remove(t)
                running[pool.submit(worker, t, str(dataset))] = t["id"]
                print(f"[{time.perf_counter() - t0:7.0f}s] start {t['id']}", flush=True)
            finished, _ = cf.wait(list(running), return_when=cf.FIRST_COMPLETED)
            for fut in finished:
                task_id = running.pop(fut)
                fut.result()
                done.add(task_id)
                secs = json.loads(out_path(task_id).read_text())["runtime_seconds"]
                print(f"[{time.perf_counter() - t0:7.0f}s] done  {task_id} ({secs:.0f}s)", flush=True)
    man["finished_at"] = now()
    man["wall_seconds"] = time.perf_counter() - t0
    (RESULTS / "manifest.json").write_text(json.dumps(man, indent=1))


# ----------------------------------------------------------------------------- smoke

def smoke(dataset: Path) -> None:
    """Tiny-step smoke test. Prints seconds per step only; outcome metrics are not printed."""
    sc = load_scenario()
    torch = cpu_runtime.install(num_threads=1)
    out = HERE / "results" / "smoke"
    out.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    report: dict = {"measured_at": now(), "threads": 1}
    s = {"warm_ticks": 24, "canonical_ticks": 16}
    t = time.perf_counter()
    res = execute({"id": "smoke-warm", "kind": "warm", "warm_seed": 1, "deps": []}, str(dataset), smoke=s)
    w = time.perf_counter() - t
    report["warm_24_ticks_seconds"] = w
    report["warm_seconds_per_tick_including_2_evals_and_dataset_load"] = w / 24
    t = time.perf_counter()
    res = execute({"id": "smoke-warm2", "kind": "warm", "warm_seed": 2, "deps": []}, str(dataset), smoke={"warm_ticks": 88})
    w2 = time.perf_counter() - t
    report["warm_88_ticks_seconds"] = w2
    report["warm_seconds_per_tick_marginal"] = (w2 - w) / (88 - 24)
    # lc3 arms: fixed and adaptive, with a failure inside the 16-tick horizon
    fail = [[4, 4]]
    for policy in ("fixed-local-checkpoint-restart", "adaptive-survivor-continuation"):
        t = time.perf_counter()
        r = execute({"id": f"smoke-lc3-{policy_short(policy)}", "kind": "lc3", "warm_seed": 1, "stream_seed": 5,
                     "stratum_id": "smoke", "policy": policy, "failures": fail, "interrupted": True,
                     "split": "evaluation", "deps": []}, str(dataset), smoke=s)["run"]
        el = time.perf_counter() - t
        report[f"lc3_{policy_short(policy)}"] = {
            "seconds": el, "attempted_tokens": r["attempted_tokens"], "canonical_tokens": r["canonical_tokens"],
            "target_reached": r["target_reached"], "opportunity_ticks": r["opportunity_ticks_elapsed"],
            "checkpoint_count": r["checkpoint_count"],
            "local_active_seconds": r["local_active_seconds"],
            "seconds_per_quota_step_incl_overhead": r["local_active_seconds"] / max(1, r["attempted_tokens"] // 1024),
        }
    # sc1 arms
    sc1_cell = {"cell_id": "smoke", "warm_seed": 1, "family_id": "E2-low-wan-then-failure", "stream_seed": 7}
    for arm in ("exact_forward_recovery", "periodic_local", "exact_forward_recovery+cosine"):
        t = time.perf_counter()
        r = execute({"id": f"smoke-sc1-{arm_short(arm)}", "kind": "sc1", "cell": sc1_cell, "arm": arm,
                     "split": "evaluation", "deps": []}, str(dataset), smoke=s)["run"]
        el = time.perf_counter() - t
        report[f"sc1_{arm_short(arm)}"] = {
            "seconds": el, "attempted_tokens": r["exact_accounting"]["attempted_tokens"],
            "useful_tokens": r["exact_accounting"]["useful_tokens"],
            "violations": r["exact_accounting"]["work_contract_violations"],
            "ema_updates": r["ema_updates"], "ema_keys": sorted(r["ema_final_held_out_nll"]),
            "seconds_per_canonical_tick": r["physical_seconds"] / s["canonical_ticks"],
        }
    (out / "smoke.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1))


def probe(dataset: Path, workers: int) -> None:
    """Measure warm-start throughput with all workers busy, then project wall-clock per level.

    Uses a 192-tick warm build per worker (about 1-2 minutes). Projection scales the measured
    rate to the task mix with the constants below (measured on a quiet single process, then
    scaled by the probe's slowdown). Prints a recommendation; it never looks at any outcome.
    """
    sc = load_scenario()
    ctx = mp.get_context("spawn")
    ticks = 192
    t0 = time.perf_counter()
    with cf.ProcessPoolExecutor(max_workers=workers, mp_context=ctx) as pool:
        futs = [pool.submit(_probe_one, str(dataset), 7000 + i, ticks) for i in range(workers)]
        secs = [f.result() for f in futs]
    rate = sum(secs) / len(secs) / ticks          # seconds per warm tick with all workers busy
    quiet_rate = 0.27                              # s/tick, 4 workers on a quiet machine (inferred, see protocol)
    slow = rate / quiet_rate
    print(f"probe: {rate:.3f} s/warm-tick with {workers} workers ({slow:.2f}x the quiet-machine rate)")
    print("projected wall-clock (hours) = core-seconds / workers; core-seconds at quiet speed x slowdown")
    for level in ("L0", "L1", "L2"):
        tasks = build_tasks(sc, level)
        warm = sum(t["kind"] == "warm" for t in tasks) * sc["warm_start"]["ticks"] * quiet_rate
        lc3 = sum(t["kind"] == "lc3" for t in tasks) * 512 * 0.15 + sum(t["kind"] == "lc3" for t in tasks) * 6
        sc1 = sum(t["kind"] == "sc1" for t in tasks) * (256 * 0.47 + 15)
        total = (warm + lc3 + sc1) * slow
        print(f"  {level}: {total / workers / 3600:.2f} h  (warm {warm * slow / 3600:.1f} core-h, "
              f"lc3 {lc3 * slow / 3600:.1f}, sc1 {sc1 * slow / 3600:.1f})")


def _probe_one(dataset: str, seed: int, ticks: int) -> float:
    execute({"id": "probe", "kind": "warm", "warm_seed": seed, "deps": []}, dataset, smoke={"warm_ticks": ticks})
    # execute() includes dataset load; measure the pure loop from the summary instead
    data = __import__("torch").load(WORK / f"warm-{seed}-smoke.pt", weights_only=False)
    return float(data["summary"]["physical_seconds"])


def fetch() -> None:
    sc = load_scenario()
    WORK.mkdir(parents=True, exist_ok=True)
    target = DATASET_DEFAULT
    if target.exists() and sha256_file(target) == sc["dataset"]["sha256"]:
        print("dataset present, sha256 ok", target)
        return
    subprocess.run(["curl", "-sS", "-L", "--max-time", "1800", "-o", str(target), sc["dataset"]["uri"]], check=True)
    digest = sha256_file(target)
    print("sha256", digest, "OK" if digest == sc["dataset"]["sha256"] else "MISMATCH")
    if digest != sc["dataset"]["sha256"]:
        target.unlink()
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["fetch", "smoke", "all", "task", "list", "probe"])
    parser.add_argument("--level", default="L0", choices=["L0", "L1", "L2"])
    parser.add_argument("task_id", nargs="?")
    parser.add_argument("--dataset", default=str(DATASET_DEFAULT))
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--deadline-hours", type=float, default=None)
    args = parser.parse_args()
    if args.command == "fetch":
        fetch()
    elif args.command == "smoke":
        smoke(Path(args.dataset))
    elif args.command == "all":
        run_all(Path(args.dataset), args.workers, args.level, args.deadline_hours * 3600 if args.deadline_hours else None)
    elif args.command == "list":
        for level in ("L0", "L1", "L2"):
            tasks = build_tasks(load_scenario(), level)
            print(level, len(tasks), "tasks:", {k: sum(t["kind"] == k for t in tasks) for k in ("warm", "lc3", "sc1")})
    elif args.command == "probe":
        probe(Path(args.dataset), args.workers)
    else:
        task = next(t for t in build_tasks(load_scenario()) if t["id"] == args.task_id)
        print(worker(task, args.dataset))


if __name__ == "__main__":
    main()
