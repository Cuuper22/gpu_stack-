"""
scopes/physical_lithography_optical_core.py
===========================================

Exposure wavelength, photon frequency, and optical-source frequency bridge.
"""

import sympy as sp

from ..core import Reference, eq, var
from ..core.units import HZ, METER, SECOND
from ..constants import PLANCK, SPEED_OF_LIGHT
from .physical_lithography_source import lithography_photon_energy


LITHOGRAPHY_REF = Reference(
    citation="Lithography abstraction: Rayleigh-style critical dimensions from wavelength, numerical aperture, process k1 factors, and signed process biases",
    kind="memo",
)


lithography_wavelength = var(
    "physical.lithography.wavelength", "lambda_litho", "m",
    "Exposure wavelength used by the lithography abstraction.",
    scope="physical",
    positive=True,
    sp_units=METER,
    references=[LITHOGRAPHY_REF],
)
lithography_photon_frequency = var(
    "physical.lithography.photon_frequency", "f_photon_litho", "Hz",
    "Optical photon frequency of the lithography exposure source.",
    scope="physical",
    positive=True,
    sp_units=HZ,
    references=[LITHOGRAPHY_REF],
)
lithography_source_angular_frequency = var(
    "physical.lithography.source_angular_frequency", "omega_litho", "1/s",
    "Angular optical frequency of the lithography exposure source.",
    scope="physical",
    positive=True,
    sp_units=1 / SECOND,
    references=[LITHOGRAPHY_REF],
)
lithography_numerical_aperture = var(
    "physical.lithography.numerical_aperture", "NA_litho", "dimensionless",
    "Numerical aperture of the lithography optical system.",
    scope="physical",
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_REF],
)


eq_lithography_photon_frequency = eq(
    "physical.eq.lithography_photon_frequency",
    lithography_photon_frequency.symbol,
    lithography_photon_energy.symbol / PLANCK.symbol,
    "Photon frequency from photon energy and Planck's constant.",
    references=[LITHOGRAPHY_REF],
    check_units=True,
)

eq_lithography_wavelength_from_frequency = eq(
    "physical.eq.lithography_wavelength_from_frequency",
    lithography_wavelength.symbol,
    SPEED_OF_LIGHT.symbol / lithography_photon_frequency.symbol,
    "Exposure wavelength from photon frequency and the speed of light in vacuum.",
    references=[LITHOGRAPHY_REF],
    check_units=True,
)

eq_lithography_source_angular_frequency = eq(
    "physical.eq.lithography_source_angular_frequency",
    lithography_source_angular_frequency.symbol,
    2 * sp.pi * lithography_photon_frequency.symbol,
    "Optical angular frequency from photon frequency.",
    references=[LITHOGRAPHY_REF],
    check_units=True,
)


LITHOGRAPHY_OPTICAL_CORE_VARIABLES = [
    lithography_wavelength,
    lithography_photon_frequency,
    lithography_source_angular_frequency,
    lithography_numerical_aperture,
]

LITHOGRAPHY_OPTICAL_CORE_EQUATIONS = [
    eq_lithography_photon_frequency,
    eq_lithography_wavelength_from_frequency,
    eq_lithography_source_angular_frequency,
]

LITHOGRAPHY_OPTICAL_CORE_EXPORTS = [
    "LITHOGRAPHY_REF",
    "lithography_wavelength",
    "lithography_photon_frequency",
    "lithography_source_angular_frequency",
    "lithography_numerical_aperture",
    "eq_lithography_photon_frequency",
    "eq_lithography_wavelength_from_frequency",
    "eq_lithography_source_angular_frequency",
    "LITHOGRAPHY_OPTICAL_CORE_VARIABLES",
    "LITHOGRAPHY_OPTICAL_CORE_EQUATIONS",
    "LITHOGRAPHY_OPTICAL_CORE_EXPORTS",
]

__all__ = LITHOGRAPHY_OPTICAL_CORE_EXPORTS
