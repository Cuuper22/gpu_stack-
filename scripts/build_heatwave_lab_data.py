"""Build docs/data/e003-heatwave-lab-v1.json for the site's Heatwave window and Story chapter.

Reads only committed result files and copies numbers from them (no number is
typed here). Optional inputs that do not exist yet become explicit "pending"
entries, which the page shows as "result pending", never as a number.

  packing  experiments/e003-heatwave/results/packing-v1.json and lab-traces-v1.json  (simulated)
  outage   experiments/e003-heatwave/results/outage-v1.json, outage-v2.json if present (simulated)
  cost     experiments/e003-heatwave/results/cost-v1.json (public price and carbon, modeled workload)
  audit    experiments/e003-heatwave/results/cost-audit-v1.json (published prices, calculator)
  heatwave --heatwave PATH: the Heatwave repository checkout, for results/forecast/multiscale.json,
           results/ablation/ablation_sim.json and ablation_real.json, results/finetune/*.json if present

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


def load(p: Path):
    return json.loads(p.read_text()) if p.exists() else None


def src(p: Path, base: Path) -> dict:
    return {"file": str(p.relative_to(base)) if p.is_relative_to(base) else str(p),
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}


def r3(x, n=4):
    return None if x is None else round(float(x), n)


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
    return {
        "status": "ready", "data_kind": "simulated",
        "sources": [src(pk, ROOT), src(tr, ROOT)],
        "test_seeds": r["test_seeds_run"],
        "penalties_usd_per_kwh": sorted(float(k) for k in r["paired_net_value_difference"]),
        "quantile_levels": tr_r["quantile_levels"],
        "policies": pol,
        "learned_vs_reactive": paired,
        "best_fixed_by_penalty": {k: v["best_fixed_policy_by_mean_net_value_on_test_seeds"] for k, v in r["best_fixed_by_penalty"].items()},
        "trace": {"seed": tr_r["seed"], "site_ids": tr_r["site_ids"], "rack_ids": tr_r["rack_ids"],
                  "site_caps_kw": [r3(c / 1000.0, 2) for c in tr_r["site_caps_w"]],
                  "bin_s": tr_r["runs"][0]["bin_s"], "runs": runs},
    }


def outage_block() -> dict:
    out = {"status": "ready", "data_kind": "simulated", "versions": {}}
    for ver in ("v1", "v2"):
        p = E3 / f"outage-{ver}.json"
        d = load(p)
        if d is None:
            out["versions"][ver] = {"status": "pending"}
            continue
        pol = {}
        for k, v in d["result"]["policies"].items():
            o = v["overall"]
            pol[k] = {"label": v.get("label", k),
                      "useful_gpu_h": r3(o["useful_gpu_h"]["mean"], 1), "lost_gpu_h": r3(o["lost_gpu_h"]["mean"], 1),
                      "deficit_gpu_h": r3(o["deficit_gpu_h"]["mean"], 1),
                      "recall": r3((o.get("recall") or {}).get("value"), 3),
                      "false_alarms_per_day": r3((o.get("false_alarms_per_day") or {}).get("mean"), 2)}
        out["versions"][ver] = {"status": "ready", "source": src(p, ROOT), "policies": pol,
                                "n_test_seeds": len(d["result"]["seeds"]["test"])}
    return out


def cost_block() -> dict:
    p = E3 / "cost-v1.json"
    d = load(p)
    if d is None:
        return {"status": "pending"}
    r = d["result"]
    pairs = {}
    show = ("no_shift", "reactive", "seasonal_naive_24", "ets_24", "arima_seasonal", "timestral_28M", "perfect", "offline_optimum")
    for pair, v in r["pairs"].items():
        curves = {}
        for key, c in v["curves"].items():
            pol, f, w, rho, q = key.split("|")
            if f != "f=0.3" or w != "W=24" or rho != "rho=0.7" or q not in ("q=0.5", "q=na") or pol not in show:
                continue
            curves[pol] = {"lambda": c["lambda"],
                           "electricity_usd_per_mtoken": [r3(x, 6) for x in c["electricity_usd_per_mtoken"]],
                           "co2_g_per_mtoken": [r3(x, 4) for x in c["co2_g_per_mtoken"]],
                           "saving_pct_electricity": [r3(x, 3) for x in c["saving_pct_electricity"]],
                           "saving_pct_co2": [r3(x, 3) for x in c["saving_pct_co2"]],
                           "saving_pct_total": [r3(x, 4) for x in c["saving_pct_total"]]}
        pairs[pair] = {"same_region": v["same_region"], "curves": curves}
    return {"status": "ready", "data_kind": "public price and carbon series, modeled workload", "source": src(p, ROOT),
            "setting": {"flexible_fraction": 0.3, "window_hours": 24, "utilization": 0.7, "planning_quantile": 0.5},
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


def heatwave_block(hw: Path | None) -> dict:
    out = {}
    if hw is None:
        return {"forecast": {"status": "pending"}, "ablation": {"status": "pending"}, "finetune": {"status": "pending"}}
    ms = hw / "results" / "forecast" / "multiscale.json"
    d = load(ms)
    if d is None:
        out["forecast"] = {"status": "pending"}
    else:
        rows = {}
        for ds, v in d["result"]["datasets"].items():
            rows[ds] = {"data_kind": v["data_kind"], "description": v["meta"]["description"],
                        "wql": {m: r3(mm["buckets"]["all"]["wql"]["est"]) for m, mm in v["methods"].items()
                                if "all" in mm.get("buckets", {})}}
        out["forecast"] = {"status": "ready", "source": src(ms, hw), "datasets": rows}
    for key, rel in (("ablation", "results/ablation/ablation_sim.json"), ("ablation_real", "results/ablation/ablation_real.json")):
        p = hw / rel
        d = load(p)
        ok = d is not None and d["result"].get("complete", True)
        out[key] = {"status": "ready", "source": src(p, hw)} if ok else {"status": "pending"}
    ft = sorted((hw / "results" / "finetune").glob("*.json")) if (hw / "results" / "finetune").exists() else []
    out["finetune"] = {"status": "ready", "sources": [src(p, hw) for p in ft]} if ft else {"status": "pending"}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--heatwave", default="/home/claude/heatwave")
    a = ap.parse_args()
    hw = Path(a.heatwave) if a.heatwave and Path(a.heatwave).exists() else None
    doc = {"schema": "gpu-stack.e003-heatwave-lab.v1",
           "note": "Generated by scripts/build_heatwave_lab_data.py from committed result files. 'pending' means the result is not in yet.",
           "packing": packing_block(), "outage": outage_block(), "cost": cost_block(), "audit": audit_block(),
           **heatwave_block(hw)}
    OUT.write_text(json.dumps(doc, separators=(",", ":"), allow_nan=False))
    print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KiB)")


if __name__ == "__main__":
    main()
