"""The `list-presets`, `scenario-report`, and `scenario-audit` subcommands.

A preset is a named bundle of variable assignments and variant selections.
These commands list the available presets, evaluate one (or a combination)
against user-facing target variables, and audit every sourced scenario pack
through its advertised targets so stale packs fail loudly.
"""

from __future__ import annotations

import argparse
import json
from typing import Dict, List, Tuple

import sympy as sp

from gpu_stack import Registry
from gpu_stack.core import Preset, combine_presets
from gpu_stack import presets as preset_package
from gpu_stack.cli_common import (
    _coerce_value,
    _iter_presets,
    _lookup_preset,
    _parse_kv,
    _print_missing_family_groups,
)

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


DEFAULT_SCENARIO_REPORT_TARGETS: Tuple[Tuple[str, str], ...] = (
    ("tokens_per_second", "training.tokens_per_sec"),
    ("job_dc_power", "econ.job.dc_power"),
    ("run_power_cost", "econ.run.power_cost"),
    ("cost_per_token", "econ.cost.per_token"),
)


def _parse_report_targets(items: List[str] | None) -> List[Tuple[str, str]]:
    if not items:
        return list(DEFAULT_SCENARIO_REPORT_TARGETS)
    targets: List[Tuple[str, str]] = []
    for item in items:
        if "=" in item:
            label, target = item.split("=", 1)
            label = label.strip()
            target = target.strip()
        else:
            target = item.strip()
            label = target.rsplit(".", 1)[-1]
        if not label or not target:
            raise SystemExit(f"bad report target: {item!r}")
        if target not in Registry.variables:
            raise SystemExit(f"unknown report target variable: {target!r}")
        targets.append((label, target))
    return targets


def _coerce_json_value(value: object) -> object:
    """Return a JSON-friendly scalar while preserving symbolic strings."""
    if value is None:
        return None
    if not isinstance(value, str):
        return value
    try:
        expr = sp.sympify(value)
    except (TypeError, ValueError, sp.SympifyError):
        return value
    if getattr(expr, "free_symbols", set()):
        return value
    if expr.is_Integer:
        return int(expr)
    if expr.is_number:
        try:
            return float(expr)
        except TypeError:
            return value
    return value


def _scenario_report_json_dict(report) -> Dict[str, object]:
    """Adapt the core scenario artifact to a stable CLI JSON shape."""
    data = report.to_dict()
    targets = data.get("targets", {})
    if isinstance(targets, dict):
        data["targets"] = [
            {
                **target,
                "value": _coerce_json_value(target.get("value")),
            }
            for target in targets.values()
            if isinstance(target, dict)
        ]
    return data


def _scenario_audit_presets(selected: List[str] | None = None) -> List[Preset]:
    if selected:
        return [_lookup_preset(name) for name in selected]
    inventory = getattr(preset_package.scenarios, "SOURCED_SCENARIO_PACKS", ())
    return [
        item if isinstance(item, Preset) else getattr(preset_package.scenarios, item)
        for item in inventory
    ]


def _scenario_audit_targets(preset: Preset) -> List[Tuple[str, str]]:
    scenarios = preset_package.scenarios
    scenario_targets_for = getattr(scenarios, "scenario_targets_for", None)
    if callable(scenario_targets_for):
        try:
            targets = scenario_targets_for(preset)
        except KeyError:
            pass
        else:
            if hasattr(targets, "items"):
                return list(targets.items())
            return list(targets)
    if preset.name == "euv_tin120_lpp_source_context_assumption":
        return list(scenarios.EUV_TIN120_SOURCE_TARGETS.items())
    return list(DEFAULT_SCENARIO_REPORT_TARGETS)


def _scenario_audit_json_dict(reports) -> Dict[str, object]:
    report_items = [_scenario_report_json_dict(report) for report in reports]
    return {
        "pack_count": len(report_items),
        "issue_count": sum(int(item["issue_count"]) for item in report_items),
        "reports": report_items,
    }


def cmd_scenario_audit(args: argparse.Namespace) -> int:
    presets = _scenario_audit_presets(args.preset)
    target_override = _parse_report_targets(args.target) if args.target else None
    reports = tuple(
        preset.evaluate_targets(target_override or _scenario_audit_targets(preset))
        for preset in presets
    )
    total_issues = sum(report.issue_count for report in reports)

    if args.json:
        print(json.dumps(_scenario_audit_json_dict(reports), indent=2, sort_keys=True))
        if args.fail_on_issues and total_issues:
            return 1
        return 0

    print("Scenario audit:")
    print(f"  packs  {len(reports)}")
    print(f"  issues {total_issues}")
    for report in reports:
        print(
            f"  {report.preset_name}: {report.status} "
            f"targets={report.target_count} issues={report.issue_count} "
            f"sourced={report.has_source}"
        )
        for target in report.targets:
            print(
                f"    {target.label}: {target.status} "
                f"target={target.target} missing={target.missing_count} "
                f"violated_constraints={target.violated_constraint_count}"
            )
            if args.missing_families and target.missing_names:
                _print_missing_family_groups(
                    target.unresolved_inputs,
                    target.missing_names,
                    indent="      ",
                )

    if args.fail_on_issues and total_issues:
        return 1
    return 0


def cmd_scenario_report(args: argparse.Namespace) -> int:
    presets: List[Preset] = [_lookup_preset(name) for name in args.preset]
    if len(presets) == 1:
        preset = presets[0]
    else:
        preset = combine_presets(
            *presets,
            name="cli_scenario_report",
            description="combined scenario-report preset",
        )

    assignments_raw = _parse_kv(args.assign or [])
    variants = _parse_kv(args.variant or [])
    if assignments_raw or variants:
        preset = preset.with_overrides(
            assignments={k: _coerce_value(v) for k, v in assignments_raw.items()},
            variants=variants,
            name=f"{preset.name}+scenario_report_override",
        )

    targets = _parse_report_targets(args.target)
    report = preset.evaluate_targets(targets)

    if args.json:
        print(json.dumps(_scenario_report_json_dict(report), indent=2, sort_keys=True))
        if args.fail_on_issues and report.issue_count:
            return 1
        return 0

    print(f"Scenario report: {preset.name}")
    print(f"  presets     : {', '.join(args.preset)}")
    print(f"  assignments : {len(preset.assignments)}")
    print(f"  variants    : {len(preset.variants)}")
    print(f"  sourced     : {preset.has_source()}")
    print()
    print("targets:")

    for target_report in report.targets:
        if target_report.status == "error":
            print(
                f"  {target_report.label}: error target={target_report.target} "
                f"error={target_report.error_type}: {target_report.error_message}"
            )
            continue

        print(
            f"  {target_report.label}: {target_report.status} "
            f"target={target_report.target} value={target_report.value} "
            f"missing={target_report.missing_count} "
            f"violated_constraints={target_report.violated_constraint_count} "
            "violated_approximation_validity="
            f"{target_report.violated_approximation_validity_count} "
            f"trace_steps={target_report.trace_step_count}"
        )
        if args.details and target_report.missing_names:
            print(f"    missing: {list(target_report.missing_names)}")
        if args.missing_families and target_report.missing_names:
            _print_missing_family_groups(
                target_report.unresolved_inputs,
                target_report.missing_names,
                indent="    ",
            )
        if args.details and target_report.violated_constraint_equations:
            print(
                "    violated constraints: "
                f"{list(target_report.violated_constraint_equations)}"
            )
        if args.details and target_report.violated_approximation_validity_equations:
            print(
                "    violated approximation validity: "
                f"{list(target_report.violated_approximation_validity_equations)}"
            )

    if args.fail_on_issues and report.issue_count:
        return 1
    return 0
