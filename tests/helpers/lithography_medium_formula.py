"""Shared fixture for the lithography medium formula-unit tests.

A "formula unit" is one repeating chemical unit of the resist medium — here
two component-A atoms and one component-B atom. The tests need a fully
worked numeric example: quark counts, liquid-drop binding energies, an
intercomponent Coulomb bond, and the resulting formula mass and density.
Building that example by hand in every test would be error-prone, so this
module computes it once (from the registry's physical constants) and hands
tests a frozen ``MediumFormulaCase`` with both the variable assignments and
the expected results.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest
import sympy as sp

from gpu_stack import Registry
from tests.helpers.lithography import (
    expected_medium_component_binding_energy,
    medium_component_quark_assignments,
    medium_liquid_drop_root_assignments,
)


MEDIUM_FORMULA_VARIABLE_NAMES = {
    "component_a_stoich": (
        "physical.lithography.medium_component_a_stoichiometric_count"
    ),
    "component_b_stoich": (
        "physical.lithography.medium_component_b_stoichiometric_count"
    ),
    "component_a_up_quarks": (
        "physical.lithography.medium_component_a_valence_up_quark_count"
    ),
    "component_a_down_quarks": (
        "physical.lithography.medium_component_a_valence_down_quark_count"
    ),
    "component_b_up_quarks": (
        "physical.lithography.medium_component_b_valence_up_quark_count"
    ),
    "component_b_down_quarks": (
        "physical.lithography.medium_component_b_valence_down_quark_count"
    ),
    "component_a_protons": "physical.lithography.medium_component_a_proton_count",
    "component_b_protons": "physical.lithography.medium_component_b_proton_count",
    "component_a_neutrons": "physical.lithography.medium_component_a_neutron_count",
    "component_b_neutrons": "physical.lithography.medium_component_b_neutron_count",
    "component_a_atomic_number": (
        "physical.lithography.medium_component_a_atomic_number"
    ),
    "component_b_atomic_number": (
        "physical.lithography.medium_component_b_atomic_number"
    ),
    "component_a_mass_number": (
        "physical.lithography.medium_component_a_isotope_mass_number"
    ),
    "component_b_mass_number": (
        "physical.lithography.medium_component_b_isotope_mass_number"
    ),
    "component_a_binding": "physical.lithography.medium_component_a_binding_energy",
    "component_b_binding": "physical.lithography.medium_component_b_binding_energy",
    "medium_saturation_density": (
        "physical.lithography.medium_component_nuclear_saturation_number_density"
    ),
    "medium_radius_coeff": (
        "physical.lithography.medium_component_nuclear_radius_coefficient"
    ),
    "medium_bulk_binding_density": (
        "physical.lithography.medium_component_nuclear_bulk_binding_energy_density"
    ),
    "medium_volume_coeff": (
        "physical.lithography.medium_component_binding_volume_coefficient"
    ),
    "medium_surface_tension": (
        "physical.lithography.medium_component_nuclear_surface_tension"
    ),
    "medium_surface_coeff": (
        "physical.lithography.medium_component_binding_surface_coefficient"
    ),
    "medium_symmetry_density": (
        "physical.lithography.medium_component_nuclear_symmetry_energy_density"
    ),
    "medium_asymmetry_coeff": (
        "physical.lithography.medium_component_binding_asymmetry_coefficient"
    ),
    "medium_pairing_gap": (
        "physical.lithography.medium_component_nuclear_pairing_gap_reference_energy"
    ),
    "medium_coulomb_coeff": (
        "physical.lithography.medium_component_binding_coulomb_coefficient"
    ),
    "shared_volume_coeff": "physical.lithography.nuclear_binding_volume_coefficient",
    "shared_surface_coeff": "physical.lithography.nuclear_binding_surface_coefficient",
    "shared_coulomb_coeff": "physical.lithography.nuclear_binding_coulomb_coefficient",
    "shared_asymmetry_coeff": (
        "physical.lithography.nuclear_binding_asymmetry_coefficient"
    ),
    "shared_pairing_gap": "physical.lithography.nuclear_pairing_gap_reference_energy",
    "component_a_intercomponent_charge": (
        "physical.lithography.medium_component_a_effective_intercomponent_charge_number"
    ),
    "component_b_intercomponent_charge": (
        "physical.lithography.medium_component_b_effective_intercomponent_charge_number"
    ),
    "intercomponent_charge_unit": (
        "physical.lithography.medium_intercomponent_charge_unit"
    ),
    "intercomponent_charge_transfer_count": (
        "physical.lithography.medium_formula_unit_intercomponent_charge_transfer_electron_count"
    ),
    "intercomponent_pair_count": (
        "physical.lithography.medium_formula_unit_intercomponent_pair_count"
    ),
    "intercomponent_separation": (
        "physical.lithography.medium_intercomponent_effective_separation"
    ),
    "component_a_intercomponent_radius_scale": (
        "physical.lithography.medium_component_a_intercomponent_radius_scale_factor"
    ),
    "component_b_intercomponent_radius_scale": (
        "physical.lithography.medium_component_b_intercomponent_radius_scale_factor"
    ),
    "component_a_intercomponent_radius": (
        "physical.lithography.medium_component_a_effective_intercomponent_radius"
    ),
    "component_b_intercomponent_radius": (
        "physical.lithography.medium_component_b_effective_intercomponent_radius"
    ),
    "intercomponent_gap_fraction": (
        "physical.lithography.medium_intercomponent_gap_fraction"
    ),
    "intercomponent_gap": "physical.lithography.medium_intercomponent_gap",
    "intercomponent_relative_permittivity": (
        "physical.lithography.medium_intercomponent_relative_permittivity"
    ),
    "intercomponent_polarizable_site_density_factor": (
        "physical.lithography.medium_intercomponent_polarizable_site_density_factor"
    ),
    "intercomponent_lorentz_lorenz_factor": (
        "physical.lithography.medium_intercomponent_lorentz_lorenz_factor"
    ),
    "intercomponent_binding": (
        "physical.lithography.medium_formula_unit_intercomponent_binding_energy"
    ),
    "proton_count": "physical.lithography.medium_formula_unit_proton_count",
    "neutron_count": "physical.lithography.medium_formula_unit_neutron_count",
    "electron_count": "physical.lithography.medium_formula_unit_electron_count",
    "binding_energy": "physical.lithography.medium_formula_unit_binding_energy",
    "formula_mass": "physical.lithography.medium_formula_unit_rest_mass",
    "molar_mass": "physical.lithography.medium_molar_mass",
    "particle_mass": "physical.lithography.medium_particle_mass",
    "packing_length": "physical.lithography.medium_formula_unit_packing_length",
    "packing_length_scale_factor": (
        "physical.lithography.medium_formula_unit_packing_length_scale_factor"
    ),
    "packing_fill_factor": (
        "physical.lithography.medium_formula_unit_packing_fill_factor"
    ),
    "packing_volume": "physical.lithography.medium_formula_unit_packing_volume",
    "mass_density": "physical.lithography.medium_mass_density",
    "number_density": "physical.lithography.medium_number_density",
}


@dataclass(frozen=True)
class MediumFormulaCase:
    assignments: dict[str, float]
    component_a_expected_binding: float
    component_b_expected_binding: float
    expected_intercomponent_binding: float
    expected_intercomponent_charge_unit: float
    expected_component_a_intercomponent_charge: float
    expected_component_b_intercomponent_charge: float
    expected_intercomponent_pair_count: int
    intercomponent_test_separation: float
    component_a_intercomponent_test_radius: float
    component_b_intercomponent_test_radius: float
    intercomponent_test_gap: float
    expected_binding_energy: float
    expected_formula_mass: float
    avogadro: float
    packing_length_scale_factor_test: float


def medium_formula_variables():
    return {
        key: Registry.variables[variable_name]
        for key, variable_name in MEDIUM_FORMULA_VARIABLE_NAMES.items()
    }


def dependency_names(variable, *, include_constraints=False):
    return {
        v.name
        for v in variable.direct_dependencies(include_constraints=include_constraints)
    }


@pytest.fixture
def medium_formula_case():
    proton_mass = Registry.variables["physics.proton_mass"].value
    neutron_mass = Registry.variables["physics.neutron_mass"].value
    electron_mass = Registry.variables["physics.electron_mass"].value
    speed_of_light = Registry.variables["physics.speed_of_light"].value
    elementary_charge = Registry.variables["physics.elementary_charge"].value
    vacuum_permittivity = Registry.variables["physics.vacuum_permittivity"].value
    avogadro = Registry.variables["physics.avogadro"].value
    component_a_expected_binding = expected_medium_component_binding_energy(1, 0)
    component_b_expected_binding = expected_medium_component_binding_energy(8, 9)
    expected_intercomponent_binding = 5.0e-12
    intercomponent_charge_transfer_count_test = 2.0
    expected_intercomponent_charge_unit = 1.0
    expected_component_a_intercomponent_charge = 1.0
    expected_component_b_intercomponent_charge = -2.0
    expected_intercomponent_pair_count = 2
    intercomponent_test_separation = (
        -expected_intercomponent_pair_count
        * expected_component_a_intercomponent_charge
        * expected_component_b_intercomponent_charge
        * elementary_charge**2
        / (4.0 * float(sp.pi) * vacuum_permittivity * expected_intercomponent_binding)
    )
    packing_length_scale_factor_test = 0.5 / intercomponent_test_separation
    component_a_intercomponent_test_radius = intercomponent_test_separation / 4.0
    component_b_intercomponent_test_radius = intercomponent_test_separation / 4.0
    intercomponent_test_gap = intercomponent_test_separation / 2.0
    medium_radius_coeff_test = (
        3.0
        * elementary_charge**2
        / (20.0 * float(sp.pi) * vacuum_permittivity * 0.5e-13)
    )
    component_a_intercomponent_radius_scale_test = (
        component_a_intercomponent_test_radius
        / (medium_radius_coeff_test * 1.0 ** (1.0 / 3.0))
    )
    component_b_intercomponent_radius_scale_test = (
        component_b_intercomponent_test_radius
        / (medium_radius_coeff_test * 17.0 ** (1.0 / 3.0))
    )
    intercomponent_gap_fraction_test = (
        intercomponent_test_gap
        / (
            component_a_intercomponent_test_radius
            + component_b_intercomponent_test_radius
        )
    )
    expected_binding_energy = (
        2 * component_a_expected_binding
        + component_b_expected_binding
        + expected_intercomponent_binding
    )
    expected_formula_mass = (
        10 * proton_mass
        + 9 * neutron_mass
        + 10 * electron_mass
        - expected_binding_energy / speed_of_light**2
    )

    assignments = {
        "physical.lithography.medium_component_a_stoichiometric_count": 2,
        **medium_component_quark_assignments("a", 1, 0),
        "physical.lithography.medium_component_b_stoichiometric_count": 1,
        **medium_component_quark_assignments("b", 8, 9),
        **medium_liquid_drop_root_assignments(),
        "physical.lithography.medium_formula_unit_intercomponent_charge_transfer_electron_count": (
            intercomponent_charge_transfer_count_test
        ),
        "physical.lithography.medium_component_a_intercomponent_radius_scale_factor": (
            component_a_intercomponent_radius_scale_test
        ),
        "physical.lithography.medium_component_b_intercomponent_radius_scale_factor": (
            component_b_intercomponent_radius_scale_test
        ),
        "physical.lithography.medium_intercomponent_gap_fraction": (
            intercomponent_gap_fraction_test
        ),
        "physical.lithography.medium_intercomponent_polarizable_site_density_factor": (
            1.0
        ),
        "physical.lithography.medium_electric_polarizability": 0.0,
    }

    return MediumFormulaCase(
        assignments=assignments,
        component_a_expected_binding=component_a_expected_binding,
        component_b_expected_binding=component_b_expected_binding,
        expected_intercomponent_binding=expected_intercomponent_binding,
        expected_intercomponent_charge_unit=expected_intercomponent_charge_unit,
        expected_component_a_intercomponent_charge=(
            expected_component_a_intercomponent_charge
        ),
        expected_component_b_intercomponent_charge=(
            expected_component_b_intercomponent_charge
        ),
        expected_intercomponent_pair_count=expected_intercomponent_pair_count,
        intercomponent_test_separation=intercomponent_test_separation,
        component_a_intercomponent_test_radius=component_a_intercomponent_test_radius,
        component_b_intercomponent_test_radius=component_b_intercomponent_test_radius,
        intercomponent_test_gap=intercomponent_test_gap,
        expected_binding_energy=expected_binding_energy,
        expected_formula_mass=expected_formula_mass,
        avogadro=avogadro,
        packing_length_scale_factor_test=packing_length_scale_factor_test,
    )
