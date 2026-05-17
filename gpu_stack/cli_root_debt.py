"""Root-debt ranking commands and formatters for the gpu_stack CLI."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

from gpu_stack import Registry
from gpu_stack.core.resolver import _boundary_family
from gpu_stack.cli_common import _short_list

@dataclass(frozen=True)
class RootDebtEntry:
    dependents: int
    name: str
    units: str
    scope: str
    family: str
    boundary_category: str
    primitive_boundary: bool


@dataclass(frozen=True)
class RootDebtFamily:
    total_weight: int
    root_count: int
    family: str
    boundary_category: str
    primitive_boundary: bool
    roots: Tuple[RootDebtEntry, ...]


def cmd_root_debt(args: argparse.Namespace) -> int:
    roots = Registry.roots()
    rows: List[RootDebtEntry] = []
    for root in roots:
        if args.scope and root.scope != args.scope:
            continue
        dependents = root.dependents(include_constraints=args.include_constraints)
        rows.append(
            RootDebtEntry(
                dependents=len(dependents),
                name=root.name,
                units=root.units,
                scope=root.scope,
                family=_boundary_family(root),
                boundary_category="primitive-root",
                primitive_boundary=root.is_root_input,
            )
        )
    rows.sort(key=lambda row: (-row.dependents, row.name))

    if args.families:
        family_rows = _root_debt_families(rows)
        if args.json:
            print(
                json.dumps(
                    _root_debt_families_json(args, len(roots), rows, family_rows),
                    indent=2,
                )
            )
            return 0

        print("Root-debt family ranking:")
        print(f"  total_roots        {len(roots)}")
        if args.scope:
            print(f"  filtered_scope     {args.scope}")
        print(f"  include_constraints {args.include_constraints}")
        print(f"  grouped_roots      {len(rows)}")
        print(f"  family_count       {len(family_rows)}")
        print(f"  shown              {min(args.limit, len(family_rows))}")
        print()
        print(
            f"{'total_weight':>12}  {'root_count':>10}  "
            f"{'family':<42}  {'boundary_category':<17}  "
            f"{'primitive_boundary':<18}  top_roots"
        )
        for family in family_rows[:args.limit]:
            print(
                f"{family.total_weight:>12}  {family.root_count:>10}  "
                f"{family.family:<42}  {family.boundary_category:<17}  "
                f"{str(family.primitive_boundary):<18}  "
                f"{_format_weighted_roots(family.roots)}"
            )
        return 0

    if args.json:
        print(json.dumps(_root_debt_json(args, len(roots), rows), indent=2))
        return 0

    print("Root-debt ranking:")
    print(f"  total_roots        {len(roots)}")
    if args.scope:
        print(f"  filtered_scope     {args.scope}")
    print(f"  include_constraints {args.include_constraints}")
    print(f"  shown              {min(args.limit, len(rows))}")
    print()
    print(f"{'dependents':>10}  {'scope':<18}  {'variable':<48}  units")
    for row in rows[:args.limit]:
        print(
            f"{row.dependents:>10}  {row.scope:<18}  "
            f"{row.name:<48}  {row.units}"
        )
    return 0


def cmd_next_work(args: argparse.Namespace) -> int:
    from gpu_stack.next_work import build_next_work_plan

    plan = build_next_work_plan()
    if args.json:
        print(json.dumps(plan.to_dict(), indent=2, sort_keys=True))
        return 0

    sections = (
        ("Top 3 highest impact", plan.highest_impact),
        ("4 best implementations", plan.best_implementations),
        ("10 bugs/risks", plan.bug_risks),
    )
    print("Next work:")
    print(
        "  graph evidence: "
        f"variables={plan.graph_evidence['variables']} "
        f"equations={plan.graph_evidence['equations']} "
        f"root_inputs={plan.graph_evidence['root_inputs']}"
    )
    for title, items in sections:
        print()
        print(f"{title}:")
        for index, item in enumerate(items, start=1):
            print(f"  {index}. {item.title}")
            print(f"     evidence: {item.evidence}")
            if item.command:
                print(f"     command: {item.command}")
            if item.path:
                print(f"     path: {item.path}")
    return 0


def _root_debt_json(
    args: argparse.Namespace,
    total_roots: int,
    rows: Sequence[RootDebtEntry],
) -> Dict[str, object]:
    shown = min(args.limit, len(rows))
    return {
        "total_roots": total_roots,
        "filtered_scope": args.scope,
        "include_constraints": args.include_constraints,
        "shown": shown,
        "rows": [_root_debt_row_json(row) for row in rows[: args.limit]],
    }


def _root_debt_families_json(
    args: argparse.Namespace,
    total_roots: int,
    rows: Sequence[RootDebtEntry],
    family_rows: Sequence[RootDebtFamily],
) -> Dict[str, object]:
    shown = min(args.limit, len(family_rows))
    return {
        "total_roots": total_roots,
        "filtered_scope": args.scope,
        "include_constraints": args.include_constraints,
        "grouped_roots": len(rows),
        "family_count": len(family_rows),
        "shown": shown,
        "families": [
            _root_debt_family_json(family) for family in family_rows[: args.limit]
        ],
    }


def _root_debt_row_json(row: RootDebtEntry) -> Dict[str, object]:
    return {
        "dependents": row.dependents,
        "scope": row.scope,
        "variable": row.name,
        "units": row.units,
        "family": row.family,
        "boundary_category": row.boundary_category,
        "primitive_boundary": row.primitive_boundary,
    }


def _root_debt_family_json(family: RootDebtFamily) -> Dict[str, object]:
    return {
        "total_weight": family.total_weight,
        "root_count": family.root_count,
        "family": family.family,
        "boundary_category": family.boundary_category,
        "primitive_boundary": family.primitive_boundary,
        "top_roots": [
            {"variable": row.name, "dependents": row.dependents}
            for row in family.roots[:4]
        ],
    }


def _root_debt_families(rows: Sequence[RootDebtEntry]) -> List[RootDebtFamily]:
    grouped: Dict[Tuple[str, str, bool], List[RootDebtEntry]] = {}
    for row in rows:
        key = (row.family, row.boundary_category, row.primitive_boundary)
        grouped.setdefault(key, []).append(row)

    family_rows: List[RootDebtFamily] = []
    for (family, boundary_category, primitive_boundary), roots in grouped.items():
        ranked_roots = tuple(sorted(roots, key=lambda row: (-row.dependents, row.name)))
        family_rows.append(
            RootDebtFamily(
                total_weight=sum(row.dependents for row in ranked_roots),
                root_count=len(ranked_roots),
                family=family,
                boundary_category=boundary_category,
                primitive_boundary=primitive_boundary,
                roots=ranked_roots,
            )
        )
    family_rows.sort(
        key=lambda row: (-row.total_weight, -row.root_count, row.family)
    )
    return family_rows


def _format_weighted_roots(
    roots: Sequence[RootDebtEntry],
    *,
    limit: int = 4,
) -> str:
    return _short_list(
        [f"{row.name}:{row.dependents}" for row in roots],
        limit=limit,
    )
