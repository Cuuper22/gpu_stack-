"""Tests for the lithography medium-response model.

Light passing through the immersion medium (water, in the reference case)
bends according to the medium's refractive index, and the graph builds that
index from first principles: nuclear composition gives particle mass, packing
geometry gives mass and number density, a Lorentz-oscillator model gives
electric polarizability, and the Lorentz-Lorenz relation turns density times
polarizability into relative permittivity.

The big test walks this whole chain. It pins which variables are root inputs
versus derived, pins every derived variable's exact dependency set, checks
that electron-count and resonance-energy roots carry unit-checked constraints,
and then resolves the chain numerically against hand-computed expectations —
including the mass defect from binding energy (E/c^2) in the particle mass.

The second test guards the model's validity limit: the Lorentz-oscillator
polarizability formula diverges when the drive frequency hits the resonance,
so resolving at (or at minus) the resonance frequency must flag the
approximation-validity check as unsatisfied rather than report a number.
"""

import pytest

from gpu_stack import Registry, resolve
from gpu_stack.core import Inequality, RelationRole
from tests.helpers.lithography import (
    expected_medium_component_binding_energy,
    medium_component_quark_assignments,
    medium_intercomponent_binding_root_assignments,
    medium_liquid_drop_root_assignments,
)


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
