"""
scopes/parallelism.py
=====================

Parallelism strategies and their memory and communication cost models.

The old file had the names of the dimensions, one FSDP memory formula, and two
pipeline bubble sketches. That was not enough to reason about actual training
plans. This version adds batch decomposition, activation memory, ZeRO stage
breakdowns, offload paths, and explicit TP, EP, and CP traffic formulas.
"""

import sympy as sp
from ..core import Approximation, System, eq, var


sys_par = System(
    name="parallelism",
    scope="parallelism",
    description="DP, TP, SP, PP, EP, CP memory and communication cost models.",
)


# ---------------------------------------------------------------------------
# Degrees of parallelism
# ---------------------------------------------------------------------------

dp_degree = var("par.dp", "d_DP", "degree", "Data-parallel degree.", scope="parallelism")
tp_degree = var("par.tp", "d_TP", "degree", "Tensor-parallel degree.", scope="parallelism")
sp_degree = var(
    "par.sp", "d_SP", "degree",
    "Sequence-parallel degree. In common Megatron-style implementations it matches the TP group size.",
    scope="parallelism",
)
pp_degree = var("par.pp", "d_PP", "degree", "Pipeline-parallel degree.", scope="parallelism")
ep_degree = var("par.ep", "d_EP", "degree", "Expert-parallel degree.", scope="parallelism")
cp_degree = var("par.cp", "d_CP", "degree", "Context-parallel degree.", scope="parallelism")
n_gpus_total = var("par.n_gpus", "N_GPU", "GPUs", "Total GPUs used in the training job.", scope="parallelism")


eq_sp_matches_tp = eq(
    "par.eq.sp_matches_tp",
    sp_degree.symbol,
    tp_degree.symbol,
    "Sequence parallelism usually reuses the tensor-parallel group rather than introducing a separate multiplicative axis.",
)

eq_n_gpus = eq(
    "par.eq.n_gpus",
    n_gpus_total.symbol,
    dp_degree.symbol * tp_degree.symbol * pp_degree.symbol * ep_degree.symbol * cp_degree.symbol,
    "Total GPUs are the product of the independent multiplicative parallelism axes. SP is commonly implemented inside the TP group and therefore does not multiply the device count again.",
)


# ---------------------------------------------------------------------------
# Batch decomposition and tokens per step
# ---------------------------------------------------------------------------

microbatch_per_gpu = var(
    "par.batch.micro_per_gpu", "B_micro_par", "samples",
    "Microbatch size processed by one GPU before gradient accumulation.",
    scope="parallelism",
)
grad_accum_steps = var(
    "par.batch.grad_accum_steps", "N_accum_par", "steps",
    "Gradient-accumulation steps before the optimizer update.",
    scope="parallelism",
)
global_batch = var(
    "par.batch.global", "B_global_par", "samples",
    "Global batch size across the data-parallel group.",
    scope="parallelism",
)
seq_len = var(
    "par.batch.seq_len", "L_seq_par", "tokens",
    "Sequence length per sample.",
    scope="parallelism",
)
tokens_per_step_par = var(
    "par.batch.tokens_per_step", "T_step_tok_par", "tokens",
    "Tokens consumed per optimizer step according to the parallelism-side batch decomposition.",
    scope="parallelism",
)


eq_global_batch = eq(
    "par.eq.global_batch",
    global_batch.symbol,
    microbatch_per_gpu.symbol * grad_accum_steps.symbol * dp_degree.symbol,
    "Global batch equals per-GPU microbatch times accumulation steps times DP degree.",
)

eq_tokens_per_step = eq(
    "par.eq.tokens_per_step",
    tokens_per_step_par.symbol,
    global_batch.symbol * seq_len.symbol,
    "Tokens per step equal global batch times sequence length.",
)


# ---------------------------------------------------------------------------
# Memory accounting
# ---------------------------------------------------------------------------

n_params = var("par.n_params", "P_mod", "params", "Total model parameter count.", scope="parallelism")
bytes_per_param = var(
    "par.bpp", "B_par", "byte/param",
    "Bytes per stored parameter replica.",
    scope="parallelism",
)
grad_bytes_per_param = var(
    "par.grad_bpp", "B_grad_par", "byte/param",
    "Bytes per gradient element.",
    scope="parallelism",
)
opt_state_mult = var(
    "par.opt_state.mult", "k_opt_par", "dimensionless",
    "Optimizer-state tensors per parameter, 2 for AdamW, 1 for Muon, larger for preconditioned methods.",
    scope="parallelism",
)
opt_state_bytes_per_param = var(
    "par.opt_state.bpp", "B_opt_par", "byte/param",
    "Bytes per optimizer-state element.",
    scope="parallelism",
)
mem_params = var("par.mem.params", "M_pm", "byte", "Total parameter memory, unsharded.", scope="parallelism")
mem_grads = var("par.mem.grads", "M_gr", "byte", "Total gradient memory, unsharded.", scope="parallelism")
mem_opt = var("par.mem.opt", "M_os", "byte", "Total optimizer-state memory, unsharded.", scope="parallelism")
mem_act = var("par.mem.activations", "M_act", "byte", "Activation memory before PP and CP partitioning.", scope="parallelism")
mem_act_per_gpu = var("par.mem.act_per_gpu", "M_act_g", "byte", "Activation memory resident on one GPU.", scope="parallelism")
mem_total_per_gpu = var("par.mem.total_per_gpu", "M_tot_g", "byte", "Total GPU memory usage under ZeRO-3 or FSDP-style sharding.", scope="parallelism")
shard_factor = var(
    "par.fsdp.shard_group", "d_shard", "degree",
    "Sharding group size, often DP times CP.",
    scope="parallelism",
)

act_layers = var(
    "par.act.layers", "L_act_par", "layers",
    "Number of layers contributing saved activations.",
    scope="parallelism",
)
act_hidden = var(
    "par.act.hidden", "d_act_par", "dim",
    "Activation width per token.",
    scope="parallelism",
)
act_tensors_per_layer = var(
    "par.act.tensors_per_layer", "N_act_layer_par", "tensors",
    "Number of activation-like tensors retained per layer.",
    scope="parallelism",
)
bytes_per_activation = var(
    "par.act.bytes_per_value", "B_act_val_par", "byte",
    "Bytes per stored activation value.",
    scope="parallelism",
)
checkpoint_keep_fraction = var(
    "par.act.checkpoint_keep_fraction", "rho_keep_par", "dimensionless",
    "Fraction of baseline activations kept after checkpointing or recomputation.",
    scope="parallelism",
)
recompute_fraction = var(
    "par.act.recompute_fraction", "rho_recomp_par", "dimensionless",
    "Fraction of activation work intentionally dropped and recomputed later.",
    scope="parallelism",
)
recompute_flop_multiplier = var(
    "par.act.recompute_flop_multiplier", "m_recomp_par", "dimensionless",
    "FLOP multiplier from activation recomputation.",
    scope="parallelism",
)


eq_mem_params = eq(
    "par.eq.mem_params",
    mem_params.symbol,
    n_params.symbol * bytes_per_param.symbol,
    "Weight memory equals parameters times bytes per parameter.",
)

eq_mem_grads = eq(
    "par.eq.mem_grads",
    mem_grads.symbol,
    n_params.symbol * grad_bytes_per_param.symbol,
    "Gradient memory equals parameters times gradient bytes per parameter.",
)

eq_mem_opt = eq(
    "par.eq.mem_opt",
    mem_opt.symbol,
    n_params.symbol * opt_state_mult.symbol * opt_state_bytes_per_param.symbol,
    "Optimizer-state memory equals parameter count times optimizer-state tensors per parameter times bytes per state value.",
)

eq_shard_group = eq(
    "par.eq.shard_group",
    shard_factor.symbol,
    dp_degree.symbol * cp_degree.symbol,
    "The common sharding group is DP times CP.",
)

eq_mem_act = eq(
    "par.eq.mem_act",
    mem_act.symbol,
    act_layers.symbol * microbatch_per_gpu.symbol * seq_len.symbol * act_hidden.symbol * bytes_per_activation.symbol * act_tensors_per_layer.symbol * checkpoint_keep_fraction.symbol,
    "Activation memory scales with layers, local microbatch, sequence length, hidden width, activation bytes, tensors retained per layer, and the checkpoint keep fraction.",
)

eq_mem_act_per_gpu = eq(
    "par.eq.mem_act_per_gpu",
    mem_act_per_gpu.symbol,
    mem_act.symbol / (pp_degree.symbol * cp_degree.symbol),
    "Pipeline parallelism splits layers and context parallelism splits sequence shards, so activation residency per GPU falls with PP times CP.",
)

eq_recompute_flop_multiplier = eq(
    "par.eq.recompute_flop_multiplier",
    recompute_flop_multiplier.symbol,
    1 + recompute_fraction.symbol,
    "Recomputation adds extra forward-like work on top of the baseline FLOPs.",
)

eq_mem_total_per_gpu_fsdp = eq(
    "par.eq.mem_total_per_gpu_fsdp",
    mem_total_per_gpu.symbol,
    mem_params.symbol / shard_factor.symbol + mem_grads.symbol / shard_factor.symbol + mem_opt.symbol / shard_factor.symbol + mem_act_per_gpu.symbol,
    "ZeRO-3 or FSDP-style memory equals sharded params, sharded grads, sharded optimizer state, plus local activations.",
)


# ---------------------------------------------------------------------------
# ZeRO stage breakdowns
# ---------------------------------------------------------------------------

mem_zero1_per_gpu = var(
    "par.zero1.mem_per_gpu", "M_zero1_par", "byte",
    "Per-GPU memory under ZeRO-1, where only optimizer state is sharded.",
    scope="parallelism",
)
mem_zero2_per_gpu = var(
    "par.zero2.mem_per_gpu", "M_zero2_par", "byte",
    "Per-GPU memory under ZeRO-2, where optimizer state and gradients are sharded.",
    scope="parallelism",
)
mem_zero3_per_gpu = var(
    "par.zero3.mem_per_gpu", "M_zero3_par", "byte",
    "Per-GPU memory under ZeRO-3, where params, gradients, and optimizer state are all sharded.",
    scope="parallelism",
)
fsdp_live_param_fraction = var(
    "par.fsdp.live_param_fraction", "rho_live_par", "dimensionless",
    "Fraction of the full parameter set materialized transiently by an all-gather window.",
    scope="parallelism",
)
fsdp_allgather_buffer = var(
    "par.fsdp.allgather_buffer", "M_gather_par", "byte",
    "Transient parameter buffer materialized during FSDP all-gather.",
    scope="parallelism",
)


eq_mem_zero1 = eq(
    "par.eq.mem_zero1",
    mem_zero1_per_gpu.symbol,
    mem_params.symbol + mem_grads.symbol + mem_opt.symbol / shard_factor.symbol + mem_act_per_gpu.symbol,
    "ZeRO-1 shards optimizer state only.",
)

eq_mem_zero2 = eq(
    "par.eq.mem_zero2",
    mem_zero2_per_gpu.symbol,
    mem_params.symbol + mem_grads.symbol / shard_factor.symbol + mem_opt.symbol / shard_factor.symbol + mem_act_per_gpu.symbol,
    "ZeRO-2 shards gradients and optimizer state but still keeps full parameter replicas.",
)

eq_mem_zero3 = eq(
    "par.eq.mem_zero3",
    mem_zero3_per_gpu.symbol,
    mem_params.symbol / shard_factor.symbol + mem_grads.symbol / shard_factor.symbol + mem_opt.symbol / shard_factor.symbol + mem_act_per_gpu.symbol,
    "ZeRO-3 shards params, gradients, and optimizer state.",
)

eq_fsdp_allgather_buffer = eq(
    "par.eq.fsdp_allgather_buffer",
    fsdp_allgather_buffer.symbol,
    mem_params.symbol * fsdp_live_param_fraction.symbol,
    "A layer-wise all-gather window only materializes the live slice of the parameter set, not the whole model at once.",
)


# ---------------------------------------------------------------------------
# CPU and NVMe offload
# ---------------------------------------------------------------------------

cpu_offload_bytes = var(
    "par.offload.cpu.bytes", "B_cpu_off_par", "byte",
    "State migrated from GPU memory to CPU memory.",
    scope="parallelism",
)
cpu_offload_bw = var(
    "par.offload.cpu.bw", "BW_cpu_off_par", "byte/s",
    "Usable host-device bandwidth for CPU offload traffic.",
    scope="parallelism",
)
cpu_offload_time = var(
    "par.offload.cpu.time", "T_cpu_off_par", "s",
    "Communication time required to move the CPU-offloaded state.",
    scope="parallelism",
)
mem_after_cpu_offload = var(
    "par.offload.cpu.mem_after", "M_cpu_after_par", "byte",
    "Remaining on-GPU memory footprint after CPU offload.",
    scope="parallelism",
)
nvme_offload_bytes = var(
    "par.offload.nvme.bytes", "B_nvme_off_par", "byte",
    "State migrated from GPU or CPU memory to NVMe.",
    scope="parallelism",
)
nvme_offload_bw = var(
    "par.offload.nvme.bw", "BW_nvme_off_par", "byte/s",
    "Usable NVMe bandwidth for optimizer or parameter offload.",
    scope="parallelism",
)
nvme_offload_time = var(
    "par.offload.nvme.time", "T_nvme_off_par", "s",
    "Communication time required to move the NVMe-offloaded state.",
    scope="parallelism",
)


eq_cpu_offload_time = eq(
    "par.eq.cpu_offload_time",
    cpu_offload_time.symbol,
    cpu_offload_bytes.symbol / cpu_offload_bw.symbol,
    "CPU offload time is bytes moved divided by effective host-device bandwidth.",
)

eq_mem_after_cpu_offload = eq(
    "par.eq.mem_after_cpu_offload",
    mem_after_cpu_offload.symbol,
    mem_zero3_per_gpu.symbol - cpu_offload_bytes.symbol,
    "CPU offload reduces the GPU-resident memory footprint by the amount migrated off the device.",
)

eq_nvme_offload_time = eq(
    "par.eq.nvme_offload_time",
    nvme_offload_time.symbol,
    nvme_offload_bytes.symbol / nvme_offload_bw.symbol,
    "NVMe offload time is bytes moved divided by usable storage bandwidth.",
)


# ---------------------------------------------------------------------------
# Pipeline schedules
# ---------------------------------------------------------------------------

n_stages = var(
    "par.pp.n_stages", "S_PP", "stages",
    "Number of pipeline stages.",
    scope="parallelism",
)
n_microbatches = var(
    "par.pp.n_microbatches", "m_PP", "microbatches",
    "Microbatches per pipeline flush.",
    scope="parallelism",
)
t_forward = var(
    "par.pp.t_fwd", "t_fwd_PP", "s",
    "Forward time of one stage on one microbatch.",
    scope="parallelism",
)
t_backward = var(
    "par.pp.t_bwd", "t_bwd_PP", "s",
    "Backward time of one stage on one microbatch.",
    scope="parallelism",
)
bubble_gpipe = var(
    "par.pp.bubble_gpipe", "phi_gpipe_PP", "dimensionless",
    "Bubble fraction for flush-style GPipe.",
    scope="parallelism",
)
bubble_1f1b = var(
    "par.pp.bubble_1f1b", "phi_1f1b_PP", "dimensionless",
    "Bubble fraction under 1F1B.",
    scope="parallelism",
)
virtual_stages = var(
    "par.pp.virtual_stages", "V_PP", "stages",
    "Virtual stages per physical stage for interleaved 1F1B.",
    scope="parallelism",
)
bubble_interleaved = var(
    "par.pp.bubble_interleaved", "phi_il_PP", "dimensionless",
    "Bubble fraction under interleaved 1F1B.",
    scope="parallelism",
)
dualpipe_overlap = var(
    "par.pp.dualpipe_overlap", "rho_dual_PP", "dimensionless",
    "Fraction of the 1F1B bubble eliminated by overlapping forward and backward pipelines in DualPipe-style schedules.",
    scope="parallelism",
)
bubble_dualpipe = var(
    "par.pp.bubble_dualpipe", "phi_dual_PP", "dimensionless",
    "Bubble fraction under DualPipe-style overlap.",
    scope="parallelism",
)
chimera_overlap = var(
    "par.pp.chimera_overlap", "rho_chim_PP", "dimensionless",
    "Fraction of the 1F1B bubble eliminated by a Chimera-style schedule.",
    scope="parallelism",
)
bubble_chimera = var(
    "par.pp.bubble_chimera", "phi_chim_PP", "dimensionless",
    "Bubble fraction under Chimera-style overlap.",
    scope="parallelism",
)
bubble_zb = var(
    "par.pp.bubble_zb", "phi_zb_PP", "dimensionless",
    "Residual bubble under a zero-bubble schedule.",
    scope="parallelism",
)


eq_bubble_1f1b = eq(
    "par.eq.bubble_1f1b",
    bubble_1f1b.symbol,
    (n_stages.symbol - 1) / (n_stages.symbol - 1 + n_microbatches.symbol),
    "1F1B bubble fraction is the pipeline fill-drain overhead divided by the total steady-state stage slots.",
)

eq_bubble_gpipe = Approximation(
    "par.eq.bubble_gpipe",
    bubble_gpipe.symbol,
    (n_stages.symbol - 1) / n_microbatches.symbol,
    n_microbatches.symbol > n_stages.symbol,
    "For GPipe with many microbatches, bubble fraction is approximately (stages - 1) / microbatches.",
)

eq_bubble_interleaved = eq(
    "par.eq.bubble_interleaved",
    bubble_interleaved.symbol,
    (n_stages.symbol / virtual_stages.symbol - 1) / (n_stages.symbol / virtual_stages.symbol - 1 + n_microbatches.symbol),
    "Interleaving reduces the effective pipeline depth seen by the schedule.",
)

eq_bubble_dualpipe = eq(
    "par.eq.bubble_dualpipe",
    bubble_dualpipe.symbol,
    bubble_1f1b.symbol * (1 - dualpipe_overlap.symbol),
    "DualPipe-style overlap reduces the remaining 1F1B bubble by the achieved overlap fraction.",
)

eq_bubble_chimera = eq(
    "par.eq.bubble_chimera",
    bubble_chimera.symbol,
    bubble_1f1b.symbol * (1 - chimera_overlap.symbol),
    "Chimera-style schedules reduce the baseline 1F1B bubble by their achieved overlap fraction.",
)

eq_bubble_zb = eq(
    "par.eq.bubble_zb",
    bubble_zb.symbol,
    sp.Abs(t_backward.symbol - t_forward.symbol) / (t_backward.symbol + t_forward.symbol),
    "If forward and backward times match exactly the residual zero-bubble penalty is zero; any mismatch leaves only the imbalance term.",
)


# ---------------------------------------------------------------------------
# Tensor parallel, expert parallel, and context parallel communication
# ---------------------------------------------------------------------------

tp_tokens_local = var(
    "par.tp.tokens_local", "T_tp_loc_par", "tokens",
    "Tokens resident on one TP rank for a block-local collective.",
    scope="parallelism",
)
tp_hidden = var(
    "par.tp.hidden", "d_tp_comm_par", "dim",
    "Hidden width participating in the TP collective.",
    scope="parallelism",
)
tp_bytes_per_value = var(
    "par.tp.bytes_per_value", "B_tp_val_par", "byte",
    "Bytes per communicated activation element in TP.",
    scope="parallelism",
)
tp_allreduces_per_block = var(
    "par.tp.allreduces_per_block", "N_tp_ar_par", "collectives",
    "All-reduces per transformer block in tensor parallelism.",
    scope="parallelism",
)
tp_comm_per_block = var(
    "par.tp.comm_per_block", "B_TP_blk_par", "byte",
    "TP communication bytes per transformer block.",
    scope="parallelism",
)
tp_overlap_fraction = var(
    "par.tp.overlap_fraction", "rho_tp_ov_par", "dimensionless",
    "Fraction of TP communication overlapped with compute.",
    scope="parallelism",
)
tp_group_bw = var(
    "par.tp.group_bw", "BW_tp_par", "byte/s",
    "Usable bandwidth inside the TP group.",
    scope="parallelism",
)
tp_exposed_time = var(
    "par.tp.exposed_time", "T_tp_exp_par", "s",
    "TP communication time not hidden by overlap.",
    scope="parallelism",
)


eq_tp_comm_per_block = eq(
    "par.eq.tp_comm_per_block",
    tp_comm_per_block.symbol,
    tp_allreduces_per_block.symbol * tp_tokens_local.symbol * tp_hidden.symbol * tp_bytes_per_value.symbol,
    "TP payload per block equals the number of collectives times the local activation tensor size.",
)

eq_tp_exposed_time = eq(
    "par.eq.tp_exposed_time",
    tp_exposed_time.symbol,
    tp_comm_per_block.symbol * (1 - tp_overlap_fraction.symbol) / tp_group_bw.symbol,
    "Only the unoverlapped fraction of TP traffic contributes to exposed communication time.",
)

n_experts_total = var(
    "par.moe.n_experts_total", "N_exp_par", "experts",
    "Total experts participating in the EP group.",
    scope="parallelism",
)
top_k = var(
    "par.moe.top_k", "k_MoE_par", "experts",
    "Top-k experts activated per token.",
    scope="parallelism",
)
moe_tokens_local = var(
    "par.moe.tokens_local", "T_moe_loc_par", "tokens",
    "Tokens entering one MoE dispatch on a rank.",
    scope="parallelism",
)
moe_hidden = var(
    "par.moe.hidden", "d_moe_par", "dim",
    "Activation width carried by the MoE dispatch.",
    scope="parallelism",
)
moe_bytes_per_value = var(
    "par.moe.bytes_per_value", "B_moe_val_par", "byte",
    "Bytes per MoE activation element.",
    scope="parallelism",
)
capacity_factor = var(
    "par.moe.capacity_factor", "rho_cap_moe_par", "dimensionless",
    "Expert-capacity multiplier above the mean routed load.",
    scope="parallelism",
)
expert_capacity = var(
    "par.moe.expert_capacity", "C_exp_moe_par", "tokens",
    "Token capacity reserved per expert after applying the capacity factor.",
    scope="parallelism",
)
expert_imbalance = var(
    "par.moe.imbalance", "rho_imb_moe_par", "dimensionless",
    "Multiplicative load imbalance above the ideal evenly routed dispatch.",
    scope="parallelism",
)
moe_payload_per_layer = var(
    "par.moe.payload_per_layer", "B_EP_L_par", "byte",
    "All-to-all payload per MoE layer, including dispatch and combine.",
    scope="parallelism",
)
ep_group_bw = var(
    "par.moe.group_bw", "BW_ep_par", "byte/s",
    "Usable bandwidth inside the expert-parallel group.",
    scope="parallelism",
)
ep_exposed_time = var(
    "par.moe.exposed_time", "T_ep_exp_par", "s",
    "Exposed expert-parallel all-to-all time.",
    scope="parallelism",
)


eq_expert_capacity = eq(
    "par.eq.expert_capacity",
    expert_capacity.symbol,
    capacity_factor.symbol * moe_tokens_local.symbol * top_k.symbol / n_experts_total.symbol,
    "Expert capacity equals mean routed tokens per expert times the capacity factor.",
)

eq_moe_payload = eq(
    "par.eq.moe_payload_per_layer",
    moe_payload_per_layer.symbol,
    2 * top_k.symbol * moe_tokens_local.symbol * moe_hidden.symbol * moe_bytes_per_value.symbol,
    "MoE traffic includes both dispatch and combine, each carrying top-k routed activations.",
)

eq_ep_exposed_time = eq(
    "par.eq.ep_exposed_time",
    ep_exposed_time.symbol,
    moe_payload_per_layer.symbol * expert_imbalance.symbol / ep_group_bw.symbol,
    "Expert imbalance inflates the ideal all-to-all time by stretching the slowest dispatch path.",
)

cp_kv_bytes_local = var(
    "par.cp.kv_bytes_local", "B_cp_kv_loc_par", "byte",
    "KV-state bytes held locally by one context-parallel rank.",
    scope="parallelism",
)
cp_ring_hops = var(
    "par.cp.ring_hops", "H_cp_ring_par", "hops",
    "Neighbor exchanges traversed in a ring-style context-parallel pass.",
    scope="parallelism",
)
cp_comm_per_layer = var(
    "par.cp.comm_per_layer", "B_cp_L_par", "byte",
    "Context-parallel communication per layer.",
    scope="parallelism",
)


eq_cp_ring_hops = eq(
    "par.eq.cp_ring_hops",
    cp_ring_hops.symbol,
    cp_degree.symbol - 1,
    "A ring over CP ranks requires degree minus one neighbor exchanges per full circulation.",
)

eq_cp_comm_per_layer = eq(
    "par.eq.cp_comm_per_layer",
    cp_comm_per_layer.symbol,
    2 * cp_kv_bytes_local.symbol * cp_ring_hops.symbol,
    "Ring-style context parallelism exchanges local KV state around the ring for both forward and backward style passes.",
)


PARALLELISM_VARIABLES = [
    dp_degree, tp_degree, sp_degree, pp_degree, ep_degree, cp_degree, n_gpus_total,
    microbatch_per_gpu, grad_accum_steps, global_batch, seq_len, tokens_per_step_par,
    n_params, bytes_per_param, grad_bytes_per_param, opt_state_mult,
    opt_state_bytes_per_param, mem_params, mem_grads, mem_opt, mem_act,
    mem_act_per_gpu, mem_total_per_gpu, shard_factor,
    act_layers, act_hidden, act_tensors_per_layer, bytes_per_activation,
    checkpoint_keep_fraction, recompute_fraction, recompute_flop_multiplier,
    mem_zero1_per_gpu, mem_zero2_per_gpu, mem_zero3_per_gpu,
    fsdp_live_param_fraction, fsdp_allgather_buffer,
    cpu_offload_bytes, cpu_offload_bw, cpu_offload_time, mem_after_cpu_offload,
    nvme_offload_bytes, nvme_offload_bw, nvme_offload_time,
    n_stages, n_microbatches, t_forward, t_backward, bubble_gpipe,
    bubble_1f1b, virtual_stages, bubble_interleaved, dualpipe_overlap,
    bubble_dualpipe, chimera_overlap, bubble_chimera, bubble_zb,
    tp_tokens_local, tp_hidden, tp_bytes_per_value, tp_allreduces_per_block,
    tp_comm_per_block, tp_overlap_fraction, tp_group_bw, tp_exposed_time,
    n_experts_total, top_k, moe_tokens_local, moe_hidden, moe_bytes_per_value,
    capacity_factor, expert_capacity, expert_imbalance, moe_payload_per_layer,
    ep_group_bw, ep_exposed_time,
    cp_kv_bytes_local, cp_ring_hops, cp_comm_per_layer,
]

PARALLELISM_EQUATIONS = [
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
    eq_mem_zero1,
    eq_mem_zero2,
    eq_mem_zero3,
    eq_fsdp_allgather_buffer,
    eq_cpu_offload_time,
    eq_mem_after_cpu_offload,
    eq_nvme_offload_time,
    eq_bubble_1f1b,
    eq_bubble_gpipe,
    eq_bubble_interleaved,
    eq_bubble_dualpipe,
    eq_bubble_chimera,
    eq_bubble_zb,
    eq_tp_comm_per_block,
    eq_tp_exposed_time,
    eq_expert_capacity,
    eq_moe_payload,
    eq_ep_exposed_time,
    eq_cp_ring_hops,
    eq_cp_comm_per_layer,
]

for v in PARALLELISM_VARIABLES:
    sys_par.add(v)

for e in PARALLELISM_EQUATIONS:
    sys_par.add(e)
