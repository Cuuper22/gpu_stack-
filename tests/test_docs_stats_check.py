"""
tests/test_docs_stats_check.py
================================

Tests for the docs-stats freshness gate.

Three scenarios:
  1. Gate passes on the current tree (numbers are correct).
  2. Gate fails with a precise message when one number is perturbed in a
     fixture copy (using tmp_path copies, not the real files).
  3. Parser robustness: label moves within line, extra whitespace.
"""

from __future__ import annotations

import shutil
import textwrap
from pathlib import Path

import pytest

import gpu_stack
from gpu_stack import Registry
from gpu_stack.docs_stats_check import (
    StatMismatch,
    _parse_appjs_facts,
    _parse_html_stat_grid,
    _parse_readme_snapshot_table,
    _parse_readme_stats_block,
    check_docs_stats,
    run_docs_stats_gate,
)
from gpu_stack.cli_common import _repo_root


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _repo() -> Path:
    return _repo_root()


def _copy_repo_docs(tmp_path: Path) -> Path:
    """
    Copy README.md and the docs/ directory into tmp_path, returning tmp_path
    as the fake repo root.
    """
    src = _repo()
    shutil.copy(src / "README.md", tmp_path / "README.md")
    shutil.copy(src / "pyproject.toml", tmp_path / "pyproject.toml")
    docs_dst = tmp_path / "docs"
    docs_dst.mkdir()
    shutil.copy(src / "docs" / "index.html", docs_dst / "index.html")
    shutil.copy(src / "docs" / "app.js", docs_dst / "app.js")
    return tmp_path


def _live_variables() -> int:
    return Registry.stats()["variables"]


def _live_equations() -> int:
    return Registry.stats()["equations"]


def _live_root_inputs() -> int:
    return Registry.stats()["root_inputs"]


def _live_unit_checks() -> int:
    return Registry.coverage()["equations_with_unit_check"]


# ---------------------------------------------------------------------------
# Gate passes on the real tree
# ---------------------------------------------------------------------------

def test_gate_passes_on_real_tree():
    mismatches = check_docs_stats(_repo())
    assert mismatches == [], (
        f"docs-stats gate unexpectedly failed on the live tree:\n"
        + "\n".join(f"  {m}" for m in mismatches)
    )


def test_run_docs_stats_gate_returns_zero_on_real_tree(capsys):
    rc = run_docs_stats_gate(_repo())
    out = capsys.readouterr().out
    assert rc == 0, f"gate returned nonzero; output:\n{out}"
    assert "OK" in out


# ---------------------------------------------------------------------------
# Gate fails when README snapshot table value is perturbed
# ---------------------------------------------------------------------------

def test_gate_fails_on_perturbed_readme_snapshot_table(tmp_path):
    fake_root = _copy_repo_docs(tmp_path)
    readme_path = fake_root / "README.md"
    original = readme_path.read_text(encoding="utf-8")

    live_variables = _live_variables()
    wrong_variables = live_variables + 1

    # Replace "| Variables | 1517 |" (or whatever live value) with wrong value
    perturbed = original.replace(
        f"| Variables | {live_variables} |",
        f"| Variables | {wrong_variables} |",
    )
    assert perturbed != original, "replacement did not change the file"
    readme_path.write_text(perturbed, encoding="utf-8")

    mismatches = check_docs_stats(fake_root)
    claim_ids = [m.claim_id for m in mismatches]
    assert any("Variables" in cid for cid in claim_ids), (
        f"expected mismatch for Variables in snapshot table; got: {claim_ids}"
    )
    # The mismatch must name the expected (live) value and the found (wrong) value
    variables_mm = next(m for m in mismatches if "Variables" in m.claim_id)
    assert variables_mm.expected == str(live_variables), (
        f"mismatch.expected should be live value {live_variables}; "
        f"got {variables_mm.expected!r}"
    )
    assert variables_mm.found == str(wrong_variables), (
        f"mismatch.found should be perturbed value {wrong_variables}; "
        f"got {variables_mm.found!r}"
    )


# ---------------------------------------------------------------------------
# Gate fails when README stats code block value is perturbed
# ---------------------------------------------------------------------------

def test_gate_fails_on_perturbed_readme_stats_block(tmp_path):
    fake_root = _copy_repo_docs(tmp_path)
    readme_path = fake_root / "README.md"
    original = readme_path.read_text(encoding="utf-8")

    live_roots = _live_root_inputs()
    wrong_roots = live_roots - 3

    # Stats block uses "  root_inputs    619" format (unique key in the block)
    perturbed = original.replace(
        f"  root_inputs    {live_roots}",
        f"  root_inputs    {wrong_roots}",
    )
    assert perturbed != original, "replacement did not change the file"
    readme_path.write_text(perturbed, encoding="utf-8")

    mismatches = check_docs_stats(fake_root)
    claim_ids = [m.claim_id for m in mismatches]
    assert any("stats_block:root_inputs" in cid for cid in claim_ids), (
        f"expected stats_block:root_inputs mismatch; got: {claim_ids}"
    )
    mm = next(m for m in mismatches if "stats_block:root_inputs" in m.claim_id)
    assert mm.expected == str(live_roots)
    assert mm.found == str(wrong_roots)


# ---------------------------------------------------------------------------
# Gate fails when docs/index.html stat-grid value is perturbed
# ---------------------------------------------------------------------------

def test_gate_fails_on_perturbed_html_stat_grid(tmp_path):
    fake_root = _copy_repo_docs(tmp_path)
    html_path = fake_root / "docs" / "index.html"
    original = html_path.read_text(encoding="utf-8")

    live_roots = _live_root_inputs()
    wrong_roots = live_roots + 7

    perturbed = original.replace(
        f"<b>{live_roots}</b><span>root inputs",
        f"<b>{wrong_roots}</b><span>root inputs",
    )
    assert perturbed != original, "replacement did not change the file"
    html_path.write_text(perturbed, encoding="utf-8")

    mismatches = check_docs_stats(fake_root)
    claim_ids = [m.claim_id for m in mismatches]
    assert any("root inputs" in cid for cid in claim_ids), (
        f"expected root_inputs mismatch in html stat grid; got: {claim_ids}"
    )
    mm = next(m for m in mismatches if "root inputs" in m.claim_id)
    assert mm.expected == str(live_roots)
    assert mm.found == str(wrong_roots)


# ---------------------------------------------------------------------------
# Gate fails when docs/app.js fact string value is perturbed
# ---------------------------------------------------------------------------

def test_gate_fails_on_perturbed_appjs_fact(tmp_path):
    fake_root = _copy_repo_docs(tmp_path)
    appjs_path = fake_root / "docs" / "app.js"
    original = appjs_path.read_text(encoding="utf-8")

    live_unit_checks = _live_unit_checks()
    wrong_unit_checks = live_unit_checks + 42

    perturbed = original.replace(
        f'"{live_unit_checks} equations are currently covered by unit checks.',
        f'"{wrong_unit_checks} equations are currently covered by unit checks.',
    )
    assert perturbed != original, "replacement did not change the file"
    appjs_path.write_text(perturbed, encoding="utf-8")

    mismatches = check_docs_stats(fake_root)
    claim_ids = [m.claim_id for m in mismatches]
    assert any("appjs:fact_unit_checks" in cid for cid in claim_ids), (
        f"expected appjs:fact_unit_checks mismatch; got: {claim_ids}"
    )
    mm = next(m for m in mismatches if "appjs:fact_unit_checks" in m.claim_id)
    assert mm.expected == str(live_unit_checks)
    assert mm.found == str(wrong_unit_checks)


# ---------------------------------------------------------------------------
# Parser robustness: extra whitespace in stats block
# ---------------------------------------------------------------------------

def test_readme_stats_block_tolerates_extra_whitespace():
    live_variables = _live_variables()
    # Extra spaces between key and value -- still must parse
    text = textwrap.dedent(f"""\
        ```text
        Registry stats:
          systems           16
          variables         {live_variables}
          constants         24
        ```
    """)
    result = _parse_readme_stats_block(text)
    assert result.get("variables") == live_variables


def test_readme_stats_block_ignores_lines_outside_fence():
    live_variables = _live_variables()
    text = textwrap.dedent(f"""\
        variables         {live_variables}
        ```text
          variables         {live_variables}
        ```
        variables         999
    """)
    result = _parse_readme_stats_block(text)
    # Only the inside-fence value is returned
    assert result.get("variables") == live_variables


# ---------------------------------------------------------------------------
# Parser robustness: snapshot table with different spacing
# ---------------------------------------------------------------------------

def test_readme_snapshot_table_tolerates_extra_spaces():
    live_eqs = _live_equations()
    # Extra spaces in the table cells
    text = textwrap.dedent(f"""\
        ## Current Snapshot

        |  Signal  |  Value  |
        |---|---:|
        |  Equations  |  {live_eqs}  |
    """)
    result = _parse_readme_snapshot_table(text)
    assert result.get("Equations") == str(live_eqs)


def test_readme_snapshot_table_stops_at_next_heading():
    live_eqs = _live_equations()
    text = textwrap.dedent(f"""\
        ## Current Snapshot

        | Equations | {live_eqs} |

        ## Other Section

        | Equations | 0 |
    """)
    result = _parse_readme_snapshot_table(text)
    # Only picks up the row before the next heading
    assert result.get("Equations") == str(live_eqs)


# ---------------------------------------------------------------------------
# Parser unit tests: HTML stat grid
# ---------------------------------------------------------------------------

def test_parse_html_stat_grid_extracts_all_four_stats():
    live_vars = _live_variables()
    live_eqs = _live_equations()
    live_roots = _live_root_inputs()
    live_unit = _live_unit_checks()
    html = textwrap.dedent(f"""\
        <div class="stat"><b>{live_vars}</b><span>registered variables</span></div>
        <div class="stat"><b>{live_eqs}</b><span>equations connecting them</span></div>
        <div class="stat"><b>{live_roots}</b><span>root inputs, named instead of hidden</span></div>
        <div class="stat"><b>{live_unit}</b><span>equations with unit checks</span></div>
    """)
    result = _parse_html_stat_grid(html)
    assert result["variables"] == live_vars
    assert result["equations"] == live_eqs
    assert result["root_inputs"] == live_roots
    assert result["equations_with_unit_check"] == live_unit


# ---------------------------------------------------------------------------
# Parser unit tests: app.js fact strings
# ---------------------------------------------------------------------------

def test_parse_appjs_facts_extracts_known_strings():
    live_vars = _live_variables()
    live_eqs = _live_equations()
    live_roots = _live_root_inputs()
    live_unit = _live_unit_checks()
    appjs = textwrap.dedent(f"""\
        "The registry currently names {live_vars} variables and {live_eqs} equations.",
        "{live_unit} equations are currently covered by unit checks.",
        "{live_roots} root inputs are still visible in the current summary.",
    """)
    result = _parse_appjs_facts(appjs)
    assert result["variables"] == live_vars
    assert result["equations"] == live_eqs
    assert result["equations_with_unit_check"] == live_unit
    assert result["root_inputs"] == live_roots


# ---------------------------------------------------------------------------
# run_docs_stats_gate exit-code contract
# ---------------------------------------------------------------------------

def test_run_docs_stats_gate_nonzero_on_drift(tmp_path, capsys):
    fake_root = _copy_repo_docs(tmp_path)
    readme_path = fake_root / "README.md"
    original = readme_path.read_text(encoding="utf-8")

    live_vars = _live_variables()
    perturbed = original.replace(
        f"| Variables | {live_vars} |",
        f"| Variables | {live_vars + 1} |",
    )
    assert perturbed != original
    readme_path.write_text(perturbed, encoding="utf-8")

    rc = run_docs_stats_gate(fake_root)
    out = capsys.readouterr().out
    assert rc != 0, "gate should return nonzero on drift"
    assert "mismatch" in out.lower() or "Variables" in out


# ---------------------------------------------------------------------------
# StatMismatch __str__ format
# ---------------------------------------------------------------------------

def test_stat_mismatch_str():
    mm = StatMismatch(
        file="README.md",
        claim_id="snapshot_table:Variables",
        expected="1517",
        found="1518",
    )
    text = str(mm)
    assert "README.md" in text
    assert "snapshot_table:Variables" in text
    assert "1517" in text
    assert "1518" in text
