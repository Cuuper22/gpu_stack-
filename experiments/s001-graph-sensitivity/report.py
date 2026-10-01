"""Print the numbers needed for RESULT.md from results/*.json (read-only)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

R = Path(__file__).resolve().parent / "results"
PRESETS = ["P1_pythia70m_full_tco", "P2_dense_fixture", "P3_pythia160m_energy_floor"]
TARGETS = ["cost_per_token", "tokens_per_sec", "dc_power", "run_power_cost"]


def load(p, t, r):
    f = R / f"sobol__{p}__{t}__{r}.json"
    return json.loads(f.read_text()) if f.exists() else None


def fmt(x, n=3):
    return "nan" if x is None else f"{x:.{n}f}"


def main() -> None:
    st = json.loads((R / "structure.json").read_text())
    print("== STRUCTURE (roots of 619)")
    for k, v in st.items():
        a, s, i = v["structurally_connected_any_equation"], v["structurally_connected_selected_equation"], v["in_resolved_formula"]
        print(f"{k}: any={a['roots']}(lith {a['lithography']},nuc {a['nuclear_quark']}) sel={s['roots']}(lith {s['lithography']}) "
              f"assigned_roots={v['assigned_in_preset']['roots']['roots']} formula_roots={i['roots']['roots']}"
              f"(lith {i['roots']['lithography']}, nuc {i['roots']['nuclear_quark']}) formula_pins={i['derived_pins']} "
              f"inputs={i['inputs_total']}")
    print("\n== CUT POINTS (P1 cost)")
    for c, d in st["P1_pythia70m_full_tco/cost_per_token"]["cut_points_in_formula"].items():
        print(" ", c, d)
    print("\n== PRIMARY AND ALL R1 PAIRS")
    for p in PRESETS:
        for t in TARGETS:
            r = load(p, t, "R1")
            if r is None or r.get("status") != "ok":
                print(p, t, "MISSING/FAILED", None if r is None else r.get("status"))
                continue
            cc, tau = r.get("convergence_checks"), r.get("tau", {})
            a = tau.get("a_present_roots", {})
            b = tau.get("b_all_619_roots", {})
            c = tau.get("c_all_factors_dependents", {})
            d = tau.get("d_family_level", {})
            e = tau.get("e_morris_mu_star_vs_ST", {})
            print(f"{p}/{t}: k={r['k_factors']} sumS1={fmt(r['sum_S1'])} sumST={fmt(r['sum_ST'])} C1={cc and cc.get('C1_pass')}"
                  f"({fmt(cc and cc.get('C1_max_abs_change_last_doubling_nonnegligible'),4)}) C2={cc and cc.get('C2_pass')}"
                  f"({fmt(cc and cc.get('C2_max_ci_halfwidth'),4)})")
            print(f"   tau_a n={a.get('n')} {fmt(a.get('tau_b'))} ci90={a.get('ci90_two_sided')} verdict={a.get('verdict_vs_0.30')}")
            print(f"   tau_b(619) {fmt(b.get('tau_b'))} ci90={b.get('ci90_two_sided')} | tau_c n={c.get('n')} {fmt(c.get('tau_b'))} "
                  f"| tau_d n={d.get('n')} {fmt(d.get('tau_b'))} | morris-vs-ST {fmt(e.get('tau_b'))}")
            g = r["groups"]
            print(f"   LITH={g['LITHOGRAPHY']['ST_group']:.4f} NUC={g['NUCLEAR_QUARK']['ST_group']:.4f} "
                  f"ALL_ROOTS={fmt(g.get('ALL_ROOTS', {}).get('ST_group'))} ALL_PINS={fmt(g.get('ALL_PINS', {}).get('ST_group'))}")
            if "seed_replicates" in r:
                print("   seed replicates:", r["seed_replicates"])
    print("\n== TOP 10 BY ST (R1)")
    for p in PRESETS[:1]:
        for t in TARGETS:
            r = load(p, t, "R1")
            if not r or r.get("status") != "ok":
                continue
            print(f"{p}/{t}")
            for f in sorted(r["factors"], key=lambda f: -f["ST"])[:10]:
                print(f"   {f['name']:46s} ST={f['ST']:.3f} [{f['ST_ci'][0]:.3f},{f['ST_ci'][1]:.3f}] S1={f['S1']:.3f} "
                      f"{'root' if f['is_root'] else 'pin '} debt={f['root_debt']} dep={f['dependents']} class={f['class']} el={fmt(f['elasticity_nominal'],2)}")
            print("   held:", r["held_inputs"])
    print("\n== TIER COUNTS (R1)")
    for p in PRESETS:
        for t in TARGETS:
            r = load(p, t, "R1")
            if not r or r.get("status") != "ok":
                continue
            cnt = {}
            for f in r["factors"]:
                cnt[f["class"]] = cnt.get(f["class"], 0) + 1
            print(p, t, cnt)
    print("\n== H1 ROBUSTNESS (primary tau_a under rules)")
    for rule in ["R1", "R1_f1.25", "R1_f4", "R4"]:
        for p in PRESETS:
            for t in TARGETS:
                r = load(p, t, rule)
                if not r or r.get("status") != "ok":
                    continue
                a = r.get("tau", {}).get("a_present_roots", {})
                print(f"{rule:9s} {p}/{t}: n={a.get('n')} tau={fmt(a.get('tau_b'))} ci90={a.get('ci90_two_sided')} {a.get('verdict_vs_0.30')}")
    print("\n== H2b: cut points with lithography beneath, P1 cost, ST by rule")
    cps = {c for c, d in st["P1_pythia70m_full_tco/cost_per_token"]["cut_points_in_formula"].items() if d["lithography_beneath"] > 0}
    for rule in ["R1_f1.25", "R1", "R1_f4"]:
        r = load("P1_pythia70m_full_tco", "cost_per_token", rule)
        for f in r["factors"]:
            if f["name"] in cps:
                print(f"  {rule:9s} {f['name']:40s} ST={f['ST']:.4f} ci=[{f['ST_ci'][0]:.4f},{f['ST_ci'][1]:.4f}] el={fmt(f['elasticity_nominal'],3)}")
    print("  cut points in formula but no lithography beneath:", sorted(set(st["P1_pythia70m_full_tco/cost_per_token"]["cut_points_in_formula"]) - cps))
    print("\n== H3 (P1 cost R1)")
    r = load("P1_pythia70m_full_tco", "cost_per_token", "R1")
    t = r["tau"]
    print("top20 root-debt:")
    cls = {f["name"]: f for f in r["factors"]}
    for n, isf, nn in zip(t["f_top20_root_debt"]["names"], t["f_top20_root_debt"]["is_factor"], t["f_top20_root_debt"]["not_negligible"]):
        f = cls.get(n)
        print(f"   {n:60s} factor={isf} not_negligible={nn} ST={fmt(f and f['ST'])}")
    print("top10 ST roots debt ranks:", json.dumps(t["g_top10_ST_roots_debt_rank"]))
    print("\n== any lithography root as factor in any run?")
    hit = []
    for p in PRESETS:
        for tt in TARGETS:
            for rule in ["R1", "R1_f1.25", "R1_f4", "R4"]:
                r = load(p, tt, rule)
                if r and r.get("status") == "ok":
                    hit += [(p, tt, rule, f["name"]) for f in r["factors"] if f["name"].startswith("physical.lithography.")]
    print(hit)


if __name__ == "__main__":
    sys.exit(main())
