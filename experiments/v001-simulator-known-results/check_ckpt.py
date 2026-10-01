"""Checks 1 and 2: checkpoint/restart against closed forms, differential oracle, accounting.

Everything here treats gpu_stack as a black box that maps (durations, failure trace) to a
timeline and a work ledger.  See protocol.md for what each pass criterion means.
"""

from __future__ import annotations

import math
import time
from collections import Counter
from decimal import Decimal
from typing import Callable, Optional, Sequence

import numpy as np
from scipy import stats as sps

import analytic as A
import ckpt_driver as D
from ref_sim import TraceTooShort as RefShort
from ref_sim import gen_failures, ref_detail, ref_wall_ns

S = 1_000_000_000


# ----------------------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------------------

def _seed(*parts: int) -> np.random.Generator:
    return np.random.default_rng(np.random.SeedSequence(list(parts)))


def run_with_horizon(sc: D.Scenario, make_failures: Callable[[int], list], h0: int):
    """Engine run with a horizon that is doubled (same seed, prefix-stable) until the
    trace covers the whole run."""
    h = h0
    while True:
        f = make_failures(h)
        try:
            return D.run_engine(sc, f, h), f, h
        except D.TraceTooShort:
            h *= 2


# ----------------------------------------------------------------------------------------
# Check 1b: differential test, engine vs independent reference, trace by trace
# ----------------------------------------------------------------------------------------

def diff_cell(args) -> dict:
    """One configuration, `n_traces` random Poisson traces.  Returns category counts."""
    cfg, seed_base, n_traces = args
    sc = D.Scenario(step_ns=cfg["step_s"] * S, k=cfg["k"], n_segments=cfg["n_segments"],
                    ckpt_ns=cfg["ckpt_s"] * S, restart_fixed_ns=cfg["rfix_s"] * S,
                    transfer_ns=cfg["rxfer_s"] * S)
    cats: Counter = Counter()
    errors: Counter = Counter()
    mism = []
    for i in range(n_traces):
        down = [1, cfg["rfix_s"] * S, 3 * sc.restart_ns][i % 3]
        h0 = 60 * sc.n_segments * sc.segment_ns
        mtbf = int(cfg["mtbf_s"] * S)

        def mk(h, i=i, down=down):
            return gen_failures(_seed(seed_base, i), mtbf, down, h)
        h = h0
        while True:
            f = mk(h)
            try:
                wall, pred, _ = ref_detail(f, h, sc.n_segments, sc.k, sc.step_ns, sc.ckpt_ns, sc.restart_ns)
                break
            except RefShort:
                h *= 2
        try:
            eng = D.run_engine(sc, f, h)
            crashed = False
            err = ""
        except D.TraceTooShort:
            raise
        except Exception as exc:  # noqa: BLE001 - any engine exception is a finding
            crashed = True
            err = f"{type(exc).__name__}: {str(exc)[:90]}"
        if crashed:
            errors[err] += 1
            cats["engine_error_predicted" if pred else "engine_error_unpredicted"] += 1
        elif pred:
            cats["no_error_but_predicted"] += 1
        elif eng.wall_ns == wall:
            cats["match"] += 1
        else:
            cats["mismatch"] += 1
            mism.append({"i": i, "engine": eng.wall_ns, "ref": wall})
    return {"cfg": cfg, "n": n_traces, "cats": dict(cats), "errors": dict(errors),
            "mismatches": mism[:5]}


# ----------------------------------------------------------------------------------------
# Check 1a: statistical agreement with the closed form (atomic-segment driver, k = 1)
# ----------------------------------------------------------------------------------------

def stat_cell(args) -> dict:
    """One (regime, tau) cell: mean segment wall time from the engine and from the
    independent reference, against the closed form."""
    cell, seed_base, budget = args
    M = cell["M_s"]
    C, R, Dn = cell["C_s"], cell["R_s"], cell["D_s"]
    L_s = cell["L_s"]                              # tau + delta
    seg_ns = int(round(L_s * S))
    rest_ns = max(2, int(round(R * S)))
    sc = D.Scenario(step_ns=seg_ns - 1, k=1, n_segments=1, ckpt_ns=1,
                    restart_fixed_ns=rest_ns // 2, transfer_ns=rest_ns - rest_ns // 2)
    exact = A.expected_segment_time(L_s - C, C, M, sc.restart_ns / S, Dn)
    Ffail = math.exp(sc.restart_ns / S / M) * math.expm1(L_s / M)  # expected failures per segment
    n_per = int(min(40, max(1, 40 // max(Ffail, 1e-9))))
    n_seg_total = int(min(budget["max_seg"], max(budget["min_seg"], budget["fail_target"] / max(Ffail, 1e-9))))
    reps = max(20, math.ceil(n_seg_total / n_per))
    sc = D.Scenario(step_ns=seg_ns - 1, k=1, n_segments=n_per, ckpt_ns=1,
                    restart_fixed_ns=sc.restart_fixed_ns, transfer_ns=sc.transfer_ns)
    eng_t, ref_t, errs = [], [], 0
    mism = 0
    down_ns = max(1, int(round(Dn * S)))
    mtbf = int(M * S)
    h0 = int(4 * n_per * exact * S + 20 * seg_ns)
    t0 = time.time()
    for i in range(reps):
        rng_seed = (seed_base, cell["idx"], i)
        h = h0
        while True:
            f = gen_failures(_seed(*rng_seed), mtbf, down_ns, h)
            try:
                rw, _ = ref_wall_ns(f, h, n_per, sc.segment_ns, sc.restart_ns)
                break
            except RefShort:
                h *= 2
        ref_t.append(rw / S / n_per)
        try:
            e = D.run_engine(sc, f, h)
            eng_t.append(e.wall_ns / S / n_per)
            mism += int(e.wall_ns != rw)
        except D.TraceTooShort:
            raise
        except Exception:  # noqa: BLE001
            errs += 1
    out = {"cell": cell, "exact_E_seg": exact, "n_per_rep": n_per, "reps": reps,
           "engine_errors": errs, "engine_ne_ref": mism, "seconds": time.time() - t0}
    for name, arr in (("engine", eng_t), ("ref", ref_t)):
        a = np.asarray(arr)
        n = len(a)
        mean = float(a.mean())
        se = float(a.std(ddof=1) / math.sqrt(n)) if n > 1 else float("nan")
        out[name] = {"n": n, "mean": mean, "se": se, "rel_dev": mean / exact - 1.0,
                     "rel_se": se / exact, "z": (mean - exact) / se if se > 0 else float("nan")}
    # wasted-time fraction = 1 - tau / E[T_seg]  (tau = L - delta); delta method
    tau = L_s - C
    for name in ("engine", "ref"):
        m = out[name]["mean"]
        out[name]["waste"] = 1.0 - tau / m
        out[name]["waste_se"] = tau * out[name]["se"] / m ** 2
    out["waste_exact"] = 1.0 - tau / exact
    return out


def regime_cells(regimes: Sequence[dict], xs: Sequence[float], M_s: float = 100_000.0) -> list[dict]:
    cells = []
    idx = 0
    for reg in regimes:
        C = reg["c_over_m"] * M_s
        R = reg["r_over_m"] * M_s
        Dn = reg.get("d_over_m", 0.0) * M_s
        te = A.tau_exact(C, M_s, R, Dn)
        pts = [("grid", x, x * te) for x in xs]
        pts += [("young", None, A.tau_young(C, M_s)), ("daly1", None, max(A.tau_daly1(C, M_s), 1e-6 * M_s)),
                ("daly2", None, A.tau_daly2(C, M_s))]
        for label, x, tau in pts:
            cells.append({"idx": idx, "regime": reg["name"], "label": label, "x": x, "tau_s": tau,
                          "L_s": tau + C, "M_s": M_s, "C_s": C, "R_s": R, "D_s": Dn, "tau_exact_s": te})
            idx += 1
    return cells


def summarize_stat(results: list[dict], z_crit: float = 3.5) -> dict:
    out = {"cells": [], "by_regime": {}}
    zs_e, zs_r = [], []
    for r in results:
        c = r["cell"]
        out["cells"].append({k: r[k] for k in ("exact_E_seg", "n_per_rep", "reps", "engine_errors",
                                               "engine_ne_ref", "engine", "ref", "waste_exact")} | {"cell": c})
        if r["engine"]["n"] > 1:
            zs_e.append(r["engine"]["z"])
        zs_r.append(r["ref"]["z"])
    ze, zr = np.asarray(zs_e), np.asarray(zs_r)
    out["engine_z"] = {"n": int(len(ze)), "max_abs": float(np.nanmax(np.abs(ze))),
                       "chi2": float(np.nansum(ze ** 2)), "chi2_p": float(sps.chi2.sf(np.nansum(ze ** 2), len(ze)))}
    out["ref_z"] = {"n": int(len(zr)), "max_abs": float(np.nanmax(np.abs(zr))),
                    "chi2": float(np.nansum(zr ** 2)), "chi2_p": float(sps.chi2.sf(np.nansum(zr ** 2), len(zr)))}
    # pooled relative bias, inverse-variance weights
    for name in ("engine", "ref"):
        dev = np.array([r[name]["rel_dev"] for r in results if r[name]["n"] > 1])
        se = np.array([r[name]["rel_se"] for r in results if r[name]["n"] > 1])
        w = 1.0 / se ** 2
        pooled = float((w * dev).sum() / w.sum())
        pse = float(1.0 / math.sqrt(w.sum()))
        out[f"{name}_pooled_rel_bias"] = {"est": pooled, "se": pse, "ci95": [pooled - 1.96 * pse, pooled + 1.96 * pse]}
    out["engine_total_errors"] = int(sum(r["engine_errors"] for r in results))
    out["engine_ne_ref_total"] = int(sum(r["engine_ne_ref"] for r in results))
    # argmin per regime and formula-vs-simulation comparison (engine data)
    regs = sorted({r["cell"]["regime"] for r in results})
    for reg in regs:
        rs = [r for r in results if r["cell"]["regime"] == reg]
        grid = [r for r in rs if r["cell"]["label"] == "grid" and r["engine"]["n"] > 1]
        te = rs[0]["cell"]["tau_exact_s"]
        best = min(grid, key=lambda r: r["engine"]["waste"])
        plateau = []
        for r in grid:
            d = r["engine"]["waste"] - best["engine"]["waste"]
            sd = math.sqrt(r["engine"]["waste_se"] ** 2 + best["engine"]["waste_se"] ** 2)
            if d <= 2.0 * sd:
                plateau.append(r["cell"]["tau_s"])
        lo, hi = min(plateau), max(plateau)
        # step to the neighbouring grid points so that "inside the hull" is judged with one grid step slack
        taus = sorted(r["cell"]["tau_s"] for r in grid)
        lo_i, hi_i = taus.index(lo), taus.index(hi)
        lo_ext = taus[max(0, lo_i - 1)] if lo_i > 0 else lo
        hi_ext = taus[min(len(taus) - 1, hi_i + 1)] if hi_i < len(taus) - 1 else hi
        entry = {"tau_exact_s": te, "sim_argmin_tau_s": best["cell"]["tau_s"], "sim_argmin_x": best["cell"]["x"],
                 "plateau_tau_s": [lo, hi], "exact_in_plateau_hull": bool(lo <= te <= hi),
                 "exact_in_plateau_hull_one_step_slack": bool(lo_ext <= te <= hi_ext), "formulas": {}}
        # analytic waste at exact optimum is the reference for formula excess
        c0 = rs[0]["cell"]
        w_opt = A.waste_fraction(te, c0["C_s"], c0["M_s"], c0["R_s"], c0["D_s"])
        # measured waste at the exact optimum: use the x=1 grid cell
        x1 = [r for r in grid if abs(r["cell"]["x"] - 1.0) < 1e-9]
        for lab in ("young", "daly1", "daly2"):
            fr = [r for r in rs if r["cell"]["label"] == lab]
            if not fr or not x1:
                continue
            fr = fr[0]
            meas = fr["engine"]["waste"] - x1[0]["engine"]["waste"]
            sd = math.sqrt(fr["engine"]["waste_se"] ** 2 + x1[0]["engine"]["waste_se"] ** 2)
            pred = A.waste_fraction(fr["cell"]["tau_s"], c0["C_s"], c0["M_s"], c0["R_s"], c0["D_s"]) - w_opt
            entry["formulas"][lab] = {"tau_s": fr["cell"]["tau_s"], "tau_rel_err_vs_exact": fr["cell"]["tau_s"] / te - 1,
                                      "excess_waste_measured": meas, "excess_waste_analytic": pred,
                                      "se_diff": sd, "z_measured_vs_analytic": (meas - pred) / sd if sd > 0 else float("nan")}
        out["by_regime"][reg] = entry
    return out


# ----------------------------------------------------------------------------------------
# Check 2: accounting identities on random and adversarial failure sequences
# ----------------------------------------------------------------------------------------

def _dec(x: float) -> Decimal:
    return Decimal(str(x))


def account(run: D.EngineRun, failures: Sequence[tuple[int, int]]) -> list[str]:
    """Return the names of every identity violated by this run (empty list = all hold)."""
    sc = run.scenario
    rt = run.runtime
    bad: list[str] = []
    G, E = run.genesis_commit_ns, run.end_ns
    ledger = rt.work_ledger
    outs = ledger.outcomes
    w = sc.work_per_step
    fstarts = [f[0] for f in failures]

    # --- work accounting from raw outcome fields (not the ledger's own aggregate properties)
    for o in outs:
        if _dec(o.attempted_work) != _dec(o.committed_work) + _dec(o.lost_work):
            bad.append("A1_outcome_attempted_ne_committed_plus_lost")
            break
    tot_att = sum((_dec(o.attempted_work) for o in outs), Decimal(0))
    tot_com = sum((_dec(o.committed_work) for o in outs), Decimal(0))
    tot_lost = sum((_dec(o.lost_work) for o in outs), Decimal(0))
    if tot_att != tot_com + tot_lost:
        bad.append("A1_total_attempted_ne_committed_plus_lost")
    # independent expected attempted work, recomputed from the failure list
    for o in outs:
        a = o.attempt
        dur = a.planned_end_ns - a.start_ns
        hit = [f for f in failures if f[0] < a.planned_end_ns and f[1] > a.start_ns]
        if hit:
            fs = max(a.start_ns, min(h[0] for h in hit))
            exp_att = a.planned_work * (fs - a.start_ns) / dur
            if not (o.interrupted and o.execution_end_ns == fs):
                bad.append("A9_interruption_time_wrong")
        else:
            exp_att = a.planned_work
            if o.interrupted:
                bad.append("A9_spurious_interruption")
        if not math.isclose(float(o.attempted_work), exp_att, rel_tol=1e-12, abs_tol=1e-18):
            bad.append("A2_attempted_work_ne_recomputed")
            break
    # useful work: the finished job holds exactly total_steps of canonical work
    useful = float(sum((_dec(o.committed_work) for o in ledger.canonical_outcomes), Decimal(0)))
    if not math.isclose(useful, sc.total_steps * w, rel_tol=1e-9):
        bad.append("A3_useful_work_ne_job_size")
    cover: Counter = Counter()
    for o in ledger.canonical_outcomes:
        for ident in ledger.logical_identities_for(o):
            cover[ident.logical_step] += 1
    if set(cover) != set(range(1, sc.total_steps + 1)) or any(v != 1 for v in cover.values()):
        bad.append("A3_logical_steps_not_covered_exactly_once")
    # work <-> time link (forward and replay both run at 1 work-unit per second at rate 1;
    # replay at replay_rate)
    t_fwd = sum((o.execution_end_ns - o.attempt.start_ns) for o in outs if o.attempt.kind.value == "forward")
    t_rep = sum((o.execution_end_ns - o.attempt.start_ns) for o in outs if o.attempt.kind.value == "replay")
    w_fwd = sum(float(o.attempted_work) for o in outs if o.attempt.kind.value == "forward")
    w_rep = sum(float(o.attempted_work) for o in outs if o.attempt.kind.value == "replay")
    if not math.isclose(t_fwd / S, w_fwd, rel_tol=1e-9, abs_tol=1e-9):
        bad.append("A4_forward_time_ne_forward_work")
    if not math.isclose(t_rep / S * sc.replay_rate, w_rep, rel_tol=1e-6, abs_tol=1e-8):
        bad.append("A4_replay_time_ne_replay_work_over_rate")
    for o in outs:
        if o.attempt.kind.value == "replay" and not o.interrupted:
            exp_ns = math.ceil(Decimal(str(o.attempt.planned_work)) / Decimal(str(sc.replay_rate)) * S)
            if o.execution_end_ns - o.attempt.start_ns != exp_ns:
                bad.append("A10_replay_duration_ne_work_over_rate")
                break

    # --- wall clock must be tiled exactly by disjoint, labelled intervals
    intervals: list[tuple[int, int, str]] = []
    for o in outs:
        intervals.append((o.attempt.start_ns, o.execution_end_ns, o.attempt.kind.value))
    committed_ids = {m.checkpoint_id: m for m in rt.committed_manifests}
    for cid, step, ws, pc in run.scheduled:
        if step == 0:
            continue
        if cid in committed_ids:
            m = committed_ids[cid]
            intervals.append((m.checkpoint_write_started_at_ns, m.commit_at_ns, "ckpt"))
            if any(ws < fs < pc for fs in fstarts):
                bad.append("A8_checkpoint_committed_across_failure")
        else:
            hit = [fs for fs in fstarts if ws <= fs < pc]
            if not hit:
                bad.append("A8_checkpoint_aborted_without_failure")
            else:
                intervals.append((ws, min(hit), "ckpt_aborted"))
    for t in rt.restore_transfers:
        intervals.append((t.recovery_start_ns, t.execution_end_ns, "restore"))
    for fs, rec in failures:
        if fs < E:
            intervals.append((fs, min(rec, E), "down"))
    iv = sorted((a, b, n) for a, b, n in intervals if b > a and b > G and a < E)
    cur = G
    for a, b, n in iv:
        if a != cur:
            bad.append(f"A5_time_not_tiled_at_{'gap' if a > cur else 'overlap'}")
            break
        cur = b
    else:
        if cur != E:
            bad.append("A5_time_not_tiled_end")
    if run.wall_ns != E - G:
        bad.append("A5_wall_ne_end_minus_start")

    # --- checkpoint ordering and completed-work vs downtime
    steps = [m.committed_step for m in rt.committed_manifests]
    if steps != sorted(steps):
        bad.append("A8_checkpoint_steps_not_monotone")
    for o in outs:
        if not o.interrupted and any(f[0] < o.execution_end_ns and f[1] > o.attempt.start_ns for f in failures):
            bad.append("A9_completed_attempt_overlaps_downtime")
            break
    # restores: byte conservation
    for t in rt.restore_transfers:
        if t.attempted_bytes != t.completed_bytes + t.lost_bytes:
            bad.append("A7_restore_bytes")
            break
    if len(rt.restore_transfers) != run.recoveries_started:
        bad.append("A7_restore_count_ne_recoveries")
    return sorted(set(bad))


def _ensure_non_overlap(raw: list[tuple[int, int]]) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    last = 0
    for s, r in sorted(raw):
        s = max(s, last + 1, 2)
        r = max(r, s + 1)
        out.append((s, r))
        last = r
    return out


def make_random_trace(kind: str, rng: np.random.Generator, sc: D.Scenario, base_end_ns: int) -> list[tuple[int, int]]:
    L = sc.segment_ns
    if kind == "none":
        return []
    if kind.startswith("poisson"):
        mult = {"poisson_hi": 0.4, "poisson_mid": 1.5, "poisson_lo": 8.0}[kind]
        down = int(rng.choice([1, sc.restart_fixed_ns, 2 * sc.restart_ns]))
        return gen_failures(rng, int(mult * L), down, int(40 * base_end_ns))
    if kind == "burst":
        raw = []
        t = int(rng.uniform(0.1, 1.0) * base_end_ns)
        for _ in range(int(rng.integers(1, 4))):
            n = int(rng.integers(2, 5))
            for _j in range(n):
                gap = int(rng.choice([1, sc.restart_fixed_ns // 2 + 2, sc.restart_ns + 3, sc.step_ns // 2 + 1,
                                      sc.k * sc.step_ns]))
                t += gap
                raw.append((t, t + int(rng.choice([1, 7, sc.restart_fixed_ns]))))
                t = raw[-1][1]
            t += int(rng.uniform(0.2, 1.5) * base_end_ns)
        return _ensure_non_overlap(raw)
    raise ValueError(kind)


def boundary_traces(sc: D.Scenario, rng: np.random.Generator, n: int) -> list[list[tuple[int, int]]]:
    """Single and double failures placed within 1 ns of an event boundary of a baseline
    run (step completion, checkpoint commit, restore end, replay end)."""
    h = 200 * sc.n_segments * sc.segment_ns
    base = D.run_engine(sc, [], h)
    times: set[int] = set()
    for o in base.runtime.work_ledger.outcomes:
        times.update({o.attempt.start_ns, o.execution_end_ns})
    for m in base.runtime.committed_manifests:
        times.update({m.checkpoint_write_started_at_ns, m.commit_at_ns})
    bt = sorted(t for t in times if t >= 2)
    traces = []
    for _ in range(n):
        t1 = int(rng.choice(bt)) + int(rng.choice([-1, 0, 1]))
        t1 = max(t1, 2)
        down = int(rng.choice([1, 5, sc.restart_fixed_ns]))
        tr = [(t1, t1 + down)]
        if rng.random() < 0.7:
            # second failure at a boundary of the post-first-failure timeline
            try:
                r1 = D.run_engine(sc, tr, h)
            except Exception:  # noqa: BLE001
                traces.append(tr)
                continue
            ts = set()
            for o in r1.runtime.work_ledger.outcomes:
                ts.update({o.attempt.start_ns, o.execution_end_ns})
            for t in r1.runtime.restore_transfers:
                ts.update({t.recovery_start_ns, t.transfer_start_ns, t.execution_end_ns})
            for m in r1.runtime.committed_manifests:
                ts.update({m.commit_at_ns})
            cand = sorted(t for t in ts if t > tr[0][1] + 1)
            if cand:
                t2 = int(rng.choice(cand)) + int(rng.choice([-1, 0, 1]))
                if t2 > tr[0][1]:
                    tr.append((t2, t2 + int(rng.choice([1, 5]))))
        traces.append(tr)
    return traces


def accounting_suite(seed: int, n_random: int, n_boundary: int, ks=(1, 2, 3, 5)) -> dict:
    """Random + adversarial traces; engine vs identities, engine vs reference, metamorphic
    relations.  Engine exceptions are counted separately (they are check 1b's finding)."""
    rng = _seed(seed, 1)
    tally: Counter = Counter()
    violations: Counter = Counter()
    engine_errors: Counter = Counter()
    meta: Counter = Counter()
    examples: list[dict] = []
    rates = [1.0, 2.0, 0.5]
    for k in ks:
        for rate in rates:
            sc = D.Scenario(step_ns=40 * S, k=k, n_segments=3, ckpt_ns=9 * S, restart_fixed_ns=3 * S,
                            transfer_ns=4 * S, replay_rate=rate)
            base_end = D.run_engine(sc, [], 10 ** 15).wall_ns
            kinds = ["none", "poisson_hi", "poisson_mid", "poisson_lo", "burst"]
            traces: list[tuple[str, list]] = []
            for i in range(n_random):
                kd = kinds[i % len(kinds)]
                traces.append((kd, make_random_trace(kd, rng, sc, base_end)))
            for tr in boundary_traces(sc, rng, n_boundary):
                traces.append(("boundary", tr))
            for kd, tr in traces:
                h = 10 ** 15
                try:
                    run = D.run_engine(sc, tr, max(h, 0))
                except D.TraceTooShort:
                    tally["trace_too_short"] += 1
                    continue
                except Exception as exc:  # noqa: BLE001
                    engine_errors[f"{type(exc).__name__}: {str(exc)[:80]}"] += 1
                    tally["engine_error"] += 1
                    if rate == 1.0:
                        _, pred, _ = ref_detail(tr, h, sc.n_segments, sc.k, sc.step_ns, sc.ckpt_ns, sc.restart_ns)
                        tally["engine_error_predicted" if pred else "engine_error_unpredicted"] += 1
                    continue
                tally["completed"] += 1
                bad = account(run, tr)
                for b in bad:
                    violations[b] += 1
                if bad and len(examples) < 5:
                    examples.append({"k": k, "rate": rate, "kind": kd, "trace": tr[:6], "violations": bad})
                if rate == 1.0:
                    wall, pred, _ = ref_detail(tr, h, sc.n_segments, sc.k, sc.step_ns, sc.ckpt_ns, sc.restart_ns)
                    if pred:
                        tally["completed_but_predicted_crash"] += 1
                    elif wall != run.wall_ns:
                        tally["wall_ne_reference"] += 1
                # metamorphic relations on a subset
                if len(tr) <= 6 and tally["completed"] % 4 == 0:
                    meta.update(_metamorphic(sc, tr, run))
    return {"tally": dict(tally), "violations": dict(violations), "engine_errors": dict(engine_errors),
            "metamorphic": dict(meta), "examples": examples}


def _metamorphic(sc: D.Scenario, tr: list, run: D.EngineRun) -> Counter:
    c: Counter = Counter()
    # (a) a failure strictly after the job ends changes nothing
    late = tr + [(run.end_ns + 5, run.end_ns + 9)]
    try:
        r2 = D.run_engine(sc, late, 10 ** 15)
        c["late_failure_total"] += 1
        c["late_failure_changed"] += int(r2.wall_ns != run.wall_ns or r2.runtime.work_ledger.ledger_digest
                                          != run.runtime.work_ledger.ledger_digest)
    except Exception:  # noqa: BLE001
        c["late_failure_error"] += 1
    # (b) shuffled input order of the failure list
    sh = list(reversed(tr))
    try:
        r3 = D.run_engine(sc, sh, 10 ** 15)
        c["order_total"] += 1
        c["order_changed"] += int(r3.wall_ns != run.wall_ns)
    except Exception:  # noqa: BLE001
        c["order_error"] += 1
    # (c) scale all times by 7: wall scales by 7, same number of recoveries
    f = 7
    sc7 = D.Scenario(step_ns=sc.step_ns * f, k=sc.k, n_segments=sc.n_segments, ckpt_ns=sc.ckpt_ns * f,
                     restart_fixed_ns=sc.restart_fixed_ns * f, transfer_ns=sc.transfer_ns * f,
                     replay_rate=sc.replay_rate)
    tr7 = [(a * f, b * f) for a, b in tr]
    try:
        r4 = D.run_engine(sc7, tr7, 10 ** 16)
        c["scale_total"] += 1
        # genesis lasts 1 ns in both runs, so compare wall minus rounding of that 1 ns offset
        c["scale_changed"] += int(abs(r4.wall_ns - f * run.wall_ns) > 8 * f
                                  or r4.recoveries_started != run.recoveries_started)
    except Exception:  # noqa: BLE001
        c["scale_error"] += 1
    # (d) determinism
    r5 = D.run_engine(sc, tr, 10 ** 15)
    c["determinism_total"] += 1
    c["determinism_changed"] += int(r5.runtime.work_ledger.ledger_digest != run.runtime.work_ledger.ledger_digest
                                    or r5.wall_ns != run.wall_ns)
    return c


# ----------------------------------------------------------------------------------------
# Minimal deterministic repro of the engine defect
# ----------------------------------------------------------------------------------------

def minimal_repro() -> dict:
    sc = D.Scenario(step_ns=250 * S, k=4, n_segments=3, ckpt_ns=10 * S, restart_fixed_ns=5 * S, transfer_ns=5 * S)
    cases = {"failure_at_600s_only": [600],
             "failures_600s_and_700s_(second_during_replay)": [600, 700],
             "failures_600s_and_1300s_(second_after_replay_before_checkpoint)": [600, 1300],
             "failures_600s_and_2100s_(second_after_next_checkpoint)": [600, 2100]}
    out = {}
    for name, fl in cases.items():
        try:
            r = D.run_engine(sc, [(a * S, a * S + S) for a in fl], 10 ** 15)
            out[name] = {"status": "ok", "wall_s": r.wall_ns / S}
        except Exception as exc:  # noqa: BLE001
            out[name] = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
    out["scenario"] = {"step_s": 250, "k": 4, "n_segments": 3, "ckpt_s": 10, "restart_s": 10, "downtime_s": 1}
    return out
