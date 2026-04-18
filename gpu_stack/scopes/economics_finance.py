"""
scopes/economics_finance.py
===========================

Financing and allocation primitives for the economics scope.

This helper holds site utilization, the fixed-cost allocation factor, the
allocated job capex rate, the annual WACC, the run discount factor, and the
NPV container. The NPV equation itself lives in the recovery helper where the
run cost is assembled.
"""

import sympy as sp
from ..core import eq, var

from .training import T_wallclock
from .economics_capex import cluster_capex_rate, job_share_of_cluster


# ---------------------------------------------------------------------------
# Allocation
# ---------------------------------------------------------------------------

cluster_utilization = var(
    "econ.cluster.utilization", "u_site", "dimensionless",
    "Fraction of time the site is productively used by billable jobs.",
    scope="economics",
)
allocated_fixed_cost_factor = var(
    "econ.job.allocated_fixed_cost_factor", "k_alloc", "dimensionless",
    "Fixed-cost allocation factor after accounting for both job share and cluster utilization.",
    scope="economics",
)
job_capex_rate = var(
    "econ.job.capex_rate", "Cdot_job_cap", "USD/s",
    "Allocated site capex charge rate attributed to the training job.",
    scope="economics",
)


eq_allocated_fixed_cost_factor = eq(
    "econ.eq.allocated_fixed_cost_factor",
    allocated_fixed_cost_factor.symbol,
    job_share_of_cluster.symbol / cluster_utilization.symbol,
    "Fixed-cost allocation factor equals job share divided by site utilization.",
)

eq_job_capex_rate = eq(
    "econ.eq.job_capex_rate",
    job_capex_rate.symbol,
    cluster_capex_rate.symbol * allocated_fixed_cost_factor.symbol,
    "Allocated job capex rate equals site capex rate scaled by fixed-cost allocation factor.",
)


# ---------------------------------------------------------------------------
# Cost of capital
# ---------------------------------------------------------------------------

wacc_annual = var(
    "econ.finance.wacc_annual", "r_wacc", "1/year",
    "Annual weighted average cost of capital or internal hurdle rate.",
    scope="economics",
)
discount_factor_run = var(
    "econ.finance.discount_factor_run", "D_run", "dimensionless",
    "Present-value discount factor applied across the run duration.",
    scope="economics",
)
npv_run_cost = var(
    "econ.finance.npv_run_cost", "NPV_run", "USD",
    "Present-value cost of the training run.",
    scope="economics",
)


eq_discount_factor_run = eq(
    "econ.eq.discount_factor_run",
    discount_factor_run.symbol,
    (1 + wacc_annual.symbol) ** (-T_wallclock.symbol / sp.Integer(31_536_000)),
    "Run discount factor applies annual WACC across wall-clock duration using a 365-day year.",
)


ECON_FINANCE_VARIABLES = [
    cluster_utilization,
    allocated_fixed_cost_factor,
    job_capex_rate,
    wacc_annual,
    discount_factor_run,
    npv_run_cost,
]

ECON_FINANCE_EQUATIONS = [
    eq_allocated_fixed_cost_factor,
    eq_job_capex_rate,
    eq_discount_factor_run,
]


__all__ = [
    "cluster_utilization", "allocated_fixed_cost_factor", "job_capex_rate",
    "wacc_annual", "discount_factor_run", "npv_run_cost",
    "eq_allocated_fixed_cost_factor", "eq_job_capex_rate",
    "eq_discount_factor_run",
    "ECON_FINANCE_VARIABLES", "ECON_FINANCE_EQUATIONS",
]
