"""
docs_stats_check.py
====================

Freshness gate: parse numeric claims in README.md, docs/index.html, and
docs/app.js, then compare them against live registry values.  Every claim
is anchored to a specific label so cosmetic rewording does not cause false
positives, but numeric drift fails loudly.

Claim IDs and their sources:

  README "stats code block" (lines like "  variables      1517")
  README "Current Snapshot" table (markdown table rows)
  docs/index.html stat-grid <b>NNN</b> cells
  docs/app.js embedded fact strings with numeric literals

The checker reports each mismatch as:
  [file:claim_id] expected <live_value>, found <doc_value>

Exit code is nonzero when any mismatch is found.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Live truth
# ---------------------------------------------------------------------------

def _live_stats(repo_root: Optional[Path] = None) -> Dict[str, int]:
    """Return registry stats, coverage, and derived audit numbers."""
    import gpu_stack
    from gpu_stack import Registry, find_cycles, topological_sort
    from importlib.metadata import version as _pkg_version

    stats = Registry.stats()
    coverage = Registry.coverage()
    cycles = find_cycles()
    topo = topological_sort()

    # Hard audit failures: collapsed equations + raw-symbol equations
    import sympy as sp
    collapsed = sum(
        1 for e in Registry.equations.values()
        if e.as_sympy() in (sp.S.true, sp.S.false)
    )
    raw_symbols = sum(
        1 for e in Registry.equations.values()
        if e.raw_dependency_symbols()
    )
    hard_failures = (len(cycles) if isinstance(cycles, list) else int(cycles)) + collapsed + raw_symbols

    # Root-debt families
    from gpu_stack.core.resolver import _boundary_family
    from gpu_stack.cli_root_debt import _root_debt_families, RootDebtEntry
    roots = Registry.roots()
    rows = []
    for root in roots:
        rows.append(
            RootDebtEntry(
                dependents=len(root.dependents(include_constraints=False)),
                name=root.name,
                units=root.units,
                scope=root.scope,
                family=_boundary_family(root),
                boundary_category="primitive-root",
                primitive_boundary=root.is_root_input,
            )
        )
    rows.sort(key=lambda r: (-r.dependents, r.name))
    family_rows = _root_debt_families(rows)

    # The checked source tree is authoritative. Editable-install metadata can
    # legitimately lag pyproject.toml until the environment is reinstalled.
    pkg_version = None
    pyproject_path = None if repo_root is None else repo_root / "pyproject.toml"
    if pyproject_path is not None and pyproject_path.is_file():
        project_text = pyproject_path.read_text(encoding="utf-8")
        project_block = re.search(
            r"(?ms)^\[project\]\s*$.*?(?=^\[|\Z)",
            project_text,
        )
        if project_block is not None:
            version_match = re.search(
                r'(?m)^version\s*=\s*"([^"]+)"\s*$',
                project_block.group(0),
            )
            if version_match is not None:
                pkg_version = version_match.group(1)
    if pkg_version is None:
        try:
            pkg_version = _pkg_version("gpu_stack")
        except Exception:
            pkg_version = "unknown"

    return {
        # Registry stats
        "systems": stats["systems"],
        "variables": stats["variables"],
        "constants": stats["constants"],
        "equations": stats["equations"],
        "root_inputs": stats["root_inputs"],
        "leaves": stats["leaves"],
        # Coverage
        "non_constant_variables": coverage["non_constant_variables"],
        "with_sp_units": coverage["with_sp_units"],
        "with_references": coverage["with_references"],
        "equations_with_references": coverage["equations_with_references"],
        "equations_with_unit_check": coverage["equations_with_unit_check"],
        # Derived
        "cycles": len(cycles) if isinstance(cycles, list) else int(cycles),
        "topological_order_length": len(topo),
        "hard_audit_failures": hard_failures,
        "root_debt_families": len(family_rows),
        # Version (stored as string, but we keep it separate)
        "_pkg_version": pkg_version,
    }


# ---------------------------------------------------------------------------
# Mismatch record
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StatMismatch:
    file: str
    claim_id: str
    expected: str
    found: str

    def __str__(self) -> str:
        return (
            f"[{self.file}:{self.claim_id}] "
            f"expected {self.expected!r}, found {self.found!r}"
        )


# ---------------------------------------------------------------------------
# README stats code block parser
# ("  key      value" indented lines inside the ```text block)
# ---------------------------------------------------------------------------

_README_STATS_BLOCK_KEYS = {
    "systems":        "systems",
    "variables":      "variables",
    "constants":      "constants",
    "equations":      "equations",
    "root_inputs":    "root_inputs",
    "leaves":         "leaves",
    "non_constant_variables":         "non_constant_variables",
    "with_sp_units":                  "with_sp_units",
    "with_references":                "with_references",
    "equations_with_references":      "equations_with_references",
    "equations_with_unit_check":      "equations_with_unit_check",
}

# Pattern: leading spaces, key, spaces, integer value
_STATS_LINE_RE = re.compile(r"^\s+(\w+)\s+(\d+)\s*$")


def _parse_readme_stats_block(text: str) -> Dict[str, int]:
    """
    Extract key->value pairs from the README stats/coverage code block.

    We look for lines of the form "  key   NNN" between ```text fences.
    Returns only the keys listed in _README_STATS_BLOCK_KEYS.
    """
    found: Dict[str, int] = {}
    in_block = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```text"):
            in_block = True
            continue
        if in_block and stripped.startswith("```"):
            in_block = False
            continue
        if not in_block:
            continue
        m = _STATS_LINE_RE.match(line)
        if m:
            key = m.group(1)
            if key in _README_STATS_BLOCK_KEYS:
                found[key] = int(m.group(2))
    return found


# ---------------------------------------------------------------------------
# README "Current Snapshot" table parser
# ---------------------------------------------------------------------------

# Map from table row label to live-stats key (or special sentinel "_version")
_README_TABLE_LABELS: Dict[str, str] = {
    "Systems":                                    "systems",
    "Variables":                                  "variables",
    "Constants":                                  "constants",
    "Equations":                                  "equations",
    "Root inputs":                                "root_inputs",
    "Leaves":                                     "leaves",
    "Cycles":                                     "cycles",
    "Topological order length":                   "topological_order_length",
    "Hard audit failures":                        "hard_audit_failures",
    "Non-constant variables with `sp_units`":     "with_sp_units",
    "Non-constant variables with references":     "with_references",
    "Equations with references":                  "equations_with_references",
    "Equations with unit checks":                 "equations_with_unit_check",
    "Root-debt families":                         "root_debt_families",
    "Package version":                            "_version",
}

# Markdown table row: | Label | Value |
# Value is either an integer or a version string like 0.23.0
_TABLE_ROW_RE = re.compile(r"^\|\s*(.+?)\s*\|\s*([^\|]+?)\s*\|")


def _parse_readme_snapshot_table(text: str) -> Dict[str, str]:
    """
    Extract label->raw_value from the "Current Snapshot" markdown table.

    Returns a dict where keys are the label strings from _README_TABLE_LABELS
    and values are the raw cell strings (e.g. "1517" or "0.23.0").
    """
    found: Dict[str, str] = {}
    in_section = False
    for line in text.splitlines():
        if "## Current Snapshot" in line:
            in_section = True
            continue
        # Stop at the next ## heading
        if in_section and line.startswith("## "):
            break
        if not in_section:
            continue
        m = _TABLE_ROW_RE.match(line)
        if not m:
            continue
        label = m.group(1).strip()
        value = m.group(2).strip()
        if label in _README_TABLE_LABELS:
            found[label] = value
    return found


# ---------------------------------------------------------------------------
# docs/index.html stat-grid parser
# ---------------------------------------------------------------------------

# Stat grid cells look like:  <div class="stat"><b>1517</b><span>...</span></div>
_STAT_GRID_CELL_RE = re.compile(
    r'<div class="stat">\s*<b>(\d+)</b>\s*<span>([^<]+)</span>'
)

# Map label text fragment -> live-stats key
_HTML_STAT_LABELS: Dict[str, str] = {
    "registered variables":          "variables",
    "equations connecting them":     "equations",
    "root inputs":                   "root_inputs",
    "equations with unit checks":    "equations_with_unit_check",
}


def _parse_html_stat_grid(text: str) -> Dict[str, int]:
    """
    Extract stat-grid cell values from docs/index.html.

    Returns a dict keyed by the label fragment.
    """
    found: Dict[str, int] = {}
    for m in _STAT_GRID_CELL_RE.finditer(text):
        value = int(m.group(1))
        label = m.group(2).strip()
        for fragment, key in _HTML_STAT_LABELS.items():
            if fragment in label:
                found[key] = value
    return found


# ---------------------------------------------------------------------------
# docs/app.js fact string parser
# ---------------------------------------------------------------------------

# The three fact strings we track:
#   "The registry currently names 1517 variables and 959 equations."
#   "799 equations are currently covered by unit checks."
#   "619 root inputs are still visible in the current summary."

_APPJS_PATTERNS: List[Tuple[str, re.Pattern, str]] = [
    (
        "appjs:fact_variables_and_equations",
        re.compile(
            r"The registry currently names\s+(\d+)\s+variables and\s+(\d+)\s+equations"
        ),
        "variables,equations",
    ),
    (
        "appjs:fact_unit_checks",
        re.compile(r"(\d+)\s+equations are currently covered by unit checks"),
        "equations_with_unit_check",
    ),
    (
        "appjs:fact_root_inputs",
        re.compile(r"(\d+)\s+root inputs are still visible in the current summary"),
        "root_inputs",
    ),
]


def _parse_appjs_facts(text: str) -> Dict[str, int]:
    """
    Extract numeric literals from the known fact strings in docs/app.js.
    """
    found: Dict[str, int] = {}
    for claim_id, pattern, keys in _APPJS_PATTERNS:
        m = pattern.search(text)
        if m is None:
            continue
        key_list = keys.split(",")
        for i, key in enumerate(key_list):
            found[key] = int(m.group(i + 1))
    return found


# ---------------------------------------------------------------------------
# Main checker
# ---------------------------------------------------------------------------

def check_docs_stats(repo_root: Path) -> List[StatMismatch]:
    """
    Compute live registry truth, parse all claim surfaces, return mismatches.

    Never raises on missing values from documents; instead records a mismatch
    with found="<not found>".
    """
    live = _live_stats(repo_root)
    mismatches: List[StatMismatch] = []

    readme_path = repo_root / "README.md"
    html_path = repo_root / "docs" / "index.html"
    appjs_path = repo_root / "docs" / "app.js"

    readme_text = readme_path.read_text(encoding="utf-8")
    html_text = html_path.read_text(encoding="utf-8")
    appjs_text = appjs_path.read_text(encoding="utf-8")

    # -- README stats code block --
    readme_block = _parse_readme_stats_block(readme_text)
    for key, stats_key in _README_STATS_BLOCK_KEYS.items():
        expected = live[stats_key]
        found_val = readme_block.get(key)
        if found_val is None:
            mismatches.append(StatMismatch(
                file="README.md",
                claim_id=f"stats_block:{key}",
                expected=str(expected),
                found="<not found>",
            ))
        elif found_val != expected:
            mismatches.append(StatMismatch(
                file="README.md",
                claim_id=f"stats_block:{key}",
                expected=str(expected),
                found=str(found_val),
            ))

    # -- README Current Snapshot table --
    readme_table = _parse_readme_snapshot_table(readme_text)
    for label, stats_key in _README_TABLE_LABELS.items():
        found_raw = readme_table.get(label)
        if stats_key == "_version":
            expected_str = live["_pkg_version"]
        else:
            expected_str = str(live[stats_key])
        if found_raw is None:
            mismatches.append(StatMismatch(
                file="README.md",
                claim_id=f"snapshot_table:{label}",
                expected=expected_str,
                found="<not found>",
            ))
        elif found_raw != expected_str:
            mismatches.append(StatMismatch(
                file="README.md",
                claim_id=f"snapshot_table:{label}",
                expected=expected_str,
                found=found_raw,
            ))

    # -- docs/index.html stat grid --
    html_stats = _parse_html_stat_grid(html_text)
    for key, stats_key in _HTML_STAT_LABELS.items():
        expected = live[stats_key]
        found_val = html_stats.get(stats_key)
        if found_val is None:
            mismatches.append(StatMismatch(
                file="docs/index.html",
                claim_id=f"stat_grid:{key}",
                expected=str(expected),
                found="<not found>",
            ))
        elif found_val != expected:
            mismatches.append(StatMismatch(
                file="docs/index.html",
                claim_id=f"stat_grid:{key}",
                expected=str(expected),
                found=str(found_val),
            ))

    # -- docs/app.js fact strings --
    appjs_vals = _parse_appjs_facts(appjs_text)

    def _check_appjs(stats_key: str, claim_id: str) -> None:
        expected = live[stats_key]
        found_val = appjs_vals.get(stats_key)
        if found_val is None:
            mismatches.append(StatMismatch(
                file="docs/app.js",
                claim_id=claim_id,
                expected=str(expected),
                found="<not found>",
            ))
        elif found_val != expected:
            mismatches.append(StatMismatch(
                file="docs/app.js",
                claim_id=claim_id,
                expected=str(expected),
                found=str(found_val),
            ))

    _check_appjs("variables", "appjs:fact_variables_and_equations:variables")
    _check_appjs("equations", "appjs:fact_variables_and_equations:equations")
    _check_appjs("equations_with_unit_check", "appjs:fact_unit_checks")
    _check_appjs("root_inputs", "appjs:fact_root_inputs")

    return mismatches


def run_docs_stats_gate(repo_root: Path) -> int:
    """
    Entry point for the docs-stats gate.

    Prints OK or a list of mismatches.  Returns 0 on success, 1 on failure.
    """
    mismatches = check_docs_stats(repo_root)
    if not mismatches:
        print("docs-stats: OK")
        return 0
    print(f"docs-stats: {len(mismatches)} mismatch(es) found")
    for mm in mismatches:
        print(f"  {mm}")
    return 1


def main(argv: Optional[List[str]] = None) -> int:
    """Stand-alone entry point."""
    import argparse
    from gpu_stack.cli_common import _repo_root

    parser = argparse.ArgumentParser(
        prog="docs-stats-check",
        description="Check that README.md and docs/ stats match live registry values.",
    )
    parser.add_argument(
        "--repo-root",
        help="path to the repository root; defaults to auto-detected repo root",
    )
    args = parser.parse_args(argv)
    root = Path(args.repo_root).resolve() if args.repo_root else _repo_root()
    return run_docs_stats_gate(root)


if __name__ == "__main__":
    sys.exit(main())
