"""Lithography source quantum numeric closure coverage."""

import pytest

from gpu_stack import Registry, resolve
from gpu_stack.core import RelationRole
from tests.helpers.lithography import source_quark_assignments
from tests.helpers.lithography_source_quantum import source_quantum_numeric_case


def test_lithography_source_quantum_numeric_chain_resolves_binding_terms():
    case = source_quantum_numeric_case()

    radius_coeff_result = resolve(
        "physical.lithography.source_nuclear_radius_coefficient",
        assignments={
            "physical.lithography.nuclear_binding_coulomb_coefficient": case.test_coulomb_coeff,
        },
    )
    assert float(radius_coeff_result.value) == pytest.approx(case.test_radius_coeff)

    saturation_density_result = resolve(
        "physical.lithography.source_nuclear_saturation_number_density",
        assignments={
            "physical.lithography.nuclear_binding_coulomb_coefficient": case.test_coulomb_coeff,
        },
    )
    assert float(saturation_density_result.value) == pytest.approx(case.test_saturation_density)

    bulk_binding_density_result = resolve(
        "physical.lithography.source_nuclear_bulk_binding_energy_density",
        assignments={
            "physical.lithography.nuclear_binding_coulomb_coefficient": case.test_coulomb_coeff,
            "physical.lithography.nuclear_binding_volume_coefficient": case.test_volume_coeff,
        },
    )
    assert float(bulk_binding_density_result.value) == pytest.approx(case.test_bulk_binding_density)

    surface_tension_result = resolve(
        "physical.lithography.source_nuclear_surface_tension",
        assignments={
            "physical.lithography.nuclear_binding_coulomb_coefficient": case.test_coulomb_coeff,
            "physical.lithography.nuclear_binding_surface_coefficient": case.test_surface_coeff,
        },
    )
    assert float(surface_tension_result.value) == pytest.approx(case.test_surface_tension)

    symmetry_density_result = resolve(
        "physical.lithography.source_nuclear_symmetry_energy_density",
        assignments={
            "physical.lithography.nuclear_binding_coulomb_coefficient": case.test_coulomb_coeff,
            "physical.lithography.nuclear_binding_asymmetry_coefficient": case.test_asymmetry_coeff,
        },
    )
    assert float(symmetry_density_result.value) == pytest.approx(case.test_symmetry_density)

    pairing_ref_result = resolve(
        "physical.lithography.source_pairing_reference_mass_number",
        assignments=source_quark_assignments(8, 8),
    )
    assert float(pairing_ref_result.value) == pytest.approx(16.0)
    pairing_ref_trace = [step.equation for step in pairing_ref_result.trace]
    assert set(pairing_ref_trace[:2]) == {
        "physical.eq.lithography_source_neutron_count_from_valence_quarks",
        "physical.eq.lithography_source_proton_count_from_valence_quarks",
    }
    assert pairing_ref_trace[2:] == [
        "physical.eq.lithography_source_isotope_mass_number",
        "physical.eq.lithography_source_mass_number",
        "physical.eq.lithography_source_pairing_reference_mass_number",
    ]

    pairing_coeff_result = resolve(
        "physical.lithography.source_binding_pairing_coefficient",
        assignments={
            **source_quark_assignments(8, 8),
            "physical.lithography.nuclear_pairing_gap_reference_energy": case.test_pairing_gap_ref,
        },
    )
    assert float(pairing_coeff_result.value) == pytest.approx(4.0)
    assert "physical.eq.lithography_source_pairing_reference_mass_number" in {
        step.equation for step in pairing_coeff_result.trace
    }

    pairing_coeff_override_result = resolve(
        "physical.lithography.source_binding_pairing_coefficient",
        assignments={
            "physical.lithography.nuclear_pairing_gap_reference_energy": case.test_pairing_gap_ref,
            "physical.lithography.source_pairing_reference_mass_number": 9,
        },
    )
    assert float(pairing_coeff_override_result.value) == pytest.approx(3.0)
    assert "physical.eq.lithography_source_pairing_reference_mass_number" not in {
        step.equation for step in pairing_coeff_override_result.trace
    }


    binding_result = resolve(
        "physical.lithography.source_nuclear_binding_energy",
        assignments={
            **source_quark_assignments(2, 2),
            "physical.lithography.nuclear_binding_coulomb_coefficient": case.test_coulomb_coeff,
            "physical.lithography.nuclear_binding_volume_coefficient": case.test_volume_coeff,
            "physical.lithography.nuclear_binding_surface_coefficient": case.test_surface_coeff,
            "physical.lithography.nuclear_binding_asymmetry_coefficient": case.test_asymmetry_coeff,
            "physical.lithography.nuclear_pairing_gap_reference_energy": case.test_pairing_gap_ref,
        },
    )
    assert float(binding_result.value) == pytest.approx(
        10.0 * 4.0
        - 2.0 * 4.0 ** (2.0 / 3.0)
        - 0.5 * 2.0 * 1.0 / 4.0 ** (1.0 / 3.0)
        + 2.0 / 4.0 ** 0.5
    )
    assert float(resolve(
        "physical.lithography.source_pairing_sign",
        assignments=source_quark_assignments(2, 2),
    ).value) == pytest.approx(1.0)
    assert float(resolve(
        "physical.lithography.source_pairing_sign",
        assignments=source_quark_assignments(3, 3),
    ).value) == pytest.approx(-1.0)
    assert float(resolve(
        "physical.lithography.source_pairing_sign",
        assignments=source_quark_assignments(2, 3),
    ).value) == pytest.approx(0.0)


def test_lithography_source_quantum_numeric_chain_resolves_electronic_shell_terms():
    case = source_quantum_numeric_case()

    partition_ratio_result = resolve(
        "physical.lithography.source_ionization_partition_ratio",
        assignments={
            "physical.lithography.source_transition_shell_capacity": 8.0,
            "physical.lithography.source_ionization_same_shell_screening_electron_count": 1.0,
        },
    )
    assert float(partition_ratio_result.value) == pytest.approx(2.0 / 7.0)
    assert [step.equation for step in partition_ratio_result.trace] == [
        "physical.eq.lithography_source_ionization_partition_ratio",
    ]
    hydrogen_partition_ratio_result = resolve(
        "physical.lithography.source_ionization_partition_ratio",
        assignments={
            "physical.lithography.source_transition_shell_capacity": 2.0,
            "physical.lithography.source_ionization_same_shell_screening_electron_count": 0.0,
        },
    )
    assert float(hydrogen_partition_ratio_result.value) == pytest.approx(0.5)
    assert (
        Registry.equations[
            "physical.eq.lithography_source_ionization_partition_ratio"
        ].role
        is RelationRole.APPROXIMATION
    )

    ion_charge_result = resolve(
        "physical.lithography.source_ion_charge_state",
        assignments={
            **source_quark_assignments(4, 0),
            "physical.lithography.source_plasma_electron_temperature": case.test_plasma_temperature,
            "physical.lithography.source_plasma_electron_number_density": case.test_plasma_electron_number_density,
            "physical.lithography.source_ionization_partition_ratio": 2.0 / 7.0,
            "physical.lithography.source_ionization_energy": 0.0,
        },
    )
    assert float(ion_charge_result.value) == pytest.approx(24.0 / 13.0)

    inner_closed_result = resolve(
        "physical.lithography.source_inner_closed_shell_electron_count",
        assignments={
            **source_quark_assignments(4, 0),
            **case.plasma_assignments_for_source(4),
            "physical.lithography.source_ionization_partition_ratio": 0.0,
        },
    )
    assert float(inner_closed_result.value) == pytest.approx(2.0)

    outer_shell_result = resolve(
        "physical.lithography.source_outer_shell_electron_count",
        assignments={
            **source_quark_assignments(12, 0),
            **case.plasma_assignments_for_source(12),
            "physical.lithography.source_ionization_partition_ratio": 0.0,
        },
    )
    assert float(outer_shell_result.value) == pytest.approx(0.0)

    screening_result = resolve(
        "physical.lithography.source_screening_constant",
        assignments={
            **source_quark_assignments(4, 0),
            **case.plasma_assignments_for_source(4),
            "physical.lithography.source_ionization_partition_ratio": 0.0,
        },
    )
    assert float(screening_result.value) == pytest.approx(2.5)


def test_lithography_source_quantum_numeric_chain_resolves_photon_energy():
    case = source_quantum_numeric_case()

    energy_result = resolve(
        "physical.lithography.photon_energy",
        assignments=case.assignments,
    )
    assert float(energy_result.value) == pytest.approx(case.expected_energy)

    wavelength_result = resolve(
        "physical.lithography.wavelength",
        assignments=case.assignments,
    )
    assert float(wavelength_result.value) == pytest.approx(
        case.planck * case.c / case.expected_energy
    )
