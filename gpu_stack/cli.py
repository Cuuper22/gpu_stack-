"""
gpu_stack.cli
=============

Small command-line interface that exercises the registry, the scenario
resolver, and the preset library without requiring users to write Python.

Subcommands:

  stats              Print Registry.stats() and the coverage report.
  list-presets       List the named presets under gpu_stack.presets.*.
  resolve TARGET     Resolve a target variable. Supply `--assign k=v` to
                     pin inputs, `--variant k=v` to select variant keys,
                     and `--preset name` to layer in a named preset.
                     Multiple --preset flags are combined in order so
                     later ones override earlier ones on conflicts.

Run with `python -m gpu_stack.cli <subcommand>`. The installed entry
point in pyproject.toml is `gpu-stack`.
"""

from __future__ import annotations

import argparse
import sys
from typing import Dict, Iterable, List, Tuple

import gpu_stack
from gpu_stack import Registry, resolve
from gpu_stack.core import Preset, combine_presets
from gpu_stack.presets import hardware, workload


_PRESET_NAMESPACES = {
    "hardware": hardware,
    "workload": workload,
}


def _iter_presets() -> Iterable[Tuple[str, Preset]]:
    for ns_name, ns in _PRESET_NAMESPACES.items():
        for attr in sorted(dir(ns)):
            if attr.startswith("_"):
                continue
            value = getattr(ns, attr)
            if isinstance(value, Preset):
                yield f"{ns_name}.{attr}", value


def _lookup_preset(qualified: str) -> Preset:
    for name, preset in _iter_presets():
        if name == qualified:
            return preset
    available = ", ".join(name for name, _ in _iter_presets())
    raise SystemExit(
        f"unknown preset {qualified!r}. available: {available}"
    )


def _parse_kv(items: List[str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise SystemExit(f"bad key=value pair: {item!r}")
        k, v = item.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def _coerce_value(raw: str):
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    return raw


def cmd_stats(_args: argparse.Namespace) -> int:
    stats = Registry.stats()
    print("Registry stats:")
    for key in ("systems", "variables", "constants", "equations", "root_inputs", "leaves"):
        print(f"  {key:<14} {stats[key]}")
    print()
    print("Coverage:")
    for key, value in Registry.coverage().items():
        print(f"  {key:<30} {value}")
    return 0


def cmd_list_presets(_args: argparse.Namespace) -> int:
    presets = list(_iter_presets())
    if not presets:
        print("(no presets registered)")
        return 0
    for name, preset in presets:
        source = preset.source or "(no source)"
        print(f"{name}")
        print(f"  description : {preset.description}")
        print(f"  assignments : {len(preset.assignments)} keys")
        print(f"  variants    : {len(preset.variants)} keys")
        print(f"  source      : {source}")
    return 0


def cmd_resolve(args: argparse.Namespace) -> int:
    assignments_raw = _parse_kv(args.assign or [])
    assignments = {k: _coerce_value(v) for k, v in assignments_raw.items()}
    variants = _parse_kv(args.variant or [])

    presets: List[Preset] = [_lookup_preset(name) for name in (args.preset or [])]
    if presets:
        base = combine_presets(*presets, name="cli_combined")
        merged_assignments = dict(base.assignments)
        merged_assignments.update(assignments)
        merged_variants = dict(base.variants)
        merged_variants.update(variants)
        assignments = merged_assignments
        variants = merged_variants

    result = resolve(args.target, assignments=assignments, variants=variants)
    print(f"{args.target} = {result.value}")
    if args.trace:
        print()
        print("trace:")
        for step in result.trace:
            print(
                f"  {step.variable} <- {step.equation} "
                f"({step.role.name}{'/' + step.variant if step.variant else ''}) "
                f"= {step.value}"
            )
    if args.missing and result.missing:
        print()
        print(f"missing: {sorted(result.missing)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gpu-stack",
        description="Command-line interface for the gpu_stack symbolic model.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_stats = subparsers.add_parser("stats", help="print registry counts and coverage")
    p_stats.set_defaults(func=cmd_stats)

    p_list = subparsers.add_parser("list-presets", help="list named presets")
    p_list.set_defaults(func=cmd_list_presets)

    p_resolve = subparsers.add_parser("resolve", help="resolve a target variable")
    p_resolve.add_argument("target", help="registered variable name")
    p_resolve.add_argument(
        "--assign", action="append", metavar="NAME=VALUE",
        help="scenario assignment; repeat for multiple",
    )
    p_resolve.add_argument(
        "--variant", action="append", metavar="NAME=KEY",
        help="variant selection for a VARIANT-tagged variable; repeat for multiple",
    )
    p_resolve.add_argument(
        "--preset", action="append", metavar="QUALIFIED_NAME",
        help="preset name like hardware.demo_rack; repeat to combine",
    )
    p_resolve.add_argument(
        "--trace", action="store_true", help="print the equation trace",
    )
    p_resolve.add_argument(
        "--missing", action="store_true", help="list unresolved dependencies",
    )
    p_resolve.set_defaults(func=cmd_resolve)
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
