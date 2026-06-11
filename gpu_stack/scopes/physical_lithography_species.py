"""
scopes/physical_lithography_species.py
======================================

Isotope composition variables for lithography source species.

The calibration boundary for the source isotope is the proton count Z and
neutron count N. These are the standard isotope identifiers (AME/IUPAC
nuclide notation). Valence quark counts follow from the proton uud and
neutron udd quark model identities:

  U = 2*Z + N   (each proton contributes 2 up quarks, each neutron 1)
  D = Z + 2*N   (each proton contributes 1 down quark, each neutron 2)

This decomposition is a real physics identity, not an approximation. Quark
counts are derived from Z and N; they are not primitive roots.
"""

import sympy as sp

from ..core import Approximation, Inequality, Reference, RelationRole, VariableKind, eq, var


LITHOGRAPHY_SOURCE_SPECIES_REF = Reference(
    citation=(
        "Lithography source isotope composition: proton count Z and neutron "
        "count N fix the isotope identity; valence quark counts U = 2Z + N "
        "and D = Z + 2N are derived from the proton (uud) and neutron (udd) "
        "quark model identities. PDG, https://pdg.lbl.gov/"
    ),
    kind="database",
    url="https://pdg.lbl.gov/",
)


lithography_source_proton_count = var(
    "physical.lithography.source_proton_count", "Z_litho_src", "count",
    "Proton count (atomic number Z) of the emitting source isotope.",
    scope="physical",
    integer=True,
    nonnegative=True,
    kind=VariableKind.ROOT_INPUT,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_SPECIES_REF],
)
lithography_source_neutron_count = var(
    "physical.lithography.source_neutron_count", "N_nuc_litho_src", "count",
    "Neutron count N of the emitting source isotope.",
    scope="physical",
    integer=True,
    nonnegative=True,
    kind=VariableKind.ROOT_INPUT,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_SPECIES_REF],
)
lithography_source_valence_up_quark_count = var(
    "physical.lithography.source_valence_up_quark_count", "N_u_val_litho_src", "count",
    "Total valence up-quark count in the emitting source isotope; derived as U = 2Z + N.",
    scope="physical",
    integer=True,
    positive=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_SPECIES_REF],
)
lithography_source_valence_down_quark_count = var(
    "physical.lithography.source_valence_down_quark_count", "N_d_val_litho_src", "count",
    "Total valence down-quark count in the emitting source isotope; derived as D = Z + 2N.",
    scope="physical",
    integer=True,
    positive=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_SPECIES_REF],
)
lithography_source_atomic_number = var(
    "physical.lithography.source_atomic_number", "Z_atom_litho_src", "count",
    "Atomic number of the lithography source isotope.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_SPECIES_REF],
)
lithography_source_isotope_mass_number = var(
    "physical.lithography.source_isotope_mass_number", "A_iso_litho_src", "count",
    "Mass number of the lithography source isotope.",
    scope="physical",
    integer=True,
    positive=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_SPECIES_REF],
)


eq_lithography_source_valence_up_quark_count_from_zn = eq(
    "physical.eq.lithography_source_valence_up_quark_count_from_zn",
    lithography_source_valence_up_quark_count.symbol,
    2 * lithography_source_proton_count.symbol + lithography_source_neutron_count.symbol,
    "Source up-quark count from proton and neutron counts: U = 2Z + N.",
    references=[LITHOGRAPHY_SOURCE_SPECIES_REF],
    check_units=True,
)
eq_lithography_source_valence_down_quark_count_from_zn = eq(
    "physical.eq.lithography_source_valence_down_quark_count_from_zn",
    lithography_source_valence_down_quark_count.symbol,
    lithography_source_proton_count.symbol + 2 * lithography_source_neutron_count.symbol,
    "Source down-quark count from proton and neutron counts: D = Z + 2N.",
    references=[LITHOGRAPHY_SOURCE_SPECIES_REF],
    check_units=True,
)
ineq_lithography_source_proton_count_positive = Inequality(
    "physical.ineq.lithography_source_proton_count_positive",
    lithography_source_proton_count.symbol,
    sp.Integer(1),
    ">=",
    "Source isotope must have at least one proton (Z >= 1) to be a nucleus.",
    references=[LITHOGRAPHY_SOURCE_SPECIES_REF],
    check_units=True,
)
eq_lithography_source_atomic_number = eq(
    "physical.eq.lithography_source_atomic_number",
    lithography_source_atomic_number.symbol,
    lithography_source_proton_count.symbol,
    "Atomic number from the source nuclear proton count.",
    references=[LITHOGRAPHY_SOURCE_SPECIES_REF],
    check_units=True,
)

eq_lithography_source_isotope_mass_number = Approximation(
    "physical.eq.lithography_source_isotope_mass_number",
    lithography_source_isotope_mass_number.symbol,
    lithography_source_proton_count.symbol
    + lithography_source_neutron_count.symbol,
    lithography_source_proton_count.symbol >= 0,
    "Isotope mass number from source nuclear proton and neutron counts.",
    references=[LITHOGRAPHY_SOURCE_SPECIES_REF],
    check_units=True,
)


LITHOGRAPHY_SOURCE_SPECIES_VARIABLES = [
    lithography_source_proton_count,
    lithography_source_neutron_count,
    lithography_source_valence_up_quark_count,
    lithography_source_valence_down_quark_count,
    lithography_source_atomic_number,
    lithography_source_isotope_mass_number,
]

LITHOGRAPHY_SOURCE_SPECIES_EQUATIONS = [
    eq_lithography_source_valence_up_quark_count_from_zn,
    eq_lithography_source_valence_down_quark_count_from_zn,
    ineq_lithography_source_proton_count_positive,
    eq_lithography_source_atomic_number,
    eq_lithography_source_isotope_mass_number,
]


__all__ = [
    "LITHOGRAPHY_SOURCE_SPECIES_REF",
    "lithography_source_proton_count",
    "lithography_source_neutron_count",
    "lithography_source_valence_up_quark_count",
    "lithography_source_valence_down_quark_count",
    "lithography_source_atomic_number",
    "lithography_source_isotope_mass_number",
    "eq_lithography_source_valence_up_quark_count_from_zn",
    "eq_lithography_source_valence_down_quark_count_from_zn",
    "ineq_lithography_source_proton_count_positive",
    "eq_lithography_source_atomic_number",
    "eq_lithography_source_isotope_mass_number",
    "LITHOGRAPHY_SOURCE_SPECIES_VARIABLES",
    "LITHOGRAPHY_SOURCE_SPECIES_EQUATIONS",
]
