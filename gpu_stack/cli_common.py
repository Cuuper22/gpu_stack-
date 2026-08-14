"""Helpers shared by the gpu_stack CLI subcommand modules.

Covers preset discovery and lookup, key=value argument parsing, and the
diagnostic printers for unresolved inputs, missing-input families, and
violated constraints. Each cli_*.py module imports from here so the
subcommands print diagnostics in one consistent format.
"""

from __future__ import annotations

import importlib
import pkgutil
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, TextIO, Tuple

import sympy as sp

import gpu_stack
from gpu_stack.core import Preset
from gpu_stack import presets as preset_package

def _iter_presets() -> Iterable[Tuple[str, Preset]]:
    for module_info in sorted(
        pkgutil.iter_modules(preset_package.__path__),
        key=lambda item: item.name,
    ):
        if module_info.ispkg:
            continue
        ns_name = module_info.name
        ns = importlib.import_module(f"{preset_package.__name__}.{ns_name}")
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


def _repo_root() -> Path:
    return Path(gpu_stack.__file__).resolve().parent.parent


def _short_list(items: Sequence[str], limit: int = 4) -> str:
    shown = list(items[:limit])
    extra = len(items) - len(shown)
    text = ", ".join(shown) if shown else "(none)"
    if extra > 0:
        text = f"{text}, +{extra} more"
    return text


def _format_inputs(inputs: Dict[str, sp.Expr]) -> str:
    if not inputs:
        return "(none)"
    return ", ".join(f"{name}={value}" for name, value in sorted(inputs.items()))


def _print_unresolved_inputs(
    items,
    file: TextIO | None = None,
    explain_alternatives: bool = False,
) -> None:
    if file is None:
        file = sys.stdout
    print("unresolved inputs:", file=file)
    for item in items:
        print(
            f"  {item.variable} [{item.units}] "
            f"scope={item.scope} kind={item.kind} reason={item.reason}",
            file=file,
        )
        print(f"    symbol: {item.symbol}", file=file)
        if item.variant_keys:
            print(
                "    hint: "
                f"--variant {item.variable}=<{ '|'.join(item.variant_keys) }> "
                f"or --assign {item.variable}=VALUE",
                file=file,
            )
        else:
            print(f"    hint: --assign {item.variable}=VALUE", file=file)
        if item.defining_equations:
            print(
                f"    definitions: {_short_list(item.defining_equations)}",
                file=file,
            )
        print(
            "    downstream: "
            f"{item.dependents_count} dependent(s); "
            f"direct {_short_list(item.direct_dependents)}",
            file=file,
        )
        if explain_alternatives and getattr(item, "not_selectable_alternatives", ()):
            print(
                f"    alternatives (not selectable): "
                f"{_short_list(item.not_selectable_alternatives)}",
                file=file,
            )


def _missing_family_groups(items, missing: Iterable[str]):
    """Group unresolved names by the resolver's compact boundary diagnostics."""
    diagnostics = {item.variable: item for item in items}
    groups: Dict[Tuple[str, str, bool], List[str]] = {}
    for name in sorted(missing):
        item = diagnostics.get(name)
        if item is None:
            key = ("unknown", "unknown", False)
        else:
            key = (
                item.family or "unknown",
                item.boundary_category or "unknown",
                bool(item.primitive_boundary),
            )
        groups.setdefault(key, []).append(name)
    return [
        (family, boundary_category, primitive_boundary, names)
        for (family, boundary_category, primitive_boundary), names in sorted(
            groups.items()
        )
    ]


def _print_missing_family_groups(
    items,
    missing: Iterable[str],
    *,
    indent: str = "",
    file: TextIO | None = None,
) -> None:
    if file is None:
        file = sys.stdout
    groups = _missing_family_groups(items, missing)
    if not groups:
        return
    print(f"{indent}missing families:", file=file)
    for family, boundary_category, primitive_boundary, names in groups:
        print(
            f"{indent}  family={family} "
            f"boundary_category={boundary_category} "
            f"primitive_boundary={primitive_boundary} "
            f"count={len(names)} names={_short_list(names)}",
            file=file,
        )


def _print_violated_constraints(items, file: TextIO | None = None) -> None:
    if file is None:
        file = sys.stdout
    print("violated constraints:", file=file)
    for item in items:
        print(
            f"  {item.equation} variable={item.variable} "
            f"evaluated={item.evaluated}",
            file=file,
        )
        print(f"    relation: {item.relation}", file=file)
        print(f"    inputs: {_format_inputs(item.inputs)}", file=file)
        if item.description:
            print(f"    description: {item.description}", file=file)
