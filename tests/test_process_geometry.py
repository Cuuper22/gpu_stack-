"""
tests/test_process_geometry.py
==============================

Process geometry should feed the transistor channel length rather than leaving
`physical.channel_length` as a bare datasheet/root knob.
"""

import pytest
import sympy as sp

from gpu_stack import Registry, resolve
from gpu_stack.core import Inequality, RelationRole
from gpu_stack.scopes import physical_lithography_absorption_edge as absorption_edge


def source_quark_assignments(protons, neutrons):
    return {
        "physical.lithography.source_valence_up_quark_count": 2 * protons + neutrons,
        "physical.lithography.source_valence_down_quark_count": protons + 2 * neutrons,
    }


def failed_constraint(result, equation):
    check = next(c for c in result.constraints if c.equation == equation)
    assert check.satisfied is False
    assert check.missing == set()
    return check


def test_source_plasma_radial_expansion_uses_species_mass_chain():
    proton_mass = Registry.variables["physics.proton_mass"].value
    neutron_mass = Registry.variables["physics.neutron_mass"].value
    boltzmann = Registry.variables["physics.boltzmann"].value
    gas_temperature = 1000.0
    expansion_factor = (5.0 / 3.0) ** 0.5
    species_mass = proton_mass + neutron_mass

    result = resolve(
        "physical.lithography.source_plasma_column_radial_expansion_speed",
        assignments={
            **source_quark_assignments(1, 1),
            "physical.lithography.source_plasma_species_gas_temperature": gas_temperature,
        },
    )

    assert float(result.value) == pytest.approx(
        expansion_factor * (boltzmann * gas_temperature / species_mass) ** 0.5
    )
    assert [step.equation for step in result.trace] == [
        "physical.eq.lithography_source_proton_count_from_valence_quarks",
        "physical.eq.lithography_source_neutron_count_from_valence_quarks",
        "physical.eq.lithography_source_plasma_species_particle_mass_from_nuclear_counts",
        "physical.eq.lithography_source_plasma_species_thermal_speed_from_gas_temperature",
        "physical.eq.lithography_source_plasma_column_expansion_speed_factor_from_monatomic_sound_speed",
        "physical.eq.lithography_source_plasma_column_radial_expansion_speed_from_species_thermal_speed",
    ]


def test_source_plasma_absorption_edge_uses_ionization_shell_chain():
    assert "LITHOGRAPHY_SOURCE_ABSORPTION_EDGE_REF" in absorption_edge.__all__
    assert absorption_edge.LITHOGRAPHY_SOURCE_ABSORPTION_EDGE_REF

    hbar = Registry.variables["physics.hbar"].value
    c = Registry.variables["physics.speed_of_light"].value

    wavelength_result = resolve(
        "physical.lithography.source_plasma_drive_beam_wavelength",
        assignments={
            "physical.lithography.source_ionization_energy": 6.0 * hbar * c,
            "physical.lithography.source_plasma_drive_edge_detuning_ratio": 1.5,
        },
    )
    assert float(wavelength_result.value) == pytest.approx(
        1.5 * 2.0 * float(sp.pi) * hbar * c / (6.0 * hbar * c)
    )
    assert [step.equation for step in wavelength_result.trace] == [
        "physical.eq.lithography_source_plasma_drive_beam_wavelength_from_ionization_edge",
    ]

    resonance_result = resolve(
        "physical.lithography.source_plasma_absorption_resonance_to_drive_ratio",
        assignments={
            "physical.lithography.source_ionization_energy": 6.0 * hbar,
            "physical.lithography.source_plasma_drive_beam_angular_frequency": 3.0,
        },
    )
    assert float(resonance_result.value) == pytest.approx(2.0)
    assert [step.equation for step in resonance_result.trace] == [
        "physical.eq.lithography_source_plasma_absorption_resonance_to_drive_ratio_from_ionization_edge",
    ]

    participating_result = resolve(
        "physical.lithography.source_plasma_absorption_participating_electron_fraction",
        assignments={
            "physical.lithography.source_proton_count": 4.0,
            "physical.lithography.source_ionization_same_shell_screening_electron_count": 1.0,
        },
    )
    assert float(participating_result.value) == pytest.approx(0.5)
    assert [step.equation for step in participating_result.trace] == [
        "physical.eq.lithography_source_plasma_absorption_participating_electron_fraction_from_ionization_shell",
    ]

    sum_rule_result = resolve(
        "physical.lithography.source_plasma_absorption_sum_rule_fraction",
        assignments={
            "physical.lithography.source_transition_shell_capacity": 8.0,
            "physical.lithography.source_ionization_same_shell_screening_electron_count": 1.0,
        },
    )
    assert float(sum_rule_result.value) == pytest.approx(0.875)
    assert [step.equation for step in sum_rule_result.trace] == [
        "physical.eq.lithography_source_plasma_absorption_sum_rule_fraction_from_ionization_shell_degeneracy",
    ]


def test_source_plasma_operating_root_frontier_is_explicit():
    def deps(name):
        return {v.name for v in Registry.variables[name].direct_dependencies()}

    def assert_root(name):
        variable = Registry.variables[name]
        assert variable.is_root_input
        assert variable.direct_dependencies() == set()

    for root in {
        "physical.lithography.source_plasma_pulse_period",
        "physical.lithography.source_plasma_drive_pulse_duty_factor",
        "physical.lithography.source_plasma_drive_pulse_fluence",
        "physical.lithography.source_plasma_drive_edge_detuning_ratio",
        "physical.lithography.source_plasma_drive_objective_pupil_radius",
        "physical.lithography.source_plasma_drive_objective_focal_length",
        "physical.lithography.source_plasma_species_partial_pressure",
        "physical.lithography.source_plasma_species_gas_temperature",
    }:
        assert_root(root)

    assert deps("physical.lithography.source_plasma_pulse_repetition_rate") == {
        "physical.lithography.source_plasma_pulse_period",
    }
    assert deps("physical.lithography.source_plasma_drive_pulse_duration") == {
        "physical.lithography.source_plasma_drive_pulse_duty_factor",
        "physical.lithography.source_plasma_pulse_period",
    }
    assert deps("physical.lithography.source_plasma_drive_peak_intensity") == {
        "physical.lithography.source_plasma_drive_pulse_duration",
        "physical.lithography.source_plasma_drive_pulse_fluence",
        "physical.lithography.source_plasma_drive_pulse_temporal_shape_factor",
    }
    assert deps("physical.lithography.source_plasma_drive_beam_wavelength") == {
        "physical.lithography.source_ionization_energy",
        "physical.lithography.source_plasma_drive_edge_detuning_ratio",
        "physics.hbar",
        "physics.speed_of_light",
    }
    assert deps("physical.lithography.source_plasma_drive_acceptance_half_angle") == {
        "physical.lithography.source_plasma_drive_objective_focal_length",
        "physical.lithography.source_plasma_drive_objective_pupil_radius",
    }
    assert deps("physical.lithography.source_plasma_species_number_density") == {
        "physical.lithography.source_plasma_species_gas_temperature",
        "physical.lithography.source_plasma_species_partial_pressure",
        "physics.boltzmann",
    }


def medium_component_quark_assignments(component: str, protons: int, neutrons: int):
    return {
        f"physical.lithography.medium_component_{component}_valence_up_quark_count": (
            2 * protons + neutrons
        ),
        f"physical.lithography.medium_component_{component}_valence_down_quark_count": (
            protons + 2 * neutrons
        ),
    }


def medium_liquid_drop_root_assignments(
    volume_coeff=10.0e-13,
    surface_coeff=2.0e-13,
    coulomb_coeff=0.5e-13,
    asymmetry_coeff=3.0e-13,
    pairing_gap=2.0e-13,
):
    return {
        "physical.lithography.nuclear_binding_volume_coefficient": volume_coeff,
        "physical.lithography.nuclear_binding_surface_coefficient": surface_coeff,
        "physical.lithography.nuclear_binding_coulomb_coefficient": coulomb_coeff,
        "physical.lithography.nuclear_binding_asymmetry_coefficient": asymmetry_coeff,
        "physical.lithography.nuclear_pairing_gap_reference_energy": pairing_gap,
    }


def medium_intercomponent_binding_root_assignments(
    binding_energy=5.0e-12,
    component_a_stoich=2,
    component_b_stoich=1,
    charge_unit=1.0,
    relative_permittivity=1.0,
    component_a_mass_number=1.0,
    component_b_mass_number=17.0,
    coulomb_coeff=0.5e-13,
):
    elementary_charge = Registry.variables["physics.elementary_charge"].value
    vacuum_permittivity = Registry.variables["physics.vacuum_permittivity"].value
    component_a_charge = component_b_stoich * charge_unit
    component_b_charge = -component_a_stoich * charge_unit
    pair_count = component_a_stoich * component_b_stoich
    charge_transfer_count = pair_count * charge_unit
    separation = (
        -pair_count
        * component_a_charge
        * component_b_charge
        * elementary_charge**2
        / (
            4.0
            * float(sp.pi)
            * vacuum_permittivity
            * relative_permittivity
            * binding_energy
        )
    )
    radius_coeff = (
        3.0
        * elementary_charge**2
        / (20.0 * float(sp.pi) * vacuum_permittivity * coulomb_coeff)
    )
    component_a_radius = separation / 4.0
    component_b_radius = separation / 4.0
    gap = separation / 2.0
    intercomponent_lorentz_lorenz = (
        (relative_permittivity - 1.0) / (relative_permittivity + 2.0)
    )
    intercomponent_polarizability = (
        intercomponent_lorentz_lorenz
        * 3.0
        * vacuum_permittivity
        * separation**3
    )
    return {
        "physical.lithography.medium_formula_unit_intercomponent_charge_transfer_electron_count": (
            charge_transfer_count
        ),
        "physical.lithography.medium_component_a_intercomponent_radius_scale_factor": (
            component_a_radius
            / (radius_coeff * component_a_mass_number ** (1.0 / 3.0))
        ),
        "physical.lithography.medium_component_b_intercomponent_radius_scale_factor": (
            component_b_radius
            / (radius_coeff * component_b_mass_number ** (1.0 / 3.0))
        ),
        "physical.lithography.medium_intercomponent_gap_fraction": (
            gap / (component_a_radius + component_b_radius)
        ),
        "physical.lithography.medium_intercomponent_polarizable_site_density_factor": (
            1.0
        ),
        "physical.lithography.medium_electric_polarizability": (
            intercomponent_polarizability
        ),
    }


def expected_medium_component_binding_energy(
    protons: int,
    neutrons: int,
    volume_coeff=10.0e-13,
    surface_coeff=2.0e-13,
    coulomb_coeff=0.5e-13,
    asymmetry_coeff=3.0e-13,
    pairing_gap=2.0e-13,
):
    mass_number = protons + neutrons
    neutron_excess = neutrons - protons
    if protons % 2 == 0 and neutrons % 2 == 0:
        pairing_sign = 1.0
    elif protons % 2 == 1 and neutrons % 2 == 1:
        pairing_sign = -1.0
    else:
        pairing_sign = 0.0
    return (
        volume_coeff * mass_number
        - surface_coeff * mass_number ** (2.0 / 3.0)
        - coulomb_coeff * protons * (protons - 1) / mass_number ** (1.0 / 3.0)
        - asymmetry_coeff * neutron_excess**2 / mass_number
        + pairing_sign * pairing_gap
    )


def test_channel_length_has_process_geometry_model():
    channel = Registry.variables["physical.channel_length"]
    assert not channel.is_root_input
    approximations = channel.approximations()
    assert len(approximations) == 1
    eq = approximations[0]
    assert eq.name == "physical.eq.channel_length_process"
    assert eq.role is RelationRole.APPROXIMATION


def test_channel_length_dependencies_are_process_geometry_inputs():
    deps = {v.name for v in Registry.variables["physical.channel_length"].direct_dependencies()}
    assert deps == {
        "physical.process.node_length",
        "physical.process.gate_length_scale",
        "physical.process.gate_length_bias",
    }


def test_process_node_length_depends_on_frontend_and_backend_pitch():
    node = Registry.variables["physical.process.node_length"]
    assert not node.is_root_input
    deps = {v.name for v in node.direct_dependencies()}
    assert deps == {
        "physical.process.contacted_gate_pitch",
        "physical.process.minimum_metal_pitch",
        "physical.process.node_geometry_factor",
    }

    result = resolve(
        "physical.process.node_length",
        assignments={
            "physical.process.contacted_gate_pitch": 4.0,
            "physical.process.minimum_metal_pitch": 9.0,
            "physical.process.node_geometry_factor": 2.0,
        },
    )
    assert float(result.value) == pytest.approx(12.0)


def test_contacted_gate_pitch_depends_on_layout_components():
    cpp = Registry.variables["physical.process.contacted_gate_pitch"]
    assert not cpp.is_root_input
    deps = {v.name for v in cpp.direct_dependencies()}
    assert deps == {
        "physical.process.drawn_gate_length",
        "physical.process.source_drain_contact_width",
        "physical.process.gate_contact_spacing",
    }

    result = resolve(
        "physical.process.contacted_gate_pitch",
        assignments={
            "physical.process.drawn_gate_length": 4.0,
            "physical.process.source_drain_contact_width": 6.0,
            "physical.process.gate_contact_spacing": 1.5,
        },
    )
    assert float(result.value) == pytest.approx(13.0)


def test_drawn_gate_length_depends_on_lithography_resolution_and_bias():
    gate = Registry.variables["physical.process.drawn_gate_length"]
    assert not gate.is_root_input
    deps = {v.name for v in gate.direct_dependencies()}
    assert deps == {
        "physical.lithography.gate_resolution",
        "physical.process.gate_length_lithography_bias",
    }

    result = resolve(
        "physical.process.drawn_gate_length",
        assignments={
            "physical.lithography.wavelength": 10.0,
            "physical.lithography.numerical_aperture": 2.0,
            "physical.lithography.gate_k1": 0.8,
            "physical.process.gate_length_lithography_bias": 1.0,
        },
    )
    assert float(result.value) == pytest.approx(5.0)


def test_lithography_wavelength_and_numerical_aperture_have_physical_models():
    wavelength = Registry.variables["physical.lithography.wavelength"]
    photon_energy = Registry.variables["physical.lithography.photon_energy"]
    frequency = Registry.variables["physical.lithography.photon_frequency"]
    angular_frequency = Registry.variables["physical.lithography.source_angular_frequency"]
    numerical_aperture = Registry.variables["physical.lithography.numerical_aperture"]
    assert not wavelength.is_root_input
    assert not photon_energy.is_root_input
    assert not frequency.is_root_input
    assert not angular_frequency.is_root_input
    assert not numerical_aperture.is_root_input
    assert wavelength.symbol.is_positive is True
    assert photon_energy.symbol.is_positive is True
    assert frequency.symbol.is_positive is True
    assert angular_frequency.symbol.is_positive is True
    assert {v.name for v in wavelength.direct_dependencies()} == {
        "physics.speed_of_light",
        "physical.lithography.photon_frequency",
    }
    assert {v.name for v in photon_energy.direct_dependencies()} == {
        "physical.lithography.source_transition_energy",
    }
    assert {v.name for v in frequency.direct_dependencies()} == {
        "physical.lithography.photon_energy",
        "physics.planck",
    }
    assert {v.name for v in angular_frequency.direct_dependencies()} == {
        "physical.lithography.photon_frequency",
    }
    assert {v.name for v in numerical_aperture.direct_dependencies()} == {
        "physical.lithography.medium_refractive_index",
        "physical.lithography.acceptance_half_angle",
    }

    c = Registry.variables["physics.speed_of_light"].value
    h = Registry.variables["physics.planck"].value
    frequency_result = resolve(
        "physical.lithography.photon_frequency",
        assignments={
            "physical.lithography.photon_energy": h * c / 10.0,
        },
    )
    assert float(frequency_result.value) == pytest.approx(c / 10.0)

    angular_result = resolve(
        "physical.lithography.source_angular_frequency",
        assignments={
            "physical.lithography.photon_energy": h * c / 10.0,
        },
    )
    assert float(angular_result.value) == pytest.approx(2.0 * float(sp.pi) * c / 10.0)

    wavelength_result = resolve(
        "physical.lithography.wavelength",
        assignments={
            "physical.lithography.photon_energy": h * c / 10.0,
        },
    )
    assert float(wavelength_result.value) == pytest.approx(10.0)


def test_lithography_rejects_nonpositive_photon_domains():
    for bad_energy in (0.0, -1.0):
        result = resolve(
            "physical.lithography.wavelength",
            assignments={
                "physical.lithography.photon_energy": bad_energy,
            },
        )
        check = next(
            c for c in result.constraints
            if c.equation == "domain.physical.lithography.photon_energy.positive"
        )
        assert check.satisfied is False
        assert check.missing == set()

    for bad_frequency in (0.0, -1.0):
        result = resolve(
            "physical.lithography.wavelength",
            assignments={
                "physical.lithography.photon_frequency": bad_frequency,
            },
        )
        checks = {c.equation: c for c in result.constraints}
        assert (
            checks[
                "domain.physical.lithography.photon_frequency.positive"
            ].satisfied
            is False
        )
        assert (
            checks[
                "domain.physical.lithography.wavelength.positive"
            ].satisfied
            is False
        )

    for bad_transition_energy in (0.0, -1.0):
        result = resolve(
            "physical.lithography.photon_energy",
            assignments={
                "physical.lithography.source_transition_energy": (
                    bad_transition_energy
                ),
            },
        )
        checks = {c.equation: c for c in result.constraints}
        assert (
            checks[
                "domain.physical.lithography.source_transition_energy.positive"
            ].satisfied
            is False
        )
        assert (
            checks[
                "domain.physical.lithography.photon_energy.positive"
            ].satisfied
            is False
        )


def test_lithography_photon_energy_has_quantum_source_model():
    photon_energy = Registry.variables["physical.lithography.photon_energy"]
    up_quarks = Registry.variables[
        "physical.lithography.source_valence_up_quark_count"
    ]
    down_quarks = Registry.variables[
        "physical.lithography.source_valence_down_quark_count"
    ]
    atomic_number = Registry.variables["physical.lithography.source_atomic_number"]
    isotope_mass_number = Registry.variables["physical.lithography.source_isotope_mass_number"]
    proton_count = Registry.variables["physical.lithography.source_proton_count"]
    neutron_count = Registry.variables["physical.lithography.source_neutron_count"]
    binding_energy = Registry.variables["physical.lithography.source_nuclear_binding_energy"]
    mass_number = Registry.variables["physical.lithography.source_mass_number"]
    neutron_excess = Registry.variables["physical.lithography.source_neutron_excess"]
    saturation_density = Registry.variables[
        "physical.lithography.source_nuclear_saturation_number_density"
    ]
    radius_coeff = Registry.variables["physical.lithography.source_nuclear_radius_coefficient"]
    bulk_binding_density = Registry.variables[
        "physical.lithography.source_nuclear_bulk_binding_energy_density"
    ]
    volume_coeff = Registry.variables["physical.lithography.source_binding_volume_coefficient"]
    surface_tension = Registry.variables["physical.lithography.source_nuclear_surface_tension"]
    surface_coeff = Registry.variables["physical.lithography.source_binding_surface_coefficient"]
    symmetry_density = Registry.variables["physical.lithography.source_nuclear_symmetry_energy_density"]
    asymmetry_coeff = Registry.variables["physical.lithography.source_binding_asymmetry_coefficient"]
    pairing_gap_ref = Registry.variables[
        "physical.lithography.source_nuclear_pairing_gap_reference_energy"
    ]
    shared_volume_coeff = Registry.variables[
        "physical.lithography.nuclear_binding_volume_coefficient"
    ]
    shared_surface_coeff = Registry.variables[
        "physical.lithography.nuclear_binding_surface_coefficient"
    ]
    shared_coulomb_coeff = Registry.variables[
        "physical.lithography.nuclear_binding_coulomb_coefficient"
    ]
    shared_asymmetry_coeff = Registry.variables[
        "physical.lithography.nuclear_binding_asymmetry_coefficient"
    ]
    shared_pairing_gap_ref = Registry.variables[
        "physical.lithography.nuclear_pairing_gap_reference_energy"
    ]
    pairing_mass_ref = Registry.variables[
        "physical.lithography.source_pairing_reference_mass_number"
    ]
    pairing_coeff = Registry.variables["physical.lithography.source_binding_pairing_coefficient"]
    coulomb_coeff = Registry.variables["physical.lithography.source_binding_coulomb_coefficient"]
    volume_term = Registry.variables["physical.lithography.source_binding_volume_term"]
    surface_term = Registry.variables["physical.lithography.source_binding_surface_term"]
    coulomb_term = Registry.variables["physical.lithography.source_binding_coulomb_term"]
    asymmetry_term = Registry.variables["physical.lithography.source_binding_asymmetry_term"]
    pairing_sign = Registry.variables["physical.lithography.source_pairing_sign"]
    pairing_term = Registry.variables["physical.lithography.source_binding_pairing_term"]
    nuclear_mass = Registry.variables["physical.lithography.source_nuclear_mass"]
    reduced_mass = Registry.variables["physical.lithography.source_reduced_mass"]
    reduced_ratio = Registry.variables["physical.lithography.source_reduced_mass_ratio"]
    ion_charge_state = Registry.variables["physical.lithography.source_ion_charge_state"]
    plasma_mean_energy = Registry.variables[
        "physical.lithography.source_plasma_electron_mean_kinetic_energy"
    ]
    plasma_debye_length = Registry.variables[
        "physical.lithography.source_plasma_debye_length"
    ]
    plasma_pulse_period = Registry.variables[
        "physical.lithography.source_plasma_pulse_period"
    ]
    plasma_pulse_energy = Registry.variables[
        "physical.lithography.source_plasma_pulse_energy"
    ]
    plasma_pulse_repetition_rate = Registry.variables[
        "physical.lithography.source_plasma_pulse_repetition_rate"
    ]
    plasma_drive_pulse_duty_factor = Registry.variables[
        "physical.lithography.source_plasma_drive_pulse_duty_factor"
    ]
    plasma_drive_pulse_fluence = Registry.variables[
        "physical.lithography.source_plasma_drive_pulse_fluence"
    ]
    plasma_drive_peak_intensity = Registry.variables[
        "physical.lithography.source_plasma_drive_peak_intensity"
    ]
    plasma_drive_pulse_duration = Registry.variables[
        "physical.lithography.source_plasma_drive_pulse_duration"
    ]
    plasma_drive_pulse_rise_fraction = Registry.variables[
        "physical.lithography.source_plasma_drive_pulse_rise_fraction"
    ]
    plasma_drive_pulse_fall_fraction = Registry.variables[
        "physical.lithography.source_plasma_drive_pulse_fall_fraction"
    ]
    plasma_drive_pulse_flat_fraction = Registry.variables[
        "physical.lithography.source_plasma_drive_pulse_flat_fraction"
    ]
    plasma_drive_pulse_temporal_shape_factor = Registry.variables[
        "physical.lithography.source_plasma_drive_pulse_temporal_shape_factor"
    ]
    plasma_drive_beam_wavelength = Registry.variables[
        "physical.lithography.source_plasma_drive_beam_wavelength"
    ]
    plasma_drive_edge_detuning_ratio = Registry.variables[
        "physical.lithography.source_plasma_drive_edge_detuning_ratio"
    ]
    plasma_drive_objective_pupil_radius = Registry.variables[
        "physical.lithography.source_plasma_drive_objective_pupil_radius"
    ]
    plasma_drive_objective_focal_length = Registry.variables[
        "physical.lithography.source_plasma_drive_objective_focal_length"
    ]
    plasma_drive_pupil_beam_fill_factor = Registry.variables[
        "physical.lithography.source_plasma_drive_pupil_beam_fill_factor"
    ]
    plasma_drive_acceptance_half_angle = Registry.variables[
        "physical.lithography.source_plasma_drive_acceptance_half_angle"
    ]
    plasma_drive_numerical_aperture = Registry.variables[
        "physical.lithography.source_plasma_drive_numerical_aperture"
    ]
    plasma_drive_focus_f_number = Registry.variables[
        "physical.lithography.source_plasma_drive_focus_f_number"
    ]
    plasma_drive_beam_parameter_waist_radius = Registry.variables[
        "physical.lithography.source_plasma_drive_beam_parameter_waist_radius"
    ]
    plasma_drive_far_field_divergence_half_angle = Registry.variables[
        "physical.lithography.source_plasma_drive_far_field_divergence_half_angle"
    ]
    plasma_drive_beam_parameter_product = Registry.variables[
        "physical.lithography.source_plasma_drive_beam_parameter_product"
    ]
    plasma_drive_beam_quality_factor = Registry.variables[
        "physical.lithography.source_plasma_drive_beam_quality_factor"
    ]
    plasma_drive_focus_waist_coefficient = Registry.variables[
        "physical.lithography.source_plasma_drive_focus_waist_coefficient"
    ]
    plasma_drive_spot_radius = Registry.variables[
        "physical.lithography.source_plasma_drive_spot_radius"
    ]
    plasma_drive_rayleigh_range = Registry.variables[
        "physical.lithography.source_plasma_drive_rayleigh_range"
    ]
    plasma_drive_confocal_length = Registry.variables[
        "physical.lithography.source_plasma_drive_confocal_length"
    ]
    plasma_drive_spot_axis_ratio = Registry.variables[
        "physical.lithography.source_plasma_drive_spot_axis_ratio"
    ]
    plasma_drive_spot_area_fill_factor = Registry.variables[
        "physical.lithography.source_plasma_drive_spot_area_fill_factor"
    ]
    plasma_drive_spot_shape_factor = Registry.variables[
        "physical.lithography.source_plasma_drive_spot_shape_factor"
    ]
    plasma_drive_spot_area = Registry.variables[
        "physical.lithography.source_plasma_drive_spot_area"
    ]
    plasma_drive_power = Registry.variables[
        "physical.lithography.source_plasma_drive_power"
    ]
    plasma_species_partial_pressure = Registry.variables[
        "physical.lithography.source_plasma_species_partial_pressure"
    ]
    plasma_species_gas_temperature = Registry.variables[
        "physical.lithography.source_plasma_species_gas_temperature"
    ]
    plasma_species_number_density = Registry.variables[
        "physical.lithography.source_plasma_species_number_density"
    ]
    plasma_column_expansion_speed_factor = Registry.variables[
        "physical.lithography.source_plasma_column_expansion_speed_factor"
    ]
    plasma_column_radial_expansion_speed = Registry.variables[
        "physical.lithography.source_plasma_column_radial_expansion_speed"
    ]
    plasma_column_radius_expansion_factor = Registry.variables[
        "physical.lithography.source_plasma_column_radius_expansion_factor"
    ]
    plasma_column_radius = Registry.variables[
        "physical.lithography.source_plasma_column_radius"
    ]
    plasma_column_aspect_ratio = Registry.variables[
        "physical.lithography.source_plasma_column_aspect_ratio"
    ]
    plasma_column_length = Registry.variables[
        "physical.lithography.source_plasma_column_length"
    ]
    plasma_active_fill_factor = Registry.variables[
        "physical.lithography.source_plasma_active_fill_factor"
    ]
    plasma_active_volume = Registry.variables[
        "physical.lithography.source_plasma_active_volume"
    ]
    plasma_absorption_path_direction_cosine = Registry.variables[
        "physical.lithography.source_plasma_absorption_path_direction_cosine"
    ]
    plasma_absorption_path_shape_factor = Registry.variables[
        "physical.lithography.source_plasma_absorption_path_shape_factor"
    ]
    plasma_absorption_path_length = Registry.variables[
        "physical.lithography.source_plasma_absorption_path_length"
    ]
    plasma_drive_beam_angular_frequency = Registry.variables[
        "physical.lithography.source_plasma_drive_beam_angular_frequency"
    ]
    plasma_absorption_resonance_to_drive_ratio = Registry.variables[
        "physical.lithography.source_plasma_absorption_resonance_to_drive_ratio"
    ]
    plasma_absorption_quality_factor = Registry.variables[
        "physical.lithography.source_plasma_absorption_quality_factor"
    ]
    plasma_absorption_collision_cross_section = Registry.variables[
        "physical.lithography.source_plasma_absorption_collision_cross_section"
    ]
    plasma_absorption_collision_orbital_radius = Registry.variables[
        "physical.lithography.source_plasma_absorption_collision_orbital_radius"
    ]
    plasma_absorption_participating_electron_fraction = Registry.variables[
        "physical.lithography.source_plasma_absorption_participating_electron_fraction"
    ]
    plasma_absorption_sum_rule_fraction = Registry.variables[
        "physical.lithography.source_plasma_absorption_sum_rule_fraction"
    ]
    plasma_absorption_resonance = Registry.variables[
        "physical.lithography.source_plasma_absorption_resonance_angular_frequency"
    ]
    plasma_absorption_damping_rate = Registry.variables[
        "physical.lithography.source_plasma_absorption_damping_rate"
    ]
    plasma_absorption_oscillator_strength = Registry.variables[
        "physical.lithography.source_plasma_absorption_oscillator_strength"
    ]
    plasma_absorption_cross_section = Registry.variables[
        "physical.lithography.source_plasma_absorption_cross_section"
    ]
    plasma_absorption_optical_depth = Registry.variables[
        "physical.lithography.source_plasma_absorption_optical_depth"
    ]
    plasma_drive_energy_absorption_fraction = Registry.variables[
        "physical.lithography.source_plasma_drive_energy_absorption_fraction"
    ]
    plasma_drive_centroid_offset_to_column_radius_ratio = Registry.variables[
        "physical.lithography.source_plasma_drive_centroid_offset_to_column_radius_ratio"
    ]
    plasma_drive_pointing_overlap_factor = Registry.variables[
        "physical.lithography.source_plasma_drive_pointing_overlap_factor"
    ]
    plasma_drive_transverse_overlap_factor = Registry.variables[
        "physical.lithography.source_plasma_drive_transverse_overlap_factor"
    ]
    plasma_drive_spatial_overlap_factor = Registry.variables[
        "physical.lithography.source_plasma_drive_spatial_overlap_factor"
    ]
    plasma_active_lifetime_to_drive_pulse_ratio = Registry.variables[
        "physical.lithography.source_plasma_active_lifetime_to_drive_pulse_ratio"
    ]
    plasma_active_response_duration = Registry.variables[
        "physical.lithography.source_plasma_active_response_duration"
    ]
    plasma_drive_timing_offset_fraction = Registry.variables[
        "physical.lithography.source_plasma_drive_timing_offset_fraction"
    ]
    plasma_drive_timing_offset_duration = Registry.variables[
        "physical.lithography.source_plasma_drive_timing_offset_duration"
    ]
    plasma_drive_temporal_duration_match_factor = Registry.variables[
        "physical.lithography.source_plasma_drive_temporal_duration_match_factor"
    ]
    plasma_drive_temporal_alignment_factor = Registry.variables[
        "physical.lithography.source_plasma_drive_temporal_alignment_factor"
    ]
    plasma_drive_temporal_overlap_factor = Registry.variables[
        "physical.lithography.source_plasma_drive_temporal_overlap_factor"
    ]
    plasma_drive_overlap_factor = Registry.variables[
        "physical.lithography.source_plasma_drive_overlap_factor"
    ]
    plasma_electron_heating_fraction = Registry.variables[
        "physical.lithography.source_plasma_electron_heating_fraction"
    ]
    plasma_absorption_efficiency = Registry.variables[
        "physical.lithography.source_plasma_absorption_efficiency"
    ]
    plasma_absorbed_power = Registry.variables[
        "physical.lithography.source_plasma_absorbed_power"
    ]
    plasma_energy_loss_path_direction_cosine = Registry.variables[
        "physical.lithography.source_plasma_energy_loss_path_direction_cosine"
    ]
    plasma_energy_loss_path_factor = Registry.variables[
        "physical.lithography.source_plasma_energy_loss_path_factor"
    ]
    plasma_energy_loss_path_length = Registry.variables[
        "physical.lithography.source_plasma_energy_loss_path_length"
    ]
    plasma_species_particle_mass = Registry.variables[
        "physical.lithography.source_plasma_species_particle_mass"
    ]
    plasma_energy_loss_transport_speed_factor = Registry.variables[
        "physical.lithography.source_plasma_energy_loss_transport_speed_factor"
    ]
    plasma_species_thermal_speed = Registry.variables[
        "physical.lithography.source_plasma_species_thermal_speed"
    ]
    plasma_energy_loss_speed = Registry.variables[
        "physical.lithography.source_plasma_energy_loss_speed"
    ]
    plasma_confinement_time = Registry.variables[
        "physical.lithography.source_plasma_energy_confinement_time"
    ]
    plasma_free_electron_inventory_charge_fraction = Registry.variables[
        "physical.lithography.source_plasma_free_electron_inventory_charge_fraction"
    ]
    plasma_free_electron_yield = Registry.variables[
        "physical.lithography.source_plasma_free_electron_yield_per_source_particle"
    ]
    plasma_free_electron_count = Registry.variables[
        "physical.lithography.source_plasma_free_electron_count"
    ]
    plasma_internal_energy = Registry.variables[
        "physical.lithography.source_plasma_electron_internal_energy"
    ]
    plasma_temperature = Registry.variables[
        "physical.lithography.source_plasma_electron_temperature"
    ]
    plasma_density = Registry.variables[
        "physical.lithography.source_plasma_electron_number_density"
    ]
    ionization_energy = Registry.variables["physical.lithography.source_ionization_energy"]
    ionization_principal = Registry.variables[
        "physical.lithography.source_ionization_principal_quantum_number"
    ]
    ionization_screening = Registry.variables[
        "physical.lithography.source_ionization_screening_constant"
    ]
    ionization_inner_screeners = Registry.variables[
        "physical.lithography.source_ionization_inner_shell_screening_electron_count"
    ]
    ionization_same_screeners = Registry.variables[
        "physical.lithography.source_ionization_same_shell_screening_electron_count"
    ]
    ionization_z_eff = Registry.variables[
        "physical.lithography.source_ionization_effective_nuclear_charge"
    ]
    partition_ratio = Registry.variables[
        "physical.lithography.source_ionization_partition_ratio"
    ]
    saha_thermal_density = Registry.variables[
        "physical.lithography.source_saha_thermal_number_density"
    ]
    saha_ratio = Registry.variables["physical.lithography.source_saha_ionization_ratio"]
    saha_fraction = Registry.variables["physical.lithography.source_saha_ionization_fraction"]
    bound_electrons = Registry.variables["physical.lithography.source_bound_electron_count"]
    lower_principal = Registry.variables[
        "physical.lithography.source_lower_principal_quantum_number"
    ]
    upper_principal = Registry.variables[
        "physical.lithography.source_upper_principal_quantum_number"
    ]
    transition_step = Registry.variables[
        "physical.lithography.source_transition_principal_quantum_step"
    ]
    shell_capacity = Registry.variables["physical.lithography.source_transition_shell_capacity"]
    inner_closed_capacity = Registry.variables[
        "physical.lithography.source_inner_closed_shell_capacity"
    ]
    inner_closed_shells = Registry.variables[
        "physical.lithography.source_inner_closed_shell_electron_count"
    ]
    outer_shells = Registry.variables[
        "physical.lithography.source_outer_shell_electron_count"
    ]
    transition_shell_occupancy = Registry.variables[
        "physical.lithography.source_transition_shell_occupancy"
    ]
    inner_screeners = Registry.variables["physical.lithography.source_inner_shell_screening_electron_count"]
    same_screeners = Registry.variables["physical.lithography.source_same_shell_screening_electron_count"]
    inner_shielding = Registry.variables["physical.lithography.source_inner_shell_shielding_factor"]
    same_shielding = Registry.variables["physical.lithography.source_same_shell_shielding_factor"]
    screening = Registry.variables["physical.lithography.source_screening_constant"]
    z_eff = Registry.variables["physical.lithography.source_effective_nuclear_charge"]
    transition = Registry.variables["physical.lithography.source_transition_energy"]
    assert not photon_energy.is_root_input
    assert up_quarks.is_root_input
    assert down_quarks.is_root_input
    assert not atomic_number.is_root_input
    assert not isotope_mass_number.is_root_input
    assert not proton_count.is_root_input
    assert not neutron_count.is_root_input
    assert len(proton_count.defining_equations) == 1
    assert len(neutron_count.defining_equations) == 1
    assert not proton_count.has_multiple_definitions()
    assert not neutron_count.has_multiple_definitions()
    assert not binding_energy.is_root_input
    assert not mass_number.is_root_input
    assert not neutron_excess.is_root_input
    assert not saturation_density.is_root_input
    assert not radius_coeff.is_root_input
    assert not bulk_binding_density.is_root_input
    assert shared_volume_coeff.is_root_input
    assert shared_surface_coeff.is_root_input
    assert shared_coulomb_coeff.is_root_input
    assert shared_asymmetry_coeff.is_root_input
    assert shared_pairing_gap_ref.is_root_input
    assert not volume_coeff.is_root_input
    assert not surface_tension.is_root_input
    assert not surface_coeff.is_root_input
    assert not symmetry_density.is_root_input
    assert not asymmetry_coeff.is_root_input
    assert not pairing_gap_ref.is_root_input
    assert not pairing_mass_ref.is_root_input
    assert not pairing_coeff.is_root_input
    assert not coulomb_coeff.is_root_input
    assert not volume_term.is_root_input
    assert not surface_term.is_root_input
    assert not coulomb_term.is_root_input
    assert not asymmetry_term.is_root_input
    assert not pairing_sign.is_root_input
    assert not pairing_term.is_root_input
    assert not nuclear_mass.is_root_input
    assert not reduced_mass.is_root_input
    assert not reduced_ratio.is_root_input
    assert not ion_charge_state.is_root_input
    assert not plasma_mean_energy.is_root_input
    assert not plasma_debye_length.is_root_input
    assert plasma_pulse_period.is_root_input
    assert not plasma_pulse_repetition_rate.is_root_input
    assert plasma_drive_pulse_duty_factor.is_root_input
    assert plasma_drive_pulse_fluence.is_root_input
    assert not plasma_drive_peak_intensity.is_root_input
    assert not plasma_drive_pulse_duration.is_root_input
    assert plasma_drive_pulse_rise_fraction.is_root_input
    assert not plasma_drive_pulse_fall_fraction.is_root_input
    assert not plasma_drive_pulse_flat_fraction.is_root_input
    assert not plasma_drive_pulse_temporal_shape_factor.is_root_input
    assert not plasma_drive_beam_wavelength.is_root_input
    assert plasma_drive_edge_detuning_ratio.is_root_input
    assert plasma_drive_objective_pupil_radius.is_root_input
    assert plasma_drive_objective_focal_length.is_root_input
    assert plasma_drive_pupil_beam_fill_factor.is_root_input
    assert not plasma_drive_acceptance_half_angle.is_root_input
    assert not plasma_drive_numerical_aperture.is_root_input
    assert not plasma_drive_focus_f_number.is_root_input
    assert not plasma_drive_beam_parameter_waist_radius.is_root_input
    assert plasma_drive_far_field_divergence_half_angle.is_root_input
    assert not plasma_drive_beam_parameter_product.is_root_input
    assert not plasma_drive_beam_quality_factor.is_root_input
    assert not plasma_drive_focus_waist_coefficient.is_root_input
    assert not plasma_drive_spot_radius.is_root_input
    assert not plasma_drive_rayleigh_range.is_root_input
    assert not plasma_drive_confocal_length.is_root_input
    assert not plasma_drive_spot_axis_ratio.is_root_input
    assert not plasma_drive_spot_area_fill_factor.is_root_input
    assert not plasma_drive_spot_shape_factor.is_root_input
    assert not plasma_drive_spot_area.is_root_input
    assert not plasma_pulse_energy.is_root_input
    assert not plasma_drive_power.is_root_input
    assert plasma_species_partial_pressure.is_root_input
    assert plasma_species_gas_temperature.is_root_input
    assert not plasma_species_number_density.is_root_input
    assert not plasma_column_expansion_speed_factor.is_root_input
    assert not plasma_column_radial_expansion_speed.is_root_input
    assert not plasma_column_radius_expansion_factor.is_root_input
    assert not plasma_column_radius.is_root_input
    assert not plasma_column_aspect_ratio.is_root_input
    assert not plasma_column_length.is_root_input
    assert not plasma_active_fill_factor.is_root_input
    assert not plasma_active_volume.is_root_input
    assert not plasma_absorption_path_direction_cosine.is_root_input
    assert not plasma_absorption_path_shape_factor.is_root_input
    assert not plasma_absorption_path_length.is_root_input
    assert not plasma_drive_beam_angular_frequency.is_root_input
    assert not plasma_absorption_resonance_to_drive_ratio.is_root_input
    assert not plasma_absorption_quality_factor.is_root_input
    assert not plasma_absorption_collision_cross_section.is_root_input
    assert not plasma_absorption_collision_orbital_radius.is_root_input
    assert not plasma_absorption_participating_electron_fraction.is_root_input
    assert not plasma_absorption_sum_rule_fraction.is_root_input
    assert not plasma_absorption_resonance.is_root_input
    assert not plasma_absorption_damping_rate.is_root_input
    assert not plasma_absorption_oscillator_strength.is_root_input
    assert not plasma_absorption_cross_section.is_root_input
    assert not plasma_absorption_optical_depth.is_root_input
    assert not plasma_drive_energy_absorption_fraction.is_root_input
    assert not plasma_drive_centroid_offset_to_column_radius_ratio.is_root_input
    assert not plasma_drive_pointing_overlap_factor.is_root_input
    assert not plasma_drive_transverse_overlap_factor.is_root_input
    assert not plasma_drive_spatial_overlap_factor.is_root_input
    assert not plasma_active_lifetime_to_drive_pulse_ratio.is_root_input
    assert not plasma_active_response_duration.is_root_input
    assert not plasma_drive_timing_offset_fraction.is_root_input
    assert not plasma_drive_timing_offset_duration.is_root_input
    assert not plasma_drive_temporal_duration_match_factor.is_root_input
    assert not plasma_drive_temporal_alignment_factor.is_root_input
    assert not plasma_drive_temporal_overlap_factor.is_root_input
    assert not plasma_drive_overlap_factor.is_root_input
    assert plasma_electron_heating_fraction.is_root_input
    assert not plasma_absorption_efficiency.is_root_input
    assert not plasma_absorbed_power.is_root_input
    assert not plasma_energy_loss_path_direction_cosine.is_root_input
    assert not plasma_energy_loss_path_factor.is_root_input
    assert not plasma_energy_loss_path_length.is_root_input
    assert not plasma_species_particle_mass.is_root_input
    assert not plasma_energy_loss_transport_speed_factor.is_root_input
    assert not plasma_species_thermal_speed.is_root_input
    assert not plasma_energy_loss_speed.is_root_input
    assert not plasma_confinement_time.is_root_input
    assert plasma_free_electron_inventory_charge_fraction.is_root_input
    assert not plasma_free_electron_yield.is_root_input
    assert not plasma_free_electron_count.is_root_input
    assert not plasma_internal_energy.is_root_input
    assert not plasma_temperature.is_root_input
    assert not plasma_density.is_root_input
    assert not ionization_energy.is_root_input
    assert not ionization_principal.is_root_input
    assert not ionization_screening.is_root_input
    assert not ionization_inner_screeners.is_root_input
    assert not ionization_same_screeners.is_root_input
    assert not ionization_z_eff.is_root_input
    assert not partition_ratio.is_root_input
    assert not saha_thermal_density.is_root_input
    assert not saha_ratio.is_root_input
    assert not saha_fraction.is_root_input
    assert not bound_electrons.is_root_input
    assert not lower_principal.is_root_input
    assert not upper_principal.is_root_input
    assert not transition_step.is_root_input
    assert not shell_capacity.is_root_input
    assert not inner_closed_capacity.is_root_input
    assert not inner_closed_shells.is_root_input
    assert not outer_shells.is_root_input
    assert not transition_shell_occupancy.is_root_input
    assert not inner_screeners.is_root_input
    assert not same_screeners.is_root_input
    assert not inner_shielding.is_root_input
    assert not same_shielding.is_root_input
    assert not screening.is_root_input
    assert not z_eff.is_root_input
    assert not transition.is_root_input
    assert {v.name for v in atomic_number.direct_dependencies()} == {
        "physical.lithography.source_proton_count",
    }
    assert {v.name for v in isotope_mass_number.direct_dependencies()} == {
        "physical.lithography.source_proton_count",
        "physical.lithography.source_neutron_count",
    }
    assert {v.name for v in up_quarks.direct_dependencies()} == set()
    assert {v.name for v in down_quarks.direct_dependencies()} == set()
    assert {
        v.name for v in up_quarks.direct_dependencies(include_constraints=True)
    } == {
        "physical.lithography.source_valence_down_quark_count",
    }
    assert {
        v.name for v in down_quarks.direct_dependencies(include_constraints=True)
    } == {
        "physical.lithography.source_valence_up_quark_count",
    }
    assert {v.name for v in proton_count.direct_dependencies()} == {
        "physical.lithography.source_valence_down_quark_count",
        "physical.lithography.source_valence_up_quark_count",
    }
    assert {v.name for v in neutron_count.direct_dependencies()} == {
        "physical.lithography.source_valence_down_quark_count",
        "physical.lithography.source_valence_up_quark_count",
    }
    assert {v.name for v in mass_number.direct_dependencies()} == {
        "physical.lithography.source_isotope_mass_number",
    }
    assert {v.name for v in neutron_excess.direct_dependencies()} == {
        "physical.lithography.source_proton_count",
        "physical.lithography.source_neutron_count",
    }
    assert {v.name for v in radius_coeff.direct_dependencies()} == {
        "physical.lithography.source_binding_coulomb_coefficient",
        "physics.elementary_charge",
        "physics.vacuum_permittivity",
    }
    assert {v.name for v in saturation_density.direct_dependencies()} == {
        "physical.lithography.source_nuclear_radius_coefficient",
    }
    assert {v.name for v in bulk_binding_density.direct_dependencies()} == {
        "physical.lithography.source_binding_volume_coefficient",
        "physical.lithography.source_nuclear_saturation_number_density",
    }
    assert {v.name for v in volume_coeff.direct_dependencies()} == {
        "physical.lithography.nuclear_binding_volume_coefficient",
    }
    assert {v.name for v in surface_tension.direct_dependencies()} == {
        "physical.lithography.source_binding_surface_coefficient",
        "physical.lithography.source_nuclear_radius_coefficient",
    }
    assert {v.name for v in surface_coeff.direct_dependencies()} == {
        "physical.lithography.nuclear_binding_surface_coefficient",
    }
    assert {v.name for v in symmetry_density.direct_dependencies()} == {
        "physical.lithography.source_binding_asymmetry_coefficient",
        "physical.lithography.source_nuclear_saturation_number_density",
    }
    assert {v.name for v in asymmetry_coeff.direct_dependencies()} == {
        "physical.lithography.nuclear_binding_asymmetry_coefficient",
    }
    assert {v.name for v in pairing_mass_ref.direct_dependencies()} == {
        "physical.lithography.source_mass_number",
    }
    pairing_ref_eq = Registry.equations[
        "physical.eq.lithography_source_pairing_reference_mass_number"
    ]
    assert pairing_mass_ref.approximations() == [pairing_ref_eq]
    assert pairing_ref_eq.role is RelationRole.APPROXIMATION
    assert str(pairing_ref_eq.validity) == "A_litho_src > 0"
    assert pairing_ref_eq.references
    assert getattr(pairing_ref_eq, "_check_units_flag", False)
    assert {v.name for v in pairing_coeff.direct_dependencies()} == {
        "physical.lithography.source_nuclear_pairing_gap_reference_energy",
        "physical.lithography.source_pairing_reference_mass_number",
    }
    assert {v.name for v in pairing_gap_ref.direct_dependencies()} == {
        "physical.lithography.nuclear_pairing_gap_reference_energy",
    }
    assert {v.name for v in coulomb_coeff.direct_dependencies()} == {
        "physical.lithography.nuclear_binding_coulomb_coefficient",
    }
    assert {v.name for v in volume_term.direct_dependencies()} == {
        "physical.lithography.source_binding_volume_coefficient",
        "physical.lithography.source_mass_number",
    }
    assert {v.name for v in surface_term.direct_dependencies()} == {
        "physical.lithography.source_binding_surface_coefficient",
        "physical.lithography.source_mass_number",
    }
    assert {v.name for v in coulomb_term.direct_dependencies()} == {
        "physical.lithography.source_binding_coulomb_coefficient",
        "physical.lithography.source_proton_count",
        "physical.lithography.source_mass_number",
    }
    assert {v.name for v in asymmetry_term.direct_dependencies()} == {
        "physical.lithography.source_binding_asymmetry_coefficient",
        "physical.lithography.source_neutron_excess",
        "physical.lithography.source_mass_number",
    }
    assert {v.name for v in pairing_sign.direct_dependencies()} == {
        "physical.lithography.source_proton_count",
        "physical.lithography.source_neutron_count",
    }
    assert {v.name for v in pairing_term.direct_dependencies()} == {
        "physical.lithography.source_binding_pairing_coefficient",
        "physical.lithography.source_pairing_sign",
        "physical.lithography.source_mass_number",
    }
    assert {v.name for v in binding_energy.direct_dependencies()} == {
        "physical.lithography.source_binding_volume_term",
        "physical.lithography.source_binding_surface_term",
        "physical.lithography.source_binding_coulomb_term",
        "physical.lithography.source_binding_asymmetry_term",
        "physical.lithography.source_binding_pairing_term",
        "physical.lithography.source_mass_number",
    }
    assert {v.name for v in nuclear_mass.direct_dependencies()} == {
        "physical.lithography.source_proton_count",
        "physical.lithography.source_neutron_count",
        "physical.lithography.source_nuclear_binding_energy",
        "physics.proton_mass",
        "physics.neutron_mass",
        "physics.speed_of_light",
    }
    assert {v.name for v in reduced_mass.direct_dependencies()} == {
        "physical.lithography.source_nuclear_mass",
        "physics.electron_mass",
    }
    assert {v.name for v in reduced_ratio.direct_dependencies()} == {
        "physical.lithography.source_reduced_mass",
        "physics.electron_mass",
    }
    assert {v.name for v in ionization_principal.direct_dependencies()} == {
        "physical.lithography.source_lower_principal_quantum_number",
    }
    assert {v.name for v in ionization_inner_screeners.direct_dependencies()} == {
        "physical.lithography.source_inner_closed_shell_capacity",
        "physical.lithography.source_proton_count",
    }
    assert {v.name for v in ionization_same_screeners.direct_dependencies()} == {
        "physical.lithography.source_ionization_inner_shell_screening_electron_count",
        "physical.lithography.source_proton_count",
        "physical.lithography.source_transition_shell_capacity",
    }
    assert {v.name for v in ionization_screening.direct_dependencies()} == {
        "physical.lithography.source_ionization_inner_shell_screening_electron_count",
        "physical.lithography.source_ionization_same_shell_screening_electron_count",
        "physical.lithography.source_inner_shell_shielding_factor",
        "physical.lithography.source_proton_count",
        "physical.lithography.source_same_shell_shielding_factor",
    }
    assert {v.name for v in ionization_z_eff.direct_dependencies()} == {
        "physical.lithography.source_ionization_screening_constant",
        "physical.lithography.source_proton_count",
    }
    assert {v.name for v in ionization_energy.direct_dependencies()} == {
        "physical.lithography.source_ionization_effective_nuclear_charge",
        "physical.lithography.source_ionization_principal_quantum_number",
        "physics.rydberg_energy",
    }
    assert {v.name for v in partition_ratio.direct_dependencies()} == {
        "physical.lithography.source_ionization_same_shell_screening_electron_count",
        "physical.lithography.source_transition_shell_capacity",
    }
    assert {v.name for v in plasma_pulse_repetition_rate.direct_dependencies()} == {
        "physical.lithography.source_plasma_pulse_period",
    }
    assert plasma_drive_pulse_duty_factor.direct_dependencies() == set()
    assert plasma_drive_pulse_fluence.direct_dependencies() == set()
    assert {v.name for v in plasma_drive_pulse_duration.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_pulse_duty_factor",
        "physical.lithography.source_plasma_pulse_period",
    }
    assert plasma_drive_pulse_rise_fraction.direct_dependencies() == set()
    assert {v.name for v in plasma_drive_pulse_fall_fraction.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_pulse_rise_fraction",
    }
    assert {v.name for v in plasma_drive_pulse_flat_fraction.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_pulse_fall_fraction",
        "physical.lithography.source_plasma_drive_pulse_rise_fraction",
    }
    assert {
        v.name for v in plasma_drive_pulse_temporal_shape_factor.direct_dependencies()
    } == {
        "physical.lithography.source_plasma_drive_pulse_fall_fraction",
        "physical.lithography.source_plasma_drive_pulse_flat_fraction",
        "physical.lithography.source_plasma_drive_pulse_rise_fraction",
    }
    assert {v.name for v in plasma_drive_peak_intensity.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_pulse_duration",
        "physical.lithography.source_plasma_drive_pulse_fluence",
        "physical.lithography.source_plasma_drive_pulse_temporal_shape_factor",
    }
    assert plasma_drive_focus_waist_coefficient.direct_dependencies() == set()
    assert {v.name for v in plasma_drive_beam_wavelength.direct_dependencies()} == {
        "physical.lithography.source_ionization_energy",
        "physical.lithography.source_plasma_drive_edge_detuning_ratio",
        "physics.hbar",
        "physics.speed_of_light",
    }
    assert {v.name for v in plasma_drive_acceptance_half_angle.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_objective_focal_length",
        "physical.lithography.source_plasma_drive_objective_pupil_radius",
    }
    assert {v.name for v in plasma_drive_numerical_aperture.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_acceptance_half_angle",
    }
    assert {v.name for v in plasma_drive_focus_f_number.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_acceptance_half_angle",
    }
    assert {
        v.name for v in plasma_drive_beam_parameter_waist_radius.direct_dependencies()
    } == {
        "physical.lithography.source_plasma_drive_objective_pupil_radius",
        "physical.lithography.source_plasma_drive_pupil_beam_fill_factor",
    }
    assert {v.name for v in plasma_drive_beam_parameter_product.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_beam_parameter_waist_radius",
        "physical.lithography.source_plasma_drive_far_field_divergence_half_angle",
    }
    assert {
        v.name
        for v in plasma_drive_beam_parameter_product.direct_dependencies(
            include_constraints=True
        )
    } == {
        "physical.lithography.source_plasma_drive_beam_parameter_waist_radius",
        "physical.lithography.source_plasma_drive_far_field_divergence_half_angle",
        "physical.lithography.source_plasma_drive_beam_wavelength",
    }
    beam_parameter_product_floor = plasma_drive_beam_parameter_product.constraints()[0]
    assert isinstance(beam_parameter_product_floor, Inequality)
    assert beam_parameter_product_floor.name == (
        "physical.ineq.lithography_source_plasma_drive_beam_parameter_product_diffraction_floor"
    )
    assert beam_parameter_product_floor.role is RelationRole.CONSTRAINT
    assert beam_parameter_product_floor.op == ">="
    assert isinstance(beam_parameter_product_floor.as_sympy(), sp.Rel)
    assert beam_parameter_product_floor.references
    assert getattr(beam_parameter_product_floor, "_check_units_flag", False)
    assert {v.name for v in plasma_drive_beam_quality_factor.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_beam_parameter_product",
        "physical.lithography.source_plasma_drive_beam_wavelength",
    }
    assert {
        v.name
        for v in plasma_drive_beam_quality_factor.direct_dependencies(
            include_constraints=True
        )
    } == {
        "physical.lithography.source_plasma_drive_beam_parameter_product",
        "physical.lithography.source_plasma_drive_beam_wavelength",
    }
    beam_quality_factor_floor = plasma_drive_beam_quality_factor.constraints()[0]
    assert isinstance(beam_quality_factor_floor, Inequality)
    assert beam_quality_factor_floor.name == (
        "physical.ineq.lithography_source_plasma_drive_beam_quality_factor_diffraction_limit"
    )
    assert beam_quality_factor_floor.role is RelationRole.CONSTRAINT
    assert beam_quality_factor_floor.op == ">="
    assert isinstance(beam_quality_factor_floor.as_sympy(), sp.Rel)
    assert beam_quality_factor_floor.references
    assert getattr(beam_quality_factor_floor, "_check_units_flag", False)
    assert {v.name for v in plasma_drive_spot_radius.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_beam_quality_factor",
        "physical.lithography.source_plasma_drive_beam_wavelength",
        "physical.lithography.source_plasma_drive_focus_f_number",
        "physical.lithography.source_plasma_drive_focus_waist_coefficient",
    }
    assert {v.name for v in plasma_drive_rayleigh_range.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_beam_quality_factor",
        "physical.lithography.source_plasma_drive_beam_wavelength",
        "physical.lithography.source_plasma_drive_spot_radius",
    }
    assert {v.name for v in plasma_drive_confocal_length.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_rayleigh_range",
    }
    assert {v.name for v in plasma_drive_spot_shape_factor.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_spot_area_fill_factor",
        "physical.lithography.source_plasma_drive_spot_axis_ratio",
    }
    assert not plasma_drive_spot_axis_ratio.direct_dependencies()
    assert not plasma_drive_spot_area_fill_factor.direct_dependencies()
    assert {v.name for v in plasma_drive_spot_area.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_spot_radius",
        "physical.lithography.source_plasma_drive_spot_shape_factor",
    }
    assert {v.name for v in plasma_pulse_energy.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_peak_intensity",
        "physical.lithography.source_plasma_drive_pulse_duration",
        "physical.lithography.source_plasma_drive_pulse_temporal_shape_factor",
        "physical.lithography.source_plasma_drive_spot_area",
    }
    assert {v.name for v in plasma_drive_power.direct_dependencies()} == {
        "physical.lithography.source_plasma_pulse_energy",
        "physical.lithography.source_plasma_pulse_repetition_rate",
    }
    assert {v.name for v in plasma_species_number_density.direct_dependencies()} == {
        "physical.lithography.source_plasma_species_partial_pressure",
        "physical.lithography.source_plasma_species_gas_temperature",
        "physics.boltzmann",
    }
    assert not plasma_column_expansion_speed_factor.direct_dependencies()
    assert {v.name for v in plasma_column_radial_expansion_speed.direct_dependencies()} == {
        "physical.lithography.source_plasma_column_expansion_speed_factor",
        "physical.lithography.source_plasma_species_thermal_speed",
    }
    assert {
        v.name for v in plasma_column_radius_expansion_factor.direct_dependencies()
    } == {
        "physical.lithography.source_plasma_column_radial_expansion_speed",
        "physical.lithography.source_plasma_drive_pulse_duration",
        "physical.lithography.source_plasma_drive_spot_radius",
    }
    assert {v.name for v in plasma_column_radius.direct_dependencies()} == {
        "physical.lithography.source_plasma_column_radius_expansion_factor",
        "physical.lithography.source_plasma_drive_spot_radius",
    }
    assert {v.name for v in plasma_column_aspect_ratio.direct_dependencies()} == {
        "physical.lithography.source_plasma_column_radius",
        "physical.lithography.source_plasma_drive_confocal_length",
    }
    assert {v.name for v in plasma_column_length.direct_dependencies()} == {
        "physical.lithography.source_plasma_column_aspect_ratio",
        "physical.lithography.source_plasma_column_radius",
    }
    assert plasma_active_fill_factor.direct_dependencies() == set()
    assert {v.name for v in plasma_active_volume.direct_dependencies()} == {
        "physical.lithography.source_plasma_column_radius",
        "physical.lithography.source_plasma_column_length",
        "physical.lithography.source_plasma_active_fill_factor",
    }
    assert {v.name for v in plasma_absorption_path_direction_cosine.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_acceptance_half_angle",
    }
    assert {v.name for v in plasma_absorption_path_shape_factor.direct_dependencies()} == {
        "physical.lithography.source_plasma_absorption_path_direction_cosine",
    }
    assert {v.name for v in plasma_absorption_path_length.direct_dependencies()} == {
        "physical.lithography.source_plasma_absorption_path_shape_factor",
        "physical.lithography.source_plasma_column_length",
    }
    assert {v.name for v in plasma_drive_beam_angular_frequency.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_beam_wavelength",
        "physics.speed_of_light",
    }
    assert {v.name for v in plasma_absorption_resonance_to_drive_ratio.direct_dependencies()} == {
        "physical.lithography.source_ionization_energy",
        "physical.lithography.source_plasma_drive_beam_angular_frequency",
        "physics.hbar",
    }
    assert {v.name for v in plasma_absorption_quality_factor.direct_dependencies()} == {
        "physical.lithography.source_plasma_absorption_damping_rate",
        "physical.lithography.source_plasma_absorption_resonance_angular_frequency",
    }
    assert {
        v.name for v in plasma_absorption_collision_orbital_radius.direct_dependencies()
    } == {
        "physical.lithography.source_ionization_effective_nuclear_charge",
        "physical.lithography.source_ionization_principal_quantum_number",
        "physics.bohr_radius",
    }
    assert {v.name for v in plasma_absorption_collision_cross_section.direct_dependencies()} == {
        "physical.lithography.source_plasma_absorption_collision_orbital_radius",
    }
    assert {
        v.name for v in plasma_absorption_participating_electron_fraction.direct_dependencies()
    } == {
        "physical.lithography.source_ionization_same_shell_screening_electron_count",
        "physical.lithography.source_proton_count",
    }
    assert {v.name for v in plasma_absorption_sum_rule_fraction.direct_dependencies()} == {
        "physical.lithography.source_ionization_same_shell_screening_electron_count",
        "physical.lithography.source_transition_shell_capacity",
    }
    assert {v.name for v in plasma_absorption_resonance.direct_dependencies()} == {
        "physical.lithography.source_plasma_absorption_resonance_to_drive_ratio",
        "physical.lithography.source_plasma_drive_beam_angular_frequency",
    }
    assert {v.name for v in plasma_absorption_damping_rate.direct_dependencies()} == {
        "physical.lithography.source_plasma_absorption_collision_cross_section",
        "physical.lithography.source_plasma_species_number_density",
        "physical.lithography.source_plasma_species_thermal_speed",
    }
    assert {
        v.name for v in plasma_absorption_oscillator_strength.direct_dependencies()
    } == {
        "physical.lithography.source_plasma_absorption_participating_electron_fraction",
        "physical.lithography.source_plasma_absorption_sum_rule_fraction",
        "physical.lithography.source_proton_count",
    }
    assert {v.name for v in plasma_absorption_cross_section.direct_dependencies()} == {
        "physical.lithography.source_plasma_absorption_damping_rate",
        "physical.lithography.source_plasma_absorption_oscillator_strength",
        "physical.lithography.source_plasma_absorption_resonance_angular_frequency",
        "physical.lithography.source_plasma_drive_beam_angular_frequency",
        "physics.elementary_charge",
        "physics.electron_mass",
        "physics.speed_of_light",
        "physics.vacuum_permittivity",
    }
    assert {v.name for v in plasma_absorption_optical_depth.direct_dependencies()} == {
        "physical.lithography.source_plasma_species_number_density",
        "physical.lithography.source_plasma_absorption_cross_section",
        "physical.lithography.source_plasma_absorption_path_length",
    }
    assert {
        v.name for v in plasma_drive_energy_absorption_fraction.direct_dependencies()
    } == {
        "physical.lithography.source_plasma_absorption_optical_depth",
    }
    assert {
        v.name for v in plasma_drive_pointing_overlap_factor.direct_dependencies()
    } == {
        "physical.lithography.source_plasma_drive_centroid_offset_to_column_radius_ratio",
    }
    assert (
        plasma_drive_centroid_offset_to_column_radius_ratio.direct_dependencies()
        == set()
    )
    assert {
        v.name for v in plasma_drive_transverse_overlap_factor.direct_dependencies()
    } == {
        "physical.lithography.source_plasma_column_radius",
        "physical.lithography.source_plasma_drive_spot_area",
    }
    assert {v.name for v in plasma_drive_spatial_overlap_factor.direct_dependencies()} == {
        "physical.lithography.source_plasma_active_fill_factor",
        "physical.lithography.source_plasma_drive_pointing_overlap_factor",
        "physical.lithography.source_plasma_drive_transverse_overlap_factor",
    }
    assert {
        v.name for v in plasma_active_lifetime_to_drive_pulse_ratio.direct_dependencies()
    } == {
        "physical.lithography.source_plasma_drive_pulse_duration",
        "physical.lithography.source_plasma_energy_confinement_time",
    }
    assert {v.name for v in plasma_active_response_duration.direct_dependencies()} == {
        "physical.lithography.source_plasma_active_lifetime_to_drive_pulse_ratio",
        "physical.lithography.source_plasma_drive_pulse_duration",
    }
    assert plasma_drive_timing_offset_fraction.direct_dependencies() == set()
    assert {v.name for v in plasma_drive_timing_offset_duration.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_pulse_duration",
        "physical.lithography.source_plasma_drive_timing_offset_fraction",
    }
    assert {
        v.name for v in plasma_drive_temporal_duration_match_factor.direct_dependencies()
    } == {
        "physical.lithography.source_plasma_active_response_duration",
        "physical.lithography.source_plasma_drive_pulse_duration",
    }
    assert {
        v.name for v in plasma_drive_temporal_alignment_factor.direct_dependencies()
    } == {
        "physical.lithography.source_plasma_active_response_duration",
        "physical.lithography.source_plasma_drive_pulse_duration",
        "physical.lithography.source_plasma_drive_timing_offset_duration",
    }
    assert {v.name for v in plasma_drive_temporal_overlap_factor.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_temporal_alignment_factor",
        "physical.lithography.source_plasma_drive_temporal_duration_match_factor",
    }
    assert {v.name for v in plasma_drive_overlap_factor.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_spatial_overlap_factor",
        "physical.lithography.source_plasma_drive_temporal_overlap_factor",
    }
    assert {v.name for v in plasma_absorption_efficiency.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_overlap_factor",
        "physical.lithography.source_plasma_drive_energy_absorption_fraction",
        "physical.lithography.source_plasma_electron_heating_fraction",
    }
    assert {v.name for v in plasma_absorbed_power.direct_dependencies()} == {
        "physical.lithography.source_plasma_absorption_efficiency",
        "physical.lithography.source_plasma_drive_power",
    }
    assert {v.name for v in plasma_energy_loss_path_direction_cosine.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_acceptance_half_angle",
    }
    assert {v.name for v in plasma_energy_loss_path_factor.direct_dependencies()} == {
        "physical.lithography.source_plasma_energy_loss_path_direction_cosine",
    }
    assert {v.name for v in plasma_energy_loss_path_length.direct_dependencies()} == {
        "physical.lithography.source_plasma_energy_loss_path_factor",
        "physical.lithography.source_plasma_column_radius",
    }
    assert {v.name for v in plasma_species_particle_mass.direct_dependencies()} == {
        "physical.lithography.source_neutron_count",
        "physical.lithography.source_proton_count",
        "physics.neutron_mass",
        "physics.proton_mass",
    }
    assert {v.name for v in plasma_species_thermal_speed.direct_dependencies()} == {
        "physical.lithography.source_plasma_species_gas_temperature",
        "physical.lithography.source_plasma_species_particle_mass",
        "physics.boltzmann",
    }
    assert {
        v.name for v in plasma_energy_loss_transport_speed_factor.direct_dependencies()
    } == {
        "physical.lithography.source_plasma_species_particle_mass",
        "physics.electron_mass",
    }
    assert [e.name for e in plasma_drive_spot_axis_ratio.approximations()] == [
        "physical.eq.lithography_source_plasma_drive_spot_axis_ratio_from_circular_convention",
    ]
    assert [e.name for e in plasma_drive_spot_area_fill_factor.approximations()] == [
        "physical.eq.lithography_source_plasma_drive_spot_area_fill_factor_from_full_area_convention",
    ]
    assert [e.name for e in plasma_drive_rayleigh_range.approximations()] == [
        "physical.eq.lithography_source_plasma_drive_rayleigh_range_from_spot_geometry",
    ]
    assert [e.name for e in plasma_drive_confocal_length.approximations()] == [
        "physical.eq.lithography_source_plasma_drive_confocal_length_from_rayleigh_range",
    ]
    assert [e.name for e in plasma_column_expansion_speed_factor.approximations()] == [
        "physical.eq.lithography_source_plasma_column_expansion_speed_factor_from_monatomic_sound_speed",
    ]
    assert [e.name for e in plasma_column_aspect_ratio.approximations()] == [
        "physical.eq.lithography_source_plasma_column_aspect_ratio_from_confocal_length",
    ]
    active_fill_eq = plasma_active_fill_factor.approximations()[0]
    assert active_fill_eq.name == (
        "physical.eq.lithography_source_plasma_active_fill_factor_from_ideal_column_convention"
    )
    assert active_fill_eq.rhs == sp.Integer(1)
    assert [e.name for e in plasma_absorption_collision_orbital_radius.approximations()] == [
        "physical.eq.lithography_source_plasma_absorption_collision_orbital_radius_from_hydrogenic_shell",
    ]
    assert [e.name for e in plasma_absorption_collision_cross_section.approximations()] == [
        "physical.eq.lithography_source_plasma_absorption_collision_cross_section_from_orbital_area",
    ]
    centroid_offset_eq = (
        plasma_drive_centroid_offset_to_column_radius_ratio.approximations()[0]
    )
    assert centroid_offset_eq.name == (
        "physical.eq.lithography_source_plasma_drive_centroid_offset_to_column_radius_ratio_from_coaxial_convention"
    )
    assert centroid_offset_eq.rhs == sp.Integer(0)
    timing_offset_eq = plasma_drive_timing_offset_fraction.approximations()[0]
    assert timing_offset_eq.name == (
        "physical.eq.lithography_source_plasma_drive_timing_offset_fraction_from_synchronized_convention"
    )
    assert timing_offset_eq.rhs == sp.Integer(0)
    assert {v.name for v in plasma_energy_loss_speed.direct_dependencies()} == {
        "physical.lithography.source_plasma_energy_loss_transport_speed_factor",
        "physical.lithography.source_plasma_species_thermal_speed",
    }
    assert {v.name for v in plasma_confinement_time.direct_dependencies()} == {
        "physical.lithography.source_plasma_energy_loss_path_length",
        "physical.lithography.source_plasma_energy_loss_speed",
    }
    assert {v.name for v in plasma_free_electron_yield.direct_dependencies()} == {
        "physical.lithography.source_plasma_free_electron_inventory_charge_fraction",
        "physical.lithography.source_proton_count",
    }
    assert {v.name for v in plasma_free_electron_count.direct_dependencies()} == {
        "physical.lithography.source_plasma_species_number_density",
        "physical.lithography.source_plasma_active_volume",
        "physical.lithography.source_plasma_free_electron_yield_per_source_particle",
    }
    assert {v.name for v in plasma_internal_energy.direct_dependencies()} == {
        "physical.lithography.source_plasma_absorbed_power",
        "physical.lithography.source_plasma_energy_confinement_time",
    }
    assert {v.name for v in plasma_temperature.direct_dependencies()} == {
        "physical.lithography.source_plasma_electron_internal_energy",
        "physical.lithography.source_plasma_free_electron_count",
        "physics.boltzmann",
    }
    assert {v.name for v in plasma_density.direct_dependencies()} == {
        "physical.lithography.source_plasma_active_volume",
        "physical.lithography.source_plasma_free_electron_count",
    }
    assert {v.name for v in plasma_mean_energy.direct_dependencies()} == {
        "physical.lithography.source_plasma_electron_temperature",
        "physics.boltzmann",
    }
    assert {v.name for v in plasma_debye_length.direct_dependencies()} == {
        "physical.lithography.source_plasma_electron_number_density",
        "physical.lithography.source_plasma_electron_temperature",
        "physics.boltzmann",
        "physics.elementary_charge",
        "physics.vacuum_permittivity",
    }
    assert {v.name for v in saha_thermal_density.direct_dependencies()} == {
        "physical.lithography.source_plasma_electron_temperature",
        "physics.boltzmann",
        "physics.electron_mass",
        "physics.planck",
    }
    assert {v.name for v in saha_ratio.direct_dependencies()} == {
        "physical.lithography.source_ionization_energy",
        "physical.lithography.source_ionization_partition_ratio",
        "physical.lithography.source_plasma_electron_number_density",
        "physical.lithography.source_plasma_electron_temperature",
        "physical.lithography.source_saha_thermal_number_density",
        "physics.boltzmann",
    }
    assert {v.name for v in saha_fraction.direct_dependencies()} == {
        "physical.lithography.source_saha_ionization_ratio",
    }
    assert {v.name for v in ion_charge_state.direct_dependencies()} == {
        "physical.lithography.source_proton_count",
        "physical.lithography.source_saha_ionization_fraction",
    }
    assert {v.name for v in bound_electrons.direct_dependencies()} == {
        "physical.lithography.source_proton_count",
        "physical.lithography.source_ion_charge_state",
    }
    assert {v.name for v in lower_principal.direct_dependencies()} == {
        "physical.lithography.source_proton_count",
    }
    assert {v.name for v in upper_principal.direct_dependencies()} == {
        "physical.lithography.source_lower_principal_quantum_number",
        "physical.lithography.source_transition_principal_quantum_step",
    }
    assert {v.name for v in transition_step.direct_dependencies()} == set()
    assert {v.name for v in shell_capacity.direct_dependencies()} == {
        "physical.lithography.source_lower_principal_quantum_number",
    }
    assert {v.name for v in inner_closed_capacity.direct_dependencies()} == {
        "physical.lithography.source_lower_principal_quantum_number",
    }
    assert {v.name for v in inner_closed_shells.direct_dependencies()} == {
        "physical.lithography.source_bound_electron_count",
        "physical.lithography.source_inner_closed_shell_capacity",
        "physical.lithography.source_outer_shell_electron_count",
    }
    assert {v.name for v in outer_shells.direct_dependencies()} == {
        "physical.lithography.source_bound_electron_count",
        "physical.lithography.source_inner_closed_shell_capacity",
        "physical.lithography.source_transition_shell_capacity",
    }
    assert {v.name for v in transition_shell_occupancy.direct_dependencies()} == {
        "physical.lithography.source_bound_electron_count",
        "physical.lithography.source_inner_closed_shell_electron_count",
        "physical.lithography.source_outer_shell_electron_count",
        "physical.lithography.source_transition_shell_capacity",
    }
    assert {v.name for v in same_screeners.direct_dependencies()} == {
        "physical.lithography.source_transition_shell_occupancy",
        "physical.lithography.source_transition_shell_capacity",
    }
    assert {v.name for v in inner_screeners.direct_dependencies()} == {
        "physical.lithography.source_bound_electron_count",
        "physical.lithography.source_transition_shell_occupancy",
        "physical.lithography.source_outer_shell_electron_count",
    }
    assert {v.name for v in inner_shielding.direct_dependencies()} == set()
    assert {v.name for v in same_shielding.direct_dependencies()} == set()
    assert {v.name for v in screening.direct_dependencies()} == {
        "physical.lithography.source_bound_electron_count",
        "physical.lithography.source_inner_shell_screening_electron_count",
        "physical.lithography.source_same_shell_screening_electron_count",
        "physical.lithography.source_inner_shell_shielding_factor",
        "physical.lithography.source_same_shell_shielding_factor",
    }
    assert {v.name for v in z_eff.direct_dependencies()} == {
        "physical.lithography.source_proton_count",
        "physical.lithography.source_screening_constant",
    }
    assert {v.name for v in transition.direct_dependencies()} == {
        "physical.lithography.source_reduced_mass_ratio",
        "physical.lithography.source_effective_nuclear_charge",
        "physical.lithography.source_lower_principal_quantum_number",
        "physical.lithography.source_upper_principal_quantum_number",
        "physics.rydberg_energy",
    }

    ionization_principal_result = resolve(
        "physical.lithography.source_ionization_principal_quantum_number",
        assignments={
            "physical.lithography.source_lower_principal_quantum_number": 3,
        },
    )
    assert float(ionization_principal_result.value) == pytest.approx(3.0)

    proton_count_result = resolve(
        "physical.lithography.source_proton_count",
        assignments=source_quark_assignments(3, 4),
    )
    assert float(proton_count_result.value) == pytest.approx(3.0)
    assert [step.equation for step in proton_count_result.trace] == [
        "physical.eq.lithography_source_proton_count_from_valence_quarks",
    ]
    proton_feasibility_eq = Registry.equations[
        "physical.ineq.lithography_source_valence_quarks_imply_nonnegative_protons"
    ]
    positive_proton_feasibility_eq = Registry.equations[
        "physical.ineq.lithography_source_valence_quarks_imply_positive_protons"
    ]
    assert isinstance(proton_feasibility_eq, Inequality)
    assert isinstance(positive_proton_feasibility_eq, Inequality)
    assert proton_feasibility_eq.role is RelationRole.CONSTRAINT
    assert positive_proton_feasibility_eq.role is RelationRole.CONSTRAINT
    assert isinstance(proton_feasibility_eq.as_sympy(), sp.Rel)
    assert isinstance(positive_proton_feasibility_eq.as_sympy(), sp.Rel)
    assert not proton_feasibility_eq.is_trivially_true()
    assert not positive_proton_feasibility_eq.is_trivially_true()
    assert proton_feasibility_eq.references
    assert positive_proton_feasibility_eq.references
    assert getattr(proton_feasibility_eq, "_check_units_flag", False)
    assert getattr(positive_proton_feasibility_eq, "_check_units_flag", False)
    proton_feasibility = next(
        c for c in proton_count_result.constraints
        if c.equation == proton_feasibility_eq.name
    )
    assert proton_feasibility.satisfied is True
    positive_proton_feasibility = next(
        c for c in proton_count_result.constraints
        if c.equation == positive_proton_feasibility_eq.name
    )
    assert positive_proton_feasibility.satisfied is True
    triplet_integrality_eq = Registry.equations[
        "physical.eq.lithography_source_valence_quark_triplet_integrality"
    ]
    assert triplet_integrality_eq.role is RelationRole.CONSTRAINT
    assert isinstance(triplet_integrality_eq.as_sympy(), sp.Equality)
    assert triplet_integrality_eq.as_sympy() is not sp.S.true
    assert triplet_integrality_eq.references
    assert getattr(triplet_integrality_eq, "_check_units_flag", False)
    triplet_integrality = next(
        c for c in proton_count_result.constraints
        if c.equation == triplet_integrality_eq.name
    )
    assert triplet_integrality.satisfied is True
    neutron_count_result = resolve(
        "physical.lithography.source_neutron_count",
        assignments=source_quark_assignments(3, 4),
    )
    assert float(neutron_count_result.value) == pytest.approx(4.0)
    assert [step.equation for step in neutron_count_result.trace] == [
        "physical.eq.lithography_source_neutron_count_from_valence_quarks",
    ]
    neutron_feasibility_eq = Registry.equations[
        "physical.ineq.lithography_source_valence_quarks_imply_nonnegative_neutrons"
    ]
    assert isinstance(neutron_feasibility_eq, Inequality)
    assert neutron_feasibility_eq.role is RelationRole.CONSTRAINT
    assert isinstance(neutron_feasibility_eq.as_sympy(), sp.Rel)
    assert not neutron_feasibility_eq.is_trivially_true()
    assert neutron_feasibility_eq.references
    assert getattr(neutron_feasibility_eq, "_check_units_flag", False)
    neutron_feasibility = next(
        c for c in neutron_count_result.constraints
        if c.equation == neutron_feasibility_eq.name
    )
    assert neutron_feasibility.satisfied is True

    invalid_proton_result = resolve(
        "physical.lithography.source_proton_count",
        assignments={
            "physical.lithography.source_valence_up_quark_count": 1,
            "physical.lithography.source_valence_down_quark_count": 5,
        },
    )
    assert float(invalid_proton_result.value) == pytest.approx(-1.0)
    invalid_proton_feasibility = next(
        c for c in invalid_proton_result.constraints
        if c.equation == proton_feasibility_eq.name
    )
    assert invalid_proton_feasibility.satisfied is False

    zero_proton_result = resolve(
        "physical.lithography.source_proton_count",
        assignments=source_quark_assignments(0, 1),
    )
    assert float(zero_proton_result.value) == pytest.approx(0.0)
    zero_positive_proton_feasibility = next(
        c for c in zero_proton_result.constraints
        if c.equation == positive_proton_feasibility_eq.name
    )
    assert zero_positive_proton_feasibility.satisfied is False

    invalid_neutron_result = resolve(
        "physical.lithography.source_neutron_count",
        assignments={
            "physical.lithography.source_valence_up_quark_count": 5,
            "physical.lithography.source_valence_down_quark_count": 1,
        },
    )
    assert float(invalid_neutron_result.value) == pytest.approx(-1.0)
    invalid_neutron_feasibility = next(
        c for c in invalid_neutron_result.constraints
        if c.equation == neutron_feasibility_eq.name
    )
    assert invalid_neutron_feasibility.satisfied is False

    fractional_triplet_result = resolve(
        "physical.lithography.source_proton_count",
        assignments={
            "physical.lithography.source_valence_up_quark_count": 1,
            "physical.lithography.source_valence_down_quark_count": 1,
        },
    )
    assert float(fractional_triplet_result.value) == pytest.approx(1.0 / 3.0)
    fractional_triplet_constraint = next(
        c for c in fractional_triplet_result.constraints
        if c.equation == triplet_integrality_eq.name
    )
    assert fractional_triplet_constraint.satisfied is False
    fractional_down_root_result = resolve(
        "physical.lithography.source_valence_down_quark_count",
        assignments={
            "physical.lithography.source_valence_up_quark_count": 1,
            "physical.lithography.source_valence_down_quark_count": 1,
        },
    )
    assert float(fractional_down_root_result.value) == pytest.approx(1.0)
    fractional_down_triplet_constraint = next(
        c for c in fractional_down_root_result.constraints
        if c.equation == triplet_integrality_eq.name
    )
    assert fractional_down_triplet_constraint.satisfied is False
    assert [
        c.equation for c in fractional_down_root_result.constraints
    ].count(triplet_integrality_eq.name) == 1

    isotope_descriptor_result = resolve(
        "physical.lithography.source_isotope_mass_number",
        assignments=source_quark_assignments(3, 4),
    )
    assert float(isotope_descriptor_result.value) == pytest.approx(7.0)
    isotope_descriptor_trace = [
        step.equation for step in isotope_descriptor_result.trace
    ]
    assert set(isotope_descriptor_trace[:2]) == {
        "physical.eq.lithography_source_neutron_count_from_valence_quarks",
        "physical.eq.lithography_source_proton_count_from_valence_quarks",
    }
    assert isotope_descriptor_trace[2:] == [
        "physical.eq.lithography_source_isotope_mass_number",
    ]
    assert (
        Registry.equations[
            "physical.eq.lithography_source_isotope_mass_number"
        ].role
        is RelationRole.APPROXIMATION
    )
    atomic_descriptor_result = resolve(
        "physical.lithography.source_atomic_number",
        assignments=source_quark_assignments(3, 0),
    )
    assert float(atomic_descriptor_result.value) == pytest.approx(3.0)
    assert [step.equation for step in atomic_descriptor_result.trace] == [
        "physical.eq.lithography_source_proton_count_from_valence_quarks",
        "physical.eq.lithography_source_atomic_number",
    ]
    assert (
        Registry.equations["physical.eq.lithography_source_atomic_number"].role
        is RelationRole.IDENTITY
    )

    for atomic_number_value, expected_shell in (
        (1, 1),
        (2, 1),
        (3, 2),
        (10, 2),
        (11, 3),
        (28, 3),
        (29, 4),
        (60, 4),
        (61, 5),
        (110, 5),
        (111, 6),
        (182, 6),
        (183, 7),
        (280, 7),
    ):
        lower_shell_result = resolve(
            "physical.lithography.source_lower_principal_quantum_number",
            assignments=source_quark_assignments(atomic_number_value, 0),
        )
        assert float(lower_shell_result.value) == pytest.approx(expected_shell)
    lower_shell_eq = Registry.equations[
        "physical.eq.lithography_source_lower_principal_quantum_number"
    ]
    assert "Z_litho_src > 0" in str(lower_shell_eq.validity)
    assert "Z_litho_src <= 280" in str(lower_shell_eq.validity)

    inner_shielding_eq = Registry.equations[
        "physical.eq.lithography_source_inner_shell_shielding_factor"
    ]
    same_shielding_eq = Registry.equations[
        "physical.eq.lithography_source_same_shell_shielding_factor"
    ]
    assert inner_shielding.approximations() == [inner_shielding_eq]
    assert same_shielding.approximations() == [same_shielding_eq]
    assert inner_shielding_eq.role is RelationRole.APPROXIMATION
    assert same_shielding_eq.role is RelationRole.APPROXIMATION
    assert inner_shielding_eq.rhs == sp.Integer(1)
    assert same_shielding_eq.rhs == sp.Rational(1, 2)

    upper_shell_result = resolve(
        "physical.lithography.source_upper_principal_quantum_number",
        assignments=source_quark_assignments(8, 0),
    )
    assert float(upper_shell_result.value) == pytest.approx(3.0)

    ionization_screening_result = resolve(
        "physical.lithography.source_ionization_screening_constant",
        assignments=source_quark_assignments(4, 0),
    )
    assert float(ionization_screening_result.value) == pytest.approx(2.5)
    assert float(ionization_screening_result.values[
        "physical.lithography.source_ionization_inner_shell_screening_electron_count"
    ]) == pytest.approx(2.0)
    assert float(ionization_screening_result.values[
        "physical.lithography.source_ionization_same_shell_screening_electron_count"
    ]) == pytest.approx(1.0)
    ionization_screening_trace = {
        step.equation for step in ionization_screening_result.trace
    }
    assert "physical.eq.lithography_source_saha_ionization_ratio" not in ionization_screening_trace
    assert "physical.eq.lithography_source_ion_charge_state" not in ionization_screening_trace

    electron_mass = Registry.variables["physics.electron_mass"].value
    boltzmann = Registry.variables["physics.boltzmann"].value
    proton_mass = Registry.variables["physics.proton_mass"].value
    rydberg_energy = Registry.variables["physics.rydberg_energy"].value
    planck = Registry.variables["physics.planck"].value
    hbar = Registry.variables["physics.hbar"].value
    c = Registry.variables["physics.speed_of_light"].value
    elementary_charge = Registry.variables["physics.elementary_charge"].value
    vacuum_permittivity = Registry.variables["physics.vacuum_permittivity"].value
    bohr_radius = Registry.variables["physics.bohr_radius"].value
    test_coulomb_coeff = 0.5
    test_volume_coeff = 10.0
    test_surface_coeff = 2.0
    test_asymmetry_coeff = 3.0
    test_radius_coeff = (
        3.0
        * elementary_charge**2
        / (20.0 * float(sp.pi) * vacuum_permittivity * test_coulomb_coeff)
    )
    test_saturation_density = 3.0 / (
        4.0 * float(sp.pi) * test_radius_coeff**3
    )
    test_bulk_binding_density = 10.0 * test_saturation_density
    test_surface_tension = 2.0 / (
        4.0 * float(sp.pi) * test_radius_coeff**2
    )
    test_symmetry_density = 3.0 * test_saturation_density
    test_pairing_gap_ref = 1.0
    test_plasma_temperature = 10000.0
    test_plasma_absorption_efficiency = 0.05
    test_plasma_pulse_period = 1.0e-9
    test_plasma_pulse_repetition_rate = 1.0 / test_plasma_pulse_period
    test_plasma_drive_pulse_duration = 1.0e-12
    test_plasma_drive_pulse_duty_factor = (
        test_plasma_drive_pulse_duration / test_plasma_pulse_period
    )
    test_plasma_drive_pulse_rise_fraction = 0.0
    test_plasma_drive_pulse_fall_fraction = test_plasma_drive_pulse_rise_fraction
    test_plasma_drive_pulse_flat_fraction = (
        1.0
        - test_plasma_drive_pulse_rise_fraction
        - test_plasma_drive_pulse_fall_fraction
    )
    test_plasma_drive_pulse_temporal_shape_factor = (
        test_plasma_drive_pulse_flat_fraction
        + 0.5
        * (
            test_plasma_drive_pulse_rise_fraction
            + test_plasma_drive_pulse_fall_fraction
        )
    )
    test_plasma_drive_energy_absorption_fraction = 0.8
    test_plasma_absorption_optical_depth = -float(
        sp.log(1.0 - test_plasma_drive_energy_absorption_fraction)
    )
    test_plasma_species_gas_temperature = 1000.0
    test_plasma_species_particle_mass = proton_mass
    test_plasma_species_thermal_speed = (
        boltzmann
        * test_plasma_species_gas_temperature
        / test_plasma_species_particle_mass
    ) ** 0.5
    test_plasma_column_expansion_speed_factor = (5.0 / 3.0) ** 0.5
    test_plasma_column_radial_expansion_speed = (
        test_plasma_column_expansion_speed_factor
        * test_plasma_species_thermal_speed
    )
    test_plasma_free_electron_yield = 0.25
    test_plasma_free_electron_inventory_charge_fraction = test_plasma_free_electron_yield
    test_saha_thermal_density = (
        2.0
        * (
            2.0
            * float(sp.pi)
            * electron_mass
            * boltzmann
            * test_plasma_temperature
            / planck**2
        ) ** 1.5
    )
    test_saha_thermal_to_electron_density_ratio = 3.0
    test_plasma_electron_number_density = (
        test_saha_thermal_density
        / test_saha_thermal_to_electron_density_ratio
    )
    test_plasma_species_number_density = (
        test_plasma_electron_number_density
        / test_plasma_free_electron_yield
    )
    test_plasma_species_partial_pressure = (
        test_plasma_species_number_density
        * boltzmann
        * test_plasma_species_gas_temperature
    )
    plasma_source_root_assignments = {
        "physical.lithography.source_plasma_pulse_period": test_plasma_pulse_period,
        "physical.lithography.source_plasma_species_partial_pressure": test_plasma_species_partial_pressure,
        "physical.lithography.source_plasma_species_gas_temperature": test_plasma_species_gas_temperature,
        "physical.lithography.source_plasma_free_electron_inventory_charge_fraction": test_plasma_free_electron_inventory_charge_fraction,
    }
    test_mean_electron_kinetic_energy = 1.5 * boltzmann * test_plasma_temperature
    test_plasma_active_fill_factor = 0.5
    test_plasma_drive_focus_f_number = 1.0
    test_plasma_drive_objective_focal_length = 1.0
    test_plasma_drive_objective_pupil_radius = (
        test_plasma_drive_objective_focal_length
        / (2.0 * test_plasma_drive_focus_f_number)
    )
    test_plasma_drive_acceptance_half_angle = float(
        sp.atan(
            test_plasma_drive_objective_pupil_radius
            / test_plasma_drive_objective_focal_length
        )
    )
    test_plasma_drive_numerical_aperture = float(
        sp.sin(test_plasma_drive_acceptance_half_angle)
    )
    test_plasma_drive_pupil_beam_fill_factor = 0.25
    test_plasma_drive_beam_quality_factor = 1.0
    test_plasma_drive_focus_waist_coefficient = 2.0 / float(sp.pi)
    test_plasma_drive_spot_radius = 1.0e-6
    test_plasma_column_radius = (
        test_plasma_drive_spot_radius
        + test_plasma_column_radial_expansion_speed
        * test_plasma_drive_pulse_duration
    )
    test_plasma_column_radius_expansion_factor = (
        test_plasma_column_radius
        / test_plasma_drive_spot_radius
    )
    test_plasma_drive_beam_wavelength = (
        test_plasma_drive_spot_radius
        / (
            test_plasma_drive_focus_waist_coefficient
            * test_plasma_drive_beam_quality_factor
            * test_plasma_drive_focus_f_number
        )
    )
    test_plasma_drive_rayleigh_range = (
        float(sp.pi)
        * test_plasma_drive_spot_radius**2
        / (
            test_plasma_drive_beam_quality_factor
            * test_plasma_drive_beam_wavelength
        )
    )
    test_plasma_drive_confocal_length = 2.0 * test_plasma_drive_rayleigh_range
    test_plasma_column_length = test_plasma_drive_confocal_length
    test_plasma_column_aspect_ratio = (
        test_plasma_column_length
        / test_plasma_column_radius
    )
    test_plasma_active_volume = (
        float(sp.pi)
        * test_plasma_column_radius**2
        * test_plasma_column_length
        * test_plasma_active_fill_factor
    )
    test_plasma_free_electron_count = (
        test_plasma_species_number_density
        * test_plasma_free_electron_yield
        * test_plasma_active_volume
    )
    test_plasma_drive_edge_detuning_ratio = 1.0
    test_plasma_drive_beam_parameter_product = (
        test_plasma_drive_beam_quality_factor
        * test_plasma_drive_beam_wavelength
        / float(sp.pi)
    )
    test_plasma_drive_beam_parameter_waist_radius = (
        test_plasma_drive_pupil_beam_fill_factor
        * test_plasma_drive_objective_pupil_radius
    )
    test_plasma_drive_far_field_divergence_half_angle = (
        test_plasma_drive_beam_parameter_product
        / test_plasma_drive_beam_parameter_waist_radius
    )
    test_plasma_source_ionization_energy = (
        2.0
        * float(sp.pi)
        * hbar
        * c
        * test_plasma_drive_edge_detuning_ratio
        / test_plasma_drive_beam_wavelength
    )
    test_plasma_drive_spot_axis_ratio = 1.0
    test_plasma_drive_spot_area_fill_factor = 1.0
    test_plasma_drive_spot_shape_factor = (
        test_plasma_drive_spot_axis_ratio
        * test_plasma_drive_spot_area_fill_factor
    )
    test_plasma_drive_spot_area = (
        float(sp.pi)
        * test_plasma_drive_spot_radius**2
        * test_plasma_drive_spot_shape_factor
    )
    test_plasma_drive_centroid_offset_to_column_radius_ratio = 0.0
    test_plasma_drive_pointing_overlap_factor = float(
        sp.exp(-(test_plasma_drive_centroid_offset_to_column_radius_ratio**2))
    )
    test_plasma_drive_transverse_overlap_factor = (
        test_plasma_drive_spot_area
        / (float(sp.pi) * test_plasma_column_radius**2)
    )
    test_plasma_drive_spatial_overlap_factor = (
        test_plasma_drive_transverse_overlap_factor
        * test_plasma_drive_pointing_overlap_factor
        * test_plasma_active_fill_factor
    )
    test_plasma_energy_loss_path_direction_cosine = float(
        sp.sin(test_plasma_drive_acceptance_half_angle)
    )
    test_plasma_energy_loss_path_factor = (
        1.0 / test_plasma_energy_loss_path_direction_cosine
    )
    test_plasma_energy_loss_path_length = (
        test_plasma_energy_loss_path_factor
        * test_plasma_column_radius
    )
    test_plasma_energy_loss_transport_speed_factor = (
        test_plasma_species_particle_mass / electron_mass
    ) ** 0.5
    test_plasma_energy_loss_speed = (
        test_plasma_energy_loss_transport_speed_factor
        * test_plasma_species_thermal_speed
    )
    test_plasma_energy_confinement_time = (
        test_plasma_energy_loss_path_length
        / test_plasma_energy_loss_speed
    )
    test_plasma_internal_energy = (
        1.5
        * boltzmann
        * test_plasma_temperature
        * test_plasma_free_electron_count
    )
    test_plasma_absorbed_power = (
        test_plasma_internal_energy
        / test_plasma_energy_confinement_time
    )
    test_plasma_drive_power = (
        test_plasma_absorbed_power
        / test_plasma_absorption_efficiency
    )
    test_plasma_pulse_energy = (
        test_plasma_drive_power
        / test_plasma_pulse_repetition_rate
    )
    test_plasma_active_lifetime_to_drive_pulse_ratio = (
        test_plasma_energy_confinement_time
        / test_plasma_drive_pulse_duration
    )
    test_plasma_active_response_duration = (
        test_plasma_active_lifetime_to_drive_pulse_ratio
        * test_plasma_drive_pulse_duration
    )
    test_plasma_drive_timing_offset_fraction = 0.0
    test_plasma_drive_timing_offset_duration = (
        test_plasma_drive_timing_offset_fraction
        * test_plasma_drive_pulse_duration
    )
    test_plasma_drive_temporal_duration_match_factor = (
        4.0
        * test_plasma_drive_pulse_duration
        * test_plasma_active_response_duration
        / (
            test_plasma_drive_pulse_duration
            + test_plasma_active_response_duration
        ) ** 2
    )
    test_plasma_drive_temporal_alignment_factor = float(
        sp.exp(
            -(
                test_plasma_drive_timing_offset_duration
                / (
                    test_plasma_drive_pulse_duration
                    + test_plasma_active_response_duration
                )
            ) ** 2
        )
    )
    test_plasma_drive_temporal_overlap_factor = (
        test_plasma_drive_temporal_duration_match_factor
        * test_plasma_drive_temporal_alignment_factor
    )
    test_plasma_drive_overlap_factor = (
        test_plasma_drive_spatial_overlap_factor
        * test_plasma_drive_temporal_overlap_factor
    )
    test_plasma_electron_heating_fraction = (
        test_plasma_absorption_efficiency
        / (
            test_plasma_drive_overlap_factor
            * test_plasma_drive_energy_absorption_fraction
        )
    )
    test_plasma_drive_peak_intensity = (
        test_plasma_pulse_energy
        / (
            test_plasma_drive_spot_area
            * test_plasma_drive_pulse_duration
            * test_plasma_drive_pulse_temporal_shape_factor
        )
    )
    test_plasma_drive_pulse_fluence = (
        test_plasma_drive_peak_intensity
        * test_plasma_drive_pulse_duration
        * test_plasma_drive_pulse_temporal_shape_factor
    )
    test_plasma_absorption_path_direction_cosine = float(
        sp.cos(test_plasma_drive_acceptance_half_angle)
    )
    test_plasma_absorption_path_shape_factor = (
        1.0 / test_plasma_absorption_path_direction_cosine
    )
    test_plasma_absorption_path_length = (
        test_plasma_absorption_path_shape_factor
        * test_plasma_column_length
    )
    test_plasma_absorption_cross_section = (
        test_plasma_absorption_optical_depth
        / (
            test_plasma_species_number_density
            * test_plasma_absorption_path_length
        )
    )
    test_plasma_drive_beam_angular_frequency = (
        2.0 * float(sp.pi) * c / test_plasma_drive_beam_wavelength
    )
    test_plasma_absorption_resonance = test_plasma_drive_beam_angular_frequency
    test_source_ionization_principal_quantum_number = 1.0
    test_source_ionization_effective_nuclear_charge = 1.0
    test_plasma_absorption_collision_orbital_radius = (
        bohr_radius
        * test_source_ionization_principal_quantum_number**2
        / test_source_ionization_effective_nuclear_charge
    )
    test_plasma_absorption_collision_cross_section = (
        float(sp.pi) * test_plasma_absorption_collision_orbital_radius**2
    )
    test_plasma_absorption_damping_rate = (
        test_plasma_species_number_density
        * test_plasma_absorption_collision_cross_section
        * test_plasma_species_thermal_speed
    )
    test_plasma_absorption_resonance_to_drive_ratio = (
        test_plasma_absorption_resonance
        / test_plasma_drive_beam_angular_frequency
    )
    test_plasma_absorption_quality_factor = (
        test_plasma_absorption_resonance
        / test_plasma_absorption_damping_rate
    )
    test_plasma_absorption_oscillator_strength = (
        test_plasma_absorption_cross_section
        * electron_mass
        * vacuum_permittivity
        * c
        * (
            (
                test_plasma_absorption_resonance**2
                - test_plasma_drive_beam_angular_frequency**2
            ) ** 2
            + (
                test_plasma_absorption_damping_rate**2
                * test_plasma_drive_beam_angular_frequency**2
            )
        )
        / elementary_charge**2
        / test_plasma_absorption_damping_rate
        / test_plasma_drive_beam_angular_frequency**2
    )
    test_plasma_absorption_sum_rule_fraction = 1.0
    test_plasma_absorption_participating_electron_fraction = (
        test_plasma_absorption_oscillator_strength
        / test_plasma_absorption_sum_rule_fraction
    )
    test_debye_length = (
        vacuum_permittivity
        * boltzmann
        * test_plasma_temperature
        / (test_plasma_electron_number_density * elementary_charge**2)
    ) ** 0.5
    plasma_assignments = {
        **plasma_source_root_assignments,
        "physical.lithography.source_plasma_drive_pulse_fluence": test_plasma_drive_pulse_fluence,
        "physical.lithography.source_plasma_drive_pulse_duty_factor": test_plasma_drive_pulse_duty_factor,
        "physical.lithography.source_plasma_drive_pulse_rise_fraction": test_plasma_drive_pulse_rise_fraction,
        "physical.lithography.source_ionization_energy": test_plasma_source_ionization_energy,
        "physical.lithography.source_plasma_drive_edge_detuning_ratio": test_plasma_drive_edge_detuning_ratio,
        "physical.lithography.source_plasma_drive_objective_pupil_radius": test_plasma_drive_objective_pupil_radius,
        "physical.lithography.source_plasma_drive_objective_focal_length": test_plasma_drive_objective_focal_length,
        "physical.lithography.source_plasma_drive_pupil_beam_fill_factor": test_plasma_drive_pupil_beam_fill_factor,
        "physical.lithography.source_plasma_drive_far_field_divergence_half_angle": test_plasma_drive_far_field_divergence_half_angle,
        "physical.lithography.source_plasma_active_fill_factor": test_plasma_active_fill_factor,
        "physical.lithography.source_plasma_drive_centroid_offset_to_column_radius_ratio": test_plasma_drive_centroid_offset_to_column_radius_ratio,
            "physical.lithography.source_plasma_drive_timing_offset_fraction": test_plasma_drive_timing_offset_fraction,
            "physical.lithography.source_plasma_absorption_participating_electron_fraction": test_plasma_absorption_participating_electron_fraction,
        "physical.lithography.source_plasma_absorption_sum_rule_fraction": test_plasma_absorption_sum_rule_fraction,
        "physical.lithography.source_plasma_electron_heating_fraction": test_plasma_electron_heating_fraction,
    }
    def plasma_assignments_for_source(protons):
        return {
            **plasma_assignments,
            "physical.lithography.source_plasma_absorption_participating_electron_fraction": (
                test_plasma_absorption_oscillator_strength
                / (protons * test_plasma_absorption_sum_rule_fraction)
            ),
            "physical.lithography.source_plasma_free_electron_inventory_charge_fraction": (
                test_plasma_free_electron_yield / protons
            ),
        }

    assignments = {
        **source_quark_assignments(1, 0),
        "physical.lithography.nuclear_binding_coulomb_coefficient": test_coulomb_coeff,
        "physical.lithography.nuclear_binding_volume_coefficient": 0.0,
        "physical.lithography.nuclear_binding_surface_coefficient": 0.0,
        "physical.lithography.nuclear_binding_asymmetry_coefficient": 0.0,
        "physical.lithography.nuclear_pairing_gap_reference_energy": 0.0,
        **plasma_assignments_for_source(1),
        "physical.lithography.source_ionization_partition_ratio": 0.0,
    }
    reduced_mass_ratio = proton_mass / (electron_mass + proton_mass)
    expected_energy = rydberg_energy * reduced_mass_ratio * (1.0 - 1.0 / 4.0)

    radius_coeff_result = resolve(
        "physical.lithography.source_nuclear_radius_coefficient",
        assignments={
            "physical.lithography.nuclear_binding_coulomb_coefficient": test_coulomb_coeff,
        },
    )
    assert float(radius_coeff_result.value) == pytest.approx(test_radius_coeff)

    saturation_density_result = resolve(
        "physical.lithography.source_nuclear_saturation_number_density",
        assignments={
            "physical.lithography.nuclear_binding_coulomb_coefficient": test_coulomb_coeff,
        },
    )
    assert float(saturation_density_result.value) == pytest.approx(test_saturation_density)

    bulk_binding_density_result = resolve(
        "physical.lithography.source_nuclear_bulk_binding_energy_density",
        assignments={
            "physical.lithography.nuclear_binding_coulomb_coefficient": test_coulomb_coeff,
            "physical.lithography.nuclear_binding_volume_coefficient": test_volume_coeff,
        },
    )
    assert float(bulk_binding_density_result.value) == pytest.approx(test_bulk_binding_density)

    surface_tension_result = resolve(
        "physical.lithography.source_nuclear_surface_tension",
        assignments={
            "physical.lithography.nuclear_binding_coulomb_coefficient": test_coulomb_coeff,
            "physical.lithography.nuclear_binding_surface_coefficient": test_surface_coeff,
        },
    )
    assert float(surface_tension_result.value) == pytest.approx(test_surface_tension)

    symmetry_density_result = resolve(
        "physical.lithography.source_nuclear_symmetry_energy_density",
        assignments={
            "physical.lithography.nuclear_binding_coulomb_coefficient": test_coulomb_coeff,
            "physical.lithography.nuclear_binding_asymmetry_coefficient": test_asymmetry_coeff,
        },
    )
    assert float(symmetry_density_result.value) == pytest.approx(test_symmetry_density)

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
            "physical.lithography.nuclear_pairing_gap_reference_energy": test_pairing_gap_ref,
        },
    )
    assert float(pairing_coeff_result.value) == pytest.approx(4.0)
    assert "physical.eq.lithography_source_pairing_reference_mass_number" in {
        step.equation for step in pairing_coeff_result.trace
    }

    pairing_coeff_override_result = resolve(
        "physical.lithography.source_binding_pairing_coefficient",
        assignments={
            "physical.lithography.nuclear_pairing_gap_reference_energy": test_pairing_gap_ref,
            "physical.lithography.source_pairing_reference_mass_number": 9,
        },
    )
    assert float(pairing_coeff_override_result.value) == pytest.approx(3.0)
    assert "physical.eq.lithography_source_pairing_reference_mass_number" not in {
        step.equation for step in pairing_coeff_override_result.trace
    }

    plasma_assignments_with_source = {
        **source_quark_assignments(1, 0),
        **plasma_assignments_for_source(1),
    }
    absorbed_power_result = resolve(
        "physical.lithography.source_plasma_absorbed_power",
        assignments=plasma_assignments_with_source,
    )
    assert float(absorbed_power_result.value) == pytest.approx(test_plasma_absorbed_power)
    drive_power_result = resolve(
        "physical.lithography.source_plasma_drive_power",
        assignments=plasma_assignments,
    )
    assert float(drive_power_result.value) == pytest.approx(test_plasma_drive_power)
    pulse_duration_result = resolve(
        "physical.lithography.source_plasma_drive_pulse_duration",
        assignments=plasma_assignments,
    )
    assert float(pulse_duration_result.value) == pytest.approx(
        test_plasma_drive_pulse_duration
    )
    pulse_fall_fraction_result = resolve(
        "physical.lithography.source_plasma_drive_pulse_fall_fraction",
        assignments=plasma_assignments,
    )
    assert float(pulse_fall_fraction_result.value) == pytest.approx(
        test_plasma_drive_pulse_fall_fraction
    )
    pulse_flat_fraction_result = resolve(
        "physical.lithography.source_plasma_drive_pulse_flat_fraction",
        assignments=plasma_assignments,
    )
    assert float(pulse_flat_fraction_result.value) == pytest.approx(
        test_plasma_drive_pulse_flat_fraction
    )
    pulse_shape_result = resolve(
        "physical.lithography.source_plasma_drive_pulse_temporal_shape_factor",
        assignments=plasma_assignments,
    )
    assert float(pulse_shape_result.value) == pytest.approx(
        test_plasma_drive_pulse_temporal_shape_factor
    )
    peak_intensity_result = resolve(
        "physical.lithography.source_plasma_drive_peak_intensity",
        assignments=plasma_assignments,
    )
    assert float(peak_intensity_result.value) == pytest.approx(
        test_plasma_drive_peak_intensity
    )
    waist_coefficient_result = resolve(
        "physical.lithography.source_plasma_drive_focus_waist_coefficient",
        assignments=plasma_assignments,
    )
    assert float(waist_coefficient_result.value) == pytest.approx(
        test_plasma_drive_focus_waist_coefficient
    )
    acceptance_half_angle_result = resolve(
        "physical.lithography.source_plasma_drive_acceptance_half_angle",
        assignments=plasma_assignments,
    )
    assert float(acceptance_half_angle_result.value) == pytest.approx(
        test_plasma_drive_acceptance_half_angle
    )
    numerical_aperture_result = resolve(
        "physical.lithography.source_plasma_drive_numerical_aperture",
        assignments=plasma_assignments,
    )
    assert float(numerical_aperture_result.value) == pytest.approx(
        test_plasma_drive_numerical_aperture
    )
    focus_f_number_result = resolve(
        "physical.lithography.source_plasma_drive_focus_f_number",
        assignments=plasma_assignments,
    )
    assert float(focus_f_number_result.value) == pytest.approx(
        test_plasma_drive_focus_f_number
    )
    beam_parameter_waist_result = resolve(
        "physical.lithography.source_plasma_drive_beam_parameter_waist_radius",
        assignments=plasma_assignments,
    )
    assert float(beam_parameter_waist_result.value) == pytest.approx(
        test_plasma_drive_beam_parameter_waist_radius
    )
    beam_parameter_product_result = resolve(
        "physical.lithography.source_plasma_drive_beam_parameter_product",
        assignments=plasma_assignments,
    )
    assert float(beam_parameter_product_result.value) == pytest.approx(
        test_plasma_drive_beam_parameter_product
    )
    beam_quality_result = resolve(
        "physical.lithography.source_plasma_drive_beam_quality_factor",
        assignments=plasma_assignments,
    )
    assert float(beam_quality_result.value) == pytest.approx(
        test_plasma_drive_beam_quality_factor
    )
    spot_axis_ratio_result = resolve(
        "physical.lithography.source_plasma_drive_spot_axis_ratio",
        assignments=plasma_assignments,
    )
    assert float(spot_axis_ratio_result.value) == pytest.approx(
        test_plasma_drive_spot_axis_ratio
    )
    spot_area_fill_factor_result = resolve(
        "physical.lithography.source_plasma_drive_spot_area_fill_factor",
        assignments=plasma_assignments,
    )
    assert float(spot_area_fill_factor_result.value) == pytest.approx(
        test_plasma_drive_spot_area_fill_factor
    )
    spot_radius_result = resolve(
        "physical.lithography.source_plasma_drive_spot_radius",
        assignments=plasma_assignments,
    )
    assert float(spot_radius_result.value) == pytest.approx(test_plasma_drive_spot_radius)
    rayleigh_range_result = resolve(
        "physical.lithography.source_plasma_drive_rayleigh_range",
        assignments=plasma_assignments,
    )
    assert float(rayleigh_range_result.value) == pytest.approx(
        test_plasma_drive_rayleigh_range
    )
    confocal_length_result = resolve(
        "physical.lithography.source_plasma_drive_confocal_length",
        assignments=plasma_assignments,
    )
    assert float(confocal_length_result.value) == pytest.approx(
        test_plasma_drive_confocal_length
    )
    spot_shape_result = resolve(
        "physical.lithography.source_plasma_drive_spot_shape_factor",
        assignments=plasma_assignments,
    )
    assert float(spot_shape_result.value) == pytest.approx(
        test_plasma_drive_spot_shape_factor
    )
    column_expansion_result = resolve(
        "physical.lithography.source_plasma_column_radius_expansion_factor",
        assignments=plasma_assignments_with_source,
    )
    assert float(column_expansion_result.value) == pytest.approx(
        test_plasma_column_radius_expansion_factor
    )
    column_aspect_result = resolve(
        "physical.lithography.source_plasma_column_aspect_ratio",
        assignments=plasma_assignments_with_source,
    )
    assert float(column_aspect_result.value) == pytest.approx(
        test_plasma_column_aspect_ratio
    )
    species_density_result = resolve(
        "physical.lithography.source_plasma_species_number_density",
        assignments=plasma_assignments,
    )
    assert float(species_density_result.value) == pytest.approx(
        test_plasma_species_number_density
    )
    absorption_path_direction_cosine_result = resolve(
        "physical.lithography.source_plasma_absorption_path_direction_cosine",
        assignments=plasma_assignments,
    )
    assert float(absorption_path_direction_cosine_result.value) == pytest.approx(
        test_plasma_absorption_path_direction_cosine
    )
    absorption_path_shape_result = resolve(
        "physical.lithography.source_plasma_absorption_path_shape_factor",
        assignments=plasma_assignments,
    )
    assert float(absorption_path_shape_result.value) == pytest.approx(
        test_plasma_absorption_path_shape_factor
    )
    absorption_path_result = resolve(
        "physical.lithography.source_plasma_absorption_path_length",
        assignments=plasma_assignments_with_source,
    )
    assert float(absorption_path_result.value) == pytest.approx(
        test_plasma_absorption_path_length
    )
    drive_beam_angular_frequency_result = resolve(
        "physical.lithography.source_plasma_drive_beam_angular_frequency",
        assignments=plasma_assignments,
    )
    assert float(drive_beam_angular_frequency_result.value) == pytest.approx(
        test_plasma_drive_beam_angular_frequency
    )
    absorption_resonance_result = resolve(
        "physical.lithography.source_plasma_absorption_resonance_angular_frequency",
        assignments=plasma_assignments_with_source,
    )
    assert float(absorption_resonance_result.value) == pytest.approx(
        test_plasma_absorption_resonance
    )
    collision_orbital_radius_result = resolve(
        "physical.lithography.source_plasma_absorption_collision_orbital_radius",
        assignments=plasma_assignments_with_source,
    )
    assert float(collision_orbital_radius_result.value) == pytest.approx(
        test_plasma_absorption_collision_orbital_radius
    )
    collision_cross_section_result = resolve(
        "physical.lithography.source_plasma_absorption_collision_cross_section",
        assignments=plasma_assignments_with_source,
    )
    assert float(collision_cross_section_result.value) == pytest.approx(
        test_plasma_absorption_collision_cross_section
    )
    absorption_damping_result = resolve(
        "physical.lithography.source_plasma_absorption_damping_rate",
        assignments=plasma_assignments_with_source,
    )
    assert float(absorption_damping_result.value) == pytest.approx(
        test_plasma_absorption_damping_rate
    )
    absorption_quality_result = resolve(
        "physical.lithography.source_plasma_absorption_quality_factor",
        assignments=plasma_assignments_with_source,
    )
    assert float(absorption_quality_result.value) == pytest.approx(
        test_plasma_absorption_quality_factor
    )
    absorption_oscillator_result = resolve(
        "physical.lithography.source_plasma_absorption_oscillator_strength",
        assignments=plasma_assignments_with_source,
    )
    assert float(absorption_oscillator_result.value) == pytest.approx(
        test_plasma_absorption_oscillator_strength
    )
    absorption_cross_section_result = resolve(
        "physical.lithography.source_plasma_absorption_cross_section",
        assignments=plasma_assignments_with_source,
    )
    assert float(absorption_cross_section_result.value) == pytest.approx(
        test_plasma_absorption_cross_section
    )
    absorption_depth_result = resolve(
        "physical.lithography.source_plasma_absorption_optical_depth",
        assignments=plasma_assignments_with_source,
    )
    assert float(absorption_depth_result.value) == pytest.approx(
        test_plasma_absorption_optical_depth
    )
    absorption_fraction_result = resolve(
        "physical.lithography.source_plasma_drive_energy_absorption_fraction",
        assignments=plasma_assignments_with_source,
    )
    assert float(absorption_fraction_result.value) == pytest.approx(
        test_plasma_drive_energy_absorption_fraction
    )
    overlap_result = resolve(
        "physical.lithography.source_plasma_drive_overlap_factor",
        assignments=plasma_assignments_with_source,
    )
    assert float(overlap_result.value) == pytest.approx(
        test_plasma_drive_overlap_factor
    )
    ideal_overlap_assignments = {
        key: value
        for key, value in plasma_assignments_with_source.items()
        if key not in {
            "physical.lithography.source_plasma_active_fill_factor",
            "physical.lithography.source_plasma_drive_centroid_offset_to_column_radius_ratio",
            "physical.lithography.source_plasma_drive_timing_offset_fraction",
        }
    }
    ideal_overlap_result = resolve(
        "physical.lithography.source_plasma_drive_overlap_factor",
        assignments=ideal_overlap_assignments,
    )
    assert float(ideal_overlap_result.value) == pytest.approx(
        test_plasma_drive_overlap_factor / test_plasma_active_fill_factor
    )
    ideal_overlap_trace = {step.equation for step in ideal_overlap_result.trace}
    assert {
        "physical.eq.lithography_source_plasma_active_fill_factor_from_ideal_column_convention",
        "physical.eq.lithography_source_plasma_drive_centroid_offset_to_column_radius_ratio_from_coaxial_convention",
        "physical.eq.lithography_source_plasma_drive_timing_offset_fraction_from_synchronized_convention",
    } <= ideal_overlap_trace
    absorption_result = resolve(
        "physical.lithography.source_plasma_absorption_efficiency",
        assignments=plasma_assignments_with_source,
    )
    assert float(absorption_result.value) == pytest.approx(
        test_plasma_absorption_efficiency
    )
    active_volume_result = resolve(
        "physical.lithography.source_plasma_active_volume",
        assignments=plasma_assignments_with_source,
    )
    assert float(active_volume_result.value) == pytest.approx(test_plasma_active_volume)
    energy_loss_direction_result = resolve(
        "physical.lithography.source_plasma_energy_loss_path_direction_cosine",
        assignments=plasma_assignments_with_source,
    )
    assert float(energy_loss_direction_result.value) == pytest.approx(
        test_plasma_energy_loss_path_direction_cosine
    )
    energy_loss_path_factor_result = resolve(
        "physical.lithography.source_plasma_energy_loss_path_factor",
        assignments=plasma_assignments_with_source,
    )
    assert float(energy_loss_path_factor_result.value) == pytest.approx(
        test_plasma_energy_loss_path_factor
    )
    energy_loss_path_result = resolve(
        "physical.lithography.source_plasma_energy_loss_path_length",
        assignments=plasma_assignments_with_source,
    )
    assert float(energy_loss_path_result.value) == pytest.approx(
        test_plasma_energy_loss_path_length
    )
    particle_mass_result = resolve(
        "physical.lithography.source_plasma_species_particle_mass",
        assignments=plasma_assignments_with_source,
    )
    assert float(particle_mass_result.value) == pytest.approx(
        test_plasma_species_particle_mass
    )
    species_thermal_speed_result = resolve(
        "physical.lithography.source_plasma_species_thermal_speed",
        assignments=plasma_assignments_with_source,
    )
    assert float(species_thermal_speed_result.value) == pytest.approx(
        test_plasma_species_thermal_speed
    )
    transport_factor_result = resolve(
        "physical.lithography.source_plasma_energy_loss_transport_speed_factor",
        assignments=plasma_assignments_with_source,
    )
    assert float(transport_factor_result.value) == pytest.approx(
        test_plasma_energy_loss_transport_speed_factor
    )
    column_expansion_speed_factor_result = resolve(
        "physical.lithography.source_plasma_column_expansion_speed_factor",
        assignments=plasma_assignments_with_source,
    )
    assert float(column_expansion_speed_factor_result.value) == pytest.approx(
        test_plasma_column_expansion_speed_factor
    )
    radial_expansion_speed_result = resolve(
        "physical.lithography.source_plasma_column_radial_expansion_speed",
        assignments=plasma_assignments_with_source,
    )
    assert float(radial_expansion_speed_result.value) == pytest.approx(
        test_plasma_column_radial_expansion_speed
    )
    energy_loss_speed_result = resolve(
        "physical.lithography.source_plasma_energy_loss_speed",
        assignments=plasma_assignments_with_source,
    )
    assert float(energy_loss_speed_result.value) == pytest.approx(
        test_plasma_energy_loss_speed
    )
    confinement_time_result = resolve(
        "physical.lithography.source_plasma_energy_confinement_time",
        assignments=plasma_assignments_with_source,
    )
    assert float(confinement_time_result.value) == pytest.approx(
        test_plasma_energy_confinement_time
    )
    active_lifetime_ratio_result = resolve(
        "physical.lithography.source_plasma_active_lifetime_to_drive_pulse_ratio",
        assignments=plasma_assignments_with_source,
    )
    assert float(active_lifetime_ratio_result.value) == pytest.approx(
        test_plasma_active_lifetime_to_drive_pulse_ratio
    )
    free_electron_yield_result = resolve(
        "physical.lithography.source_plasma_free_electron_yield_per_source_particle",
        assignments=plasma_assignments_with_source,
    )
    assert float(free_electron_yield_result.value) == pytest.approx(
        test_plasma_free_electron_yield
    )
    free_electron_count_result = resolve(
        "physical.lithography.source_plasma_free_electron_count",
        assignments=plasma_assignments_with_source,
    )
    assert float(free_electron_count_result.value) == pytest.approx(
        test_plasma_free_electron_count
    )
    internal_energy_result = resolve(
        "physical.lithography.source_plasma_electron_internal_energy",
        assignments=plasma_assignments_with_source,
    )
    assert float(internal_energy_result.value) == pytest.approx(test_plasma_internal_energy)
    temperature_result = resolve(
        "physical.lithography.source_plasma_electron_temperature",
        assignments=plasma_assignments_with_source,
    )
    assert float(temperature_result.value) == pytest.approx(test_plasma_temperature)
    electron_density_result = resolve(
        "physical.lithography.source_plasma_electron_number_density",
        assignments=plasma_assignments_with_source,
    )
    assert float(electron_density_result.value) == pytest.approx(
        test_plasma_electron_number_density
    )

    mean_energy_result = resolve(
        "physical.lithography.source_plasma_electron_mean_kinetic_energy",
        assignments=plasma_assignments_with_source,
    )
    assert float(mean_energy_result.value) == pytest.approx(
        test_mean_electron_kinetic_energy
    )
    debye_length_result = resolve(
        "physical.lithography.source_plasma_debye_length",
        assignments=plasma_assignments_with_source,
    )
    assert float(debye_length_result.value) == pytest.approx(test_debye_length)

    violated_pulse_duration_result = resolve(
        "physical.lithography.source_plasma_drive_pulse_duration",
        assignments={
            "physical.lithography.source_plasma_drive_pulse_duration": 2.0,
            "physical.lithography.source_plasma_pulse_period": 1.0,
        },
    )
    pulse_duration_check = next(
        c for c in violated_pulse_duration_result.constraints
        if c.equation
        == "physical.ineq.lithography_source_plasma_pulse_duration_within_period"
    )
    assert pulse_duration_check.satisfied is False
    assert pulse_duration_check.missing == set()

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
            "physical.lithography.source_plasma_electron_temperature": test_plasma_temperature,
            "physical.lithography.source_plasma_electron_number_density": test_plasma_electron_number_density,
            "physical.lithography.source_ionization_partition_ratio": 2.0 / 7.0,
            "physical.lithography.source_ionization_energy": 0.0,
        },
    )
    assert float(ion_charge_result.value) == pytest.approx(24.0 / 13.0)

    inner_closed_result = resolve(
        "physical.lithography.source_inner_closed_shell_electron_count",
        assignments={
            **source_quark_assignments(4, 0),
            **plasma_assignments_for_source(4),
            "physical.lithography.source_ionization_partition_ratio": 0.0,
        },
    )
    assert float(inner_closed_result.value) == pytest.approx(2.0)

    outer_shell_result = resolve(
        "physical.lithography.source_outer_shell_electron_count",
        assignments={
            **source_quark_assignments(12, 0),
            **plasma_assignments_for_source(12),
            "physical.lithography.source_ionization_partition_ratio": 0.0,
        },
    )
    assert float(outer_shell_result.value) == pytest.approx(0.0)

    binding_result = resolve(
        "physical.lithography.source_nuclear_binding_energy",
        assignments={
            **source_quark_assignments(2, 2),
            "physical.lithography.nuclear_binding_coulomb_coefficient": test_coulomb_coeff,
            "physical.lithography.nuclear_binding_volume_coefficient": test_volume_coeff,
            "physical.lithography.nuclear_binding_surface_coefficient": test_surface_coeff,
            "physical.lithography.nuclear_binding_asymmetry_coefficient": test_asymmetry_coeff,
            "physical.lithography.nuclear_pairing_gap_reference_energy": test_pairing_gap_ref,
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

    screening_result = resolve(
        "physical.lithography.source_screening_constant",
        assignments={
            **source_quark_assignments(4, 0),
            **plasma_assignments_for_source(4),
            "physical.lithography.source_ionization_partition_ratio": 0.0,
        },
    )
    assert float(screening_result.value) == pytest.approx(2.5)

    energy_result = resolve(
        "physical.lithography.photon_energy",
        assignments=assignments,
    )
    assert float(energy_result.value) == pytest.approx(expected_energy)

    wavelength_result = resolve(
        "physical.lithography.wavelength",
        assignments=assignments,
    )
    assert float(wavelength_result.value) == pytest.approx(
        planck * c / expected_energy
    )


def test_lithography_source_reduced_mass_constraints_are_explicit():
    expected = {
        "physical.ineq.lithography_source_nuclear_mass_positive": (
            "physical.lithography.source_nuclear_mass"
        ),
        "physical.ineq.lithography_source_reduced_mass_positive": (
            "physical.lithography.source_reduced_mass"
        ),
        "physical.ineq.lithography_source_reduced_mass_ratio_positive": (
            "physical.lithography.source_reduced_mass_ratio"
        ),
    }

    for equation_name, variable_name in expected.items():
        eq = Registry.equations[equation_name]
        assert isinstance(eq, Inequality)
        assert eq.role is RelationRole.CONSTRAINT
        assert eq in Registry.variables[variable_name].constraints()
        assert eq.references
        assert not getattr(eq, "_check_units_flag", False)
        relation = eq.as_sympy()
        assert relation is not sp.S.true
        assert isinstance(relation, sp.Rel)


def test_lithography_source_reduced_mass_constraints_report_invalid_masses():
    electron_mass = Registry.variables["physics.electron_mass"].value
    proton_mass = Registry.variables["physics.proton_mass"].value
    speed_of_light = Registry.variables["physics.speed_of_light"].value

    negative_nuclear_mass = resolve(
        "physical.lithography.source_nuclear_mass",
        assignments={
            "physical.lithography.source_proton_count": 1.0,
            "physical.lithography.source_neutron_count": 0.0,
            "physical.lithography.source_nuclear_binding_energy": (
                2.0 * proton_mass * speed_of_light**2
            ),
        },
    )
    assert float(negative_nuclear_mass.value) == pytest.approx(-proton_mass)
    failed_constraint(
        negative_nuclear_mass,
        "physical.ineq.lithography_source_nuclear_mass_positive",
    )

    singular_reduced_mass = resolve(
        "physical.lithography.source_reduced_mass",
        assignments={
            "physical.lithography.source_nuclear_mass": -electron_mass,
        },
    )
    assert singular_reduced_mass.value is sp.zoo
    failed_constraint(
        singular_reduced_mass,
        "physical.ineq.lithography_source_nuclear_mass_positive",
    )
    failed_constraint(
        singular_reduced_mass,
        "physical.ineq.lithography_source_reduced_mass_positive",
    )

    negative_reduced_mass_ratio = resolve(
        "physical.lithography.source_reduced_mass_ratio",
        assignments={
            "physical.lithography.source_reduced_mass": -electron_mass,
        },
    )
    assert float(negative_reduced_mass_ratio.value) == pytest.approx(-1.0)
    failed_constraint(
        negative_reduced_mass_ratio,
        "physical.ineq.lithography_source_reduced_mass_positive",
    )
    failed_constraint(
        negative_reduced_mass_ratio,
        "physical.ineq.lithography_source_reduced_mass_ratio_positive",
    )


def test_lithography_medium_relative_permittivity_rejects_bad_lorentz_lorenz_branch():
    result = resolve(
        "physical.lithography.medium_relative_permittivity",
        assignments={
            "physical.lithography.medium_lorentz_lorenz_factor": -0.75,
        },
    )
    assert float(result.value) == pytest.approx(-1.0 / 3.5)
    check = next(
        c for c in result.approximation_validity
        if c.equation == "physical.eq.lithography_medium_relative_permittivity"
    )
    assert check.satisfied is False
    assert check.missing == set()


def test_lithography_refractive_index_and_acceptance_angle_have_lower_models():
    refractive_index = Registry.variables["physical.lithography.medium_refractive_index"]
    acceptance = Registry.variables["physical.lithography.acceptance_half_angle"]
    numerical_aperture = Registry.variables["physical.lithography.numerical_aperture"]
    assert not refractive_index.is_root_input
    assert not acceptance.is_root_input
    assert not numerical_aperture.is_root_input
    assert {v.name for v in refractive_index.direct_dependencies()} == {
        "physical.lithography.medium_relative_permittivity",
        "physical.lithography.medium_relative_permeability",
    }
    assert {v.name for v in acceptance.direct_dependencies()} == {
        "physical.lithography.objective_pupil_radius",
        "physical.lithography.objective_focal_length",
    }
    assert {v.name for v in numerical_aperture.direct_dependencies()} == {
        "physical.lithography.medium_refractive_index",
        "physical.lithography.acceptance_half_angle",
    }

    forward_cone = Registry.equations[
        "physical.ineq.lithography_acceptance_half_angle_within_forward_half_space"
    ]
    na_medium_bound = Registry.equations[
        "physical.ineq.lithography_numerical_aperture_within_medium_index"
    ]
    assert isinstance(forward_cone, Inequality)
    assert isinstance(na_medium_bound, Inequality)
    assert forward_cone.role is RelationRole.CONSTRAINT
    assert na_medium_bound.role is RelationRole.CONSTRAINT
    assert forward_cone.op == "<="
    assert na_medium_bound.op == "<="
    assert forward_cone.rhs == sp.pi / 2
    assert na_medium_bound.rhs == refractive_index.symbol
    assert forward_cone.references
    assert na_medium_bound.references
    assert getattr(forward_cone, "_check_units_flag", False)
    assert getattr(na_medium_bound, "_check_units_flag", False)
    assert isinstance(forward_cone.as_sympy(), sp.Rel)
    assert isinstance(na_medium_bound.as_sympy(), sp.Rel)
    assert forward_cone.as_sympy() is not sp.S.true
    assert na_medium_bound.as_sympy() is not sp.S.true
    assert [eq.name for eq in acceptance.constraints()] == [forward_cone.name]
    assert [eq.name for eq in numerical_aperture.constraints()] == [
        na_medium_bound.name
    ]

    refractive_result = resolve(
        "physical.lithography.medium_refractive_index",
        assignments={
            "physical.lithography.medium_relative_permittivity": 4.0,
            "physical.lithography.medium_relative_permeability": 1.0,
        },
    )
    assert float(refractive_result.value) == pytest.approx(2.0)

    aperture_result = resolve(
        "physical.lithography.numerical_aperture",
        assignments={
            "physical.lithography.medium_relative_permittivity": 4.0,
            "physical.lithography.medium_relative_permeability": 1.0,
            "physical.lithography.objective_pupil_radius": 1.0,
            "physical.lithography.objective_focal_length": 1.0,
        },
    )
    assert float(aperture_result.value) == pytest.approx(2.0 ** 0.5)


def test_lithography_medium_response_has_material_models():
    particle_mass = Registry.variables["physical.lithography.medium_particle_mass"]
    packing_length = Registry.variables[
        "physical.lithography.medium_formula_unit_packing_length"
    ]
    packing_length_scale_factor = Registry.variables[
        "physical.lithography.medium_formula_unit_packing_length_scale_factor"
    ]
    packing_fill_factor = Registry.variables[
        "physical.lithography.medium_formula_unit_packing_fill_factor"
    ]
    packing_volume = Registry.variables[
        "physical.lithography.medium_formula_unit_packing_volume"
    ]
    mass_density = Registry.variables["physical.lithography.medium_mass_density"]
    number_density = Registry.variables["physical.lithography.medium_number_density"]
    polarizable_electron_count = Registry.variables[
        "physical.lithography.medium_polarizable_electron_count"
    ]
    polarizable_electron_fraction = Registry.variables[
        "physical.lithography.medium_polarizable_electron_fraction"
    ]
    dominant_oscillator_electron_count = Registry.variables[
        "physical.lithography.medium_dominant_oscillator_electron_count"
    ]
    oscillator_sum_rule_fraction = Registry.variables[
        "physical.lithography.medium_oscillator_sum_rule_fraction"
    ]
    resonance_energy = Registry.variables[
        "physical.lithography.medium_resonance_energy"
    ]
    resonance_ratio = Registry.variables[
        "physical.lithography.medium_resonance_to_source_frequency_ratio"
    ]
    resonance = Registry.variables[
        "physical.lithography.medium_resonance_angular_frequency"
    ]
    oscillator_strength = Registry.variables[
        "physical.lithography.medium_oscillator_strength"
    ]
    polarizability = Registry.variables["physical.lithography.medium_electric_polarizability"]
    intercomponent_site_density = Registry.variables[
        "physical.lithography.medium_intercomponent_polarizable_site_density_factor"
    ]
    intercomponent_lorentz_lorenz = Registry.variables[
        "physical.lithography.medium_intercomponent_lorentz_lorenz_factor"
    ]
    intercomponent_permittivity = Registry.variables[
        "physical.lithography.medium_intercomponent_relative_permittivity"
    ]
    lorentz_lorenz = Registry.variables["physical.lithography.medium_lorentz_lorenz_factor"]
    rel_permittivity = Registry.variables["physical.lithography.medium_relative_permittivity"]
    rel_permeability = Registry.variables["physical.lithography.medium_relative_permeability"]
    assert not particle_mass.is_root_input
    assert packing_length_scale_factor.is_root_input
    assert not packing_length.is_root_input
    assert packing_fill_factor.is_root_input
    assert not packing_volume.is_root_input
    assert not mass_density.is_root_input
    assert not number_density.is_root_input
    assert polarizable_electron_count.is_root_input
    assert not polarizable_electron_fraction.is_root_input
    assert dominant_oscillator_electron_count.is_root_input
    assert not oscillator_sum_rule_fraction.is_root_input
    assert resonance_energy.is_root_input
    assert not resonance_ratio.is_root_input
    assert not resonance.is_root_input
    assert not oscillator_strength.is_root_input
    assert not polarizability.is_root_input
    assert intercomponent_site_density.is_root_input
    assert not intercomponent_lorentz_lorenz.is_root_input
    assert not intercomponent_permittivity.is_root_input
    assert not lorentz_lorenz.is_root_input
    assert not rel_permittivity.is_root_input
    assert not rel_permeability.is_root_input
    assert {v.name for v in particle_mass.direct_dependencies()} == {
        "physical.lithography.medium_molar_mass",
        "physics.avogadro",
    }
    assert packing_length_scale_factor.direct_dependencies() == set()
    assert {v.name for v in packing_length.direct_dependencies()} == {
        "physical.lithography.medium_formula_unit_packing_length_scale_factor",
        "physical.lithography.medium_intercomponent_effective_separation",
    }
    assert packing_fill_factor.direct_dependencies() == set()
    assert {v.name for v in packing_volume.direct_dependencies()} == {
        "physical.lithography.medium_formula_unit_packing_length",
    }
    assert {v.name for v in mass_density.direct_dependencies()} == {
        "physical.lithography.medium_formula_unit_packing_fill_factor",
        "physical.lithography.medium_formula_unit_packing_volume",
        "physical.lithography.medium_particle_mass",
    }
    assert {v.name for v in number_density.direct_dependencies()} == {
        "physical.lithography.medium_mass_density",
        "physical.lithography.medium_particle_mass",
    }
    assert polarizable_electron_count.direct_dependencies() == set()
    assert {v.name for v in polarizable_electron_fraction.direct_dependencies()} == {
        "physical.lithography.medium_formula_unit_electron_count",
        "physical.lithography.medium_polarizable_electron_count",
    }
    polarizable_count_constraint = polarizable_electron_count.constraints()[0]
    assert isinstance(polarizable_count_constraint, Inequality)
    assert polarizable_count_constraint.role is RelationRole.CONSTRAINT
    assert polarizable_count_constraint.op == "<="
    assert polarizable_count_constraint.references
    assert getattr(polarizable_count_constraint, "_check_units_flag", False)
    assert dominant_oscillator_electron_count.direct_dependencies() == set()
    assert {v.name for v in oscillator_sum_rule_fraction.direct_dependencies()} == {
        "physical.lithography.medium_dominant_oscillator_electron_count",
        "physical.lithography.medium_polarizable_electron_count",
    }
    oscillator_count_constraint = dominant_oscillator_electron_count.constraints()[0]
    assert isinstance(oscillator_count_constraint, Inequality)
    assert oscillator_count_constraint.role is RelationRole.CONSTRAINT
    assert oscillator_count_constraint.op == "<="
    assert oscillator_count_constraint.references
    assert getattr(oscillator_count_constraint, "_check_units_flag", False)
    assert resonance_energy.direct_dependencies() == set()
    assert {v.name for v in resonance_ratio.direct_dependencies()} == {
        "physical.lithography.medium_resonance_energy",
        "physical.lithography.photon_energy",
    }
    resonance_energy_constraint = resonance_energy.constraints()[0]
    assert isinstance(resonance_energy_constraint, Inequality)
    assert resonance_energy_constraint.role is RelationRole.CONSTRAINT
    assert resonance_energy_constraint.op == ">"
    assert resonance_energy_constraint.references
    assert getattr(resonance_energy_constraint, "_check_units_flag", False)
    assert {v.name for v in resonance.direct_dependencies()} == {
        "physical.lithography.medium_resonance_to_source_frequency_ratio",
        "physical.lithography.source_angular_frequency",
    }
    assert {v.name for v in oscillator_strength.direct_dependencies()} == {
        "physical.lithography.medium_formula_unit_electron_count",
        "physical.lithography.medium_oscillator_sum_rule_fraction",
        "physical.lithography.medium_polarizable_electron_fraction",
    }
    assert {v.name for v in polarizability.direct_dependencies()} == {
        "physical.lithography.medium_oscillator_strength",
        "physical.lithography.medium_resonance_angular_frequency",
        "physical.lithography.source_angular_frequency",
        "physics.elementary_charge",
        "physics.electron_mass",
    }
    assert intercomponent_site_density.direct_dependencies() == set()
    assert {v.name for v in intercomponent_lorentz_lorenz.direct_dependencies()} == {
        "physical.lithography.medium_electric_polarizability",
        "physical.lithography.medium_intercomponent_effective_separation",
        "physical.lithography.medium_intercomponent_polarizable_site_density_factor",
        "physics.vacuum_permittivity",
    }
    assert {v.name for v in intercomponent_permittivity.direct_dependencies()} == {
        "physical.lithography.medium_intercomponent_lorentz_lorenz_factor",
    }
    assert {v.name for v in lorentz_lorenz.direct_dependencies()} == {
        "physical.lithography.medium_electric_polarizability",
        "physical.lithography.medium_number_density",
        "physics.vacuum_permittivity",
    }
    assert {v.name for v in rel_permittivity.direct_dependencies()} == {
        "physical.lithography.medium_lorentz_lorenz_factor",
    }
    assert {v.name for v in rel_permeability.direct_dependencies()} == {
        "physical.lithography.medium_magnetic_susceptibility",
    }

    epsilon_0 = Registry.variables["physics.vacuum_permittivity"].value
    electron_charge = Registry.variables["physics.elementary_charge"].value
    electron_mass = Registry.variables["physics.electron_mass"].value
    proton_mass = Registry.variables["physics.proton_mass"].value
    neutron_mass = Registry.variables["physics.neutron_mass"].value
    speed_of_light = Registry.variables["physics.speed_of_light"].value
    intercomponent_binding_energy = 5.0e-12
    medium_binding_energy = (
        2 * expected_medium_component_binding_energy(1, 0)
        + expected_medium_component_binding_energy(8, 8)
        + intercomponent_binding_energy
    )
    expected_particle_mass = (
        10 * proton_mass
        + 8 * neutron_mass
        + 10 * electron_mass
        - medium_binding_energy / speed_of_light**2
    )
    medium_assignments = {
        "physical.lithography.medium_component_a_stoichiometric_count": 2,
        **medium_component_quark_assignments("a", 1, 0),
        "physical.lithography.medium_component_b_stoichiometric_count": 1,
        **medium_component_quark_assignments("b", 8, 8),
        **medium_liquid_drop_root_assignments(),
        **medium_intercomponent_binding_root_assignments(
            intercomponent_binding_energy,
            component_b_mass_number=16.0,
        ),
    }

    intercomponent_result = resolve(
        "physical.lithography.medium_formula_unit_intercomponent_binding_energy",
        assignments=medium_assignments,
    )
    assert float(intercomponent_result.value) == pytest.approx(
        intercomponent_binding_energy
    )

    particle_mass_result = resolve(
        "physical.lithography.medium_particle_mass",
        assignments=medium_assignments,
    )
    assert float(particle_mass_result.value) == pytest.approx(expected_particle_mass)
    packing_length_scale_factor_test = 0.5 / float(
        resolve(
            "physical.lithography.medium_intercomponent_effective_separation",
            assignments=medium_assignments,
        ).value
    )

    mass_density_result = resolve(
        "physical.lithography.medium_mass_density",
        assignments={
            **medium_assignments,
            "physical.lithography.medium_formula_unit_packing_length_scale_factor": (
                packing_length_scale_factor_test
            ),
            "physical.lithography.medium_formula_unit_packing_fill_factor": 0.375,
        },
    )
    assert float(mass_density_result.value) == pytest.approx(
        3.0 * expected_particle_mass
    )

    number_density_result = resolve(
        "physical.lithography.medium_number_density",
        assignments={
            **medium_assignments,
            "physical.lithography.medium_formula_unit_packing_length_scale_factor": (
                packing_length_scale_factor_test
            ),
            "physical.lithography.medium_formula_unit_packing_fill_factor": 0.375,
        },
    )
    assert float(number_density_result.value) == pytest.approx(3.0)

    polarizability_result = resolve(
        "physical.lithography.medium_electric_polarizability",
        assignments={
            "physical.lithography.medium_formula_unit_electron_count": 10.0,
            "physical.lithography.medium_polarizable_electron_count": 5.0,
            "physical.lithography.medium_dominant_oscillator_electron_count": 1.0,
            "physical.lithography.medium_resonance_energy": 2.0,
            "physical.lithography.photon_energy": 1.0,
            "physical.lithography.source_angular_frequency": 1.0,
        },
    )
    assert float(polarizability_result.value) == pytest.approx(
        electron_charge**2 / (3.0 * electron_mass)
    )

    intercomponent_permittivity_result = resolve(
        "physical.lithography.medium_intercomponent_relative_permittivity",
        assignments={
            "physical.lithography.medium_intercomponent_effective_separation": 1.0,
            "physical.lithography.medium_intercomponent_polarizable_site_density_factor": (
                1.0
            ),
            "physical.lithography.medium_electric_polarizability": 0.75 * epsilon_0,
        },
    )
    assert float(intercomponent_permittivity_result.value) == pytest.approx(2.0)

    permittivity_result = resolve(
        "physical.lithography.medium_relative_permittivity",
        assignments={
            "physical.lithography.medium_number_density": 3.0,
            "physical.lithography.medium_electric_polarizability": epsilon_0 / 4.0,
        },
    )
    assert float(permittivity_result.value) == pytest.approx(2.0)

    permeability_result = resolve(
        "physical.lithography.medium_relative_permeability",
        assignments={
            "physical.lithography.medium_magnetic_susceptibility": 0.02,
        },
    )
    assert float(permeability_result.value) == pytest.approx(1.02)


def test_lithography_medium_polarizability_rejects_on_resonance_drive():
    for source_omega in (2.0, -2.0):
        result = resolve(
            "physical.lithography.medium_electric_polarizability",
            assignments={
                "physical.lithography.medium_oscillator_strength": 1.0,
                "physical.lithography.medium_resonance_angular_frequency": 2.0,
                "physical.lithography.source_angular_frequency": source_omega,
            },
        )
        check = next(
            c for c in result.approximation_validity
            if c.equation == "physical.eq.lithography_medium_electric_polarizability"
        )
        assert check.satisfied is False
        assert check.missing == set()


def test_contact_width_and_gate_spacing_have_lower_process_models():
    contact = Registry.variables["physical.process.source_drain_contact_width"]
    assert not contact.is_root_input
    assert {v.name for v in contact.direct_dependencies()} == {
        "physical.lithography.contact_resolution",
        "physical.process.source_drain_contact_bias",
    }

    spacing = Registry.variables["physical.process.gate_contact_spacing"]
    assert not spacing.is_root_input
    assert {v.name for v in spacing.direct_dependencies()} == {
        "physical.process.gate_contact_overlay_budget",
        "physical.process.gate_contact_enclosure_margin",
    }

    contact_result = resolve(
        "physical.process.source_drain_contact_width",
        assignments={
            "physical.lithography.wavelength": 10.0,
            "physical.lithography.numerical_aperture": 2.0,
            "physical.lithography.contact_k1": 1.0,
            "physical.process.source_drain_contact_bias": 1.0,
        },
    )
    assert float(contact_result.value) == pytest.approx(6.0)

    spacing_result = resolve(
        "physical.process.gate_contact_spacing",
        assignments={
            "physical.process.gate_contact_overlay_budget": 0.5,
            "physical.process.gate_contact_enclosure_margin": 1.0,
        },
    )
    assert float(spacing_result.value) == pytest.approx(1.5)


def test_metal_width_and_spacing_depend_on_lithography_resolution_and_bias():
    width = Registry.variables["physical.process.minimum_metal_width"]
    spacing = Registry.variables["physical.process.minimum_metal_spacing"]
    assert not width.is_root_input
    assert not spacing.is_root_input
    assert {v.name for v in width.direct_dependencies()} == {
        "physical.lithography.metal_width_resolution",
        "physical.process.minimum_metal_width_bias",
    }
    assert {v.name for v in spacing.direct_dependencies()} == {
        "physical.lithography.metal_spacing_resolution",
        "physical.process.minimum_metal_spacing_bias",
    }

    width_result = resolve(
        "physical.process.minimum_metal_width",
        assignments={
            "physical.lithography.wavelength": 10.0,
            "physical.lithography.numerical_aperture": 2.0,
            "physical.lithography.metal_width_k1": 0.8,
            "physical.process.minimum_metal_width_bias": 0.25,
        },
    )
    assert float(width_result.value) == pytest.approx(4.25)

    spacing_result = resolve(
        "physical.process.minimum_metal_spacing",
        assignments={
            "physical.lithography.wavelength": 10.0,
            "physical.lithography.numerical_aperture": 2.0,
            "physical.lithography.metal_spacing_k1": 1.0,
            "physical.process.minimum_metal_spacing_bias": -0.5,
        },
    )
    assert float(spacing_result.value) == pytest.approx(4.5)


def test_minimum_metal_pitch_depends_on_width_and_spacing():
    pitch = Registry.variables["physical.process.minimum_metal_pitch"]
    assert not pitch.is_root_input
    deps = {v.name for v in pitch.direct_dependencies()}
    assert deps == {
        "physical.process.minimum_metal_width",
        "physical.process.minimum_metal_spacing",
    }

    result = resolve(
        "physical.process.minimum_metal_pitch",
        assignments={
            "physical.process.minimum_metal_width": 4.0,
            "physical.process.minimum_metal_spacing": 5.0,
        },
    )
    assert float(result.value) == pytest.approx(9.0)


def test_process_geometry_constraints_are_explicit_feasibility_relations():
    expected = {
        "physical.ineq.drawn_gate_length_positive": (
            "physical.process.drawn_gate_length"
        ),
        "physical.ineq.source_drain_contact_width_positive": (
            "physical.process.source_drain_contact_width"
        ),
        "physical.ineq.gate_contact_spacing_nonnegative": (
            "physical.process.gate_contact_spacing"
        ),
        "physical.ineq.contacted_gate_pitch_positive": (
            "physical.process.contacted_gate_pitch"
        ),
        "physical.ineq.minimum_metal_width_positive": (
            "physical.process.minimum_metal_width"
        ),
        "physical.ineq.minimum_metal_spacing_positive": (
            "physical.process.minimum_metal_spacing"
        ),
        "physical.ineq.minimum_metal_pitch_positive": (
            "physical.process.minimum_metal_pitch"
        ),
        "physical.ineq.process_node_length_positive": (
            "physical.process.node_length"
        ),
        "physical.ineq.channel_length_positive": "physical.channel_length",
    }

    for equation_name, variable_name in expected.items():
        eq = Registry.equations[equation_name]
        assert isinstance(eq, Inequality)
        assert eq.role is RelationRole.CONSTRAINT
        assert eq in Registry.variables[variable_name].constraints()
        assert eq.references
        assert not getattr(eq, "_check_units_flag", False)
        relation = eq.as_sympy()
        assert relation is not sp.S.true
        assert isinstance(relation, sp.Rel)


def test_process_geometry_constraints_report_negative_derived_dimensions():
    cases = [
        (
            "physical.process.drawn_gate_length",
            {
                "physical.lithography.gate_resolution": 1.0,
                "physical.process.gate_length_lithography_bias": -2.0,
            },
            -1.0,
            "physical.ineq.drawn_gate_length_positive",
        ),
        (
            "physical.process.source_drain_contact_width",
            {
                "physical.lithography.contact_resolution": 1.0,
                "physical.process.source_drain_contact_bias": -2.0,
            },
            -1.0,
            "physical.ineq.source_drain_contact_width_positive",
        ),
        (
            "physical.process.gate_contact_spacing",
            {
                "physical.process.gate_contact_overlay_budget": -2.0,
                "physical.process.gate_contact_enclosure_margin": 1.0,
            },
            -1.0,
            "physical.ineq.gate_contact_spacing_nonnegative",
        ),
        (
            "physical.process.minimum_metal_width",
            {
                "physical.lithography.metal_width_resolution": 1.0,
                "physical.process.minimum_metal_width_bias": -2.0,
            },
            -1.0,
            "physical.ineq.minimum_metal_width_positive",
        ),
        (
            "physical.process.minimum_metal_spacing",
            {
                "physical.lithography.metal_spacing_resolution": 1.0,
                "physical.process.minimum_metal_spacing_bias": -2.0,
            },
            -1.0,
            "physical.ineq.minimum_metal_spacing_positive",
        ),
        (
            "physical.process.contacted_gate_pitch",
            {
                "physical.process.drawn_gate_length": -4.0,
                "physical.process.source_drain_contact_width": 1.0,
                "physical.process.gate_contact_spacing": 1.0,
            },
            -1.0,
            "physical.ineq.contacted_gate_pitch_positive",
        ),
        (
            "physical.process.minimum_metal_pitch",
            {
                "physical.process.minimum_metal_width": -1.0,
                "physical.process.minimum_metal_spacing": 0.5,
            },
            -0.5,
            "physical.ineq.minimum_metal_pitch_positive",
        ),
        (
            "physical.process.node_length",
            {
                "physical.process.contacted_gate_pitch": 1.0,
                "physical.process.minimum_metal_pitch": 1.0,
                "physical.process.node_geometry_factor": -1.0,
            },
            -1.0,
            "physical.ineq.process_node_length_positive",
        ),
        (
            "physical.channel_length",
            {
                "physical.process.node_length": 1.0,
                "physical.process.gate_length_scale": 1.0,
                "physical.process.gate_length_bias": -2.0,
            },
            -1.0,
            "physical.ineq.channel_length_positive",
        ),
    ]

    for target, assignments, expected_value, constraint_name in cases:
        result = resolve(target, assignments=assignments)
        assert float(result.value) == pytest.approx(expected_value)
        failed_constraint(result, constraint_name)


def test_process_node_validity_stays_symbolic():
    eq = Registry.equations["physical.eq.process_node_from_pitches"]
    assert eq.validity is not True
    assert "CPP_proc" in str(eq.validity)
    assert "MMP_proc" in str(eq.validity)


def test_lithography_validity_stays_symbolic():
    eq = Registry.equations["physical.eq.gate_lithography_resolution"]
    assert eq.validity is not True
    assert "lambda_litho" in str(eq.validity)
    assert "NA_litho" in str(eq.validity)


def test_resolve_channel_length_from_process_geometry():
    result = resolve(
        "physical.channel_length",
        assignments={
            "physical.process.node_length": 4.0,
            "physical.process.gate_length_scale": 1.2,
            "physical.process.gate_length_bias": -0.5,
        },
    )
    assert float(result.value) == pytest.approx(4.3)
    assert any(step.equation == "physical.eq.channel_length_process" for step in result.trace)


def test_resolve_channel_length_through_process_pitch_layer():
    result = resolve(
        "physical.channel_length",
        assignments={
            "physical.process.drawn_gate_length": 1.0,
            "physical.process.source_drain_contact_width": 1.0,
            "physical.process.gate_contact_spacing": 1.0,
            "physical.process.minimum_metal_width": 4.0,
            "physical.process.minimum_metal_spacing": 5.0,
            "physical.process.node_geometry_factor": 2.0,
            "physical.process.gate_length_scale": 0.5,
            "physical.process.gate_length_bias": 1.0,
        },
    )
    assert float(result.value) == pytest.approx(7.0)


def test_resolve_channel_length_through_lithography_layer():
    c = Registry.variables["physics.speed_of_light"].value
    h = Registry.variables["physics.planck"].value
    pupil_radius = 3.0 ** 0.5
    focal_length = 1.0
    numerical_aperture = 3.0 ** 0.5
    wavelength = 10.0
    gate_k1 = 0.8
    gate_cd = gate_k1 * wavelength / numerical_aperture
    contact_cd = gate_k1 * wavelength / numerical_aperture
    metal_width_cd = gate_k1 * wavelength / numerical_aperture
    metal_spacing_cd = gate_k1 * wavelength / numerical_aperture
    cpp = (gate_cd + 1.0) + (contact_cd + 1.0) + 2 * (0.5 + 1.0)
    mmp = metal_width_cd + metal_spacing_cd
    expected = 1.0 + 0.5 * 2.0 * (cpp * mmp) ** 0.5
    result = resolve(
        "physical.channel_length",
        assignments={
            "physical.lithography.photon_energy": h * c / wavelength,
            "physical.lithography.medium_relative_permittivity": 4.0,
            "physical.lithography.medium_relative_permeability": 1.0,
            "physical.lithography.objective_pupil_radius": pupil_radius,
            "physical.lithography.objective_focal_length": focal_length,
            "physical.lithography.gate_k1_aerial_image_contrast_factor": 0.5,
            "physical.lithography.gate_k1_resist_process_factor": 0.7,
            "physical.lithography.gate_k1_mask_error_factor": 0.8,
            "physical.lithography.gate_k1_resolution_enhancement_factor": 1.4,
            "physical.process.gate_length_lithography_bias": 1.0,
            "physical.process.source_drain_contact_bias": 1.0,
            "physical.process.gate_contact_overlay_budget": 0.5,
            "physical.process.gate_contact_enclosure_margin": 1.0,
            "physical.process.minimum_metal_width_bias": 0.0,
            "physical.process.minimum_metal_spacing_bias": 0.0,
            "physical.process.node_geometry_factor": 2.0,
            "physical.process.gate_length_scale": 0.5,
            "physical.process.gate_length_bias": 1.0,
        },
    )
    assert float(result.value) == pytest.approx(expected)
    assert any(
        step.equation == "physical.eq.lithography_gate_k1_from_process_factors"
        for step in result.trace
    )
    assert {
        "physical.eq.contact_k1_from_gate_baseline",
        "physical.eq.metal_width_k1_from_gate_baseline",
        "physical.eq.metal_spacing_k1_from_gate_baseline",
    } <= {step.equation for step in result.trace}


def test_channel_length_process_equation_has_unit_check():
    eq = Registry.equations["physical.eq.channel_length_process"]
    assert getattr(eq, "_check_units_flag", False)
    assert Registry.variables["physical.process.gate_length_bias"].signed is True


def test_process_node_pitch_equation_has_unit_check():
    eq = Registry.equations["physical.eq.process_node_from_pitches"]
    assert getattr(eq, "_check_units_flag", False)


def test_process_pitch_component_equations_have_unit_checks():
    checked = {
        name
        for name, eq in Registry.equations.items()
        if getattr(eq, "_check_units_flag", False)
    }
    assert {
            "physical.eq.lithography_source_proton_count_from_valence_quarks",
            "physical.eq.lithography_source_neutron_count_from_valence_quarks",
            "physical.ineq.lithography_source_valence_quarks_imply_nonnegative_protons",
            "physical.ineq.lithography_source_valence_quarks_imply_positive_protons",
            "physical.ineq.lithography_source_valence_quarks_imply_nonnegative_neutrons",
            "physical.eq.lithography_source_valence_quark_triplet_integrality",
            "physical.eq.lithography_source_atomic_number",
            "physical.eq.lithography_source_isotope_mass_number",
            "physical.eq.lithography_source_mass_number",
            "physical.eq.lithography_source_binding_volume_coefficient_from_shared_nuclear_calibration",
            "physical.eq.lithography_source_binding_surface_coefficient_from_shared_nuclear_calibration",
            "physical.eq.lithography_source_binding_coulomb_coefficient_from_shared_nuclear_calibration",
            "physical.eq.lithography_source_binding_asymmetry_coefficient_from_shared_nuclear_calibration",
            "physical.eq.lithography_source_nuclear_pairing_gap_reference_energy_from_shared_nuclear_calibration",
            "physical.eq.lithography_source_pairing_reference_mass_number",
            "physical.eq.lithography_source_neutron_excess",
            "physical.eq.lithography_source_pairing_sign",
            "physical.eq.lithography_source_nuclear_radius_coefficient",
            "physical.eq.lithography_source_nuclear_saturation_number_density",
            "physical.eq.lithography_source_nuclear_bulk_binding_energy_density",
            "physical.eq.lithography_source_nuclear_surface_tension",
            "physical.eq.lithography_source_binding_pairing_coefficient",
            "physical.eq.lithography_source_nuclear_symmetry_energy_density",
            "physical.eq.lithography_source_binding_volume_term",
            "physical.eq.lithography_source_binding_surface_term",
            "physical.eq.lithography_source_binding_coulomb_term",
            "physical.eq.lithography_source_binding_asymmetry_term",
            "physical.eq.lithography_source_binding_pairing_term",
            "physical.eq.lithography_source_nuclear_binding_energy",
            "physical.eq.lithography_source_nuclear_mass",
            "physical.eq.lithography_source_reduced_mass",
            "physical.eq.lithography_source_reduced_mass_ratio",
            "physical.eq.lithography_source_inner_shell_shielding_factor",
            "physical.eq.lithography_source_same_shell_shielding_factor",
            "physical.eq.lithography_source_transition_principal_quantum_step_from_adjacent_shells",
            "physical.eq.lithography_source_lower_principal_quantum_number",
            "physical.eq.lithography_source_upper_principal_quantum_number",
            "physical.eq.lithography_source_ionization_principal_quantum_number",
            "physical.eq.lithography_source_ionization_inner_shell_screening_electron_count",
            "physical.eq.lithography_source_ionization_same_shell_screening_electron_count",
            "physical.eq.lithography_source_ionization_screening_constant",
            "physical.eq.lithography_source_ionization_effective_nuclear_charge",
            "physical.eq.lithography_source_ionization_energy",
            "physical.eq.lithography_source_ionization_partition_ratio",
            "physical.eq.lithography_source_plasma_drive_beam_wavelength_from_ionization_edge",
            "physical.eq.lithography_source_plasma_absorption_resonance_to_drive_ratio_from_ionization_edge",
            "physical.eq.lithography_source_plasma_absorption_participating_electron_fraction_from_ionization_shell",
            "physical.eq.lithography_source_plasma_absorption_sum_rule_fraction_from_ionization_shell_degeneracy",
            "physical.eq.lithography_source_plasma_absorption_collision_orbital_radius_from_hydrogenic_shell",
            "physical.eq.lithography_source_plasma_absorption_collision_cross_section_from_orbital_area",
            "physical.eq.lithography_source_plasma_pulse_repetition_rate_from_period",
            "physical.eq.lithography_source_plasma_drive_pulse_duration_from_duty_cycle",
            "physical.eq.lithography_source_plasma_drive_pulse_fall_fraction_from_symmetric_ramp",
            "physical.eq.lithography_source_plasma_drive_pulse_flat_fraction_from_ramps",
            "physical.eq.lithography_source_plasma_drive_pulse_temporal_shape_factor_from_trapezoid",
            "physical.ineq.lithography_source_plasma_drive_pulse_ramp_fractions_within_pulse",
            "physical.eq.lithography_source_plasma_drive_peak_intensity_from_fluence",
            "physical.eq.lithography_source_plasma_drive_focus_waist_coefficient_from_gaussian_f_number",
            "physical.eq.lithography_source_plasma_drive_acceptance_half_angle_from_pupil_geometry",
            "physical.eq.lithography_source_plasma_drive_numerical_aperture_from_acceptance_angle",
            "physical.eq.lithography_source_plasma_drive_focus_f_number_from_acceptance_angle",
            "physical.ineq.lithography_source_plasma_drive_pupil_beam_fill_factor_within_unit_interval",
            "physical.eq.lithography_source_plasma_drive_beam_parameter_waist_radius_from_pupil_fill",
            "physical.eq.lithography_source_plasma_drive_beam_parameter_product_from_waist_divergence",
            "physical.ineq.lithography_source_plasma_drive_beam_parameter_product_diffraction_floor",
            "physical.eq.lithography_source_plasma_drive_beam_quality_factor_from_beam_parameter_product",
            "physical.ineq.lithography_source_plasma_drive_beam_quality_factor_diffraction_limit",
            "physical.eq.lithography_source_plasma_drive_spot_radius_from_focus",
            "physical.eq.lithography_source_plasma_drive_rayleigh_range_from_spot_geometry",
            "physical.eq.lithography_source_plasma_drive_confocal_length_from_rayleigh_range",
            "physical.eq.lithography_source_plasma_drive_spot_axis_ratio_from_circular_convention",
            "physical.eq.lithography_source_plasma_drive_spot_area_fill_factor_from_full_area_convention",
            "physical.eq.lithography_source_plasma_drive_spot_shape_factor_from_ellipse",
            "physical.eq.lithography_source_plasma_drive_spot_area_from_radius",
            "physical.eq.lithography_source_plasma_pulse_energy_from_intensity_area_duration",
            "physical.ineq.lithography_source_plasma_pulse_duration_within_period",
            "physical.eq.lithography_source_plasma_drive_power_from_pulses",
            "physical.eq.lithography_source_plasma_species_number_density_from_ideal_gas",
            "physical.eq.lithography_source_plasma_column_expansion_speed_factor_from_monatomic_sound_speed",
            "physical.eq.lithography_source_plasma_column_radial_expansion_speed_from_species_thermal_speed",
            "physical.eq.lithography_source_plasma_column_radius_expansion_factor_from_radial_speed",
            "physical.eq.lithography_source_plasma_column_radius_from_drive_spot",
            "physical.eq.lithography_source_plasma_column_aspect_ratio_from_confocal_length",
            "physical.eq.lithography_source_plasma_column_length_from_aspect_ratio",
            "physical.eq.lithography_source_plasma_active_fill_factor_from_ideal_column_convention",
            "physical.eq.lithography_source_plasma_active_volume_from_column_geometry",
            "physical.eq.lithography_source_plasma_drive_beam_angular_frequency",
            "physical.eq.lithography_source_plasma_absorption_path_direction_cosine_from_acceptance_angle",
            "physical.eq.lithography_source_plasma_absorption_path_shape_factor_from_direction_cosine",
            "physical.eq.lithography_source_plasma_absorption_path_length_from_column",
            "physical.eq.lithography_source_plasma_absorption_resonance_from_drive_ratio",
            "physical.eq.lithography_source_plasma_absorption_damping_rate_from_species_collision",
            "physical.eq.lithography_source_plasma_absorption_quality_factor_from_collision_damping",
            "physical.eq.lithography_source_plasma_absorption_oscillator_strength_from_source_charge",
            "physical.eq.lithography_source_plasma_absorption_cross_section_from_lorentz_oscillator",
            "physical.eq.lithography_source_plasma_absorption_optical_depth",
            "physical.eq.lithography_source_plasma_drive_energy_absorption_fraction_from_optical_depth",
            "physical.eq.lithography_source_plasma_drive_centroid_offset_to_column_radius_ratio_from_coaxial_convention",
            "physical.eq.lithography_source_plasma_drive_pointing_overlap_factor_from_offset",
            "physical.eq.lithography_source_plasma_drive_transverse_overlap_factor_from_area_ratio",
            "physical.ineq.lithography_source_plasma_drive_spot_area_within_column_cross_section",
            "physical.eq.lithography_source_plasma_drive_spatial_overlap_factor_from_geometry",
            "physical.eq.lithography_source_plasma_active_response_duration_from_drive_ratio",
            "physical.eq.lithography_source_plasma_drive_timing_offset_fraction_from_synchronized_convention",
            "physical.eq.lithography_source_plasma_drive_timing_offset_duration_from_fraction",
            "physical.eq.lithography_source_plasma_drive_temporal_duration_match_factor",
            "physical.eq.lithography_source_plasma_drive_temporal_alignment_factor_from_timing_offset",
            "physical.eq.lithography_source_plasma_drive_temporal_overlap_factor_from_duration_and_alignment",
            "physical.eq.lithography_source_plasma_drive_overlap_factor_from_spatial_temporal",
            "physical.eq.lithography_source_plasma_absorption_efficiency_from_overlap_optical_depth_heating",
            "physical.eq.lithography_source_plasma_energy_loss_path_direction_cosine_from_acceptance_angle",
            "physical.eq.lithography_source_plasma_energy_loss_path_factor_from_direction_cosine",
            "physical.eq.lithography_source_plasma_energy_loss_path_length_from_radius",
            "physical.eq.lithography_source_plasma_species_particle_mass_from_nuclear_counts",
            "physical.eq.lithography_source_plasma_species_thermal_speed_from_gas_temperature",
            "physical.eq.lithography_source_plasma_energy_loss_transport_speed_factor_from_mass_ratio",
            "physical.eq.lithography_source_plasma_energy_loss_speed_from_species_thermal_speed",
            "physical.eq.lithography_source_plasma_energy_confinement_time_from_loss_path",
            "physical.eq.lithography_source_plasma_active_lifetime_to_drive_pulse_ratio_from_energy_confinement_time",
            "physical.eq.lithography_source_plasma_free_electron_yield_per_source_particle_from_inventory_charge_fraction",
            "physical.eq.lithography_source_plasma_free_electron_count_from_species_inventory",
            "physical.eq.lithography_source_plasma_absorbed_power_from_drive",
            "physical.eq.lithography_source_plasma_electron_internal_energy_from_confinement",
            "physical.eq.lithography_source_plasma_electron_temperature_from_internal_energy",
            "physical.eq.lithography_source_plasma_electron_number_density_from_count_volume",
            "physical.eq.lithography_source_plasma_electron_mean_kinetic_energy_from_temperature",
            "physical.eq.lithography_source_plasma_debye_length_from_temperature_density",
            "physical.eq.lithography_source_saha_thermal_number_density",
            "physical.eq.lithography_source_saha_ionization_ratio",
            "physical.eq.lithography_source_saha_ionization_fraction",
            "physical.eq.lithography_source_ion_charge_state",
            "physical.eq.lithography_source_bound_electron_count",
            "physical.eq.lithography_source_transition_shell_capacity",
            "physical.eq.lithography_source_inner_closed_shell_capacity",
            "physical.eq.lithography_source_outer_shell_electron_count",
            "physical.eq.lithography_source_inner_closed_shell_electron_count",
            "physical.eq.lithography_source_transition_shell_occupancy",
            "physical.eq.lithography_source_same_shell_screening_electron_count",
            "physical.eq.lithography_source_inner_shell_screening_electron_count",
            "physical.eq.lithography_source_screening_constant",
            "physical.eq.lithography_source_effective_nuclear_charge",
            "physical.eq.lithography_source_transition_energy",
            "physical.eq.lithography_photon_energy_from_source_transition",
            "physical.eq.lithography_photon_frequency",
            "physical.eq.lithography_wavelength_from_frequency",
            "physical.eq.lithography_source_angular_frequency",
            "physical.eq.lithography_medium_component_a_proton_count_from_valence_quarks",
            "physical.eq.lithography_medium_component_a_neutron_count_from_valence_quarks",
            "physical.eq.lithography_medium_component_b_proton_count_from_valence_quarks",
            "physical.eq.lithography_medium_component_b_neutron_count_from_valence_quarks",
            "physical.ineq.lithography_medium_component_a_valence_quarks_imply_nonnegative_protons",
            "physical.ineq.lithography_medium_component_a_valence_quarks_imply_positive_protons",
            "physical.ineq.lithography_medium_component_a_valence_quarks_imply_nonnegative_neutrons",
            "physical.eq.lithography_medium_component_a_valence_quark_triplet_integrality",
            "physical.ineq.lithography_medium_component_b_valence_quarks_imply_nonnegative_protons",
            "physical.ineq.lithography_medium_component_b_valence_quarks_imply_positive_protons",
            "physical.ineq.lithography_medium_component_b_valence_quarks_imply_nonnegative_neutrons",
            "physical.eq.lithography_medium_component_b_valence_quark_triplet_integrality",
            "physical.eq.lithography_medium_component_a_atomic_number",
            "physical.eq.lithography_medium_component_b_atomic_number",
            "physical.eq.lithography_medium_component_a_isotope_mass_number",
            "physical.eq.lithography_medium_component_b_isotope_mass_number",
            "physical.eq.lithography_medium_component_nuclear_radius_coefficient",
            "physical.eq.lithography_medium_component_nuclear_saturation_number_density",
            "physical.eq.lithography_medium_component_nuclear_bulk_binding_energy_density",
            "physical.eq.lithography_medium_component_nuclear_surface_tension",
            "physical.eq.lithography_medium_component_nuclear_symmetry_energy_density",
            "physical.eq.lithography_medium_component_a_neutron_excess",
            "physical.eq.lithography_medium_component_b_neutron_excess",
            "physical.eq.lithography_medium_component_a_pairing_sign",
            "physical.eq.lithography_medium_component_b_pairing_sign",
            "physical.eq.lithography_medium_component_a_pairing_reference_mass_number",
            "physical.eq.lithography_medium_component_b_pairing_reference_mass_number",
            "physical.eq.lithography_medium_component_a_binding_pairing_coefficient",
            "physical.eq.lithography_medium_component_b_binding_pairing_coefficient",
            "physical.eq.lithography_medium_component_a_binding_volume_term",
            "physical.eq.lithography_medium_component_b_binding_volume_term",
            "physical.eq.lithography_medium_component_a_binding_surface_term",
            "physical.eq.lithography_medium_component_b_binding_surface_term",
            "physical.eq.lithography_medium_component_a_binding_coulomb_term",
            "physical.eq.lithography_medium_component_b_binding_coulomb_term",
            "physical.eq.lithography_medium_component_a_binding_asymmetry_term",
            "physical.eq.lithography_medium_component_b_binding_asymmetry_term",
            "physical.eq.lithography_medium_component_a_binding_pairing_term",
            "physical.eq.lithography_medium_component_b_binding_pairing_term",
            "physical.eq.lithography_medium_component_a_binding_energy",
            "physical.eq.lithography_medium_component_b_binding_energy",
            "physical.ineq.lithography_medium_formula_unit_intercomponent_charge_transfer_at_most_component_a_electron_inventory",
            "physical.ineq.lithography_medium_formula_unit_intercomponent_charge_transfer_at_most_component_b_electron_inventory",
            "physical.eq.lithography_medium_intercomponent_charge_unit_from_formula_unit_charge_transfer",
            "physical.eq.lithography_medium_component_a_effective_intercomponent_charge_number",
            "physical.eq.lithography_medium_component_b_effective_intercomponent_charge_number",
            "physical.eq.lithography_medium_formula_unit_intercomponent_pair_count",
            "physical.eq.lithography_medium_component_a_effective_intercomponent_radius",
            "physical.eq.lithography_medium_component_b_effective_intercomponent_radius",
            "physical.eq.lithography_medium_intercomponent_gap_from_radius_fraction",
            "physical.eq.lithography_medium_intercomponent_effective_separation",
            "physical.eq.lithography_medium_formula_unit_intercomponent_binding_energy",
            "physical.eq.lithography_medium_formula_unit_proton_count",
            "physical.eq.lithography_medium_formula_unit_neutron_count",
            "physical.eq.lithography_medium_formula_unit_electron_count",
            "physical.eq.lithography_medium_formula_unit_binding_energy",
            "physical.eq.lithography_medium_formula_unit_rest_mass",
            "physical.eq.lithography_medium_molar_mass",
            "physical.eq.lithography_medium_particle_mass",
            "physical.ineq.lithography_medium_formula_unit_packing_length_scale_factor_at_least_unity",
            "physical.eq.lithography_medium_formula_unit_packing_length_from_intercomponent_separation_scale",
            "physical.eq.lithography_medium_formula_unit_packing_volume",
            "physical.eq.lithography_medium_mass_density_from_packing",
            "physical.eq.lithography_medium_number_density_from_mass",
            "physical.eq.lithography_medium_polarizable_electron_fraction_from_count",
            "physical.ineq.lithography_medium_polarizable_electron_count_within_formula_unit",
            "physical.eq.lithography_medium_oscillator_sum_rule_fraction_from_count",
            "physical.ineq.lithography_medium_dominant_oscillator_electron_count_within_polarizable_count",
            "physical.eq.lithography_medium_resonance_to_source_frequency_ratio_from_energy",
            "physical.ineq.lithography_medium_resonance_energy_above_source_photon_energy",
            "physical.eq.lithography_medium_resonance_angular_frequency_from_source_ratio",
            "physical.eq.lithography_medium_oscillator_strength_from_formula_electrons",
            "physical.eq.lithography_medium_electric_polarizability",
            "physical.eq.lithography_medium_intercomponent_lorentz_lorenz_factor",
            "physical.eq.lithography_medium_intercomponent_relative_permittivity_from_local_lorentz_lorenz",
            "physical.eq.lithography_medium_refractive_index",
            "physical.eq.lithography_acceptance_half_angle",
            "physical.ineq.lithography_acceptance_half_angle_within_forward_half_space",
            "physical.eq.lithography_numerical_aperture",
            "physical.ineq.lithography_numerical_aperture_within_medium_index",
            "physical.eq.lithography_gate_k1_from_process_factors",
        "physical.eq.gate_lithography_resolution",
        "physical.eq.contact_lithography_resolution",
        "physical.eq.metal_width_lithography_resolution",
        "physical.eq.metal_spacing_lithography_resolution",
        "physical.eq.drawn_gate_length",
        "physical.eq.source_drain_contact_width",
        "physical.eq.gate_contact_spacing",
        "physical.eq.minimum_metal_width",
        "physical.eq.minimum_metal_spacing",
        "physical.eq.contacted_gate_pitch",
        "physical.eq.minimum_metal_pitch",
    } <= checked
