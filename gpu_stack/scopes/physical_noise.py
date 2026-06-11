"""
scopes/physical_noise.py
=======================

Noise floors relevant to transistor and wire behavior.

These are not decorative terms. They set sensing limits, clock-jitter floors,
and minimum reliable voltage margins.
"""

import sympy as sp

from ..core import Reference, StochasticRelation, var, eq
from ..core.units import AMPERE, FARAD, HZ, METER, SECOND, VOLT
from ..constants import BOLTZMANN, ELEMENTARY_CHARGE
from .physical_semiconductor import I_current, R_res, T_temp
from .physical_mosfet import C_ox, L_channel, W_channel


DIMENSIONLESS = sp.Integer(1)

NOISE_JOHNSON_REF = Reference(
    "Johnson, Thermal Agitation of Electricity in Conductors, Physical Review 32, 1928; "
    "Nyquist, Thermal Agitation of Electric Charge in Conductors, Physical Review 32, 1928.",
    kind="paper",
    year=1928,
)
NOISE_SHOT_REF = Reference(
    "Schottky, Spontaneous Current Fluctuations in Various Electrical Conductors, "
    "Annalen der Physik 57, 1918; shot noise model standard in electronic noise theory.",
    kind="paper",
    year=1918,
)
NOISE_FLICKER_REF = Reference(
    "Tsividis and McAndrew, Operation and Modeling of the MOS Transistor, "
    "input-referred 1/f flicker-noise PSD model for MOSFET devices.",
    kind="textbook",
)


noise_bandwidth = var(
    "physical.noise.bandwidth", "Delta_f", "Hz",
    "Measurement or receive bandwidth over which noise is integrated.",
    scope="physical",
    sp_units=HZ,
    references=[NOISE_JOHNSON_REF],
)
v_noise_mean_sq = var(
    "physical.noise.v_thermal_mean_sq", "v_n2", "V^2",
    "Thermal-noise mean-square voltage.",
    scope="physical",
    sp_units=VOLT**2,
    references=[NOISE_JOHNSON_REF],
)
i_noise_mean_sq = var(
    "physical.noise.i_shot_mean_sq", "i_n2", "A^2",
    "Shot-noise mean-square current.",
    scope="physical",
    sp_units=AMPERE**2,
    references=[NOISE_SHOT_REF],
)
f_noise = var(
    "physical.noise.frequency", "f_noise", "Hz",
    "Frequency at which flicker-noise PSD is evaluated.",
    scope="physical",
    sp_units=HZ,
    references=[NOISE_FLICKER_REF],
)
K_flicker = var(
    "physical.noise.flicker_coeff", "K_f", "mixed",
    "Empirical flicker-noise coefficient. Kept as a Variable because process reality does not care about tidy notation.",
    scope="physical",
    sp_units=VOLT**2 * FARAD * METER**2 * HZ,
    references=[NOISE_FLICKER_REF],
)
gamma_flicker = var(
    "physical.noise.flicker_exponent", "gamma_f", "dimensionless",
    "Exponent in the 1/f^gamma flicker-noise spectrum.",
    scope="physical",
    sp_units=DIMENSIONLESS,
    references=[NOISE_FLICKER_REF],
)
s_v_flicker = var(
    "physical.noise.flicker_psd", "S_v_1f", "V^2/Hz",
    "Input-referred flicker-noise power spectral density.",
    scope="physical",
    sp_units=VOLT**2 / HZ,
    references=[NOISE_FLICKER_REF],
)
v_noise_total_mean_sq = var(
    "physical.noise.v_total_mean_sq", "v_n_tot2", "V^2",
    "Approximate total mean-square voltage noise in the modeled bandwidth.",
    scope="physical",
    sp_units=VOLT**2,
    references=[NOISE_JOHNSON_REF],
)
V_noise_sample = var(
    "physical.noise.v_sample", "V_noise", "V",
    "A sample drawn from the modeled zero-mean voltage-noise distribution.",
    scope="physical",
    sp_units=VOLT,
    references=[NOISE_JOHNSON_REF],
)


eq_thermal_noise = eq(
    "physical.eq.thermal_noise_voltage",
    v_noise_mean_sq.symbol,
    4 * BOLTZMANN.symbol * T_temp.symbol * R_res.symbol * noise_bandwidth.symbol,
    "Johnson-Nyquist thermal-noise mean-square voltage integrated over bandwidth.",
    references=[NOISE_JOHNSON_REF],
    check_units=True,
)

eq_shot_noise = eq(
    "physical.eq.shot_noise_current",
    i_noise_mean_sq.symbol,
    2 * ELEMENTARY_CHARGE.symbol * I_current.symbol * noise_bandwidth.symbol,
    "Shot-noise mean-square current integrated over bandwidth.",
    references=[NOISE_SHOT_REF],
    check_units=True,
)

eq_flicker_noise = eq(
    "physical.eq.flicker_noise_psd",
    s_v_flicker.symbol,
    K_flicker.symbol /
    (C_ox.symbol * W_channel.symbol * L_channel.symbol * f_noise.symbol**gamma_flicker.symbol),
    "Simple input-referred 1/f noise PSD model. Geometry and oxide capacitance matter.",
    references=[NOISE_FLICKER_REF],
)

eq_total_noise = eq(
    "physical.eq.total_voltage_noise",
    v_noise_total_mean_sq.symbol,
    v_noise_mean_sq.symbol + s_v_flicker.symbol * noise_bandwidth.symbol,
    "Total mean-square voltage noise from thermal noise plus integrated flicker noise.",
    references=[NOISE_JOHNSON_REF],
    check_units=True,
)
noise_voltage_distribution = StochasticRelation(
    "physical.eq.noise_voltage_distribution",
    V_noise_sample.symbol,
    distribution="Normal",
    parameters={"mean": 0, "variance": v_noise_total_mean_sq.symbol},
    mean=0,
    variance=v_noise_total_mean_sq.symbol,
    description="Zero-mean Gaussian noise sample with the modeled aggregate variance.",
    references=[NOISE_JOHNSON_REF],
)


NOISE_VARIABLES = [
    noise_bandwidth, v_noise_mean_sq, i_noise_mean_sq, f_noise, K_flicker,
    gamma_flicker, s_v_flicker, v_noise_total_mean_sq, V_noise_sample,
]

NOISE_EQUATIONS = [
    eq_thermal_noise,
    eq_shot_noise,
    eq_flicker_noise,
    eq_total_noise,
    noise_voltage_distribution,
]


__all__ = [
    "noise_bandwidth", "v_noise_mean_sq", "i_noise_mean_sq", "f_noise",
    "K_flicker", "gamma_flicker", "s_v_flicker", "v_noise_total_mean_sq",
    "V_noise_sample", "eq_thermal_noise", "eq_shot_noise",
    "eq_flicker_noise", "eq_total_noise", "noise_voltage_distribution",
    "NOISE_VARIABLES", "NOISE_EQUATIONS",
]
