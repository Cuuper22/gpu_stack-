"""
scopes/architecture_moe.py
==========================

Mixture-of-experts routing and sparsity. Covers expert counts, router and
shared-expert parameters, capacity factors, auxiliary balancing losses, and
per-step active FLOPs.
"""

import sympy as sp

from ..core import Reference, eq, var
from ..core.units import FLOP

from .architecture_embeddings import n_tokens_step


DIMENSIONLESS = sp.Integer(1)

MOE_ROUTING_REF = Reference(
    "MoE routing metadata tracks total experts, active experts, routed token "
    "capacity, router penalties, and load-balancing terms as dimensionless "
    "routing counts or losses.",
    kind="model",
)
MOE_PARAM_REF = Reference(
    "MoE parameter accounting distinguishes instantiated expert parameters "
    "from active per-token expert parameters and always includes shared "
    "experts and router parameters in the layer total.",
    kind="model",
)
MOE_FLOP_REF = Reference(
    "MoE training FLOP accounting uses active parameters per token path rather "
    "than total instantiated expert parameters.",
    kind="model",
)


# ---------------------------------------------------------------------------
# MoE routing and sparsity
# ---------------------------------------------------------------------------

n_moe_layers = var(
    "arch.moe.n_moe_layers", "L_moe_arch", "layers",
    "Number of MoE layers in the model.",
    scope="architecture",
)
n_experts = var(
    "arch.moe.n_experts", "N_exp_arch", "experts",
    "Experts per MoE layer.",
    scope="architecture",
)
active_experts = var(
    "arch.moe.active_experts", "k_exp_arch", "experts",
    "Experts activated per token.",
    scope="architecture",
)
sparsity_ratio = var(
    "arch.moe.sparsity", "s_moe_arch", "dimensionless",
    "MoE sparsity ratio, total experts divided by active experts.",
    scope="architecture",
)
params_expert_each = var(
    "arch.moe.params_expert_each", "P_exp_each_arch", "params",
    "Parameters in one expert.",
    scope="architecture",
)
params_router = var(
    "arch.moe.params_router", "P_router_arch", "params",
    "Router parameters per MoE layer.",
    scope="architecture",
)
shared_expert_count = var(
    "arch.moe.shared_expert_count", "N_shared_exp_arch", "experts",
    "Shared experts present in every token path.",
    scope="architecture",
)
shared_expert_params_each = var(
    "arch.moe.shared_expert_params_each", "P_shared_each_arch", "params",
    "Parameters in one shared expert.",
    scope="architecture",
)
params_shared_experts = var(
    "arch.moe.params_shared", "P_shared_arch", "params",
    "Shared-expert parameters per MoE layer.",
    scope="architecture",
)
params_moe_layer_total = var(
    "arch.moe.params_layer_total", "P_moe_layer_total_arch", "params",
    "Total parameters instantiated by one MoE layer.",
    scope="architecture",
)
params_moe_layer_active = var(
    "arch.moe.params_layer_active", "P_moe_layer_active_arch", "params",
    "Active parameters touched by one token path through one MoE layer.",
    scope="architecture",
)
params_total_moe = var(
    "arch.moe.params_total", "P_moe_total_arch", "params",
    "Total parameters across all MoE layers.",
    scope="architecture",
)
params_active_moe = var(
    "arch.moe.params_active", "P_moe_active_arch", "params",
    "Active parameters per token path across all MoE layers.",
    scope="architecture",
)
moe_tokens_batch = var(
    "arch.moe.tokens_batch", "T_moe_batch_arch", "tokens",
    "Tokens entering one MoE layer in a batch.",
    scope="architecture",
)
moe_capacity_factor = var(
    "arch.moe.capacity_factor", "rho_cap_arch", "dimensionless",
    "Capacity factor above mean routed load.",
    scope="architecture",
)
expert_capacity = var(
    "arch.moe.expert_capacity", "C_exp_arch", "tokens",
    "Capacity reserved per expert.",
    scope="architecture",
)
router_fi_pi_sum = var(
    "arch.moe.router_fi_pi_sum", "S_bal_arch", "dimensionless",
    "The sum over experts of token fraction times average router probability.",
    scope="architecture",
)
load_balance_loss = var(
    "arch.moe.load_balance_loss", "L_bal_arch", "dimensionless",
    "Auxiliary MoE load-balance loss.",
    scope="architecture",
)
router_log_z = var(
    "arch.moe.router_log_z", "logZ_arch", "dimensionless",
    "Log partition function at the router.",
    scope="architecture",
    positive=False,
)
router_z_loss = var(
    "arch.moe.router_z_loss", "L_z_arch", "dimensionless",
    "Router z-loss.",
    scope="architecture",
)
flops_step_moe = var(
    "arch.flops.step_moe", "F_step_moe_arch", "FLOP",
    "MoE training FLOPs per step.",
    scope="architecture",
)

for _v in (
    n_moe_layers, n_experts, active_experts, sparsity_ratio,
    params_expert_each, params_router, shared_expert_count,
    shared_expert_params_each, params_shared_experts, params_moe_layer_total,
    params_moe_layer_active, params_total_moe, params_active_moe,
    moe_tokens_batch, moe_capacity_factor, expert_capacity,
    router_fi_pi_sum, load_balance_loss, router_log_z, router_z_loss,
):
    _v.sp_units = DIMENSIONLESS
    _v.references.append(MOE_ROUTING_REF)

for _v in (
    params_expert_each, params_router, shared_expert_params_each,
    params_shared_experts, params_moe_layer_total,
    params_moe_layer_active, params_total_moe, params_active_moe,
):
    _v.references.append(MOE_PARAM_REF)

flops_step_moe.sp_units = FLOP
flops_step_moe.references.append(MOE_FLOP_REF)


eq_sparsity = eq(
    "arch.eq.sparsity",
    sparsity_ratio.symbol,
    n_experts.symbol / active_experts.symbol,
    "MoE sparsity ratio equals total experts divided by active experts.",
    check_units=True,
)

eq_params_shared_experts = eq(
    "arch.eq.params_shared_experts",
    params_shared_experts.symbol,
    shared_expert_count.symbol * shared_expert_params_each.symbol,
    "Shared-expert parameters equal shared expert count times parameters per shared expert.",
    check_units=True,
)

eq_params_moe_layer_total = eq(
    "arch.eq.params_moe_layer_total",
    params_moe_layer_total.symbol,
    n_experts.symbol * params_expert_each.symbol + params_shared_experts.symbol + params_router.symbol,
    "Total MoE-layer parameters include all experts, shared experts, and the router.",
    check_units=True,
)

eq_params_moe_layer_active = eq(
    "arch.eq.params_moe_layer_active",
    params_moe_layer_active.symbol,
    active_experts.symbol * params_expert_each.symbol + params_shared_experts.symbol + params_router.symbol,
    "Active MoE-layer parameters include only the active experts plus shared experts and the router.",
    check_units=True,
)

eq_params_total_moe = eq(
    "arch.eq.params_total_moe",
    params_total_moe.symbol,
    n_moe_layers.symbol * params_moe_layer_total.symbol,
    "Total MoE parameters equal MoE layers times parameters instantiated per MoE layer.",
    check_units=True,
)

eq_params_active_moe = eq(
    "arch.eq.params_active_moe",
    params_active_moe.symbol,
    n_moe_layers.symbol * params_moe_layer_active.symbol,
    "Active MoE parameters per token path equal MoE layers times active parameters per MoE layer.",
    check_units=True,
)

eq_expert_capacity = eq(
    "arch.eq.expert_capacity",
    expert_capacity.symbol,
    moe_capacity_factor.symbol * moe_tokens_batch.symbol * active_experts.symbol / n_experts.symbol,
    "Expert capacity equals mean routed tokens per expert times the capacity factor.",
    check_units=True,
)

eq_load_balance_loss = eq(
    "arch.eq.load_balance_loss",
    load_balance_loss.symbol,
    n_experts.symbol * router_fi_pi_sum.symbol,
    "The common MoE auxiliary balancing loss is number_of_experts times the sum over experts of token fraction times average routing probability.",
    check_units=True,
)

eq_router_z_loss = eq(
    "arch.eq.router_z_loss",
    router_z_loss.symbol,
    router_log_z.symbol ** 2,
    "Router z-loss penalizes the square of log Z.",
    check_units=True,
)

eq_flops_step_moe = eq(
    "arch.eq.flops_step_moe",
    flops_step_moe.symbol,
    6 * params_active_moe.symbol * n_tokens_step.symbol,
    "MoE training FLOPs depend on active parameters, not total instantiated parameters.",
    check_units=True,
)


ARCH_MOE_VARIABLES = [
    n_moe_layers, n_experts, active_experts, sparsity_ratio,
    params_expert_each, params_router, shared_expert_count,
    shared_expert_params_each, params_shared_experts, params_moe_layer_total,
    params_moe_layer_active, params_total_moe, params_active_moe,
    moe_tokens_batch, moe_capacity_factor, expert_capacity,
    router_fi_pi_sum, load_balance_loss, router_log_z, router_z_loss,
    flops_step_moe,
]

ARCH_MOE_EQUATIONS = [
    eq_sparsity,
    eq_params_shared_experts,
    eq_params_moe_layer_total,
    eq_params_moe_layer_active,
    eq_params_total_moe,
    eq_params_active_moe,
    eq_expert_capacity,
    eq_load_balance_loss,
    eq_router_z_loss,
    eq_flops_step_moe,
]

for _e in (
    eq_sparsity, eq_expert_capacity, eq_load_balance_loss, eq_router_z_loss,
):
    _e.references.append(MOE_ROUTING_REF)

for _e in (
    eq_params_shared_experts, eq_params_moe_layer_total,
    eq_params_moe_layer_active, eq_params_total_moe, eq_params_active_moe,
):
    _e.references.append(MOE_PARAM_REF)

eq_flops_step_moe.references.append(MOE_FLOP_REF)


__all__ = [
    "n_moe_layers", "n_experts", "active_experts", "sparsity_ratio",
    "params_expert_each", "params_router", "shared_expert_count",
    "shared_expert_params_each", "params_shared_experts",
    "params_moe_layer_total", "params_moe_layer_active",
    "params_total_moe", "params_active_moe",
    "moe_tokens_batch", "moe_capacity_factor", "expert_capacity",
    "router_fi_pi_sum", "load_balance_loss", "router_log_z",
    "router_z_loss", "flops_step_moe",
    "eq_sparsity", "eq_params_shared_experts", "eq_params_moe_layer_total",
    "eq_params_moe_layer_active", "eq_params_total_moe",
    "eq_params_active_moe", "eq_expert_capacity", "eq_load_balance_loss",
    "eq_router_z_loss", "eq_flops_step_moe",
    "ARCH_MOE_VARIABLES", "ARCH_MOE_EQUATIONS",
]
