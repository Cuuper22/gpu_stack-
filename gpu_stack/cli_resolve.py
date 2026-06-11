"""Resolve command implementation for the gpu_stack CLI."""

from __future__ import annotations

import argparse
import sys
from typing import List

from gpu_stack import resolve
from gpu_stack.core import Preset, ResolverError, combine_presets
from gpu_stack.cli_common import (
    _coerce_value,
    _lookup_preset,
    _parse_kv,
    _print_missing_family_groups,
    _print_unresolved_inputs,
    _print_violated_constraints,
)

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

    fallback = getattr(args, "fallback_on_violated_validity", False)
    solve_sys = getattr(args, "solve_systems", False)
    explain = getattr(args, "explain_selection", False)

    try:
        result = resolve(
            args.target,
            assignments=assignments,
            variants=variants,
            fallback_on_violated_validity=fallback,
            solve_systems=solve_sys,
            explain_selection=explain,
        )
    except ResolverError as exc:
        print(f"resolve error: {exc}", file=sys.stderr)
        unresolved_inputs = getattr(exc, "unresolved_inputs", [])
        if unresolved_inputs:
            print(file=sys.stderr)
            _print_unresolved_inputs(unresolved_inputs, file=sys.stderr)
        return 1
    print(f"{args.target} = {result.value}")
    if args.trace:
        print()
        print("trace:")
        for step in result.trace:
            variant_part = "/" + step.variant if step.variant else ""
            fallback_part = (
                f" [fallback from {step.fallback_from}]"
                if step.fallback_from else ""
            )
            system_part = (
                f" [system: {', '.join(step.system_peers)}]"
                if step.system_peers else ""
            )
            reason_part = (
                f" [why: {step.selection_reason}]"
                if step.selection_reason else ""
            )
            print(
                f"  {step.variable} <- {step.equation} "
                f"({step.role.name}{variant_part})"
                f"{fallback_part}{system_part}{reason_part}"
                f" = {step.value}"
            )
    if args.missing and result.missing:
        print()
        print(f"missing: {sorted(result.missing)}")
        if result.unresolved_inputs:
            _print_unresolved_inputs(
                result.unresolved_inputs,
                explain_alternatives=explain,
            )
    if args.missing_families and result.missing:
        print()
        _print_missing_family_groups(result.unresolved_inputs, result.missing)
    if args.constraints:
        print()
        print("constraints:")
        if not result.constraints:
            print("  (none in dependency cone)")
        for check in result.constraints:
            if check.satisfied is True:
                status = "satisfied"
            elif check.satisfied is False:
                status = "violated"
            else:
                status = "symbolic"
            print(f"  {check.equation} [{status}] {check.evaluated}")
    if args.diagnostics:
        diagnostics_printed = False
        if result.unresolved_inputs and not args.missing:
            print()
            _print_unresolved_inputs(
                result.unresolved_inputs,
                explain_alternatives=explain,
            )
            diagnostics_printed = True
        if result.violated_constraints:
            print()
            _print_violated_constraints(result.violated_constraints)
            diagnostics_printed = True
        if not diagnostics_printed:
            print()
            print("diagnostics: no unresolved inputs or violated constraints")
    if args.approximation_validity:
        print()
        print("approximation validity:")
        if not result.approximation_validity:
            print("  (none in selected trace)")
        for check in result.approximation_validity:
            if check.satisfied is True:
                status = "satisfied"
            elif check.satisfied is False:
                status = "violated"
            else:
                status = "symbolic"
            print(f"  {check.equation} [{status}] {check.evaluated}")
    if args.fail_on_violated_constraints and result.violated_constraints:
        if not args.constraints and not args.diagnostics:
            print("resolve error: violated constraints", file=sys.stderr)
            _print_violated_constraints(result.violated_constraints, file=sys.stderr)
        return 1
    if args.fail_on_violated_approximation_validity and any(
        check.satisfied is False for check in result.approximation_validity
    ):
        return 1
    return 0
