"""
tests/test_root_debt_cli.py
===========================

Focused checks for the root-debt CLI table. These keep the highest-impact
root list machine-parseable and provide a small family grouping helper for
making physical root-debt progress easier to inspect.
"""

from __future__ import annotations

import contextlib
import io
import json
from collections import Counter
from dataclasses import dataclass

from gpu_stack.cli import main


@dataclass(frozen=True)
class RootDebtRow:
    dependents: int
    scope: str
    variable: str
    units: str


@dataclass(frozen=True)
class RootDebtFamilyRow:
    total_weight: int
    root_count: int
    family: str
    boundary_category: str
    primitive_boundary: str
    top_roots: str


_PHYSICAL_FAMILY_PREFIXES = (
    "physical.lithography.source_plasma_drive",
    "physical.lithography.source_plasma",
    "physical.lithography.medium_component",
    "physical.lithography.medium_formula_unit",
    "physical.lithography.medium_intercomponent",
    "physical.lithography.nuclear_binding",
    "physical.lithography.gate_k1",
    "physical.lithography.source",
    "physical.lithography.medium",
)


def _run_root_debt(*args: str) -> str:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = main(["root-debt", *args])
    assert rc == 0
    return buf.getvalue()


def _parse_root_debt_rows(output: str) -> list[RootDebtRow]:
    rows: list[RootDebtRow] = []
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped or not stripped[0].isdigit():
            continue
        parts = stripped.split(maxsplit=3)
        assert len(parts) == 4, f"unparseable root-debt row: {line!r}"
        count, scope, variable, units = parts
        rows.append(RootDebtRow(int(count), scope, variable, units))
    return rows


def _parse_root_debt_family_rows(output: str) -> list[RootDebtFamilyRow]:
    rows: list[RootDebtFamilyRow] = []
    in_table = False
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith("total_weight"):
            in_table = True
            continue
        if not in_table or not stripped or not stripped[0].isdigit():
            continue
        parts = stripped.split(maxsplit=5)
        assert len(parts) == 6, f"unparseable root-debt family row: {line!r}"
        total_weight, root_count, family, category, primitive, top_roots = parts
        rows.append(
            RootDebtFamilyRow(
                int(total_weight),
                int(root_count),
                family,
                category,
                primitive,
                top_roots,
            )
        )
    return rows


def _root_debt_family(variable: str) -> str:
    for prefix in _PHYSICAL_FAMILY_PREFIXES:
        if variable.startswith(prefix):
            return prefix

    namespace, _, local_name = variable.rpartition(".")
    if not namespace:
        return variable
    family_tokens = local_name.split("_")[:2]
    return f"{namespace}.{'_'.join(family_tokens)}"


def _group_by_family(rows: list[RootDebtRow]) -> Counter[str]:
    grouped: Counter[str] = Counter()
    for row in rows:
        grouped[_root_debt_family(row.variable)] += row.dependents
    return grouped


def test_physical_root_debt_output_is_parseable_and_groupable():
    output = _run_root_debt("--scope", "physical", "--limit", "20")

    rows = _parse_root_debt_rows(output)
    assert len(rows) == 20
    assert all(row.scope == "physical" for row in rows)
    assert all(row.variable.startswith("physical.") for row in rows)
    assert all(row.units for row in rows)
    assert [row.dependents for row in rows] == sorted(
        (row.dependents for row in rows),
        reverse=True,
    )

    grouped = _group_by_family(rows)
    assert grouped
    assert sum(grouped.values()) == sum(row.dependents for row in rows)
    assert all(family.startswith("physical.") for family in grouped)


def test_physical_root_debt_top_rows_expose_source_frontier():
    output = _run_root_debt("--scope", "physical", "--limit", "10")

    rows = _parse_root_debt_rows(output)
    variables = [row.variable for row in rows]
    assert any(".source_valence_" in variable for variable in variables[:5])
    assert any(
        variable.startswith("physical.lithography.source_plasma")
        for variable in variables
    )


def test_physical_root_debt_limit_is_deterministic_prefix():
    limit_5_a = _parse_root_debt_rows(
        _run_root_debt("--scope", "physical", "--limit", "5")
    )
    limit_5_b_output = _run_root_debt("--scope", "physical", "--limit", "5")
    limit_5_b = _parse_root_debt_rows(limit_5_b_output)
    limit_20 = _parse_root_debt_rows(
        _run_root_debt("--scope", "physical", "--limit", "20")
    )

    assert "shown              5" in limit_5_b_output
    assert limit_5_a == limit_5_b
    assert limit_5_a == limit_20[:5]


def test_physical_root_debt_json_output_is_parseable():
    output = _run_root_debt("--scope", "physical", "--limit", "5", "--json")
    repeated_output = _run_root_debt("--scope", "physical", "--limit", "5", "--json")

    payload = json.loads(output)
    assert json.loads(repeated_output) == payload
    assert "Root-debt ranking:" not in output
    assert set(payload) == {
        "total_roots",
        "filtered_scope",
        "include_constraints",
        "shown",
        "rows",
    }
    assert payload["filtered_scope"] == "physical"
    assert payload["include_constraints"] is False
    assert payload["shown"] == 5

    rows = payload["rows"]
    assert len(rows) == 5
    assert all(
        set(row) == {
            "dependents",
            "scope",
            "variable",
            "units",
            "family",
            "boundary_category",
            "primitive_boundary",
        }
        for row in rows
    )
    assert all(row["scope"] == "physical" for row in rows)
    assert all(row["variable"].startswith("physical.") for row in rows)
    assert all(row["boundary_category"] == "primitive-root" for row in rows)
    assert all(row["primitive_boundary"] is True for row in rows)
    assert [row["dependents"] for row in rows] == sorted(
        (row["dependents"] for row in rows),
        reverse=True,
    )


def test_physical_root_debt_families_group_ranked_rows():
    output = _run_root_debt("--scope", "physical", "--families", "--limit", "10")

    rows = _parse_root_debt_family_rows(output)
    assert len(rows) == 10
    assert "Root-debt family ranking:" in output
    assert "filtered_scope     physical" in output
    assert "grouped_roots" in output
    assert "family_count" in output
    assert "dependents  scope" not in output
    assert all(row.family.startswith("physical.") for row in rows)
    assert all(row.boundary_category == "primitive-root" for row in rows)
    assert all(row.primitive_boundary == "True" for row in rows)
    assert [
        (row.total_weight, row.root_count, row.family)
        for row in rows
    ] == sorted(
        ((row.total_weight, row.root_count, row.family) for row in rows),
        key=lambda item: (-item[0], -item[1], item[2]),
    )

    source_valence = next(
        row for row in rows
        if row.family == "physical.lithography.source_valence"
    )
    assert source_valence.root_count == 2
    assert "source_valence_down_quark_count" in source_valence.top_roots
    assert "source_valence_up_quark_count" in source_valence.top_roots

    assert any(
        row.family == "physical.lithography.source_plasma_drive"
        and row.root_count > 1
        and "source_plasma_drive" in row.top_roots
        for row in rows
    )


def test_economics_root_debt_families_use_public_prefixes_deterministically():
    limit_5_output = _run_root_debt(
        "--scope", "economics", "--families", "--limit", "5"
    )
    repeated_output = _run_root_debt(
        "--scope", "economics", "--families", "--limit", "5"
    )
    limit_10_output = _run_root_debt(
        "--scope", "economics", "--families", "--limit", "10"
    )

    limit_5 = _parse_root_debt_family_rows(limit_5_output)
    repeated = _parse_root_debt_family_rows(repeated_output)
    limit_10 = _parse_root_debt_family_rows(limit_10_output)

    assert "filtered_scope     economics" in limit_5_output
    assert "shown              5" in limit_5_output
    assert limit_5 == repeated
    assert limit_5 == limit_10[:5]
    assert all(row.family.startswith("econ.") for row in limit_10)
    assert "economics.econ" not in limit_10_output
    assert any(row.family == "econ.node" and row.root_count > 1 for row in limit_10)
    assert any(row.family == "econ.facility" for row in limit_10)
    assert all(row.boundary_category == "primitive-root" for row in limit_10)
    assert all(row.primitive_boundary == "True" for row in limit_10)
    assert all(":" in row.top_roots for row in limit_10)


def test_physical_root_debt_families_json_output_is_parseable():
    output = _run_root_debt(
        "--scope", "physical", "--families", "--limit", "5", "--json"
    )
    repeated_output = _run_root_debt(
        "--scope", "physical", "--families", "--limit", "5", "--json"
    )

    payload = json.loads(output)
    assert json.loads(repeated_output) == payload
    assert "Root-debt family ranking:" not in output
    assert set(payload) == {
        "total_roots",
        "filtered_scope",
        "include_constraints",
        "grouped_roots",
        "family_count",
        "shown",
        "families",
    }
    assert payload["filtered_scope"] == "physical"
    assert payload["include_constraints"] is False
    assert payload["grouped_roots"] > 0
    assert payload["family_count"] >= 5
    assert payload["shown"] == 5

    families = payload["families"]
    assert len(families) == 5
    assert all(
        set(family) == {
            "total_weight",
            "root_count",
            "family",
            "boundary_category",
            "primitive_boundary",
            "top_roots",
        }
        for family in families
    )
    assert [
        (family["total_weight"], family["root_count"], family["family"])
        for family in families
    ] == sorted(
        (
            (family["total_weight"], family["root_count"], family["family"])
            for family in families
        ),
        key=lambda item: (-item[0], -item[1], item[2]),
    )
    assert all(family["family"].startswith("physical.") for family in families)
    assert all(family["boundary_category"] == "primitive-root" for family in families)
    assert all(family["primitive_boundary"] is True for family in families)
    assert all(1 <= len(family["top_roots"]) <= 4 for family in families)
    assert all(
        set(root) == {"variable", "dependents"}
        for family in families
        for root in family["top_roots"]
    )


def test_root_debt_family_groups_known_physical_clusters():
    assert (
        _root_debt_family(
            "physical.lithography.source_plasma_drive_objective_pupil_radius"
        )
        == "physical.lithography.source_plasma_drive"
    )
    assert (
        _root_debt_family(
            "physical.lithography.medium_component_a_valence_up_quark_count"
        )
        == "physical.lithography.medium_component"
    )
    assert (
        _root_debt_family(
            "physical.lithography.nuclear_binding_coulomb_coefficient"
        )
        == "physical.lithography.nuclear_binding"
    )
