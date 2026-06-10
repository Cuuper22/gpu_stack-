"""Tests for the export-graph-json CLI subcommand."""

from __future__ import annotations

import json

import pytest

from gpu_stack.cli import build_parser, main
from gpu_stack.cli_export_graph import DEFAULT_TARGETS, build_export_payload
from tests.helpers.cli import captured_stdout


# ---------------------------------------------------------------------------
# Subcommand wiring
# ---------------------------------------------------------------------------


def test_parser_includes_export_graph_json():
    """The build_parser result must include export-graph-json."""
    parser = build_parser()
    choices = parser._subparsers._actions[-1].choices  # type: ignore[attr-defined]
    assert "export-graph-json" in choices


def test_export_graph_subcommand_runs_and_exits_zero():
    """export-graph-json exits 0 and produces JSON output."""
    with captured_stdout() as buf:
        rc = main(["export-graph-json"])
    assert rc == 0
    data = json.loads(buf.getvalue())
    assert data["version"] == 1


# ---------------------------------------------------------------------------
# JSON schema shape
# ---------------------------------------------------------------------------


def test_payload_has_required_top_level_keys():
    payload = build_export_payload(DEFAULT_TARGETS)
    for key in ("version", "generated_at", "targets", "nodes", "edges"):
        assert key in payload, f"missing key: {key!r}"


def test_payload_version_is_one():
    payload = build_export_payload(DEFAULT_TARGETS)
    assert payload["version"] == 1


def test_payload_targets_sorted():
    payload = build_export_payload(DEFAULT_TARGETS)
    assert payload["targets"] == sorted(payload["targets"])


def test_payload_contains_default_targets_as_keys():
    payload = build_export_payload(DEFAULT_TARGETS)
    for t in DEFAULT_TARGETS:
        assert t in payload["nodes"], f"target node missing: {t!r}"


def test_node_has_required_fields():
    payload = build_export_payload(DEFAULT_TARGETS)
    required = {"name", "units", "scope", "description", "is_root_input",
                "is_constant", "defining_equations"}
    for node in payload["nodes"].values():
        missing = required - node.keys()
        assert not missing, f"node {node['name']!r} missing fields: {missing}"


def test_node_is_root_input_false_for_targets():
    payload = build_export_payload(DEFAULT_TARGETS)
    for t in DEFAULT_TARGETS:
        node = payload["nodes"][t]
        assert not node["is_root_input"], f"{t} should not be a root input"


def test_node_descriptions_bounded():
    """Descriptions must not exceed DESC_LIMIT characters."""
    from gpu_stack.cli_export_graph import DESC_LIMIT
    payload = build_export_payload(DEFAULT_TARGETS)
    for node in payload["nodes"].values():
        assert len(node["description"]) <= DESC_LIMIT + 3, (  # +3 for "..."
            f"description too long for {node['name']!r}"
        )


def test_edges_have_from_and_to():
    payload = build_export_payload(DEFAULT_TARGETS)
    for edge in payload["edges"]:
        assert "from" in edge and "to" in edge


def test_edges_reference_known_nodes():
    payload = build_export_payload(DEFAULT_TARGETS)
    node_names = set(payload["nodes"].keys())
    for edge in payload["edges"]:
        assert edge["from"] in node_names, f"unknown source: {edge['from']!r}"
        assert edge["to"] in node_names, f"unknown target: {edge['to']!r}"


def test_nodes_dict_keys_sorted():
    payload = build_export_payload(DEFAULT_TARGETS)
    keys = list(payload["nodes"].keys())
    assert keys == sorted(keys), "nodes dict keys must be sorted"


def test_edges_list_sorted():
    payload = build_export_payload(DEFAULT_TARGETS)
    edges = payload["edges"]
    keys = [(e["from"], e["to"]) for e in edges]
    assert keys == sorted(keys), "edges must be sorted by (from, to)"


def test_roots_present_in_nodes():
    """Root input nodes must appear; constants must be marked is_constant."""
    payload = build_export_payload(DEFAULT_TARGETS)
    roots = [n for n in payload["nodes"].values() if n["is_root_input"]]
    assert len(roots) > 0, "expected some root input nodes in the cone"
    consts = [n for n in payload["nodes"].values() if n["is_constant"]]
    assert len(consts) > 0, "expected some constant nodes in the cone"


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_payload_is_deterministic():
    """Two successive builds must produce identical nodes and edges."""
    p1 = build_export_payload(DEFAULT_TARGETS)
    p2 = build_export_payload(DEFAULT_TARGETS)
    assert p1["nodes"] == p2["nodes"]
    assert p1["edges"] == p2["edges"]
    assert p1["targets"] == p2["targets"]


def test_json_serialisation_deterministic():
    """JSON serialisation of two payloads must be identical (sans timestamp)."""
    p1 = build_export_payload(DEFAULT_TARGETS)
    p2 = build_export_payload(DEFAULT_TARGETS)
    # Blank the timestamp then compare.
    p1["generated_at"] = ""
    p2["generated_at"] = ""
    assert json.dumps(p1, indent=2) == json.dumps(p2, indent=2)


# ---------------------------------------------------------------------------
# Bounds
# ---------------------------------------------------------------------------


def test_payload_size_under_500kb():
    """Serialised JSON must stay comfortably under 500 KB."""
    payload = build_export_payload(DEFAULT_TARGETS)
    size = len(json.dumps(payload).encode("utf-8"))
    assert size < 500 * 1024, f"payload too large: {size / 1024:.1f} KB"


def test_node_count_non_trivial():
    """The combined cone must have a meaningful number of nodes."""
    payload = build_export_payload(DEFAULT_TARGETS)
    assert len(payload["nodes"]) > 100


# ---------------------------------------------------------------------------
# File output mode
# ---------------------------------------------------------------------------


def test_output_to_file(tmp_path):
    out = tmp_path / "cone.json"
    rc = main(["export-graph-json", "--output", str(out)])
    assert rc == 0
    assert out.exists()
    data = json.loads(out.read_text())
    assert data["version"] == 1
    assert len(data["nodes"]) > 0


# ---------------------------------------------------------------------------
# Custom targets
# ---------------------------------------------------------------------------


def test_single_custom_target():
    payload = build_export_payload(["econ.cost.per_token"])
    assert "econ.cost.per_token" in payload["nodes"]
    # Only the selected target's cone -- not the full default set.
    assert len(payload["nodes"]) < len(build_export_payload(DEFAULT_TARGETS)["nodes"])


def test_unknown_target_raises_key_error():
    with pytest.raises(KeyError):
        build_export_payload(["nonexistent.fake.variable"])
