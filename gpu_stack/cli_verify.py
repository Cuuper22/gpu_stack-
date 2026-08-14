"""The `verify` subcommand of the gpu_stack CLI.

Runs a fixed sequence of verification gates — each a subprocess such as the
graph audit, pytest, a compile/syntax pass, or the demo — and stops at the
first failure, printing the failed gate's command and output tail. The
`fast` profile covers the audit plus core tests; `full` adds the whole
pytest suite, compilation, the demo, and the docs-stats freshness check.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from gpu_stack.cli_common import _repo_root


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


VERIFY_TIMEOUT_RETURN_CODE = 124
DEFAULT_GATE_TIMEOUT_SECONDS = {
    "fast": 120.0,
    "full": 300.0,
}


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
                    "tests/test_import_physical_exports.py",
                    "tests/test_import_registry.py",
                    "tests/test_graph_health.py",
                    "tests/test_units.py",
                    "tests/test_memory_units.py",
                    "tests/test_relation_roles.py",
                    "tests/test_symbolic_integrity.py",
                    "tests/test_resolver.py",
                    "tests/test_resolver_approximations.py",
                    "tests/test_resolver_constraints.py",
                    "tests/test_resolver_dependencies.py",
                    "tests/test_resolver_iterative.py",
                    "tests/test_resolver_relations.py",
                    "tests/test_cli.py",
                    "tests/test_cli_audit.py",
                    "tests/test_cli_inventory.py",
                    "tests/test_cli_resolve.py",
                    "tests/test_cli_root_debt.py",
                    "tests/test_cli_scenarios.py",
                    "tests/test_cli_verify.py",
                    "tests/test_next_work.py",
                    "tests/test_next_work_continuation_contract.py",
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
            VerifyGate(
                "docs-stats",
                _python_command(
                    "-m",
                    "gpu_stack.docs_stats_check",
                    read_only=read_only,
                ),
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


def cmd_verify(args: argparse.Namespace, *, run_gate=None) -> int:
    if run_gate is None:
        run_gate = _run_verify_gate
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
        result = run_gate(gate, cwd, timeout_seconds)
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
