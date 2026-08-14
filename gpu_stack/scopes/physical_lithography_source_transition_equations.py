"""
scopes/physical_lithography_source_transition_equations.py
==========================================================

The relations that finally produce the exposure photon. The transition
energy follows the screened hydrogenic (Rydberg-like) formula: effective
nuclear charge squared, times the reduced-mass correction, times the
difference of inverse squared principal quantum numbers between the upper
and lower shells. The exposure photon energy is then equated to that
transition energy. Everything upstream -- plasma, ionization balance,
shielding, nuclear mass -- exists to pin down the inputs of these two
equations.
"""

import sympy as sp

from ..constants import RYDBERG_ENERGY
from ..core import Approximation
from .physical_lithography_electronic_structure import (
    lithography_source_effective_nuclear_charge,
    lithography_source_lower_principal_quantum_number,
    lithography_source_upper_principal_quantum_number,
)
from .physical_lithography_source_variables import (
    LITHOGRAPHY_SOURCE_REF,
    lithography_photon_energy,
    lithography_source_reduced_mass_ratio,
    lithography_source_transition_energy,
)


eq_lithography_source_transition_energy = Approximation(
    "physical.eq.lithography_source_transition_energy",
    lithography_source_transition_energy.symbol,
    RYDBERG_ENERGY.symbol
    * lithography_source_reduced_mass_ratio.symbol
    * lithography_source_effective_nuclear_charge.symbol**2
    * (
        sp.Integer(1) / lithography_source_lower_principal_quantum_number.symbol**2
        - sp.Integer(1) / lithography_source_upper_principal_quantum_number.symbol**2
    ),
    (lithography_source_upper_principal_quantum_number.symbol
     > lithography_source_lower_principal_quantum_number.symbol)
    & (lithography_source_effective_nuclear_charge.symbol > 0)
    & (lithography_source_reduced_mass_ratio.symbol > 0),
    "Hydrogenic reduced-mass source transition energy with screened effective charge.",
    references=[LITHOGRAPHY_SOURCE_REF],
    check_units=True,
)

eq_lithography_photon_energy_from_source_transition = Approximation(
    "physical.eq.lithography_photon_energy_from_source_transition",
    lithography_photon_energy.symbol,
    lithography_source_transition_energy.symbol,
    lithography_source_transition_energy.symbol > 0,
    "Exposure photon energy from the emitting source transition energy.",
    references=[LITHOGRAPHY_SOURCE_REF],
    check_units=True,
)


_LITHOGRAPHY_SOURCE_TRANSITION_EQUATIONS = [
    eq_lithography_source_transition_energy,
    eq_lithography_photon_energy_from_source_transition,
]

_LITHOGRAPHY_SOURCE_TRANSITION_EQUATION_EXPORTS = [
    "eq_lithography_source_transition_energy",
    "eq_lithography_photon_energy_from_source_transition",
]


__all__ = _LITHOGRAPHY_SOURCE_TRANSITION_EQUATION_EXPORTS
