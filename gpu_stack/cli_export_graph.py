"""
gpu_stack.cli_export_graph
==========================

CLI subcommand ``export-graph-json`` that walks the dependency cones of
chosen target variables and writes a bounded JSON artifact suitable for
static hosting on the GitHub Pages portfolio.

Default targets: econ.cost.per_token, training.tokens_per_sec, thermal.dc.pue

Output structure (all collections sorted for deterministic diffs):

  {
    "version": 1,
    "generated_at": "<ISO-8601>",
    "targets": ["econ.cost.per_token", ...],
    "nodes": {
      "econ.cost.per_token": {
        "name": "econ.cost.per_token",
        "units": "USD/token",
        "scope": "economics",
        "description": "...",  // trimmed to DESC_LIMIT chars
        "is_root_input": false,
        "is_constant": false,
        "defining_equations": ["econ.eq.cost_per_token"]
      },
      ...
    },
    "edges": [
      {"from": "dep_var", "to": "defined_var"},
      ...
    ]
  }

The ``edges`` list contains one entry for each (dependency -> dependent)
pair that appears in the combined dependency cones of the chosen targets.
Only value-defining relations (not constraint-only) contribute edges, so
the graph mirrors what ``Variable.dependencies()`` traverses.

Payload is bounded to the dependency cones only (no extraneous registry
nodes) and descriptions are capped at DESC_LIMIT characters.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Dict, List, Set

DESC_LIMIT = 160
DEFAULT_TARGETS = [
    "econ.cost.per_token",
    "training.tokens_per_sec",
    "thermal.dc.pue",
]


def _build_cone(
    target_names: List[str],
) -> tuple[Set[str], List[dict]]:
    """
    Collect all nodes in the union of dependency cones and build the edge list.

    Returns (node_name_set, edges_list).
    """
    from gpu_stack.core.registry import Registry

    # Collect each target plus every variable in its dependency cone.
    cone_vars: Set[str] = set()
    for name in target_names:
        var = Registry.variables.get(name)
        if var is None:
            raise KeyError(f"Target variable not in registry: {name!r}")
        cone_vars.add(var.name)
        for dep in var.dependencies():
            cone_vars.add(dep.name)

    # Emit one (dependency -> dependent) edge for each direct dependency that
    # is also inside the cone. Only value-defining relations contribute, so
    # the edge list mirrors what Variable.dependencies() traverses.
    seen_edges: Set[tuple] = set()
    edges: List[dict] = []
    for vname in sorted(cone_vars):
        var = Registry.variables[vname]
        for dep in var.direct_dependencies():
            if dep.name in cone_vars:
                key = (dep.name, vname)
                if key not in seen_edges:
                    seen_edges.add(key)
                    edges.append({"from": dep.name, "to": vname})

    edges.sort(key=lambda e: (e["from"], e["to"]))
    return cone_vars, edges


def _build_nodes(cone_vars: Set[str]) -> Dict[str, dict]:
    """Build the nodes dict from the cone variable set."""
    from gpu_stack.core.registry import Registry
    from gpu_stack.core.variable import Constant
    from gpu_stack.core.equation import RelationRole

    nodes: Dict[str, dict] = {}
    for vname in sorted(cone_vars):
        var = Registry.variables[vname]
        is_const = isinstance(var, Constant)
        # Collect value-defining equation names (exclude constraint-only).
        def_eqs = [
            eq.name
            for eq in var._defined_by
            if eq.role is not RelationRole.CONSTRAINT
        ]
        def_eqs.sort()

        desc = (var.description or "").strip()
        if len(desc) > DESC_LIMIT:
            desc = desc[:DESC_LIMIT].rstrip() + "..."

        nodes[vname] = {
            "name": vname,
            "units": var.units,
            "scope": var.scope,
            "description": desc,
            "is_root_input": var.is_root_input,
            "is_constant": is_const,
            "defining_equations": def_eqs,
        }
    return nodes


def build_export_payload(target_names: List[str]) -> dict:
    """Build the complete JSON payload dict for the given targets."""
    cone_vars, edges = _build_cone(target_names)
    nodes = _build_nodes(cone_vars)
    return {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "targets": sorted(target_names),
        "nodes": nodes,
        "edges": edges,
    }


def cmd_export_graph(args: argparse.Namespace) -> int:
    """Entry-point for the export-graph-json subcommand."""
    target_names: List[str] = list(args.targets) if args.targets else DEFAULT_TARGETS

    try:
        payload = build_export_payload(target_names)
    except KeyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    json_text = json.dumps(payload, indent=2, ensure_ascii=False)

    if args.output and args.output != "-":
        import pathlib
        out_path = pathlib.Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json_text, encoding="utf-8")
        node_count = len(payload["nodes"])
        edge_count = len(payload["edges"])
        size_kb = len(json_text.encode()) / 1024
        print(
            f"Wrote {out_path}  "
            f"({node_count} nodes, {edge_count} edges, {size_kb:.1f} KB)"
        )
    else:
        print(json_text)
    return 0


__all__ = ["build_export_payload", "cmd_export_graph", "DEFAULT_TARGETS"]
