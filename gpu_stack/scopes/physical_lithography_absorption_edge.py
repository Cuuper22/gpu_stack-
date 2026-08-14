"""
scopes/physical_lithography_absorption_edge.py
==============================================

Bridge that ties source-plasma absorption inputs to electronic-shell
structure. The plasma absorption model needs a resonance-frequency ratio and
oscillator-strength fractions; physically these come from the ionization
edge of the emitting ion, which the electronic-structure layer knows about.
Making the low-level absorption module import the electronic-structure layer
would create a cycle, so this module closes the loop from above instead,
equating the absorption knobs to shell-derived quantities.
"""

import sympy as sp

from ..constants import BOHR_RADIUS, HBAR, SPEED_OF_LIGHT
from ..core import Approximation, Registry, ge, gt, le, lt, valid_all, var
from ..core.units import METER


_vars = Registry.variables

lithography_source_ionization_energy = _vars[
    "physical.lithography.source_ionization_energy"
]
lithography_source_ionization_same_shell_screening_electron_count = _vars[
    "physical.lithography.source_ionization_same_shell_screening_electron_count"
]
lithography_source_ionization_principal_quantum_number = _vars[
    "physical.lithography.source_ionization_principal_quantum_number"
]
lithography_source_ionization_effective_nuclear_charge = _vars[
    "physical.lithography.source_ionization_effective_nuclear_charge"
]
lithography_source_transition_shell_capacity = _vars[
    "physical.lithography.source_transition_shell_capacity"
]
lithography_source_proton_count = _vars["physical.lithography.source_proton_count"]
lithography_source_plasma_drive_beam_angular_frequency = _vars[
    "physical.lithography.source_plasma_drive_beam_angular_frequency"
]
lithography_source_plasma_drive_beam_wavelength = _vars[
    "physical.lithography.source_plasma_drive_beam_wavelength"
]
lithography_source_plasma_drive_edge_detuning_ratio = _vars[
    "physical.lithography.source_plasma_drive_edge_detuning_ratio"
]
lithography_source_plasma_absorption_resonance_to_drive_ratio = _vars[
    "physical.lithography.source_plasma_absorption_resonance_to_drive_ratio"
]
lithography_source_plasma_absorption_participating_electron_fraction = _vars[
    "physical.lithography.source_plasma_absorption_participating_electron_fraction"
]
lithography_source_plasma_absorption_sum_rule_fraction = _vars[
    "physical.lithography.source_plasma_absorption_sum_rule_fraction"
]
lithography_source_plasma_absorption_collision_cross_section = _vars[
    "physical.lithography.source_plasma_absorption_collision_cross_section"
]

LITHOGRAPHY_SOURCE_ABSORPTION_EDGE_REF = (
    lithography_source_ionization_energy.references[0]
)


lithography_source_plasma_absorption_collision_orbital_radius = var(
    "physical.lithography.source_plasma_absorption_collision_orbital_radius",
    "r_orb_abs_collision_litho_src",
    "m",
    "Hydrogenic orbital radius scale used for source-plasma absorption collision damping.",
    scope="physical",
    positive=True,
    sp_units=METER,
    references=[LITHOGRAPHY_SOURCE_ABSORPTION_EDGE_REF],
)


eq_lithography_source_plasma_drive_beam_wavelength_from_ionization_edge = Approximation(
    "physical.eq.lithography_source_plasma_drive_beam_wavelength_from_ionization_edge",
    lithography_source_plasma_drive_beam_wavelength.symbol,
    (
        sp.Integer(2)
        * sp.pi
        * HBAR.symbol
        * SPEED_OF_LIGHT.symbol
        * lithography_source_plasma_drive_edge_detuning_ratio.symbol
        / lithography_source_ionization_energy.symbol
    ),
    valid_all(
        gt(lithography_source_ionization_energy.symbol, 0),
        gt(lithography_source_plasma_drive_edge_detuning_ratio.symbol, 0),
        gt(HBAR.symbol, 0),
        gt(SPEED_OF_LIGHT.symbol, 0),
    ),
    "Detuned source-plasma drive wavelength from the ionization-edge photon energy and edge-detuning ratio.",
    references=[LITHOGRAPHY_SOURCE_ABSORPTION_EDGE_REF],
    check_units=True,
)
eq_lithography_source_plasma_absorption_resonance_to_drive_ratio_from_ionization_edge = Approximation(
    "physical.eq.lithography_source_plasma_absorption_resonance_to_drive_ratio_from_ionization_edge",
    lithography_source_plasma_absorption_resonance_to_drive_ratio.symbol,
    (
        lithography_source_ionization_energy.symbol
        / (
            HBAR.symbol
            * lithography_source_plasma_drive_beam_angular_frequency.symbol
        )
    ),
    valid_all(
        gt(lithography_source_ionization_energy.symbol, 0),
        gt(HBAR.symbol, 0),
        gt(lithography_source_plasma_drive_beam_angular_frequency.symbol, 0),
    ),
    "Source-plasma absorption resonance ratio from the ionization-edge energy over drive photon angular energy.",
    references=[LITHOGRAPHY_SOURCE_ABSORPTION_EDGE_REF],
    check_units=True,
)
eq_lithography_source_plasma_absorption_participating_electron_fraction_from_ionization_shell = Approximation(
    "physical.eq.lithography_source_plasma_absorption_participating_electron_fraction_from_ionization_shell",
    lithography_source_plasma_absorption_participating_electron_fraction.symbol,
    (
        lithography_source_ionization_same_shell_screening_electron_count.symbol
        + sp.Integer(1)
    )
    / lithography_source_proton_count.symbol,
    valid_all(
        gt(lithography_source_proton_count.symbol, 0),
        ge(lithography_source_ionization_same_shell_screening_electron_count.symbol, 0),
        le(
            lithography_source_ionization_same_shell_screening_electron_count.symbol
            + sp.Integer(1),
            lithography_source_proton_count.symbol,
        ),
    ),
    "Participating absorption-electron fraction from the ionization-edge same-shell population plus the edge electron.",
    references=[LITHOGRAPHY_SOURCE_ABSORPTION_EDGE_REF],
    check_units=True,
)
eq_lithography_source_plasma_absorption_sum_rule_fraction_from_ionization_shell_degeneracy = Approximation(
    "physical.eq.lithography_source_plasma_absorption_sum_rule_fraction_from_ionization_shell_degeneracy",
    lithography_source_plasma_absorption_sum_rule_fraction.symbol,
    (
        lithography_source_transition_shell_capacity.symbol
        - lithography_source_ionization_same_shell_screening_electron_count.symbol
    )
    / lithography_source_transition_shell_capacity.symbol,
    valid_all(
        gt(lithography_source_transition_shell_capacity.symbol, 0),
        ge(lithography_source_ionization_same_shell_screening_electron_count.symbol, 0),
        lt(
            lithography_source_ionization_same_shell_screening_electron_count.symbol,
            lithography_source_transition_shell_capacity.symbol,
        ),
    ),
    "Absorption sum-rule fraction from unfilled ionization-edge shell degeneracy.",
    references=[LITHOGRAPHY_SOURCE_ABSORPTION_EDGE_REF],
    check_units=True,
)
eq_lithography_source_plasma_absorption_collision_orbital_radius_from_hydrogenic_shell = Approximation(
    "physical.eq.lithography_source_plasma_absorption_collision_orbital_radius_from_hydrogenic_shell",
    lithography_source_plasma_absorption_collision_orbital_radius.symbol,
    (
        BOHR_RADIUS.symbol
        * lithography_source_ionization_principal_quantum_number.symbol**2
        / lithography_source_ionization_effective_nuclear_charge.symbol
    ),
    valid_all(
        gt(BOHR_RADIUS.symbol, 0),
        gt(lithography_source_ionization_principal_quantum_number.symbol, 0),
        gt(lithography_source_ionization_effective_nuclear_charge.symbol, 0),
    ),
    "Hydrogenic orbital radius scale from Bohr radius, ionization shell number, and screened effective nuclear charge.",
    references=[LITHOGRAPHY_SOURCE_ABSORPTION_EDGE_REF],
    check_units=True,
)
eq_lithography_source_plasma_absorption_collision_cross_section_from_orbital_area = Approximation(
    "physical.eq.lithography_source_plasma_absorption_collision_cross_section_from_orbital_area",
    lithography_source_plasma_absorption_collision_cross_section.symbol,
    (
        sp.pi
        * lithography_source_plasma_absorption_collision_orbital_radius.symbol**2
    ),
    gt(lithography_source_plasma_absorption_collision_orbital_radius.symbol, 0),
    "Geometric orbital-area scale for source-plasma absorption collision damping.",
    references=[LITHOGRAPHY_SOURCE_ABSORPTION_EDGE_REF],
    check_units=True,
)


LITHOGRAPHY_SOURCE_ABSORPTION_EDGE_VARIABLES = [
    lithography_source_plasma_absorption_collision_orbital_radius,
]

LITHOGRAPHY_SOURCE_ABSORPTION_EDGE_EQUATIONS = [
    eq_lithography_source_plasma_drive_beam_wavelength_from_ionization_edge,
    eq_lithography_source_plasma_absorption_resonance_to_drive_ratio_from_ionization_edge,
    eq_lithography_source_plasma_absorption_participating_electron_fraction_from_ionization_shell,
    eq_lithography_source_plasma_absorption_sum_rule_fraction_from_ionization_shell_degeneracy,
    eq_lithography_source_plasma_absorption_collision_orbital_radius_from_hydrogenic_shell,
    eq_lithography_source_plasma_absorption_collision_cross_section_from_orbital_area,
]


__all__ = [
    "LITHOGRAPHY_SOURCE_ABSORPTION_EDGE_REF",
    "lithography_source_plasma_absorption_collision_orbital_radius",
    "eq_lithography_source_plasma_drive_beam_wavelength_from_ionization_edge",
    "eq_lithography_source_plasma_absorption_resonance_to_drive_ratio_from_ionization_edge",
    "eq_lithography_source_plasma_absorption_participating_electron_fraction_from_ionization_shell",
    "eq_lithography_source_plasma_absorption_sum_rule_fraction_from_ionization_shell_degeneracy",
    "eq_lithography_source_plasma_absorption_collision_orbital_radius_from_hydrogenic_shell",
    "eq_lithography_source_plasma_absorption_collision_cross_section_from_orbital_area",
    "LITHOGRAPHY_SOURCE_ABSORPTION_EDGE_VARIABLES",
    "LITHOGRAPHY_SOURCE_ABSORPTION_EDGE_EQUATIONS",
]
