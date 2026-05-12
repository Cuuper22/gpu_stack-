"""
scopes/physical_lithography_medium_components.py
=================================================

Stoichiometric and isotope component variables for lithography imaging media.
"""

import sympy as sp

from ..core import Approximation, Inequality, Reference, RelationRole, eq, var


LITHOGRAPHY_MEDIUM_COMPOSITION_REF = Reference(
    citation=(
        "Lithography imaging-medium composition: representative binary "
        "formula unit from stoichiometric component counts and isotope content"
    ),
    kind="memo",
)


lithography_medium_component_a_stoichiometric_count = var(
    "physical.lithography.medium_component_a_stoichiometric_count", "nu_A_litho_med", "count",
    "Stoichiometric count of component A in the representative imaging-medium formula unit.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_b_stoichiometric_count = var(
    "physical.lithography.medium_component_b_stoichiometric_count", "nu_B_litho_med", "count",
    "Stoichiometric count of component B in the representative imaging-medium formula unit.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
ineq_lithography_medium_component_a_stoichiometric_count_at_least_one = Inequality(
    "physical.ineq.lithography_medium_component_a_stoichiometric_count_at_least_one",
    lithography_medium_component_a_stoichiometric_count.symbol,
    sp.Integer(1),
    ">=",
    "Component A stoichiometric count must be at least one in the representative binary imaging-medium formula unit.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
ineq_lithography_medium_component_b_stoichiometric_count_at_least_one = Inequality(
    "physical.ineq.lithography_medium_component_b_stoichiometric_count_at_least_one",
    lithography_medium_component_b_stoichiometric_count.symbol,
    sp.Integer(1),
    ">=",
    "Component B stoichiometric count must be at least one in the representative binary imaging-medium formula unit.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
lithography_medium_component_a_valence_up_quark_count = var(
    "physical.lithography.medium_component_a_valence_up_quark_count",
    "N_u_val_A_litho_med",
    "count",
    "Total valence up-quark count in one component A isotope of the imaging medium.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_a_valence_down_quark_count = var(
    "physical.lithography.medium_component_a_valence_down_quark_count",
    "N_d_val_A_litho_med",
    "count",
    "Total valence down-quark count in one component A isotope of the imaging medium.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_b_valence_up_quark_count = var(
    "physical.lithography.medium_component_b_valence_up_quark_count",
    "N_u_val_B_litho_med",
    "count",
    "Total valence up-quark count in one component B isotope of the imaging medium.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_b_valence_down_quark_count = var(
    "physical.lithography.medium_component_b_valence_down_quark_count",
    "N_d_val_B_litho_med",
    "count",
    "Total valence down-quark count in one component B isotope of the imaging medium.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_a_proton_count = var(
    "physical.lithography.medium_component_a_proton_count", "Z_A_litho_med", "count",
    "Proton count of component A in the representative imaging-medium formula unit.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_b_proton_count = var(
    "physical.lithography.medium_component_b_proton_count", "Z_B_litho_med", "count",
    "Proton count of component B in the representative imaging-medium formula unit.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_a_neutron_count = var(
    "physical.lithography.medium_component_a_neutron_count", "N_A_litho_med", "count",
    "Neutron count of component A in the representative imaging-medium formula unit.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_b_neutron_count = var(
    "physical.lithography.medium_component_b_neutron_count", "N_B_litho_med", "count",
    "Neutron count of component B in the representative imaging-medium formula unit.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_a_atomic_number = var(
    "physical.lithography.medium_component_a_atomic_number", "Z_atom_A_litho_med", "count",
    "Atomic number of component A in the representative imaging-medium formula unit.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_b_atomic_number = var(
    "physical.lithography.medium_component_b_atomic_number", "Z_atom_B_litho_med", "count",
    "Atomic number of component B in the representative imaging-medium formula unit.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_a_isotope_mass_number = var(
    "physical.lithography.medium_component_a_isotope_mass_number", "A_iso_A_litho_med", "count",
    "Mass number of component A in the representative imaging-medium formula unit.",
    scope="physical",
    integer=True,
    positive=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_b_isotope_mass_number = var(
    "physical.lithography.medium_component_b_isotope_mass_number", "A_iso_B_litho_med", "count",
    "Mass number of component B in the representative imaging-medium formula unit.",
    scope="physical",
    integer=True,
    positive=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)


eq_lithography_medium_component_a_proton_count_from_valence_quarks = eq(
    "physical.eq.lithography_medium_component_a_proton_count_from_valence_quarks",
    lithography_medium_component_a_proton_count.symbol,
    sp.Rational(1, 3)
    * (
        2 * lithography_medium_component_a_valence_up_quark_count.symbol
        - lithography_medium_component_a_valence_down_quark_count.symbol
    ),
    "Component A proton count from total valence up/down quark content.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_component_a_neutron_count_from_valence_quarks = eq(
    "physical.eq.lithography_medium_component_a_neutron_count_from_valence_quarks",
    lithography_medium_component_a_neutron_count.symbol,
    sp.Rational(1, 3)
    * (
        2 * lithography_medium_component_a_valence_down_quark_count.symbol
        - lithography_medium_component_a_valence_up_quark_count.symbol
    ),
    "Component A neutron count from total valence up/down quark content.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_component_b_proton_count_from_valence_quarks = eq(
    "physical.eq.lithography_medium_component_b_proton_count_from_valence_quarks",
    lithography_medium_component_b_proton_count.symbol,
    sp.Rational(1, 3)
    * (
        2 * lithography_medium_component_b_valence_up_quark_count.symbol
        - lithography_medium_component_b_valence_down_quark_count.symbol
    ),
    "Component B proton count from total valence up/down quark content.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_component_b_neutron_count_from_valence_quarks = eq(
    "physical.eq.lithography_medium_component_b_neutron_count_from_valence_quarks",
    lithography_medium_component_b_neutron_count.symbol,
    sp.Rational(1, 3)
    * (
        2 * lithography_medium_component_b_valence_down_quark_count.symbol
        - lithography_medium_component_b_valence_up_quark_count.symbol
    ),
    "Component B neutron count from total valence up/down quark content.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
ineq_lithography_medium_component_a_valence_quarks_imply_nonnegative_protons = Inequality(
    "physical.ineq.lithography_medium_component_a_valence_quarks_imply_nonnegative_protons",
    lithography_medium_component_a_valence_down_quark_count.symbol,
    2 * lithography_medium_component_a_valence_up_quark_count.symbol,
    "<=",
    "Component A valence quark counts must satisfy D <= 2U so the derived proton count is non-negative.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
ineq_lithography_medium_component_a_valence_quarks_imply_positive_protons = Inequality(
    "physical.ineq.lithography_medium_component_a_valence_quarks_imply_positive_protons",
    lithography_medium_component_a_valence_up_quark_count.symbol,
    sp.Rational(1, 2)
    * (lithography_medium_component_a_valence_down_quark_count.symbol + sp.Integer(3)),
    ">=",
    "Component A valence quark counts must satisfy U >= (D + 3)/2 so the derived proton count is at least one.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
ineq_lithography_medium_component_a_valence_quarks_imply_nonnegative_neutrons = Inequality(
    "physical.ineq.lithography_medium_component_a_valence_quarks_imply_nonnegative_neutrons",
    lithography_medium_component_a_valence_up_quark_count.symbol,
    2 * lithography_medium_component_a_valence_down_quark_count.symbol,
    "<=",
    "Component A valence quark counts must satisfy U <= 2D so the derived neutron count is non-negative.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_component_a_valence_quark_triplet_integrality = eq(
    "physical.eq.lithography_medium_component_a_valence_quark_triplet_integrality",
    lithography_medium_component_a_valence_up_quark_count.symbol,
    (
        lithography_medium_component_a_valence_up_quark_count.symbol
        - sp.Mod(
            lithography_medium_component_a_valence_up_quark_count.symbol
            + lithography_medium_component_a_valence_down_quark_count.symbol,
            3,
        )
    ),
    "Total component A valence quark count must be divisible into three-quark baryon triplets.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
    role=RelationRole.CONSTRAINT,
)
ineq_lithography_medium_component_b_valence_quarks_imply_nonnegative_protons = Inequality(
    "physical.ineq.lithography_medium_component_b_valence_quarks_imply_nonnegative_protons",
    lithography_medium_component_b_valence_down_quark_count.symbol,
    2 * lithography_medium_component_b_valence_up_quark_count.symbol,
    "<=",
    "Component B valence quark counts must satisfy D <= 2U so the derived proton count is non-negative.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
ineq_lithography_medium_component_b_valence_quarks_imply_positive_protons = Inequality(
    "physical.ineq.lithography_medium_component_b_valence_quarks_imply_positive_protons",
    lithography_medium_component_b_valence_up_quark_count.symbol,
    sp.Rational(1, 2)
    * (lithography_medium_component_b_valence_down_quark_count.symbol + sp.Integer(3)),
    ">=",
    "Component B valence quark counts must satisfy U >= (D + 3)/2 so the derived proton count is at least one.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
ineq_lithography_medium_component_b_valence_quarks_imply_nonnegative_neutrons = Inequality(
    "physical.ineq.lithography_medium_component_b_valence_quarks_imply_nonnegative_neutrons",
    lithography_medium_component_b_valence_up_quark_count.symbol,
    2 * lithography_medium_component_b_valence_down_quark_count.symbol,
    "<=",
    "Component B valence quark counts must satisfy U <= 2D so the derived neutron count is non-negative.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_component_b_valence_quark_triplet_integrality = eq(
    "physical.eq.lithography_medium_component_b_valence_quark_triplet_integrality",
    lithography_medium_component_b_valence_up_quark_count.symbol,
    (
        lithography_medium_component_b_valence_up_quark_count.symbol
        - sp.Mod(
            lithography_medium_component_b_valence_up_quark_count.symbol
            + lithography_medium_component_b_valence_down_quark_count.symbol,
            3,
        )
    ),
    "Total component B valence quark count must be divisible into three-quark baryon triplets.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
    role=RelationRole.CONSTRAINT,
)
eq_lithography_medium_component_a_atomic_number = eq(
    "physical.eq.lithography_medium_component_a_atomic_number",
    lithography_medium_component_a_atomic_number.symbol,
    lithography_medium_component_a_proton_count.symbol,
    "Component A atomic number from its nuclear proton count.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_component_b_atomic_number = eq(
    "physical.eq.lithography_medium_component_b_atomic_number",
    lithography_medium_component_b_atomic_number.symbol,
    lithography_medium_component_b_proton_count.symbol,
    "Component B atomic number from its nuclear proton count.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_component_a_isotope_mass_number = Approximation(
    "physical.eq.lithography_medium_component_a_isotope_mass_number",
    lithography_medium_component_a_isotope_mass_number.symbol,
    lithography_medium_component_a_proton_count.symbol
    + lithography_medium_component_a_neutron_count.symbol,
    lithography_medium_component_a_proton_count.symbol >= 0,
    "Component A isotope mass number from proton and neutron counts.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_component_b_isotope_mass_number = Approximation(
    "physical.eq.lithography_medium_component_b_isotope_mass_number",
    lithography_medium_component_b_isotope_mass_number.symbol,
    lithography_medium_component_b_proton_count.symbol
    + lithography_medium_component_b_neutron_count.symbol,
    lithography_medium_component_b_proton_count.symbol >= 0,
    "Component B isotope mass number from proton and neutron counts.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)


LITHOGRAPHY_MEDIUM_COMPONENT_VARIABLES = [
    lithography_medium_component_a_stoichiometric_count,
    lithography_medium_component_b_stoichiometric_count,
    lithography_medium_component_a_valence_up_quark_count,
    lithography_medium_component_a_valence_down_quark_count,
    lithography_medium_component_b_valence_up_quark_count,
    lithography_medium_component_b_valence_down_quark_count,
    lithography_medium_component_a_proton_count,
    lithography_medium_component_b_proton_count,
    lithography_medium_component_a_neutron_count,
    lithography_medium_component_b_neutron_count,
    lithography_medium_component_a_atomic_number,
    lithography_medium_component_b_atomic_number,
    lithography_medium_component_a_isotope_mass_number,
    lithography_medium_component_b_isotope_mass_number,
]

LITHOGRAPHY_MEDIUM_COMPONENT_EQUATIONS = [
    ineq_lithography_medium_component_a_stoichiometric_count_at_least_one,
    ineq_lithography_medium_component_b_stoichiometric_count_at_least_one,
    eq_lithography_medium_component_a_proton_count_from_valence_quarks,
    eq_lithography_medium_component_a_neutron_count_from_valence_quarks,
    eq_lithography_medium_component_b_proton_count_from_valence_quarks,
    eq_lithography_medium_component_b_neutron_count_from_valence_quarks,
    ineq_lithography_medium_component_a_valence_quarks_imply_nonnegative_protons,
    ineq_lithography_medium_component_a_valence_quarks_imply_positive_protons,
    ineq_lithography_medium_component_a_valence_quarks_imply_nonnegative_neutrons,
    eq_lithography_medium_component_a_valence_quark_triplet_integrality,
    ineq_lithography_medium_component_b_valence_quarks_imply_nonnegative_protons,
    ineq_lithography_medium_component_b_valence_quarks_imply_positive_protons,
    ineq_lithography_medium_component_b_valence_quarks_imply_nonnegative_neutrons,
    eq_lithography_medium_component_b_valence_quark_triplet_integrality,
    eq_lithography_medium_component_a_atomic_number,
    eq_lithography_medium_component_b_atomic_number,
    eq_lithography_medium_component_a_isotope_mass_number,
    eq_lithography_medium_component_b_isotope_mass_number,
]


__all__ = [
    "LITHOGRAPHY_MEDIUM_COMPOSITION_REF",
    "lithography_medium_component_a_stoichiometric_count",
    "lithography_medium_component_b_stoichiometric_count",
    "lithography_medium_component_a_valence_up_quark_count",
    "lithography_medium_component_a_valence_down_quark_count",
    "lithography_medium_component_b_valence_up_quark_count",
    "lithography_medium_component_b_valence_down_quark_count",
    "lithography_medium_component_a_proton_count",
    "lithography_medium_component_b_proton_count",
    "lithography_medium_component_a_neutron_count",
    "lithography_medium_component_b_neutron_count",
    "lithography_medium_component_a_atomic_number",
    "lithography_medium_component_b_atomic_number",
    "lithography_medium_component_a_isotope_mass_number",
    "lithography_medium_component_b_isotope_mass_number",
    "ineq_lithography_medium_component_a_stoichiometric_count_at_least_one",
    "ineq_lithography_medium_component_b_stoichiometric_count_at_least_one",
    "eq_lithography_medium_component_a_proton_count_from_valence_quarks",
    "eq_lithography_medium_component_a_neutron_count_from_valence_quarks",
    "eq_lithography_medium_component_b_proton_count_from_valence_quarks",
    "eq_lithography_medium_component_b_neutron_count_from_valence_quarks",
    "ineq_lithography_medium_component_a_valence_quarks_imply_nonnegative_protons",
    "ineq_lithography_medium_component_a_valence_quarks_imply_positive_protons",
    "ineq_lithography_medium_component_a_valence_quarks_imply_nonnegative_neutrons",
    "eq_lithography_medium_component_a_valence_quark_triplet_integrality",
    "ineq_lithography_medium_component_b_valence_quarks_imply_nonnegative_protons",
    "ineq_lithography_medium_component_b_valence_quarks_imply_positive_protons",
    "ineq_lithography_medium_component_b_valence_quarks_imply_nonnegative_neutrons",
    "eq_lithography_medium_component_b_valence_quark_triplet_integrality",
    "eq_lithography_medium_component_a_atomic_number",
    "eq_lithography_medium_component_b_atomic_number",
    "eq_lithography_medium_component_a_isotope_mass_number",
    "eq_lithography_medium_component_b_isotope_mass_number",
    "LITHOGRAPHY_MEDIUM_COMPONENT_VARIABLES",
    "LITHOGRAPHY_MEDIUM_COMPONENT_EQUATIONS",
]
