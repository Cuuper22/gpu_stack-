"""
scopes/physical_semiconductor.py
================================

Compatibility surface for semiconductor carrier transport: how charge
actually moves, what resistance that motion implies, and the
speed-of-signal floor no wire can beat. Declarations live in focused helper
modules (transport, signal, references); this module re-exports them so
the original import surface stays stable for downstream consumers.
"""

import sympy as sp

from ..constants import BOLTZMANN, ELEMENTARY_CHARGE, ELECTRON_MASS, SPEED_OF_LIGHT
from ..core import Approximation, DifferentialEquation, Reference, var, eq
from ..core.units import AMPERE, COULOMB, KELVIN, KILOGRAM, METER, OHM, SECOND, VOLT
from .physical_process import (
    L_channel,
    contacted_gate_pitch,
    drawn_gate_length,
    eq_channel_length_process,
    eq_contacted_gate_pitch,
    eq_minimum_metal_pitch,
    eq_process_node_from_pitches,
    gate_contact_spacing,
    gate_length_bias,
    gate_length_scale,
    minimum_metal_pitch,
    minimum_metal_spacing,
    minimum_metal_width,
    node_geometry_factor,
    process_node_length,
    source_drain_contact_width,
)
from .physical_local_thermal import (
    T_local_ambient,
    T_self_heating_rise,
    T_temp,
    eq_heat_flux_from_power_area,
    eq_heat_source_area,
    eq_temperature_local,
    eq_temperature_self_heating,
    eq_thermal_resistance_area_from_conduction,
    heat_flux,
    heat_source_area,
    heat_source_cell_area_scale,
    heat_source_cell_count,
    heat_source_power,
    thermal_boundary_thickness,
    thermal_conductivity,
    thermal_resistance_area,
    thermal_spreading_factor,
)
from .physical_semiconductor_refs import _SI_BASE_UNITS, _SZE_TRANSPORT
from .physical_semiconductor_transport import (
    A_cross,
    A_wire,
    D_diff,
    E_crit,
    E_field,
    G_gen,
    I_current,
    L_wire,
    R_rec,
    R_res,
    SEMICONDUCTOR_TRANSPORT_EQUATIONS as _SEMICONDUCTOR_TRANSPORT_EQUATIONS,
    SEMICONDUCTOR_TRANSPORT_VARIABLES as _SEMICONDUCTOR_TRANSPORT_VARIABLES,
    V_applied,
    V_ohmic_drop,
    dn_dt,
    eq_carrier_continuity,
    eq_critical_field,
    eq_current_from_carriers,
    eq_diffusion_einstein,
    eq_drift_velocity_low_field,
    eq_drift_velocity_saturated,
    eq_effective_mass,
    eq_field_from_voltage,
    eq_net_carrier_rate,
    eq_ohms_law,
    eq_resistance_geom,
    eq_resistivity_temperature_size,
    eq_thermal_velocity,
    m_eff,
    m_eff_ratio,
    mu_mob,
    n_carrier,
    rho_ref,
    rho_ref_temperature,
    rho_res,
    rho_size_factor,
    rho_temp_coeff,
    time,
    v_drift,
    v_sat,
    v_thermal_carrier,
)
from .physical_semiconductor_signal import (
    SEMICONDUCTOR_SIGNAL_EQUATIONS as _SEMICONDUCTOR_SIGNAL_EQUATIONS,
    SEMICONDUCTOR_SIGNAL_VARIABLES as _SEMICONDUCTOR_SIGNAL_VARIABLES,
    d_link,
    eq_signal_speed,
    eq_time_of_flight,
    n_medium,
    t_flight,
    v_signal,
)


SEMICONDUCTOR_VARIABLES = [
    *_SEMICONDUCTOR_TRANSPORT_VARIABLES,
    *_SEMICONDUCTOR_SIGNAL_VARIABLES,
]

SEMICONDUCTOR_EQUATIONS = [
    *_SEMICONDUCTOR_TRANSPORT_EQUATIONS,
    *_SEMICONDUCTOR_SIGNAL_EQUATIONS,
]


__all__ = [
    "n_carrier", "v_drift", "A_cross", "mu_mob", "E_field", "V_applied",
    "V_ohmic_drop", "L_channel", "I_current", "R_res", "rho_res",
    "rho_ref", "rho_temp_coeff", "rho_ref_temperature", "rho_size_factor",
    "L_wire", "A_wire",
    "drawn_gate_length", "source_drain_contact_width", "gate_contact_spacing",
    "contacted_gate_pitch", "minimum_metal_width", "minimum_metal_spacing",
    "minimum_metal_pitch", "node_geometry_factor",
    "process_node_length", "gate_length_scale", "gate_length_bias",
    "T_local_ambient", "heat_source_power", "heat_source_cell_count",
    "heat_source_cell_area_scale", "heat_source_area", "thermal_boundary_thickness",
    "thermal_conductivity", "thermal_spreading_factor", "heat_flux", "thermal_resistance_area",
    "T_self_heating_rise", "T_temp", "time", "D_diff", "v_sat", "E_crit", "m_eff_ratio", "m_eff",
    "v_thermal_carrier", "G_gen", "R_rec", "dn_dt", "d_link",
    "n_medium", "v_signal", "t_flight",
    "eq_current_from_carriers", "eq_drift_velocity_low_field",
    "eq_drift_velocity_saturated", "eq_field_from_voltage",
    "eq_contacted_gate_pitch", "eq_minimum_metal_pitch",
    "eq_process_node_from_pitches", "eq_channel_length_process", "eq_ohms_law",
    "eq_resistance_geom", "eq_resistivity_temperature_size",
    "eq_heat_source_area", "eq_heat_flux_from_power_area",
    "eq_thermal_resistance_area_from_conduction",
    "eq_temperature_self_heating", "eq_temperature_local",
    "eq_diffusion_einstein", "eq_critical_field",
    "eq_effective_mass", "eq_thermal_velocity", "eq_net_carrier_rate",
    "eq_carrier_continuity", "eq_signal_speed", "eq_time_of_flight",
    "SEMICONDUCTOR_VARIABLES", "SEMICONDUCTOR_EQUATIONS",
]
