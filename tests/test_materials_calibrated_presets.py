"""
tests/test_materials_calibrated_presets.py
==========================================

Focused guardrails for sourced material preset expansion.
"""

import pytest

from gpu_stack import Registry
from gpu_stack.presets import materials


EXPECTED_COMPOSITION_ASSIGNMENTS = (
    (
        materials.source_hydrogen_1,
        {
            "physical.lithography.source_valence_up_quark_count": 2,
            "physical.lithography.source_valence_down_quark_count": 1,
        },
    ),
    (
        materials.source_oxygen_16,
        {
            "physical.lithography.source_valence_up_quark_count": 24,
            "physical.lithography.source_valence_down_quark_count": 24,
        },
    ),
    (
        materials.source_tin_120,
        {
            "physical.lithography.source_valence_up_quark_count": 170,
            "physical.lithography.source_valence_down_quark_count": 190,
        },
    ),
    (
        materials.medium_h2o_h1_o16_composition,
        {
            "physical.lithography.medium_component_a_stoichiometric_count": 2,
            "physical.lithography.medium_component_a_valence_up_quark_count": 2,
            "physical.lithography.medium_component_a_valence_down_quark_count": 1,
            "physical.lithography.medium_component_b_stoichiometric_count": 1,
            "physical.lithography.medium_component_b_valence_up_quark_count": 24,
            "physical.lithography.medium_component_b_valence_down_quark_count": 24,
        },
    ),
)


EXPECTED_COMPOSITION_SOURCE_TOKENS = (
    (
        materials.source_hydrogen_1,
        (
            "References:",
            "IUPAC/CIAAW nuclide notation",
            "For hydrogen-1: Z=1, A=1, N=0.",
            "Valence-quark accounting",
            "IUPAC Gold Book, nuclide",
            "https://goldbook.iupac.org/terms/view/N04257",
            "Particle Data Group Review of Particle Physics",
            "https://pdg.lbl.gov/",
        ),
    ),
    (
        materials.source_oxygen_16,
        (
            "References:",
            "IUPAC/CIAAW nuclide notation",
            "For oxygen-16: Z=8, A=16, N=8.",
            "Valence-quark accounting",
            "IUPAC Gold Book, nuclide",
            "https://goldbook.iupac.org/terms/view/N04257",
            "Particle Data Group Review of Particle Physics",
            "https://pdg.lbl.gov/",
        ),
    ),
    (
        materials.source_tin_120,
        (
            "References:",
            "ASML establishes molten tin droplets",
            "tin as Z=50",
            "tin-120 A=120 and N=70",
            "Valence-quark accounting",
            "ASML Light & lasers lithography principles",
            "https://www.asml.com/en/technology/lithography-principles/light-and-lasers",
            "CIAAW Atomic Weight of Tin",
            "https://www.ciaaw.org/tin.htm",
            "tin-120 isotopic abundance 0.3258(9)",
            "Particle Data Group Review of Particle Physics",
            "https://pdg.lbl.gov/",
        ),
    ),
    (
        materials.medium_h2o_h1_o16_composition,
        (
            "References:",
            "NIST Chemistry WebBook water entry",
            "water has molecular formula H2O",
            "component A=hydrogen-1",
            "component B=oxygen-16",
            "stoichiometric counts 2:1",
            "Valence-quark accounting",
            "NIST Chemistry WebBook, SRD 69, Water",
            "https://webbook.nist.gov/cgi/cbook.cgi?ID=C7732185",
            "IUPAC Gold Book, nuclide",
            "https://goldbook.iupac.org/terms/view/N04257",
            "Particle Data Group Review of Particle Physics",
            "https://pdg.lbl.gov/",
        ),
    ),
)


COMPOSITION_PRESETS = tuple(
    preset for preset, _expected in EXPECTED_COMPOSITION_ASSIGNMENTS
)


FORBIDDEN_COMPOSITION_ASSIGNMENT_TOKENS = (
    "density",
    "binding",
    "plasma",
    "drive",
    "optical",
    "response",
)


def test_material_preset_sources_include_structured_reference_metadata():
    preset = materials.medium_h2o_h1_o16_composition
    source = preset.source or ""

    assert "References:" in source
    assert "NIST Chemistry WebBook, SRD 69, Water" in source
    assert "https://webbook.nist.gov/cgi/cbook.cgi?ID=C7732185" in source
    assert "IUPAC Gold Book, nuclide" in source
    assert "https://goldbook.iupac.org/terms/view/N04257" in source
    assert "Particle Data Group Review of Particle Physics" in source
    assert "https://pdg.lbl.gov/" in source


def test_source_tin_120_source_uses_official_euv_and_isotope_references():
    preset = materials.source_tin_120
    source = preset.source or ""

    assert "References:" in source
    assert "ASML Light & lasers lithography principles" in source
    assert "https://www.asml.com/en/technology/lithography-principles/light-and-lasers" in source
    assert "CIAAW Atomic Weight of Tin" in source
    assert "https://www.ciaaw.org/tin.htm" in source
    assert "tin-120 isotopic abundance 0.3258(9)" in source
    assert "Particle Data Group Review of Particle Physics" in source


@pytest.mark.parametrize(
    "preset,expected_assignments",
    EXPECTED_COMPOSITION_ASSIGNMENTS,
)
def test_material_composition_presets_keep_exact_root_only_assignments(
    preset,
    expected_assignments,
):
    assert preset.source
    assert preset.assignments == expected_assignments

    for name in preset.assignments:
        assert Registry.variables[name].is_root_input, name


@pytest.mark.parametrize(
    "preset,expected_source_tokens",
    EXPECTED_COMPOSITION_SOURCE_TOKENS,
)
def test_material_composition_presets_keep_expected_provenance_tokens(
    preset,
    expected_source_tokens,
):
    source = preset.source or ""

    for token in expected_source_tokens:
        assert token in source


@pytest.mark.parametrize(
    "preset",
    COMPOSITION_PRESETS,
)
def test_material_composition_presets_do_not_assign_noncomposition_roots(
    preset,
):
    forbidden = {
        name
        for name in preset.assignments
        if any(
            token in name
            for token in FORBIDDEN_COMPOSITION_ASSIGNMENT_TOKENS
        )
    }

    assert forbidden == set()


def test_calibrated_density_table_value_is_not_added_as_derived_assignment():
    preset = materials.medium_h2o_h1_o16_composition

    assert "physical.lithography.medium_mass_density" not in preset.assignments
    assert not Registry.variables[
        "physical.lithography.medium_mass_density"
    ].is_root_input

    with pytest.raises(ValueError, match="root inputs only"):
        materials._root_assignments(
            {"physical.lithography.medium_mass_density": 997.04702}
        )


def test_material_provenance_requires_at_least_one_reference():
    with pytest.raises(ValueError, match="requires references"):
        materials._provenance("unsafe unsourced material statement", references=())
