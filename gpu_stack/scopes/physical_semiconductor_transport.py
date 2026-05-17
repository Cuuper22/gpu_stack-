"""
scopes/physical_semiconductor_transport.py
==========================================

Carrier transport, resistance, and lumped continuity declarations.
"""

import sympy as sp

from ..constants import BOLTZMANN, ELEMENTARY_CHARGE, ELECTRON_MASS
from ..core import Approximation, DifferentialEquation, eq, var
from ..core.units import AMPERE, KELVIN, KILOGRAM, METER, OHM, SECOND, VOLT
from .physical_local_thermal import T_temp
from .physical_process import L_channel
from .physical_semiconductor_refs import _SI_BASE_UNITS, _SZE_TRANSPORT


n_carrier = var(
    "physical.carrier_density", "n_c", "1/m^3",
    "Free charge carrier density in a conductor or inversion channel.",
    scope="physical",
    sp_units=1 / METER**3,
    references=[_SZE_TRANSPORT],
)
v_drift = var(
    "physical.drift_velocity", "v_d", "m/s",
    "Carrier drift velocity under an applied electric field.",
    scope="physical",
    sp_units=METER / SECOND,
    references=[_SZE_TRANSPORT],
)
A_cross = var(
    "physical.cross_section", "A_x", "m^2",
    "Cross-sectional area supporting current flow.",
    scope="physical",
    sp_units=METER**2,
)
mu_mob = var(
    "physical.carrier_mobility", "mu_n", "m^2/(V*s)",
    "Carrier mobility. Process, field, and temperature dependent.",
    scope="physical",
    sp_units=METER**2 / (VOLT * SECOND),
    references=[_SZE_TRANSPORT],
)
E_field = var(
    "physical.electric_field", "E_f", "V/m",
    "Electric field strength across the active region.",
    scope="physical",
    sp_units=VOLT / METER,
)
V_applied = var(
    "physical.voltage", "V", "V",
    "Applied voltage across a device or conductor segment.",
    scope="physical",
    sp_units=VOLT,
)
V_ohmic_drop = var(
    "physical.voltage_ohmic_drop", "V_ohm", "V",
    "Voltage drop implied by Ohm's law for a resistive segment.",
    scope="physical",
    sp_units=VOLT,
)
I_current = var(
    "physical.current", "I", "A",
    "Electrical current.",
    scope="physical",
    sp_units=AMPERE,
    references=[_SI_BASE_UNITS],
)
R_res = var(
    "physical.resistance", "R_res", "ohm",
    "Electrical resistance of a path segment.",
    scope="physical",
    sp_units=OHM,
)
rho_res = var(
    "physical.resistivity", "rho_res", "ohm*m",
    "Material resistivity.",
    scope="physical",
    sp_units=OHM * METER,
)
rho_ref = var(
    "physical.resistivity.reference", "rho_ref", "ohm*m",
    "Reference resistivity for the conductor material at the reference temperature and large-line limit.",
    scope="physical",
    sp_units=OHM * METER,
    references=[_SZE_TRANSPORT],
)
rho_temp_coeff = var(
    "physical.resistivity.temp_coeff", "alpha_rho", "1/K",
    "First-order temperature coefficient for resistivity.",
    scope="physical",
    sp_units=1 / KELVIN,
    references=[_SZE_TRANSPORT],
)
rho_ref_temperature = var(
    "physical.resistivity.reference_temperature", "T_rho_ref", "K",
    "Reference temperature for the tabulated conductor resistivity.",
    scope="physical",
    sp_units=KELVIN,
)
rho_size_factor = var(
    "physical.resistivity.size_factor", "chi_rho_size", "dimensionless",
    "Multiplicative resistivity inflation from line-size, grain-boundary, and surface-scattering effects.",
    scope="physical",
    sp_units=sp.Integer(1),
    references=[_SZE_TRANSPORT],
)
L_wire = var(
    "physical.wire_length", "L_w", "m",
    "Length of a conductor or interconnect segment.",
    scope="physical",
    sp_units=METER,
)
A_wire = var(
    "physical.wire_cross_section", "A_w", "m^2",
    "Effective cross-sectional area of a wire.",
    scope="physical",
    sp_units=METER**2,
)
time = var(
    "physical.time", "t", "s",
    "Independent time coordinate for lumped differential transport equations.",
    scope="physical",
    sp_units=SECOND,
)

D_diff = var(
    "physical.diffusion_coefficient", "D_diff", "m^2/s",
    "Carrier diffusion coefficient. Linked to mobility by the Einstein relation.",
    scope="physical",
    sp_units=METER**2 / SECOND,
    references=[_SZE_TRANSPORT],
)
v_sat = var(
    "physical.velocity_saturation", "v_sat", "m/s",
    "Velocity-saturation limit reached at high electric field.",
    scope="physical",
    sp_units=METER / SECOND,
)
E_crit = var(
    "physical.critical_field", "E_crit", "V/m",
    "Field scale where low-field mobility starts to break down.",
    scope="physical",
    sp_units=VOLT / METER,
)
m_eff_ratio = var(
    "physical.effective_mass_ratio", "m_eff_rel", "dimensionless",
    "Carrier effective mass as a multiple of the free-electron mass.",
    scope="physical",
    sp_units=sp.Integer(1),
)
m_eff = var(
    "physical.effective_mass", "m_eff", "kg",
    "Carrier effective mass used in transport approximations.",
    scope="physical",
    sp_units=KILOGRAM,
)
v_thermal_carrier = var(
    "physical.thermal_velocity", "v_th_car", "m/s",
    "Thermal carrier velocity from equipartition-scale reasoning.",
    scope="physical",
    sp_units=METER / SECOND,
)
G_gen = var(
    "physical.generation_rate", "G_gen", "1/(m^3*s)",
    "Carrier generation rate density.",
    scope="physical",
    sp_units=1 / (METER**3 * SECOND),
)
R_rec = var(
    "physical.recombination_rate", "R_rec", "1/(m^3*s)",
    "Carrier recombination rate density.",
    scope="physical",
    sp_units=1 / (METER**3 * SECOND),
)
dn_dt = var(
    "physical.net_carrier_rate", "dn_dt", "1/(m^3*s)",
    "Net carrier-density rate of change from generation minus recombination.",
    scope="physical",
    sp_units=1 / (METER**3 * SECOND),
)


eq_current_from_carriers = eq(
    "physical.eq.current_from_carriers",
    I_current.symbol,
    n_carrier.symbol * ELEMENTARY_CHARGE.symbol * v_drift.symbol * A_cross.symbol,
    "Current equals carrier density times carrier charge times drift velocity times area.",
    references=["Any solid-state device text, for example Sze chapter 2."],
    check_units=True,
)

eq_drift_velocity_low_field = Approximation(
    "physical.eq.drift_velocity_low_field",
    v_drift.symbol,
    mu_mob.symbol * E_field.symbol,
    sp.Abs(E_field.symbol) < E_crit.symbol,
    "Low-field drift approximation v_d ~= mu E, valid below the velocity-saturation knee.",
    references=["Sze, Physics of Semiconductor Devices."],
    check_units=True,
)

eq_drift_velocity_saturated = eq(
    "physical.eq.drift_velocity_saturated",
    v_drift.symbol,
    (mu_mob.symbol * E_field.symbol) /
    (1 + (mu_mob.symbol * E_field.symbol / v_sat.symbol)),
    "Velocity-saturation transport model that interpolates between mu E and v_sat.",
    references=["Common compact-model transport approximation for short-channel MOSFETs."],
    check_units=True,
)

eq_field_from_voltage = eq(
    "physical.eq.field_from_voltage",
    E_field.symbol,
    V_applied.symbol / L_channel.symbol,
    "Uniform-field approximation across a conduction path of length L.",
    check_units=True,
)

eq_ohms_law = eq(
    "physical.eq.ohms_law",
    V_ohmic_drop.symbol,
    I_current.symbol * R_res.symbol,
    "Ohm's law defines the resistive voltage drop V_ohm = I R. The externally applied voltage can differ when the segment sits inside a larger network.",
    check_units=True,
)

eq_resistance_geom = eq(
    "physical.eq.resistance_geometry",
    R_res.symbol,
    rho_res.symbol * L_wire.symbol / A_wire.symbol,
    "Resistance from resistivity and geometry.",
    check_units=True,
)

eq_resistivity_temperature_size = Approximation(
    "physical.eq.resistivity_temperature_size",
    rho_res.symbol,
    rho_ref.symbol
    * (1 + rho_temp_coeff.symbol * (T_temp.symbol - rho_ref_temperature.symbol))
    * rho_size_factor.symbol,
    T_temp.symbol > 0,
    "Conductor resistivity approximated from reference resistivity, first-order temperature coefficient, and size-effect inflation.",
    references=[_SZE_TRANSPORT],
    check_units=True,
)

eq_diffusion_einstein = eq(
    "physical.eq.einstein_relation",
    D_diff.symbol,
    mu_mob.symbol * BOLTZMANN.symbol * T_temp.symbol / ELEMENTARY_CHARGE.symbol,
    "Einstein relation D = mu k_B T / q.",
    references=["Semiconductor transport theory."],
    check_units=True,
)

eq_critical_field = eq(
    "physical.eq.critical_field",
    E_crit.symbol,
    v_sat.symbol / mu_mob.symbol,
    "Critical field where low-field transport crosses into velocity saturation.",
    check_units=True,
)

eq_effective_mass = eq(
    "physical.eq.effective_mass",
    m_eff.symbol,
    m_eff_ratio.symbol * ELECTRON_MASS.symbol,
    "Effective carrier mass as a material-specific multiple of the free-electron mass.",
    check_units=True,
)

eq_thermal_velocity = eq(
    "physical.eq.thermal_velocity",
    v_thermal_carrier.symbol,
    sp.sqrt(3 * BOLTZMANN.symbol * T_temp.symbol / m_eff.symbol),
    "Thermal velocity from equipartition-scale reasoning.",
)

eq_net_carrier_rate = eq(
    "physical.eq.net_carrier_rate",
    dn_dt.symbol,
    G_gen.symbol - R_rec.symbol,
    "Net carrier-density rate is generation minus recombination.",
    check_units=True,
)

eq_carrier_continuity = DifferentialEquation(
    "physical.eq.carrier_continuity",
    n_carrier.symbol,
    dn_dt.symbol,
    indep_var=time.symbol,
    order=1,
    description="Lumped continuity equation dn/dt = G - R.",
)


SEMICONDUCTOR_TRANSPORT_VARIABLES = [
    n_carrier, v_drift, A_cross, mu_mob, E_field, V_applied, V_ohmic_drop,
    I_current, R_res, rho_res, rho_ref, rho_temp_coeff, rho_ref_temperature,
    rho_size_factor, L_wire, A_wire, time,
    D_diff, v_sat, E_crit, m_eff_ratio, m_eff, v_thermal_carrier,
    G_gen, R_rec, dn_dt,
]

SEMICONDUCTOR_TRANSPORT_EQUATIONS = [
    eq_current_from_carriers,
    eq_drift_velocity_low_field,
    eq_drift_velocity_saturated,
    eq_field_from_voltage,
    eq_ohms_law,
    eq_resistance_geom,
    eq_resistivity_temperature_size,
    eq_diffusion_einstein,
    eq_critical_field,
    eq_effective_mass,
    eq_thermal_velocity,
    eq_net_carrier_rate,
    eq_carrier_continuity,
]

SEMICONDUCTOR_TRANSPORT_EXPORTS = [
    "n_carrier", "v_drift", "A_cross", "mu_mob", "E_field", "V_applied",
    "V_ohmic_drop", "I_current", "R_res", "rho_res", "rho_ref",
    "rho_temp_coeff", "rho_ref_temperature", "rho_size_factor", "L_wire",
    "A_wire", "time", "D_diff", "v_sat", "E_crit", "m_eff_ratio", "m_eff",
    "v_thermal_carrier", "G_gen", "R_rec", "dn_dt",
    "eq_current_from_carriers", "eq_drift_velocity_low_field",
    "eq_drift_velocity_saturated", "eq_field_from_voltage", "eq_ohms_law",
    "eq_resistance_geom", "eq_resistivity_temperature_size",
    "eq_diffusion_einstein", "eq_critical_field", "eq_effective_mass",
    "eq_thermal_velocity", "eq_net_carrier_rate", "eq_carrier_continuity",
]


__all__ = [
    *SEMICONDUCTOR_TRANSPORT_EXPORTS,
    "SEMICONDUCTOR_TRANSPORT_VARIABLES",
    "SEMICONDUCTOR_TRANSPORT_EQUATIONS",
]
