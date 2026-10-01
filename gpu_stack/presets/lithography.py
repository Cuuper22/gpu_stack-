"""
gpu_stack.presets.lithography
=============================

Exposure inputs for the two lithography tools that matter for a modern GPU:
EUV (13.5 nm light) and ArF immersion (193 nm light through water). Each
preset assigns only the three optics roots: wavelength, numerical aperture,
and the refractive index of the medium under the lens. The k1 process
factors are left open because they belong to a fab's process, not to the
tool.
"""

from __future__ import annotations

from ..core.presets import Preset


EUV_WAVELENGTH_M = 13.5e-9
EUV_NUMERICAL_APERTURE = 0.33
ARF_IMMERSION_WAVELENGTH_M = 193e-9
ARF_IMMERSION_NUMERICAL_APERTURE = 1.35
WATER_REFRACTIVE_INDEX_193NM = 1.44

_ASML_SOURCE = (
    "ASML product specifications: TWINSCAN NXE:3600D (EUV, 13.5 nm, NA 0.33) "
    "and TWINSCAN NXT:2000i (ArF immersion, 193 nm, NA 1.35), "
    "https://www.asml.com/en/products"
)

euv_exposure = Preset(
    name="euv_exposure",
    description=(
        "EUV exposure optics: 13.5 nm wavelength, 0.33 numerical aperture, "
        "vacuum between lens and wafer."
    ),
    assignments={
        "physical.lithography.wavelength": EUV_WAVELENGTH_M,
        "physical.lithography.numerical_aperture": EUV_NUMERICAL_APERTURE,
        "physical.lithography.medium_refractive_index": 1.0,
    },
    source=_ASML_SOURCE,
    notes=(
        "EUV light is absorbed by air and glass, so the optics are mirrors in "
        "vacuum and the medium index is 1.",
        "High-NA EUV tools use NA 0.55; assign that value to "
        "physical.lithography.numerical_aperture to model them.",
    ),
)

arf_immersion_exposure = Preset(
    name="arf_immersion_exposure",
    description=(
        "ArF immersion exposure optics: 193 nm wavelength, 1.35 numerical "
        "aperture, water between lens and wafer."
    ),
    assignments={
        "physical.lithography.wavelength": ARF_IMMERSION_WAVELENGTH_M,
        "physical.lithography.numerical_aperture": (
            ARF_IMMERSION_NUMERICAL_APERTURE
        ),
        "physical.lithography.medium_refractive_index": (
            WATER_REFRACTIVE_INDEX_193NM
        ),
    },
    source=(
        f"{_ASML_SOURCE}; refractive index of water near 193 nm is about "
        "1.44 (Burnett and Kaplan, 2004, measurement of the refractive index "
        "of water at 193 nm)."
    ),
    notes=(
        "Numerical aperture cannot exceed the medium index, so 1.35 is "
        "close to the limit that water allows.",
    ),
)


EXPOSURE_PRESETS = (euv_exposure, arf_immersion_exposure)


__all__ = [
    "ARF_IMMERSION_NUMERICAL_APERTURE",
    "ARF_IMMERSION_WAVELENGTH_M",
    "EUV_NUMERICAL_APERTURE",
    "EUV_WAVELENGTH_M",
    "EXPOSURE_PRESETS",
    "WATER_REFRACTIVE_INDEX_193NM",
    "arf_immersion_exposure",
    "euv_exposure",
]
