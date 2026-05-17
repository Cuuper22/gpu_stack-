"""Stats and graph-integrity audit commands for the gpu_stack CLI."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Tuple

import sympy as sp

import gpu_stack
from gpu_stack import Registry
from gpu_stack.core import Approximation
from gpu_stack.cli_common import _repo_root

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


def _large_scope_files(threshold: int) -> List[Tuple[str, int]]:
    scopes_dir = Path(gpu_stack.__file__).parent / "scopes"
    out: List[Tuple[str, int]] = []
    for path in sorted(scopes_dir.glob("*.py")):
        if path.name == "__init__.py":
            continue
        lines = len(path.read_text(encoding="utf-8").splitlines())
        if lines >= threshold:
            out.append((path.name, lines))
    return out


def _large_project_files(threshold: int) -> List[Tuple[str, int]]:
    repo_root = _repo_root()
    roots = [Path(gpu_stack.__file__).parent, repo_root / "tests"]
    out: List[Tuple[str, int]] = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            lines = len(path.read_text(encoding="utf-8").splitlines())
            if lines >= threshold:
                out.append((path.relative_to(repo_root).as_posix(), lines))
    return out


def cmd_audit(args: argparse.Namespace) -> int:
    stats = Registry.stats()
    coverage = Registry.coverage()
    cycles = gpu_stack.find_cycles()
    try:
        topo_len = len(gpu_stack.topological_sort())
        topo_error = ""
    except RuntimeError as exc:
        topo_len = 0
        topo_error = str(exc)

    collapsed = [
        e.name for e in Registry.equations.values()
        if e.as_sympy() in (sp.S.true, sp.S.false)
    ]
    collapsed_approximation_validity = [
        e.name for e in Registry.equations.values()
        if isinstance(e, Approximation)
        and getattr(e, "validity", None) in (sp.S.true, sp.S.false, True, False)
    ]
    raw_symbols = {
        e.name: sorted(str(s) for s in e.raw_dependency_symbols())
        for e in Registry.equations.values()
        if e.raw_dependency_symbols()
    }
    orphan_value_equations = [
        e.name for e in Registry.equations.values()
        if e.role is not gpu_stack.RelationRole.CONSTRAINT
        and e.lhs_variable() is None
    ]
    multi_definition = [
        v.name for v in Registry.variables.values()
        if v.has_multiple_definitions()
    ]
    large_scope_files = _large_scope_files(args.large_file_threshold)
    large_project_files = _large_project_files(args.large_file_threshold)
    positive_symbols = [
        v.name for v in Registry.variables.values()
        if v.symbol.is_positive is True
    ]
    forced_noninteger = [
        v.name for v in Registry.variables.values()
        if v.symbol.is_integer is False
    ]

    hard_failures = (
        len(cycles)
        + len(collapsed)
        + len(collapsed_approximation_validity)
        + len(raw_symbols)
        + len(orphan_value_equations)
        + (1 if topo_error or topo_len != len(Registry.variables) else 0)
    )

    print("Audit:")
    print(f"  systems                         {stats['systems']}")
    print(f"  variables                       {stats['variables']}")
    print(f"  constants                       {stats['constants']}")
    print(f"  equations                       {stats['equations']}")
    print(f"  root_inputs                     {stats['root_inputs']}")
    print(f"  leaves                          {stats['leaves']}")
    print(f"  cycles                          {len(cycles)}")
    print(f"  topological_order_length        {topo_len}")
    print(f"  collapsed_equations             {len(collapsed)}")
    print(f"  collapsed_approximation_validity {len(collapsed_approximation_validity)}")
    print(f"  unresolved_raw_symbols          {len(raw_symbols)}")
    print(f"  orphan_value_equations          {len(orphan_value_equations)}")
    print(f"  multi_definition_variables      {len(multi_definition)}")
    print(f"  positive_symbols                {len(positive_symbols)}")
    print(f"  forced_noninteger_symbols       {len(forced_noninteger)}")
    print(f"  large_scope_files               {len(large_scope_files)}")
    print(f"  large_project_files             {len(large_project_files)}")
    print(f"  hard_failures                   {hard_failures}")
    print()
    print("Metadata:")
    for key, value in coverage.items():
        print(f"  {key:<30} {value}")

    if args.details:
        print()
        print("Details:")
        if topo_error:
            print(f"  topological_error: {topo_error}")
        if collapsed:
            print("  collapsed_equations:")
            for name in collapsed:
                print(f"    {name}")
        if collapsed_approximation_validity:
            print("  collapsed_approximation_validity:")
            for name in collapsed_approximation_validity:
                print(f"    {name}")
        if raw_symbols:
            print("  unresolved_raw_symbols:")
            for name, symbols in raw_symbols.items():
                print(f"    {name}: {', '.join(symbols)}")
        if orphan_value_equations:
            print("  orphan_value_equations:")
            for name in orphan_value_equations:
                print(f"    {name}")
        if multi_definition:
            print("  multi_definition_variables:")
            for name in multi_definition:
                print(f"    {name}")
        if large_scope_files:
            print("  large_scope_files:")
            for name, lines in large_scope_files:
                print(f"    {name}: {lines}")
        if large_project_files:
            print("  large_project_files:")
            for name, lines in large_project_files:
                print(f"    {name}: {lines}")

    if args.fail_on_issues and hard_failures:
        return 1
    return 0
