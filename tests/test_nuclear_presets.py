"""
tests/test_nuclear_presets.py
=============================

Focused guardrails for SEMF calibration preset scaffolding.
"""

import pytest

from gpu_stack import Registry
from gpu_stack.constants import ELEMENTARY_CHARGE
from gpu_stack.core import Preset
from gpu_stack.core.units import JOULE
from gpu_stack.presets import nuclear


SEMF_TEST_ASSIGNMENTS = {
    name: float(index + 1)
    for index, name in enumerate(nuclear.SEMF_CALIBRATION_ROOTS)
}


def test_semf_calibration_inventory_is_metadata_only_and_root_scoped():
    inventory = nuclear.semf_calibration_root_inventory()

    assert tuple(row["name"] for row in inventory) == nuclear.SEMF_CALIBRATION_ROOTS
    for row in inventory:
        variable = Registry.variables[row["name"]]

        assert variable.is_root_input
        assert variable.sp_units == JOULE
        assert row["is_root_input"] is True
        assert row["units"] == "J"
        assert row["reference_count"] >= 1
        assert row["preset_value"] is None
        assert row["source_required"] is True


def test_nuclear_module_does_not_publish_semf_coefficient_defaults():
    exported_presets = [
        value for value in vars(nuclear).values() if isinstance(value, Preset)
    ]

    assert exported_presets == []


def test_mev_to_joule_uses_exact_si_elementary_charge():
    assert nuclear.MEV_TO_JOULE == pytest.approx(
        1_000_000.0 * ELEMENTARY_CHARGE.value
    )
    assert nuclear.mev_to_joule(1.0) == pytest.approx(nuclear.MEV_TO_JOULE)
    assert nuclear.mev_to_joule(15.5) == pytest.approx(15.5 * nuclear.MEV_TO_JOULE)
    assert "exact 2019 SI elementary charge" in nuclear.MEV_TO_JOULE_SOURCE


@pytest.mark.parametrize("bad_value", ["15.5 MeV", True, float("nan"), float("inf")])
def test_mev_to_joule_rejects_nonfinite_or_nonnumeric_inputs(bad_value):
    with pytest.raises(ValueError, match="finite real numbers"):
        nuclear.mev_to_joule(bad_value)


def test_pairing_gap_metadata_documents_pairing_coefficient_semantics():
    metadata = nuclear.semf_pairing_gap_reference_energy_semantics()

    assert metadata["root"] == nuclear.NUCLEAR_PAIRING_GAP_REFERENCE_ENERGY_ROOT
    assert metadata["root"] == "physical.lithography.nuclear_pairing_gap_reference_energy"
    assert metadata["units"] == "J"
    assert metadata["mev_to_joule"] == pytest.approx(nuclear.MEV_TO_JOULE)
    assert metadata["direct_pairing_coefficient_assignable"] is False
    assert metadata["pairing_coefficient_relation"] == (
        "a_pair = Delta_pair_ref * sqrt(A_ref)"
    )
    assert "reference mass number" in metadata["why_not_direct"]


def test_krane_style_pairing_coefficient_is_not_a_gap_assignment_default():
    metadata = nuclear.semf_pairing_gap_reference_energy_semantics()

    assert metadata["direct_pairing_coefficient_assignable"] is False
    assert "a_pair" in metadata["why_not_direct"]
    assert "Delta_pair_ref" in metadata["why_not_direct"]
    assert "reference mass number" in metadata["why_not_direct"]


def test_semf_calibration_preset_requires_source_text():
    with pytest.raises(ValueError, match="requires non-blank source text"):
        nuclear.semf_calibration_preset(
            name="unsafe_semf",
            description="missing provenance",
            assignments={
                "physical.lithography.nuclear_binding_volume_coefficient": 1.0
            },
            source_text="  ",
        )


@pytest.mark.parametrize(
    ("field", "overrides", "match"),
    [
        ("name", {"name": "  "}, "requires non-blank name"),
        ("description", {"description": "  "}, "requires non-blank description"),
    ],
)
def test_semf_calibration_preset_requires_named_text_fields(field, overrides, match):
    kwargs = {
        "name": "paper_table_semf",
        "description": "Sourced SEMF fixture.",
        "assignments": {
            "physical.lithography.nuclear_binding_volume_coefficient": 1.0
        },
        "source_text": "Unit-test source text.",
    }
    kwargs.update(overrides)

    with pytest.raises(ValueError, match=match):
        nuclear.semf_calibration_preset(**kwargs)


@pytest.mark.parametrize("bad_notes", [("  ",), ("ok", ""), ("ok", object()), "ok"])
def test_semf_calibration_preset_rejects_blank_or_nonstr_notes(bad_notes):
    with pytest.raises(ValueError, match="notes must be non-blank strings"):
        nuclear.semf_calibration_preset(
            name="paper_table_semf",
            description="Sourced SEMF fixture.",
            assignments={
                "physical.lithography.nuclear_binding_volume_coefficient": 1.0
            },
            source_text="Unit-test source text.",
            notes=bad_notes,
        )


def test_semf_calibration_preset_requires_at_least_one_assignment():
    with pytest.raises(ValueError, match="requires at least one assignment"):
        nuclear.semf_calibration_preset(
            name="empty_semf",
            description="source exists but no values were copied",
            assignments={},
            source_text="Unit-test source text.",
        )


def test_semf_calibration_preset_accepts_sourced_root_assignments():
    preset = nuclear.semf_calibration_preset(
        name="paper_table_semf_partial",
        description="Partial SEMF coefficient table copied from a cited source.",
        assignments={
            "physical.lithography.nuclear_binding_volume_coefficient": 1.0,
            "physical.lithography.nuclear_binding_coulomb_coefficient": 2.0,
        },
        source_text=(
            "Example unit-test source text: cited SEMF coefficient table, "
            "values already converted to joules."
        ),
        notes=("Unit-test fixture only; not exported as a module preset.",),
    )

    assert preset.require_source() is preset
    assert dict(preset.assignments) == {
        "physical.lithography.nuclear_binding_volume_coefficient": 1.0,
        "physical.lithography.nuclear_binding_coulomb_coefficient": 2.0,
    }
    for name in preset.assignments:
        assert name in nuclear.SEMF_CALIBRATION_ROOTS
        assert Registry.variables[name].is_root_input
    assert "does not publish coefficient defaults" in preset.notes[0]


def test_semf_calibration_preset_accepts_caller_converted_mev_values():
    value_joule = nuclear.mev_to_joule(15.5)

    preset = nuclear.semf_calibration_preset(
        name="paper_table_semf_mev_converted",
        description="SEMF coefficient copied from a cited MeV table.",
        assignments={
            "physical.lithography.nuclear_binding_volume_coefficient": value_joule
        },
        source_text=(
            "Example unit-test source text: cited coefficient table quotes "
            "15.5 MeV, caller converted to joules with nuclear.mev_to_joule."
        ),
        notes=("  Unit-test conversion only; no default coefficient table.  ",),
    )

    assert dict(preset.assignments) == {
        "physical.lithography.nuclear_binding_volume_coefficient": pytest.approx(
            value_joule
        )
    }
    assert preset.notes[1] == "Unit-test conversion only; no default coefficient table."


def test_semf_calibration_preset_strips_name_description_source_and_notes():
    preset = nuclear.semf_calibration_preset(
        name="  paper_table_semf_trimmed  ",
        description="  Sourced SEMF fixture.  ",
        assignments={
            "physical.lithography.nuclear_binding_volume_coefficient": 1.0
        },
        source_text="  Unit-test source text.  ",
        notes=("  Trimmed note.  ",),
    )

    assert preset.name == "paper_table_semf_trimmed"
    assert preset.description == "Sourced SEMF fixture."
    assert preset.source == "Unit-test source text."
    assert preset.notes[1] == "Trimmed note."


def test_semf_calibration_preset_keeps_one_source_for_all_assignments():
    source_text = (
        "  Example source: cited coefficient table, values converted to SI "
        "joules before constructing the preset.  "
    )

    preset = nuclear.semf_calibration_preset(
        name="paper_table_semf_all_roots",
        description="Complete SEMF fixture with caller-provided SI values.",
        assignments=SEMF_TEST_ASSIGNMENTS,
        source_text=source_text,
    )

    assert dict(preset.assignments) == SEMF_TEST_ASSIGNMENTS
    assert preset.source == source_text.strip()
    assert preset.source_summary() == {
        "name": "paper_table_semf_all_roots",
        "has_source": True,
        "source": source_text.strip(),
        "assignment_count": len(SEMF_TEST_ASSIGNMENTS),
        "variant_count": 0,
        "note_count": 1,
    }
    assignment_sources = {name: preset.source for name in preset.assignments}
    assert set(assignment_sources) == set(nuclear.SEMF_CALIBRATION_ROOTS)
    assert all(source == source_text.strip() for source in assignment_sources.values())


def test_semf_calibration_preset_rejects_unknown_variable_names():
    with pytest.raises(ValueError, match="unknown variables"):
        nuclear.semf_calibration_preset(
            name="bad_semf",
            description="typo",
            assignments={
                "physical.lithography.nuclear_binding_volume_coefficent": 1.0
            },
            source_text="source text",
        )


@pytest.mark.parametrize(
    "name",
    [
        "physical.lithography.source_binding_volume_coefficient",
        "physical.lithography.source_binding_coulomb_coefficient",
        "physical.lithography.medium_component_binding_volume_coefficient",
        "physical.lithography.medium_component_nuclear_pairing_gap_reference_energy",
    ],
)
def test_semf_calibration_preset_rejects_nonroot_semf_aliases(name):
    assert name in Registry.variables
    assert Registry.variables[name].is_root_input is False

    with pytest.raises(ValueError, match="SEMF calibration roots only"):
        nuclear.semf_calibration_preset(
            name="bad_semf",
            description="derived SEMF aliases are not calibration roots",
            assignments={name: 1.0},
            source_text="source text",
        )


def test_semf_calibration_preset_rejects_non_semf_assignments():
    with pytest.raises(ValueError, match="SEMF calibration roots only"):
        nuclear.semf_calibration_preset(
            name="bad_semf",
            description="wrong root family",
            assignments={"cluster.rack.n_nodes": 9},
            source_text="source text",
        )


@pytest.mark.parametrize("bad_value", ["15.5 MeV", True, object()])
def test_semf_calibration_preset_rejects_nonnumeric_values(bad_value):
    with pytest.raises(ValueError, match="numeric SI joule values"):
        nuclear.semf_calibration_preset(
            name="bad_semf",
            description="wrong value type",
            assignments={
                "physical.lithography.nuclear_binding_volume_coefficient": bad_value
            },
            source_text="source text",
        )


@pytest.mark.parametrize("bad_value", [float("nan"), float("inf")])
def test_semf_calibration_preset_rejects_nonfinite_numeric_values(bad_value):
    with pytest.raises(ValueError, match="finite SI joule values"):
        nuclear.semf_calibration_preset(
            name="bad_semf",
            description="nonfinite value",
            assignments={
                "physical.lithography.nuclear_binding_volume_coefficient": bad_value
            },
            source_text="source text",
        )
