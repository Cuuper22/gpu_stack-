"""
tests/test_economics_units.py
=============================

Focused economics metadata and unit-check coverage.
"""

from gpu_stack.scopes import economics as econ
from gpu_stack.scopes.economics_capex import USD
from gpu_stack.scopes.economics_opex import ENERGY_PRICE, USD_RATE
from gpu_stack.core.units import KILOGRAM, SECOND, WATT, byte


OPEX_CHECKED_EQUATIONS = {
    "econ.eq.job_dc_power",
    "econ.eq.price_kwh",
    "econ.eq.ws_from_kwh",
    "econ.eq.peak_demand_kw",
    "econ.eq.capacity_charge_rate",
    "econ.eq.maintenance_cost_rate",
    "econ.eq.network_transit_cost_rate",
    "econ.eq.carbon_emission_rate",
    "econ.eq.carbon_cost_rate",
    "econ.eq.run_power_cost",
    "econ.eq.water_cost_rate",
}

FINANCE_CHECKED_EQUATIONS = {
    "econ.eq.allocated_fixed_cost_factor",
    "econ.eq.job_capex_rate",
}


def test_opex_variables_and_equations_have_metadata():
    assert all(v.sp_units is not None for v in econ.ECON_OPEX_VARIABLES)
    assert all(v.references for v in econ.ECON_OPEX_VARIABLES)
    assert all(eq.references for eq in econ.ECON_OPEX_EQUATIONS)


def test_opex_unit_checked_relations_are_explicitly_curated():
    checked = {
        eq.name
        for eq in econ.ECON_OPEX_EQUATIONS
        if getattr(eq, "_check_units_flag", False)
    }
    assert checked == OPEX_CHECKED_EQUATIONS


def test_opex_units_cover_power_network_water_and_carbon_paths():
    assert econ.job_dc_power.sp_units == WATT
    assert econ.price_kwh.sp_units == ENERGY_PRICE
    assert econ.cost_per_watt_sec.sp_units == ENERGY_PRICE
    assert econ.capacity_charge_rate.sp_units == USD_RATE
    assert econ.water_cost_rate.sp_units == USD_RATE
    assert econ.network_transit_price_per_gb.sp_units == USD / byte
    assert econ.network_egress_bytes_per_s.sp_units == byte / SECOND
    assert econ.carbon_intensity_kg_per_kwh.sp_units == KILOGRAM / (WATT * SECOND)
    assert econ.carbon_emission_rate.sp_units == KILOGRAM / SECOND
    assert econ.carbon_price_per_tonne.sp_units == USD / KILOGRAM


def test_finance_variables_and_equations_have_metadata():
    assert all(v.sp_units is not None for v in econ.ECON_FINANCE_VARIABLES)
    assert all(v.references for v in econ.ECON_FINANCE_VARIABLES)
    assert all(eq.references for eq in econ.ECON_FINANCE_EQUATIONS)


def test_finance_unit_checked_relations_are_explicitly_curated():
    checked = {
        eq.name
        for eq in econ.ECON_FINANCE_EQUATIONS
        if getattr(eq, "_check_units_flag", False)
    }
    assert checked == FINANCE_CHECKED_EQUATIONS


def test_finance_units_cover_allocation_discount_and_capex_rate_paths():
    assert econ.cluster_utilization.sp_units == 1
    assert econ.allocated_fixed_cost_factor.sp_units == 1
    assert econ.job_capex_rate.sp_units == USD / SECOND
    assert econ.wacc_annual.sp_units == 1
    assert econ.discount_factor_run.sp_units == 1
    assert econ.npv_run_cost.sp_units == USD
