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
  verify             Run a compact local verification profile.
  list-presets       List the named presets under gpu_stack.presets.*.
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
import importlib
import json
import os
import pkgutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, TextIO, Tuple

import sympy as sp

import gpu_stack
from gpu_stack import Registry, resolve
from gpu_stack.core import Approximation, Preset, ResolverError, combine_presets
from gpu_stack.core.resolver import _boundary_family
from gpu_stack import presets as preset_package


@dataclass(frozen=True)
class VerifyGate:
    name: str
    command: Tuple[str, ...]
    env: Dict[str, str] | None = None


@dataclass(frozen=True)
class VerifyGateResult:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False


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


VERIFY_TIMEOUT_RETURN_CODE = 124
DEFAULT_GATE_TIMEOUT_SECONDS = {
    "fast": 120.0,
    "full": 300.0,
}


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


def _repo_root() -> Path:
    return Path(gpu_stack.__file__).resolve().parent.parent


def _python_command(*args: str, read_only: bool = False) -> Tuple[str, ...]:
    python = sys.executable
    if read_only:
        return (python, "-B", *args)
    return (python, *args)


def _read_only_env(read_only: bool) -> Dict[str, str] | None:
    if not read_only:
        return None
    return {"PYTHONDONTWRITEBYTECODE": "1"}


def _pytest_command(*args: str, read_only: bool = False) -> Tuple[str, ...]:
    command = _python_command("-m", "pytest", *args, read_only=read_only)
    if read_only:
        command = (*command, "-p", "no:cacheprovider")
    return command


def _syntax_check_command(read_only: bool = False) -> Tuple[str, ...]:
    script = (
        "from pathlib import Path\n"
        "import tokenize\n"
        "for root in ('gpu_stack', 'tests'):\n"
        "    for path in Path(root).rglob('*.py'):\n"
        "        with tokenize.open(path) as handle:\n"
        "            compile(handle.read(), str(path), 'exec')\n"
    )
    return _python_command("-c", script, read_only=read_only)


def _verify_gates(profile: str, read_only: bool = False) -> List[VerifyGate]:
    env = _read_only_env(read_only)
    if profile == "fast":
        return [
            VerifyGate(
                "audit",
                _python_command(
                    "-m",
                    "gpu_stack.cli",
                    "audit",
                    "--fail-on-issues",
                    read_only=read_only,
                ),
                env=env,
            ),
            VerifyGate(
                "core-tests",
                _pytest_command(
                    "tests/test_import.py",
                    "tests/test_graph_health.py",
                    "tests/test_units.py",
                    "tests/test_relation_roles.py",
                    "tests/test_symbolic_integrity.py",
                    "tests/test_resolver.py",
                    "tests/test_cli.py",
                    (
                        "tests/test_process_geometry.py::"
                        "test_source_plasma_radial_expansion_uses_species_mass_chain"
                    ),
                    "-q",
                    read_only=read_only,
                ),
                env=env,
            ),
        ]
    if profile == "full":
        compile_gate = VerifyGate(
            "syntax" if read_only else "compileall",
            (
                _syntax_check_command(read_only=read_only)
                if read_only
                else _python_command("-m", "compileall", "-q", "gpu_stack", "tests")
            ),
            env=env,
        )
        return [
            VerifyGate("pytest", _pytest_command("-q", read_only=read_only), env=env),
            compile_gate,
            VerifyGate(
                "audit",
                _python_command(
                    "-m",
                    "gpu_stack.cli",
                    "audit",
                    "--fail-on-issues",
                    read_only=read_only,
                ),
                env=env,
            ),
            VerifyGate(
                "demo",
                _python_command("-m", "gpu_stack.demo", read_only=read_only),
                env=env,
            ),
        ]
    raise ValueError(f"unknown verify profile: {profile}")


def _run_verify_gate(
    gate: VerifyGate,
    cwd: Path,
    timeout_seconds: float | None,
) -> VerifyGateResult:
    try:
        result = subprocess.run(
            gate.command,
            cwd=cwd,
            env=({**os.environ, **gate.env} if gate.env else None),
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = _coerce_timeout_text(exc.stdout)
        stderr = _coerce_timeout_text(exc.stderr)
        timeout_text = _format_timeout(timeout_seconds)
        message = f"gate timed out after {timeout_text}"
        stderr = f"{stderr}\n{message}" if stderr else message
        return VerifyGateResult(
            returncode=VERIFY_TIMEOUT_RETURN_CODE,
            stdout=stdout,
            stderr=stderr,
            timed_out=True,
        )
    return VerifyGateResult(
        returncode=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
    )


def _coerce_timeout_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _format_timeout(timeout_seconds: float | None) -> str:
    if timeout_seconds is None:
        return "unbounded"
    if float(timeout_seconds).is_integer():
        return f"{int(timeout_seconds)}s"
    return f"{timeout_seconds:g}s"


def _gate_timeout(profile: str, override: float | None) -> float | None:
    if override is not None:
        if override <= 0:
            return None
        return override
    return DEFAULT_GATE_TIMEOUT_SECONDS[profile]


def _tail(text: str, max_lines: int) -> str:
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return "\n".join(lines)
    return "\n".join(lines[-max_lines:])


def _format_command(command: Sequence[str]) -> str:
    return " ".join(command)


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


def _print_unresolved_inputs(items, file: TextIO | None = None) -> None:
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


def cmd_verify(args: argparse.Namespace) -> int:
    gates = _verify_gates(args.profile, read_only=args.read_only)
    cwd = Path(args.cwd).resolve() if args.cwd else _repo_root()
    timeout_seconds = _gate_timeout(args.profile, args.gate_timeout)
    started = time.perf_counter()

    print(f"Verify profile: {args.profile}")
    print(f"Working directory: {cwd}")
    print(f"Gate timeout: {_format_timeout(timeout_seconds)}")
    print(f"Read-only mode: {'on' if args.read_only else 'off'}")
    passed = 0

    for gate in gates:
        gate_started = time.perf_counter()
        result = _run_verify_gate(gate, cwd, timeout_seconds)
        elapsed = time.perf_counter() - gate_started
        status = "OK" if result.returncode == 0 else "FAIL"
        if getattr(result, "timed_out", False):
            status = "TIMEOUT"
        print(f"{status:<4} {gate.name:<12} {elapsed:6.2f}s")
        if result.returncode != 0:
            print(f"command: {_format_command(gate.command)}")
            if result.stdout:
                print()
                print("stdout tail:")
                print(_tail(result.stdout, args.tail_lines))
            if result.stderr:
                print()
                print("stderr tail:")
                print(_tail(result.stderr, args.tail_lines))
            total = time.perf_counter() - started
            print()
            print(f"Summary: {passed}/{len(gates)} gates passed in {total:.2f}s")
            return result.returncode
        passed += 1

    total = time.perf_counter() - started
    print(f"Summary: {passed}/{len(gates)} gates passed in {total:.2f}s")
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

    try:
        result = resolve(args.target, assignments=assignments, variants=variants)
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
            print(
                f"  {step.variable} <- {step.equation} "
                f"({step.role.name}{'/' + step.variant if step.variant else ''}) "
                f"= {step.value}"
            )
    if args.missing and result.missing:
        print()
        print(f"missing: {sorted(result.missing)}")
        if result.unresolved_inputs:
            _print_unresolved_inputs(result.unresolved_inputs)
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
            _print_unresolved_inputs(result.unresolved_inputs)
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
        help="print the live top-impact, implementation, and bug-risk compass",
    )
    p_next_work.add_argument(
        "--json",
        action="store_true",
        help="emit the live next-work compass as structured JSON",
    )
    p_next_work.set_defaults(func=cmd_next_work)

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
    p_resolve.set_defaults(func=cmd_resolve)
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
