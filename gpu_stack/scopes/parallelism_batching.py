"""
scopes/parallelism_batching.py
==============================

Sequence parallelism (SP), batch decomposition, tokens-per-step math,
activation-memory formulas, checkpoint keep fraction, and recomputation
FLOP multiplier. Foundation helper for parallelism; downstream helpers
import shared symbols from here.
"""

import sympy as sp

from ..core import Reference, eq, var
from ..core.units import byte


DIMENSIONLESS = sp.Integer(1)

PARALLELISM_TOPOLOGY_REF = Reference(
    "Parallelism topology model: DP, TP, SP, PP, EP, and CP are represented "
    "as dimensionless multiplicative rank-group axes, with SP nested inside "
    "the TP group for common Megatron-style layouts.",
    kind="model",
)
PARALLELISM_BATCHING_REF = Reference(
    "Parallelism batch accounting model: local microbatch size, gradient "
    "accumulation, data-parallel degree, and sequence length determine "
    "global batch and tokens consumed per optimizer step.",
    kind="model",
)
PARALLELISM_MEMORY_REF = Reference(
    "Parallelism memory accounting model: parameter, gradient, optimizer, "
    "activation, recomputation, and FSDP-style shard terms are tracked as "
    "byte-valued quantities with dimensionless partition factors.",
    kind="model",
)


# ---------------------------------------------------------------------------
# Degrees of parallelism
# ---------------------------------------------------------------------------

dp_degree = var(
    "par.dp", "d_DP", "degree", "Data-parallel degree.",
    scope="parallelism",
    sp_units=DIMENSIONLESS,
    references=[PARALLELISM_TOPOLOGY_REF],
)
tp_degree = var(
    "par.tp", "d_TP", "degree", "Tensor-parallel degree.",
    scope="parallelism",
    sp_units=DIMENSIONLESS,
    references=[PARALLELISM_TOPOLOGY_REF],
)
sp_degree = var(
    "par.sp", "d_SP", "degree",
    "Sequence-parallel degree. In common Megatron-style implementations it matches the TP group size.",
    scope="parallelism",
    sp_units=DIMENSIONLESS,
    references=[PARALLELISM_TOPOLOGY_REF],
)
pp_degree = var(
    "par.pp", "d_PP", "degree", "Pipeline-parallel degree.",
    scope="parallelism",
    sp_units=DIMENSIONLESS,
    references=[PARALLELISM_TOPOLOGY_REF],
)
ep_degree = var(
    "par.ep", "d_EP", "degree", "Expert-parallel degree.",
    scope="parallelism",
    sp_units=DIMENSIONLESS,
    references=[PARALLELISM_TOPOLOGY_REF],
)
cp_degree = var(
    "par.cp", "d_CP", "degree", "Context-parallel degree.",
    scope="parallelism",
    sp_units=DIMENSIONLESS,
    references=[PARALLELISM_TOPOLOGY_REF],
)
n_gpus_total = var(
    "par.n_gpus", "N_GPU", "GPUs", "Total GPUs used in the training job.",
    scope="parallelism",
    sp_units=DIMENSIONLESS,
    references=[PARALLELISM_TOPOLOGY_REF],
)


eq_sp_matches_tp = eq(
    "par.eq.sp_matches_tp",
    sp_degree.symbol,
    tp_degree.symbol,
    "Sequence parallelism usually reuses the tensor-parallel group rather than introducing a separate multiplicative axis.",
    references=[PARALLELISM_TOPOLOGY_REF],
    check_units=True,
)

eq_n_gpus = eq(
    "par.eq.n_gpus",
    n_gpus_total.symbol,
    dp_degree.symbol * tp_degree.symbol * pp_degree.symbol * ep_degree.symbol * cp_degree.symbol,
    "Total GPUs are the product of the independent multiplicative parallelism axes. SP is commonly implemented inside the TP group and therefore does not multiply the device count again.",
    references=[PARALLELISM_TOPOLOGY_REF],
    check_units=True,
)


# ---------------------------------------------------------------------------
# Batch decomposition and tokens per step
# ---------------------------------------------------------------------------

microbatch_per_gpu = var(
    "par.batch.micro_per_gpu", "B_micro_par", "samples",
    "Microbatch size processed by one GPU before gradient accumulation.",
    scope="parallelism",
    sp_units=DIMENSIONLESS,
    references=[PARALLELISM_BATCHING_REF],
)
grad_accum_steps = var(
    "par.batch.grad_accum_steps", "N_accum_par", "steps",
    "Gradient-accumulation steps before the optimizer update.",
    scope="parallelism",
    sp_units=DIMENSIONLESS,
    references=[PARALLELISM_BATCHING_REF],
)
global_batch = var(
    "par.batch.global", "B_global_par", "samples",
    "Global batch size across the data-parallel group.",
    scope="parallelism",
    sp_units=DIMENSIONLESS,
    references=[PARALLELISM_BATCHING_REF],
)
seq_len = var(
    "par.batch.seq_len", "L_seq_par", "tokens",
    "Sequence length per sample.",
    scope="parallelism",
    sp_units=DIMENSIONLESS,
    references=[PARALLELISM_BATCHING_REF],
)
tokens_per_step_par = var(
    "par.batch.tokens_per_step", "T_step_tok_par", "tokens",
    "Tokens consumed per optimizer step according to the parallelism-side batch decomposition.",
    scope="parallelism",
    sp_units=DIMENSIONLESS,
    references=[PARALLELISM_BATCHING_REF],
)


eq_global_batch = eq(
    "par.eq.global_batch",
    global_batch.symbol,
    microbatch_per_gpu.symbol * grad_accum_steps.symbol * dp_degree.symbol,
    "Global batch equals per-GPU microbatch times accumulation steps times DP degree.",
    references=[PARALLELISM_BATCHING_REF],
    check_units=True,
)

eq_tokens_per_step = eq(
    "par.eq.tokens_per_step",
    tokens_per_step_par.symbol,
    global_batch.symbol * seq_len.symbol,
    "Tokens per step equal global batch times sequence length.",
    references=[PARALLELISM_BATCHING_REF],
    check_units=True,
)


# ---------------------------------------------------------------------------
# Memory accounting
# ---------------------------------------------------------------------------

n_params = var(
    "par.n_params", "P_mod", "params", "Total model parameter count.",
    scope="parallelism",
    sp_units=DIMENSIONLESS,
    references=[PARALLELISM_MEMORY_REF],
)
bytes_per_param = var(
    "par.bpp", "B_par", "byte/param",
    "Bytes per stored parameter replica.",
    scope="parallelism",
    sp_units=byte,
    references=[PARALLELISM_MEMORY_REF],
)
grad_bytes_per_param = var(
    "par.grad_bpp", "B_grad_par", "byte/param",
    "Bytes per gradient element.",
    scope="parallelism",
    sp_units=byte,
    references=[PARALLELISM_MEMORY_REF],
)
opt_state_mult = var(
    "par.opt_state.mult", "k_opt_par", "dimensionless",
    "Optimizer-state tensors per parameter, 2 for AdamW, 1 for Muon, larger for preconditioned methods.",
    scope="parallelism",
    sp_units=DIMENSIONLESS,
    references=[PARALLELISM_MEMORY_REF],
)
opt_state_bytes_per_param = var(
    "par.opt_state.bpp", "B_opt_par", "byte/param",
    "Bytes per optimizer-state element.",
    scope="parallelism",
    sp_units=byte,
    references=[PARALLELISM_MEMORY_REF],
)
mem_params = var(
    "par.mem.params", "M_pm", "byte", "Total parameter memory, unsharded.",
    scope="parallelism",
    sp_units=byte,
    references=[PARALLELISM_MEMORY_REF],
)
mem_grads = var(
    "par.mem.grads", "M_gr", "byte", "Total gradient memory, unsharded.",
    scope="parallelism",
    sp_units=byte,
    references=[PARALLELISM_MEMORY_REF],
)
mem_opt = var(
    "par.mem.opt", "M_os", "byte", "Total optimizer-state memory, unsharded.",
    scope="parallelism",
    sp_units=byte,
    references=[PARALLELISM_MEMORY_REF],
)
mem_act = var(
    "par.mem.activations", "M_act", "byte", "Activation memory before PP and CP partitioning.",
    scope="parallelism",
    sp_units=byte,
    references=[PARALLELISM_MEMORY_REF],
)
mem_act_per_gpu = var(
    "par.mem.act_per_gpu", "M_act_g", "byte", "Activation memory resident on one GPU.",
    scope="parallelism",
    sp_units=byte,
    references=[PARALLELISM_MEMORY_REF],
)
mem_total_per_gpu = var(
    "par.mem.total_per_gpu", "M_tot_g", "byte", "Total GPU memory usage under ZeRO-3 or FSDP-style sharding.",
    scope="parallelism",
    sp_units=byte,
    references=[PARALLELISM_MEMORY_REF],
)
shard_factor = var(
    "par.fsdp.shard_group", "d_shard", "degree",
    "Sharding group size, often DP times CP.",
    scope="parallelism",
    sp_units=DIMENSIONLESS,
    references=[PARALLELISM_MEMORY_REF],
)

act_layers = var(
    "par.act.layers", "L_act_par", "layers",
    "Number of layers contributing saved activations.",
    scope="parallelism",
    sp_units=DIMENSIONLESS,
    references=[PARALLELISM_MEMORY_REF],
)
act_hidden = var(
    "par.act.hidden", "d_act_par", "dim",
    "Activation width per token.",
    scope="parallelism",
    sp_units=DIMENSIONLESS,
    references=[PARALLELISM_MEMORY_REF],
)
act_tensors_per_layer = var(
    "par.act.tensors_per_layer", "N_act_layer_par", "tensors",
    "Number of activation-like tensors retained per layer.",
    scope="parallelism",
    sp_units=DIMENSIONLESS,
    references=[PARALLELISM_MEMORY_REF],
)
bytes_per_activation = var(
    "par.act.bytes_per_value", "B_act_val_par", "byte",
    "Bytes per stored activation value.",
    scope="parallelism",
    sp_units=byte,
    references=[PARALLELISM_MEMORY_REF],
)
checkpoint_keep_fraction = var(
    "par.act.checkpoint_keep_fraction", "rho_keep_par", "dimensionless",
    "Fraction of baseline activations kept after checkpointing or recomputation.",
    scope="parallelism",
    sp_units=DIMENSIONLESS,
    references=[PARALLELISM_MEMORY_REF],
)
recompute_fraction = var(
    "par.act.recompute_fraction", "rho_recomp_par", "dimensionless",
    "Fraction of activation work intentionally dropped and recomputed later.",
    scope="parallelism",
    sp_units=DIMENSIONLESS,
    references=[PARALLELISM_MEMORY_REF],
)
recompute_flop_multiplier = var(
    "par.act.recompute_flop_multiplier", "m_recomp_par", "dimensionless",
    "FLOP multiplier from activation recomputation.",
    scope="parallelism",
    sp_units=DIMENSIONLESS,
    references=[PARALLELISM_MEMORY_REF],
)


eq_mem_params = eq(
    "par.eq.mem_params",
    mem_params.symbol,
    n_params.symbol * bytes_per_param.symbol,
    "Weight memory equals parameters times bytes per parameter.",
    references=[PARALLELISM_MEMORY_REF],
    check_units=True,
)

eq_mem_grads = eq(
    "par.eq.mem_grads",
    mem_grads.symbol,
    n_params.symbol * grad_bytes_per_param.symbol,
    "Gradient memory equals parameters times gradient bytes per parameter.",
    references=[PARALLELISM_MEMORY_REF],
    check_units=True,
)

eq_mem_opt = eq(
    "par.eq.mem_opt",
    mem_opt.symbol,
    n_params.symbol * opt_state_mult.symbol * opt_state_bytes_per_param.symbol,
    "Optimizer-state memory equals parameter count times optimizer-state tensors per parameter times bytes per state value.",
    references=[PARALLELISM_MEMORY_REF],
    check_units=True,
)

eq_shard_group = eq(
    "par.eq.shard_group",
    shard_factor.symbol,
    dp_degree.symbol * cp_degree.symbol,
    "The common sharding group is DP times CP.",
    references=[PARALLELISM_MEMORY_REF],
    check_units=True,
)

eq_mem_act = eq(
    "par.eq.mem_act",
    mem_act.symbol,
    act_layers.symbol * microbatch_per_gpu.symbol * seq_len.symbol * act_hidden.symbol * bytes_per_activation.symbol * act_tensors_per_layer.symbol * checkpoint_keep_fraction.symbol,
    "Activation memory scales with layers, local microbatch, sequence length, hidden width, activation bytes, tensors retained per layer, and the checkpoint keep fraction.",
    references=[PARALLELISM_MEMORY_REF],
    check_units=True,
)

eq_mem_act_per_gpu = eq(
    "par.eq.mem_act_per_gpu",
    mem_act_per_gpu.symbol,
    mem_act.symbol / (pp_degree.symbol * cp_degree.symbol),
    "Pipeline parallelism splits layers and context parallelism splits sequence shards, so activation residency per GPU falls with PP times CP.",
    references=[PARALLELISM_MEMORY_REF],
    check_units=True,
)

eq_recompute_flop_multiplier = eq(
    "par.eq.recompute_flop_multiplier",
    recompute_flop_multiplier.symbol,
    1 + recompute_fraction.symbol,
    "Recomputation adds extra forward-like work on top of the baseline FLOPs.",
    references=[PARALLELISM_MEMORY_REF],
    check_units=True,
)

eq_mem_total_per_gpu_fsdp = eq(
    "par.eq.mem_total_per_gpu_fsdp",
    mem_total_per_gpu.symbol,
    mem_params.symbol / shard_factor.symbol + mem_grads.symbol / shard_factor.symbol + mem_opt.symbol / shard_factor.symbol + mem_act_per_gpu.symbol,
    "ZeRO-3 or FSDP-style memory equals sharded params, sharded grads, sharded optimizer state, plus local activations.",
    references=[PARALLELISM_MEMORY_REF],
    check_units=True,
)


PARALLELISM_BATCHING_VARIABLES = [
    dp_degree, tp_degree, sp_degree, pp_degree, ep_degree, cp_degree, n_gpus_total,
    microbatch_per_gpu, grad_accum_steps, global_batch, seq_len, tokens_per_step_par,
    n_params, bytes_per_param, grad_bytes_per_param, opt_state_mult,
    opt_state_bytes_per_param, mem_params, mem_grads, mem_opt, mem_act,
    mem_act_per_gpu, mem_total_per_gpu, shard_factor,
    act_layers, act_hidden, act_tensors_per_layer, bytes_per_activation,
    checkpoint_keep_fraction, recompute_fraction, recompute_flop_multiplier,
]

PARALLELISM_BATCHING_EQUATIONS = [
    eq_sp_matches_tp,
    eq_n_gpus,
    eq_global_batch,
    eq_tokens_per_step,
    eq_mem_params,
    eq_mem_grads,
    eq_mem_opt,
    eq_shard_group,
    eq_mem_act,
    eq_mem_act_per_gpu,
    eq_recompute_flop_multiplier,
    eq_mem_total_per_gpu_fsdp,
]


__all__ = [
    "dp_degree",
    "tp_degree",
    "sp_degree",
    "pp_degree",
    "ep_degree",
    "cp_degree",
    "n_gpus_total",
    "microbatch_per_gpu",
    "grad_accum_steps",
    "global_batch",
    "seq_len",
    "tokens_per_step_par",
    "n_params",
    "bytes_per_param",
    "grad_bytes_per_param",
    "opt_state_mult",
    "opt_state_bytes_per_param",
    "mem_params",
    "mem_grads",
    "mem_opt",
    "mem_act",
    "mem_act_per_gpu",
    "mem_total_per_gpu",
    "shard_factor",
    "act_layers",
    "act_hidden",
    "act_tensors_per_layer",
    "bytes_per_activation",
    "checkpoint_keep_fraction",
    "recompute_fraction",
    "recompute_flop_multiplier",
    "eq_sp_matches_tp",
    "eq_n_gpus",
    "eq_global_batch",
    "eq_tokens_per_step",
    "eq_mem_params",
    "eq_mem_grads",
    "eq_mem_opt",
    "eq_shard_group",
    "eq_mem_act",
    "eq_mem_act_per_gpu",
    "eq_recompute_flop_multiplier",
    "eq_mem_total_per_gpu_fsdp",
    "PARALLELISM_BATCHING_VARIABLES",
    "PARALLELISM_BATCHING_EQUATIONS",
]
