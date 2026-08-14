"""
scopes/physical_lithography_medium_intercomponent_geometry.py
=============================================================

Geometry of the A-B bond: each component gets an effective radius from a
scale factor, a gap fraction sets the space between them, and the effective
separation is the sum of the two radii plus the gap. This separation is
what the screened Coulomb binding relation and the packing-length density
closure both consume.
"""

import sympy as sp

from ..core import Approximation, eq
from .physical_lithography_medium_binding import (
    lithography_medium_component_nuclear_radius_coefficient,
)
from .physical_lithography_medium_components import (
    LITHOGRAPHY_MEDIUM_COMPOSITION_REF,
    lithography_medium_component_a_isotope_mass_number,
    lithography_medium_component_b_isotope_mass_number,
)
from .physical_lithography_medium_intercomponent_variables import (
    lithography_medium_component_a_effective_intercomponent_radius,
    lithography_medium_component_a_intercomponent_radius_scale_factor,
    lithography_medium_component_b_effective_intercomponent_radius,
    lithography_medium_component_b_intercomponent_radius_scale_factor,
    lithography_medium_intercomponent_effective_separation,
    lithography_medium_intercomponent_gap,
    lithography_medium_intercomponent_gap_fraction,
)


eq_lithography_medium_component_a_effective_intercomponent_radius = Approximation(
    "physical.eq.lithography_medium_component_a_effective_intercomponent_radius",
    lithography_medium_component_a_effective_intercomponent_radius.symbol,
    (
        lithography_medium_component_nuclear_radius_coefficient.symbol
        * lithography_medium_component_a_isotope_mass_number.symbol**sp.Rational(1, 3)
        * lithography_medium_component_a_intercomponent_radius_scale_factor.symbol
    ),
    (
        (lithography_medium_component_nuclear_radius_coefficient.symbol > 0)
        & (lithography_medium_component_a_isotope_mass_number.symbol > 0)
        & (lithography_medium_component_a_intercomponent_radius_scale_factor.symbol > 0)
    ),
    "Component-A effective intercomponent radius from nuclear radius scaling and local geometry factor.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_component_b_effective_intercomponent_radius = Approximation(
    "physical.eq.lithography_medium_component_b_effective_intercomponent_radius",
    lithography_medium_component_b_effective_intercomponent_radius.symbol,
    (
        lithography_medium_component_nuclear_radius_coefficient.symbol
        * lithography_medium_component_b_isotope_mass_number.symbol**sp.Rational(1, 3)
        * lithography_medium_component_b_intercomponent_radius_scale_factor.symbol
    ),
    (
        (lithography_medium_component_nuclear_radius_coefficient.symbol > 0)
        & (lithography_medium_component_b_isotope_mass_number.symbol > 0)
        & (lithography_medium_component_b_intercomponent_radius_scale_factor.symbol > 0)
    ),
    "Component-B effective intercomponent radius from nuclear radius scaling and local geometry factor.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_intercomponent_gap_from_radius_fraction = Approximation(
    "physical.eq.lithography_medium_intercomponent_gap_from_radius_fraction",
    lithography_medium_intercomponent_gap.symbol,
    (
        lithography_medium_intercomponent_gap_fraction.symbol
        * (
            lithography_medium_component_a_effective_intercomponent_radius.symbol
            + lithography_medium_component_b_effective_intercomponent_radius.symbol
        )
    ),
    (
        (lithography_medium_intercomponent_gap_fraction.symbol >= 0)
        & (lithography_medium_component_a_effective_intercomponent_radius.symbol > 0)
        & (lithography_medium_component_b_effective_intercomponent_radius.symbol > 0)
    ),
    "Residual intercomponent gap from effective radii and a dimensionless gap fraction.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_intercomponent_effective_separation = eq(
    "physical.eq.lithography_medium_intercomponent_effective_separation",
    lithography_medium_intercomponent_effective_separation.symbol,
    (
        lithography_medium_component_a_effective_intercomponent_radius.symbol
        + lithography_medium_component_b_effective_intercomponent_radius.symbol
        + lithography_medium_intercomponent_gap.symbol
    ),
    "Intercomponent effective separation from component effective radii plus residual gap.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)


LITHOGRAPHY_MEDIUM_INTERCOMPONENT_GEOMETRY_EQUATIONS = [
    eq_lithography_medium_component_a_effective_intercomponent_radius,
    eq_lithography_medium_component_b_effective_intercomponent_radius,
    eq_lithography_medium_intercomponent_gap_from_radius_fraction,
    eq_lithography_medium_intercomponent_effective_separation,
]

LITHOGRAPHY_MEDIUM_INTERCOMPONENT_GEOMETRY_EXPORTS = [
    "eq_lithography_medium_component_a_effective_intercomponent_radius",
    "eq_lithography_medium_component_b_effective_intercomponent_radius",
    "eq_lithography_medium_intercomponent_gap_from_radius_fraction",
    "eq_lithography_medium_intercomponent_effective_separation",
]

__all__ = [
    *LITHOGRAPHY_MEDIUM_INTERCOMPONENT_GEOMETRY_EXPORTS,
    "LITHOGRAPHY_MEDIUM_INTERCOMPONENT_GEOMETRY_EQUATIONS",
    "LITHOGRAPHY_MEDIUM_INTERCOMPONENT_GEOMETRY_EXPORTS",
]
