"""
scopes/optimizer_sharding.py
============================

Distributed optimizer-state memory.

This helper covers the total optimizer-state footprint across all parameters
and the distributed-Shampoo sharding that amortizes per-block preconditioner
state across ranks.
"""

from ..core import eq, var

from .optimizer_first_order import bytes_per_opt_param
from .optimizer_second_order import shampoo_state_bytes
from .parallelism import n_params


# ---------------------------------------------------------------------------
# Distributed Shampoo sharding
# ---------------------------------------------------------------------------

distributed_shampoo_shard_degree = var(
    "opt.shampoo.shard_degree", "d_shampoo_opt", "degree",
    "Sharding degree for distributed Shampoo state.",
    scope="optimizer",
)
distributed_shampoo_state_bytes = var(
    "opt.shampoo.state_bytes_distributed", "M_shampoo_dist_opt", "byte",
    "Per-rank Shampoo state after sharding.",
    scope="optimizer",
)


eq_distributed_shampoo_state_bytes = eq(
    "opt.eq.distributed_shampoo_state_bytes",
    distributed_shampoo_state_bytes.symbol,
    shampoo_state_bytes.symbol / distributed_shampoo_shard_degree.symbol,
    "Distributed Shampoo amortizes the preconditioner state across the chosen shard degree.",
)


# ---------------------------------------------------------------------------
# Optimizer-state memory
# ---------------------------------------------------------------------------

opt_state_mult = var(
    "opt.state_mult", "k_opt_state_opt", "multiplier",
    "Optimizer-state tensors per parameter in the selected optimizer.",
    scope="optimizer",
)
opt_state_bytes = var(
    "opt.state.bytes", "M_opt_state_opt", "byte",
    "Total optimizer-state memory footprint.",
    scope="optimizer",
)


eq_opt_state = eq(
    "opt.eq.state_memory",
    opt_state_bytes.symbol,
    opt_state_mult.symbol * bytes_per_opt_param.symbol * n_params.symbol,
    "Optimizer-state memory equals tensors-per-parameter times bytes-per-state times total parameter count.",
)


OPT_SHARDING_VARIABLES = [
    distributed_shampoo_shard_degree,
    distributed_shampoo_state_bytes,
    opt_state_mult,
    opt_state_bytes,
]

OPT_SHARDING_EQUATIONS = [
    eq_distributed_shampoo_state_bytes,
    eq_opt_state,
]


__all__ = [
    "distributed_shampoo_shard_degree", "distributed_shampoo_state_bytes",
    "opt_state_mult", "opt_state_bytes",
    "eq_distributed_shampoo_state_bytes", "eq_opt_state",
    "OPT_SHARDING_VARIABLES", "OPT_SHARDING_EQUATIONS",
]
