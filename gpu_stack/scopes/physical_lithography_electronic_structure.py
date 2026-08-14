"""
scopes/physical_lithography_electronic_structure.py
===================================================

Electronic-shell structure of the emitting source ion. The exposure photon
comes from an electron dropping between principal shells of a highly
charged ion, so its energy depends on which shells are involved and how
strongly the remaining electrons screen the nucleus. This layer derives ion
charge, bound-electron count, shell capacities (2n^2 per shell), filled
lower-shell accounting, and radial-ordering shielding factors as symbolic
graph structure instead of leaving them as raw scenario knobs. It composes
variables and equations from focused sibling modules (shells, ionization,
shielding, absorption edge, transition step) and preserves the public
import surface.
"""

from .physical_lithography_plasma_state import *
from .physical_lithography_plasma_state import (
    LITHOGRAPHY_SOURCE_PLASMA_STATE_EQUATIONS,
    LITHOGRAPHY_SOURCE_PLASMA_STATE_VARIABLES,
    __all__ as LITHOGRAPHY_SOURCE_PLASMA_STATE_EXPORTS,
)
from .physical_lithography_shielding import *
from .physical_lithography_shielding import (
    LITHOGRAPHY_SOURCE_SHIELDING_EQUATIONS,
    LITHOGRAPHY_SOURCE_SHIELDING_VARIABLES,
    __all__ as LITHOGRAPHY_SOURCE_SHIELDING_EXPORTS,
)
from .physical_lithography_electronic_structure_variables import *
from .physical_lithography_electronic_structure_ionization import *
from .physical_lithography_electronic_structure_ionization import (
    LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_IONIZATION_EDGE_EQUATIONS,
    LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_SAHA_CHARGE_EQUATIONS,
)
from .physical_lithography_electronic_structure_shells import *
from .physical_lithography_electronic_structure_shells import (
    LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_SHELL_EQUATIONS,
)
from .physical_lithography_absorption_edge import *
from .physical_lithography_absorption_edge import (
    LITHOGRAPHY_SOURCE_ABSORPTION_EDGE_EQUATIONS,
    LITHOGRAPHY_SOURCE_ABSORPTION_EDGE_VARIABLES,
    __all__ as LITHOGRAPHY_SOURCE_ABSORPTION_EDGE_EXPORTS,
)
from .physical_lithography_transition_step import *
from .physical_lithography_transition_step import (
    LITHOGRAPHY_SOURCE_TRANSITION_STEP_EQUATIONS,
    __all__ as LITHOGRAPHY_SOURCE_TRANSITION_STEP_EXPORTS,
)


LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_VARIABLES = [
    lithography_source_ion_charge_state,
    *LITHOGRAPHY_SOURCE_PLASMA_STATE_VARIABLES,
    lithography_source_ionization_energy,
    lithography_source_ionization_principal_quantum_number,
    lithography_source_ionization_screening_constant,
    lithography_source_ionization_inner_shell_screening_electron_count,
    lithography_source_ionization_same_shell_screening_electron_count,
    lithography_source_ionization_effective_nuclear_charge,
    lithography_source_ionization_partition_ratio,
    *LITHOGRAPHY_SOURCE_ABSORPTION_EDGE_VARIABLES,
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
    *LITHOGRAPHY_SOURCE_SHIELDING_VARIABLES,
    lithography_source_screening_constant,
    lithography_source_effective_nuclear_charge,
]

LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_EQUATIONS = [
    *LITHOGRAPHY_SOURCE_PLASMA_STATE_EQUATIONS,
    *LITHOGRAPHY_SOURCE_SHIELDING_EQUATIONS,
    *LITHOGRAPHY_SOURCE_TRANSITION_STEP_EQUATIONS,
    *LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_IONIZATION_EDGE_EQUATIONS,
    *LITHOGRAPHY_SOURCE_ABSORPTION_EDGE_EQUATIONS,
    *LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_SAHA_CHARGE_EQUATIONS,
    *LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_SHELL_EQUATIONS,
]

__all__ = [
    "LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF",
    "lithography_source_ion_charge_state",
    *LITHOGRAPHY_SOURCE_PLASMA_STATE_EXPORTS,
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
    *LITHOGRAPHY_SOURCE_SHIELDING_EXPORTS,
    "lithography_source_screening_constant",
    "lithography_source_effective_nuclear_charge",
    *LITHOGRAPHY_SOURCE_TRANSITION_STEP_EXPORTS,
    "eq_lithography_source_lower_principal_quantum_number",
    "eq_lithography_source_upper_principal_quantum_number",
    "eq_lithography_source_ionization_principal_quantum_number",
    "eq_lithography_source_ionization_inner_shell_screening_electron_count",
    "eq_lithography_source_ionization_same_shell_screening_electron_count",
    "eq_lithography_source_ionization_screening_constant",
    "eq_lithography_source_ionization_effective_nuclear_charge",
    "eq_lithography_source_ionization_energy",
    "eq_lithography_source_ionization_partition_ratio",
    *LITHOGRAPHY_SOURCE_ABSORPTION_EDGE_EXPORTS,
    "eq_lithography_source_saha_thermal_number_density",
    "eq_lithography_source_saha_ionization_ratio",
    "eq_lithography_source_saha_ionization_fraction",
    "eq_lithography_source_ion_charge_state",
    "eq_lithography_source_bound_electron_count",
    "eq_lithography_source_transition_shell_capacity",
    "eq_lithography_source_inner_closed_shell_capacity",
    "eq_lithography_source_outer_shell_electron_count",
    "eq_lithography_source_inner_closed_shell_electron_count",
    "eq_lithography_source_transition_shell_occupancy",
    "eq_lithography_source_same_shell_screening_electron_count",
    "eq_lithography_source_inner_shell_screening_electron_count",
    "eq_lithography_source_screening_constant",
    "eq_lithography_source_effective_nuclear_charge",
    "LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_VARIABLES",
    "LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_EQUATIONS",
]
