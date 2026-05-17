"""
GPU-level capex, residual value, amortization, and rental markup.
"""

from ..core import eq, var
from ..core.units import SECOND

from .economics_capex_refs import CAPEX_BOM_REF, DIMENSIONLESS, USD


gpu_capex = var(
    "econ.gpu.capex", "C_cap_GPU", "USD",
    "Purchase price of one GPU.",
    scope="economics",
    sp_units=USD,
    references=[CAPEX_BOM_REF],
)
useful_life = var(
    "econ.asset.useful_life", "T_life", "s",
    "Depreciation horizon in seconds.",
    scope="economics",
    sp_units=SECOND,
    references=[CAPEX_BOM_REF],
)
residual_value_fraction = var(
    "econ.asset.residual_fraction", "f_resid", "dimensionless",
    "Residual-value fraction remaining at the end of the depreciation horizon.",
    scope="economics",
    sp_units=DIMENSIONLESS,
    references=[CAPEX_BOM_REF],
)
gpu_residual_value = var(
    "econ.gpu.residual_value", "C_resid_GPU", "USD",
    "Residual value of one GPU at end of life.",
    scope="economics",
    sp_units=USD,
    references=[CAPEX_BOM_REF],
)
gpu_hourly_amortized = var(
    "econ.gpu.hourly_amortized", "C_amort", "USD/s",
    "Straight-line amortized GPU cost per second after residual value is removed.",
    scope="economics",
    sp_units=USD / SECOND,
    references=[CAPEX_BOM_REF],
)
gpu_hourly_rent = var(
    "econ.gpu.hourly_rent", "C_rent", "USD/s",
    "Market rental price of one GPU per second.",
    scope="economics",
    sp_units=USD / SECOND,
    references=[CAPEX_BOM_REF],
)
gpu_rental_markup = var(
    "econ.gpu.rental_markup", "k_rent", "dimensionless",
    "Rental markup relative to straight-line amortized GPU cost.",
    scope="economics",
    sp_units=DIMENSIONLESS,
    references=[CAPEX_BOM_REF],
)


eq_gpu_residual_value = eq(
    "econ.eq.gpu_residual_value",
    gpu_residual_value.symbol,
    residual_value_fraction.symbol * gpu_capex.symbol,
    "GPU residual value equals residual fraction times GPU purchase cost.",
    references=[CAPEX_BOM_REF],
    check_units=True,
)

eq_amortized = eq(
    "econ.eq.amortized",
    gpu_hourly_amortized.symbol,
    (gpu_capex.symbol - gpu_residual_value.symbol) / useful_life.symbol,
    "GPU straight-line amortization equals depreciable GPU capex divided by useful life.",
    references=[CAPEX_BOM_REF],
    check_units=True,
)

eq_gpu_rental_markup = eq(
    "econ.eq.gpu_rental_markup",
    gpu_rental_markup.symbol,
    gpu_hourly_rent.symbol / gpu_hourly_amortized.symbol,
    "Rental markup is market rental price divided by straight-line amortized GPU cost.",
    references=[CAPEX_BOM_REF],
    check_units=True,
)


__all__ = [
    "eq_amortized",
    "eq_gpu_rental_markup",
    "eq_gpu_residual_value",
    "gpu_capex",
    "gpu_hourly_amortized",
    "gpu_hourly_rent",
    "gpu_rental_markup",
    "gpu_residual_value",
    "residual_value_fraction",
    "useful_life",
]
