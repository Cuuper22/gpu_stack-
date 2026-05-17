"""
scopes/physical_lithography_medium_components_isotope_relations.py
==================================================================

Relations that derive lithography imaging-medium component isotope descriptors.
"""

import sympy as sp

from ..core import Approximation, Inequality, RelationRole, eq
from .physical_lithography_medium_components_reference import (
    LITHOGRAPHY_MEDIUM_COMPOSITION_REF,
)
from .physical_lithography_medium_components_isotope_state import (
    lithography_medium_component_a_atomic_number,
    lithography_medium_component_a_isotope_mass_number,
    lithography_medium_component_a_neutron_count,
    lithography_medium_component_a_proton_count,
    lithography_medium_component_a_valence_down_quark_count,
    lithography_medium_component_a_valence_up_quark_count,
    lithography_medium_component_b_atomic_number,
    lithography_medium_component_b_isotope_mass_number,
    lithography_medium_component_b_neutron_count,
    lithography_medium_component_b_proton_count,
    lithography_medium_component_b_valence_down_quark_count,
    lithography_medium_component_b_valence_up_quark_count,
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


LITHOGRAPHY_MEDIUM_COMPONENT_ISOTOPE_RELATION_EQUATIONS = [
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


LITHOGRAPHY_MEDIUM_COMPONENT_ISOTOPE_RELATION_EXPORTS = [
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
]


__all__ = [*LITHOGRAPHY_MEDIUM_COMPONENT_ISOTOPE_RELATION_EXPORTS]
