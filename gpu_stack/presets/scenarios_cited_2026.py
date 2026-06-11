"""
gpu_stack.presets.scenarios_cited_2026
=======================================

Additional sourced scenario packs extending the base inventory in
gpu_stack.presets.scenarios.

Two new pack families with strict provenance discipline:

  Pythia-160M on one DGX H100 node (U.S. 2024 industrial electricity price).
  Uses the same DGX H100 hardware facts and EIA industrial tariff as the
  existing Pythia-70M pack, with the larger GPT-NeoX architecture sourced
  from the EleutherAI Pythia repository and Hugging Face config.json.

  Pythia-70M on one DGX H100 node (U.S. 2024 commercial electricity price).
  Reuses the existing Pythia-70M hardware and workload facts but substitutes
  the EIA 2024 commercial average retail electricity price for the industrial
  rate, making the tariff sensitivity explicit.

Every numeric assignment carries a source string naming a public document.
Assumptions are separated into clearly named closure presets.
"""

from __future__ import annotations

from ..core.presets import Preset, combine
from . import economics, hardware, workload
from .scenario_targets import COST_PER_TOKEN_TARGET, DENSE_TRAINING_COST_TARGETS


# ---------------------------------------------------------------------------
# Pythia-160M sourced workload preset
# ---------------------------------------------------------------------------

pythia_160m_dense_training = Preset(
    name="pythia_160m_dense_training",
    description=(
        "Sourced EleutherAI Pythia-160M dense GPT-NeoX training workload. "
        "Includes only registered workload and architecture fields with a "
        "direct public source mapping."
    ),
    assignments={
        "arch.n_layers": 12,
        "arch.d_model": 768,
        "arch.d_ffn": 3072,
        "arch.n_heads": 12,
        "arch.vocab": 50304,
        "arch.seq_len": 2048,
        "arch.tokens_per_step": 2_097_152,
        "arch.output.untied_factor": 1,
        "training.total_tokens": 299_892_736_000,
    },
    variants={
        "training.flops_per_step": "dense",
        "training.scaling_params": "dense",
    },
    source=(
        "EleutherAI Pythia repository, Models table and Quickstart notes, "
        "https://github.com/EleutherAI/pythia: Pythia-160M has n_layers=12, "
        "d_model=768, n_heads=12, d_head=64, batch size 2M tokens; each model "
        "saw 299,892,736,000 tokens; final checkpoint is after 143000 steps "
        "at batch size 2,097,152 tokens. Hugging Face "
        "EleutherAI/pythia-160m config.json, "
        "https://huggingface.co/EleutherAI/pythia-160m/blob/main/config.json: "
        "hidden_size=768, intermediate_size=3072, max_position_embeddings=2048, "
        "num_attention_heads=12, num_hidden_layers=12, tie_word_embeddings=false, "
        "vocab_size=50304."
    ),
    notes=(
        "arch.output.untied_factor=1 maps the cited tie_word_embeddings=false "
        "config field onto this graph's registered untied-output factor.",
        "The cited d_head=64 and 143000 training steps are left as resolver "
        "cross-checks: arch.head_dim derives from arch.d_model / arch.n_heads, "
        "and training.n_steps derives from training.total_tokens / "
        "arch.tokens_per_step.",
        "arch.n_kv_heads is intentionally unassigned here because the cited "
        "Pythia configuration does not expose a registered key-value head count; "
        "the scenario-layer run-closure preset supplies the graph-closing value.",
    ),
)


# ---------------------------------------------------------------------------
# Pythia-160M single-node DGX H100 run closure
# ---------------------------------------------------------------------------

pythia_160m_dgx_h100_single_node_run_closure = Preset(
    name="pythia_160m_dgx_h100_single_node_run_closure",
    description=(
        "Single-node DGX H100 run-closure inputs needed to connect the "
        "sourced hardware, Pythia-160M workload, and electricity-price presets "
        "through training throughput and run power cost."
    ),
    assignments={
        "arch.n_kv_heads": 12,
        "arch.ffn.weight_matrices": 2,
        "arch.norm.param_multiplier": 4,
        "par.n_gpus": 8,
        "gpu.peak_flops_power_limited": 67e12,
        "gpu.power.total": 700.0,
        "cluster.rack.n_nodes": 1,
        "cluster.site.n_racks": 1,
        "thermal.dc.total_power": 10_200.0,
        "training.recompute_overhead": 1.0,
        "training.optimizer_flop_multiplier": 1.0,
        "training.t_exposed_comm": 0.0,
        "training.t_mem_bound": 0.0,
        "training.overhead_fraction": 0.0,
        "training.cluster_availability": 1.0,
    },
    source=(
        "Run closure for a single NVIDIA DGX H100 node. NVIDIA DGX H100/H200 "
        "User Guide, Introduction to NVIDIA DGX H100/H200 Systems, states "
        "DGX H100 systems are built on eight NVIDIA H100 GPUs and Table 3 "
        "lists 10.2 kW max for 200-240 V AC input. NVIDIA H100 product "
        "specifications list H100 SXM FP32 at 67 teraFLOPS and max TDP up "
        "to 700 W. Architecture closures select standard dense GPT-NeoX "
        "accounting assumptions for this graph: no grouped-query attention "
        "(arch.n_kv_heads=arch.n_heads=12), a two-matrix MLP FFN, and two "
        "LayerNorm modules with learned weight and bias per block. The "
        "remaining 1.0/0.0 training overhead closures are explicit ideal "
        "operating-boundary selections for this scenario pack, not benchmark "
        "measurements."
    ),
    notes=(
        "arch.n_kv_heads=12 closes the graph as ordinary multi-head attention "
        "rather than grouped-query or multi-query attention.",
        "arch.ffn.weight_matrices=2 closes the graph as a plain GPT-NeoX MLP "
        "rather than a gated FFN.",
        "arch.norm.param_multiplier=4 represents two LayerNorm modules per "
        "block, each carrying learned weight and bias per hidden element.",
        "par.n_gpus=8 matches the single DGX H100 node GPU count.",
        "thermal.dc.total_power=10.2 kW uses NVIDIA's max system-power entry "
        "as the site-power boundary for the one-node scenario.",
        "gpu.peak_flops_power_limited=67e12 uses the sourced H100 SXM FP32 "
        "peak as the effective per-GPU throughput boundary for this run.",
        "Neutral overhead closures keep recomputation, optimizer extra FLOPs, "
        "exposed communication, memory-bound auxiliary time, non-nominal "
        "overhead, and availability from dominating a source-composition "
        "regression scenario.",
    ),
)


# ---------------------------------------------------------------------------
# Pythia-160M + DGX H100 + U.S. 2024 industrial power
# ---------------------------------------------------------------------------

pythia_160m_dgx_h100_us_2024_industrial_power = combine(
    hardware.dgx_h100_8gpu_node,
    pythia_160m_dense_training,
    economics.us_2024_industrial_flat_power_tariff,
    pythia_160m_dgx_h100_single_node_run_closure,
    name="pythia_160m_dgx_h100_us_2024_industrial_power",
    description=(
        "Sourced scenario pack combining NVIDIA DGX H100 hardware facts, "
        "EleutherAI Pythia-160M workload facts, EIA 2024 U.S. industrial "
        "average electricity price, and explicit one-node run closures."
    ),
)

_PYTHIA_160M_ENERGY_FLOOR_COST_ASSUMPTION = (
    "Scenario-layer energy-floor cost assumption for resolver closure. "
    "Sets allocated capex rate and non-energy opex to zero so "
    "econ.cost.per_token represents only sourced run electricity cost "
    "from the composed power scenario. This is not measured procurement, "
    "staffing, water, maintenance, network, carbon, demand-charge, or "
    "fully allocated datacenter TCO."
)

pythia_160m_dgx_h100_energy_floor_cost_closure = Preset(
    name="pythia_160m_dgx_h100_energy_floor_cost_closure",
    description=(
        "Assumption-labeled economics closure that lets the Pythia-160M on "
        "DGX H100 industrial-power scenario resolve cost per token as an "
        "electricity-only cost floor."
    ),
    assignments={
        "econ.job.capex_rate": 0.0,
        "econ.run.opex_misc_cost": 0.0,
    },
    source=(
        f"{_PYTHIA_160M_ENERGY_FLOOR_COST_ASSUMPTION}"
    ),
    notes=(
        "econ.job.capex_rate=0.0 excludes hardware, facility, depreciation, "
        "financing, and utilization allocation from this cost floor.",
        "econ.run.opex_misc_cost=0.0 excludes water, maintenance, staff, "
        "network transit, demand charges, and carbon cost from this cost "
        "floor.",
        "The closure intentionally uses two scenario-level economic boundary "
        "assignments, matching the existing preset convention, instead of "
        "inventing zero-valued procurement, staff, water, carbon, network, "
        "maintenance, and demand-charge root measurements.",
    ),
)

pythia_160m_dgx_h100_us_2024_industrial_energy_floor_cost = combine(
    pythia_160m_dgx_h100_us_2024_industrial_power,
    pythia_160m_dgx_h100_energy_floor_cost_closure,
    name="pythia_160m_dgx_h100_us_2024_industrial_energy_floor_cost",
    description=(
        "Assumption-labeled energy cost-floor scenario pack for Pythia-160M "
        "on one DGX H100 node using the sourced 2024 U.S. industrial "
        "electricity price. Cost per token resolves as an electricity-only "
        "lower bound, not fully allocated datacenter TCO."
    ),
)


# ---------------------------------------------------------------------------
# Pythia-70M + DGX H100 + U.S. 2024 commercial power (tariff variant)
# ---------------------------------------------------------------------------
#
# This family reuses the existing hardware (dgx_h100_8gpu_node), workload
# (pythia_70m_dense_training), and run-closure presets from the base pack
# in gpu_stack.presets.scenarios, replacing only the electricity-price
# preset with the EIA 2024 commercial rate to make the tariff sensitivity
# explicit.
#

_COMMERCIAL_TARIFF_RUN_CLOSURE_SOURCE = (
    "Run closure for a single NVIDIA DGX H100 node with the U.S. 2024 "
    "commercial electricity price tariff. NVIDIA DGX H100/H200 User Guide, "
    "Introduction to NVIDIA DGX H100/H200 Systems, states DGX H100 systems "
    "are built on eight NVIDIA H100 GPUs and Table 3 lists 10.2 kW max for "
    "200-240 V AC input. NVIDIA H100 product specifications list H100 SXM "
    "FP32 at 67 teraFLOPS and max TDP up to 700 W. Architecture closures "
    "select standard dense GPT-NeoX accounting assumptions for this graph: "
    "no grouped-query attention (arch.n_kv_heads=arch.n_heads=8), a "
    "two-matrix MLP FFN, and two LayerNorm modules with learned weight and "
    "bias per block. The remaining 1.0/0.0 training overhead closures are "
    "explicit ideal operating-boundary selections for this scenario pack, "
    "not benchmark measurements."
)

pythia_70m_dgx_h100_us_2024_commercial_run_closure = Preset(
    name="pythia_70m_dgx_h100_us_2024_commercial_run_closure",
    description=(
        "Single-node DGX H100 run-closure inputs for the Pythia-70M "
        "commercial-tariff scenario. Identical hardware and overhead closures "
        "to the industrial-tariff run closure."
    ),
    assignments={
        "arch.n_kv_heads": 8,
        "arch.ffn.weight_matrices": 2,
        "arch.norm.param_multiplier": 4,
        "par.n_gpus": 8,
        "gpu.peak_flops_power_limited": 67e12,
        "gpu.power.total": 700.0,
        "cluster.rack.n_nodes": 1,
        "cluster.site.n_racks": 1,
        "thermal.dc.total_power": 10_200.0,
        "training.recompute_overhead": 1.0,
        "training.optimizer_flop_multiplier": 1.0,
        "training.t_exposed_comm": 0.0,
        "training.t_mem_bound": 0.0,
        "training.overhead_fraction": 0.0,
        "training.cluster_availability": 1.0,
    },
    source=_COMMERCIAL_TARIFF_RUN_CLOSURE_SOURCE,
    notes=(
        "arch.n_kv_heads=8 closes the graph as ordinary multi-head attention "
        "rather than grouped-query or multi-query attention.",
        "arch.ffn.weight_matrices=2 closes the graph as a plain GPT-NeoX MLP "
        "rather than a gated FFN.",
        "arch.norm.param_multiplier=4 represents two LayerNorm modules per "
        "block, each carrying learned weight and bias per hidden element.",
        "par.n_gpus=8 matches the single DGX H100 node GPU count.",
        "thermal.dc.total_power=10.2 kW uses NVIDIA's max system-power entry "
        "as the site-power boundary for the one-node scenario.",
        "gpu.peak_flops_power_limited=67e12 uses the sourced H100 SXM FP32 "
        "peak as the effective per-GPU throughput boundary for this run.",
        "Neutral overhead closures keep recomputation, optimizer extra FLOPs, "
        "exposed communication, memory-bound auxiliary time, non-nominal "
        "overhead, and availability from dominating a source-composition "
        "regression scenario.",
    ),
)

pythia_70m_dgx_h100_us_2024_commercial_power = combine(
    hardware.dgx_h100_8gpu_node,
    workload.pythia_70m_dense_training,
    economics.us_2024_commercial_flat_power_tariff,
    pythia_70m_dgx_h100_us_2024_commercial_run_closure,
    name="pythia_70m_dgx_h100_us_2024_commercial_power",
    description=(
        "Sourced scenario pack combining NVIDIA DGX H100 hardware facts, "
        "EleutherAI Pythia-70M workload facts, EIA 2024 U.S. commercial "
        "average electricity price, and explicit one-node run closures. "
        "Companion to the industrial-tariff pack in gpu_stack.presets.scenarios; "
        "highlights the commercial/industrial electricity-price differential."
    ),
)

_COMMERCIAL_ENERGY_FLOOR_ASSUMPTION = (
    "Scenario-layer energy-floor cost assumption for resolver closure. "
    "Sets allocated capex rate and non-energy opex to zero so "
    "econ.cost.per_token represents only sourced run electricity cost "
    "from the composed power scenario. This is not measured procurement, "
    "staffing, water, maintenance, network, carbon, demand-charge, or "
    "fully allocated datacenter TCO."
)

pythia_70m_dgx_h100_us_2024_commercial_energy_floor_cost_closure = Preset(
    name="pythia_70m_dgx_h100_us_2024_commercial_energy_floor_cost_closure",
    description=(
        "Assumption-labeled economics closure that lets the Pythia-70M on "
        "DGX H100 commercial-power scenario resolve cost per token as an "
        "electricity-only cost floor."
    ),
    assignments={
        "econ.job.capex_rate": 0.0,
        "econ.run.opex_misc_cost": 0.0,
    },
    source=_COMMERCIAL_ENERGY_FLOOR_ASSUMPTION,
    notes=(
        "econ.job.capex_rate=0.0 excludes hardware, facility, depreciation, "
        "financing, and utilization allocation from this cost floor.",
        "econ.run.opex_misc_cost=0.0 excludes water, maintenance, staff, "
        "network transit, demand charges, and carbon cost from this cost "
        "floor.",
        "The closure intentionally uses two scenario-level economic boundary "
        "assignments, matching the existing preset convention, instead of "
        "inventing zero-valued procurement, staff, water, carbon, network, "
        "maintenance, and demand-charge root measurements.",
    ),
)

pythia_70m_dgx_h100_us_2024_commercial_energy_floor_cost = combine(
    pythia_70m_dgx_h100_us_2024_commercial_power,
    pythia_70m_dgx_h100_us_2024_commercial_energy_floor_cost_closure,
    name="pythia_70m_dgx_h100_us_2024_commercial_energy_floor_cost",
    description=(
        "Assumption-labeled energy cost-floor scenario pack for Pythia-70M "
        "on one DGX H100 node using the sourced 2024 U.S. commercial "
        "electricity price. Cost per token resolves as an electricity-only "
        "lower bound, not fully allocated datacenter TCO. The commercial "
        "rate (12.75 cents/kWh) is approximately 57% higher than the "
        "industrial rate (8.13 cents/kWh), showing tariff sensitivity."
    ),
)


# ---------------------------------------------------------------------------
# Public registry
# ---------------------------------------------------------------------------

SOURCED_SCENARIO_PACKS_2026 = (
    pythia_160m_dgx_h100_us_2024_industrial_power,
    pythia_160m_dgx_h100_us_2024_industrial_energy_floor_cost,
    pythia_70m_dgx_h100_us_2024_commercial_power,
    pythia_70m_dgx_h100_us_2024_commercial_energy_floor_cost,
)

_PYTHIA_TARGETS = (
    ("tokens_per_second", DENSE_TRAINING_COST_TARGETS["tokens_per_second"]),
    ("job_dc_power", DENSE_TRAINING_COST_TARGETS["job_dc_power"]),
    ("run_power_cost", DENSE_TRAINING_COST_TARGETS["run_power_cost"]),
    ("cost_per_token", COST_PER_TOKEN_TARGET),
)

SCENARIO_TARGET_SETS_2026 = {
    pythia_160m_dgx_h100_us_2024_industrial_power.name: _PYTHIA_TARGETS,
    pythia_160m_dgx_h100_us_2024_industrial_energy_floor_cost.name: _PYTHIA_TARGETS,
    pythia_70m_dgx_h100_us_2024_commercial_power.name: _PYTHIA_TARGETS,
    pythia_70m_dgx_h100_us_2024_commercial_energy_floor_cost.name: _PYTHIA_TARGETS,
}


__all__ = [
    "SOURCED_SCENARIO_PACKS_2026",
    "SCENARIO_TARGET_SETS_2026",
    "pythia_160m_dense_training",
    "pythia_160m_dgx_h100_energy_floor_cost_closure",
    "pythia_160m_dgx_h100_single_node_run_closure",
    "pythia_160m_dgx_h100_us_2024_industrial_energy_floor_cost",
    "pythia_160m_dgx_h100_us_2024_industrial_power",
    "pythia_70m_dgx_h100_us_2024_commercial_energy_floor_cost",
    "pythia_70m_dgx_h100_us_2024_commercial_energy_floor_cost_closure",
    "pythia_70m_dgx_h100_us_2024_commercial_power",
    "pythia_70m_dgx_h100_us_2024_commercial_run_closure",
]
