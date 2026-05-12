"""
Focused provenance helpers for the core Preset framework.
"""

import pytest

import gpu_stack
from gpu_stack.core import Preset


def test_preset_has_source_tracks_nonblank_provenance():
    assert "cluster.rack.n_nodes" in gpu_stack.Registry.variables

    sourced = Preset(
        name="sourced",
        description="auditable preset",
        assignments={"cluster.rack.n_nodes": 9},
        source="vendor datasheet",
    )
    unsourced = Preset(
        name="unsourced",
        description="scratch preset",
        assignments={"cluster.rack.n_nodes": 9},
    )
    blank = Preset(
        name="blank",
        description="blank provenance",
        assignments={"cluster.rack.n_nodes": 9},
        source="  ",
    )

    assert sourced.has_source()
    assert not unsourced.has_source()
    assert not blank.has_source()


def test_preset_require_source_returns_self_or_raises():
    sourced = Preset(
        name="sourced",
        description="auditable preset",
        assignments={"cluster.rack.n_nodes": 9},
        source="vendor datasheet",
    )
    unsourced = Preset(
        name="unsourced",
        description="scratch preset",
        assignments={"cluster.rack.n_nodes": 9},
    )

    assert sourced.require_source() is sourced
    with pytest.raises(ValueError, match="preset 'unsourced' has no source"):
        unsourced.require_source()


def test_preset_source_summary_reports_provenance_counts():
    preset = Preset(
        name="audit",
        description="auditable preset",
        assignments={"cluster.rack.n_nodes": 9},
        variants={"training.flops_per_step": "dense"},
        source="  vendor datasheet  ",
        notes=("calibrated for demo rack",),
    )

    assert preset.source_summary() == {
        "name": "audit",
        "has_source": True,
        "source": "vendor datasheet",
        "assignment_count": 1,
        "variant_count": 1,
        "note_count": 1,
    }


def test_preset_source_summary_marks_missing_source():
    preset = Preset(
        name="scratch",
        description="scratch preset",
        assignments={"cluster.rack.n_nodes": 9},
    )

    assert preset.source_summary() == {
        "name": "scratch",
        "has_source": False,
        "source": None,
        "assignment_count": 1,
        "variant_count": 0,
        "note_count": 0,
    }
