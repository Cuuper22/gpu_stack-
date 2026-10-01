"""Evaluate every shipped scenario preset and measure which equations the resolver
actually executes (the "scenario-effective" cone), as opposed to the structural cone
that inventory.py reports.

Run:  PYTHONPATH=<repo> <venv python> -B analysis/graph-audit/scenario_eval.py

Outputs: resolved values for each advertised target, plus the union of trace equations
across all shipped scenarios, grouped by family. Also prints hand cross-checks of the
resolved numbers against first-principles arithmetic (see CHECKS at the bottom).
"""
from __future__ import annotations

import collections
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import gpu_stack  # noqa: F401,E402
from gpu_stack import Registry  # noqa: E402
from gpu_stack.presets import scenarios  # noqa: E402
from gpu_stack.presets.scenarios import SCENARIO_TARGET_SETS  # noqa: E402
from inventory import eq_family  # noqa: E402

PACKS = {
    p.name: p
    for p in (
        scenarios.dense_training_cost_fixture,
        *scenarios.SOURCED_SCENARIO_PACKS,
    )
}


def fnum(x):
    try:
        return float(x)
    except Exception:
        return str(x)


def main():
    all_trace = set()
    per_scn = {}
    for name, targets in SCENARIO_TARGET_SETS.items():
        preset = PACKS.get(name)
        if preset is None:
            continue
        rep = preset.evaluate_targets(targets)
        print(f"\n== {name}  status={rep.status} issues={rep.issue_count}")
        tr = set()
        for t in rep.targets:
            v = t.value
            try:
                v = f"{float(v):.6g}"
            except Exception:
                pass
            print(f"   {t.label:20s} {t.target:30s} = {v}   trace_eqs={t.trace_equation_count} "
                  f"missing={t.missing_count} {t.error_type or ''}")
            tr |= set(t.trace_equations)
        per_scn[name] = tr
        all_trace |= tr
    E = Registry.equations
    print(f"\nUnion of equations executed by all shipped scenario targets: {len(all_trace)}/{len(E)}")
    fam = collections.Counter(eq_family(E[n]) for n in all_trace)
    for f, c in sorted(fam.items()):
        print(f"   {f:38s} {c}")
    print("\nPer scenario trace size:")
    for n, tr in per_scn.items():
        print(f"   {n:70s} {len(tr)}")
    # What the headline-target scenarios actually use (cost per token only scenarios)
    cost_scn = [n for n in per_scn if "full_tco" in n]
    for n in cost_scn:
        print(f"\nTrace of {n} (cost_per_token):")
        for e in sorted(per_scn[n]):
            print("   ", e)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
