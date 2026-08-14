"""
Advertised resolver targets for scenario presets.

Each scenario preset promises a set of variables it can resolve. This module
holds that promise as an explicit registry mapping short labels (like
"cost_per_token") to full variable names, so tools can list and look up a
scenario's targets without parsing the preset itself. The scenario packs
themselves live in ``gpu_stack.presets.scenarios``.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

from ..core.presets import Preset


COST_PER_TOKEN_TARGET = "econ.cost.per_token"

ScenarioTargetSet = tuple[tuple[str, str], ...]

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


def build_scenario_target_sets(
    *,
    dense_training_cost_fixture: Preset,
    pythia_industrial_power: Preset,
    pythia_energy_floor_cost: Preset,
    pythia_full_tco: Preset,
    euv_tin120_source_context: Preset,
) -> Mapping[str, ScenarioTargetSet]:
    """Build the read-only registry mapping each preset name to its target set."""
    pythia_targets = (
        ("tokens_per_second", DENSE_TRAINING_COST_TARGETS["tokens_per_second"]),
        ("job_dc_power", DENSE_TRAINING_COST_TARGETS["job_dc_power"]),
        ("run_power_cost", DENSE_TRAINING_COST_TARGETS["run_power_cost"]),
        ("cost_per_token", COST_PER_TOKEN_TARGET),
    )
    return MappingProxyType(
        {
            dense_training_cost_fixture.name: tuple(
                DENSE_TRAINING_COST_TARGETS.items()
            ),
            pythia_industrial_power.name: pythia_targets,
            pythia_energy_floor_cost.name: pythia_targets,
            pythia_full_tco.name: pythia_targets,
            euv_tin120_source_context.name: tuple(
                EUV_TIN120_SOURCE_TARGETS.items()
            ),
        }
    )


def targets_for(
    target_sets: Mapping[str, ScenarioTargetSet],
    preset_or_name: Preset | str,
) -> ScenarioTargetSet:
    """Look up the advertised (label, variable) targets for one scenario preset."""
    name = (
        preset_or_name.name
        if isinstance(preset_or_name, Preset)
        else preset_or_name
    )
    try:
        return target_sets[name]
    except KeyError:
        raise KeyError(
            f"no advertised scenario targets registered for {name!r}"
        ) from None


__all__ = [
    "COST_PER_TOKEN_TARGET",
    "DENSE_TRAINING_COST_TARGETS",
    "EUV_TIN120_SOURCE_TARGETS",
    "ScenarioTargetSet",
    "build_scenario_target_sets",
    "targets_for",
]
