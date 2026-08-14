"""
constants.py
============

Universal physics constants. These are the only non-Variables in the model.
The rule for what belongs here: a Constant exists iff it is a constant in a
fundamental physical law (or a dimensioned combination of other such
constants). Anything engineering (clock speed, bit width, transistor count,
voltage, even the speed of sound in air) can change with design choices, so
it is a Variable living in some scope instead.

Values are CODATA 2018 unless noted. Those marked "exact" are exact by the
2019 SI redefinition.
"""

import sympy as sp

from .core import Constant, Reference
from .core.units import _UNITS_AVAILABLE

# Unit expressions for dimensional-consistency checking.
# sympy.physics.units is optional; fall back to None placeholders without it.
if _UNITS_AVAILABLE:
    from sympy.physics.units import (
        meter, second, kilogram, ampere, kelvin, mole, candela,
        hertz, newton, pascal, joule, watt, coulomb, volt, ohm, farad, henry,
    )
else:
    meter = second = kilogram = ampere = kelvin = mole = candela = None
    hertz = newton = pascal = joule = watt = coulomb = volt = ohm = farad = henry = None


_codata_2018 = Reference(
    citation="CODATA 2018 recommended values of the fundamental physical constants",
    kind="standard",
    url="https://physics.nist.gov/cuu/Constants/",
    year=2018,
)


# ---------------------------------------------------------------------------
# Electromagnetism
# ---------------------------------------------------------------------------

SPEED_OF_LIGHT = Constant(
    name="physics.speed_of_light",
    symbol="c",
    units="m/s",
    description="Speed of light in vacuum. Exact by SI definition.",
    value=2.99792458e8,
    source="exact by 2019 SI definition",
    sp_units=(meter / second) if _UNITS_AVAILABLE else None,
)

ELEMENTARY_CHARGE = Constant(
    name="physics.elementary_charge",
    symbol="e",
    units="C",
    description="Absolute value of the charge of a single electron or proton. Exact by SI definition.",
    value=1.602176634e-19,
    source="exact by 2019 SI definition",
    sp_units=coulomb if _UNITS_AVAILABLE else None,
)

EPSILON_0 = Constant(
    name="physics.vacuum_permittivity",
    symbol="epsilon_0",
    units="F/m",
    description="Electric constant (vacuum permittivity).",
    value=8.8541878128e-12,
    source="CODATA 2018",
    sp_units=(farad / meter) if _UNITS_AVAILABLE else None,
)

MU_0 = Constant(
    name="physics.vacuum_permeability",
    symbol="mu_0",
    units="H/m",
    description="Magnetic constant (vacuum permeability).",
    value=1.25663706212e-6,
    source="CODATA 2018",
    sp_units=(henry / meter) if _UNITS_AVAILABLE else None,
)

FINE_STRUCTURE = Constant(
    name="physics.fine_structure",
    symbol="alpha_fs",
    units="dimensionless",
    description=(
        "Fine-structure constant: alpha = e^2 / (4*pi*epsilon_0*hbar*c) "
        "~ 1/137.036. Governs strength of EM interaction; shows up in "
        "quantum transport corrections."
    ),
    value=7.2973525693e-3,
    source="CODATA 2018",
)

CONDUCTANCE_QUANTUM = Constant(
    name="physics.conductance_quantum",
    symbol="G_0",
    units="S",
    description=(
        "Conductance quantum G_0 = 2e^2/h. Conductance of a single "
        "ballistic 1D channel (one transverse mode, spin-degenerate). "
        "Relevant when transistor channel length approaches the mean free path."
    ),
    value=7.748091729e-5,
    source="CODATA 2018",
)

MAGNETIC_FLUX_QUANTUM = Constant(
    name="physics.magnetic_flux_quantum",
    symbol="Phi_0",
    units="Wb",
    description="Flux quantum Phi_0 = h/(2e). Appears in superconducting circuits (Josephson, SQUID).",
    value=2.067833848e-15,
    source="CODATA 2018",
)

VON_KLITZING = Constant(
    name="physics.von_klitzing",
    symbol="R_K",
    units="ohm",
    description="Von Klitzing constant R_K = h/e^2 ~ 25812.807 ohm. Resistance quantum.",
    value=25812.80745,
    source="CODATA 2018",
    sp_units=ohm if _UNITS_AVAILABLE else None,
)


# ---------------------------------------------------------------------------
# Thermodynamics
# ---------------------------------------------------------------------------

BOLTZMANN = Constant(
    name="physics.boltzmann",
    symbol="k_B",
    units="J/K",
    description="Boltzmann constant. Exact by SI definition.",
    value=1.380649e-23,
    source="exact by 2019 SI definition",
    sp_units=(joule / kelvin) if _UNITS_AVAILABLE else None,
)

AVOGADRO = Constant(
    name="physics.avogadro",
    symbol="N_A",
    units="1/mol",
    description="Avogadro constant. Exact by SI definition.",
    value=6.02214076e23,
    source="exact by 2019 SI definition",
    sp_units=(1 / mole) if _UNITS_AVAILABLE else None,
)

GAS_CONSTANT = Constant(
    name="physics.gas_constant",
    symbol="R_gas",
    units="J/(mol*K)",
    description="Universal gas constant R = N_A * k_B.",
    value=8.314462618,
    source="derived exact from N_A and k_B",
    sp_units=(joule / (mole * kelvin)) if _UNITS_AVAILABLE else None,
)

STEFAN_BOLTZMANN = Constant(
    name="physics.stefan_boltzmann",
    symbol="sigma_SB",
    units="W/(m^2*K^4)",
    description="Stefan-Boltzmann constant for blackbody radiation.",
    value=5.670374419e-8,
    source="CODATA 2018 (derived from k_B, hbar, c)",
    sp_units=(watt / (meter**2 * kelvin**4)) if _UNITS_AVAILABLE else None,
)


# ---------------------------------------------------------------------------
# Quantum / atomic
# ---------------------------------------------------------------------------

PLANCK = Constant(
    name="physics.planck",
    symbol="h",
    units="J*s",
    description="Planck constant. Exact by SI definition.",
    value=6.62607015e-34,
    source="exact by 2019 SI definition",
    sp_units=(joule * second) if _UNITS_AVAILABLE else None,
)

HBAR = Constant(
    name="physics.hbar",
    symbol="hbar",
    units="J*s",
    description="Reduced Planck constant h/(2*pi).",
    value=1.054571817e-34,
    source="derived exact from h",
    sp_units=(joule * second) if _UNITS_AVAILABLE else None,
)

ELECTRON_MASS = Constant(
    name="physics.electron_mass",
    symbol="m_e",
    units="kg",
    description="Rest mass of the electron.",
    value=9.1093837015e-31,
    source="CODATA 2018",
    sp_units=kilogram if _UNITS_AVAILABLE else None,
)

PROTON_MASS = Constant(
    name="physics.proton_mass",
    symbol="m_p",
    units="kg",
    description="Rest mass of the proton.",
    value=1.67262192369e-27,
    source="CODATA 2018",
    sp_units=kilogram if _UNITS_AVAILABLE else None,
)

NEUTRON_MASS = Constant(
    name="physics.neutron_mass",
    symbol="m_n",
    units="kg",
    description="Rest mass of the neutron.",
    value=1.67492749804e-27,
    source="CODATA 2018",
    sp_units=kilogram if _UNITS_AVAILABLE else None,
)

ATOMIC_MASS_UNIT = Constant(
    name="physics.amu",
    symbol="u",
    units="kg",
    description="Unified atomic mass unit (1/12 of a 12C atom at rest).",
    value=1.66053906660e-27,
    source="CODATA 2018",
    sp_units=kilogram if _UNITS_AVAILABLE else None,
)

BOHR_RADIUS = Constant(
    name="physics.bohr_radius",
    symbol="a_0",
    units="m",
    description=(
        "Bohr radius a_0 = hbar/(m_e * c * alpha). Natural length scale for "
        "atomic wavefunctions; relevant when channel length approaches "
        "atomic dimensions."
    ),
    value=5.29177210903e-11,
    source="CODATA 2018",
    sp_units=meter if _UNITS_AVAILABLE else None,
)

RYDBERG_ENERGY = Constant(
    name="physics.rydberg_energy",
    symbol="Ry",
    units="J",
    description="Rydberg energy. Natural atomic energy scale (~13.6 eV).",
    value=2.1798723611035e-18,
    source="CODATA 2018",
    sp_units=joule if _UNITS_AVAILABLE else None,
)

CLASSICAL_ELECTRON_RADIUS = Constant(
    name="physics.classical_electron_radius",
    symbol="r_e",
    units="m",
    description="Classical electron radius r_e = e^2 / (4*pi*epsilon_0*m_e*c^2).",
    value=2.8179403262e-15,
    source="CODATA 2018",
    sp_units=meter if _UNITS_AVAILABLE else None,
)


# ---------------------------------------------------------------------------
# Mechanical / environmental reference (used in data-center engineering)
# ---------------------------------------------------------------------------

STANDARD_GRAVITY = Constant(
    name="physics.standard_gravity",
    symbol="g_n",
    units="m/s^2",
    description=(
        "Standard acceleration due to gravity at Earth's surface. "
        "Convention (local g varies ~0.5% over latitude). "
        "Used in cooling system design (pump head, fluid potential energy)."
    ),
    value=9.80665,
    source="CGPM 1901 definition",
    sp_units=(meter / second**2) if _UNITS_AVAILABLE else None,
)

STANDARD_ATMOSPHERE = Constant(
    name="physics.standard_atmosphere",
    symbol="atm",
    units="Pa",
    description=(
        "Standard atmospheric pressure. Convention. "
        "Relevant in data-center HVAC (pressure drop across filters, fans)."
    ),
    value=101325.0,
    source="CGPM 1954 definition",
    sp_units=pascal if _UNITS_AVAILABLE else None,
)

ICE_POINT = Constant(
    name="physics.ice_point",
    symbol="T_0",
    units="K",
    description=(
        "Ice-point temperature (273.15 K = 0 degC). Useful for converting "
        "between Celsius and Kelvin in engineering inputs."
    ),
    value=273.15,
    source="SI convention",
    sp_units=kelvin if _UNITS_AVAILABLE else None,
)


# ---------------------------------------------------------------------------
# Mathematical helpers frequently appearing in equations
# ---------------------------------------------------------------------------
# These are not Constants in the gpu_stack sense; they carry no units or
# provenance. They are plain sympy expressions for equations that need them
# (propagation delay uses ln 2, subthreshold slope uses ln 10).

LN_2 = sp.log(2)
LN_10 = sp.log(10)
PI = sp.pi
E_MATH = sp.E
TWO_PI = 2 * sp.pi


__all__ = [
    # electromagnetism
    "SPEED_OF_LIGHT", "ELEMENTARY_CHARGE", "EPSILON_0", "MU_0",
    "FINE_STRUCTURE", "CONDUCTANCE_QUANTUM", "MAGNETIC_FLUX_QUANTUM",
    "VON_KLITZING",
    # thermodynamics
    "BOLTZMANN", "AVOGADRO", "GAS_CONSTANT", "STEFAN_BOLTZMANN",
    # quantum / atomic
    "PLANCK", "HBAR", "ELECTRON_MASS", "PROTON_MASS", "NEUTRON_MASS",
    "ATOMIC_MASS_UNIT", "BOHR_RADIUS", "RYDBERG_ENERGY",
    "CLASSICAL_ELECTRON_RADIUS",
    # mechanical / environmental
    "STANDARD_GRAVITY", "STANDARD_ATMOSPHERE", "ICE_POINT",
    # math helpers
    "LN_2", "LN_10", "PI", "E_MATH", "TWO_PI",
]
