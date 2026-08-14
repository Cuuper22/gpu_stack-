"""
scopes/parallelism_moe.py
=========================

The traffic bills of tensor, expert, and context parallelism.

Splitting a layer across GPUs means the pieces must talk every layer, and
this helper counts the bytes for three axes. Tensor parallel: each
transformer block triggers a fixed number of allreduces over the TP group,
each carrying local tokens times hidden width times bytes per value; the
unoverlapped fraction of that traffic, divided by TP-group bandwidth, is
the exposed time per block. Expert parallel: top-k routing dispatches and
combines token activations through all-to-alls, with expert capacity set
by the capacity factor and the time stretched by router imbalance.
Context parallel: each rank's local KV state circulates around a ring of
CP-minus-one hops so every rank attends over the full sequence.

The collective scope prices these payloads with its alpha-beta formulas;
the training scope adds the exposed times to the step.
"""

import sympy as sp

from ..core import Reference, eq, var
from ..core.units import BPS, SECOND, byte
from .parallelism_batching import cp_degree


DIMENSIONLESS = sp.Integer(1)

TP_COMM_REF = Reference(
    "Tensor-parallel communication model: per-block payloads are activation "
    "tensor byte counts multiplied by collective count, with exposed time "
    "computed from unoverlapped traffic over usable TP-group bandwidth.",
    kind="model",
)
MOE_ROUTING_REF = Reference(
    "MoE routing and expert-parallel communication model: top-k dispatch, "
    "capacity factor, imbalance, dispatch/combine payload, and EP group "
    "bandwidth define expert capacity and all-to-all exposed time.",
    kind="model",
)
CP_COMM_REF = Reference(
    "Context-parallel communication model: local KV-state bytes circulate "
    "over a CP ring whose hop count is CP degree minus one.",
    kind="model",
)


# ---------------------------------------------------------------------------
# Tensor parallel, expert parallel, and context parallel communication
# ---------------------------------------------------------------------------

tp_tokens_local = var(
    "par.tp.tokens_local", "T_tp_loc_par", "tokens",
    "Tokens resident on one TP rank for a block-local collective.",
    scope="parallelism",
    sp_units=DIMENSIONLESS,
    references=[TP_COMM_REF],
)
tp_hidden = var(
    "par.tp.hidden", "d_tp_comm_par", "dim",
    "Hidden width participating in the TP collective.",
    scope="parallelism",
    sp_units=DIMENSIONLESS,
    references=[TP_COMM_REF],
)
tp_bytes_per_value = var(
    "par.tp.bytes_per_value", "B_tp_val_par", "byte",
    "Bytes per communicated activation element in TP.",
    scope="parallelism",
    sp_units=byte,
    references=[TP_COMM_REF],
)
tp_allreduces_per_block = var(
    "par.tp.allreduces_per_block", "N_tp_ar_par", "collectives",
    "All-reduces per transformer block in tensor parallelism.",
    scope="parallelism",
    sp_units=DIMENSIONLESS,
    references=[TP_COMM_REF],
)
tp_comm_per_block = var(
    "par.tp.comm_per_block", "B_TP_blk_par", "byte",
    "TP communication bytes per transformer block.",
    scope="parallelism",
    sp_units=byte,
    references=[TP_COMM_REF],
)
tp_overlap_fraction = var(
    "par.tp.overlap_fraction", "rho_tp_ov_par", "dimensionless",
    "Fraction of TP communication overlapped with compute.",
    scope="parallelism",
    sp_units=DIMENSIONLESS,
    references=[TP_COMM_REF],
)
tp_group_bw = var(
    "par.tp.group_bw", "BW_tp_par", "byte/s",
    "Usable bandwidth inside the TP group.",
    scope="parallelism",
    sp_units=BPS,
    references=[TP_COMM_REF],
)
tp_exposed_time = var(
    "par.tp.exposed_time", "T_tp_exp_par", "s",
    "TP communication time not hidden by overlap.",
    scope="parallelism",
    sp_units=SECOND,
    references=[TP_COMM_REF],
)


eq_tp_comm_per_block = eq(
    "par.eq.tp_comm_per_block",
    tp_comm_per_block.symbol,
    tp_allreduces_per_block.symbol * tp_tokens_local.symbol * tp_hidden.symbol * tp_bytes_per_value.symbol,
    "TP payload per block equals the number of collectives times the local activation tensor size.",
    references=[TP_COMM_REF],
    check_units=True,
)

eq_tp_exposed_time = eq(
    "par.eq.tp_exposed_time",
    tp_exposed_time.symbol,
    tp_comm_per_block.symbol * (1 - tp_overlap_fraction.symbol) / tp_group_bw.symbol,
    "Only the unoverlapped fraction of TP traffic contributes to exposed communication time.",
    references=[TP_COMM_REF],
    check_units=True,
)

n_experts_total = var(
    "par.moe.n_experts_total", "N_exp_par", "experts",
    "Total experts participating in the EP group.",
    scope="parallelism",
    sp_units=DIMENSIONLESS,
    references=[MOE_ROUTING_REF],
)
top_k = var(
    "par.moe.top_k", "k_MoE_par", "experts",
    "Top-k experts activated per token.",
    scope="parallelism",
    sp_units=DIMENSIONLESS,
    references=[MOE_ROUTING_REF],
)
moe_tokens_local = var(
    "par.moe.tokens_local", "T_moe_loc_par", "tokens",
    "Tokens entering one MoE dispatch on a rank.",
    scope="parallelism",
    sp_units=DIMENSIONLESS,
    references=[MOE_ROUTING_REF],
)
moe_hidden = var(
    "par.moe.hidden", "d_moe_par", "dim",
    "Activation width carried by the MoE dispatch.",
    scope="parallelism",
    sp_units=DIMENSIONLESS,
    references=[MOE_ROUTING_REF],
)
moe_bytes_per_value = var(
    "par.moe.bytes_per_value", "B_moe_val_par", "byte",
    "Bytes per MoE activation element.",
    scope="parallelism",
    sp_units=byte,
    references=[MOE_ROUTING_REF],
)
capacity_factor = var(
    "par.moe.capacity_factor", "rho_cap_moe_par", "dimensionless",
    "Expert-capacity multiplier above the mean routed load.",
    scope="parallelism",
    sp_units=DIMENSIONLESS,
    references=[MOE_ROUTING_REF],
)
expert_capacity = var(
    "par.moe.expert_capacity", "C_exp_moe_par", "tokens",
    "Token capacity reserved per expert after applying the capacity factor.",
    scope="parallelism",
    sp_units=DIMENSIONLESS,
    references=[MOE_ROUTING_REF],
)
expert_imbalance = var(
    "par.moe.imbalance", "rho_imb_moe_par", "dimensionless",
    "Multiplicative load imbalance above the ideal evenly routed dispatch.",
    scope="parallelism",
    sp_units=DIMENSIONLESS,
    references=[MOE_ROUTING_REF],
)
moe_payload_per_layer = var(
    "par.moe.payload_per_layer", "B_EP_L_par", "byte",
    "All-to-all payload per MoE layer, including dispatch and combine.",
    scope="parallelism",
    sp_units=byte,
    references=[MOE_ROUTING_REF],
)
ep_group_bw = var(
    "par.moe.group_bw", "BW_ep_par", "byte/s",
    "Usable bandwidth inside the expert-parallel group.",
    scope="parallelism",
    sp_units=BPS,
    references=[MOE_ROUTING_REF],
)
ep_exposed_time = var(
    "par.moe.exposed_time", "T_ep_exp_par", "s",
    "Exposed expert-parallel all-to-all time.",
    scope="parallelism",
    sp_units=SECOND,
    references=[MOE_ROUTING_REF],
)


eq_expert_capacity = eq(
    "par.eq.expert_capacity",
    expert_capacity.symbol,
    capacity_factor.symbol * moe_tokens_local.symbol * top_k.symbol / n_experts_total.symbol,
    "Expert capacity equals mean routed tokens per expert times the capacity factor.",
    references=[MOE_ROUTING_REF],
    check_units=True,
)

eq_moe_payload = eq(
    "par.eq.moe_payload_per_layer",
    moe_payload_per_layer.symbol,
    2 * top_k.symbol * moe_tokens_local.symbol * moe_hidden.symbol * moe_bytes_per_value.symbol,
    "MoE traffic includes both dispatch and combine, each carrying top-k routed activations.",
    references=[MOE_ROUTING_REF],
    check_units=True,
)

eq_ep_exposed_time = eq(
    "par.eq.ep_exposed_time",
    ep_exposed_time.symbol,
    moe_payload_per_layer.symbol * expert_imbalance.symbol / ep_group_bw.symbol,
    "Expert imbalance inflates the ideal all-to-all time by stretching the slowest dispatch path.",
    references=[MOE_ROUTING_REF],
    check_units=True,
)

cp_kv_bytes_local = var(
    "par.cp.kv_bytes_local", "B_cp_kv_loc_par", "byte",
    "KV-state bytes held locally by one context-parallel rank.",
    scope="parallelism",
    sp_units=byte,
    references=[CP_COMM_REF],
)
cp_ring_hops = var(
    "par.cp.ring_hops", "H_cp_ring_par", "hops",
    "Neighbor exchanges traversed in a ring-style context-parallel pass.",
    scope="parallelism",
    sp_units=DIMENSIONLESS,
    references=[CP_COMM_REF],
)
cp_comm_per_layer = var(
    "par.cp.comm_per_layer", "B_cp_L_par", "byte",
    "Context-parallel communication per layer.",
    scope="parallelism",
    sp_units=byte,
    references=[CP_COMM_REF],
)


eq_cp_ring_hops = eq(
    "par.eq.cp_ring_hops",
    cp_ring_hops.symbol,
    cp_degree.symbol - 1,
    "A ring over CP ranks requires degree minus one neighbor exchanges per full circulation.",
    references=[CP_COMM_REF],
    check_units=True,
)

eq_cp_comm_per_layer = eq(
    "par.eq.cp_comm_per_layer",
    cp_comm_per_layer.symbol,
    2 * cp_kv_bytes_local.symbol * cp_ring_hops.symbol,
    "Ring-style context parallelism exchanges local KV state around the ring for both forward and backward style passes.",
    references=[CP_COMM_REF],
    check_units=True,
)


PARALLELISM_MOE_VARIABLES = [
    tp_tokens_local, tp_hidden, tp_bytes_per_value, tp_allreduces_per_block,
    tp_comm_per_block, tp_overlap_fraction, tp_group_bw, tp_exposed_time,
    n_experts_total, top_k, moe_tokens_local, moe_hidden, moe_bytes_per_value,
    capacity_factor, expert_capacity, expert_imbalance, moe_payload_per_layer,
    ep_group_bw, ep_exposed_time,
    cp_kv_bytes_local, cp_ring_hops, cp_comm_per_layer,
]

PARALLELISM_MOE_EQUATIONS = [
    eq_tp_comm_per_block,
    eq_tp_exposed_time,
    eq_expert_capacity,
    eq_moe_payload,
    eq_ep_exposed_time,
    eq_cp_ring_hops,
    eq_cp_comm_per_layer,
]


__all__ = [
    "tp_tokens_local",
    "tp_hidden",
    "tp_bytes_per_value",
    "tp_allreduces_per_block",
    "tp_comm_per_block",
    "tp_overlap_fraction",
    "tp_group_bw",
    "tp_exposed_time",
    "n_experts_total",
    "top_k",
    "moe_tokens_local",
    "moe_hidden",
    "moe_bytes_per_value",
    "capacity_factor",
    "expert_capacity",
    "expert_imbalance",
    "moe_payload_per_layer",
    "ep_group_bw",
    "ep_exposed_time",
    "cp_kv_bytes_local",
    "cp_ring_hops",
    "cp_comm_per_layer",
    "eq_tp_comm_per_block",
    "eq_tp_exposed_time",
    "eq_expert_capacity",
    "eq_moe_payload",
    "eq_ep_exposed_time",
    "eq_cp_ring_hops",
    "eq_cp_comm_per_layer",
    "PARALLELISM_MOE_VARIABLES",
    "PARALLELISM_MOE_EQUATIONS",
]
