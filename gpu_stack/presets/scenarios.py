"""
gpu_stack.presets.scenarios
===========================

Small end-to-end scenario fixtures and sourced scenario packs.

The dense-training cost fixture is synthetic, not historical measurement or a
vendor specification. Sourced scenario packs compose narrower presets so a
caller can feed a compact scenario into the existing resolver without copying
domain-specific root assignments by hand.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

from ..core.presets import Preset, combine
from . import economics, hardware, lithography, materials, workload


COST_PER_TOKEN_TARGET = "econ.cost.per_token"

_ScenarioTargetSet = tuple[tuple[str, str], ...]

DENSE_TRAINING_COST_TARGETS: Mapping[str, str] = MappingProxyType(
    {
        "step_time": "training.t_step",
        "tokens_per_second": "training.tokens_per_sec",
        "wallclock": "training.wallclock",
        "job_dc_power": "econ.job.dc_power",
        "run_power_cost": "econ.run.power_cost",
        "run_cost": "econ.run.total_cost",
        "cost_per_token": COST_PER_TOKEN_TARGET,
    }
)

EUV_TIN120_SOURCE_TARGETS: Mapping[str, str] = MappingProxyType(
    {
        "source_proton_count": "physical.lithography.source_proton_count",
        "source_neutron_count": "physical.lithography.source_neutron_count",
        "pulse_repetition_rate": (
            "physical.lithography.source_plasma_pulse_repetition_rate"
        ),
    }
)


dense_training_cost_inputs = Preset(
    name="dense_training_cost_inputs",
    description=(
        "Round-number dense training run inputs that exercise training "
        "throughput, cluster power, facility power allocation, electricity "
        "pricing, and run-cost rollup."
    ),
    assignments={
        # Training work and step-time boundary conditions.
        "arch.flops.step_dense": 1.0e15,
        "arch.tokens_per_step": 1.0e6,
        "training.total_tokens": 1.0e7,
        "training.recompute_overhead": 1.0,
        "training.optimizer_flop_multiplier": 1.0,
        "training.t_exposed_comm": 0.025,
        "training.t_mem_bound": 0.0,
        "training.overhead_fraction": 0.0,
        "training.cluster_availability": 1.0,
        "par.n_gpus": 8,
        "gpu.peak_flops_power_limited": 1.0e15,
        # Site power path. The resolver derives econ.job.dc_power from these.
        "gpu.power.total": 500.0,
        "cluster.node.n_gpus": 8,
        "cluster.node.cpu_power": 200.0,
        "cluster.node.ram_power": 100.0,
        "cluster.node.nic_power": 50.0,
        "cluster.node.storage_power": 25.0,
        "cluster.node.misc_power": 25.0,
        "cluster.rack.n_nodes": 1,
        "cluster.site.n_racks": 1,
        "thermal.facility.cooling_power": 600.0,
        "thermal.facility.ups_loss": 100.0,
        "thermal.facility.transformer_loss": 100.0,
        "thermal.facility.lighting": 0.0,
        "thermal.facility.misc": 0.0,
        # Economics knobs. These are fixture assumptions, not market data.
        "econ.job.capex_rate": 20.0,
        "econ.power.price_kwh_peak": 0.36,
        "econ.power.price_kwh_offpeak": 0.36,
        "econ.power.peak_energy_fraction": 1.0,
        "econ.run.opex_misc_cost": 0.0,
    },
    source=(
        "Synthetic resolver fixture in gpu_stack.presets.scenarios. Values are "
        "round-number assumptions chosen for deterministic tests; they are not "
        "historical data, vendor specifications, or price recommendations."
    ),
    notes=(
        "Cost per token resolves through training.wallclock, econ.job.dc_power, "
        "econ.run.power_cost, econ.run.total_cost, and econ.cost.per_token.",
        "Override assignments with Preset.with_overrides() for concrete user "
        "scenarios or sourced measurements.",
    ),
)


dense_training_cost_fixture = combine(
    workload.dense_variant_selector,
    dense_training_cost_inputs,
    name="dense_training_cost_fixture",
    description=(
        "Synthetic dense-training economics fixture with the dense FLOP "
        "variant selected and enough boundary assignments to resolve "
        "cost-per-token end to end."
    ),
)


pythia_70m_dgx_h100_single_node_run_closure = Preset(
    name="pythia_70m_dgx_h100_single_node_run_closure",
    description=(
        "Single-node DGX H100 run-closure inputs needed to connect the "
        "sourced hardware, workload, and electricity-price presets through "
        "training throughput and run power cost."
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
    source=(
        "Run closure for a single NVIDIA DGX H100 node. NVIDIA DGX H100/H200 "
        "User Guide, Introduction to NVIDIA DGX H100/H200 Systems, states "
        "DGX H100 systems are built on eight NVIDIA H100 GPUs and Table 3 "
        "lists 10.2 kW max for 200-240 V AC input. NVIDIA H100 product "
        "specifications list H100 SXM FP32 at 67 teraFLOPS and max TDP up "
        "to 700 W. Architecture closures select standard dense GPT-NeoX "
        "accounting assumptions for this graph: no grouped-query attention "
        "(arch.n_kv_heads=arch.n_heads=8), a two-matrix MLP FFN, and two "
        "LayerNorm modules with learned weight and bias per block. The "
        "remaining 1.0/0.0 training overhead closures are explicit ideal "
        "operating-boundary selections for this scenario pack, not benchmark "
        "measurements."
    ),
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


pythia_70m_dgx_h100_us_2024_industrial_power = combine(
    hardware.dgx_h100_8gpu_node,
    workload.pythia_70m_dense_training,
    economics.us_2024_industrial_flat_power_tariff,
    pythia_70m_dgx_h100_single_node_run_closure,
    name="pythia_70m_dgx_h100_us_2024_industrial_power",
    description=(
        "Sourced scenario pack combining NVIDIA DGX H100 hardware facts, "
        "EleutherAI Pythia-70M workload facts, EIA 2024 U.S. industrial "
        "average electricity price, and explicit one-node run closures."
    ),
)


pythia_70m_dgx_h100_energy_floor_cost_closure = Preset(
    name="pythia_70m_dgx_h100_energy_floor_cost_closure",
    description=(
        "Assumption-labeled economics closure that lets the Pythia-70M on "
        "DGX H100 industrial-power scenario resolve cost per token as an "
        "electricity-only cost floor."
    ),
    assignments={
        "econ.job.capex_rate": 0.0,
        "econ.run.opex_misc_cost": 0.0,
    },
    source=(
        "Scenario-layer energy-floor cost assumption for resolver closure. "
        "Sets allocated capex rate and non-energy opex to zero so "
        "econ.cost.per_token represents only sourced run electricity cost "
        "from the composed power scenario. This is not measured procurement, "
        "staffing, water, maintenance, network, carbon, demand-charge, or "
        "fully allocated datacenter TCO."
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


pythia_70m_dgx_h100_us_2024_industrial_energy_floor_cost = combine(
    pythia_70m_dgx_h100_us_2024_industrial_power,
    pythia_70m_dgx_h100_energy_floor_cost_closure,
    name="pythia_70m_dgx_h100_us_2024_industrial_energy_floor_cost",
    description=(
        "Assumption-labeled energy cost-floor scenario pack for Pythia-70M "
        "on one DGX H100 node using the sourced 2024 U.S. industrial "
        "electricity price. Cost per token resolves as an electricity-only "
        "lower bound, not fully allocated datacenter TCO."
    ),
)


_TIN120_SOURCE_CONTEXT_ASSUMPTION = (
    "Scenario-layer tin-120 assumption: this pack models the EUV tin source "
    "species as 120Sn for isotope-level closure only. ASML public material "
    "establishes tin laser-produced-plasma context, not isotope selection."
)


def _euv_tin120_lpp_source_context_assumption() -> Preset:
    combined = combine(
        materials.source_tin_120,
        lithography.asml_euv_tin_lpp_public_context,
        name="euv_tin120_lpp_source_context_assumption",
        description=(
            "Assumption-labeled EUV tin-source scenario pack combining the "
            "materials.source_tin_120 composition closure with ASML's public "
            "50 kHz laser-produced-plasma repetition-rate context."
        ),
    )
    return combined.with_overrides(
        name=combined.name,
        source=f"{combined.source} | {_TIN120_SOURCE_CONTEXT_ASSUMPTION}",
        notes=(
            *combined.notes,
            "This scenario pack assigns only tin-120 source composition roots "
            "and the ASML public pulse-period root.",
            "It does not assign drive fluence, species pressure, gas "
            "temperature, focusing geometry, plasma heating, or conversion "
            "efficiency roots.",
        ),
    )


euv_tin120_lpp_source_context_assumption = (
    _euv_tin120_lpp_source_context_assumption()
)


SOURCED_SCENARIO_PACKS = (
    pythia_70m_dgx_h100_us_2024_industrial_power,
    pythia_70m_dgx_h100_us_2024_industrial_energy_floor_cost,
    euv_tin120_lpp_source_context_assumption,
)

SCENARIO_TARGET_SETS: Mapping[str, _ScenarioTargetSet] = MappingProxyType(
    {
        dense_training_cost_fixture.name: tuple(DENSE_TRAINING_COST_TARGETS.items()),
        pythia_70m_dgx_h100_us_2024_industrial_power.name: (
            ("tokens_per_second", DENSE_TRAINING_COST_TARGETS["tokens_per_second"]),
            ("job_dc_power", DENSE_TRAINING_COST_TARGETS["job_dc_power"]),
            ("run_power_cost", DENSE_TRAINING_COST_TARGETS["run_power_cost"]),
            ("cost_per_token", COST_PER_TOKEN_TARGET),
        ),
        pythia_70m_dgx_h100_us_2024_industrial_energy_floor_cost.name: (
            ("tokens_per_second", DENSE_TRAINING_COST_TARGETS["tokens_per_second"]),
            ("job_dc_power", DENSE_TRAINING_COST_TARGETS["job_dc_power"]),
            ("run_power_cost", DENSE_TRAINING_COST_TARGETS["run_power_cost"]),
            ("cost_per_token", COST_PER_TOKEN_TARGET),
        ),
        euv_tin120_lpp_source_context_assumption.name: tuple(
            EUV_TIN120_SOURCE_TARGETS.items()
        ),
    }
)


def scenario_targets_for(preset_or_name: Preset | str) -> _ScenarioTargetSet:
    """Return advertised labeled resolver targets for a scenario preset."""
    name = (
        preset_or_name.name
        if isinstance(preset_or_name, Preset)
        else preset_or_name
    )
    try:
        return SCENARIO_TARGET_SETS[name]
    except KeyError:
        raise KeyError(
            f"no advertised scenario targets registered for {name!r}"
        ) from None


__all__ = [
    "COST_PER_TOKEN_TARGET",
    "DENSE_TRAINING_COST_TARGETS",
    "EUV_TIN120_SOURCE_TARGETS",
    "SCENARIO_TARGET_SETS",
    "SOURCED_SCENARIO_PACKS",
    "dense_training_cost_inputs",
    "dense_training_cost_fixture",
    "euv_tin120_lpp_source_context_assumption",
    "pythia_70m_dgx_h100_energy_floor_cost_closure",
    "pythia_70m_dgx_h100_single_node_run_closure",
    "pythia_70m_dgx_h100_us_2024_industrial_energy_floor_cost",
    "pythia_70m_dgx_h100_us_2024_industrial_power",
    "scenario_targets_for",
]
