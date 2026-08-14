"""
scopes/optimizer_sharding.py
============================

How many bytes the optimizer's memory bill comes to, and who pays it.

Optimizer state is often the largest tensor family in training: the total
footprint is parameter count times bytes of state per parameter, where
the state multiplier depends on the rule (two moments for AdamW, one
buffer for Lion, more for Shampoo). At scale nobody keeps a full copy per
GPU — distributed Shampoo divides its per-block preconditioner state by a
shard degree, each rank holding one slice. This helper computes both the
undivided total and the per-rank Shampoo state; the parallelism scope's
ZeRO and FSDP formulas apply the equivalent sharding to first-order
state when budgeting per-GPU memory.
"""

import sympy as sp

from ..core import Reference, eq, var
from ..core.units import byte

from .optimizer_first_order import bytes_per_opt_param
from .optimizer_second_order import shampoo_state_bytes
from .parallelism import n_params


DIMENSIONLESS = sp.Integer(1)

OPT_SHARDING_REF = Reference(
    "Optimizer-state memory accounting tracks byte-valued per-rank state "
    "after sharding dimensionless parameter counts and shard degrees.",
    kind="model",
)


# ---------------------------------------------------------------------------
# Distributed Shampoo sharding
# ---------------------------------------------------------------------------

distributed_shampoo_shard_degree = var(
    "opt.shampoo.shard_degree", "d_shampoo_opt", "degree",
    "Sharding degree for distributed Shampoo state.",
    scope="optimizer",
    sp_units=DIMENSIONLESS,
    references=[OPT_SHARDING_REF],
)
distributed_shampoo_state_bytes = var(
    "opt.shampoo.state_bytes_distributed", "M_shampoo_dist_opt", "byte",
    "Per-rank Shampoo state after sharding.",
    scope="optimizer",
    sp_units=byte,
    references=[OPT_SHARDING_REF],
)


eq_distributed_shampoo_state_bytes = eq(
    "opt.eq.distributed_shampoo_state_bytes",
    distributed_shampoo_state_bytes.symbol,
    shampoo_state_bytes.symbol / distributed_shampoo_shard_degree.symbol,
    "Distributed Shampoo amortizes the preconditioner state across the chosen shard degree.",
    references=[OPT_SHARDING_REF],
    check_units=True,
)


# ---------------------------------------------------------------------------
# Optimizer-state memory
# ---------------------------------------------------------------------------

opt_state_mult = var(
    "opt.state_mult", "k_opt_state_opt", "multiplier",
    "Optimizer-state tensors per parameter in the selected optimizer.",
    scope="optimizer",
    sp_units=DIMENSIONLESS,
    references=[OPT_SHARDING_REF],
)
opt_state_bytes = var(
    "opt.state.bytes", "M_opt_state_opt", "byte",
    "Total optimizer-state memory footprint.",
    scope="optimizer",
    sp_units=byte,
    references=[OPT_SHARDING_REF],
)


eq_opt_state = eq(
    "opt.eq.state_memory",
    opt_state_bytes.symbol,
    opt_state_mult.symbol * bytes_per_opt_param.symbol * n_params.symbol,
    "Optimizer-state memory equals tensors-per-parameter times bytes-per-state times total parameter count.",
    references=[OPT_SHARDING_REF],
    check_units=True,
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
