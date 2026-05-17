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
from tests.helpers.lithography import (
    expected_medium_component_binding_energy,
    failed_constraint,
    medium_component_quark_assignments,
    medium_intercomponent_binding_root_assignments,
    medium_liquid_drop_root_assignments,
    source_quark_assignments,
)


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
