"""
tests/test_lithography_presets.py
=================================

A preset is a named bundle of root-input assignments plus provenance — the
citations and caveats that say where each number came from. The rule these
tests enforce is honesty: a preset may only assign roots that its cited
public sources actually state. The ASML EUV public-context preset knows six
public facts (13.5 nm wavelength, tin droplets, 25 micron diameter, 70 m/s
speed, dual-pulse sequence, 50 kHz repetition rate) but assigns exactly one
root — the pulse period, 1/50,000 s, derived from the repetition rate. The
other five stay "provenance-only" with an explicit withholding reason, and
uncalibrated plasma roots are never smuggled in. The tin-120 composition
preset (Z=50, N=70) is labeled an assumption, not an ASML claim, and this
module also checks the derived counts it implies and that combining the two
presets still assigns only root inputs.
"""

import pytest

from gpu_stack import Registry
from gpu_stack.presets import lithography


TIN120_SOURCE_ROOTS = {
    "physical.lithography.source_proton_count": 50,
    "physical.lithography.source_neutron_count": 70,
}

FORBIDDEN_UNCALIBRATED_ROOTS = {
    "physical.lithography.source_plasma_drive_pulse_fluence",
    "physical.lithography.source_plasma_species_partial_pressure",
    "physical.lithography.source_plasma_species_gas_temperature",
    "physical.lithography.source_plasma_drive_objective_pupil_radius",
    "physical.lithography.source_plasma_drive_objective_focal_length",
    "physical.lithography.source_plasma_drive_edge_detuning_ratio",
    "physical.lithography.source_plasma_drive_far_field_divergence_half_angle",
    "physical.lithography.source_plasma_drive_pupil_beam_fill_factor",
    "physical.lithography.source_plasma_electron_heating_fraction",
    "physical.lithography.source_plasma_free_electron_inventory_charge_fraction",
}


def test_asml_euv_tin_lpp_context_records_public_provenance_and_caveats():
    preset = lithography.asml_euv_tin_lpp_public_context
    source = preset.source or ""

    assert "ASML EUV lithography systems" in source
    assert "ASML Light and lasers" in source
    assert "13.5 nm" in source
    assert "CO2 laser" in source
    assert "tin" in source
    assert "50,000" in source
    assert "25 microns" in source
    assert "70 m/s" in source
    assert any("not as a per-tool calibration" in note for note in preset.notes)
    assert any("not assigned" in note for note in preset.notes)
    assert any("No drive fluence" in note for note in preset.notes)


def test_asml_euv_tin_lpp_context_assigns_only_the_sourced_period_root():
    preset = lithography.asml_euv_tin_lpp_public_context

    assert dict(preset.assignments) == {
        "physical.lithography.source_plasma_pulse_period": pytest.approx(
            1.0 / 50_000.0
        )
    }
    for name in preset.assignments:
        assert Registry.variables[name].is_root_input, name

    assert not FORBIDDEN_UNCALIBRATED_ROOTS & set(preset.assignments)
    assert "physical.lithography.exposure_wavelength" not in preset.assignments
    assert "physical.lithography.photon_energy" not in preset.assignments


def test_asml_public_context_inventory_maps_only_repetition_to_period_root():
    inventory = lithography.asml_euv_public_context_inventory()
    by_key = {row["key"]: row for row in inventory}

    assert set(by_key) == {
        "euv_wavelength_13p5_nm",
        "tin_droplets",
        "tin_droplet_diameter_25_micron",
        "tin_droplet_speed_70_m_per_s",
        "dual_pulse_sequence",
        "source_repetition_rate_50_khz",
    }

    assigned = [
        row for row in inventory if row["status"] == "assigned-root"
    ]
    assert assigned == [by_key["source_repetition_rate_50_khz"]]
    assert assigned[0]["public_value"] == lithography.ASML_EUV_REPETITION_RATE_HZ
    assert assigned[0]["public_units"] == "Hz"
    assert (
        assigned[0]["assigned_root"]
        == "physical.lithography.source_plasma_pulse_period"
    )
    assert assigned[0]["assigned_value"] == pytest.approx(
        lithography.ASML_EUV_PULSE_PERIOD_S
    )
    assert assigned[0]["assigned_in_preset"] is True

    assigned_roots = {
        row["assigned_root"] for row in inventory if row["assigned_root"]
    }
    assert assigned_roots == set(
        lithography.asml_euv_tin_lpp_public_context.assignments
    )


def test_asml_public_context_inventory_keeps_other_facts_provenance_only():
    preset = lithography.asml_euv_tin_lpp_public_context
    inventory = lithography.asml_euv_public_context_inventory()
    by_key = {row["key"]: row for row in inventory}
    provenance_only_keys = set(by_key) - {"source_repetition_rate_50_khz"}

    for key in provenance_only_keys:
        row = by_key[key]
        assert row["status"] == "provenance-only", key
        assert row["assigned_root"] is None, key
        assert row["assigned_value"] is None, key
        assert row["assigned_in_preset"] is False, key
        assert row["withholding_reason"], key

    assert by_key["euv_wavelength_13p5_nm"]["public_value"] == pytest.approx(
        13.5e-9
    )
    assert (
        by_key["euv_wavelength_13p5_nm"]["candidate_root"]
        == "physical.lithography.wavelength"
    )
    assert "physical.lithography.wavelength" not in preset.assignments

    assert by_key["tin_droplets"]["public_value"] == "tin"
    assert by_key["tin_droplet_diameter_25_micron"][
        "public_value"
    ] == pytest.approx(25e-6)
    assert by_key["tin_droplet_speed_70_m_per_s"][
        "public_value"
    ] == pytest.approx(70.0)
    assert by_key["dual_pulse_sequence"]["public_value"] == (
        "two-pulse sequence"
    )


def test_tin120_source_composition_is_marked_as_an_assumption():
    preset = lithography.source_tin_120_composition_assumption
    source = preset.source or ""

    assert dict(preset.assignments) == TIN120_SOURCE_ROOTS
    assert "NIST Atomic Data for Tin" in source
    assert "Atomic Number = 50" in source
    assert "120Sn" in source
    assert "not an ASML claim" in source
    assert any("does not say ASML uses" in note for note in preset.notes)
    for name in preset.assignments:
        assert Registry.variables[name].is_root_input, name


@pytest.mark.parametrize(
    ("target", "expected"),
    [
        ("physical.lithography.source_valence_up_quark_count", 170.0),
        ("physical.lithography.source_valence_down_quark_count", 190.0),
        ("physical.lithography.source_isotope_mass_number", 120.0),
    ],
)
def test_tin120_source_composition_resolves_derived_counts(target, expected):
    result = lithography.source_tin_120_composition_assumption.resolve(target)

    assert float(result.value) == pytest.approx(expected)
    assert result.missing == set()
    assert result.trace


def test_combined_euv_tin120_boundary_stays_root_only_and_resolves_frequency():
    preset = lithography.euv_tin120_lpp_source_boundary_assumption

    assert dict(preset.assignments) == {
        **TIN120_SOURCE_ROOTS,
        "physical.lithography.source_plasma_pulse_period": pytest.approx(
            lithography.ASML_EUV_PULSE_PERIOD_S
        ),
    }
    assert "assumption" in preset.name
    assert preset in lithography.SOURCE_PLASMA_OPERATING_PRESETS
    for name in preset.assignments:
        assert Registry.variables[name].is_root_input, name

    repetition = preset.resolve(
        "physical.lithography.source_plasma_pulse_repetition_rate"
    )

    assert float(repetition.value) == pytest.approx(
        lithography.ASML_EUV_REPETITION_RATE_HZ
    )
    assert repetition.missing == set()
    assert (
        "physical.eq.lithography_source_plasma_pulse_repetition_rate_from_period"
        in {step.equation for step in repetition.trace}
    )
    assert not FORBIDDEN_UNCALIBRATED_ROOTS & set(preset.assignments)
