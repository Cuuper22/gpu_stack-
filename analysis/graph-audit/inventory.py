"""Inventory + reachability audit of the gpu_stack equation graph.

Run:  PYTHONPATH=<repo> <venv python> -B analysis/graph-audit/inventory.py [--json out.json] [--list-decorative]

For each scope family it counts variables, equations (by role) and roots, and how many
of them feed the four headline targets. "Feeds" is computed two ways:

  graph  : edges the repo itself draws (Equation.variables_on_rhs, which includes the
           validity predicate of an Approximation/Piecewise as a dependency).
  value  : only variables needed to compute the value (Equation._value_dependency_exprs).

An equation "feeds" a target when it is a non-constraint relation whose left-hand variable
is in the target's dependency cone (including the target). Constraint relations (inequalities)
are counted separately: they feed nothing by construction.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys

import gpu_stack  # noqa: F401  (populates Registry)
from gpu_stack import Registry
from gpu_stack.core.equation import RelationRole
from gpu_stack.core.symbolic import registered_variables_in_exprs

TARGETS = [
    "econ.cost.per_token",
    "training.tokens_per_sec",
    "econ.job.dc_power",
    "gpu.peak_flops",
]

NUC = re.compile(r"nucle|isotope|binding|neutron|proton|quark|pairing|valence|mass_number|atomic_number|"
                 r"stoichiom|rest_mass|reduced_mass|source_mass|molar_mass|particle_mass(?!_from)", re.I)
ATOM = re.compile(r"ioniz|saha|transition|shell|screening|ion_charge|bound_electron|principal|outer_shell|"
                  r"effective_nuclear_charge|inner_closed|same_shell|inner_shell", re.I)


def lith_sub(tail: str) -> str:
    if "plasma" in tail:
        return "physical_lith_plasma_source"
    if NUC.search(tail):
        return "physical_lith_nuclear_quark"
    if ATOM.search(tail):
        return "physical_lith_atomic"
    if tail.startswith(("medium", "component")) or "medium" in tail:
        return "physical_lith_medium_optics"
    return "physical_lith_k1_resolution"


def family_of_name(name: str) -> str:
    p = name.split(".")
    head = p[0]
    if head == "physical":
        sub = p[1] if len(p) > 1 else ""
        if sub == "eq":  # equation names: physical.eq.<thing>
            sub = p[2] if len(p) > 2 else ""
        if "lithography" in name or sub.startswith(("contact_k1", "gate_lithography", "contact_lithography",
                                                    "metal_width_lithography", "metal_spacing_lithography",
                                                    "metal_width_k1", "metal_spacing_k1")):
            tail = name.split("lithography", 1)[1] if "lithography" in name else sub
            return lith_sub(tail.lstrip("._"))
        if sub.startswith("interconnect") or "interconnect" in sub:
            return "physical_interconnect"
        if sub.startswith("mosfet") or sub in ("effective_threshold",):
            return "physical_mosfet"
        if sub.startswith("noise") or "noise" in sub:
            return "physical_noise"
        return "physical_other"
    return {
        "arch": "architecture", "mem": "memory", "memcell": "memory", "opt": "optimizer",
        "par": "parallelism", "link": "interconnect", "col": "collective", "arith": "arithmetic",
        "econ": "economics", "physics": "constants",
    }.get(head, head)


def lhs_name(eq) -> str:
    v = eq.lhs_variable()
    if v is not None:
        return v.name
    lv = eq.variables_on_lhs()
    return lv[0].name if lv else eq.name


def eq_family(eq) -> str:
    # physical.eq.* names carry the lithography/nuclear hint; other eqs follow their lhs variable
    if eq.name.startswith("physical.eq."):
        fam = family_of_name(eq.name)
        if fam in ("physical_other", "physical_lith_k1_resolution") and "lithography" not in eq.name:
            fam = family_of_name(lhs_name(eq))
        return fam
    return family_of_name(lhs_name(eq))


def value_vars(eq):
    return registered_variables_in_exprs(eq._value_dependency_exprs(), eq._bound_symbols())


def cone(target_name: str, mode: str):
    """Return (variable-name set, equation-name set) feeding the target."""
    seen_v = set()
    seen_e = set()
    stack = [Registry.variables[target_name]]
    while stack:
        v = stack.pop()
        if v.name in seen_v:
            continue
        seen_v.add(v.name)
        for eq in v.defining_equations:
            if eq.role is RelationRole.CONSTRAINT:
                continue
            seen_e.add(eq.name)
            deps = eq.variables_on_rhs() if mode == "graph" else value_vars(eq)
            for d in deps:
                if d.name not in seen_v:
                    stack.append(d)
    return seen_v, seen_e


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    ap.add_argument("--list-decorative", action="store_true")
    args = ap.parse_args()

    V = Registry.variables
    E = Registry.equations
    consts = {n for n, v in V.items() if type(v).__name__ == "Constant"}
    roots = {v.name for v in Registry.roots()}

    cones = {m: {t: cone(t, m) for t in TARGETS} for m in ("graph", "value")}
    union = {}
    for m in cones:
        uv, ue = set(), set()
        for t in TARGETS:
            uv |= cones[m][t][0]
            ue |= cones[m][t][1]
        union[m] = (uv, ue)

    # sanity: our graph cone must agree with the repo's subgraph()
    from gpu_stack import subgraph
    for t in TARGETS:
        repo = {v.name for v in subgraph(V[t], "dependencies")}
        mine = cones["graph"][t][0]
        if repo != mine:
            print(f"NOTE cone mismatch for {t}: repo={len(repo)} mine={len(mine)}", file=sys.stderr)

    fams = collections.defaultdict(lambda: collections.Counter())
    for n, v in V.items():
        f = family_of_name(n)
        fams[f]["vars"] += 1
        if n in consts:
            fams[f]["consts"] += 1
        if n in roots:
            fams[f]["roots"] += 1
            if n in union["graph"][0]:
                fams[f]["roots_feed_graph"] += 1
            if n in union["value"][0]:
                fams[f]["roots_feed_value"] += 1
        if n in union["graph"][0]:
            fams[f]["vars_feed_graph"] += 1
        if n in union["value"][0]:
            fams[f]["vars_feed_value"] += 1
        for t in TARGETS:
            if n in cones["graph"][t][0]:
                fams[f]["vars_" + t] += 1
    for n, e in E.items():
        f = eq_family(e)
        fams[f]["eqs"] += 1
        if e.role is RelationRole.CONSTRAINT:
            fams[f]["eq_constraint"] += 1
        if e.role is RelationRole.APPROXIMATION:
            fams[f]["eq_approx"] += 1
        if n in union["graph"][1]:
            fams[f]["eqs_feed_graph"] += 1
        if n in union["value"][1]:
            fams[f]["eqs_feed_value"] += 1
        for t in TARGETS:
            if n in cones["graph"][t][1]:
                fams[f]["eqs_" + t] += 1
        # does the equation carry at least one reference
        if e.references:
            fams[f]["eq_with_refs"] += 1

    cols = ["vars", "roots", "eqs", "eq_constraint", "eqs_feed_graph", "eqs_feed_value",
            "vars_feed_graph", "roots_feed_graph"]
    hdr = ["vars", "roots", "eqs", "constr", "eq_feed", "eq_feedV", "var_feed", "root_feed"]
    print("%-32s" % "family" + "".join("%10s" % c for c in hdr))
    tot = collections.Counter()
    for f in sorted(fams):
        print("%-32s" % f + "".join("%10d" % fams[f][c] for c in cols))
        tot.update(fams[f])
    print("%-32s" % "TOTAL" + "".join("%10d" % tot[c] for c in cols))

    print("\nPer target (graph mode / value mode):  variables, equations, roots needed")
    for t in TARGETS:
        gv, ge = cones["graph"][t]
        vv, ve = cones["value"][t]
        print(f"  {t:28s} vars {len(gv):4d}/{len(vv):4d}  eqs {len(ge):4d}/{len(ve):4d}  "
              f"roots {len(gv & roots):4d}/{len(vv & roots):4d}")
    gv, ge = union["graph"]
    vv, ve = union["value"]
    n_eq = len(E)
    n_nc = sum(1 for e in E.values() if e.role is not RelationRole.CONSTRAINT)
    n_v = len(V) - len(consts)
    print(f"\nUnion of 4 targets: eqs feed {len(ge)}/{n_eq} ({100*len(ge)/n_eq:.1f}%) graph; "
          f"{len(ve)}/{n_eq} ({100*len(ve)/n_eq:.1f}%) value")
    print(f"  non-constraint equations: {n_nc}; decorative (graph) = {n_nc-len(ge)} "
          f"({100*(n_nc-len(ge))/n_nc:.1f}% of non-constraint, {100*(n_eq-len(ge))/n_eq:.1f}% of all)")
    print(f"  variables (non-constant) feeding: {len(gv - consts)}/{n_v}; constants feeding: {len(gv & consts)}/{len(consts)}")
    print(f"  roots feeding: {len(gv & roots)}/{len(roots)}")

    # lithography / nuclear / quark
    lith = [n for n in E if eq_family(E[n]).startswith("physical_lith")]
    lith_v = [n for n in V if family_of_name(n).startswith("physical_lith")]
    print(f"\nlithography layer: {len(lith_v)} vars, {len(lith)} eqs; "
          f"eqs in any headline cone (graph) = {len([n for n in lith if n in ge])}, "
          f"vars in cone = {len([n for n in lith_v if n in gv])}")
    print("lithography eqs that DO feed a target:", [n for n in lith if n in ge][:20])
    q = [n for n in E if re.search(r"quark", n)]
    print("quark-named eqs:", len(q), "in cone:", len([n for n in q if n in ge]))

    # who consumes lithography output?
    lv_in_cone = [n for n in lith_v if n in gv]
    print("lithography vars in cone:", lv_in_cone[:20])

    # reference quality: does an equation cite an external work (paper/textbook/standard/datasheet/manual/database)?
    EXT = {"paper", "textbook", "standard", "datasheet", "manual", "database"}
    def ext(e):
        return any(r.kind in EXT for r in e.references)
    n_ext_all = sum(1 for e in E.values() if ext(e))
    n_ext_cone = sum(1 for n in ge if ext(E[n]))
    n_url = sum(1 for e in E.values() if any(r.url or r.doi for r in e.references))
    print(f"\nreferences: equations citing an external work (paper/textbook/standard/datasheet): "
          f"{n_ext_all}/{n_eq} all, {n_ext_cone}/{len(ge)} in headline cone; equations with any URL or DOI: {n_url}")
    kinds = collections.Counter(r.kind for e in E.values() for r in e.references)
    print("reference kinds:", dict(kinds))

    if args.list_decorative:
        print("\nDECORATIVE equations (not in any headline cone, graph mode):")
        for n in sorted(E):
            if n not in ge and E[n].role is not RelationRole.CONSTRAINT:
                print("  ", eq_family(E[n]), n)

    if args.json:
        out = {
            "families": {f: dict(c) for f, c in fams.items()},
            "targets": {t: {"graph_vars": len(cones["graph"][t][0]), "graph_eqs": len(cones["graph"][t][1]),
                            "value_vars": len(cones["value"][t][0]), "value_eqs": len(cones["value"][t][1])}
                        for t in TARGETS},
            "union_graph_eqs": len(ge), "union_value_eqs": len(ve), "total_eqs": n_eq,
            "decorative_eqs": sorted(n for n in E if n not in ge and E[n].role is not RelationRole.CONSTRAINT),
        }
        with open(args.json, "w") as fh:
            json.dump(out, fh, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
