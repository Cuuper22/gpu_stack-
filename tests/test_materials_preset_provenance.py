"""
tests/test_materials_preset_provenance.py
=========================================

Focused provenance and strict-assignment coverage for material presets.
"""

import pytest

from gpu_stack import Registry
from gpu_stack.presets import materials


H2O_H1_O16_ASSIGNMENTS = {
    "physical.lithography.medium_component_a_stoichiometric_count": 2,
    "physical.lithography.medium_component_a_proton_count": 1,
    "physical.lithography.medium_component_a_neutron_count": 0,
    "physical.lithography.medium_component_b_stoichiometric_count": 1,
    "physical.lithography.medium_component_b_proton_count": 8,
    "physical.lithography.medium_component_b_neutron_count": 8,
}


def test_h2o_medium_preset_records_material_provenance():
    preset = materials.medium_h2o_h1_o16_composition
    source = preset.source or ""

    assert "NIST Chemistry WebBook" in source
    assert "IUPAC/CIAAW" in source
    assert "H2O" in source
    assert "hydrogen-1" in source
    assert "oxygen-16" in source
    assert "(Z=1, N=0)" in source
    assert "(Z=8, N=8)" in source
    assert any("Formula-unit proton, neutron, electron" in note for note in preset.notes)
    assert any(
        "derived from Z and N" in note for note in preset.notes
    )


def test_h2o_medium_preset_assigns_only_sourced_root_values():
    preset = materials.medium_h2o_h1_o16_composition

    assert dict(preset.assignments) == H2O_H1_O16_ASSIGNMENTS
    for name in preset.assignments:
        assert Registry.variables[name].is_root_input, name
        assert "medium_formula_unit" not in name
        assert "medium_mass_density" not in name
        assert "medium_number_density" not in name
        assert "medium_resonance" not in name


@pytest.mark.parametrize(
    ("target", "expected"),
    [
        ("physical.lithography.medium_formula_unit_proton_count", 10.0),
        ("physical.lithography.medium_formula_unit_neutron_count", 8.0),
        ("physical.lithography.medium_formula_unit_electron_count", 10.0),
    ],
)
def test_h2o_formula_unit_counts_remain_derived(target, expected):
    preset = materials.medium_h2o_h1_o16_composition

    assert target not in preset.assignments
    result = preset.resolve(target)

    assert float(result.value) == pytest.approx(expected)
    assert result.trace
