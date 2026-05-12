"""
scopes/physical_lithography_electronic_structure.py
===================================================

Electronic-shell structure for lithography source transitions.

This layer keeps source screening and active-shell occupancy from being raw
scenario knobs. It exposes ion charge, bound electrons, principal-shell
capacity, closed lower-shell capacity, filled lower-shell accounting, and
radial-ordering shielding factors as symbolic graph structure.
"""

import sympy as sp

from ..core import Approximation, Reference, eq, var
from ..core.units import JOULE, METER
from ..constants import BOLTZMANN, ELECTRON_MASS, PLANCK, RYDBERG_ENERGY
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
from .physical_lithography_species import lithography_source_proton_count


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
eq_lithography_source_transition_shell_capacity = eq(
    "physical.eq.lithography_source_transition_shell_capacity",
    lithography_source_transition_shell_capacity.symbol,
    sp.Integer(2) * lithography_source_lower_principal_quantum_number.symbol**2,
    "Principal-shell electron capacity 2 n^2 for the active source transition shell.",
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
    check_units=True,
)
eq_lithography_source_inner_closed_shell_capacity = eq(
    "physical.eq.lithography_source_inner_closed_shell_capacity",
    lithography_source_inner_closed_shell_capacity.symbol,
    (
        lithography_source_lower_principal_quantum_number.symbol
        * (lithography_source_lower_principal_quantum_number.symbol - 1)
        * (2 * lithography_source_lower_principal_quantum_number.symbol - 1)
    )
    / sp.Integer(3),
    "Closed-form sum of 2 n^2 electron states below the active principal shell.",
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
    check_units=True,
)
eq_lithography_source_outer_shell_electron_count = Approximation(
    "physical.eq.lithography_source_outer_shell_electron_count",
    lithography_source_outer_shell_electron_count.symbol,
    sp.Max(
        sp.Integer(0),
        lithography_source_bound_electron_count.symbol
        - lithography_source_inner_closed_shell_capacity.symbol
        - lithography_source_transition_shell_capacity.symbol,
    ),
    lithography_source_lower_principal_quantum_number.symbol >= 1,
    "Filled-shell approximation for bound electrons outside the active transition shell.",
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
    check_units=True,
)
eq_lithography_source_inner_closed_shell_electron_count = Approximation(
    "physical.eq.lithography_source_inner_closed_shell_electron_count",
    lithography_source_inner_closed_shell_electron_count.symbol,
    sp.Min(
        lithography_source_bound_electron_count.symbol
        - lithography_source_outer_shell_electron_count.symbol,
        lithography_source_inner_closed_shell_capacity.symbol,
    ),
    (
        lithography_source_lower_principal_quantum_number.symbol >= 1
    )
    & (
        lithography_source_bound_electron_count.symbol
        >= lithography_source_outer_shell_electron_count.symbol
    ),
    "Filled-lower-shell approximation for closed inner electrons below the active transition shell.",
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
    check_units=True,
)
eq_lithography_source_transition_shell_occupancy = Approximation(
    "physical.eq.lithography_source_transition_shell_occupancy",
    lithography_source_transition_shell_occupancy.symbol,
    lithography_source_bound_electron_count.symbol
    - lithography_source_inner_closed_shell_electron_count.symbol
    - lithography_source_outer_shell_electron_count.symbol,
    (
        lithography_source_bound_electron_count.symbol
        >= (
            lithography_source_inner_closed_shell_electron_count.symbol
            + lithography_source_outer_shell_electron_count.symbol
        )
    )
    & (
        (
            lithography_source_bound_electron_count.symbol
            - lithography_source_inner_closed_shell_electron_count.symbol
            - lithography_source_outer_shell_electron_count.symbol
        )
        <= lithography_source_transition_shell_capacity.symbol
    ),
    "Active-shell occupancy from bound electrons after accounting for closed inner shells and outer electrons.",
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
    check_units=True,
)
eq_lithography_source_same_shell_screening_electron_count = Approximation(
    "physical.eq.lithography_source_same_shell_screening_electron_count",
    lithography_source_same_shell_screening_electron_count.symbol,
    lithography_source_transition_shell_occupancy.symbol - 1,
    (lithography_source_transition_shell_occupancy.symbol > 0)
    & (
        lithography_source_transition_shell_occupancy.symbol
        <= lithography_source_transition_shell_capacity.symbol
    ),
    "Same-shell screening electrons as active-shell occupancy excluding the transitioning electron.",
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
    check_units=True,
)
eq_lithography_source_inner_shell_screening_electron_count = Approximation(
    "physical.eq.lithography_source_inner_shell_screening_electron_count",
    lithography_source_inner_shell_screening_electron_count.symbol,
    lithography_source_bound_electron_count.symbol
    - lithography_source_transition_shell_occupancy.symbol
    - lithography_source_outer_shell_electron_count.symbol,
    lithography_source_bound_electron_count.symbol
    >= (
        lithography_source_transition_shell_occupancy.symbol
        + lithography_source_outer_shell_electron_count.symbol
    ),
    "Inner-shell screening electron count from bound electrons, active-shell occupancy, and outer electrons.",
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
    check_units=True,
)
eq_lithography_source_screening_constant = Approximation(
    "physical.eq.lithography_source_screening_constant",
    lithography_source_screening_constant.symbol,
    lithography_source_inner_shell_screening_electron_count.symbol
    * lithography_source_inner_shell_shielding_factor.symbol
    + lithography_source_same_shell_screening_electron_count.symbol
    * lithography_source_same_shell_shielding_factor.symbol,
    (
        lithography_source_inner_shell_screening_electron_count.symbol
        + lithography_source_same_shell_screening_electron_count.symbol
        <= lithography_source_bound_electron_count.symbol
    ),
    "Shell-count screening approximation from bound electrons and per-shell shielding factors.",
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
    check_units=True,
)

eq_lithography_source_effective_nuclear_charge = Approximation(
    "physical.eq.lithography_source_effective_nuclear_charge",
    lithography_source_effective_nuclear_charge.symbol,
    lithography_source_proton_count.symbol
    - lithography_source_screening_constant.symbol,
    lithography_source_proton_count.symbol
    > lithography_source_screening_constant.symbol,
    "Screened effective nuclear charge from nuclear proton count and electronic screening.",
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
    check_units=True,
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
    eq_lithography_source_lower_principal_quantum_number,
    eq_lithography_source_upper_principal_quantum_number,
    eq_lithography_source_ionization_principal_quantum_number,
    eq_lithography_source_ionization_inner_shell_screening_electron_count,
    eq_lithography_source_ionization_same_shell_screening_electron_count,
    eq_lithography_source_ionization_screening_constant,
    eq_lithography_source_ionization_effective_nuclear_charge,
    eq_lithography_source_ionization_energy,
    eq_lithography_source_ionization_partition_ratio,
    *LITHOGRAPHY_SOURCE_ABSORPTION_EDGE_EQUATIONS,
    eq_lithography_source_saha_thermal_number_density,
    eq_lithography_source_saha_ionization_ratio,
    eq_lithography_source_saha_ionization_fraction,
    eq_lithography_source_ion_charge_state,
    eq_lithography_source_bound_electron_count,
    eq_lithography_source_transition_shell_capacity,
    eq_lithography_source_inner_closed_shell_capacity,
    eq_lithography_source_outer_shell_electron_count,
    eq_lithography_source_inner_closed_shell_electron_count,
    eq_lithography_source_transition_shell_occupancy,
    eq_lithography_source_same_shell_screening_electron_count,
    eq_lithography_source_inner_shell_screening_electron_count,
    eq_lithography_source_screening_constant,
    eq_lithography_source_effective_nuclear_charge,
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
