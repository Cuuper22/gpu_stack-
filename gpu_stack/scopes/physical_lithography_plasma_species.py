"""
scopes/physical_lithography_plasma_species.py
=============================================

Source-species gas inventory and thermal scales for the lithography plasma.
"""

import sympy as sp

from ..constants import BOLTZMANN, NEUTRON_MASS, PROTON_MASS, SPEED_OF_LIGHT
from ..core import Approximation, Inequality, Reference, ge, gt, valid_all, var
from ..core.units import KELVIN, KILOGRAM, METER, PASCAL, SECOND
from .physical_lithography_species import (
    lithography_source_neutron_count,
    lithography_source_proton_count,
)


LITHOGRAPHY_SOURCE_PLASMA_STATE_REF = Reference(
    citation=(
        "Lithography source plasma state: absorbed drive power from source "
        "pulse energy and repetition rate; pulse duration from pulse period "
        "and duty factor; temporal shape factor from trapezoidal waveform "
        "fractions; peak intensity from pulse fluence, duration, and waveform "
        "shape; pulse energy from peak drive intensity, "
        "focus-derived spot area, pulse duration, and waveform shape factor; "
        "source-species density from partial pressure and gas "
        "temperature; source-species mass from nuclear composition; "
        "source-species thermal speed from gas temperature and particle mass; "
        "active volume from spot-coupled column geometry, radial expansion "
        "over the pulse, and fill factor; absorption optical depth from "
        "species density, cross section, and path length; confinement time "
        "from loss path and loss speed; free-electron count from species "
        "inventory and charge-fraction electron yield; mean kinetic energy "
        "and Debye length from the resulting temperature and density"
    ),
    kind="memo",
)


lithography_source_plasma_species_partial_pressure = var(
    "physical.lithography.source_plasma_species_partial_pressure",
    "p_species_plasma_litho_src",
    "Pa",
    "Partial pressure of source species feeding the active lithography plasma.",
    scope="physical",
    positive=True,
    sp_units=PASCAL,
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
)
lithography_source_plasma_species_gas_temperature = var(
    "physical.lithography.source_plasma_species_gas_temperature",
    "T_species_gas_litho_src",
    "K",
    "Gas temperature of the source species before plasma ionization closure.",
    scope="physical",
    positive=True,
    sp_units=KELVIN,
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
)
lithography_source_plasma_species_number_density = var(
    "physical.lithography.source_plasma_species_number_density",
    "n_species_plasma_litho_src",
    "1/m^3",
    "Source-species number density in the active lithography plasma feed.",
    scope="physical",
    positive=True,
    sp_units=sp.Integer(1) / METER**3,
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
)
lithography_source_plasma_species_particle_mass = var(
    "physical.lithography.source_plasma_species_particle_mass",
    "m_plasma_species_litho_src",
    "kg",
    "Approximate source-plasma heavy-particle mass from nuclear proton and neutron rest masses.",
    scope="physical",
    positive=True,
    sp_units=KILOGRAM,
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
)
lithography_source_plasma_species_thermal_speed = var(
    "physical.lithography.source_plasma_species_thermal_speed",
    "v_th_species_litho_src",
    "m/s",
    "Characteristic source-species thermal speed from gas temperature and heavy-particle mass.",
    scope="physical",
    positive=True,
    sp_units=METER / SECOND,
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
)

ineq_lithography_source_plasma_species_partial_pressure_positive = Inequality(
    "physical.ineq.lithography_source_plasma_species_partial_pressure_positive",
    lithography_source_plasma_species_partial_pressure.symbol,
    sp.Integer(0),
    ">",
    "Source-species partial pressure must be positive for the ideal-gas plasma feed boundary.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
)
ineq_lithography_source_plasma_species_gas_temperature_positive = Inequality(
    "physical.ineq.lithography_source_plasma_species_gas_temperature_positive",
    lithography_source_plasma_species_gas_temperature.symbol,
    sp.Integer(0),
    ">",
    "Source-species gas temperature must be positive for the thermal plasma feed boundary.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
)
ineq_lithography_source_plasma_species_number_density_positive = Inequality(
    "physical.ineq.lithography_source_plasma_species_number_density_positive",
    lithography_source_plasma_species_number_density.symbol,
    sp.Integer(0),
    ">",
    "Source-species number density must remain positive under the ideal-gas plasma feed closure.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
)
ineq_lithography_source_plasma_species_thermal_speed_positive = Inequality(
    "physical.ineq.lithography_source_plasma_species_thermal_speed_positive",
    lithography_source_plasma_species_thermal_speed.symbol,
    sp.Integer(0),
    ">",
    "Source-species thermal speed must be positive under the gas-temperature closure.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
)
ineq_lithography_source_plasma_species_thermal_speed_subluminal = Inequality(
    "physical.ineq.lithography_source_plasma_species_thermal_speed_subluminal",
    lithography_source_plasma_species_thermal_speed.symbol,
    SPEED_OF_LIGHT.symbol,
    "<",
    "Classical source-species thermal speed must remain below the speed of light.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)


eq_lithography_source_plasma_species_number_density_from_ideal_gas = Approximation(
    "physical.eq.lithography_source_plasma_species_number_density_from_ideal_gas",
    lithography_source_plasma_species_number_density.symbol,
    (
        lithography_source_plasma_species_partial_pressure.symbol
        / (
            BOLTZMANN.symbol
            * lithography_source_plasma_species_gas_temperature.symbol
        )
    ),
    valid_all(
        gt(lithography_source_plasma_species_partial_pressure.symbol, 0),
        gt(lithography_source_plasma_species_gas_temperature.symbol, 0),
        gt(BOLTZMANN.symbol, 0),
    ),
    "Source-species number density from the ideal-gas relation p = n k_B T.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_species_particle_mass_from_nuclear_counts = Approximation(
    "physical.eq.lithography_source_plasma_species_particle_mass_from_nuclear_counts",
    lithography_source_plasma_species_particle_mass.symbol,
    (
        lithography_source_proton_count.symbol * PROTON_MASS.symbol
        + lithography_source_neutron_count.symbol * NEUTRON_MASS.symbol
    ),
    valid_all(
        ge(lithography_source_proton_count.symbol, 0),
        ge(lithography_source_neutron_count.symbol, 0),
        gt(
            lithography_source_proton_count.symbol
            + lithography_source_neutron_count.symbol,
            0,
        ),
        gt(PROTON_MASS.symbol, 0),
        gt(NEUTRON_MASS.symbol, 0),
    ),
    "Approximate source-plasma heavy-particle mass from proton and neutron rest-mass counts.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_species_thermal_speed_from_gas_temperature = Approximation(
    "physical.eq.lithography_source_plasma_species_thermal_speed_from_gas_temperature",
    lithography_source_plasma_species_thermal_speed.symbol,
    (
        BOLTZMANN.symbol
        * lithography_source_plasma_species_gas_temperature.symbol
        / lithography_source_plasma_species_particle_mass.symbol
    )
    ** sp.Rational(1, 2),
    valid_all(
        gt(BOLTZMANN.symbol, 0),
        gt(lithography_source_plasma_species_gas_temperature.symbol, 0),
        gt(lithography_source_plasma_species_particle_mass.symbol, 0),
    ),
    "Source-species thermal speed scale from gas temperature and heavy-particle mass.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)


LITHOGRAPHY_SOURCE_PLASMA_SPECIES_INVENTORY_VARIABLES = [
    lithography_source_plasma_species_partial_pressure,
    lithography_source_plasma_species_gas_temperature,
    lithography_source_plasma_species_number_density,
]

LITHOGRAPHY_SOURCE_PLASMA_SPECIES_TRANSPORT_VARIABLES = [
    lithography_source_plasma_species_particle_mass,
    lithography_source_plasma_species_thermal_speed,
]

LITHOGRAPHY_SOURCE_PLASMA_SPECIES_VARIABLES = [
    *LITHOGRAPHY_SOURCE_PLASMA_SPECIES_INVENTORY_VARIABLES,
    *LITHOGRAPHY_SOURCE_PLASMA_SPECIES_TRANSPORT_VARIABLES,
]

LITHOGRAPHY_SOURCE_PLASMA_SPECIES_INVENTORY_EQUATIONS = [
    ineq_lithography_source_plasma_species_partial_pressure_positive,
    ineq_lithography_source_plasma_species_gas_temperature_positive,
    eq_lithography_source_plasma_species_number_density_from_ideal_gas,
    ineq_lithography_source_plasma_species_number_density_positive,
]

LITHOGRAPHY_SOURCE_PLASMA_SPECIES_TRANSPORT_EQUATIONS = [
    eq_lithography_source_plasma_species_particle_mass_from_nuclear_counts,
    eq_lithography_source_plasma_species_thermal_speed_from_gas_temperature,
    ineq_lithography_source_plasma_species_thermal_speed_positive,
    ineq_lithography_source_plasma_species_thermal_speed_subluminal,
]

LITHOGRAPHY_SOURCE_PLASMA_SPECIES_EQUATIONS = [
    *LITHOGRAPHY_SOURCE_PLASMA_SPECIES_INVENTORY_EQUATIONS,
    *LITHOGRAPHY_SOURCE_PLASMA_SPECIES_TRANSPORT_EQUATIONS,
]


__all__ = [
    "LITHOGRAPHY_SOURCE_PLASMA_STATE_REF",
    "lithography_source_plasma_species_partial_pressure",
    "lithography_source_plasma_species_gas_temperature",
    "lithography_source_plasma_species_number_density",
    "lithography_source_plasma_species_particle_mass",
    "lithography_source_plasma_species_thermal_speed",
    "ineq_lithography_source_plasma_species_partial_pressure_positive",
    "ineq_lithography_source_plasma_species_gas_temperature_positive",
    "ineq_lithography_source_plasma_species_number_density_positive",
    "ineq_lithography_source_plasma_species_thermal_speed_positive",
    "ineq_lithography_source_plasma_species_thermal_speed_subluminal",
    "eq_lithography_source_plasma_species_number_density_from_ideal_gas",
    "eq_lithography_source_plasma_species_particle_mass_from_nuclear_counts",
    "eq_lithography_source_plasma_species_thermal_speed_from_gas_temperature",
    "LITHOGRAPHY_SOURCE_PLASMA_SPECIES_INVENTORY_VARIABLES",
    "LITHOGRAPHY_SOURCE_PLASMA_SPECIES_TRANSPORT_VARIABLES",
    "LITHOGRAPHY_SOURCE_PLASMA_SPECIES_VARIABLES",
    "LITHOGRAPHY_SOURCE_PLASMA_SPECIES_INVENTORY_EQUATIONS",
    "LITHOGRAPHY_SOURCE_PLASMA_SPECIES_TRANSPORT_EQUATIONS",
    "LITHOGRAPHY_SOURCE_PLASMA_SPECIES_EQUATIONS",
]
