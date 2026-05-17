"""CLI verify command tests."""

from types import SimpleNamespace

import gpu_stack.cli as cli_mod
from gpu_stack.cli import main
from tests.helpers.cli import captured_stdout


def test_verify_fast_prints_compact_gate_summary(monkeypatch):
    calls = []

    def fake_run(gate, cwd, timeout_seconds):
        calls.append((gate.name, cwd, gate.command, timeout_seconds))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(cli_mod, "_run_verify_gate", fake_run)
    with captured_stdout() as buf:
        rc = main(["verify", "--profile", "fast"])
    out = buf.getvalue()
    assert rc == 0
    assert "Verify profile: fast" in out
    assert "OK   audit" in out
    assert "OK   core-tests" in out
    assert "Summary: 2/2 gates passed" in out
    assert [name for name, _, _, _ in calls] == ["audit", "core-tests"]
    assert [timeout for *_, timeout in calls] == [120.0, 120.0]
    core_command = calls[1][2]
    assert "tests/test_relation_roles.py" in core_command
    assert "tests/test_symbolic_integrity.py" in core_command
    for resolver_test_file in (
        "tests/test_resolver.py",
        "tests/test_resolver_approximations.py",
        "tests/test_resolver_constraints.py",
        "tests/test_resolver_dependencies.py",
        "tests/test_resolver_iterative.py",
        "tests/test_resolver_relations.py",
    ):
        assert resolver_test_file in core_command
    for cli_test_file in (
        "tests/test_cli.py",
        "tests/test_cli_audit.py",
        "tests/test_cli_inventory.py",
        "tests/test_cli_resolve.py",
        "tests/test_cli_root_debt.py",
        "tests/test_cli_scenarios.py",
        "tests/test_cli_verify.py",
    ):
        assert cli_test_file in core_command
    assert (
        "tests/test_process_geometry.py::"
        "test_source_plasma_radial_expansion_uses_species_mass_chain"
    ) in core_command
    assert "Read-only mode: off" in out


def test_verify_read_only_uses_no_bytecode_and_no_pytest_cache(monkeypatch):
    calls = []

    def fake_run(gate, cwd, timeout_seconds):
        calls.append((gate.name, gate.command, gate.env))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(cli_mod, "_run_verify_gate", fake_run)
    with captured_stdout() as buf:
        rc = main(["verify", "--profile", "full", "--read-only"])
    out = buf.getvalue()

    assert rc == 0
    assert "Read-only mode: on" in out
    assert [name for name, _, _ in calls] == ["pytest", "syntax", "audit", "demo"]
    for _, command, env in calls:
        assert command[1] == "-B"
        assert env == {"PYTHONDONTWRITEBYTECODE": "1"}
    pytest_command = calls[0][1]
    assert "-p" in pytest_command
    assert "no:cacheprovider" in pytest_command
    assert "compileall" not in calls[1][1]
    assert "tokenize.open" in calls[1][1][-1]


def test_run_verify_gate_merges_gate_env(monkeypatch, tmp_path):
    captured = {}

    def fake_run(*args, **kwargs):
        captured["env"] = kwargs["env"]
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(cli_mod.subprocess, "run", fake_run)
    result = cli_mod._run_verify_gate(
        cli_mod.VerifyGate(
            "readonly",
            ("python", "-B", "-c", "pass"),
            env={"PYTHONDONTWRITEBYTECODE": "1"},
        ),
        tmp_path,
        1.0,
    )
    assert result.returncode == 0
    assert captured["env"]["PYTHONDONTWRITEBYTECODE"] == "1"


def test_verify_failure_prints_limited_tail(monkeypatch):
    def fake_run(gate, cwd, timeout_seconds):
        return SimpleNamespace(
            returncode=7,
            stdout="old\nnew\n",
            stderr="problem\n",
        )

    monkeypatch.setattr(cli_mod, "_run_verify_gate", fake_run)
    with captured_stdout() as buf:
        rc = main(["verify", "--profile", "fast", "--tail-lines", "1"])
    out = buf.getvalue()
    assert rc == 7
    assert "FAIL audit" in out
    assert "stdout tail:" in out
    assert "new" in out
    assert "old" not in out
    assert "stderr tail:" in out


def test_verify_timeout_prints_timeout_status(monkeypatch):
    def fake_run(gate, cwd, timeout_seconds):
        return SimpleNamespace(
            returncode=cli_mod.VERIFY_TIMEOUT_RETURN_CODE,
            stdout="partial stdout\n",
            stderr=f"gate timed out after {timeout_seconds:g}s\n",
            timed_out=True,
        )

    monkeypatch.setattr(cli_mod, "_run_verify_gate", fake_run)
    with captured_stdout() as buf:
        rc = main(["verify", "--profile", "fast", "--gate-timeout", "3"])
    out = buf.getvalue()
    assert rc == cli_mod.VERIFY_TIMEOUT_RETURN_CODE
    assert "Gate timeout: 3s" in out
    assert "TIMEOUT audit" in out
    assert "gate timed out after 3s" in out
    assert "Summary: 0/2 gates passed" in out


def test_verify_gate_timeout_override_applies_to_all_gates(monkeypatch):
    seen = []

    def fake_run(gate, cwd, timeout_seconds):
        seen.append(timeout_seconds)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(cli_mod, "_run_verify_gate", fake_run)
    with captured_stdout():
        rc = main(["verify", "--profile", "fast", "--gate-timeout", "12"])
    assert rc == 0
    assert seen == [12.0, 12.0]


def test_verify_gate_timeout_zero_disables_timeout(monkeypatch):
    seen = []

    def fake_run(gate, cwd, timeout_seconds):
        seen.append(timeout_seconds)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(cli_mod, "_run_verify_gate", fake_run)
    with captured_stdout() as buf:
        rc = main(["verify", "--profile", "fast", "--gate-timeout", "0"])
    assert rc == 0
    assert seen == [None, None]
    assert "Gate timeout: unbounded" in buf.getvalue()


def test_run_verify_gate_converts_subprocess_timeout(monkeypatch, tmp_path):
    def fake_run(*args, **kwargs):
        assert kwargs["timeout"] == 0.5
        raise cli_mod.subprocess.TimeoutExpired(
            cmd=args[0],
            timeout=0.5,
            output=b"partial out\n",
            stderr=b"partial err\n",
        )

    monkeypatch.setattr(cli_mod.subprocess, "run", fake_run)
    result = cli_mod._run_verify_gate(
        cli_mod.VerifyGate("slow", ("python", "-c", "pass")),
        tmp_path,
        0.5,
    )
    assert result.returncode == cli_mod.VERIFY_TIMEOUT_RETURN_CODE
    assert result.timed_out is True
    assert "partial out" in result.stdout
    assert "partial err" in result.stderr
    assert "gate timed out after 0.5s" in result.stderr
