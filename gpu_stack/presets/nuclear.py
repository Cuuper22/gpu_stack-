"""
gpu_stack.presets.nuclear
=========================

Guardrails for nuclear calibration presets.

The SEMF/liquid-drop coefficients are empirical calibration roots. This
module intentionally ships no numerical defaults: callers may construct a
Preset only by providing explicit source text plus assignments to the
registered SEMF root variables in SI joules.
"""

from __future__ import annotations

import math
from numbers import Real
from typing import Mapping

from ..constants import ELEMENTARY_CHARGE
from ..core.presets import Preset
from ..core.registry import Registry


SEMF_CALIBRATION_ROOTS = (
    "physical.lithography.nuclear_binding_volume_coefficient",
    "physical.lithography.nuclear_binding_surface_coefficient",
    "physical.lithography.nuclear_binding_coulomb_coefficient",
    "physical.lithography.nuclear_binding_asymmetry_coefficient",
    "physical.lithography.nuclear_pairing_gap_reference_energy",
)

_SEMF_CALIBRATION_ROOT_SET = frozenset(SEMF_CALIBRATION_ROOTS)

NUCLEAR_PAIRING_GAP_REFERENCE_ENERGY_ROOT = (
    "physical.lithography.nuclear_pairing_gap_reference_energy"
)
MEV_TO_JOULE = 1_000_000.0 * ELEMENTARY_CHARGE.value
MEV_TO_JOULE_SOURCE = (
    "1 MeV = 10^6 eV and 1 eV = e joules, using the exact 2019 SI "
    "elementary charge."
)

_SOURCE_NOTE = (
    "SEMF calibration coefficients are empirical fit parameters. This preset "
    "factory accepts only caller-provided values with explicit source text; "
    "gpu_stack.presets.nuclear does not publish coefficient defaults."
)


def semf_calibration_root_inventory() -> tuple[dict[str, object], ...]:
    """
    Return the SEMF calibration roots without attaching numerical values.

    The inventory is deliberately metadata-only so a caller can inspect which
    roots need sourced calibration while keeping the graph free of implicit
    coefficient defaults.
    """
    out: list[dict[str, object]] = []
    for name in SEMF_CALIBRATION_ROOTS:
        variable = Registry.variables[name]
        out.append(
            {
                "name": variable.name,
                "symbol": str(variable.symbol),
                "units": variable.units,
                "is_root_input": variable.is_root_input,
                "assumptions": dict(variable.assumptions),
                "reference_count": len(variable.references),
                "preset_value": None,
                "source_required": True,
            }
        )
    return tuple(out)


def mev_to_joule(value_mev: float) -> float:
    """
    Convert a caller-cited MeV energy value to SI joules.

    This is an exact unit conversion through the SI elementary charge. It does
    not decide whether a source value is the right SEMF coefficient or pairing
    semantic for a graph root.
    """
    if isinstance(value_mev, bool) or not isinstance(value_mev, Real):
        raise ValueError("MeV energy values must be finite real numbers")
    value = float(value_mev)
    if not math.isfinite(value):
        raise ValueError("MeV energy values must be finite real numbers")
    return value * MEV_TO_JOULE


def semf_pairing_gap_reference_energy_semantics() -> dict[str, object]:
    """
    Return metadata for the shared pairing-gap calibration root.

    The graph root is a reference energy Delta_pair_ref. A liquid-drop pairing
    coefficient a_pair is a derived calibration scale in this model:
    a_pair = Delta_pair_ref * sqrt(A_ref). A cited a_pair value therefore is
    not directly assignable to the pairing-gap root without a cited reference
    mass-number convention.
    """
    variable = Registry.variables[NUCLEAR_PAIRING_GAP_REFERENCE_ENERGY_ROOT]
    return {
        "root": variable.name,
        "symbol": str(variable.symbol),
        "units": variable.units,
        "mev_to_joule": MEV_TO_JOULE,
        "mev_to_joule_source": MEV_TO_JOULE_SOURCE,
        "direct_pairing_coefficient_assignable": False,
        "pairing_coefficient_relation": (
            "a_pair = Delta_pair_ref * sqrt(A_ref)"
        ),
        "why_not_direct": (
            "A pairing coefficient convention such as a_pair in MeV is not "
            "the same quantity as Delta_pair_ref. It needs a cited reference "
            "mass number before it can be converted into this root."
        ),
    }


def _clean_required_text(field: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"SEMF calibration preset requires non-blank {field}")
    return value.strip()


def _clean_notes(notes: tuple[str, ...]) -> tuple[str, ...]:
    if isinstance(notes, str):
        raise ValueError("SEMF calibration preset notes must be non-blank strings")
    cleaned: list[str] = []
    for note in notes:
        if not isinstance(note, str) or not note.strip():
            raise ValueError(
                "SEMF calibration preset notes must be non-blank strings"
            )
        cleaned.append(note.strip())
    return tuple(cleaned)


def _semf_root_assignments(assignments: Mapping[str, float]) -> dict[str, float]:
    if not assignments:
        raise ValueError("SEMF calibration preset requires at least one assignment")

    unknown = [name for name in assignments if name not in Registry.variables]
    if unknown:
        raise ValueError(
            "SEMF calibration assignments reference unknown variables: "
            f"{sorted(unknown)}"
        )

    unsupported = [
        name for name in assignments if name not in _SEMF_CALIBRATION_ROOT_SET
    ]
    if unsupported:
        raise ValueError(
            "SEMF calibration presets may assign SEMF calibration roots only: "
            f"{sorted(unsupported)}"
        )

    non_roots = [
        name for name in assignments if not Registry.variables[name].is_root_input
    ]
    if non_roots:
        raise ValueError(
            "SEMF calibration assignments must be root inputs only: "
            f"{sorted(non_roots)}"
        )

    non_numeric = [
        name
        for name, value in assignments.items()
        if isinstance(value, bool) or not isinstance(value, Real)
    ]
    if non_numeric:
        raise ValueError(
            "SEMF calibration assignments must be numeric SI joule values: "
            f"{sorted(non_numeric)}"
        )

    non_finite = [
        name for name, value in assignments.items() if not math.isfinite(float(value))
    ]
    if non_finite:
        raise ValueError(
            "SEMF calibration assignments must be finite SI joule values: "
            f"{sorted(non_finite)}"
        )

    return {name: float(value) for name, value in assignments.items()}


def semf_calibration_preset(
    *,
    name: str,
    description: str,
    assignments: Mapping[str, float],
    source_text: str,
    notes: tuple[str, ...] = (),
) -> Preset:
    """
    Build a sourced SEMF calibration Preset from caller-supplied values.

    Values must already be expressed in SI joules. The function does not
    convert MeV or publish a reference table because those choices belong with
    the cited calibration source, not in an unsourced default layer.
    """
    clean_name = _clean_required_text("name", name)
    clean_description = _clean_required_text("description", description)
    clean_source = _clean_required_text("source text", source_text)
    clean_notes = _clean_notes(notes)
    return Preset(
        name=clean_name,
        description=clean_description,
        assignments=_semf_root_assignments(assignments),
        source=clean_source,
        notes=(_SOURCE_NOTE, *clean_notes),
    ).require_source()


__all__ = [
    "MEV_TO_JOULE",
    "MEV_TO_JOULE_SOURCE",
    "NUCLEAR_PAIRING_GAP_REFERENCE_ENERGY_ROOT",
    "SEMF_CALIBRATION_ROOTS",
    "mev_to_joule",
    "semf_calibration_root_inventory",
    "semf_calibration_preset",
    "semf_pairing_gap_reference_energy_semantics",
]
