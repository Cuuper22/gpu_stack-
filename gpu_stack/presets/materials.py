"""
gpu_stack.presets.materials
===========================

Composition-layer material presets.

These presets intentionally stop at exact isotope/count assignments. They do
not assign binding calibration coefficients, density, or optical-response
values. Those remain explicit scenario roots until sourced material data is
added.
"""

from ..core import Reference
from ..core.presets import Preset
from ..core.registry import Registry


_NIST_WEBBOOK_WATER = Reference(
    citation=(
        "NIST Chemistry WebBook, SRD 69, Water; formula H2O and "
        "CAS Registry Number 7732-18-5"
    ),
    kind="database",
    url="https://webbook.nist.gov/cgi/cbook.cgi?ID=C7732185",
)

_IUPAC_NUCLIDE = Reference(
    citation=(
        "IUPAC Gold Book, nuclide: atom species specified by mass number, "
        "atomic number, and nuclear energy state"
    ),
    kind="database",
    url="https://goldbook.iupac.org/terms/view/N04257",
)

_PARTICLE_DATA_GROUP_QUARK_MODEL = Reference(
    citation=(
        "Particle Data Group Review of Particle Physics, quark model "
        "baryon valence content"
    ),
    kind="database",
    url="https://pdg.lbl.gov/",
)

_ASML_EUV_TIN_LPP = Reference(
    citation=(
        "ASML Light & lasers lithography principles; EUV LPP source uses "
        "molten tin droplets vaporized into EUV-emitting plasma"
    ),
    kind="official",
    url="https://www.asml.com/en/technology/lithography-principles/light-and-lasers",
)

_CIAAW_TIN_ISOTOPIC_COMPOSITION = Reference(
    citation=(
        "CIAAW Atomic Weight of Tin; tin has atomic number 50 and "
        "tin-120 isotopic abundance 0.3258(9)"
    ),
    kind="database",
    url="https://www.ciaaw.org/tin.htm",
)

_NUCLIDE_PROVENANCE = (
    "IUPAC/CIAAW nuclide notation and standard atomic-number convention: "
    "hydrogen has Z=1 and oxygen has Z=8; isotope labels hydrogen-1 and "
    "oxygen-16 give A=1 and A=16, so N=A-Z."
)

_WATER_FORMULA_PROVENANCE = (
    "NIST Chemistry WebBook water entry and standard chemical notation: "
    "water has molecular formula H2O."
)

_VALENCE_QUARK_PROVENANCE = (
    "Valence-quark accounting from the proton uud and neutron udd quark "
    "model, encoded as U=2Z+N and D=Z+2N."
)


def _reference_summary(reference: Reference) -> str:
    parts = [reference.citation]
    if reference.url:
        parts.append(reference.url)
    if reference.doi:
        parts.append(f"doi:{reference.doi}")
    if reference.year:
        parts.append(str(reference.year))
    return " ".join(parts)


def _provenance(
    statement: str,
    *,
    references: tuple[Reference, ...],
) -> str:
    if not references:
        raise ValueError("material preset provenance requires references")
    return f"{statement} References: {'; '.join(_reference_summary(ref) for ref in references)}"


def _root_assignments(assignments: dict[str, int]) -> dict[str, int]:
    unknown = [name for name in assignments if name not in Registry.variables]
    if unknown:
        raise ValueError(
            "material preset assignments reference unknown variables: "
            f"{sorted(unknown)}"
        )
    non_roots = [
        name
        for name in assignments
        if not Registry.variables[name].is_root_input
    ]
    if non_roots:
        raise ValueError(
            "material preset assignments must be root inputs only: "
            f"{sorted(non_roots)}"
        )
    return assignments


def _source_nucleon_assignments(protons: int, neutrons: int) -> dict[str, int]:
    return {
        "physical.lithography.source_proton_count": protons,
        "physical.lithography.source_neutron_count": neutrons,
    }


def _medium_component_nucleon_assignments(
    component: str,
    protons: int,
    neutrons: int,
) -> dict[str, int]:
    return {
        f"physical.lithography.medium_component_{component}_proton_count": protons,
        f"physical.lithography.medium_component_{component}_neutron_count": neutrons,
    }


source_hydrogen_1 = Preset(
    name="source_hydrogen_1",
    description=(
        "Composition-only lithography source isotope preset for hydrogen-1 "
        "(protium): one proton and zero neutrons, encoded at the proton-count "
        "and neutron-count root layer."
    ),
    assignments=_root_assignments(
        _source_nucleon_assignments(protons=1, neutrons=0)
    ),
    source=_provenance(
        f"{_NUCLIDE_PROVENANCE} For hydrogen-1: Z=1, A=1, N=0.",
        references=(_IUPAC_NUCLIDE,),
    ),
    notes=(
        "Composition only; does not assign source binding calibration, "
        "screening, plasma, or optical drive roots.",
        "Valence quark counts U=2 and D=1 are derived from Z=1, N=0 by "
        "the scope equations.",
    ),
)


source_oxygen_16 = Preset(
    name="source_oxygen_16",
    description=(
        "Composition-only lithography source isotope preset for oxygen-16: "
        "eight protons and eight neutrons, encoded at the proton-count and "
        "neutron-count root layer."
    ),
    assignments=_root_assignments(
        _source_nucleon_assignments(protons=8, neutrons=8)
    ),
    source=_provenance(
        f"{_NUCLIDE_PROVENANCE} For oxygen-16: Z=8, A=16, N=8.",
        references=(_IUPAC_NUCLIDE,),
    ),
    notes=(
        "Composition only; does not assign source binding calibration, "
        "screening, plasma, or optical drive roots.",
        "Valence quark counts U=24 and D=24 are derived from Z=8, N=8 by "
        "the scope equations.",
    ),
)


source_tin_120 = Preset(
    name="source_tin_120",
    description=(
        "Composition-only EUV lithography source isotope preset for "
        "tin-120: fifty protons and seventy neutrons, encoded at the "
        "proton-count and neutron-count root layer."
    ),
    assignments=_root_assignments(
        _source_nucleon_assignments(protons=50, neutrons=70)
    ),
    source=_provenance(
        (
            "ASML establishes molten tin droplets as the laser-produced "
            "plasma source material for EUV lithography. CIAAW identifies "
            "tin as Z=50 and lists tin-120 as a standard isotope with "
            "abundance 0.3258(9), so for tin-120 A=120 and N=70."
        ),
        references=(
            _ASML_EUV_TIN_LPP,
            _CIAAW_TIN_ISOTOPIC_COMPOSITION,
        ),
    ),
    notes=(
        "Composition only; does not assign source binding calibration, "
        "density, screening, plasma, drive, or optical-response roots.",
        "Tin-120 is used as a sourced isotope-level stand-in for the EUV "
        "tin source context, not as a natural-abundance mixture preset.",
        "Valence quark counts U=170 and D=190 are derived from Z=50, N=70 "
        "by the scope equations.",
    ),
)


medium_h2o_h1_o16_composition = Preset(
    name="medium_h2o_h1_o16_composition",
    description=(
        "Composition-only binary imaging-medium formula unit with two "
        "hydrogen-1 component-A atoms and one oxygen-16 component-B atom."
    ),
    assignments=_root_assignments(
        {
            "physical.lithography.medium_component_a_stoichiometric_count": 2,
            **_medium_component_nucleon_assignments("a", protons=1, neutrons=0),
            "physical.lithography.medium_component_b_stoichiometric_count": 1,
            **_medium_component_nucleon_assignments("b", protons=8, neutrons=8),
        }
    ),
    source=_provenance(
        (
            f"{_WATER_FORMULA_PROVENANCE} {_NUCLIDE_PROVENANCE} "
            "Preset maps H2O to component A=hydrogen-1 (Z=1, N=0) and "
            "component B=oxygen-16 (Z=8, N=8) with stoichiometric counts 2:1."
        ),
        references=(
            _NIST_WEBBOOK_WATER,
            _IUPAC_NUCLIDE,
        ),
    ),
    notes=(
        "Composition only; does not assign liquid-drop binding calibration, "
        "formula-unit intercomponent charge-transfer count, density packing, "
        "or optical-response roots.",
        "Formula-unit proton, neutron, electron, mass, density, and optical "
        "response values remain derived resolver outputs or explicit "
        "scenario roots outside this composition preset.",
        "Valence quark counts for each component are derived from Z and N "
        "by the scope equations.",
    ),
)


__all__ = [
    "source_hydrogen_1",
    "source_oxygen_16",
    "source_tin_120",
    "medium_h2o_h1_o16_composition",
]
