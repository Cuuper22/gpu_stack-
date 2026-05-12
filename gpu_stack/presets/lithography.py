"""
gpu_stack.presets.lithography
=============================

Lithography source-plasma preset scaffolding.

These presets are intentionally narrow. Public ASML material describes the
EUV source context, but it does not publish enough operating detail to close
fluence, plasma thermodynamics, focusing geometry, or conversion efficiency in
this graph. Values below either come directly from cited public context or are
marked as modelling assumptions.
"""

from __future__ import annotations

from ..core.presets import Preset, combine
from ..core.registry import Registry


ASML_EUV_REPETITION_RATE_HZ = 50_000.0
ASML_EUV_PULSE_PERIOD_S = 1.0 / ASML_EUV_REPETITION_RATE_HZ

_ASML_EUV_PRODUCTS_SOURCE = (
    "ASML EUV lithography systems product page, "
    "https://www.asml.com/en/en/products/euv-lithography-systems "
    "(accessed 2026-05-06): EUV systems use 13.5 nm light; the light "
    "source uses a CO2 laser firing two separate laser pulses at a "
    "fast-moving drop of tin and does this up to 50,000 times per second."
)

_ASML_LIGHT_AND_LASERS_SOURCE = (
    "ASML Light and lasers lithography-principles page, "
    "https://www.asml.com/en/en/technology/lithography-principles/"
    "light-and-lasers (accessed 2026-05-06): ASML describes a "
    "laser-produced plasma source using molten tin droplets around "
    "25 microns in diameter moving at 70 m/s; a low-intensity pulse "
    "flattens the droplet and a more powerful pulse vaporizes it into an "
    "EUV-emitting plasma; the process is repeated 50,000 times every "
    "second."
)

_NIST_TIN_ATOMIC_DATA_SOURCE = (
    "NIST Atomic Data for Tin (Sn), "
    "https://physics.nist.gov/PhysRefData/Handbook/Tables/tintable1_a.htm "
    "(accessed 2026-05-06): Atomic Number = 50 and isotope table includes "
    "120Sn. The choice of 120Sn here is a representative source-species "
    "closure for the graph, not an ASML claim about isotope selection."
)

_PROVENANCE_ONLY = "provenance-only"
_ASSIGNED_ROOT = "assigned-root"

_ASML_EUV_PUBLIC_CONTEXT_FACTS: tuple[dict[str, object], ...] = (
    {
        "key": "euv_wavelength_13p5_nm",
        "label": "EUV wavelength",
        "public_value": 13.5e-9,
        "public_units": "m",
        "source": _ASML_EUV_PRODUCTS_SOURCE,
        "status": _PROVENANCE_ONLY,
        "assigned_root": None,
        "assigned_value": None,
        "candidate_root": "physical.lithography.wavelength",
        "withholding_reason": (
            "A graph exposure-wavelength root exists, but this preset is "
            "only the source-plasma public operating context. Assigning "
            "the imaging/exposure wavelength belongs in an explicit optics "
            "or exposure preset."
        ),
    },
    {
        "key": "tin_droplets",
        "label": "Molten tin droplets",
        "public_value": "tin",
        "public_units": None,
        "source": _ASML_LIGHT_AND_LASERS_SOURCE,
        "status": _PROVENANCE_ONLY,
        "assigned_root": None,
        "assigned_value": None,
        "candidate_root": None,
        "withholding_reason": (
            "The graph source-species roots require isotope-level closure; "
            "ASML's public context establishes tin LPP, not isotope "
            "selection or valence-quark counts."
        ),
    },
    {
        "key": "tin_droplet_diameter_25_micron",
        "label": "Tin droplet diameter",
        "public_value": 25e-6,
        "public_units": "m",
        "source": _ASML_LIGHT_AND_LASERS_SOURCE,
        "status": _PROVENANCE_ONLY,
        "assigned_root": None,
        "assigned_value": None,
        "candidate_root": None,
        "withholding_reason": (
            "The current source-plasma graph has no droplet-diameter root. "
            "Column radius, spot radius, and active volume are different "
            "post-drive plasma quantities."
        ),
    },
    {
        "key": "tin_droplet_speed_70_m_per_s",
        "label": "Tin droplet speed",
        "public_value": 70.0,
        "public_units": "m/s",
        "source": _ASML_LIGHT_AND_LASERS_SOURCE,
        "status": _PROVENANCE_ONLY,
        "assigned_root": None,
        "assigned_value": None,
        "candidate_root": None,
        "withholding_reason": (
            "The graph has thermal and expansion speeds, but not a "
            "pre-plasma droplet injection-speed root. Mapping 70 m/s onto "
            "those variables would change the physics."
        ),
    },
    {
        "key": "dual_pulse_sequence",
        "label": "Low-intensity pre-pulse plus stronger vaporizing pulse",
        "public_value": "two-pulse sequence",
        "public_units": None,
        "source": (
            f"{_ASML_EUV_PRODUCTS_SOURCE} {_ASML_LIGHT_AND_LASERS_SOURCE}"
        ),
        "status": _PROVENANCE_ONLY,
        "assigned_root": None,
        "assigned_value": None,
        "candidate_root": None,
        "withholding_reason": (
            "The graph exposes scalar pulse-period and pulse-shape roots, "
            "not a discrete pre-pulse/main-pulse sequence model with "
            "separate energies, timings, or shapes."
        ),
    },
    {
        "key": "source_repetition_rate_50_khz",
        "label": "Source repetition rate",
        "public_value": ASML_EUV_REPETITION_RATE_HZ,
        "public_units": "Hz",
        "source": (
            f"{_ASML_EUV_PRODUCTS_SOURCE} {_ASML_LIGHT_AND_LASERS_SOURCE}"
        ),
        "status": _ASSIGNED_ROOT,
        "assigned_root": "physical.lithography.source_plasma_pulse_period",
        "assigned_value": ASML_EUV_PULSE_PERIOD_S,
        "candidate_root": "physical.lithography.source_plasma_pulse_period",
        "withholding_reason": None,
        "mapping_note": (
            "ASML publishes repetition rate; the graph root is pulse period, "
            "so the assigned value is period = 1 / repetition_rate."
        ),
    },
)


def _root_assignments(assignments: dict[str, float]) -> dict[str, float]:
    unknown = [name for name in assignments if name not in Registry.variables]
    if unknown:
        raise ValueError(
            "lithography preset assignments reference unknown variables: "
            f"{sorted(unknown)}"
        )
    non_roots = [
        name
        for name in assignments
        if not Registry.variables[name].is_root_input
    ]
    if non_roots:
        raise ValueError(
            "lithography preset assignments must be root inputs only: "
            f"{sorted(non_roots)}"
        )
    return assignments


def _source_quark_assignments(protons: int, neutrons: int) -> dict[str, int]:
    return {
        "physical.lithography.source_valence_up_quark_count": (
            2 * protons + neutrons
        ),
        "physical.lithography.source_valence_down_quark_count": (
            protons + 2 * neutrons
        ),
    }


asml_euv_tin_lpp_public_context = Preset(
    name="asml_euv_tin_lpp_public_context",
    description=(
        "Public ASML EUV laser-produced-plasma context mapped only onto the "
        "root currently supported by this graph: the source-plasma pulse "
        "period corresponding to 50 kHz operation."
    ),
    assignments=_root_assignments(
        {
            "physical.lithography.source_plasma_pulse_period": (
                ASML_EUV_PULSE_PERIOD_S
            ),
        }
    ),
    source=f"{_ASML_EUV_PRODUCTS_SOURCE} {_ASML_LIGHT_AND_LASERS_SOURCE}",
    notes=(
        "The assigned pulse period is the reciprocal of ASML's public "
        "50,000-times-per-second EUV source statement. Treat it as a public "
        "operating-boundary context, not as a per-tool calibration.",
        "ASML's 13.5 nm EUV wavelength, tin-droplet diameter, droplet speed, "
        "dual-pulse sequence, and vacuum context are recorded in provenance "
        "but are not assigned here because they either lack a matching root "
        "or belong to a separate exposure/optics or source-species preset.",
        "No drive fluence, gas pressure, gas temperature, collection optics, "
        "detuning, heating fraction, or conversion-efficiency values are "
        "invented here.",
    ),
)


def asml_euv_public_context_inventory() -> tuple[dict[str, object], ...]:
    """
    Return ASML public EUV facts and their graph-assignment status.

    This is metadata-only except for the one fact that this preset actually
    assigns: ASML's 50 kHz public source cadence mapped to the graph's pulse
    period root. All other rows explain why the fact stays provenance-only.
    """
    assignments = asml_euv_tin_lpp_public_context.assignments
    out: list[dict[str, object]] = []
    for fact in _ASML_EUV_PUBLIC_CONTEXT_FACTS:
        row = dict(fact)
        assigned_root = row["assigned_root"]
        row["assigned_in_preset"] = (
            assigned_root in assignments if assigned_root is not None else False
        )
        if assigned_root is not None:
            row["assigned_value"] = assignments.get(str(assigned_root))
        out.append(row)
    return tuple(out)


source_tin_120_composition_assumption = Preset(
    name="source_tin_120_composition_assumption",
    description=(
        "Assumption-labeled source-species composition closure for a 120Sn "
        "tin plasma source, encoded through exact valence-quark root counts."
    ),
    assignments=_root_assignments(
        _source_quark_assignments(protons=50, neutrons=70)
    ),
    source=_NIST_TIN_ATOMIC_DATA_SOURCE,
    notes=(
        "This preset says: model the source species as 120Sn for closure. It "
        "does not say ASML uses isotopically selected 120Sn.",
        "The root assignments are exact quark-count bookkeeping from Z=50 "
        "and A=120: U=2Z+N and D=Z+2N. Binding, charge state, screening, "
        "ionization, plasma temperature, and laser-drive roots remain open.",
    ),
)


euv_tin120_lpp_source_boundary_assumption = combine(
    source_tin_120_composition_assumption,
    asml_euv_tin_lpp_public_context,
    name="euv_tin120_lpp_source_boundary_assumption",
    description=(
        "Assumption-labeled EUV tin-plasma source boundary that combines a "
        "120Sn source-species closure with ASML's public 50 kHz LPP context."
    ),
)


SOURCE_PLASMA_OPERATING_PRESETS = (
    asml_euv_tin_lpp_public_context,
    source_tin_120_composition_assumption,
    euv_tin120_lpp_source_boundary_assumption,
)


__all__ = [
    "ASML_EUV_REPETITION_RATE_HZ",
    "ASML_EUV_PULSE_PERIOD_S",
    "SOURCE_PLASMA_OPERATING_PRESETS",
    "asml_euv_public_context_inventory",
    "asml_euv_tin_lpp_public_context",
    "source_tin_120_composition_assumption",
    "euv_tin120_lpp_source_boundary_assumption",
]
