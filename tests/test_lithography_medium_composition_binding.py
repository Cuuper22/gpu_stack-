"""
tests/test_lithography_medium_composition_binding.py
====================================================

The lithography imaging medium is modeled as a two-component material (a and
b), and each component's nuclear binding energy comes from the liquid-drop
model — the classic formula that treats a nucleus like a charged liquid drop
with volume, surface, Coulomb, asymmetry, and pairing terms. This module
verifies that chain end to end: given quark-level composition and the four
root liquid-drop coefficients, the graph must derive the nuclear radius
coefficient, saturation density, bulk binding energy density, surface
tension, and symmetry energy density with the exact algebraic relationships
(for example, the radius coefficient falls out of the Coulomb coefficient via
3*e^2 / (20*pi*eps0*a_C)). It also checks the pairing sign convention:
+1 for even-even nuclei, -1 for odd-odd, 0 for mixed parity.
"""

import pytest
import sympy as sp

from gpu_stack import Registry, resolve
from tests.helpers.lithography import (
    expected_medium_component_binding_energy,
    medium_component_quark_assignments,
    medium_liquid_drop_root_assignments,
)


def test_lithography_medium_component_liquid_drop_binding_terms():
    volume_coeff = 10.0e-13
    surface_coeff = 2.0e-13
    coulomb_coeff = 0.5e-13
    asymmetry_coeff = 3.0e-13
    assignments = {
        **medium_component_quark_assignments("a", 2, 2),
        **medium_liquid_drop_root_assignments(
            volume_coeff=volume_coeff,
            surface_coeff=surface_coeff,
            coulomb_coeff=coulomb_coeff,
            asymmetry_coeff=asymmetry_coeff,
        ),
    }
    elementary_charge = Registry.variables["physics.elementary_charge"].value
    vacuum_permittivity = Registry.variables["physics.vacuum_permittivity"].value
    expected_radius_coeff = (
        3.0
        * elementary_charge**2
        / (20.0 * float(sp.pi) * vacuum_permittivity * coulomb_coeff)
    )
    expected_saturation_density = 3.0 / (
        4.0 * float(sp.pi) * expected_radius_coeff**3
    )
    assert float(resolve(
        "physical.lithography.medium_component_nuclear_radius_coefficient",
        assignments=assignments,
    ).value) == pytest.approx(expected_radius_coeff)
    assert float(resolve(
        "physical.lithography.medium_component_nuclear_saturation_number_density",
        assignments=assignments,
    ).value) == pytest.approx(expected_saturation_density)
    assert float(resolve(
        "physical.lithography.medium_component_nuclear_bulk_binding_energy_density",
        assignments=assignments,
    ).value) == pytest.approx(volume_coeff * expected_saturation_density)
    assert float(resolve(
        "physical.lithography.medium_component_nuclear_surface_tension",
        assignments=assignments,
    ).value) == pytest.approx(
        surface_coeff / (4.0 * float(sp.pi) * expected_radius_coeff**2)
    )
    assert float(resolve(
        "physical.lithography.medium_component_nuclear_symmetry_energy_density",
        assignments=assignments,
    ).value) == pytest.approx(asymmetry_coeff * expected_saturation_density)
    assert float(resolve(
        "physical.lithography.medium_component_binding_coulomb_coefficient",
        assignments=assignments,
    ).value) == pytest.approx(coulomb_coeff)
    assert float(resolve(
        "physical.lithography.medium_component_binding_volume_coefficient",
        assignments=assignments,
    ).value) == pytest.approx(volume_coeff)
    assert float(resolve(
        "physical.lithography.medium_component_binding_surface_coefficient",
        assignments=assignments,
    ).value) == pytest.approx(surface_coeff)
    assert float(resolve(
        "physical.lithography.medium_component_binding_asymmetry_coefficient",
        assignments=assignments,
    ).value) == pytest.approx(asymmetry_coeff)
    assert float(resolve(
        "physical.lithography.medium_component_a_pairing_reference_mass_number",
        assignments=assignments,
    ).value) == pytest.approx(4.0)
    assert float(resolve(
        "physical.lithography.medium_component_a_binding_pairing_coefficient",
        assignments=assignments,
    ).value) == pytest.approx(4.0e-13)
    assert float(resolve(
        "physical.lithography.medium_component_a_pairing_sign",
        assignments=medium_component_quark_assignments("a", 2, 2),
    ).value) == pytest.approx(1.0)
    assert float(resolve(
        "physical.lithography.medium_component_a_pairing_sign",
        assignments=medium_component_quark_assignments("a", 3, 3),
    ).value) == pytest.approx(-1.0)
    assert float(resolve(
        "physical.lithography.medium_component_a_pairing_sign",
        assignments=medium_component_quark_assignments("a", 2, 3),
    ).value) == pytest.approx(0.0)

    component_a_binding = resolve(
        "physical.lithography.medium_component_a_binding_energy",
        assignments=assignments,
    )
    assert float(component_a_binding.value) == pytest.approx(
        expected_medium_component_binding_energy(2, 2)
    )

    component_b_binding = resolve(
        "physical.lithography.medium_component_b_binding_energy",
        assignments={
            **medium_component_quark_assignments("b", 3, 3),
            **medium_liquid_drop_root_assignments(),
        },
    )
    assert float(component_b_binding.value) == pytest.approx(
        expected_medium_component_binding_energy(3, 3)
    )
