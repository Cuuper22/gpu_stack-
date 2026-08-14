"""Experiment E001: can adaptive training survive beyond one datacenter?

This is a virtual mechanics screen, not a real training run. Timing,
traffic, power, and failure behavior all come from explicit
virtual-datacenter events, so the engine can compare synchronization
policies mechanically. What it cannot do is measure learning: the learning
response is an unfitted sensitivity prior seeded by observations, which
leaves the learning and time-to-target falsifiers unresolved. A virtual
result is not validation.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Optional, Sequence, Tuple

from .multisite import (
    ConfigurationIntervention,
    DatacenterResult,
    MembershipIntervention,
    Site,
    SyncCadence,
    SyncCadenceIntervention,
    VirtualDatacenter,
    WANLink,
    VisibleDatacenterState,
)
from .protocols import (
    ComparisonOperator,
    EvidenceRequirementSpec,
    ExperimentProtocol,
    ExperimentRunArtifact,
    ExperimentStage,
    FalsifierSpec,
    MetricSpec,
)
from .temporal import duration_ns_for_rate


E001_RESULT_SCHEMA = "gpu-stack.e001-comparison.v1"
E001_ENGINE_ID = "gpu-stack.e001-mechanics.v1"


def e001_engine_source_hash() -> str:
    """Hash the source modules that define E001 mechanics and conclusions."""

    root = Path(__file__).resolve().parent
    digest = hashlib.sha256()
    for name in ("protocols.py", "temporal.py", "multisite.py", "e001.py"):
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update((root / name).read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


E001_PROTOCOL = ExperimentProtocol(
    experiment_id="E001",
    title="Beyond One Datacenter",
    question=(
        "Can frontier pretraining span heterogeneous, intermittently powered "
        "datacenters without surrendering centralized learning efficiency?"
    ),
    hypothesis=(
        "Adaptive consistency, communication topology, parallelism, and site "
        "membership retain at least 95% of centralized loss progress per FLOP, "
        "use at least 10 times fewer inter-site bytes than synchronous global "
        "all-reduce, and finish sooner under site interruptions."
    ),
    baselines=(
        "single-site-centralized-equivalent-capacity",
        "synchronous-global-all-reduce",
        "fixed-local-update-cadence",
        "fixed-sparse-gossip",
        "power-aware-migration-without-learning-adaptation",
        "future-trace-oracle-regret-bound",
    ),
    metrics=(
        MetricSpec(
            "progress_per_flop_ratio",
            "1",
            "Calibrated learning progress per FLOP relative to synchronous updates.",
            True,
        ),
        MetricSpec(
            "collective_payload_byte_fraction",
            "1",
            "Policy inter-site collective payload divided by the synchronous baseline.",
            True,
        ),
        MetricSpec(
            "completion_time_ratio",
            "1",
            "Calibrated time-to-target divided by synchronous time-to-target.",
            True,
        ),
        MetricSpec(
            "facility_energy_to_target_j",
            "J",
            "Full-boundary facility energy to the held-out learning target.",
            True,
        ),
        MetricSpec(
            "peak_wan_demand_bytes_per_second",
            "byte/s",
            "Peak aggregate WAN demand over the complete collective algorithm.",
            True,
        ),
        MetricSpec(
            "unacceptable_quality_probability",
            "1",
            "Probability of divergence or unacceptable held-out model quality.",
            True,
        ),
        MetricSpec(
            "policy_decision_regret",
            "1",
            "Decision regret relative to the frozen future-trace oracle.",
            True,
        ),
        MetricSpec(
            "nominal_90_interval_coverage",
            "1",
            "Held-out coverage of nominal 90% prediction intervals.",
            True,
        ),
        MetricSpec(
            "modeled_base_and_compute_energy_j",
            "J",
            "Site base energy plus accelerator compute energy; dynamic network, "
            "checkpoint, storage, host, and cooling energy are excluded.",
        ),
        MetricSpec("peak_allocated_power_w", "W", "Peak allocated IT power."),
        MetricSpec(
            "modeled_collective_payload_link_bytes",
            "byte",
            "Sum of gradient payload bytes placed on modeled inter-site links.",
        ),
        MetricSpec("state_transfer_bytes", "byte", "Inter-site state migration."),
        MetricSpec("checkpoint_bytes", "byte", "Checkpoint traffic."),
    ),
    falsifiers=(
        FalsifierSpec(
            "e001-progress",
            "progress_per_flop_ratio",
            ComparisonOperator.GE,
            0.95,
            description="Less than 95% centralized progress per FLOP falsifies E001.",
        ),
        FalsifierSpec(
            "e001-wan",
            "collective_payload_byte_fraction",
            ComparisonOperator.LE,
            0.1,
            description=(
                "More than 10% of synchronous collective payload fails the "
                "preregistered 10x reduction threshold."
            ),
        ),
        FalsifierSpec(
            "e001-time",
            "completion_time_ratio",
            ComparisonOperator.LE,
            1.0,
            description="Slower held-out time-to-target falsifies E001.",
        ),
    ),
    evidence_requirements=(
        EvidenceRequirementSpec(
            requirement_id="e001-baseline-vector-superiority",
            kind="baseline_vector_dominance",
            description=(
                "Adaptive control must beat every fixed baseline on the complete "
                "primary outcome vector rather than one favorable scalar."
            ),
            earliest_resolvable_stage=ExperimentStage.CONTROLLED,
            required_metrics=(
                "progress_per_flop_ratio",
                "collective_payload_byte_fraction",
                "completion_time_ratio",
                "facility_energy_to_target_j",
                "peak_wan_demand_bytes_per_second",
                "unacceptable_quality_probability",
                "policy_decision_regret",
                "nominal_90_interval_coverage",
            ),
            required_panels=(
                "model family",
                "accelerator family",
                "WAN regime",
                "power stress regime",
            ),
            comparison_baselines=(
                "single-site-centralized-equivalent-capacity",
                "synchronous-global-all-reduce",
                "fixed-local-update-cadence",
                "fixed-sparse-gossip",
                "power-aware-migration-without-learning-adaptation",
            ),
            acceptance_rule=(
                "No fixed baseline may match the adaptive policy across the "
                "complete preregistered primary vector within uncertainty."
            ),
            evidence_boundary="Requires held-out controlled training evidence.",
        ),
        EvidenceRequirementSpec(
            requirement_id="e001-heldout-learning-transfer",
            kind="directional_real_world_transfer",
            description=(
                "Learning progress, quality risk, and time-to-target must transfer "
                "from calibration runs to held-out multi-site training."
            ),
            earliest_resolvable_stage=ExperimentStage.CONTROLLED,
            required_metrics=(
                "progress_per_flop_ratio",
                "completion_time_ratio",
                "unacceptable_quality_probability",
                "nominal_90_interval_coverage",
            ),
            required_panels=(
                "30B to 100B-plus model",
                "held-out site",
                "held-out optimizer and workload",
            ),
            acceptance_rule=(
                "All learning metrics must satisfy their preregistered bounds on "
                "held-out runs with calibrated interval coverage."
            ),
            evidence_boundary=(
                "A virtual prior or 360M one-step-delay paper cannot resolve this."
            ),
        ),
        EvidenceRequirementSpec(
            requirement_id="e001-full-boundary-nonreversal",
            kind="accounting_nonreversal",
            description=(
                "The result must survive full time, energy, recovery, and cost "
                "accounting rather than shifting work outside the window."
            ),
            earliest_resolvable_stage=ExperimentStage.CONTROLLED,
            required_metrics=(
                "completion_time_ratio",
                "facility_energy_to_target_j",
            ),
            required_panels=("normal operation", "interruption", "recovery"),
            acceptance_rule=(
                "Deferred and replayed work must not reverse the claimed benefit."
            ),
            evidence_boundary=(
                "Requires metered facility energy and complete recovery accounting."
            ),
        ),
        EvidenceRequirementSpec(
            requirement_id="e001-joint-mechanism-completeness",
            kind="mechanism_completeness",
            description=(
                "The tested policy must expose cadence, topology, pipeline delay, "
                "optimizer correction, parallelism, placement, and membership."
            ),
            earliest_resolvable_stage=ExperimentStage.VIRTUAL,
            required_metrics=("policy_decision_regret",),
            required_panels=(
                "cadence",
                "topology",
                "pipeline delay",
                "optimizer correction",
                "parallelism",
                "placement",
                "membership",
            ),
            acceptance_rule=(
                "Every mechanism in the hypothesis must be executable or the run "
                "must remain an explicitly partial mechanics screen."
            ),
            evidence_boundary="The current E001 runner implements cadence only.",
        ),
        EvidenceRequirementSpec(
            requirement_id="e001-baseline-completeness",
            kind="baseline_completeness",
            description="Every preregistered baseline must execute on matched traces.",
            earliest_resolvable_stage=ExperimentStage.VIRTUAL,
            required_metrics=("policy_decision_regret",),
            comparison_baselines=(
                "single-site-centralized-equivalent-capacity",
                "synchronous-global-all-reduce",
                "fixed-local-update-cadence",
                "fixed-sparse-gossip",
                "power-aware-migration-without-learning-adaptation",
                "future-trace-oracle-regret-bound",
            ),
            acceptance_rule=(
                "No baseline may be omitted from a superiority or regret claim."
            ),
            evidence_boundary="The current screen implements two baselines only.",
        ),
        EvidenceRequirementSpec(
            requirement_id="e001-heldout-panel-completeness",
            kind="panel_completeness",
            description=(
                "The confirmatory evidence must span every frozen transfer panel."
            ),
            earliest_resolvable_stage=ExperimentStage.CONTROLLED,
            required_metrics=("nominal_90_interval_coverage",),
            required_panels=(
                "site",
                "accelerator family",
                "model family",
                "WAN regime",
                "power stress regime",
            ),
            acceptance_rule=(
                "All named panels must be present before a transfer conclusion."
            ),
            evidence_boundary="Virtual scenario coverage is not a held-out panel.",
        ),
        EvidenceRequirementSpec(
            requirement_id="e001-collective-and-failure-model-admission",
            kind="model_admission",
            description=(
                "Traffic and interruption claims require algorithm-specific "
                "collective bytes plus preemption, lost-work, and recovery semantics."
            ),
            earliest_resolvable_stage=ExperimentStage.VIRTUAL,
            required_metrics=(
                "collective_payload_byte_fraction",
                "peak_wan_demand_bytes_per_second",
                "completion_time_ratio",
            ),
            required_panels=(
                "collective algorithm",
                "mid-operation failure",
                "checkpoint recovery",
            ),
            acceptance_rule=(
                "The complete modeled boundaries must pass admission before their "
                "metrics can support E001."
            ),
            evidence_boundary=(
                "Payload-per-link and whole-operation postponement are insufficient."
            ),
        ),
    ),
    independent_variables=(
        "site membership",
        "local update cadence",
        "WAN topology and bandwidth",
        "parallelism layout",
        "power availability",
        "failure process",
        "optimizer delay response",
    ),
    held_out_dimensions=(
        "site",
        "accelerator family",
        "model family",
        "WAN regime",
        "power stress regime",
    ),
    real_validation_requirements=(
        "at least three geographically separate clusters",
        "controlled bandwidth and site-power perturbations",
        "identical data and evaluation accounting",
        "controlled 7B to 30B learning-transfer experiments",
        "30B to 100B-plus multi-week validation run",
    ),
    seed_policy="publish all fixed seeds and repeat every stochastic calibration",
    source_window="2026-04-13/2026-07-12",
    notes=(
        "The virtual datacenter can screen but cannot validate convergence.",
        "Learning response must be calibrated from separate observations.",
    ),
)


class E001PolicyKind(str, Enum):
    SYNCHRONOUS = "synchronous"
    FIXED_LOCAL = "fixed_local"
    ADAPTIVE_CADENCE = "adaptive_cadence"


@dataclass(frozen=True)
class LearningProgressPrior:
    """Unvalidated screening prior for delayed-synchronization learning response.

    The seed observations report final validation loss under exactly one step
    of delay.  They do not identify progress per FLOP or behavior at longer
    local-update intervals, so this object must not be presented as a fitted
    calibration or used to resolve E001's learning falsifiers.
    """

    prior_id: str
    seed_observation_ids: Tuple[str, ...]
    staleness_sensitivity: float
    staleness_exponent: float = 1.0
    sensitivity_scale: float = 0.0
    optimizer: str = "unspecified"
    model_family: str = "unspecified"
    source: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.prior_id, str) or not self.prior_id.strip():
            raise ValueError("learning prior requires a non-blank id")
        seed_observation_ids = tuple(self.seed_observation_ids)
        if (
            not seed_observation_ids
            or any(
                not isinstance(item, str) or not item.strip()
                for item in seed_observation_ids
            )
        ):
            raise ValueError("learning prior requires an id and seed observations")
        seed_observation_ids = tuple(item.strip() for item in seed_observation_ids)
        if len(set(seed_observation_ids)) != len(seed_observation_ids):
            raise ValueError("learning-prior seed observation ids must be unique")
        for name in (
            "staleness_sensitivity",
            "staleness_exponent",
            "sensitivity_scale",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"learning prior {name} must be a real number")
            object.__setattr__(self, name, float(value))
        if self.staleness_sensitivity < 0 or not math.isfinite(self.staleness_sensitivity):
            raise ValueError("staleness_sensitivity must be finite and nonnegative")
        if self.staleness_exponent <= 0 or not math.isfinite(self.staleness_exponent):
            raise ValueError("staleness_exponent must be finite and positive")
        if self.sensitivity_scale < 0 or not math.isfinite(
            self.sensitivity_scale
        ):
            raise ValueError("sensitivity scale must be finite and nonnegative")
        for name in ("optimizer", "model_family", "source"):
            value = getattr(self, name)
            if not isinstance(value, str):
                raise TypeError(f"learning prior {name} must be a string")
            object.__setattr__(self, name, value.strip())
        object.__setattr__(self, "prior_id", self.prior_id.strip())
        object.__setattr__(self, "seed_observation_ids", seed_observation_ids)

    def screening_progress_ratio(
        self, local_steps: float, sensitivity_multiplier: float = 0.0
    ) -> float:
        """Return one explicitly hypothetical sensitivity scenario."""
        if local_steps < 1:
            raise ValueError("local_steps must be at least one")
        sensitivity = max(
            0.0,
            self.staleness_sensitivity
            + sensitivity_multiplier * self.sensitivity_scale,
        )
        delay = (local_steps - 1.0) ** self.staleness_exponent
        return 1.0 / (1.0 + sensitivity * delay)

    def to_dict(self) -> dict[str, object]:
        return {
            "prior_id": self.prior_id,
            "seed_observation_ids": list(self.seed_observation_ids),
            "staleness_sensitivity": self.staleness_sensitivity,
            "staleness_exponent": self.staleness_exponent,
            "sensitivity_scale": self.sensitivity_scale,
            "optimizer": self.optimizer,
            "model_family": self.model_family,
            "source": self.source,
            "evidence_status": "screening_prior_not_fitted",
        }


# Compatibility name for early callers.  The canonical type and serialized
# evidence status deliberately use "prior", because no fitted calibration
# exists yet.
LearningProgressCalibration = LearningProgressPrior


@dataclass(frozen=True)
class SiteOutage:
    event_id: str
    site_id: str
    failure_start_ns: int
    recovery_ns: int
    cause: str = "unspecified"

    def __post_init__(self) -> None:
        if not self.event_id.strip() or not self.site_id.strip():
            raise ValueError("outage event and site ids must be non-blank")
        if self.failure_start_ns < 0 or self.recovery_ns <= self.failure_start_ns:
            raise ValueError(
                "outage requires nonnegative failure_start_ns and an absolute "
                "recovery_ns later than the failure"
            )

    @property
    def duration_ns(self) -> int:
        return self.recovery_ns - self.failure_start_ns

    def to_dict(self) -> dict[str, object]:
        return {
            "event_id": self.event_id,
            "site_id": self.site_id,
            "failure_start_ns": self.failure_start_ns,
            "recovery_ns": self.recovery_ns,
            "duration_ns": self.duration_ns,
            "cause": self.cause,
        }


@dataclass(frozen=True)
class E001Scenario:
    scenario_id: str
    sites: Tuple[Site, ...]
    links: Tuple[WANLink, ...]
    total_steps: int
    flops_per_global_step: float
    gradient_bytes: int
    checkpoint_bytes: int
    checkpoint_interval_steps: int
    learning_prior: LearningProgressPrior
    evaluation_observation_ids: Tuple[str, ...]
    fixed_local_steps: int = 8
    adaptive_min_local_steps: int = 1
    adaptive_max_local_steps: int = 64
    outages: Tuple[SiteOutage, ...] = ()
    assumptions: Tuple[str, ...] = ()
    provenance: Tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.scenario_id.strip():
            raise ValueError("E001 scenario_id must be non-blank")
        if len(self.sites) < 2:
            raise ValueError("E001 requires at least two sites")
        site_ids = [site.site_id for site in self.sites]
        if len(site_ids) != len(set(site_ids)):
            raise ValueError("E001 site ids must be unique")
        if not self.links:
            raise ValueError("E001 requires at least one WAN link")
        known_sites = set(site_ids)
        for link in self.links:
            if {link.site_a, link.site_b} - known_sites:
                raise ValueError(f"link {link.link_id!r} references an unknown site")
        if self.total_steps <= 0 or self.flops_per_global_step <= 0:
            raise ValueError("E001 work and step counts must be positive")
        if self.gradient_bytes <= 0 or self.checkpoint_bytes < 0:
            raise ValueError("E001 byte counts are invalid")
        if self.checkpoint_interval_steps <= 0:
            raise ValueError("checkpoint interval must be positive")
        if not 1 <= self.adaptive_min_local_steps <= self.adaptive_max_local_steps:
            raise ValueError("adaptive local-step bounds are invalid")
        if self.fixed_local_steps < 1:
            raise ValueError("fixed_local_steps must be positive")
        if not isinstance(self.learning_prior, LearningProgressPrior):
            raise TypeError("learning_prior must be a LearningProgressPrior")
        overlap = set(self.learning_prior.seed_observation_ids) & set(
            self.evaluation_observation_ids
        )
        if overlap:
            raise ValueError(
                f"learning-prior seed and evaluation observations overlap: {sorted(overlap)}"
            )
        for outage in self.outages:
            if outage.site_id not in known_sites:
                raise ValueError(f"outage references unknown site {outage.site_id!r}")
        object.__setattr__(self, "sites", tuple(self.sites))
        object.__setattr__(self, "links", tuple(self.links))
        object.__setattr__(self, "outages", tuple(self.outages))
        object.__setattr__(self, "assumptions", tuple(self.assumptions))
        object.__setattr__(self, "provenance", tuple(self.provenance))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "E001Scenario":
        prior_data = data.get("learning_prior", data.get("learning_calibration"))
        if prior_data is None:
            raise ValueError("E001 scenario requires learning_prior")
        normalized_prior = dict(prior_data)
        normalized_prior.pop("evidence_status", None)
        if "prior_id" not in normalized_prior and "calibration_id" in normalized_prior:
            normalized_prior["prior_id"] = normalized_prior.pop("calibration_id")
        if (
            "seed_observation_ids" not in normalized_prior
            and "observation_ids" in normalized_prior
        ):
            normalized_prior["seed_observation_ids"] = normalized_prior.pop(
                "observation_ids"
            )
        if (
            "sensitivity_scale" not in normalized_prior
            and "sensitivity_standard_deviation" in normalized_prior
        ):
            normalized_prior["sensitivity_scale"] = normalized_prior.pop(
                "sensitivity_standard_deviation"
            )
        learning_prior = LearningProgressPrior(**normalized_prior)
        return cls(
            scenario_id=data["scenario_id"],
            sites=tuple(Site(**item) for item in data["sites"]),
            links=tuple(WANLink(**item) for item in data["links"]),
            total_steps=int(data["total_steps"]),
            flops_per_global_step=float(data["flops_per_global_step"]),
            gradient_bytes=int(data["gradient_bytes"]),
            checkpoint_bytes=int(data.get("checkpoint_bytes", 0)),
            checkpoint_interval_steps=int(data.get("checkpoint_interval_steps", 100)),
            learning_prior=learning_prior,
            evaluation_observation_ids=tuple(data["evaluation_observation_ids"]),
            fixed_local_steps=int(data.get("fixed_local_steps", 8)),
            adaptive_min_local_steps=int(data.get("adaptive_min_local_steps", 1)),
            adaptive_max_local_steps=int(data.get("adaptive_max_local_steps", 64)),
            outages=tuple(
                SiteOutage(
                    **{
                        key: value
                        for key, value in item.items()
                        if key != "duration_ns"
                    }
                )
                for item in data.get("outages", ())
            ),
            assumptions=tuple(data.get("assumptions", ())),
            provenance=tuple(data.get("provenance", ())),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def from_json(cls, text: str) -> "E001Scenario":
        return cls.from_dict(json.loads(text))

    def to_dict(self) -> dict[str, object]:
        return {
            "scenario_id": self.scenario_id,
            "sites": [site.to_dict() for site in self.sites],
            "links": [link.to_dict() for link in self.links],
            "total_steps": self.total_steps,
            "flops_per_global_step": self.flops_per_global_step,
            "gradient_bytes": self.gradient_bytes,
            "checkpoint_bytes": self.checkpoint_bytes,
            "checkpoint_interval_steps": self.checkpoint_interval_steps,
            "learning_prior": self.learning_prior.to_dict(),
            "evaluation_observation_ids": list(self.evaluation_observation_ids),
            "fixed_local_steps": self.fixed_local_steps,
            "adaptive_min_local_steps": self.adaptive_min_local_steps,
            "adaptive_max_local_steps": self.adaptive_max_local_steps,
            "outages": [outage.to_dict() for outage in self.outages],
            "assumptions": list(self.assumptions),
            "provenance": list(self.provenance),
            "metadata": dict(self.metadata),
        }

    def canonical_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )

    @property
    def scenario_hash(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AdaptiveCadencePolicy:
    """Observable-only controller over completed-cycle WAN duty.

    Membership actions remain in the policy boundary for future persistent
    health epochs, but this first screen only exercises cadence adaptation.
    """

    min_local_steps: int
    max_local_steps: int
    high_link_pressure: float = 0.45
    low_link_pressure: float = 0.20

    def decide(self, state: VisibleDatacenterState) -> Sequence[object]:
        actions: list[object] = []
        for site in state.sites:
            if site.active and not site.healthy:
                actions.append(
                    MembershipIntervention(
                        site.site_id, False, "observed site health failure"
                    )
                )
            elif not site.active and site.healthy:
                actions.append(
                    MembershipIntervention(
                        site.site_id, True, "observed site recovery"
                    )
                )

        visible = dict(state.configuration)
        if visible.get("last_sync_observed") is not True:
            return tuple(actions)
        pressure_value = visible.get("last_collective_phase_fraction")
        if not isinstance(pressure_value, (int, float)) or isinstance(
            pressure_value, bool
        ):
            return tuple(actions)
        pressure = float(pressure_value)
        if not math.isfinite(pressure) or not 0.0 <= pressure <= 1.0:
            return tuple(actions)

        current = state.sync_cadence.local_steps
        target = current
        if pressure >= self.high_link_pressure:
            target = min(self.max_local_steps, max(current + 1, current * 2))
        elif pressure <= self.low_link_pressure:
            target = max(self.min_local_steps, current // 2)
        if target != current:
            actions.append(
                SyncCadenceIntervention(
                    SyncCadence(
                        local_steps=target,
                        topology=(
                            "global_all_reduce"
                            if target == 1
                            else "periodic_local_updates"
                        ),
                        pipeline_depth=state.sync_cadence.pipeline_depth,
                        max_update_staleness=target - 1,
                    ),
                    f"completed-cycle communication phase fraction {pressure:.6f}",
                )
            )
        actions.append(
            ConfigurationIntervention.create(
                {"last_sync_observed": False},
                "consume completed-cycle WAN observation",
            )
        )
        return tuple(actions)


AdaptiveConsistencyPolicy = AdaptiveCadencePolicy


@dataclass(frozen=True)
class E001SyncCycle:
    """One causally ordered compute window followed by synchronization."""

    cycle_index: int
    start_step: int
    end_step: int
    selected_local_steps: int
    completed_local_steps: int
    start_ns: int
    end_ns: int
    compute_elapsed_ns: int
    collective_elapsed_ns: int
    collective_phase_fraction: float
    outage_event_ids: Tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "cycle_index": self.cycle_index,
            "start_step": self.start_step,
            "end_step": self.end_step,
            "selected_local_steps": self.selected_local_steps,
            "completed_local_steps": self.completed_local_steps,
            "start_ns": self.start_ns,
            "end_ns": self.end_ns,
            "elapsed_ns": self.end_ns - self.start_ns,
            "compute_elapsed_ns": self.compute_elapsed_ns,
            "collective_elapsed_ns": self.collective_elapsed_ns,
            "collective_phase_fraction": self.collective_phase_fraction,
            "outage_event_ids": list(self.outage_event_ids),
        }


@dataclass(frozen=True)
class E001MechanicsMetrics:
    """Mechanics aggregates over successive decision epochs."""

    compute_flops: float
    inter_site_collective_bytes: float
    state_transfer_bytes: float
    checkpoint_bytes: float
    accelerator_time_ns: float
    modeled_base_and_compute_energy_j: float
    peak_allocated_power_w: float

    def to_dict(self) -> dict[str, float]:
        return {
            "compute_flops": self.compute_flops,
            "inter_site_collective_bytes": self.inter_site_collective_bytes,
            "state_transfer_bytes": self.state_transfer_bytes,
            "checkpoint_bytes": self.checkpoint_bytes,
            "accelerator_time_ns": self.accelerator_time_ns,
            "modeled_base_and_compute_energy_j": (
                self.modeled_base_and_compute_energy_j
            ),
            "peak_allocated_power_w": self.peak_allocated_power_w,
        }


@dataclass(frozen=True)
class E001Run:
    policy_kind: E001PolicyKind
    initial_local_steps: int
    final_local_steps: int
    epochs: Tuple[DatacenterResult, ...]
    sync_cycles: Tuple[E001SyncCycle, ...]
    metrics: E001MechanicsMetrics
    prior_screening_progress_ratio: float
    pessimistic_sensitivity_progress_ratio: float
    prior_projected_time_to_equivalent_progress_ns: float

    @property
    def local_steps(self) -> int:
        """Compatibility alias for the initial cadence; history is authoritative."""
        return self.initial_local_steps

    @property
    def start_ns(self) -> int:
        return self.epochs[0].start_ns

    @property
    def end_ns(self) -> int:
        return self.epochs[-1].end_ns

    @property
    def elapsed_ns(self) -> int:
        return self.end_ns - self.start_ns

    def to_dict(self, *, include_traces: bool = False) -> dict[str, object]:
        result: dict[str, object] = {
            "policy": self.policy_kind.value,
            "initial_local_steps": self.initial_local_steps,
            "final_local_steps": self.final_local_steps,
            "epoch_count": len(self.epochs),
            "start_ns": self.start_ns,
            "end_ns": self.end_ns,
            "elapsed_ns": self.elapsed_ns,
            "metrics": self.metrics.to_dict(),
            "sync_cycles": [cycle.to_dict() for cycle in self.sync_cycles],
            "learning_prior": {
                "evidence_status": "screening_prior_not_fitted",
                "prior_screening_progress_ratio": (
                    self.prior_screening_progress_ratio
                ),
                "pessimistic_sensitivity_progress_ratio": (
                    self.pessimistic_sensitivity_progress_ratio
                ),
                "prior_projected_time_to_equivalent_progress_ns": (
                    self.prior_projected_time_to_equivalent_progress_ns
                ),
            },
        }
        if include_traces:
            result["epochs"] = [epoch.to_dict() for epoch in self.epochs]
        return result


@dataclass(frozen=True)
class E001Comparison:
    scenario: E001Scenario
    protocol_hash: str
    engine_source_hash: str
    baseline: E001Run
    candidates: Tuple[E001Run, ...]
    artifacts: Tuple[ExperimentRunArtifact, ...]

    @property
    def scenario_id(self) -> str:
        return self.scenario.scenario_id

    def to_dict(self, include_traces: bool = False) -> dict[str, object]:
        payload = {
            "schema": E001_RESULT_SCHEMA,
            "scenario_id": self.scenario_id,
            "scenario_hash": self.scenario.scenario_hash,
            "scenario": self.scenario.to_dict(),
            "protocol": E001_PROTOCOL.to_dict(),
            "protocol_hash": self.protocol_hash,
            "engine": {
                "engine_id": E001_ENGINE_ID,
                "source_sha256": self.engine_source_hash,
            },
            "traces_included": include_traces,
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "runs": [
                run.to_dict(include_traces=include_traces)
                for run in (self.baseline,) + self.candidates
            ],
        }
        payload["artifact_sha256"] = hashlib.sha256(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()
        return payload

    def to_json(self, include_traces: bool = False) -> str:
        return json.dumps(
            self.to_dict(include_traces=include_traces),
            indent=2,
            sort_keys=True,
        )


def _initial_local_steps(scenario: E001Scenario, kind: E001PolicyKind) -> int:
    if kind is E001PolicyKind.SYNCHRONOUS:
        return 1
    if kind is E001PolicyKind.FIXED_LOCAL:
        return scenario.fixed_local_steps
    total_compute_rate = sum(
        site.accelerator_count * site.accelerator_flops_per_second
        for site in scenario.sites
    )
    step_seconds = scenario.flops_per_global_step / total_compute_rate
    available_links = [link for link in scenario.links if link.available]
    if not available_links:
        return scenario.adaptive_max_local_steps
    bottleneck_sync_seconds = max(
        link.latency_ns / 1e9
        + scenario.gradient_bytes / link.bandwidth_bytes_per_second
        for link in available_links
    )
    ratio = max(1, math.ceil(bottleneck_sync_seconds / step_seconds))
    return min(
        scenario.adaptive_max_local_steps,
        max(scenario.adaptive_min_local_steps, ratio),
    )


def _queue_outages_for_window(
    datacenter: VirtualDatacenter,
    scenario: E001Scenario,
    consumed: set[str],
    predicted_end_ns: int,
) -> Tuple[str, ...]:
    """Queue only exogenous outages that can affect the current operation.

    The policy acts before this function is called, so future outage IDs never
    appear in its visible queued-event state.  Recovery timestamps may extend
    the current window and thereby expose a later outage; the loop expands the
    window until that cascade is closed.
    """

    start_ns = datacenter.timestamp_ns
    window_end_ns = predicted_end_ns
    queued: list[str] = []
    while True:
        newly_queued = False
        for outage in sorted(
            scenario.outages,
            key=lambda item: (item.failure_start_ns, item.event_id),
        ):
            if outage.event_id in consumed:
                continue
            if outage.failure_start_ns < start_ns:
                raise RuntimeError(
                    f"outage {outage.event_id!r} was skipped by a decision epoch"
                )
            if not start_ns <= outage.failure_start_ns < window_end_ns:
                continue
            datacenter.schedule_site_outage(
                outage.event_id,
                outage.site_id,
                outage.failure_start_ns,
                outage.recovery_ns,
                cause=outage.cause,
            )
            consumed.add(outage.event_id)
            queued.append(outage.event_id)
            operation_duration_ns = predicted_end_ns - start_ns
            window_end_ns = max(
                window_end_ns,
                outage.recovery_ns + operation_duration_ns,
            )
            newly_queued = True
        if not newly_queued:
            return tuple(queued)


def _run_compute_epoch(
    datacenter: VirtualDatacenter,
    scenario: E001Scenario,
    policy_kind: E001PolicyKind,
    step: int,
    consumed_outages: set[str],
) -> tuple[DatacenterResult, Tuple[str, ...]]:
    state = datacenter.observe()
    sites_by_id = {site.site_id: site for site in scenario.sites}
    active = tuple(state.site(site_id) for site_id in state.membership)
    if not active:
        raise RuntimeError("E001 has no active site available for compute")
    rates = {
        item.site_id: (
            item.effective_accelerators
            * float(sites_by_id[item.site_id].accelerator_flops_per_second)
        )
        for item in active
    }
    total_rate = sum(rates.values())
    if total_rate <= 0:
        raise RuntimeError("E001 active membership has zero compute rate")

    expected_duration_ns = 0
    for item in active:
        site_work = scenario.flops_per_global_step * rates[item.site_id] / total_rate
        event = datacenter.schedule_compute(
            f"{policy_kind.value}.step.{step}.compute.{item.site_id}",
            item.site_id,
            site_work,
            item.effective_accelerators,
            metadata={
                "step": step,
                "selected_local_steps": state.sync_cadence.local_steps,
            },
        )
        expected_duration_ns = max(expected_duration_ns, event.duration_ns)
    outage_ids = _queue_outages_for_window(
        datacenter,
        scenario,
        consumed_outages,
        datacenter.timestamp_ns + expected_duration_ns,
    )
    return datacenter.run(), outage_ids


def _run_collective_epoch(
    datacenter: VirtualDatacenter,
    scenario: E001Scenario,
    policy_kind: E001PolicyKind,
    step: int,
    consumed_outages: set[str],
) -> tuple[DatacenterResult, Tuple[str, ...]]:
    state = datacenter.observe()
    active_ids = set(state.membership)
    sites_by_id = {site.site_id: site for site in scenario.sites}
    active_links = tuple(
        link for link in scenario.links
        if link.available and {link.site_a, link.site_b} <= active_ids
    )
    if not active_links:
        raise RuntimeError("E001 synchronization has no active inter-site link")
    expected_duration_ns = 0
    for link in active_links:
        rate = min(
            float(link.bandwidth_bytes_per_second),
            float(sites_by_id[link.site_a].state_transfer_bandwidth_bytes_per_second),
            float(sites_by_id[link.site_b].state_transfer_bandwidth_bytes_per_second),
        )
        event = datacenter.schedule_collective(
            f"{policy_kind.value}.step.{step}.sync.{link.link_id}",
            scenario.gradient_bytes,
            link_id=link.link_id,
            metadata={
                "step": step,
                "selected_local_steps": state.sync_cadence.local_steps,
            },
        )
        expected_duration_ns = max(expected_duration_ns, event.duration_ns)
        expected_duration_ns = max(
            expected_duration_ns,
            link.latency_ns
            + duration_ns_for_rate(scenario.gradient_bytes, rate),
        )
    outage_ids = _queue_outages_for_window(
        datacenter,
        scenario,
        consumed_outages,
        datacenter.timestamp_ns + expected_duration_ns,
    )
    return datacenter.run(), outage_ids


def _run_checkpoint_epoch(
    datacenter: VirtualDatacenter,
    scenario: E001Scenario,
    policy_kind: E001PolicyKind,
    step: int,
    consumed_outages: set[str],
) -> tuple[DatacenterResult, Tuple[str, ...]]:
    state = datacenter.observe()
    sites_by_id = {site.site_id: site for site in scenario.sites}
    active = tuple(state.site(site_id) for site_id in state.membership)
    total_accelerators = sum(item.effective_accelerators for item in active)
    if total_accelerators <= 0:
        raise RuntimeError("E001 checkpoint has no active accelerator state")
    expected_duration_ns = 0
    for item in active:
        size = max(
            1,
            round(
                scenario.checkpoint_bytes
                * item.effective_accelerators
                / total_accelerators
            ),
        )
        event = datacenter.schedule_checkpoint(
            f"{policy_kind.value}.step.{step}.checkpoint.{item.site_id}",
            item.site_id,
            size,
            metadata={"step": step},
        )
        expected_duration_ns = max(expected_duration_ns, event.duration_ns)
    outage_ids = _queue_outages_for_window(
        datacenter,
        scenario,
        consumed_outages,
        datacenter.timestamp_ns + expected_duration_ns,
    )
    return datacenter.run(), outage_ids


def _aggregate_metrics(
    epochs: Sequence[DatacenterResult],
) -> E001MechanicsMetrics:
    if not epochs:
        raise ValueError("E001 run requires at least one decision epoch")
    return E001MechanicsMetrics(
        compute_flops=sum(float(epoch.metrics.compute_flops) for epoch in epochs),
        inter_site_collective_bytes=sum(
            float(epoch.metrics.inter_site_collective_bytes) for epoch in epochs
        ),
        state_transfer_bytes=sum(
            float(epoch.metrics.state_transfer_bytes) for epoch in epochs
        ),
        checkpoint_bytes=sum(
            float(epoch.metrics.checkpoint_bytes) for epoch in epochs
        ),
        accelerator_time_ns=sum(
            float(epoch.metrics.accelerator_time_ns) for epoch in epochs
        ),
        modeled_base_and_compute_energy_j=sum(
            epoch.metrics.modeled_base_and_compute_energy_j for epoch in epochs
        ),
        peak_allocated_power_w=max(
            float(epoch.metrics.peak_allocated_power_w) for epoch in epochs
        ),
    )


def _schedule_run(
    scenario: E001Scenario,
    policy_kind: E001PolicyKind,
) -> E001Run:
    initial_local_steps = _initial_local_steps(scenario, policy_kind)
    cadence = SyncCadence(
        local_steps=initial_local_steps,
        topology=(
            "global_all_reduce"
            if initial_local_steps == 1
            else "periodic_local_updates"
        ),
        pipeline_depth=0,
        max_update_staleness=initial_local_steps - 1,
    )
    datacenter = VirtualDatacenter(
        scenario.sites,
        scenario.links,
        sync_cadence=cadence,
        configuration={
            "experiment_id": "E001",
            "policy": policy_kind.value,
            "last_sync_observed": False,
        },
    )
    policy = (
        AdaptiveCadencePolicy(
            scenario.adaptive_min_local_steps,
            scenario.adaptive_max_local_steps,
        )
        if policy_kind is E001PolicyKind.ADAPTIVE_CADENCE
        else None
    )
    epochs: list[DatacenterResult] = []
    sync_cycles: list[E001SyncCycle] = []
    consumed_outages: set[str] = set()
    steps_since_sync = 0
    cycle_start_step = 1
    cycle_start_ns = datacenter.timestamp_ns
    cycle_compute_elapsed_ns = 0
    cycle_outage_ids: list[str] = []
    cycle_selected_local_steps = initial_local_steps
    prior_progress_weighted = 0.0
    pessimistic_progress_weighted = 0.0

    for step in range(1, scenario.total_steps + 1):
        if policy is not None:
            datacenter.apply_policy(policy)
        state = datacenter.observe()
        if steps_since_sync == 0:
            cycle_start_step = step
            cycle_start_ns = datacenter.timestamp_ns
            cycle_selected_local_steps = state.sync_cadence.local_steps

        compute_result, outage_ids = _run_compute_epoch(
            datacenter,
            scenario,
            policy_kind,
            step,
            consumed_outages,
        )
        epochs.append(compute_result)
        cycle_compute_elapsed_ns += compute_result.elapsed_ns
        cycle_outage_ids.extend(outage_ids)
        steps_since_sync += 1

        current_cadence = datacenter.observe().sync_cadence.local_steps
        should_sync = (
            steps_since_sync >= current_cadence
            or step == scenario.total_steps
        )
        if should_sync:
            collective_result, sync_outages = _run_collective_epoch(
                datacenter,
                scenario,
                policy_kind,
                step,
                consumed_outages,
            )
            epochs.append(collective_result)
            cycle_outage_ids.extend(sync_outages)
            collective_elapsed_ns = collective_result.elapsed_ns

            denominator = cycle_compute_elapsed_ns + collective_elapsed_ns
            collective_phase_fraction = (
                0.0 if denominator == 0
                else collective_elapsed_ns / denominator
            )
            sync_cycles.append(
                E001SyncCycle(
                    cycle_index=len(sync_cycles) + 1,
                    start_step=cycle_start_step,
                    end_step=step,
                    selected_local_steps=cycle_selected_local_steps,
                    completed_local_steps=steps_since_sync,
                    start_ns=cycle_start_ns,
                    end_ns=datacenter.timestamp_ns,
                    compute_elapsed_ns=cycle_compute_elapsed_ns,
                    collective_elapsed_ns=collective_elapsed_ns,
                    collective_phase_fraction=collective_phase_fraction,
                    outage_event_ids=tuple(dict.fromkeys(cycle_outage_ids)),
                )
            )
            prior_progress_weighted += (
                steps_since_sync
                * scenario.learning_prior.screening_progress_ratio(
                    steps_since_sync
                )
            )
            pessimistic_progress_weighted += (
                steps_since_sync
                * scenario.learning_prior.screening_progress_ratio(
                    steps_since_sync,
                    sensitivity_multiplier=2.0,
                )
            )
            if policy is not None and step != scenario.total_steps:
                datacenter.apply_interventions(
                    (
                        ConfigurationIntervention.create(
                            {
                                "last_sync_observed": True,
                                "last_collective_phase_fraction": (
                                    collective_phase_fraction
                                ),
                                "last_cycle_steps": steps_since_sync,
                            },
                            "completed synchronization-cycle observation",
                        ),
                    )
                )
            steps_since_sync = 0
            cycle_compute_elapsed_ns = 0
            cycle_outage_ids = []

        checkpoint_due = scenario.checkpoint_bytes and (
            step % scenario.checkpoint_interval_steps == 0
            or step == scenario.total_steps
        )
        if checkpoint_due:
            checkpoint_result, checkpoint_outages = _run_checkpoint_epoch(
                datacenter,
                scenario,
                policy_kind,
                step,
                consumed_outages,
            )
            epochs.append(checkpoint_result)
            if steps_since_sync:
                cycle_outage_ids.extend(checkpoint_outages)

    if steps_since_sync != 0:
        raise RuntimeError("E001 ended with unsynchronized local steps")
    metrics = _aggregate_metrics(epochs)
    point_ratio = prior_progress_weighted / scenario.total_steps
    pessimistic_ratio = pessimistic_progress_weighted / scenario.total_steps
    elapsed_ns = epochs[-1].end_ns - epochs[0].start_ns
    return E001Run(
        policy_kind=policy_kind,
        initial_local_steps=initial_local_steps,
        final_local_steps=datacenter.observe().sync_cadence.local_steps,
        epochs=tuple(epochs),
        sync_cycles=tuple(sync_cycles),
        metrics=metrics,
        prior_screening_progress_ratio=point_ratio,
        pessimistic_sensitivity_progress_ratio=pessimistic_ratio,
        prior_projected_time_to_equivalent_progress_ns=elapsed_ns / point_ratio,
    )


def run_e001(scenario: E001Scenario) -> E001Comparison:
    """Execute the mechanics screen while leaving unsupported claims unresolved."""
    engine_source_hash = e001_engine_source_hash()
    scenario_hash = scenario.scenario_hash
    baseline = _schedule_run(scenario, E001PolicyKind.SYNCHRONOUS)
    candidates = (
        _schedule_run(scenario, E001PolicyKind.FIXED_LOCAL),
        _schedule_run(scenario, E001PolicyKind.ADAPTIVE_CADENCE),
    )
    artifacts = []
    baseline_bytes = baseline.metrics.inter_site_collective_bytes
    if baseline_bytes <= 0:
        raise RuntimeError("E001 synchronous baseline produced no collective payload")
    for run in candidates:
        candidate_bytes = run.metrics.inter_site_collective_bytes
        collective_payload_fraction = candidate_bytes / baseline_bytes
        metrics = {
            "collective_payload_byte_fraction": collective_payload_fraction,
            "modeled_collective_payload_link_bytes": candidate_bytes,
            "modeled_base_and_compute_energy_j": (
                run.metrics.modeled_base_and_compute_energy_j
            ),
            "peak_allocated_power_w": run.metrics.peak_allocated_power_w,
            "state_transfer_bytes": run.metrics.state_transfer_bytes,
            "checkpoint_bytes": run.metrics.checkpoint_bytes,
        }
        evidence_gaps = (
            "no held-out multi-site learning observations are attached to this run",
            "the learning response is an unfitted sensitivity prior seeded only by one-step 360M Muon final-loss observations",
            "progress per FLOP and completion-time falsifiers are not evaluated from the screening prior",
            "the implemented controller adapts synchronization cadence only; topology, parallelism, optimizer correction, and state migration remain absent",
            "single-site centralized, sparse-gossip, migration-only, and future-trace oracle baselines remain absent",
            "outage overlap postpones whole operations and does not yet model preemption, lost work, or checkpoint recovery",
            "collective traffic is payload per modeled WAN link, not a complete algorithm-specific all-reduce byte model",
            "energy includes site base power and accelerator compute demand only; dynamic network, checkpoint, storage, host, and cooling energy are unmodeled",
            "site base power remains constant through the assumed outage; no measured curtailment or recovery power waveform is attached",
        )
        artifacts.append(
            E001_PROTOCOL.build_run_artifact(
                run_id=(
                    f"{scenario.scenario_id}:{run.policy_kind.value}:"
                    f"{scenario_hash[:12]}:{engine_source_hash[:12]}"
                ),
                stage=ExperimentStage.VIRTUAL,
                policy=run.policy_kind.value,
                scenario_id=scenario.scenario_id,
                metrics=metrics,
                calibration_observation_ids=(),
                evaluation_observation_ids=scenario.evaluation_observation_ids,
                assumptions=scenario.assumptions,
                evidence_gaps=evidence_gaps,
                trace_uri=(
                    "#/runs/1/epochs"
                    if run.policy_kind is E001PolicyKind.FIXED_LOCAL
                    else "#/runs/2/epochs"
                ),
                metadata={
                    "scenario_sha256": scenario_hash,
                    "engine_id": E001_ENGINE_ID,
                    "engine_source_sha256": engine_source_hash,
                    "comparison_role": (
                        "preregistered_baseline"
                        if run.policy_kind is E001PolicyKind.FIXED_LOCAL
                        else "hypothesis_policy"
                    ),
                    "initial_local_steps": run.initial_local_steps,
                    "final_local_steps": run.final_local_steps,
                    "sync_cycle_count": len(run.sync_cycles),
                    "learning_prior": scenario.learning_prior.to_dict(),
                    "learning_prior_seed_observation_ids": list(
                        scenario.learning_prior.seed_observation_ids
                    ),
                    "provenance": list(scenario.provenance),
                    "prior_screening_progress_ratio": (
                        run.prior_screening_progress_ratio
                    ),
                    "pessimistic_sensitivity_progress_ratio": (
                        run.pessimistic_sensitivity_progress_ratio
                    ),
                    "prior_projected_time_to_equivalent_progress_ns": (
                        run.prior_projected_time_to_equivalent_progress_ns
                    ),
                    "implemented_mechanisms": [
                        "successive decision epochs",
                        "adaptive synchronization cadence",
                    ],
                },
            )
        )
    return E001Comparison(
        scenario=scenario,
        protocol_hash=E001_PROTOCOL.protocol_hash,
        engine_source_hash=engine_source_hash,
        baseline=baseline,
        candidates=candidates,
        artifacts=tuple(artifacts),
    )


__all__ = [
    "AdaptiveCadencePolicy",
    "AdaptiveConsistencyPolicy",
    "E001Comparison",
    "E001MechanicsMetrics",
    "E001PolicyKind",
    "E001Run",
    "E001Scenario",
    "E001SyncCycle",
    "E001_PROTOCOL",
    "E001_RESULT_SCHEMA",
    "E001_ENGINE_ID",
    "LearningProgressCalibration",
    "LearningProgressPrior",
    "SiteOutage",
    "run_e001",
    "e001_engine_source_hash",
]
