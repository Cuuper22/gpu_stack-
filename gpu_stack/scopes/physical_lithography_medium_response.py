"""
scopes/physical_lithography_medium_response.py
==============================================

Count and energy boundary layer for lithography imaging-medium response.
"""

import sympy as sp

from ..core import Approximation, Inequality, Reference, ge, gt, le, valid_all, var
from ..core.units import JOULE
from .physical_lithography_medium_composition import (
    lithography_medium_formula_unit_electron_count,
)
from .physical_lithography_source import lithography_photon_energy


LITHOGRAPHY_MEDIUM_RESPONSE_REF = Reference(
    citation="Lithography imaging-medium response: polarizable-electron counts, oscillator-strength allocation, and off-resonant bound-electron energy scale",
    kind="memo",
)


lithography_medium_polarizable_electron_count = var(
    "physical.lithography.medium_polarizable_electron_count",
    "N_e_pol_litho_med",
    "count",
    "Effective count of formula-unit electrons participating in the dominant electric polarization mode.",
    scope="physical",
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_RESPONSE_REF],
)
lithography_medium_polarizable_electron_fraction = var(
    "physical.lithography.medium_polarizable_electron_fraction",
    "eta_e_pol_litho_med",
    "dimensionless",
    "Fraction of formula-unit electrons participating in the dominant electric polarization mode.",
    scope="physical",
    nonnegative=True,
    value_range=(0.0, 1.0),
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_RESPONSE_REF],
)
lithography_medium_dominant_oscillator_electron_count = var(
    "physical.lithography.medium_dominant_oscillator_electron_count",
    "N_e_osc_dom_litho_med",
    "count",
    "Effective polarizable-electron oscillator-strength count assigned to the dominant medium resonance.",
    scope="physical",
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_RESPONSE_REF],
)
lithography_medium_oscillator_sum_rule_fraction = var(
    "physical.lithography.medium_oscillator_sum_rule_fraction",
    "eta_f_sum_litho_med",
    "dimensionless",
    "Fraction of the polarizable-electron oscillator-strength sum assigned to the dominant resonance.",
    scope="physical",
    nonnegative=True,
    value_range=(0.0, 1.0),
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_RESPONSE_REF],
)
lithography_medium_resonance_energy = var(
    "physical.lithography.medium_resonance_energy",
    "E_res_litho_med",
    "J",
    "Dominant bound-electron resonance energy of the lithography imaging medium.",
    scope="physical",
    positive=True,
    sp_units=JOULE,
    references=[LITHOGRAPHY_MEDIUM_RESPONSE_REF],
)
lithography_medium_resonance_to_source_frequency_ratio = var(
    "physical.lithography.medium_resonance_to_source_frequency_ratio",
    "rho_omega0_src_litho_med",
    "dimensionless",
    "Ratio of dominant medium resonance angular frequency to exposure-source angular frequency.",
    scope="physical",
    positive=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_RESPONSE_REF],
)


eq_lithography_medium_polarizable_electron_fraction_from_count = Approximation(
    "physical.eq.lithography_medium_polarizable_electron_fraction_from_count",
    lithography_medium_polarizable_electron_fraction.symbol,
    (
        lithography_medium_polarizable_electron_count.symbol
        / lithography_medium_formula_unit_electron_count.symbol
    ),
    valid_all(
        gt(lithography_medium_formula_unit_electron_count.symbol, 0),
        ge(lithography_medium_polarizable_electron_count.symbol, 0),
        le(
            lithography_medium_polarizable_electron_count.symbol,
            lithography_medium_formula_unit_electron_count.symbol,
        ),
    ),
    "Polarizable-electron fraction from effective polarizable electron count over formula-unit electron count.",
    references=[LITHOGRAPHY_MEDIUM_RESPONSE_REF],
    check_units=True,
)

ineq_lithography_medium_polarizable_electron_count_within_formula_unit = Inequality(
    "physical.ineq.lithography_medium_polarizable_electron_count_within_formula_unit",
    lithography_medium_polarizable_electron_count.symbol,
    lithography_medium_formula_unit_electron_count.symbol,
    "<=",
    "Polarizable electron count cannot exceed the formula-unit electron count.",
    references=[LITHOGRAPHY_MEDIUM_RESPONSE_REF],
    check_units=True,
)

ineq_lithography_medium_polarizable_electron_fraction_within_unit_interval = Inequality(
    "physical.ineq.lithography_medium_polarizable_electron_fraction_within_unit_interval",
    lithography_medium_polarizable_electron_fraction.symbol,
    sp.Integer(1),
    "<=",
    "Polarizable electron fraction cannot exceed the formula-unit electron inventory.",
    references=[LITHOGRAPHY_MEDIUM_RESPONSE_REF],
    check_units=True,
)

eq_lithography_medium_oscillator_sum_rule_fraction_from_count = Approximation(
    "physical.eq.lithography_medium_oscillator_sum_rule_fraction_from_count",
    lithography_medium_oscillator_sum_rule_fraction.symbol,
    (
        lithography_medium_dominant_oscillator_electron_count.symbol
        / lithography_medium_polarizable_electron_count.symbol
    ),
    valid_all(
        gt(lithography_medium_polarizable_electron_count.symbol, 0),
        ge(lithography_medium_dominant_oscillator_electron_count.symbol, 0),
        le(
            lithography_medium_dominant_oscillator_electron_count.symbol,
            lithography_medium_polarizable_electron_count.symbol,
        ),
    ),
    "Oscillator sum-rule fraction from dominant oscillator electron count over polarizable electron count.",
    references=[LITHOGRAPHY_MEDIUM_RESPONSE_REF],
    check_units=True,
)

ineq_lithography_medium_dominant_oscillator_electron_count_within_polarizable_count = Inequality(
    "physical.ineq.lithography_medium_dominant_oscillator_electron_count_within_polarizable_count",
    lithography_medium_dominant_oscillator_electron_count.symbol,
    lithography_medium_polarizable_electron_count.symbol,
    "<=",
    "Dominant oscillator electron count cannot exceed the polarizable electron count.",
    references=[LITHOGRAPHY_MEDIUM_RESPONSE_REF],
    check_units=True,
)

ineq_lithography_medium_dominant_oscillator_electron_count_within_formula_unit = Inequality(
    "physical.ineq.lithography_medium_dominant_oscillator_electron_count_within_formula_unit",
    lithography_medium_dominant_oscillator_electron_count.symbol,
    lithography_medium_formula_unit_electron_count.symbol,
    "<=",
    "Dominant oscillator electron count cannot exceed the formula-unit electron inventory.",
    references=[LITHOGRAPHY_MEDIUM_RESPONSE_REF],
    check_units=True,
)

ineq_lithography_medium_oscillator_sum_rule_fraction_within_unit_interval = Inequality(
    "physical.ineq.lithography_medium_oscillator_sum_rule_fraction_within_unit_interval",
    lithography_medium_oscillator_sum_rule_fraction.symbol,
    sp.Integer(1),
    "<=",
    "Dominant oscillator sum-rule fraction cannot exceed the available polarizable-electron oscillator-strength sum.",
    references=[LITHOGRAPHY_MEDIUM_RESPONSE_REF],
    check_units=True,
)

eq_lithography_medium_resonance_to_source_frequency_ratio_from_energy = Approximation(
    "physical.eq.lithography_medium_resonance_to_source_frequency_ratio_from_energy",
    lithography_medium_resonance_to_source_frequency_ratio.symbol,
    lithography_medium_resonance_energy.symbol / lithography_photon_energy.symbol,
    valid_all(
        gt(lithography_medium_resonance_energy.symbol, 0),
        gt(lithography_photon_energy.symbol, 0),
    ),
    "Medium resonance-to-source frequency ratio from dominant resonance energy over exposure photon energy.",
    references=[LITHOGRAPHY_MEDIUM_RESPONSE_REF],
    check_units=True,
)

ineq_lithography_medium_resonance_energy_above_source_photon_energy = Inequality(
    "physical.ineq.lithography_medium_resonance_energy_above_source_photon_energy",
    lithography_medium_resonance_energy.symbol,
    lithography_photon_energy.symbol,
    ">",
    "Dominant transparent-medium resonance energy should sit above the exposure photon energy for the off-resonant Lorentz response.",
    references=[LITHOGRAPHY_MEDIUM_RESPONSE_REF],
    check_units=True,
)

ineq_lithography_medium_resonance_to_source_frequency_ratio_above_unity = Inequality(
    "physical.ineq.lithography_medium_resonance_to_source_frequency_ratio_above_unity",
    lithography_medium_resonance_to_source_frequency_ratio.symbol,
    sp.Integer(1),
    ">",
    "Dominant transparent-medium resonance/source frequency ratio must exceed unity for the off-resonant Lorentz response.",
    references=[LITHOGRAPHY_MEDIUM_RESPONSE_REF],
    check_units=True,
)


LITHOGRAPHY_MEDIUM_RESPONSE_VARIABLES = [
    lithography_medium_polarizable_electron_count,
    lithography_medium_polarizable_electron_fraction,
    lithography_medium_dominant_oscillator_electron_count,
    lithography_medium_oscillator_sum_rule_fraction,
    lithography_medium_resonance_energy,
    lithography_medium_resonance_to_source_frequency_ratio,
]

LITHOGRAPHY_MEDIUM_RESPONSE_EQUATIONS = [
    eq_lithography_medium_polarizable_electron_fraction_from_count,
    ineq_lithography_medium_polarizable_electron_count_within_formula_unit,
    ineq_lithography_medium_polarizable_electron_fraction_within_unit_interval,
    eq_lithography_medium_oscillator_sum_rule_fraction_from_count,
    ineq_lithography_medium_dominant_oscillator_electron_count_within_polarizable_count,
    ineq_lithography_medium_dominant_oscillator_electron_count_within_formula_unit,
    ineq_lithography_medium_oscillator_sum_rule_fraction_within_unit_interval,
    eq_lithography_medium_resonance_to_source_frequency_ratio_from_energy,
    ineq_lithography_medium_resonance_energy_above_source_photon_energy,
    ineq_lithography_medium_resonance_to_source_frequency_ratio_above_unity,
]

LITHOGRAPHY_MEDIUM_RESPONSE_EXPORTS = [
    "LITHOGRAPHY_MEDIUM_RESPONSE_REF",
    "lithography_medium_polarizable_electron_count",
    "lithography_medium_polarizable_electron_fraction",
    "lithography_medium_dominant_oscillator_electron_count",
    "lithography_medium_oscillator_sum_rule_fraction",
    "lithography_medium_resonance_energy",
    "lithography_medium_resonance_to_source_frequency_ratio",
    "eq_lithography_medium_polarizable_electron_fraction_from_count",
    "ineq_lithography_medium_polarizable_electron_count_within_formula_unit",
    "ineq_lithography_medium_polarizable_electron_fraction_within_unit_interval",
    "eq_lithography_medium_oscillator_sum_rule_fraction_from_count",
    "ineq_lithography_medium_dominant_oscillator_electron_count_within_polarizable_count",
    "ineq_lithography_medium_dominant_oscillator_electron_count_within_formula_unit",
    "ineq_lithography_medium_oscillator_sum_rule_fraction_within_unit_interval",
    "eq_lithography_medium_resonance_to_source_frequency_ratio_from_energy",
    "ineq_lithography_medium_resonance_energy_above_source_photon_energy",
    "ineq_lithography_medium_resonance_to_source_frequency_ratio_above_unity",
    "LITHOGRAPHY_MEDIUM_RESPONSE_VARIABLES",
    "LITHOGRAPHY_MEDIUM_RESPONSE_EQUATIONS",
    "LITHOGRAPHY_MEDIUM_RESPONSE_EXPORTS",
]

__all__ = LITHOGRAPHY_MEDIUM_RESPONSE_EXPORTS
