"""
tests/test_materials_preset_provenance.py
=========================================

The H2O preset describes water as two hydrogen-1 atoms (Z=1, N=0) and one
oxygen-16 atom (Z=8, N=8) — and it may assign only those six composition
roots, because that is all its cited sources (NIST Chemistry WebBook,
IUPAC/CIAAW nuclide notation) actually state. This module checks the
preset's source string names those references and isotopes, that its notes
say the formula-unit counts are derived from Z and N rather than assigned,
and that no derived name (formula-unit totals, mass density, number
density, resonance) sneaks into the assignments. It then resolves the
formula-unit counts through the graph and confirms the physics does the
counting: 10 protons, 8 neutrons, 10 electrons per H2O unit, each arriving
with a nonempty derivation trace.
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
