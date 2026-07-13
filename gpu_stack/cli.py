"""
gpu_stack.cli
=============

Small command-line interface that exercises the registry, the scenario
resolver, and the preset library without requiring users to write Python.

Subcommands:

  stats              Print Registry.stats() and the coverage report.
  audit              Print graph-integrity and metadata audit signals.
  root-debt          Rank unresolved root inputs by downstream blast radius.
  next-work          Print a live continuation compass from graph evidence.
  experiment-protocol
                     Print a preregistered research protocol.
  experiment-run     Execute a virtual research experiment from an explicit
                     scenario artifact.
  verify             Run a compact local verification profile.
  list-presets       List the named presets under gpu_stack.presets.*.
  export-graph-json  Export dependency-cone JSON for portfolio page viewer.
  resolve TARGET     Resolve a target variable. Supply `--assign k=v` to
                     pin inputs, `--variant k=v` to select variant keys,
                     and `--preset name` to layer in a named preset.
                     Multiple --preset flags are combined in order so
                     later ones override earlier ones on conflicts.
                     Use `--constraints` to print evaluated feasibility
                     checks, and `--approximation-validity` to print
                     selected approximation regime checks.

Run with `python -m gpu_stack.cli <subcommand>`. The installed entry
point in pyproject.toml is `gpu-stack`.
"""

from __future__ import annotations

import argparse
import subprocess
import sys

from gpu_stack.cli_audit import (
    _large_project_files,
    _large_scope_files,
    cmd_audit,
    cmd_stats,
)
from gpu_stack.cli_common import (
    _coerce_value,
    _format_inputs,
    _iter_presets,
    _lookup_preset,
    _missing_family_groups,
    _parse_kv,
    _print_missing_family_groups,
    _print_unresolved_inputs,
    _print_violated_constraints,
    _repo_root,
    _short_list,
)
from gpu_stack.cli_resolve import cmd_resolve
from gpu_stack.cli_root_debt import (
    RootDebtEntry,
    RootDebtFamily,
    _format_weighted_roots,
    _root_debt_families,
    _root_debt_families_json,
    _root_debt_family_json,
    _root_debt_json,
    _root_debt_row_json,
    cmd_root_debt,
)
from gpu_stack.cli_scenario import (
    DEFAULT_SCENARIO_REPORT_TARGETS,
    _coerce_json_value,
    _parse_report_targets,
    _scenario_audit_json_dict,
    _scenario_audit_presets,
    _scenario_audit_targets,
    _scenario_report_json_dict,
    cmd_list_presets,
    cmd_scenario_audit,
    cmd_scenario_report,
)
from gpu_stack.cli_export_graph import cmd_export_graph
from gpu_stack.cli_research import cmd_experiment_protocol, cmd_experiment_run
from gpu_stack.cli_verify import (
    DEFAULT_GATE_TIMEOUT_SECONDS,
    VERIFY_TIMEOUT_RETURN_CODE,
    VerifyGate,
    VerifyGateResult,
    _coerce_timeout_text,
    _format_command,
    _format_timeout,
    _gate_timeout,
    _python_command,
    _pytest_command,
    _read_only_env,
    _run_verify_gate,
    _syntax_check_command,
    _tail,
    _verify_gates,
    cmd_verify as _cmd_verify,
)


def cmd_next_work(args: argparse.Namespace) -> int:
    from gpu_stack.next_work import build_next_work_plan

    plan = build_next_work_plan()
    if args.json:
        import json

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
    if plan.legacy_diagnostics:
        print()
        print("Legacy diagnostics (not scientific priorities):")
        for index, item in enumerate(plan.legacy_diagnostics, start=1):
            print(f"  {index}. {item.title}")
            print(f"     evidence: {item.evidence}")
            if item.command:
                print(f"     command: {item.command}")
            if item.path:
                print(f"     path: {item.path}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    return _cmd_verify(args, run_gate=_run_verify_gate)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gpu-stack",
        description="Command-line interface for the gpu_stack symbolic model.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_stats = subparsers.add_parser("stats", help="print registry counts and coverage")
    p_stats.set_defaults(func=cmd_stats)

    p_audit = subparsers.add_parser("audit", help="print graph-integrity audit signals")
    p_audit.add_argument(
        "--details", action="store_true", help="print concrete names behind nonzero counts",
    )
    p_audit.add_argument(
        "--fail-on-issues", action="store_true",
        help="return nonzero on cycles, collapsed equations, raw symbols, or topo failure",
    )
    p_audit.add_argument(
        "--large-file-threshold", type=int, default=700,
        help="line-count threshold for reporting oversized scope files",
    )
    p_audit.set_defaults(func=cmd_audit)

    p_roots = subparsers.add_parser(
        "root-debt",
        help="rank unresolved root inputs by transitive dependent count",
    )
    p_roots.add_argument(
        "--limit", type=int, default=20,
        help="number of roots to print",
    )
    p_roots.add_argument(
        "--scope", help="only show roots from this scope",
    )
    p_roots.add_argument(
        "--include-constraints", action="store_true",
        help="count constraint-only dependency edges in downstream blast radius",
    )
    p_roots.add_argument(
        "--families", action="store_true",
        help="group root-debt rows by compact boundary family",
    )
    p_roots.add_argument(
        "--json", action="store_true", help="print root-debt data as JSON"
    )
    p_roots.set_defaults(func=cmd_root_debt)

    p_next_work = subparsers.add_parser(
        "next-work",
        help="print the research-first priority, implementation, and risk compass",
    )
    p_next_work.add_argument(
        "--json",
        action="store_true",
        help="emit the live next-work compass as structured JSON",
    )
    p_next_work.set_defaults(func=cmd_next_work)

    p_experiment_protocol = subparsers.add_parser(
        "experiment-protocol",
        help="print a preregistered research protocol and falsifiers",
    )
    p_experiment_protocol.add_argument(
        "experiment",
        choices=(
            "E001",
            "E001-RECOVERY-V2",
            "E002",
            "E003",
            "E004",
            "E005",
            "E006",
        ),
        help="experiment identifier",
    )
    p_experiment_protocol.add_argument(
        "--json",
        action="store_true",
        help="emit the protocol and canonical hash as structured JSON",
    )
    p_experiment_protocol.set_defaults(func=cmd_experiment_protocol)

    p_experiment_run = subparsers.add_parser(
        "experiment-run",
        help="execute a virtual experiment from an explicit scenario artifact",
    )
    p_experiment_run.add_argument(
        "experiment",
        choices=("E001", "E001-RECOVERY-V2"),
        help="experiment identifier",
    )
    p_experiment_run.add_argument(
        "--scenario",
        required=True,
        metavar="PATH",
        help="path to the machine-readable experiment scenario",
    )
    p_experiment_run.add_argument(
        "--output",
        "-o",
        default="-",
        metavar="PATH",
        help="result artifact path; defaults to stdout (use - for stdout)",
    )
    p_experiment_run.add_argument(
        "--observatory-output",
        metavar="PATH",
        help="also write the evidence-preserving causal-observatory projection",
    )
    p_experiment_run.add_argument(
        "--observation",
        action="append",
        metavar="PATH",
        help=(
            "observation JSON to embed in the observatory artifact; repeat for "
            "multiple. E001 defaults to the repository literature observations"
        ),
    )
    p_experiment_run.set_defaults(func=cmd_experiment_run)

    p_verify = subparsers.add_parser(
        "verify",
        help="run compact fast or full verification gates",
    )
    p_verify.add_argument(
        "--profile",
        choices=("fast", "full"),
        default="fast",
        help="fast runs audit plus core tests; full runs pytest, compile, audit, and demo",
    )
    p_verify.add_argument(
        "--cwd",
        help="working directory for verification commands; defaults to repo root",
    )
    p_verify.add_argument(
        "--tail-lines",
        type=int,
        default=80,
        help="maximum stdout/stderr lines shown for a failed gate",
    )
    p_verify.add_argument(
        "--gate-timeout",
        type=float,
        default=None,
        help=(
            "seconds allowed per verification gate; defaults to 120 for fast "
            "and 300 for full; use 0 to disable"
        ),
    )
    p_verify.add_argument(
        "--read-only",
        action="store_true",
        help=(
            "avoid bytecode and pytest-cache writes where practical; full "
            "profile uses an in-memory syntax gate instead of compileall"
        ),
    )
    p_verify.set_defaults(func=cmd_verify)

    p_export = subparsers.add_parser(
        "export-graph-json",
        help="export dependency-cone JSON for the portfolio page viewer",
    )
    p_export.add_argument(
        "--target",
        dest="targets",
        action="append",
        metavar="VARIABLE",
        help=(
            "target variable to include; repeat for multiple. Defaults to "
            "econ.cost.per_token, training.tokens_per_sec, thermal.dc.pue"
        ),
    )
    p_export.add_argument(
        "--output",
        "-o",
        default="-",
        metavar="PATH",
        help="output file path; defaults to stdout (use - for stdout)",
    )
    p_export.set_defaults(func=cmd_export_graph)

    p_list = subparsers.add_parser("list-presets", help="list named presets")
    p_list.set_defaults(func=cmd_list_presets)

    p_report = subparsers.add_parser(
        "scenario-report",
        help="summarize preset resolution status for user-facing targets",
    )
    p_report.add_argument(
        "preset",
        nargs="+",
        metavar="QUALIFIED_NAME",
        help="preset name like scenarios.dense_training_cost_fixture; multiple presets combine in order",
    )
    p_report.add_argument(
        "--target",
        action="append",
        metavar="[LABEL=]VARIABLE",
        help=(
            "target variable to include; repeat for multiple. Defaults to "
            "tokens/sec, job DC power, run power cost, and cost/token"
        ),
    )
    p_report.add_argument(
        "--assign",
        action="append",
        metavar="NAME=VALUE",
        help="scenario assignment override; repeat for multiple",
    )
    p_report.add_argument(
        "--variant",
        action="append",
        metavar="NAME=KEY",
        help="variant selection override; repeat for multiple",
    )
    p_report.add_argument(
        "--details",
        action="store_true",
        help="print missing names and violated relation names for targets with issues",
    )
    p_report.add_argument(
        "--missing-families",
        action="store_true",
        help="group missing inputs by resolver boundary family diagnostics",
    )
    p_report.add_argument(
        "--json",
        action="store_true",
        help="emit a structured JSON scenario evaluation artifact",
    )
    p_report.add_argument(
        "--fail-on-issues",
        action="store_true",
        help="return nonzero when any report target has missing inputs or violated checks",
    )
    p_report.set_defaults(func=cmd_scenario_report)

    p_scenario_audit = subparsers.add_parser(
        "scenario-audit",
        help="audit all sourced scenario packs through their advertised targets",
    )
    p_scenario_audit.add_argument(
        "--preset",
        action="append",
        metavar="QUALIFIED_NAME",
        help=(
            "qualified preset name to audit; repeat for multiple. Defaults "
            "to all sourced scenario packs"
        ),
    )
    p_scenario_audit.add_argument(
        "--target",
        action="append",
        metavar="[LABEL=]VARIABLE",
        help=(
            "target variable to audit for every selected preset; repeat for "
            "multiple. Overrides advertised scenario targets"
        ),
    )
    p_scenario_audit.add_argument(
        "--json",
        action="store_true",
        help="emit structured JSON for every sourced scenario pack",
    )
    p_scenario_audit.add_argument(
        "--missing-families",
        action="store_true",
        help="group missing inputs by resolver boundary family diagnostics",
    )
    p_scenario_audit.add_argument(
        "--fail-on-issues",
        action="store_true",
        help="return nonzero when any sourced scenario target has issues",
    )
    p_scenario_audit.set_defaults(func=cmd_scenario_audit)

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
    p_resolve.add_argument(
        "--missing-families",
        action="store_true",
        help="group missing inputs by boundary-family diagnostics",
    )
    p_resolve.add_argument(
        "--diagnostics",
        action="store_true",
        help="print actionable unresolved-input and violated-constraint diagnostics",
    )
    p_resolve.add_argument(
        "--constraints", action="store_true",
        help="print constraint checks in the target dependency cone",
    )
    p_resolve.add_argument(
        "--approximation-validity", action="store_true",
        help="print validity checks for approximation equations used in the trace",
    )
    p_resolve.add_argument(
        "--fail-on-violated-constraints",
        action="store_true",
        help="return nonzero when any evaluated constraint is violated",
    )
    p_resolve.add_argument(
        "--fail-on-violated-approximation-validity",
        action="store_true",
        help="return nonzero when any selected approximation validity check is violated",
    )
    p_resolve.add_argument(
        "--fallback-on-violated-validity",
        dest="fallback_on_violated_validity",
        action="store_true",
        help=(
            "when a selected Approximation has a violated validity predicate "
            "and an alternative defining relation exists, retry with the "
            "alternative instead of keeping the violating approximation"
        ),
    )
    p_resolve.add_argument(
        "--solve-systems",
        dest="solve_systems",
        action="store_true",
        help=(
            "when resolution stalls on 2-3 variables that define each other "
            "(a small cycle), solve the subsystem simultaneously with "
            "sympy.solve/linsolve; accepts only unique real solutions "
            "consistent with variable symbol assumptions"
        ),
    )
    p_resolve.add_argument(
        "--explain-selection",
        dest="explain_selection",
        action="store_true",
        help=(
            "enrich trace steps with a selection_reason explaining why each "
            "relation was chosen, and unresolved inputs with a list of "
            "alternative equations that were not selectable"
        ),
    )
    p_resolve.set_defaults(func=cmd_resolve)
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
