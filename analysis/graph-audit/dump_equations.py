"""Dump equations as readable text for hand review.

Run:  PYTHONPATH=<repo> <venv python> -B analysis/graph-audit/dump_equations.py <name-prefix> [...]
Example: dump_equations.py training.eq econ.eq col.eq
Each record: name [role, in-headline-cone?], lhs = rhs, with the unit string of every variable
and the reference titles attached to the equation.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import gpu_stack  # noqa: F401,E402
from gpu_stack import Registry  # noqa: E402
from inventory import TARGETS, cone  # noqa: E402


def main(prefixes):
    feeds = set()
    for t in TARGETS:
        feeds |= cone(t, "graph")[1]
    for name, e in Registry.equations.items():
        if not any(name.startswith(p) for p in prefixes):
            continue
        print(f"## {name} [{e.role.name}{', variant=' + e.variant if e.variant else ''}"
              f"{', IN-CONE' if name in feeds else ', decorative'}]")
        print(f"   {e.lhs} = {e.rhs}")
        vs = e.variables_in_relation()
        print("   vars: " + "; ".join(f"{v.symbol}={v.name}[{v.units}]" for v in vs))
        print(f"   desc: {e.description.strip()[:300]}")
        if e.references:
            print("   refs: " + " | ".join(str(r)[:140] for r in e.references))
        if getattr(e, "validity", None) is not None and e.role.name == "APPROXIMATION":
            print(f"   validity: {e.validity}")


if __name__ == "__main__":
    main(sys.argv[1:] or ["training.eq"])
