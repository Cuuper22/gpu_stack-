"""
scopes/physical_noise.py
=======================

Noise floors relevant to transistor and wire behavior.

These are not decorative terms. They set sensing limits, clock-jitter floors,
and minimum reliable voltage margins.
"""

from ..core import StochasticRelation, var, eq
from ..constants import BOLTZMANN, ELEMENTARY_CHARGE
from .physical_semiconductor import I_current, R_res, T_temp
from .physical_mosfet import C_ox, L_channel, W_channel


noise_bandwidth = var(
    "physical.noise.bandwidth", "Delta_f", "Hz",
    "Measurement or receive bandwidth over which noise is integrated.",
    scope="physical",
)
v_noise_mean_sq = var(
    "physical.noise.v_thermal_mean_sq", "v_n2", "V^2",
    "Thermal-noise mean-square voltage.",
    scope="physical",
)
i_noise_mean_sq = var(
    "physical.noise.i_shot_mean_sq", "i_n2", "A^2",
    "Shot-noise mean-square current.",
    scope="physical",
)
f_noise = var(
    "physical.noise.frequency", "f_noise", "Hz",
    "Frequency at which flicker-noise PSD is evaluated.",
    scope="physical",
)
K_flicker = var(
    "physical.noise.flicker_coeff", "K_f", "mixed",
    "Empirical flicker-noise coefficient. Kept as a Variable because process reality does not care about tidy notation.",
    scope="physical",
)
gamma_flicker = var(
    "physical.noise.flicker_exponent", "gamma_f", "dimensionless",
    "Exponent in the 1/f^gamma flicker-noise spectrum.",
    scope="physical",
)
s_v_flicker = var(
    "physical.noise.flicker_psd", "S_v_1f", "V^2/Hz",
    "Input-referred flicker-noise power spectral density.",
    scope="physical",
)
v_noise_total_mean_sq = var(
    "physical.noise.v_total_mean_sq", "v_n_tot2", "V^2",
    "Approximate total mean-square voltage noise in the modeled bandwidth.",
    scope="physical",
)
V_noise_sample = var(
    "physical.noise.v_sample", "V_noise", "V",
    "A sample drawn from the modeled zero-mean voltage-noise distribution.",
    scope="physical",
)


eq_thermal_noise = eq(
    "physical.eq.thermal_noise_voltage",
    v_noise_mean_sq.symbol,
    4 * BOLTZMANN.symbol * T_temp.symbol * R_res.symbol * noise_bandwidth.symbol,
    "Johnson-Nyquist thermal-noise mean-square voltage integrated over bandwidth.",
)

eq_shot_noise = eq(
    "physical.eq.shot_noise_current",
    i_noise_mean_sq.symbol,
    2 * ELEMENTARY_CHARGE.symbol * I_current.symbol * noise_bandwidth.symbol,
    "Shot-noise mean-square current integrated over bandwidth.",
)

eq_flicker_noise = eq(
    "physical.eq.flicker_noise_psd",
    s_v_flicker.symbol,
    K_flicker.symbol /
    (C_ox.symbol * W_channel.symbol * L_channel.symbol * f_noise.symbol**gamma_flicker.symbol),
    "Simple input-referred 1/f noise PSD model. Geometry and oxide capacitance matter.",
)

eq_total_noise = eq(
    "physical.eq.total_voltage_noise",
    v_noise_total_mean_sq.symbol,
    v_noise_mean_sq.symbol + s_v_flicker.symbol * noise_bandwidth.symbol,
    "Total mean-square voltage noise from thermal noise plus integrated flicker noise.",
)
noise_voltage_distribution = StochasticRelation(
    "physical.eq.noise_voltage_distribution",
    V_noise_sample.symbol,
    distribution="Normal",
    parameters={"mean": 0, "variance": v_noise_total_mean_sq.symbol},
    mean=0,
    variance=v_noise_total_mean_sq.symbol,
    description="Zero-mean Gaussian noise sample with the modeled aggregate variance.",
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
