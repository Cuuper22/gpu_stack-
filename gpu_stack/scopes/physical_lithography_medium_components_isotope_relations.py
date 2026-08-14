"""
scopes/physical_lithography_medium_components_isotope_relations.py
==================================================================

Relations that derive imaging-medium component isotope descriptors from
the calibration boundary, which is the proton count Z and neutron count N
of each component. Valence quark counts follow from the proton uud and
neutron udd quark content: U = 2Z + N (each proton carries 2 up quarks,
each neutron 1) and D = Z + 2N (each proton 1 down quark, each neutron 2).
This is an exact identity, not an approximation -- it holds for any nucleus
regardless of binding energy or nuclear model, and the total U + D =
3(Z + N) = 3A is always divisible by 3 (baryon number conservation). The
atomic number is likewise recovered as an alias of Z.
"""

import sympy as sp

from ..core import Approximation, Inequality, Reference, eq
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


_QUARK_MODEL_REF = Reference(
    citation=(
        "Particle Data Group Review of Particle Physics, quark model: "
        "proton = uud (2 up, 1 down), neutron = udd (1 up, 2 down). "
        "For a nucleus with Z protons and N neutrons: "
        "U = 2*Z + N, D = Z + 2*N. "
        "PDG, https://pdg.lbl.gov/"
    ),
    kind="database",
    url="https://pdg.lbl.gov/",
)


eq_lithography_medium_component_a_valence_up_quark_count_from_zn = eq(
    "physical.eq.lithography_medium_component_a_valence_up_quark_count_from_zn",
    lithography_medium_component_a_valence_up_quark_count.symbol,
    2 * lithography_medium_component_a_proton_count.symbol
    + lithography_medium_component_a_neutron_count.symbol,
    "Component A up-quark count from proton and neutron counts: U = 2Z + N.",
    references=[_QUARK_MODEL_REF],
    check_units=True,
)
eq_lithography_medium_component_a_valence_down_quark_count_from_zn = eq(
    "physical.eq.lithography_medium_component_a_valence_down_quark_count_from_zn",
    lithography_medium_component_a_valence_down_quark_count.symbol,
    lithography_medium_component_a_proton_count.symbol
    + 2 * lithography_medium_component_a_neutron_count.symbol,
    "Component A down-quark count from proton and neutron counts: D = Z + 2N.",
    references=[_QUARK_MODEL_REF],
    check_units=True,
)
eq_lithography_medium_component_b_valence_up_quark_count_from_zn = eq(
    "physical.eq.lithography_medium_component_b_valence_up_quark_count_from_zn",
    lithography_medium_component_b_valence_up_quark_count.symbol,
    2 * lithography_medium_component_b_proton_count.symbol
    + lithography_medium_component_b_neutron_count.symbol,
    "Component B up-quark count from proton and neutron counts: U = 2Z + N.",
    references=[_QUARK_MODEL_REF],
    check_units=True,
)
eq_lithography_medium_component_b_valence_down_quark_count_from_zn = eq(
    "physical.eq.lithography_medium_component_b_valence_down_quark_count_from_zn",
    lithography_medium_component_b_valence_down_quark_count.symbol,
    lithography_medium_component_b_proton_count.symbol
    + 2 * lithography_medium_component_b_neutron_count.symbol,
    "Component B down-quark count from proton and neutron counts: D = Z + 2N.",
    references=[_QUARK_MODEL_REF],
    check_units=True,
)


ineq_lithography_medium_component_a_proton_count_positive = Inequality(
    "physical.ineq.lithography_medium_component_a_proton_count_positive",
    lithography_medium_component_a_proton_count.symbol,
    sp.Integer(1),
    ">=",
    "Component A must have at least one proton (Z >= 1) to be a nucleus.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
ineq_lithography_medium_component_b_proton_count_positive = Inequality(
    "physical.ineq.lithography_medium_component_b_proton_count_positive",
    lithography_medium_component_b_proton_count.symbol,
    sp.Integer(1),
    ">=",
    "Component B must have at least one proton (Z >= 1) to be a nucleus.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
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
    eq_lithography_medium_component_a_valence_up_quark_count_from_zn,
    eq_lithography_medium_component_a_valence_down_quark_count_from_zn,
    eq_lithography_medium_component_b_valence_up_quark_count_from_zn,
    eq_lithography_medium_component_b_valence_down_quark_count_from_zn,
    ineq_lithography_medium_component_a_proton_count_positive,
    ineq_lithography_medium_component_b_proton_count_positive,
    eq_lithography_medium_component_a_atomic_number,
    eq_lithography_medium_component_b_atomic_number,
    eq_lithography_medium_component_a_isotope_mass_number,
    eq_lithography_medium_component_b_isotope_mass_number,
]


LITHOGRAPHY_MEDIUM_COMPONENT_ISOTOPE_RELATION_EXPORTS = [
    "eq_lithography_medium_component_a_valence_up_quark_count_from_zn",
    "eq_lithography_medium_component_a_valence_down_quark_count_from_zn",
    "eq_lithography_medium_component_b_valence_up_quark_count_from_zn",
    "eq_lithography_medium_component_b_valence_down_quark_count_from_zn",
    "ineq_lithography_medium_component_a_proton_count_positive",
    "ineq_lithography_medium_component_b_proton_count_positive",
    "eq_lithography_medium_component_a_atomic_number",
    "eq_lithography_medium_component_b_atomic_number",
    "eq_lithography_medium_component_a_isotope_mass_number",
    "eq_lithography_medium_component_b_isotope_mass_number",
]


__all__ = [*LITHOGRAPHY_MEDIUM_COMPONENT_ISOTOPE_RELATION_EXPORTS]
