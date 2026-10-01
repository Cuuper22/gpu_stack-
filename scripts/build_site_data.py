#!/usr/bin/env python3
"""Regenerate the website's calculator data.

Writes:
  docs/data/calculator-model.json  the calculator's graph-resolved expressions, GPU table and test cases
  docs/data/drivers.json           what drives the cost per token (variance-based sensitivity)

Run from the repo root:  python scripts/build_site_data.py [--skip-drivers] [--n-pow 15]
Needs sympy, numpy and scipy (the drivers step).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DATA = ROOT / "docs" / "data"


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {path.relative_to(ROOT)} ({path.stat().st_size:,} bytes)")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-drivers", action="store_true", help="only rebuild the calculator model")
    ap.add_argument("--n-pow", type=int, default=15, help="Sobol base sample size 2**n (default 15)")
    args = ap.parse_args(argv)

    from gpu_stack import calculator

    write_json(DATA / "calculator-model.json", calculator.web_model())
    if not args.skip_drivers:
        from gpu_stack import drivers

        write_json(DATA / "drivers.json", drivers.compute_drivers(n_pow=args.n_pow))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
