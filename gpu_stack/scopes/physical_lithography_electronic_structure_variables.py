"""
scopes/physical_lithography_electronic_structure_variables.py
=============================================================

Variable declarations for the source electronic structure: ion charge,
ionization energy and its screening inputs, Saha-balance quantities, bound
electron count, and the principal quantum numbers of the emitting
transition. The public electronic-structure module composes these with the
plasma, shielding, absorption-edge, and transition-step shims. Keeping the
raw declarations in one file makes the registry surface easy to audit
without touching names, units, references, or exports.
"""

import sympy as sp

from ..core import Reference, var
from ..core.units import JOULE, METER


LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF = Reference(
    citation=(
        "Lithography source electronic structure: mean ion charge from a Saha-style "
        "thermal ionization ratio, bound electron count from ion charge, ionization edge "
        "shell from the active transition shell, principal shell capacity 2n^2, closed "
        "lower-shell capacity sum, active-shell occupancy, and shell-count screening"
    ),
    kind="memo",
)


lithography_source_ion_charge_state = var(
    "physical.lithography.source_ion_charge_state", "q_ion_litho_src", "elementary charges",
    "Mean positive ion charge state of the emitting source species.",
    scope="physical",
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
)
lithography_source_ionization_energy = var(
    "physical.lithography.source_ionization_energy", "E_ion_litho_src", "J",
    "Effective ionization energy scale for the emitting source species in the plasma.",
    scope="physical",
    nonnegative=True,
    sp_units=JOULE,
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
)
lithography_source_ionization_principal_quantum_number = var(
    "physical.lithography.source_ionization_principal_quantum_number", "n_ion_litho_src", "dimensionless",
    "Principal quantum number of the electron shell used for the source ionization edge.",
    scope="physical",
    positive=True,
    integer=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
)
lithography_source_ionization_screening_constant = var(
    "physical.lithography.source_ionization_screening_constant", "sigma_ion_litho_src", "dimensionless",
    "Effective screening constant seen by the electron at the source ionization edge.",
    scope="physical",
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
)
lithography_source_ionization_inner_shell_screening_electron_count = var(
    "physical.lithography.source_ionization_inner_shell_screening_electron_count", "N_inner_screen_ion_litho_src", "count",
    "Inner-shell electrons screening the source ionization-edge electron.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
)
lithography_source_ionization_same_shell_screening_electron_count = var(
    "physical.lithography.source_ionization_same_shell_screening_electron_count", "N_same_screen_ion_litho_src", "count",
    "Same-shell electrons screening the source ionization-edge electron.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
)
lithography_source_ionization_effective_nuclear_charge = var(
    "physical.lithography.source_ionization_effective_nuclear_charge", "Z_eff_ion_litho_src", "dimensionless",
    "Screened effective nuclear charge used for the source ionization edge.",
    scope="physical",
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
)
lithography_source_ionization_partition_ratio = var(
    "physical.lithography.source_ionization_partition_ratio", "g_ion_ratio_litho_src", "dimensionless",
    "Ionized-to-neutral shell-configuration degeneracy ratio in the Saha balance.",
    scope="physical",
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
)
lithography_source_saha_thermal_number_density = var(
    "physical.lithography.source_saha_thermal_number_density", "n_Q_saha_litho_src", "1/m^3",
    "Thermal electron phase-space density factor in the source-plasma Saha relation.",
    scope="physical",
    positive=True,
    sp_units=sp.Integer(1) / METER**3,
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
)
lithography_source_saha_ionization_ratio = var(
    "physical.lithography.source_saha_ionization_ratio", "R_saha_litho_src", "dimensionless",
    "Saha ratio between ionized and neutral source populations for the effective ionization edge.",
    scope="physical",
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
)
lithography_source_saha_ionization_fraction = var(
    "physical.lithography.source_saha_ionization_fraction", "x_saha_litho_src", "dimensionless",
    "Mean ionized fraction implied by the one-edge Saha balance.",
    scope="physical",
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
)
lithography_source_bound_electron_count = var(
    "physical.lithography.source_bound_electron_count", "N_e_bound_litho_src", "count",
    "Bound electron count of the emitting source ion.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
)
lithography_source_lower_principal_quantum_number = var(
    "physical.lithography.source_lower_principal_quantum_number", "n_low_litho_src", "dimensionless",
    "Lower principal quantum number for the approximate source transition.",
    scope="physical",
    positive=True,
    integer=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
)
lithography_source_upper_principal_quantum_number = var(
    "physical.lithography.source_upper_principal_quantum_number", "n_up_litho_src", "dimensionless",
    "Upper principal quantum number for the approximate source transition.",
    scope="physical",
    positive=True,
    integer=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
)
lithography_source_transition_principal_quantum_step = var(
    "physical.lithography.source_transition_principal_quantum_step", "Delta_n_litho_src", "dimensionless",
    "Principal-shell step between the lower and upper source-transition shells.",
    scope="physical",
    positive=True,
    integer=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
)
lithography_source_transition_shell_capacity = var(
    "physical.lithography.source_transition_shell_capacity", "N_shell_cap_litho_src", "count",
    "Electron capacity of the principal shell containing the source transition.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
)
lithography_source_inner_closed_shell_capacity = var(
    "physical.lithography.source_inner_closed_shell_capacity", "N_inner_closed_cap_litho_src", "count",
    "Total electron-state capacity of principal shells below the active source transition shell.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
)
lithography_source_inner_closed_shell_electron_count = var(
    "physical.lithography.source_inner_closed_shell_electron_count", "N_inner_closed_litho_src", "count",
    "Bound electrons in closed shells below the active source transition shell.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
)
lithography_source_transition_shell_occupancy = var(
    "physical.lithography.source_transition_shell_occupancy", "N_shell_occ_litho_src", "count",
    "Electron occupancy of the principal shell containing the active source transition.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
)
lithography_source_outer_shell_electron_count = var(
    "physical.lithography.source_outer_shell_electron_count", "N_outer_e_litho_src", "count",
    "Effective count of bound electrons outside the active transition shell.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
)
lithography_source_inner_shell_screening_electron_count = var(
    "physical.lithography.source_inner_shell_screening_electron_count", "N_inner_screen_litho_src", "count",
    "Effective count of inner-shell electrons screening the source transition.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
)
lithography_source_same_shell_screening_electron_count = var(
    "physical.lithography.source_same_shell_screening_electron_count", "N_same_screen_litho_src", "count",
    "Effective count of same-shell electrons screening the source transition.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
)
lithography_source_screening_constant = var(
    "physical.lithography.source_screening_constant", "sigma_screen_litho_src", "dimensionless",
    "Effective electronic screening constant for the source transition.",
    scope="physical",
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
)
lithography_source_effective_nuclear_charge = var(
    "physical.lithography.source_effective_nuclear_charge", "Z_eff_litho_src", "dimensionless",
    "Screened effective nuclear charge seen by the transitioning electron.",
    scope="physical",
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
)


LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_LOCAL_VARIABLES = [
    lithography_source_ion_charge_state,
    lithography_source_ionization_energy,
    lithography_source_ionization_principal_quantum_number,
    lithography_source_ionization_screening_constant,
    lithography_source_ionization_inner_shell_screening_electron_count,
    lithography_source_ionization_same_shell_screening_electron_count,
    lithography_source_ionization_effective_nuclear_charge,
    lithography_source_ionization_partition_ratio,
    lithography_source_saha_thermal_number_density,
    lithography_source_saha_ionization_ratio,
    lithography_source_saha_ionization_fraction,
    lithography_source_bound_electron_count,
    lithography_source_lower_principal_quantum_number,
    lithography_source_upper_principal_quantum_number,
    lithography_source_transition_principal_quantum_step,
    lithography_source_transition_shell_capacity,
    lithography_source_inner_closed_shell_capacity,
    lithography_source_inner_closed_shell_electron_count,
    lithography_source_transition_shell_occupancy,
    lithography_source_outer_shell_electron_count,
    lithography_source_inner_shell_screening_electron_count,
    lithography_source_same_shell_screening_electron_count,
    lithography_source_screening_constant,
    lithography_source_effective_nuclear_charge,
]


__all__ = [
    "LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF",
    "lithography_source_ion_charge_state",
    "lithography_source_ionization_energy",
    "lithography_source_ionization_principal_quantum_number",
    "lithography_source_ionization_screening_constant",
    "lithography_source_ionization_inner_shell_screening_electron_count",
    "lithography_source_ionization_same_shell_screening_electron_count",
    "lithography_source_ionization_effective_nuclear_charge",
    "lithography_source_ionization_partition_ratio",
    "lithography_source_saha_thermal_number_density",
    "lithography_source_saha_ionization_ratio",
    "lithography_source_saha_ionization_fraction",
    "lithography_source_bound_electron_count",
    "lithography_source_lower_principal_quantum_number",
    "lithography_source_upper_principal_quantum_number",
    "lithography_source_transition_principal_quantum_step",
    "lithography_source_transition_shell_capacity",
    "lithography_source_inner_closed_shell_capacity",
    "lithography_source_inner_closed_shell_electron_count",
    "lithography_source_transition_shell_occupancy",
    "lithography_source_outer_shell_electron_count",
    "lithography_source_inner_shell_screening_electron_count",
    "lithography_source_same_shell_screening_electron_count",
    "lithography_source_screening_constant",
    "lithography_source_effective_nuclear_charge",
]
