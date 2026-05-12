"""
scopes/physical_lithography_species.py
======================================

Isotope composition variables for lithography source species.

This small layer exposes the source nuclear composition through valence quark
counts, derives proton and neutron counts, then derives the atomic/isotope
descriptors from that composition.
"""

import sympy as sp

from ..core import Approximation, Inequality, Reference, RelationRole, eq, var


LITHOGRAPHY_SOURCE_SPECIES_REF = Reference(
    citation=(
        "Lithography source isotope composition: valence quark content fixes "
        "nuclear proton and neutron counts, which then fix atomic number and "
        "isotope mass number"
    ),
    kind="memo",
)


lithography_source_valence_up_quark_count = var(
    "physical.lithography.source_valence_up_quark_count", "N_u_val_litho_src", "count",
    "Total valence up-quark count in the emitting source isotope.",
    scope="physical",
    integer=True,
    positive=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_SPECIES_REF],
)
lithography_source_valence_down_quark_count = var(
    "physical.lithography.source_valence_down_quark_count", "N_d_val_litho_src", "count",
    "Total valence down-quark count in the emitting source isotope.",
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
lithography_source_proton_count = var(
    "physical.lithography.source_proton_count", "Z_litho_src", "count",
    "Proton count of the emitting source nucleus or ion species.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_SPECIES_REF],
)
lithography_source_neutron_count = var(
    "physical.lithography.source_neutron_count", "N_nuc_litho_src", "count",
    "Neutron count of the emitting source isotope.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_SPECIES_REF],
)


eq_lithography_source_proton_count_from_valence_quarks = eq(
    "physical.eq.lithography_source_proton_count_from_valence_quarks",
    lithography_source_proton_count.symbol,
    sp.Rational(1, 3)
    * (
        2 * lithography_source_valence_up_quark_count.symbol
        - lithography_source_valence_down_quark_count.symbol
    ),
    "Proton count from total valence up/down quark content.",
    references=[LITHOGRAPHY_SOURCE_SPECIES_REF],
    check_units=True,
)
eq_lithography_source_neutron_count_from_valence_quarks = eq(
    "physical.eq.lithography_source_neutron_count_from_valence_quarks",
    lithography_source_neutron_count.symbol,
    sp.Rational(1, 3)
    * (
        2 * lithography_source_valence_down_quark_count.symbol
        - lithography_source_valence_up_quark_count.symbol
    ),
    "Neutron count from total valence up/down quark content.",
    references=[LITHOGRAPHY_SOURCE_SPECIES_REF],
    check_units=True,
)
ineq_lithography_source_valence_quarks_imply_nonnegative_protons = Inequality(
    "physical.ineq.lithography_source_valence_quarks_imply_nonnegative_protons",
    lithography_source_valence_down_quark_count.symbol,
    2 * lithography_source_valence_up_quark_count.symbol,
    "<=",
    "Source valence quark counts must satisfy D <= 2U so the derived proton count is non-negative.",
    references=[LITHOGRAPHY_SOURCE_SPECIES_REF],
    check_units=True,
)
ineq_lithography_source_valence_quarks_imply_positive_protons = Inequality(
    "physical.ineq.lithography_source_valence_quarks_imply_positive_protons",
    lithography_source_valence_up_quark_count.symbol,
    sp.Rational(1, 2)
    * (lithography_source_valence_down_quark_count.symbol + sp.Integer(3)),
    ">=",
    "Source valence quark counts must satisfy U >= (D + 3)/2 so the derived proton count is at least one.",
    references=[LITHOGRAPHY_SOURCE_SPECIES_REF],
    check_units=True,
)
ineq_lithography_source_valence_quarks_imply_nonnegative_neutrons = Inequality(
    "physical.ineq.lithography_source_valence_quarks_imply_nonnegative_neutrons",
    lithography_source_valence_up_quark_count.symbol,
    2 * lithography_source_valence_down_quark_count.symbol,
    "<=",
    "Source valence quark counts must satisfy U <= 2D so the derived neutron count is non-negative.",
    references=[LITHOGRAPHY_SOURCE_SPECIES_REF],
    check_units=True,
)
eq_lithography_source_valence_quark_triplet_integrality = eq(
    "physical.eq.lithography_source_valence_quark_triplet_integrality",
    lithography_source_valence_up_quark_count.symbol,
    (
        lithography_source_valence_up_quark_count.symbol
        - sp.Mod(
            lithography_source_valence_up_quark_count.symbol
            + lithography_source_valence_down_quark_count.symbol,
            3,
        )
    ),
    "Total source valence quark count must be divisible into three-quark baryon triplets.",
    references=[LITHOGRAPHY_SOURCE_SPECIES_REF],
    check_units=True,
    role=RelationRole.CONSTRAINT,
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
    lithography_source_valence_up_quark_count,
    lithography_source_valence_down_quark_count,
    lithography_source_atomic_number,
    lithography_source_isotope_mass_number,
    lithography_source_proton_count,
    lithography_source_neutron_count,
]

LITHOGRAPHY_SOURCE_SPECIES_EQUATIONS = [
    eq_lithography_source_proton_count_from_valence_quarks,
    eq_lithography_source_neutron_count_from_valence_quarks,
    ineq_lithography_source_valence_quarks_imply_nonnegative_protons,
    ineq_lithography_source_valence_quarks_imply_positive_protons,
    ineq_lithography_source_valence_quarks_imply_nonnegative_neutrons,
    eq_lithography_source_valence_quark_triplet_integrality,
    eq_lithography_source_atomic_number,
    eq_lithography_source_isotope_mass_number,
]


__all__ = [
    "LITHOGRAPHY_SOURCE_SPECIES_REF",
    "lithography_source_valence_up_quark_count",
    "lithography_source_valence_down_quark_count",
    "lithography_source_atomic_number",
    "lithography_source_isotope_mass_number",
    "lithography_source_proton_count",
    "lithography_source_neutron_count",
    "eq_lithography_source_proton_count_from_valence_quarks",
    "eq_lithography_source_neutron_count_from_valence_quarks",
    "ineq_lithography_source_valence_quarks_imply_nonnegative_protons",
    "ineq_lithography_source_valence_quarks_imply_positive_protons",
    "ineq_lithography_source_valence_quarks_imply_nonnegative_neutrons",
    "eq_lithography_source_valence_quark_triplet_integrality",
    "eq_lithography_source_atomic_number",
    "eq_lithography_source_isotope_mass_number",
    "LITHOGRAPHY_SOURCE_SPECIES_VARIABLES",
    "LITHOGRAPHY_SOURCE_SPECIES_EQUATIONS",
]
