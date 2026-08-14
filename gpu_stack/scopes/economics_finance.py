"""
scopes/economics_finance.py
===========================

How fixed costs and the time value of money reach one training job.

Two financial facts connect a cluster's books to a single run. First,
allocation: a site is never 100% busy, so its fixed costs must be spread
over only the productive fraction — the allocation factor is the job's
share of the cluster divided by site utilization, and multiplying it into
the cluster capex rate gives the job's capex rate. Idle time makes every
productive hour dearer.

Second, discounting: money spent during a months-long run is worth more
than the same amount later, so an annual WACC (weighted average cost of
capital, the firm's hurdle rate) becomes a discount factor over the run's
wall-clock duration. This helper declares the NPV container; the NPV
equation itself lives in the recovery helper, where the run cost is
assembled.
"""

import sympy as sp
from ..core import Reference, eq, var
from ..core.units import SECOND

from .training import T_wallclock
from .economics_capex import USD, cluster_capex_rate, job_share_of_cluster


DIMENSIONLESS = sp.Integer(1)
USD_RATE = USD / SECOND

FINANCE_ALLOCATION_REF = Reference(
    "Economics finance allocation spreads fixed site costs by job share and "
    "productive site utilization before assigning the job capex rate.",
    kind="model",
)

FINANCE_DISCOUNT_REF = Reference(
    "Run-level finance applies an annual hurdle-rate convention as a "
    "present-value discount factor over the training duration.",
    kind="model",
)


# ---------------------------------------------------------------------------
# Allocation
# ---------------------------------------------------------------------------

cluster_utilization = var(
    "econ.cluster.utilization", "u_site", "dimensionless",
    "Fraction of time the site is productively used by billable jobs.",
    scope="economics",
    sp_units=DIMENSIONLESS,
    references=[FINANCE_ALLOCATION_REF],
)
allocated_fixed_cost_factor = var(
    "econ.job.allocated_fixed_cost_factor", "k_alloc", "dimensionless",
    "Fixed-cost allocation factor after accounting for both job share and cluster utilization.",
    scope="economics",
    sp_units=DIMENSIONLESS,
    references=[FINANCE_ALLOCATION_REF],
)
job_capex_rate = var(
    "econ.job.capex_rate", "Cdot_job_cap", "USD/s",
    "Allocated site capex charge rate attributed to the training job.",
    scope="economics",
    sp_units=USD_RATE,
    references=[FINANCE_ALLOCATION_REF],
)


eq_allocated_fixed_cost_factor = eq(
    "econ.eq.allocated_fixed_cost_factor",
    allocated_fixed_cost_factor.symbol,
    job_share_of_cluster.symbol / cluster_utilization.symbol,
    "Fixed-cost allocation factor equals job share divided by site utilization.",
    references=[FINANCE_ALLOCATION_REF],
    check_units=True,
)

eq_job_capex_rate = eq(
    "econ.eq.job_capex_rate",
    job_capex_rate.symbol,
    cluster_capex_rate.symbol * allocated_fixed_cost_factor.symbol,
    "Allocated job capex rate equals site capex rate scaled by fixed-cost allocation factor.",
    references=[FINANCE_ALLOCATION_REF],
    check_units=True,
)


# ---------------------------------------------------------------------------
# Cost of capital
# ---------------------------------------------------------------------------

wacc_annual = var(
    "econ.finance.wacc_annual", "r_wacc", "1/year",
    "Annual weighted average cost of capital or internal hurdle rate.",
    scope="economics",
    sp_units=DIMENSIONLESS,
    references=[FINANCE_DISCOUNT_REF],
)
discount_factor_run = var(
    "econ.finance.discount_factor_run", "D_run", "dimensionless",
    "Present-value discount factor applied across the run duration.",
    scope="economics",
    sp_units=DIMENSIONLESS,
    references=[FINANCE_DISCOUNT_REF],
)
npv_run_cost = var(
    "econ.finance.npv_run_cost", "NPV_run", "USD",
    "Present-value cost of the training run.",
    scope="economics",
    sp_units=USD,
    references=[FINANCE_DISCOUNT_REF],
)


eq_discount_factor_run = eq(
    "econ.eq.discount_factor_run",
    discount_factor_run.symbol,
    (1 + wacc_annual.symbol) ** (-T_wallclock.symbol / sp.Integer(31_536_000)),
    "Run discount factor applies annual WACC across wall-clock duration using a 365-day year.",
    references=[FINANCE_DISCOUNT_REF],
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
