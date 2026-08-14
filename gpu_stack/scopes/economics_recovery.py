"""
scopes/economics_recovery.py
============================

The bottom line: total run cost, unit costs, and the payback target.

This helper is where the economics scope converges. Each cost stream —
allocated capex, electricity, water, maintenance, staff, network transit,
demand charges, carbon — becomes a run-level amount by multiplying its rate
by the run's wall-clock time, and the amounts sum to the total run cost.
Dividing that total by steps, tokens, or achieved FLOPs from the training
scope gives the unit costs people quote, and applying the finance helper's
discount factor gives the run's net present value.

The recovery target closes the loop on the business: take revenue per
served inference token, subtract serving cost to get net margin per token,
and divide the run cost by that margin. The result is how many inference
tokens the finished model must serve before the training run has paid for
itself.
"""

import sympy as sp

from ..core import Reference, eq, var
from ..core.units import FLOP, SECOND

from .economics_capex_refs import USD
from .training import N_train_tokens, T_wallclock, achieved_flops_run, n_steps
from .economics_opex import (
    capacity_charge_rate,
    carbon_cost_rate,
    maintenance_cost_rate,
    network_transit_cost_rate,
    run_power_cost,
    staff_cost_rate,
    water_cost_rate,
)
from .economics_finance import (
    allocated_fixed_cost_factor,
    discount_factor_run,
    job_capex_rate,
    npv_run_cost,
)


DIMENSIONLESS = sp.Integer(1)

RUN_ROLLUP_REF = Reference(
    "Run-level cost rollup sums allocated capex, electricity, and operating "
    "sub-costs and divides by steps, tokens, or FLOPs to yield unit costs.",
    kind="model",
)

INFERENCE_RECOVERY_REF = Reference(
    "Inference token recovery target divides total training-run cost by the "
    "net margin available per served inference token.",
    kind="model",
)


# ---------------------------------------------------------------------------
# Run cost, step cost, and delivered-work cost
# ---------------------------------------------------------------------------

cost_per_step = var(
    "econ.cost.per_step", "C_step", "USD",
    "Average fully allocated cost per optimizer step over the whole run.",
    scope="economics",
    sp_units=USD,
    references=[RUN_ROLLUP_REF],
)
cost_per_token = var(
    "econ.cost.per_token", "C_tok", "USD/token",
    "Average fully allocated cost per training token.",
    scope="economics",
    sp_units=USD,
    references=[RUN_ROLLUP_REF],
)
cost_per_flop = var(
    "econ.cost.per_flop", "C_FLOP", "USD/FLOP",
    "Average fully allocated cost per delivered FLOP.",
    scope="economics",
    sp_units=USD / FLOP,
    references=[RUN_ROLLUP_REF],
)
run_hw_cost = var(
    "econ.run.hw_cost", "C_hw_run", "USD",
    "Allocated capex charge of the training run.",
    scope="economics",
    sp_units=USD,
    references=[RUN_ROLLUP_REF],
)
run_water_cost = var(
    "econ.run.water_cost", "C_water_run", "USD",
    "Water cost of the training run.",
    scope="economics",
    sp_units=USD,
    references=[RUN_ROLLUP_REF],
)
run_maintenance_cost = var(
    "econ.run.maintenance_cost", "C_maint_run", "USD",
    "Allocated maintenance cost of the training run.",
    scope="economics",
    sp_units=USD,
    references=[RUN_ROLLUP_REF],
)
run_staff_cost = var(
    "econ.run.staff_cost", "C_staff_run", "USD",
    "Allocated operations-staff cost of the training run.",
    scope="economics",
    sp_units=USD,
    references=[RUN_ROLLUP_REF],
)
run_network_cost = var(
    "econ.run.network_cost", "C_net_run", "USD",
    "Network-transit cost of the training run.",
    scope="economics",
    sp_units=USD,
    references=[RUN_ROLLUP_REF],
)
run_capacity_charge_cost = var(
    "econ.run.capacity_charge_cost", "C_capchg_run", "USD",
    "Demand-charge cost of the training run.",
    scope="economics",
    sp_units=USD,
    references=[RUN_ROLLUP_REF],
)
run_carbon_cost = var(
    "econ.run.carbon_cost", "C_CO2_run", "USD",
    "Carbon cost of the training run.",
    scope="economics",
    sp_units=USD,
    references=[RUN_ROLLUP_REF],
)
run_opex_misc_cost = var(
    "econ.run.opex_misc_cost", "C_opex_run", "USD",
    "Non-energy opex of the training run.",
    scope="economics",
    sp_units=USD,
    references=[RUN_ROLLUP_REF],
)
run_cost = var(
    "econ.run.total_cost", "C_run", "USD",
    "Total fully allocated training-run cost.",
    scope="economics",
    sp_units=USD,
    references=[RUN_ROLLUP_REF],
)


eq_run_hw_cost = eq(
    "econ.eq.run_hw_cost",
    run_hw_cost.symbol,
    job_capex_rate.symbol * T_wallclock.symbol,
    "Run capex charge equals allocated job capex rate times wall-clock duration.",
    references=[RUN_ROLLUP_REF],
    check_units=True,
)

eq_run_water_cost = eq(
    "econ.eq.run_water_cost",
    run_water_cost.symbol,
    water_cost_rate.symbol * T_wallclock.symbol,
    "Run water cost equals water cost rate times wall-clock duration.",
    references=[RUN_ROLLUP_REF],
    check_units=True,
)

eq_run_maintenance_cost = eq(
    "econ.eq.run_maintenance_cost",
    run_maintenance_cost.symbol,
    maintenance_cost_rate.symbol * allocated_fixed_cost_factor.symbol * T_wallclock.symbol,
    "Run maintenance cost equals site maintenance rate times fixed-cost allocation factor times wall-clock duration.",
    references=[RUN_ROLLUP_REF],
    check_units=True,
)

eq_run_staff_cost = eq(
    "econ.eq.run_staff_cost",
    run_staff_cost.symbol,
    staff_cost_rate.symbol * allocated_fixed_cost_factor.symbol * T_wallclock.symbol,
    "Run staff cost equals site operations-staff rate times fixed-cost allocation factor times wall-clock duration.",
    references=[RUN_ROLLUP_REF],
    check_units=True,
)

eq_run_network_cost = eq(
    "econ.eq.run_network_cost",
    run_network_cost.symbol,
    network_transit_cost_rate.symbol * T_wallclock.symbol,
    "Run network-transit cost equals network-transit cost rate times wall-clock duration.",
    references=[RUN_ROLLUP_REF],
    check_units=True,
)

eq_run_capacity_charge_cost = eq(
    "econ.eq.run_capacity_charge_cost",
    run_capacity_charge_cost.symbol,
    capacity_charge_rate.symbol * T_wallclock.symbol,
    "Run demand-charge cost equals capacity-charge rate times wall-clock duration.",
    references=[RUN_ROLLUP_REF],
    check_units=True,
)

eq_run_carbon_cost = eq(
    "econ.eq.run_carbon_cost",
    run_carbon_cost.symbol,
    carbon_cost_rate.symbol * T_wallclock.symbol,
    "Run carbon cost equals carbon cost rate times wall-clock duration.",
    references=[RUN_ROLLUP_REF],
    check_units=True,
)

eq_run_opex_misc_cost = eq(
    "econ.eq.run_opex_misc_cost",
    run_opex_misc_cost.symbol,
    run_water_cost.symbol + run_maintenance_cost.symbol + run_staff_cost.symbol + run_network_cost.symbol + run_capacity_charge_cost.symbol + run_carbon_cost.symbol,
    "Miscellaneous run opex sums water, maintenance, staff, network transit, demand charges, and carbon costs.",
    references=[RUN_ROLLUP_REF],
    check_units=True,
)

eq_run_total = eq(
    "econ.eq.run_total",
    run_cost.symbol,
    run_hw_cost.symbol + run_power_cost.symbol + run_opex_misc_cost.symbol,
    "Total run cost equals capex allocation plus power cost plus all other operating costs.",
    references=[RUN_ROLLUP_REF],
    check_units=True,
)

eq_cost_per_step = eq(
    "econ.eq.cost_per_step",
    cost_per_step.symbol,
    run_cost.symbol / n_steps.symbol,
    "Average cost per optimizer step equals total run cost divided by the total number of training steps.",
    references=[RUN_ROLLUP_REF],
    check_units=True,
)

eq_cost_per_token = eq(
    "econ.eq.cost_per_token",
    cost_per_token.symbol,
    run_cost.symbol / N_train_tokens.symbol,
    "Average cost per token equals total run cost divided by total training tokens.",
    references=[RUN_ROLLUP_REF],
    check_units=True,
)

eq_cost_per_flop = eq(
    "econ.eq.cost_per_flop",
    cost_per_flop.symbol,
    run_cost.symbol / (T_wallclock.symbol * achieved_flops_run.symbol),
    "Average cost per delivered FLOP equals total run cost divided by delivered FLOPs over wall-clock time.",
    references=[RUN_ROLLUP_REF],
    check_units=True,
)

eq_npv_run_cost = eq(
    "econ.eq.npv_run_cost",
    npv_run_cost.symbol,
    run_cost.symbol * discount_factor_run.symbol,
    "Present-value run cost equals nominal run cost times the run discount factor.",
    references=[RUN_ROLLUP_REF],
    check_units=True,
)


# ---------------------------------------------------------------------------
# Inference-token recovery targets
# ---------------------------------------------------------------------------

inference_revenue_per_token = var(
    "econ.recovery.inference_revenue_per_token", "R_tok_inf", "USD/token",
    "Gross revenue captured per served inference token.",
    scope="economics",
    sp_units=USD,
    references=[INFERENCE_RECOVERY_REF],
)
inference_serving_cost_per_token = var(
    "econ.recovery.inference_serving_cost_per_token", "C_tok_inf", "USD/token",
    "Serving cost per inference token, excluding the amortized training bill being recovered.",
    scope="economics",
    sp_units=USD,
    references=[INFERENCE_RECOVERY_REF],
)
net_inference_margin_per_token = var(
    "econ.recovery.net_inference_margin_per_token", "M_tok_inf", "USD/token",
    "Net contribution margin per inference token available to recover training cost.",
    scope="economics",
    sp_units=USD,
    references=[INFERENCE_RECOVERY_REF],
)
inference_tokens_to_recover_run = var(
    "econ.recovery.inference_tokens_to_recover_run", "N_tok_rec", "tokens",
    "Inference tokens required to recover the full training-run cost.",
    scope="economics",
    sp_units=DIMENSIONLESS,
    references=[INFERENCE_RECOVERY_REF],
)


eq_net_inference_margin_per_token = eq(
    "econ.eq.net_inference_margin_per_token",
    net_inference_margin_per_token.symbol,
    inference_revenue_per_token.symbol - inference_serving_cost_per_token.symbol,
    "Net inference margin per token equals gross revenue minus serving cost.",
    references=[INFERENCE_RECOVERY_REF],
    check_units=True,
)

eq_inference_tokens_to_recover_run = eq(
    "econ.eq.inference_tokens_to_recover_run",
    inference_tokens_to_recover_run.symbol,
    run_cost.symbol / net_inference_margin_per_token.symbol,
    "Training-cost recovery target equals run cost divided by net inference margin per token.",
    references=[INFERENCE_RECOVERY_REF],
    check_units=True,
)


ECON_RECOVERY_VARIABLES = [
    cost_per_step,
    cost_per_token,
    cost_per_flop,
    run_hw_cost,
    run_water_cost,
    run_maintenance_cost,
    run_staff_cost,
    run_network_cost,
    run_capacity_charge_cost,
    run_carbon_cost,
    run_opex_misc_cost,
    run_cost,
    inference_revenue_per_token,
    inference_serving_cost_per_token,
    net_inference_margin_per_token,
    inference_tokens_to_recover_run,
]

ECON_RECOVERY_EQUATIONS = [
    eq_run_hw_cost,
    eq_run_water_cost,
    eq_run_maintenance_cost,
    eq_run_staff_cost,
    eq_run_network_cost,
    eq_run_capacity_charge_cost,
    eq_run_carbon_cost,
    eq_run_opex_misc_cost,
    eq_run_total,
    eq_cost_per_step,
    eq_cost_per_token,
    eq_cost_per_flop,
    eq_npv_run_cost,
    eq_net_inference_margin_per_token,
    eq_inference_tokens_to_recover_run,
]


__all__ = [
    "cost_per_step", "cost_per_token", "cost_per_flop",
    "run_hw_cost", "run_water_cost", "run_maintenance_cost",
    "run_staff_cost", "run_network_cost", "run_capacity_charge_cost",
    "run_carbon_cost", "run_opex_misc_cost", "run_cost",
    "inference_revenue_per_token", "inference_serving_cost_per_token",
    "net_inference_margin_per_token", "inference_tokens_to_recover_run",
    "eq_run_hw_cost", "eq_run_water_cost", "eq_run_maintenance_cost",
    "eq_run_staff_cost", "eq_run_network_cost",
    "eq_run_capacity_charge_cost", "eq_run_carbon_cost",
    "eq_run_opex_misc_cost", "eq_run_total",
    "eq_cost_per_step", "eq_cost_per_token", "eq_cost_per_flop",
    "eq_npv_run_cost",
    "eq_net_inference_margin_per_token",
    "eq_inference_tokens_to_recover_run",
    "ECON_RECOVERY_VARIABLES", "ECON_RECOVERY_EQUATIONS",
]
