"""
scopes/physical_lithography_electronic_structure_ionization.py
==============================================================

Ionization balance for the source ion. Two things are computed here.
First, the ionization edge: the energy needed to remove the active
electron, from a screened hydrogenic model with an effective nuclear
charge. Second, the Saha balance: given the plasma electron temperature and
density, statistical mechanics fixes the population ratio of adjacent
charge states, and from that the equilibrium ionization fraction and
bound-electron count. This is how the model decides which charge state
actually emits, rather than assuming one.
"""

import sympy as sp

from ..constants import BOLTZMANN, ELECTRON_MASS, PLANCK, RYDBERG_ENERGY
from ..core import Approximation, eq
from .physical_lithography_electronic_structure_variables import (
    LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF,
    lithography_source_bound_electron_count,
    lithography_source_inner_closed_shell_capacity,
    lithography_source_ion_charge_state,
    lithography_source_ionization_effective_nuclear_charge,
    lithography_source_ionization_energy,
    lithography_source_ionization_inner_shell_screening_electron_count,
    lithography_source_ionization_partition_ratio,
    lithography_source_ionization_principal_quantum_number,
    lithography_source_ionization_same_shell_screening_electron_count,
    lithography_source_ionization_screening_constant,
    lithography_source_lower_principal_quantum_number,
    lithography_source_saha_ionization_fraction,
    lithography_source_saha_ionization_ratio,
    lithography_source_saha_thermal_number_density,
    lithography_source_transition_principal_quantum_step,
    lithography_source_transition_shell_capacity,
    lithography_source_upper_principal_quantum_number,
)
from .physical_lithography_plasma_state import (
    lithography_source_plasma_electron_number_density,
    lithography_source_plasma_electron_temperature,
)
from .physical_lithography_shielding import (
    lithography_source_inner_shell_shielding_factor,
    lithography_source_same_shell_shielding_factor,
)
from .physical_lithography_species import lithography_source_proton_count


eq_lithography_source_lower_principal_quantum_number = Approximation(
    "physical.eq.lithography_source_lower_principal_quantum_number",
    lithography_source_lower_principal_quantum_number.symbol,
    sp.Piecewise(
        (sp.Integer(1), lithography_source_proton_count.symbol <= 2),
        (sp.Integer(2), lithography_source_proton_count.symbol <= 10),
        (sp.Integer(3), lithography_source_proton_count.symbol <= 28),
        (sp.Integer(4), lithography_source_proton_count.symbol <= 60),
        (sp.Integer(5), lithography_source_proton_count.symbol <= 110),
        (sp.Integer(6), lithography_source_proton_count.symbol <= 182),
        (sp.Integer(7), lithography_source_proton_count.symbol <= 280),
    ),
    (lithography_source_proton_count.symbol > 0)
    & (lithography_source_proton_count.symbol <= 280),
    "Lower transition shell from coarse neutral-shell filling boundaries for principal-shell capacities.",
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
    check_units=True,
)
eq_lithography_source_upper_principal_quantum_number = Approximation(
    "physical.eq.lithography_source_upper_principal_quantum_number",
    lithography_source_upper_principal_quantum_number.symbol,
    lithography_source_lower_principal_quantum_number.symbol
    + lithography_source_transition_principal_quantum_step.symbol,
    lithography_source_transition_principal_quantum_step.symbol > 0,
    "Upper transition shell from lower shell plus a scenario-selected principal-shell step.",
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
    check_units=True,
)
eq_lithography_source_ionization_principal_quantum_number = Approximation(
    "physical.eq.lithography_source_ionization_principal_quantum_number",
    lithography_source_ionization_principal_quantum_number.symbol,
    lithography_source_lower_principal_quantum_number.symbol,
    lithography_source_lower_principal_quantum_number.symbol > 0,
    "Ionization-edge shell tied to the active lower transition shell.",
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
    check_units=True,
)
eq_lithography_source_ionization_inner_shell_screening_electron_count = Approximation(
    "physical.eq.lithography_source_ionization_inner_shell_screening_electron_count",
    lithography_source_ionization_inner_shell_screening_electron_count.symbol,
    sp.Min(
        lithography_source_proton_count.symbol - 1,
        lithography_source_inner_closed_shell_capacity.symbol,
    ),
    lithography_source_proton_count.symbol > 0,
    "Ionization-edge inner-shell screening count from neutral source charge and lower closed-shell capacity.",
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
    check_units=True,
)
eq_lithography_source_ionization_same_shell_screening_electron_count = Approximation(
    "physical.eq.lithography_source_ionization_same_shell_screening_electron_count",
    lithography_source_ionization_same_shell_screening_electron_count.symbol,
    sp.Min(
        lithography_source_transition_shell_capacity.symbol - 1,
        sp.Max(
            sp.Integer(0),
            lithography_source_proton_count.symbol
            - lithography_source_ionization_inner_shell_screening_electron_count.symbol
            - 1,
        ),
    ),
    (
        lithography_source_proton_count.symbol > 0
    )
    & (
        lithography_source_transition_shell_capacity.symbol > 0
    ),
    "Ionization-edge same-shell screening count from neutral source charge after inner-shell screeners.",
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
    check_units=True,
)
eq_lithography_source_ionization_screening_constant = Approximation(
    "physical.eq.lithography_source_ionization_screening_constant",
    lithography_source_ionization_screening_constant.symbol,
    lithography_source_ionization_inner_shell_screening_electron_count.symbol
    * lithography_source_inner_shell_shielding_factor.symbol
    + lithography_source_ionization_same_shell_screening_electron_count.symbol
    * lithography_source_same_shell_shielding_factor.symbol,
    (
        lithography_source_ionization_inner_shell_screening_electron_count.symbol
        + lithography_source_ionization_same_shell_screening_electron_count.symbol
        <= lithography_source_proton_count.symbol - 1
    ),
    "Ionization-edge screening constant from inner- and same-shell neutral screening counts.",
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
    check_units=True,
)
eq_lithography_source_ionization_effective_nuclear_charge = Approximation(
    "physical.eq.lithography_source_ionization_effective_nuclear_charge",
    lithography_source_ionization_effective_nuclear_charge.symbol,
    lithography_source_proton_count.symbol
    - lithography_source_ionization_screening_constant.symbol,
    lithography_source_proton_count.symbol
    >= lithography_source_ionization_screening_constant.symbol,
    "Ionization-edge effective nuclear charge from proton count and edge screening.",
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
    check_units=True,
)
eq_lithography_source_ionization_energy = Approximation(
    "physical.eq.lithography_source_ionization_energy",
    lithography_source_ionization_energy.symbol,
    RYDBERG_ENERGY.symbol
    * lithography_source_ionization_effective_nuclear_charge.symbol**2
    / lithography_source_ionization_principal_quantum_number.symbol**2,
    lithography_source_ionization_principal_quantum_number.symbol > 0,
    "Hydrogenic screened-edge ionization energy for the source plasma Saha balance.",
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
    check_units=True,
)
eq_lithography_source_ionization_partition_ratio = Approximation(
    "physical.eq.lithography_source_ionization_partition_ratio",
    lithography_source_ionization_partition_ratio.symbol,
    (lithography_source_ionization_same_shell_screening_electron_count.symbol + sp.Integer(1))
    / (lithography_source_transition_shell_capacity.symbol - lithography_source_ionization_same_shell_screening_electron_count.symbol),
    lithography_source_transition_shell_capacity.symbol
    > lithography_source_ionization_same_shell_screening_electron_count.symbol,
    "One-edge shell-configuration degeneracy ratio C(G, N-1)/C(G, N) for ionized versus neutral source states.",
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
    check_units=True,
)
eq_lithography_source_saha_thermal_number_density = eq(
    "physical.eq.lithography_source_saha_thermal_number_density",
    lithography_source_saha_thermal_number_density.symbol,
    sp.Integer(2)
    * (
        2
        * sp.pi
        * ELECTRON_MASS.symbol
        * BOLTZMANN.symbol
        * lithography_source_plasma_electron_temperature.symbol
        / PLANCK.symbol**2
    ) ** sp.Rational(3, 2),
    "Thermal electron phase-space density factor 2(2 pi m_e k_B T_e / h^2)^(3/2).",
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
    check_units=True,
)
eq_lithography_source_saha_ionization_ratio = Approximation(
    "physical.eq.lithography_source_saha_ionization_ratio",
    lithography_source_saha_ionization_ratio.symbol,
    lithography_source_saha_thermal_number_density.symbol
    * lithography_source_ionization_partition_ratio.symbol
    / lithography_source_plasma_electron_number_density.symbol
    * sp.exp(
        -lithography_source_ionization_energy.symbol
        / (
            BOLTZMANN.symbol
            * lithography_source_plasma_electron_temperature.symbol
        )
    ),
    (lithography_source_plasma_electron_temperature.symbol > 0)
    & (lithography_source_plasma_electron_number_density.symbol > 0),
    "One-edge Saha ionization ratio from plasma temperature, electron density, ionization energy, and partition ratio.",
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
    check_units=True,
)
eq_lithography_source_saha_ionization_fraction = Approximation(
    "physical.eq.lithography_source_saha_ionization_fraction",
    lithography_source_saha_ionization_fraction.symbol,
    lithography_source_saha_ionization_ratio.symbol
    / (1 + lithography_source_saha_ionization_ratio.symbol),
    lithography_source_saha_ionization_ratio.symbol >= 0,
    "Ionized population fraction from the Saha ionization ratio.",
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
    check_units=True,
)
eq_lithography_source_ion_charge_state = Approximation(
    "physical.eq.lithography_source_ion_charge_state",
    lithography_source_ion_charge_state.symbol,
    lithography_source_proton_count.symbol
    * lithography_source_saha_ionization_fraction.symbol,
    (lithography_source_saha_ionization_fraction.symbol >= 0)
    & (lithography_source_saha_ionization_fraction.symbol <= 1),
    "Mean source ion charge state from nuclear charge and a one-edge Saha ionization fraction.",
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
    check_units=True,
)
eq_lithography_source_bound_electron_count = Approximation(
    "physical.eq.lithography_source_bound_electron_count",
    lithography_source_bound_electron_count.symbol,
    lithography_source_proton_count.symbol
    - lithography_source_ion_charge_state.symbol,
    lithography_source_proton_count.symbol
    >= lithography_source_ion_charge_state.symbol,
    "Bound electron count from nuclear charge and positive ion charge state.",
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
    check_units=True,
)


LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_IONIZATION_EDGE_EQUATIONS = [
    eq_lithography_source_lower_principal_quantum_number,
    eq_lithography_source_upper_principal_quantum_number,
    eq_lithography_source_ionization_principal_quantum_number,
    eq_lithography_source_ionization_inner_shell_screening_electron_count,
    eq_lithography_source_ionization_same_shell_screening_electron_count,
    eq_lithography_source_ionization_screening_constant,
    eq_lithography_source_ionization_effective_nuclear_charge,
    eq_lithography_source_ionization_energy,
    eq_lithography_source_ionization_partition_ratio,
]

LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_SAHA_CHARGE_EQUATIONS = [
    eq_lithography_source_saha_thermal_number_density,
    eq_lithography_source_saha_ionization_ratio,
    eq_lithography_source_saha_ionization_fraction,
    eq_lithography_source_ion_charge_state,
    eq_lithography_source_bound_electron_count,
]

LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_IONIZATION_EQUATIONS = [
    *LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_IONIZATION_EDGE_EQUATIONS,
    *LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_SAHA_CHARGE_EQUATIONS,
]


__all__ = [
    "eq_lithography_source_lower_principal_quantum_number",
    "eq_lithography_source_upper_principal_quantum_number",
    "eq_lithography_source_ionization_principal_quantum_number",
    "eq_lithography_source_ionization_inner_shell_screening_electron_count",
    "eq_lithography_source_ionization_same_shell_screening_electron_count",
    "eq_lithography_source_ionization_screening_constant",
    "eq_lithography_source_ionization_effective_nuclear_charge",
    "eq_lithography_source_ionization_energy",
    "eq_lithography_source_ionization_partition_ratio",
    "eq_lithography_source_saha_thermal_number_density",
    "eq_lithography_source_saha_ionization_ratio",
    "eq_lithography_source_saha_ionization_fraction",
    "eq_lithography_source_ion_charge_state",
    "eq_lithography_source_bound_electron_count",
]
