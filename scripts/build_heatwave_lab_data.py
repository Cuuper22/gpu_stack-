"""Build the data files for the site's Heatwave window and Story chapter.

Reads only committed result files and copies numbers from them (no result number
is typed here). Results that do not exist yet become explicit "pending" entries,
which the page shows as "result pending", never as a number.

  packing  experiments/e003-heatwave/results/packing-v1.json and lab-traces-v1.json  (simulated)
  outage   experiments/e003-heatwave/results/outage-v1.json, outage-v2.json, outage-v3.json if present (simulated)
  cost     experiments/e003-heatwave/results/cost-v1.json (public price and carbon, modeled workload)
  audit    experiments/e003-heatwave/results/cost-audit-v1.json (published prices, calculator)
  heatwave --heatwave PATH: the Heatwave repository checkout, for results/forecast/multiscale.json,
           results/thermal/*.json, results/ablation/ablation_real.json and ablation_sim.json,
           results/finetune/**/*.json (each block is "pending" when its file is missing)

Outputs
  docs/data/e003-heatwave-lab-v1.json    everything, including the replay traces the window plays
  docs/data/e003-heatwave-story-v1.json  the same blocks without traces (the Story figures read this one)
  Both carry "story_numbers": every number the Story chapter quotes, with the exact words used in
  the chapter and the file and key it comes from. tests/test_heatwave_lab.mjs checks the chapter
  against it, so a number in the prose cannot drift from its result file.

Usage: python scripts/build_heatwave_lab_data.py [--heatwave /home/claude/heatwave]
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
E3 = ROOT / "experiments" / "e003-heatwave" / "results"
OUT = ROOT / "docs" / "data" / "e003-heatwave-lab-v1.json"
OUT_STORY = ROOT / "docs" / "data" / "e003-heatwave-story-v1.json"
ENC = json.JSONEncoder(separators=(",", ":"), allow_nan=False).encode
WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
         11: "eleven", 12: "twelve"}


def load(p: Path):
    return json.loads(p.read_text()) if p.exists() else None


def src(p: Path, base: Path) -> dict:
    out = {"file": str(p.relative_to(base)) if p.is_relative_to(base) else str(p),
           "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    prov = (load(p) or {}).get("provenance") or {}
    commit = (prov.get("git") or {}).get("commit")
    if commit:
        out["produced_at_commit"] = commit
    return out


def r3(x, n=4):
    return None if x is None else round(float(x), n)


def ci3(m, n=4):
    """{"mean"|"value"|"est", lo, hi} -> {"mean", "lo", "hi"} rounded."""
    if not m:
        return None
    mean = m.get("mean", m.get("value", m.get("est")))
    return {"mean": r3(mean, n), "lo": r3(m.get("lo"), n), "hi": r3(m.get("hi"), n)}


def n0(x) -> str:
    return f"{x:,.0f}"


def n1(x) -> str:
    return f"{x:,.1f}"


# ----------------------------------------------------------------------------- packing


def packing_block() -> dict:
    pk, tr = E3 / "packing-v1.json", E3 / "lab-traces-v1.json"
    d, t = load(pk), load(tr)
    if d is None or t is None:
        return {"status": "pending"}
    r, tr_r = d["result"], t["result"]
    pol = {}
    for pid, p in r["policies"].items():
        pol[pid] = {k: {"mean": r3(p[k]["mean"]), "lo": r3(p[k]["lo"]), "hi": r3(p[k]["hi"])}
                    for k in ("gpu_hours", "energy_above_cap_kwh", "violation_rate", "stranded_kwh", "value_usd") if k in p}
        if "net_value_usd" in p:
            pol[pid]["net_value_usd"] = {str(k): {"mean": r3(v["mean"]), "lo": r3(v["lo"]), "hi": r3(v["hi"])}
                                         for k, v in p["net_value_usd"].items()}
    runs = {}
    for run in tr_r["runs"]:
        runs[run["policy"]] = {
            "site_power_kw": [[r3(v / 1000.0, 2) for v in row] for row in run["site_power_w"]],
            "busy_gpus": run["busy_gpus"],
            "rack_max_gpu_c": run["rack_max_gpu_c"],
            "metrics": {k: r3(run["metrics"][k]) for k in ("gpu_hours", "energy_above_cap_kwh", "violation_rate", "stranded_kwh")},
            "matches_committed_part": run["matches_committed_part"],
        }
    paired = {pen: {"vs_reactive": {k: r3(v["net_value_difference_usd_vs"]["reactive"][k]) for k in ("mean", "lo", "hi")}}
              for pen, v in r["paired_net_value_difference"].items()}
    ep = r["scenario"]["episode"]
    return {
        "status": "ready", "data_kind": "simulated",
        "sources": [src(pk, ROOT), src(tr, ROOT)],
        "test_seeds": r["test_seeds_run"],
        "window_hours": (ep["horizon_s"] - ep["warmup_s"]) / 3600.0,
        "decision_interval_s": ep["decision_interval_s"],
        "penalties_usd_per_kwh": sorted(float(k) for k in r["paired_net_value_difference"]),
        "quantile_levels": tr_r["quantile_levels"],
        "policies": pol,
        "learned_vs_reactive": paired,
        "best_fixed_by_penalty": {k: v["best_fixed_policy_by_mean_net_value_on_test_seeds"] for k, v in r["best_fixed_by_penalty"].items()},
        "trace": {"seed": tr_r["seed"], "site_ids": tr_r["site_ids"], "rack_ids": tr_r["rack_ids"],
                  "site_caps_kw": [r3(c / 1000.0, 2) for c in tr_r["site_caps_w"]],
                  "bin_s": tr_r["runs"][0]["bin_s"], "runs": runs},
    }


# ----------------------------------------------------------------------------- outage

EVENT_NAMES = {"hardware_fault": "hardware fault", "grid_curtailment": "grid curtailment", "cooling_failure": "cooling failure",
               "thermal_throttle": "thermal throttle", "breaker_trip": "breaker trip"}


def outage_block() -> dict:
    out = {"status": "ready", "data_kind": "simulated", "versions": {}}
    for ver in ("v1", "v2", "v3"):
        p = E3 / f"outage-{ver}.json"
        d = load(p)
        if d is None:
            out["versions"][ver] = {"status": "pending"}
            continue
        r = d["result"]
        paired = r.get("paired_vs_reactive", {})
        pol = {}
        for k, v in r["policies"].items():
            o = v["overall"]
            row = {"label": v.get("label", k), "threshold": v.get("threshold"),
                   "useful_gpu_h": r3(o["useful_gpu_h"]["mean"], 1), "lost_gpu_h": r3(o["lost_gpu_h"]["mean"], 1),
                   "deficit_gpu_h": r3(o["deficit_gpu_h"]["mean"], 1),
                   "recall": r3((o.get("recall") or {}).get("value"), 3),
                   "recall_in_time": r3((o.get("recall_in_time") or {}).get("value"), 3),
                   "false_alarms_per_day": r3((o.get("false_alarms_per_day") or {}).get("mean"), 2)}
            pv = paired.get(k)
            if pv:
                row["lost_gpu_h_vs_reactive"] = ci3(pv.get("lost_gpu_h_minus_reactive"), 4)
                if "useful_gpu_h_minus_reactive" in pv:
                    row["useful_gpu_h_vs_reactive"] = ci3(pv["useful_gpu_h_minus_reactive"], 4)
            pol[k] = row
        ver_out = {"status": "ready", "source": src(p, ROOT), "policies": pol,
                   "n_test_seeds": len(r["seeds"]["test"]), "seeds_test": r["seeds"]["test"],
                   "episode_hours": r["horizon_s"] / 3600.0}
        if "event_counts_test_seeds" in r:
            counts = r["event_counts_test_seeds"]
            ver_out["events"] = {EVENT_NAMES.get(k, k): v for k, v in counts.items()}
            ver_out["events_total"] = sum(v["n"] for v in counts.values())
            ver_out["events_scheduled"] = sum(v["scheduled"] for v in counts.values())
            ver_out["events_with_precursor"] = sum(v["with_precursor"] for v in counts.values())
            by_type = {}
            for key in ("reactive", "ts28m"):
                pk = r["policies"].get(key)
                if not pk or "by_event_type" not in pk:
                    continue
                by_type[key] = {}
                for et, v in pk["by_event_type"].items():
                    rt, lead = v.get("recall_in_time"), v.get("lead_minutes_median")
                    by_type[key][EVENT_NAMES.get(et, et)] = {
                        "n_events": v["n_events"], "n_with_precursor": v["n_with_precursor"],
                        "warned_in_time": r3(rt["value"], 3) if rt else None,
                        "median_lead_min": r3(lead["value"], 1) if lead else None,
                        "lost_gpu_h": r3(v["lost_gpu_h"]["mean"], 2)}
            ver_out["by_event_type"] = by_type
            ts = r["policies"].get("ts28m", {})
            if "with_precursor" in ts and ts["with_precursor"].get("recall"):
                ver_out["ts28m_recall_with_precursor"] = r3(ts["with_precursor"]["recall"]["value"], 3)
        out["versions"][ver] = ver_out
    return out


# ----------------------------------------------------------------------------- cost and audit


def cost_block() -> dict:
    p = E3 / "cost-v1.json"
    d = load(p)
    if d is None:
        return {"status": "pending"}
    r = d["result"]
    wl = r["scenario"]["workload"]
    flex, win = wl["headline"]["flexible_fraction"], wl["headline"]["window_hours"]
    util, qd = wl["utilization"], r["scenario"]["planning_quantiles"]["default"]
    want = (f"f={flex:g}", f"W={win:g}", f"rho={util:g}")
    pairs = {}
    show = ("no_shift", "reactive", "seasonal_naive_24", "ets_24", "arima_seasonal", "timestral_28M", "perfect", "offline_optimum")
    for pair, v in r["pairs"].items():
        curves = {}
        for key, c in v["curves"].items():
            pol, f, w, rho, q = key.split("|")
            if (f, w, rho) != want or q not in (f"q={qd:g}", "q=na") or pol not in show:
                continue
            curves[pol] = {"lambda": c["lambda"],
                           "electricity_usd_per_mtoken": [r3(x, 6) for x in c["electricity_usd_per_mtoken"]],
                           "co2_g_per_mtoken": [r3(x, 4) for x in c["co2_g_per_mtoken"]],
                           "saving_pct_electricity": [r3(x, 3) for x in c["saving_pct_electricity"]],
                           "saving_pct_co2": [r3(x, 3) for x in c["saving_pct_co2"]],
                           "saving_pct_total": [r3(x, 4) for x in c["saving_pct_total"]]}
        pairs[pair] = {"same_region": v["same_region"], "curves": curves}
    return {"status": "ready", "data_kind": "public price and carbon series, modeled workload", "source": src(p, ROOT),
            "setting": {"flexible_fraction": flex, "window_hours": win, "utilization": util, "planning_quantile": qd},
            "test_weeks": r["scenario"]["test"]["weeks"],
            "pairs": pairs}


def audit_block() -> dict:
    p = E3 / "cost-audit-v1.json"
    d = load(p)
    if d is None:
        return {"status": "pending"}
    r = d["result"]
    base = r["base_case"]
    regions = [{"setting": x["setting"], "electricity_share": r3(x["electricity_share"])}
               for x in r["one_at_a_time"]["H100"] if x["parameter"] == "electricity price"]
    return {"status": "ready", "source": src(p, ROOT), "base_electricity_share": r3(base["electricity_share"]),
            "base_inputs": {k: base["inputs"][k] for k in ("useful_life_years", "pue", "electricity_price")},
            "regions_h100": regions}


# ----------------------------------------------------------------------------- Heatwave repository results


def forecast_block(hw: Path) -> dict:
    ms = hw / "results" / "forecast" / "multiscale.json"
    d = load(ms)
    if d is None:
        return {"status": "pending"}
    rows, lower_both, lower_any = {}, 0, 0
    for ds, v in d["result"]["datasets"].items():
        wql = {m: r3(mm["buckets"]["all"]["wql"]["est"], 6) for m, mm in v["methods"].items() if "all" in mm.get("buckets", {})}
        ts = {m: x for m, x in wql.items() if m.startswith("timestral")}
        classical = {m: x for m, x in wql.items() if not m.startswith("timestral")}
        best_name = min(classical, key=classical.get)
        rows[ds] = {"data_kind": v["data_kind"], "description": v["meta"]["description"], "wql": wql,
                    "best_classical": best_name, "best_classical_wql": classical[best_name]}
        lower_both += all(x < classical[best_name] for x in ts.values())
        lower_any += any(x < classical[best_name] for x in ts.values())
    return {"status": "ready", "source": src(ms, hw), "datasets": rows,
            "n_series": len(rows), "n_series_both_sizes_lower": lower_both, "n_series_any_size_lower": lower_any}


def thermal_block(hw: Path) -> dict:
    rc, tw = hw / "results" / "thermal" / "laptop_rc.json", hw / "results" / "thermal" / "throttle_warning.json"
    a, b = load(rc), load(tw)
    if a is None or b is None:
        return {"status": "pending"}
    th = a["result"]["throttle"]["run1"]
    test_run = b["result"]["settings"]["test_runs"][0]
    methods = {}
    for m in ("reactive", "ets", "timestral-5M", "timestral-28M"):
        t = b["result"]["methods"][m]["test"][test_run]
        methods[m] = {"onsets": t["onsets"], "onsets_warned": t["onsets_warned"], "median_lead_s": t["median_lead_s"]}
    return {"status": "ready", "data_kind": "measured", "sources": [src(rc, hw), src(tw, hw)],
            "throttle_run1": {"temp_c_p05": th["temp_c_at_sw_thermal_p05"],
                              "clock_mhz_throttled_median": th["sm_clock_mhz_training_sw_thermal_median"],
                              "clock_mhz_not_throttled_median": th["sm_clock_mhz_training_no_thermal_median"]},
            "warning": {"test_run": test_run, "horizon_s": b["result"]["settings"]["horizon_s"], "methods": methods}}


def ablation_block(path: Path, only_test: bool) -> dict:
    """Compact view of a covariate-ablation result (same schema for the real-data and the simulator file)."""
    d = load(path)
    if d is None or not d["result"].get("complete", True):
        return {"status": "pending"}
    r = d["result"]
    design_groups = {k: v["name"] for k, v in (r.get("design", {}).get("groups") or {}).items()}
    datasets = {}
    for name, ds in r["datasets"].items():
        if only_test and name.endswith("_run1"):
            continue  # run1 is the calibration run; run2 is the held-out test run
        names = design_groups or {k: v for k, v in (ds.get("covariate_groups") or {}).items()}
        methods = {}
        for m, mm in ds["methods"].items():
            if m.startswith("timestral"):
                cfgs = {}
                for cname, c in mm["configs"].items():
                    if "L" in c["groups"]:
                        continue  # uses realised future values; the result file marks it comparison only
                    b = c["buckets"]["all"]
                    cfgs[cname] = {"groups": c["groups"], "wql": r3(b["wql"], 6), "lo": r3(b["wql_ci95"][0], 6), "hi": r3(b["wql_ci95"][1], 6),
                                   "cov80": r3(b["cov80"], 3), "n_windows": b["n_windows"]}
                    if b.get("delta_wql") is not None:
                        # paired over the same windows: config minus no inputs, bootstrap interval
                        cfgs[cname]["d"] = r3(b["delta_wql"], 6)
                        cfgs[cname]["d_lo"], cfgs[cname]["d_hi"] = r3(b["delta_wql_ci95"][0], 6), r3(b["delta_wql_ci95"][1], 6)
                base = cfgs["none"]
                for cname, c in cfgs.items():
                    # reading from the paired difference: its interval is clear of zero, or it is not
                    c["vs_none"] = "baseline" if cname == "none" else ("lower" if c["d_hi"] < 0 else "higher" if c["d_lo"] > 0 else "overlap")
                    c["change_pct"] = None if cname == "none" else r3(100.0 * (c["wql"] - base["wql"]) / base["wql"], 2)
                methods[m] = cfgs
            else:
                b = mm["configs"]["none"]["buckets"]["all"]
                methods[m] = {"none": {"groups": [], "wql": r3(b["wql"], 6), "lo": r3(b["wql_ci95"][0], 6), "hi": r3(b["wql_ci95"][1], 6)}}
        datasets[name] = {"data_kind": ds["data_kind"], "what": ds["what"], "groups": {k: names[k] for k in names if k != "L"},
                          "step": ds["scale"]["step"], "horizon_steps": ds["scale"]["horizon"],
                          "n_origins": ds["subsampling"].get("n_origins"), "methods": methods}
    out = {"status": "ready", "source": src(path, path.parents[2]), "datasets": datasets,
           "hardware": (r.get("meta") or {}).get("hardware", {}).get("gpu"), "run_label": (r.get("meta") or {}).get("run_label")}
    vint = (r.get("diagnostics") or {}).get("gb_forecast_vintage")
    if vint:
        out["gb_forecast_vintage_note"] = "GB intensity forecast vintage is undocumented; it is assumed to be issued 24 hours ahead"
    return out


FT_NAMES = {"laptop_power": "laptop GPU power, 1 s", "laptop_temp": "laptop GPU temperature, 1 s",
            "elsayed_gpu_power": "H100 and B200 GPU power, 1 s", "nlr_job_power": "H100 multi-node job power",
            "mit_node_power": "V100 node power, 1 s", "mit_node_temp": "V100 node temperature, 1 min",
            "caiso_rt_price_1h": "CAISO real-time price, 1 h", "uk_carbon_actual_1h": "GB carbon intensity, 1 h",
            "sim_rack_power_1s": "simulated rack power, 1 s", "sim_rack_temp_1min": "simulated rack temperature, 1 min",
            "sim_site_power_1h": "simulated site power, 1 h"}


def finetune_block(hw: Path) -> dict:
    """Per size and series: best zero-shot and best fine-tuned configuration (with or without known-future inputs),
    their ratio, and the paired fine-tuned minus zero-shot difference in each input mode (bootstrap interval)."""
    files = sorted(p for p in (hw / "results" / "finetune").rglob("*.json")) if (hw / "results" / "finetune").exists() else []
    runs = []
    for p in files:
        d = load(p)
        res = (d or {}).get("result") or {}
        ev = res.get("evaluation")
        if not ev:
            continue
        hwinfo = res.get("hardware") or {}
        for size, e in ev.items():
            ref = e.get("reference")
            if not ref:
                continue
            series = []
            for ds, v in e["datasets"].items():
                modes = v["modes"]
                best = {}
                for mode, m in modes.items():
                    for label, x in m["models"].items():
                        kind = "zero_shot" if label == ref else label
                        val = x["all"]["wql"]["est"]
                        cur = best.get(kind)
                        if cur is None or val < cur["wql"]:
                            best[kind] = {"wql": r3(val, 6), "mode": mode}
                deltas = {}
                for mode, m in modes.items():
                    for label, dv in (m.get("delta_vs_reference") or {}).items():
                        w = (dv.get("all") or {}).get("wql")
                        if w:
                            deltas.setdefault(label, {})[mode] = ci3(w)
                zs_modes = {mode: r3(m["models"][ref]["all"]["wql"]["est"]) for mode, m in modes.items() if ref in m["models"]}
                series.append({"name": ds, "what": FT_NAMES.get(ds, ds), "data_kind": v.get("data_kind"),
                               "n_windows": v.get("n_windows"), "best": best, "zero_shot_by_mode": zs_modes,
                               "paired_vs_zero_shot": deltas})
            runs.append({"file": src(p, hw), "size": size, "reference": ref, "series": series,
                         "models": [m for m in next(iter(e["datasets"].values()))["modes"]["none"]["models"] if m != ref],
                         "hardware": hwinfo.get("gpu") or hwinfo.get("device"), "run_label": res.get("run_label")})
    return {"status": "ready", "runs": runs,
            "note": "best = lowest test-window loss over input modes (none, or with known-future inputs where the series has them)"} if runs else {"status": "pending"}


def heatwave_blocks(hw: Path | None) -> dict:
    if hw is None:
        return {k: {"status": "pending"} for k in ("forecast", "thermal", "ablation", "ablation_sim", "finetune")}
    return {"forecast": forecast_block(hw), "thermal": thermal_block(hw),
            "ablation": ablation_block(hw / "results" / "ablation" / "ablation_real.json", True),
            "ablation_sim": ablation_block(hw / "results" / "ablation" / "ablation_sim.json", False),
            "finetune": finetune_block(hw)}


# ----------------------------------------------------------------------------- the numbers the Story quotes


def story_numbers(doc: dict) -> list[dict]:
    """Every number in the Story chapter, in the words the chapter uses, with its source."""
    out: list[dict] = []

    def add(id_: str, text: str, value, source: str) -> None:
        out.append({"id": id_, "text": text, "value": value, "source": source})

    f, th, P, OUTG, C = doc["forecast"], doc["thermal"], doc["packing"], doc["outage"], doc["cost"]
    if f["status"] == "ready":
        s = "heatwave:results/forecast/multiscale.json"
        el = f["datasets"]["elsayed_gpu_power"]
        add("forecast.series", WORDS[f["n_series"]] + " series", f["n_series"], s + " datasets (count); lower than best classical for both sizes on " + str(f["n_series_both_sizes_lower"]))
        add("forecast.elsayed.timestral_28m", f"{el['wql']['timestral-28M']:.3f}", el["wql"]["timestral-28M"], s + " elsayed_gpu_power timestral-28M all-horizon WQL")
        add("forecast.elsayed.best_classical", f"{el['best_classical_wql']:.3f}", el["best_classical_wql"], s + " elsayed_gpu_power " + el["best_classical"] + " all-horizon WQL")
    if th["status"] == "ready":
        s = "heatwave:results/thermal/"
        t1 = th["throttle_run1"]
        add("thermal.onset_c", f"{t1['temp_c_p05']:.0f} degrees", t1["temp_c_p05"], s + "laptop_rc.json throttle.run1.temp_c_at_sw_thermal_p05")
        add("thermal.clock_free", n0(t1["clock_mhz_not_throttled_median"]), t1["clock_mhz_not_throttled_median"], s + "laptop_rc.json throttle.run1 median clock, not throttled")
        add("thermal.clock_throttled", n0(t1["clock_mhz_throttled_median"]), t1["clock_mhz_throttled_median"], s + "laptop_rc.json throttle.run1 median clock, throttled")
        w = th["warning"]
        m = w["methods"]
        add("thermal.horizon", f"{w['horizon_s']:.0f}-second", w["horizon_s"], s + "throttle_warning.json settings.horizon_s")
        add("thermal.timestral_warned", f"{m['timestral-28M']['onsets_warned']} of the {m['timestral-28M']['onsets']}", m["timestral-28M"]["onsets_warned"], s + "throttle_warning.json timestral-28M test onsets_warned of onsets")
        add("thermal.timestral_lead", f"{m['timestral-28M']['median_lead_s']:g} seconds", m["timestral-28M"]["median_lead_s"], s + "throttle_warning.json timestral-28M test median_lead_s")
        add("thermal.reactive_lead", f"{m['reactive']['median_lead_s']:g} seconds", m["reactive"]["median_lead_s"], s + "throttle_warning.json reactive test median_lead_s")
        add("thermal.ets_lead", f"{m['ets']['median_lead_s']:g} seconds", m["ets"]["median_lead_s"], s + "throttle_warning.json ets test median_lead_s")
        add("thermal.ets_warned", f"{m['ets']['onsets_warned']}", m["ets"]["onsets_warned"], s + "throttle_warning.json ets test onsets_warned")
    if P["status"] == "ready":
        s = "gpu_stack:experiments/e003-heatwave/results/packing-v1.json result.policies."
        re_, q9 = P["policies"]["reactive"], P["policies"]["timestral-5M/q0.9"]
        add("packing.window_hours", f"{P['window_hours']:.0f} hours", P["window_hours"], s[:-len("policies.")] + "scenario.episode (horizon_s - warmup_s)")
        add("packing.test_seeds", WORDS[len(P["test_seeds"])] + " held-out", len(P["test_seeds"]), s[:-len("policies.")] + "test_seeds_run")
        add("packing.reactive.gpu_hours", n0(re_["gpu_hours"]["mean"]), re_["gpu_hours"]["mean"], s + "reactive.gpu_hours.mean")
        add("packing.reactive.violation", f"{100 * re_['violation_rate']['mean']:.0f} percent", re_["violation_rate"]["mean"], s + "reactive.violation_rate.mean")
        less = 100 * (1 - q9["gpu_hours"]["mean"] / re_["gpu_hours"]["mean"])
        add("packing.q90.less_work", f"{less:.0f} percent less work", less, s + "timestral-5M/q0.9.gpu_hours.mean against reactive")
        add("packing.q90.gpu_hours", n0(q9["gpu_hours"]["mean"]), q9["gpu_hours"]["mean"], s + "timestral-5M/q0.9.gpu_hours.mean")
        ratio = q9["energy_above_cap_kwh"]["mean"] / re_["energy_above_cap_kwh"]["mean"]
        add("packing.q90.energy_ratio", "a sixth of the energy", ratio, s + "timestral-5M/q0.9.energy_above_cap_kwh.mean over reactive (1/6 = 0.167)")
        add("packing.reactive.energy", n1(re_["energy_above_cap_kwh"]["mean"]) + " kWh", re_["energy_above_cap_kwh"]["mean"], s + "reactive.energy_above_cap_kwh.mean")
        add("packing.q90.energy", n1(q9["energy_above_cap_kwh"]["mean"]) + " kWh", q9["energy_above_cap_kwh"]["mean"], s + "timestral-5M/q0.9.energy_above_cap_kwh.mean")
        for pen in P["penalties_usd_per_kwh"]:
            add(f"packing.penalty.{pen:g}", f"${pen:,.2f}" if pen % 1 else f"${pen:,.0f}", pen, "packing-v1.json result.paired_net_value_difference (penalty sweep keys)")
        lv = P["learned_vs_reactive"]
        add("packing.learned.at40", f"${lv['40']['vs_reactive']['mean']:,.0f}", lv["40"]["vs_reactive"]["mean"], "packing-v1.json result.paired_net_value_difference.40 vs reactive mean")
        add("packing.learned.at160", f"${lv['160']['vs_reactive']['mean']:,.0f}", lv["160"]["vs_reactive"]["mean"], "packing-v1.json result.paired_net_value_difference.160 vs reactive mean")
        add("packing.learned.at2_5", f"${-lv['2.5']['vs_reactive']['mean']:,.0f}", lv["2.5"]["vs_reactive"]["mean"], "packing-v1.json result.paired_net_value_difference.2.5 vs reactive mean (negative)")
    if C["status"] == "ready":
        s = "gpu_stack:experiments/e003-heatwave/results/cost-v1.json pairs.caiso curves (f=0.3, W=24, rho=0.7, q=0.5) at lambda 0.5 "
        c = C["pairs"]["caiso"]["curves"]
        mid = c["timestral_28M"]["lambda"].index(0.5)
        add("cost.flexible", f"{100 * C['setting']['flexible_fraction']:.0f} percent of the work", C["setting"]["flexible_fraction"], "cost-v1.json result.scenario.workload.headline.flexible_fraction")
        add("cost.timestral.electricity", f"{c['timestral_28M']['saving_pct_electricity'][mid]:.1f} percent", c["timestral_28M"]["saving_pct_electricity"][mid], s + "timestral_28M saving_pct_electricity")
        add("cost.timestral.co2", f"{c['timestral_28M']['saving_pct_co2'][mid]:.1f} percent", c["timestral_28M"]["saving_pct_co2"][mid], s + "timestral_28M saving_pct_co2")
        add("cost.perfect.electricity", f"{c['perfect']['saving_pct_electricity'][mid]:.1f} percent", c["perfect"]["saving_pct_electricity"][mid], s + "perfect saving_pct_electricity")
        add("cost.naive.electricity", f"{c['seasonal_naive_24']['saving_pct_electricity'][mid]:.1f} percent", c["seasonal_naive_24"]["saving_pct_electricity"][mid], s + "seasonal_naive_24 saving_pct_electricity")
        add("cost.timestral.total", f"{c['timestral_28M']['saving_pct_total'][mid]:.2f} percent", c["timestral_28M"]["saving_pct_total"][mid], s + "timestral_28M saving_pct_total")
    v2 = OUTG["versions"].get("v2", {})
    if v2.get("status") == "ready" and "events" in v2:
        s = "gpu_stack:experiments/e003-heatwave/results/outage-v2.json result."
        pol = v2["policies"]
        re_, ts = pol["reactive"], pol["ts28m"]
        add("outage.events_total", f"{v2['events_total']} events", v2["events_total"], s + "event_counts_test_seeds (sum of n)")
        add("outage.n_seeds", WORDS[v2["n_test_seeds"]] + " held-out", v2["n_test_seeds"], s + "seeds.test")
        add("outage.events_scheduled", f"{v2['events_scheduled']} of them", v2["events_scheduled"], s + "event_counts_test_seeds (sum of scheduled)")
        add("outage.events_with_precursor", f"{v2['events_with_precursor']} showed", v2["events_with_precursor"], s + "event_counts_test_seeds (sum of with_precursor)")
        add("outage.events_without", f"{v2['events_scheduled'] - v2['events_with_precursor']} showed nothing", v2["events_scheduled"] - v2["events_with_precursor"], s + "event_counts_test_seeds (scheduled minus with_precursor)")
        add("outage.reactive.lost", n1(re_["lost_gpu_h"]), re_["lost_gpu_h"], s + "policies.reactive.overall.lost_gpu_h.mean")
        add("outage.ts28m.lost", n1(ts["lost_gpu_h"]), ts["lost_gpu_h"], s + "policies.ts28m.overall.lost_gpu_h.mean")
        add("outage.ts28m.warned", f"{100 * ts['recall_in_time']:.0f} percent", ts["recall_in_time"], s + "policies.ts28m.overall.recall_in_time.value")
        add("outage.ts28m.false_alarms", f"{ts['false_alarms_per_day']:.1f} false alarms", ts["false_alarms_per_day"], s + "policies.ts28m.overall.false_alarms_per_day.mean")
        add("outage.ts28m.precursor_recall", f"{v2['ts28m_recall_with_precursor'] * v2['events_with_precursor']:.0f} of the {v2['events_with_precursor']}", v2["ts28m_recall_with_precursor"], s + "policies.ts28m.with_precursor.recall.value times n_events")
        add("outage.reactive.useful", n0(re_["useful_gpu_h"]), re_["useful_gpu_h"], s + "policies.reactive.overall.useful_gpu_h.mean")
        add("outage.ts28m.useful", n0(ts["useful_gpu_h"]), ts["useful_gpu_h"], s + "policies.ts28m.overall.useful_gpu_h.mean")
        u = ts["useful_gpu_h_vs_reactive"]
        add("outage.ts28m.useful_diff", f"{u['mean']:.1f} GPU-hours more, with a 95 percent interval from {u['lo']:.1f} to {u['hi']:.1f}", u["mean"], s + "paired_vs_reactive.ts28m.useful_gpu_h_minus_reactive")
        v1_ts = OUTG["versions"]["v1"]["policies"]["ts28m"]
        add("outage.v1.ts28m.warned", f"{100 * v1_ts['recall_in_time']:.0f} percent", v1_ts["recall_in_time"], "outage-v1.json result.policies.ts28m.overall.recall_in_time.value")
    v3 = OUTG["versions"].get("v3", {})
    if v3.get("status") == "ready" and v2.get("status") == "ready":
        s = "gpu_stack:experiments/e003-heatwave/results/outage-v3.json result."
        pol3 = v3["policies"]
        pf3, pf2, ts3 = pol3["perfect_foresight"], v2["policies"]["perfect_foresight"], pol3["ts28m"]
        add("outage.v2.perfect.deficit", f"{pf2['deficit_gpu_h']:.1f} short", pf2["deficit_gpu_h"], "outage-v2.json result.policies.perfect_foresight.overall.deficit_gpu_h.mean")
        d3 = pf3["deficit_gpu_h"]
        add("outage.v3.perfect.deficit", f"{abs(d3):.1f} GPU-hours {'above' if d3 < 0 else 'short of'}", d3, s + "policies.perfect_foresight.overall.deficit_gpu_h.mean (event-free minus policy)")
        add("outage.v3.ts28m.lost", n1(ts3["lost_gpu_h"]), ts3["lost_gpu_h"], s + "policies.ts28m.overall.lost_gpu_h.mean")
        lv = ts3["lost_gpu_h_vs_reactive"]
        add("outage.v3.ts28m.lost_diff", f"{-lv['mean']:.1f} fewer, with a 95 percent interval from {-lv['hi']:.1f} to {-lv['lo']:.1f}", lv["mean"], s + "paired_vs_reactive.ts28m.lost_gpu_h_minus_reactive (sign flipped)")
        u3 = ts3["useful_gpu_h_vs_reactive"]
        add("outage.v3.ts28m.useful_diff", f"{u3['mean']:.1f} GPU-hours more, with a 95 percent interval from {u3['lo']:.1f} to {u3['hi']:.1f}", u3["mean"], s + "paired_vs_reactive.ts28m.useful_gpu_h_minus_reactive")
        up = pf3["useful_gpu_h_vs_reactive"]
        add("outage.v3.perfect.useful_diff", f"{up['mean']:.1f} more (interval {up['lo']:.1f} to {up['hi']:.1f})", up["mean"], s + "paired_vs_reactive.perfect_foresight.useful_gpu_h_minus_reactive")
        add("outage.v3.ts28m.false_alarms", f"{ts3['false_alarms_per_day']:.1f} false alarms", ts3["false_alarms_per_day"], s + "policies.ts28m.overall.false_alarms_per_day.mean")
        fa = [pol3[k]["false_alarms_per_day"] for k in ("naive", "arima")]
        add("outage.v3.classical.false_alarms", f"{min(fa):.1f} to {max(fa):.1f}", max(fa), s + "policies.naive and policies.arima overall.false_alarms_per_day.mean")
    A = doc["ablation"]
    if A["status"] == "ready":
        s = "heatwave:results/ablation/ablation_real.json result.datasets."

        def w(ds, cfg, size="timestral-209M"):
            return A["datasets"][ds]["methods"][size][cfg]

        def a(id_, ds, cfg, size="timestral-209M"):
            x = w(ds, cfg, size)
            add(id_, f"{x['wql']:.3f}", x["wql"], f"{s}{ds}.methods.{size}.configs.{cfg}.buckets.all.wql")

        a("ablation.caiso.none", "caiso_rt_lmp_5min", "none")
        a("ablation.caiso.da", "caiso_rt_lmp_5min", "DA")
        a("ablation.caiso.wx", "caiso_rt_lmp_5min", "WX")
        x = w("caiso_rt_lmp_5min", "DA")
        add("ablation.caiso.da_diff", f"{x['d']:.3f}, with a 95 percent interval from {x['d_lo']:.3f} to {x['d_hi']:.3f}", x["d"],
            s + "caiso_rt_lmp_5min.methods.timestral-209M.configs.DA.buckets.all.delta_wql (paired, moving-block bootstrap)")
        a("ablation.gb.none", "gb_carbon_30min", "none")
        a("ablation.gb.f", "gb_carbon_30min", "F")
        a("ablation.laptop.none", "laptop_power_1s_run2", "none")
        a("ablation.laptop.s", "laptop_power_1s_run2", "S")
        a("ablation.laptop10.none", "laptop_power_10hz_run2", "none")
        a("ablation.laptop10.s", "laptop_power_10hz_run2", "S")
        add("ablation.laptop10.windows", n0(A["datasets"]["laptop_power_10hz_run2"]["n_origins"]) + " windows", A["datasets"]["laptop_power_10hz_run2"]["n_origins"], s + "laptop_power_10hz_run2.subsampling.n_origins")
    F = doc["finetune"]
    if F["status"] == "ready":
        gpu = {r["size"]: r for r in F["runs"] if r["run_label"] == "colab-gpu"}
        big = gpu.get("209M")
        if big:
            s = "heatwave:" + big["file"]["file"] + " result.evaluation.209M.datasets."
            ser = {x["name"]: x for x in big["series"]}
            m = big["models"][0]

            def ratio(ds):
                x = ser[ds]["best"]
                return x[m]["wql"] / x["zero_shot"]["wql"]

            add("finetune.laptop.ratio", f"{ratio('laptop_power'):.2f}", ratio("laptop_power"), s + "laptop_power best fine-tuned over best zero-shot WQL (all horizons)")
            add("finetune.simrack.ratio", f"{ratio('sim_rack_power_1s'):.2f}", ratio("sim_rack_power_1s"), s + "sim_rack_power_1s best fine-tuned over best zero-shot WQL")
            zm = ser["sim_rack_power_1s"]["zero_shot_by_mode"]
            add("finetune.simrack.zs_none", f"{zm['none']:.3f}", zm["none"], s + "sim_rack_power_1s.modes.none zero-shot-209M WQL")
            add("finetune.simrack.zs_cov", f"{zm['cov_all']:.3f}", zm["cov_all"], s + "sim_rack_power_1s.modes.cov_all zero-shot-209M WQL")
            el = ser["elsayed_gpu_power"]["best"]
            add("finetune.elsayed.zs", f"{el['zero_shot']['wql']:.3f}", el["zero_shot"]["wql"], s + "elsayed_gpu_power.modes.none zero-shot-209M WQL")
            add("finetune.elsayed.ft", f"{el[m]['wql']:.3f}", el[m]["wql"], s + "elsayed_gpu_power.modes.none " + m + " WQL")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--heatwave", default="/home/claude/heatwave")
    a = ap.parse_args()
    hw = Path(a.heatwave) if a.heatwave and Path(a.heatwave).exists() else None
    doc = {"schema": "gpu-stack.e003-heatwave-lab.v1",
           "note": "Generated by scripts/build_heatwave_lab_data.py from committed result files. 'pending' means the result is not in yet.",
           "packing": packing_block(), "outage": outage_block(), "cost": cost_block(), "audit": audit_block(),
           **heatwave_blocks(hw)}
    doc["story_numbers"] = story_numbers(doc)
    OUT.write_text(ENC(doc))
    print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KiB)")
    story = json.loads(ENC(doc))
    if story["packing"].get("status") == "ready":
        story["packing"]["trace"] = {k: v for k, v in story["packing"]["trace"].items() if k != "runs"}
        story["packing"]["trace"]["note"] = "replay traces are in e003-heatwave-lab-v1.json"
    story["schema"] = "gpu-stack.e003-heatwave-story.v1"
    OUT_STORY.write_text(ENC(story))
    print(f"wrote {OUT_STORY} ({OUT_STORY.stat().st_size / 1024:.0f} KiB)")


if __name__ == "__main__":
    main()
