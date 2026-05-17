"""Shared lithography setup and expectation helpers."""

from __future__ import annotations

import sympy as sp

from gpu_stack import Registry


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
