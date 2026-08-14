"""Runs one complete recovery-backed E001 mechanical experiment.

The runner deliberately compares exactly four policies on one absolute-time
failure trace, all required to reach the same terminal durable frontier.
Learning progress stays an explicit prior — it is never measured here.
Recovery, work, communication, time, and energy accounting all come from
the executed mechanics, so the observatory has nothing to infer.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, Optional, Sequence, Tuple

from .recovery import (
    EvidenceBasis,
    EvidenceBoundary,
    FailureCauseCode,
    FailureInterval,
    FailureStatus,
    FailureTrace,
    LogicalWorkIdentity,
    RecoveryRequest,
    SiteWorkAttempt,
    StepSiteContributionRequirement,
    WorkAttemptKind,
    WorkLedger,
    WorkOutcomeDisposition,
    plan_recovery,
)
from .recovery_runtime import (
    CheckpointManifest,
    CheckpointShard,
    DecisionBoundary,
    RecoveryRuntime,
    RuntimeSnapshot,
    SiteState,
)


SYNC_POLICY_ID = "synchronous-wait-restore"
FIXED_LOCAL_POLICY_ID = "fixed-local-checkpoint-restart"
ADAPTIVE_POLICY_ID = "adaptive-recovery"
ORACLE_POLICY_ID = "future-trace-recovery-oracle"
POLICY_IDS = (
    SYNC_POLICY_ID,
    FIXED_LOCAL_POLICY_ID,
    ADAPTIVE_POLICY_ID,
    ORACLE_POLICY_ID,
)
ENGINE_ID = "e001-recovery-mechanics-v2"
EXECUTION_SCHEMA_VERSION = "e001-recovery-execution-v2"


def _json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _sha256_json(value: object) -> str:
    return "sha256:" + hashlib.sha256(_json_bytes(value)).hexdigest()


def _digest(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


def _engine_source_hash() -> str:
    directory = Path(__file__).resolve().parent
    digest = hashlib.sha256()
    for name in ("recovery.py", "recovery_runtime.py", Path(__file__).name):
        path = directory / name
        payload = path.read_bytes()
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return "sha256:" + digest.hexdigest()


def _evidence(boundary_id: str, source_id: str) -> EvidenceBoundary:
    return EvidenceBoundary(
        boundary_id=boundary_id,
        basis=EvidenceBasis.ASSUMED,
        source_ids=(source_id,),
        assumptions=("deterministic recovery-v2 mechanical scenario",),
    )


@dataclass(frozen=True)
class RecoveryFailureSpec:
    failure_id: str
    site_id: str
    failure_start_ns: int
    recovery_ns: int
    cause: str

    def __post_init__(self) -> None:
        if not self.failure_id or not self.site_id or not self.cause:
            raise ValueError("failure identifiers and cause must be non-blank")
        if self.failure_start_ns < 0 or self.recovery_ns <= self.failure_start_ns:
            raise ValueError("failure interval must be positive and half-open")

    def to_dict(self) -> dict[str, object]:
        return {
            "failure_id": self.failure_id,
            "site_id": self.site_id,
            "failure_start_ns": self.failure_start_ns,
            "recovery_ns": self.recovery_ns,
            "cause": self.cause,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "RecoveryFailureSpec":
        return cls(
            failure_id=str(data["failure_id"]),
            site_id=str(data["site_id"]),
            failure_start_ns=int(data["failure_start_ns"]),
            recovery_ns=int(data["recovery_ns"]),
            cause=str(data["cause"]),
        )


@dataclass(frozen=True)
class E001RecoveryScenario:
    scenario_id: str
    source_scenario_id: str
    site_ids: Tuple[str, ...]
    failed_site_id: str
    checkpoint_store_id: str
    target_steps: int
    work_per_site_step_flops: float
    step_compute_ns: int
    dense_collective_ns: int
    dense_collective_link_bytes: int
    sparse_collective_every_steps: int
    checkpoint_bytes: int
    baseline_checkpoint_interval_steps: int
    adaptive_checkpoint_interval_steps: int
    checkpoint_write_ns: int
    restore_bandwidth_bytes_per_second: float
    replay_work_per_second: float
    fixed_restart_latency_ns: int
    membership_reconfiguration_ns: int
    compute_energy_j_per_flop: float
    network_energy_j_per_link_byte: float
    learning_prior_progress_per_step: float
    learning_prior_source_id: str
    failures: Tuple[RecoveryFailureSpec, ...]
    assumptions: Tuple[str, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        sites = tuple(sorted(self.site_ids))
        if len(sites) < 2 or len(sites) != len(set(sites)):
            raise ValueError("scenario requires at least two unique sites")
        if self.failed_site_id not in sites:
            raise ValueError("failed_site_id must be a scenario site")
        if self.target_steps < 3:
            raise ValueError("target_steps must be at least three")
        positive_ints = (
            self.step_compute_ns,
            self.dense_collective_ns,
            self.dense_collective_link_bytes,
            self.sparse_collective_every_steps,
            self.checkpoint_bytes,
            self.baseline_checkpoint_interval_steps,
            self.adaptive_checkpoint_interval_steps,
            self.checkpoint_write_ns,
            self.fixed_restart_latency_ns,
            self.membership_reconfiguration_ns,
        )
        if any(value <= 0 for value in positive_ints):
            raise ValueError("mechanical scenario values must be positive")
        if not math.isfinite(self.work_per_site_step_flops) or self.work_per_site_step_flops <= 0:
            raise ValueError("work_per_site_step_flops must be finite and positive")
        if (
            not math.isfinite(self.restore_bandwidth_bytes_per_second)
            or self.restore_bandwidth_bytes_per_second <= 0
            or not math.isfinite(self.replay_work_per_second)
            or self.replay_work_per_second <= 0
        ):
            raise ValueError("recovery rates must be finite and positive")
        for name, value in (
            ("compute_energy_j_per_flop", self.compute_energy_j_per_flop),
            ("network_energy_j_per_link_byte", self.network_energy_j_per_link_byte),
            ("learning_prior_progress_per_step", self.learning_prior_progress_per_step),
        ):
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive")
        if not self.learning_prior_source_id.strip():
            raise ValueError("learning_prior_source_id must be non-blank")
        failures = tuple(self.failures)
        if len(failures) < 2:
            raise ValueError("the recovery-v2 experiment requires repeated failure")
        if any(item.site_id != self.failed_site_id for item in failures):
            raise ValueError("minimal recovery-v2 path uses one repeatedly failing site")
        ordered = tuple(sorted(failures, key=lambda item: (item.failure_start_ns, item.failure_id)))
        if any(left.recovery_ns > right.failure_start_ns for left, right in zip(ordered, ordered[1:])):
            raise ValueError("repeated failure intervals must not overlap")
        object.__setattr__(self, "site_ids", sites)
        object.__setattr__(self, "failures", ordered)
        object.__setattr__(self, "assumptions", tuple(self.assumptions))
        object.__setattr__(self, "metadata", MappingProxyType(dict(sorted(self.metadata.items()))))

    def to_dict(self) -> dict[str, object]:
        return {
            "scenario_id": self.scenario_id,
            "source_scenario_id": self.source_scenario_id,
            "site_ids": list(self.site_ids),
            "failed_site_id": self.failed_site_id,
            "checkpoint_store_id": self.checkpoint_store_id,
            "target_steps": self.target_steps,
            "work_per_site_step_flops": self.work_per_site_step_flops,
            "step_compute_ns": self.step_compute_ns,
            "dense_collective_ns": self.dense_collective_ns,
            "dense_collective_link_bytes": self.dense_collective_link_bytes,
            "sparse_collective_every_steps": self.sparse_collective_every_steps,
            "checkpoint_bytes": self.checkpoint_bytes,
            "baseline_checkpoint_interval_steps": self.baseline_checkpoint_interval_steps,
            "adaptive_checkpoint_interval_steps": self.adaptive_checkpoint_interval_steps,
            "checkpoint_write_ns": self.checkpoint_write_ns,
            "restore_bandwidth_bytes_per_second": self.restore_bandwidth_bytes_per_second,
            "replay_work_per_second": self.replay_work_per_second,
            "fixed_restart_latency_ns": self.fixed_restart_latency_ns,
            "membership_reconfiguration_ns": self.membership_reconfiguration_ns,
            "compute_energy_j_per_flop": self.compute_energy_j_per_flop,
            "network_energy_j_per_link_byte": self.network_energy_j_per_link_byte,
            "learning_prior_progress_per_step": self.learning_prior_progress_per_step,
            "learning_prior_source_id": self.learning_prior_source_id,
            "failures": [item.to_dict() for item in self.failures],
            "assumptions": list(self.assumptions),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "E001RecoveryScenario":
        failures = data.get("failures", ())
        if isinstance(failures, (str, bytes)) or not isinstance(failures, Sequence):
            raise TypeError("failures must be a sequence")
        return cls(
            scenario_id=str(data["scenario_id"]),
            source_scenario_id=str(data["source_scenario_id"]),
            site_ids=tuple(str(item) for item in data["site_ids"]),
            failed_site_id=str(data["failed_site_id"]),
            checkpoint_store_id=str(data["checkpoint_store_id"]),
            target_steps=int(data["target_steps"]),
            work_per_site_step_flops=float(data["work_per_site_step_flops"]),
            step_compute_ns=int(data["step_compute_ns"]),
            dense_collective_ns=int(data["dense_collective_ns"]),
            dense_collective_link_bytes=int(data["dense_collective_link_bytes"]),
            sparse_collective_every_steps=int(data["sparse_collective_every_steps"]),
            checkpoint_bytes=int(data["checkpoint_bytes"]),
            baseline_checkpoint_interval_steps=int(data["baseline_checkpoint_interval_steps"]),
            adaptive_checkpoint_interval_steps=int(data["adaptive_checkpoint_interval_steps"]),
            checkpoint_write_ns=int(data["checkpoint_write_ns"]),
            restore_bandwidth_bytes_per_second=float(data["restore_bandwidth_bytes_per_second"]),
            replay_work_per_second=float(data["replay_work_per_second"]),
            fixed_restart_latency_ns=int(data["fixed_restart_latency_ns"]),
            membership_reconfiguration_ns=int(data["membership_reconfiguration_ns"]),
            compute_energy_j_per_flop=float(data["compute_energy_j_per_flop"]),
            network_energy_j_per_link_byte=float(
                data["network_energy_j_per_link_byte"]
            ),
            learning_prior_progress_per_step=float(
                data["learning_prior_progress_per_step"]
            ),
            learning_prior_source_id=str(data["learning_prior_source_id"]),
            failures=tuple(RecoveryFailureSpec.from_dict(item) for item in failures),
            assumptions=tuple(str(item) for item in data.get("assumptions", ())),
            metadata=dict(data.get("metadata", {})),
        )

    @classmethod
    def from_json_path(cls, path: Path | str) -> "E001RecoveryScenario":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


@dataclass(frozen=True)
class LinkSegment:
    segment_id: str
    traffic_class: str
    start_ns: int
    end_ns: int
    link_bytes: int
    committed: bool
    related_object_id: str
    failure_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.end_ns < self.start_ns or self.link_bytes < 0:
            raise ValueError("link segment time and bytes must be non-negative")

    def to_dict(self) -> dict[str, object]:
        return {
            "segment_id": self.segment_id,
            "traffic_class": self.traffic_class,
            "start_ns": self.start_ns,
            "end_ns": self.end_ns,
            "link_bytes": self.link_bytes,
            "committed": self.committed,
            "related_object_id": self.related_object_id,
            "failure_id": self.failure_id,
        }


@dataclass(frozen=True)
class RecoveryEpisode:
    episode_id: str
    failure_ids: Tuple[str, ...]
    target_site_id: str
    failure_observed_at_ns: int
    preempted_attempt_ids: Tuple[str, ...]
    membership_removed_at_ns: Optional[int]
    physical_recovery_at_ns: int
    restore_started_at_ns: int
    restore_completed_at_ns: int
    replay_completed_at_ns: int
    membership_rejoined_at_ns: int
    checkpoint_id: str
    checkpoint_step: int
    interrupted_recovery_ids: Tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "episode_id": self.episode_id,
            "failure_ids": list(self.failure_ids),
            "target_site_id": self.target_site_id,
            "failure_observed_at_ns": self.failure_observed_at_ns,
            "preempted_attempt_ids": list(self.preempted_attempt_ids),
            "membership_removed_at_ns": self.membership_removed_at_ns,
            "physical_recovery_at_ns": self.physical_recovery_at_ns,
            "restore_started_at_ns": self.restore_started_at_ns,
            "restore_completed_at_ns": self.restore_completed_at_ns,
            "replay_completed_at_ns": self.replay_completed_at_ns,
            "membership_rejoined_at_ns": self.membership_rejoined_at_ns,
            "checkpoint_id": self.checkpoint_id,
            "checkpoint_step": self.checkpoint_step,
            "interrupted_recovery_ids": list(self.interrupted_recovery_ids),
        }


@dataclass(frozen=True)
class PolicyExecution:
    policy_id: str
    runtime_id: str
    lineage_id: str
    start_ns: int
    end_ns: int
    terminal_frontier: int
    terminal_checkpoint: CheckpointManifest
    recovery_episodes: Tuple[RecoveryEpisode, ...]
    snapshots: Tuple[RuntimeSnapshot, ...]
    work_ledger: WorkLedger
    checkpoint_manifests: Tuple[CheckpointManifest, ...]
    link_segments: Tuple[LinkSegment, ...]
    learning_progress_prior: float
    learning_prior_source_id: str
    compute_energy_j_per_flop: float
    network_energy_j_per_link_byte: float

    def __post_init__(self) -> None:
        if self.policy_id not in POLICY_IDS:
            raise ValueError("unknown recovery-v2 policy")
        if self.end_ns < self.start_ns:
            raise ValueError("policy execution ends before it starts")
        if self.terminal_checkpoint.committed_step != self.terminal_frontier:
            raise ValueError("terminal checkpoint must prove terminal frontier")
        if self.work_ledger.as_of_ns is not None:
            raise ValueError("terminal work ledger must be the live complete ledger")
        if not math.isclose(
            self.work_ledger.attempted_work,
            self.work_ledger.committed_work + self.work_ledger.lost_work,
            rel_tol=0.0,
            abs_tol=1e-3,
        ):
            raise ValueError("terminal exact work conservation failed")

    @property
    def elapsed_ns(self) -> int:
        return self.end_ns - self.start_ns

    @property
    def traffic_by_class(self) -> Mapping[str, int]:
        totals: dict[str, int] = {}
        for segment in self.link_segments:
            totals[segment.traffic_class] = totals.get(segment.traffic_class, 0) + segment.link_bytes
        return MappingProxyType(dict(sorted(totals.items())))

    @property
    def total_inter_site_link_bytes(self) -> int:
        return sum(self.traffic_by_class.values())

    @property
    def work_dispositions(self) -> Mapping[str, Mapping[str, float | int]]:
        result: dict[str, dict[str, float | int]] = {}
        for disposition in WorkOutcomeDisposition:
            outcomes = tuple(
                item for item in self.work_ledger.outcomes if item.disposition is disposition
            )
            result[disposition.value] = {
                "outcome_count": len(outcomes),
                "attempted_work": sum(item.attempted_work for item in outcomes),
                "committed_work": sum(item.committed_work for item in outcomes),
                "lost_work": sum(item.lost_work for item in outcomes),
                "replayed_work": sum(item.replayed_work for item in outcomes),
            }
        return MappingProxyType({key: MappingProxyType(value) for key, value in result.items()})

    @property
    def exact_work_conservation(self) -> bool:
        return math.isclose(
            self.work_ledger.attempted_work,
            self.work_ledger.committed_work + self.work_ledger.lost_work,
            rel_tol=0.0,
            abs_tol=1e-3,
        )

    @property
    def recovery_time_ns(self) -> int:
        return sum(
            item.membership_rejoined_at_ns - item.failure_observed_at_ns
            for item in self.recovery_episodes
        )

    def to_dict(self) -> dict[str, object]:
        accounting = self.work_ledger.to_dict()["accounting"]
        metrics = {
            "mechanical_completion_time_ns": self.elapsed_ns,
            "total_inter_site_link_bytes": self.total_inter_site_link_bytes,
            "terminal_durable_frontier": self.terminal_frontier,
            "attempted_compute_flops": accounting["attempted_work"],
            "valid_final_state_compute_flops": accounting["committed_work"],
            "lost_compute_flops": accounting["lost_work"],
            "replay_compute_flops": accounting["replayed_work"],
            "recomputed_compute_flops": accounting["recomputed_work"],
            "exact_work_conservation": self.exact_work_conservation,
            "traffic_by_class": dict(self.traffic_by_class),
            "learning_progress": {
                "value": self.learning_progress_prior,
                "unit": "prior_normalized_progress",
                "evidence_class": "prior",
                "source_id": self.learning_prior_source_id,
            },
            "recovery_time_ns": self.recovery_time_ns,
            "recovery_debt_ns": self.recovery_time_ns,
            "modeled_energy_j": (
                accounting["attempted_work"] * self.compute_energy_j_per_flop
                + self.total_inter_site_link_bytes
                * self.network_energy_j_per_link_byte
            ),
            "modeled_compute_energy_j": (
                accounting["attempted_work"] * self.compute_energy_j_per_flop
            ),
            "modeled_network_energy_j": (
                self.total_inter_site_link_bytes
                * self.network_energy_j_per_link_byte
            ),
        }
        return {
            "policy_id": self.policy_id,
            "runtime_id": self.runtime_id,
            "lineage_id": self.lineage_id,
            "start_ns": self.start_ns,
            "end_ns": self.end_ns,
            "durable_frontier_reached_at_ns": self.end_ns,
            "elapsed_ns": self.elapsed_ns,
            "terminal_frontier": self.terminal_frontier,
            "terminal_checkpoint": self.terminal_checkpoint.to_dict(),
            "recovery_episodes": [item.to_dict() for item in self.recovery_episodes],
            "decision_batches": [
                {
                    "timestamp_ns": snapshot.timestamp_ns,
                    "boundaries": [item.value for item in snapshot.boundaries],
                    "boundary_ids": list(snapshot.boundary_ids),
                    "desired_membership": list(snapshot.desired_membership),
                    "effective_membership": list(snapshot.effective_membership),
                }
                for snapshot in self.snapshots
            ],
            "work_ledger": self.work_ledger.to_dict(),
            "work_dispositions": {
                key: dict(value) for key, value in self.work_dispositions.items()
            },
            "checkpoint_manifests": [item.to_dict() for item in self.checkpoint_manifests],
            "link_segments": [item.to_dict() for item in self.link_segments],
            "metrics": metrics,
            "snapshots": [item.to_dict() for item in self.snapshots],
        }


@dataclass(frozen=True)
class MatchedRecoveryComparison:
    baseline_policy_id: str
    candidate_policy_id: str
    matched_frontier: int
    equal_terminal_frontier: bool
    baseline_completion_time_ns: int
    candidate_completion_time_ns: int
    completion_time_delta_ns: int
    completion_time_ratio: float
    baseline_total_inter_site_link_bytes: int
    candidate_total_inter_site_link_bytes: int
    total_inter_site_link_bytes_delta: int
    total_inter_site_link_bytes_ratio: float
    both_exact_work_conservation: bool
    hypothesis_supported: bool

    def to_dict(self) -> dict[str, object]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class E001RecoveryExecution:
    schema_version: str
    experiment_id: str
    engine_id: str
    engine_source_hash: str
    scenario_hash: str
    scenario: E001RecoveryScenario
    failure_trace: FailureTrace
    matched_frontier: int
    policies: Tuple[PolicyExecution, ...]
    comparison: MatchedRecoveryComparison

    def __post_init__(self) -> None:
        if tuple(item.policy_id for item in self.policies) != POLICY_IDS:
            raise ValueError("execution must contain exactly the four frozen policies")
        if any(item.terminal_frontier != self.matched_frontier for item in self.policies):
            raise ValueError("all policies must reach the matched frontier")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "experiment_id": self.experiment_id,
            "engine_id": self.engine_id,
            "engine_source_hash": self.engine_source_hash,
            "scenario_hash": self.scenario_hash,
            "scenario": self.scenario.to_dict(),
            "failure_trace": self.failure_trace.to_dict(),
            "matched_frontier": self.matched_frontier,
            "policies": [item.to_dict() for item in self.policies],
            "comparison": self.comparison.to_dict(),
        }

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=indent, allow_nan=False)


def run_e001_recovery_v2(scenario: E001RecoveryScenario) -> E001RecoveryExecution:
    """Execute the frozen four-policy panel on one matched trace and frontier."""
    executions = tuple(_run_policy(scenario, policy_id) for policy_id in POLICY_IDS)
    by_policy = {item.policy_id: item for item in executions}
    baseline = by_policy[SYNC_POLICY_ID]
    candidate = by_policy[ADAPTIVE_POLICY_ID]
    comparison = MatchedRecoveryComparison(
        baseline_policy_id=baseline.policy_id,
        candidate_policy_id=candidate.policy_id,
        matched_frontier=scenario.target_steps,
        equal_terminal_frontier=(
            baseline.terminal_frontier
            == candidate.terminal_frontier
            == scenario.target_steps
        ),
        baseline_completion_time_ns=baseline.elapsed_ns,
        candidate_completion_time_ns=candidate.elapsed_ns,
        completion_time_delta_ns=candidate.elapsed_ns - baseline.elapsed_ns,
        completion_time_ratio=candidate.elapsed_ns / baseline.elapsed_ns,
        baseline_total_inter_site_link_bytes=baseline.total_inter_site_link_bytes,
        candidate_total_inter_site_link_bytes=candidate.total_inter_site_link_bytes,
        total_inter_site_link_bytes_delta=(
            candidate.total_inter_site_link_bytes - baseline.total_inter_site_link_bytes
        ),
        total_inter_site_link_bytes_ratio=(
            candidate.total_inter_site_link_bytes / baseline.total_inter_site_link_bytes
        ),
        both_exact_work_conservation=(
            baseline.exact_work_conservation and candidate.exact_work_conservation
        ),
        hypothesis_supported=(
            baseline.terminal_frontier == candidate.terminal_frontier
            and candidate.elapsed_ns < baseline.elapsed_ns
            and candidate.total_inter_site_link_bytes < baseline.total_inter_site_link_bytes
            and baseline.exact_work_conservation
            and candidate.exact_work_conservation
        ),
    )
    return E001RecoveryExecution(
        schema_version=EXECUTION_SCHEMA_VERSION,
        experiment_id="E001-recovery-v2",
        engine_id=ENGINE_ID,
        engine_source_hash=_engine_source_hash(),
        scenario_hash=_sha256_json(scenario.to_dict()),
        scenario=scenario,
        failure_trace=_failure_trace(scenario),
        matched_frontier=scenario.target_steps,
        policies=executions,
        comparison=comparison,
    )


def _failure_trace(scenario: E001RecoveryScenario) -> FailureTrace:
    intervals = tuple(
        FailureInterval(
            failure_id=item.failure_id,
            site_id=item.site_id,
            failure_start_ns=item.failure_start_ns,
            recovery_ns=item.recovery_ns,
            cause=FailureCauseCode.SITE_UNAVAILABLE,
            evidence=_evidence(
                f"e001-recovery:failure:{item.failure_id}",
                f"scenario:{scenario.scenario_id}",
            ),
            metadata={"scenario_cause": item.cause},
        )
        for item in scenario.failures
    )
    return FailureTrace(
        trace_id=f"{scenario.scenario_id}:shared-failure-trace",
        intervals=intervals,
        metadata={"absolute_time_matched": True, "policy_ids": list(POLICY_IDS)},
    )


@dataclass(frozen=True)
class _CollectivePlan:
    segment_id: str
    traffic_class: str
    attempt_ids: Tuple[str, ...]
    start_ns: int
    end_ns: int
    link_bytes: int


@dataclass(frozen=True)
class _ActiveRecovery:
    recovery_id: str
    failure_id: str
    failure_observed_at_ns: int
    physical_recovery_at_ns: int
    preempted_attempt_ids: Tuple[str, ...]
    restore_started_at_ns: int
    restore_completed_at_ns: int
    replay_completed_at_ns: int
    checkpoint_id: str
    checkpoint_step: int


def _checkpoint_manifest(
    scenario: E001RecoveryScenario,
    *,
    policy_id: str,
    lineage_id: str,
    checkpoint_serial: int,
    committed_step: int,
    start_ns: int,
    membership: Tuple[str, ...],
) -> CheckpointManifest:
    checkpoint_id = f"{policy_id}:checkpoint:{checkpoint_serial}:step-{committed_step}"
    state_version = f"{lineage_id}:step-{committed_step}"
    shard_id = f"{checkpoint_id}:complete-state"
    completed_at_ns = start_ns + scenario.checkpoint_write_ns
    shard = CheckpointShard(
        shard_id=shard_id,
        site_id=scenario.checkpoint_store_id,
        source_state_version=state_version,
        storage_location=f"object://{scenario.checkpoint_store_id}/{checkpoint_id}",
        failure_domain=f"storage-domain:{scenario.checkpoint_store_id}",
        state_bytes=scenario.checkpoint_bytes,
        checksum=_digest(f"{checkpoint_id}:state"),
        write_started_at_ns=start_ns,
        write_completed_at_ns=completed_at_ns,
    )
    return CheckpointManifest(
        checkpoint_id=checkpoint_id,
        lineage_id=lineage_id,
        committed_step=committed_step,
        state_version=state_version,
        model_hash=_digest(f"{state_version}:model"),
        optimizer_hash=_digest(f"{state_version}:optimizer"),
        rng_hash=_digest(f"{state_version}:rng"),
        data_cursor_hash=_digest(f"{state_version}:cursor"),
        state_bytes=scenario.checkpoint_bytes,
        required_shard_ids=(shard_id,),
        shards=(shard,),
        site_membership=membership,
        recovery_source_site_id=scenario.checkpoint_store_id,
        checkpoint_write_started_at_ns=start_ns,
        checkpoint_write_completed_at_ns=completed_at_ns,
        manifest_committed_at_ns=completed_at_ns,
        evidence=_evidence(
            f"e001-recovery:checkpoint:{checkpoint_id}",
            f"scenario:{scenario.scenario_id}",
        ),
        metadata={"policy_id": policy_id, "atomic_manifest": True},
    )


def _logical_sites_at_step(
    work: WorkLedger,
    *,
    lineage_id: str,
    step: int,
) -> Tuple[str, ...]:
    sites: list[str] = []
    for outcome in work.canonical_outcomes:
        for identity in work.logical_identities_for(outcome):
            if identity.lineage_id == lineage_id and identity.logical_step == step:
                sites.append(identity.original_site_id)
    if len(sites) != len(set(sites)):
        raise RuntimeError(f"ambiguous canonical logical work at step {step}")
    return tuple(sorted(sites))


def _durable_frontier(
    work: WorkLedger,
    *,
    lineage_id: str,
    site_ids: Tuple[str, ...],
    limit: int,
) -> int:
    frontier = 0
    for step in range(1, limit + 1):
        if _logical_sites_at_step(work, lineage_id=lineage_id, step=step) != site_ids:
            break
        frontier = step
    return frontier


def _checkpoint_interval(scenario: E001RecoveryScenario, policy_id: str) -> int:
    if policy_id == ADAPTIVE_POLICY_ID:
        return scenario.adaptive_checkpoint_interval_steps
    if policy_id == ORACLE_POLICY_ID:
        return 1
    return scenario.baseline_checkpoint_interval_steps


def _collective_enabled(
    scenario: E001RecoveryScenario,
    policy_id: str,
    *,
    step: int,
    start_ns: int,
) -> bool:
    if policy_id == SYNC_POLICY_ID:
        return True
    periodic = step % scenario.sparse_collective_every_steps == 0
    if policy_id != ORACLE_POLICY_ID:
        return periodic
    planned_end_ns = start_ns + scenario.step_compute_ns + (
        scenario.dense_collective_ns if periodic else 0
    )
    failure_will_preempt = any(
        start_ns < item.failure_start_ns < planned_end_ns
        for item in scenario.failures
    )
    return periodic and not failure_will_preempt


def _attempt(
    scenario: E001RecoveryScenario,
    *,
    policy_id: str,
    lineage_id: str,
    site_id: str,
    step: int,
    attempt_serial: int,
    start_ns: int,
    duration_ns: int,
) -> SiteWorkAttempt:
    attempt_id = f"{policy_id}:attempt:{attempt_serial}:{site_id}:step-{step}"
    return SiteWorkAttempt(
        attempt_id=attempt_id,
        lineage_id=lineage_id,
        site_id=site_id,
        step=step,
        start_ns=start_ns,
        planned_end_ns=start_ns + duration_ns,
        planned_work=scenario.work_per_site_step_flops,
        work_unit="FLOP",
        kind=WorkAttemptKind.FORWARD,
        logical_work=LogicalWorkIdentity(
            logical_work_id=f"{lineage_id}:{site_id}:step-{step}",
            lineage_id=lineage_id,
            logical_step=step,
            logical_partition=f"partition:{site_id}",
            original_site_id=site_id,
            state_lineage_hash=_digest(f"{lineage_id}:input:step-{step}"),
        ),
        evidence=_evidence(
            f"e001-recovery:attempt:{attempt_id}",
            f"scenario:{scenario.scenario_id}",
        ),
        metadata={"policy_id": policy_id},
    )


def _recovery_plan(
    scenario: E001RecoveryScenario,
    *,
    policy_id: str,
    lineage_id: str,
    runtime: RecoveryRuntime,
    snapshot: RuntimeSnapshot,
    recovery_serial: int,
):
    recovered = tuple(
        item
        for item in snapshot.observed_failures
        if item.site_id == scenario.failed_site_id
        and item.status is FailureStatus.RECOVERED
    )
    if not recovered:
        raise RuntimeError("physical recovery boundary lacks a recovered observation")
    failure = max(recovered, key=lambda item: (item.failure_start_ns, item.failure_id))
    frontier = _durable_frontier(
        runtime.work_ledger,
        lineage_id=lineage_id,
        site_ids=scenario.site_ids,
        limit=scenario.target_steps,
    )
    checkpoint = runtime.checkpoint_ledger.latest_at(
        failure.failure_start_ns,
        lineage_id=lineage_id,
    )
    if checkpoint is None:
        raise RuntimeError("focused E001 path requires a committed genesis checkpoint")
    restore_resources = checkpoint.restore_resource_ids(scenario.failed_site_id)
    requirements = tuple(
        StepSiteContributionRequirement(step=step, site_ids=scenario.site_ids)
        for step in range(checkpoint.step + 1, frontier + 1)
    )
    request = RecoveryRequest(
        recovery_id=f"{policy_id}:recovery:{recovery_serial}:{failure.failure_id}",
        lineage_id=lineage_id,
        decision_time_ns=snapshot.timestamp_ns,
        failure=failure,
        target_site_id=scenario.failed_site_id,
        last_committed_step=frontier,
        restore_bandwidth_bytes_per_second=(
            scenario.restore_bandwidth_bytes_per_second
        ),
        replay_work_per_second=scenario.replay_work_per_second,
        fixed_restart_latency_ns=scenario.fixed_restart_latency_ns,
        unavailable_site_ids=tuple(
            sorted(
                {
                    item.site_id
                    for item in snapshot.observed_failures
                    if item.status is FailureStatus.ACTIVE
                }
            )
        ),
        evidence=_evidence(
            f"e001-recovery:decision:{policy_id}:{recovery_serial}",
            f"scenario:{scenario.scenario_id}",
        ),
        failure_observations=snapshot.observed_failures,
        available_resource_ids=restore_resources,
        required_restore_resource_ids=restore_resources,
        step_site_requirements=requirements,
        evidence_gaps=(
            "learning progress is a declared prior, not an observed held-out metric",
        ),
    )
    return plan_recovery(request, runtime.checkpoint_ledger, runtime.work_ledger)


def _link_segments(
    scenario: E001RecoveryScenario,
    *,
    runtime: RecoveryRuntime,
    collective_plans: Sequence[_CollectivePlan],
    scheduled_manifests: Sequence[CheckpointManifest],
) -> Tuple[LinkSegment, ...]:
    outcomes = {
        item.attempt.attempt_id: item for item in runtime.work_ledger.outcomes
    }
    segments: list[LinkSegment] = []
    for plan in collective_plans:
        plan_outcomes = tuple(outcomes[item] for item in plan.attempt_ids)
        interrupted = tuple(item for item in plan_outcomes if item.interrupted)
        if interrupted:
            execution_end_ns = max(
                plan.start_ns,
                min(item.execution_end_ns for item in interrupted),
            )
            collective_duration = plan.end_ns - plan.start_ns
            active_ns = max(
                0,
                min(execution_end_ns, plan.end_ns) - plan.start_ns,
            )
            link_bytes = int(plan.link_bytes * active_ns / collective_duration)
            failure_id = min(
                item.interruption_failure_id for item in interrupted
                if item.interruption_failure_id is not None
            )
            committed = False
        else:
            execution_end_ns = plan.end_ns
            link_bytes = plan.link_bytes
            failure_id = None
            committed = True
        segments.append(
            LinkSegment(
                segment_id=plan.segment_id,
                traffic_class=plan.traffic_class,
                start_ns=plan.start_ns,
                end_ns=execution_end_ns,
                link_bytes=link_bytes,
                committed=committed,
                related_object_id=",".join(plan.attempt_ids),
                failure_id=failure_id,
            )
        )

    committed_ids = {item.checkpoint_id for item in runtime.committed_manifests}
    failure_trace = _failure_trace(scenario)
    for manifest in scheduled_manifests:
        committed = manifest.checkpoint_id in committed_ids
        end_ns = manifest.commit_at_ns
        link_bytes = manifest.state_bytes
        failure_id = None
        if not committed:
            interrupting = tuple(
                item
                for item in failure_trace.intervals
                if item.site_id in manifest.site_membership
                and manifest.checkpoint_write_started_at_ns
                <= item.failure_start_ns
                < manifest.commit_at_ns
            )
            if not interrupting:
                raise RuntimeError("aborted checkpoint has no matched interrupting failure")
            failure = min(interrupting, key=lambda item: item.failure_start_ns)
            end_ns = failure.failure_start_ns
            duration = manifest.commit_at_ns - manifest.checkpoint_write_started_at_ns
            link_bytes = int(
                manifest.state_bytes
                * (end_ns - manifest.checkpoint_write_started_at_ns)
                / duration
            )
            failure_id = failure.failure_id
        segments.append(
            LinkSegment(
                segment_id=f"checkpoint-transfer:{manifest.checkpoint_id}",
                traffic_class="checkpoint",
                start_ns=manifest.checkpoint_write_started_at_ns,
                end_ns=end_ns,
                link_bytes=link_bytes,
                committed=committed,
                related_object_id=manifest.checkpoint_id,
                failure_id=failure_id,
            )
        )

    for transfer in runtime.restore_transfers:
        segments.append(
            LinkSegment(
                segment_id=(
                    f"restore:{transfer.recovery_id}:{transfer.shard_id}:"
                    f"{transfer.execution_end_ns}"
                ),
                traffic_class="restore",
                start_ns=min(
                    transfer.transfer_start_ns,
                    transfer.execution_end_ns,
                ),
                end_ns=transfer.execution_end_ns,
                link_bytes=transfer.attempted_bytes,
                committed=not transfer.interrupted,
                related_object_id=transfer.recovery_id,
                failure_id=transfer.interruption_failure_id,
            )
        )
    return tuple(sorted(segments, key=lambda item: (item.start_ns, item.segment_id)))


def _run_policy(scenario: E001RecoveryScenario, policy_id: str) -> PolicyExecution:
    if policy_id not in POLICY_IDS:
        raise ValueError(f"unknown E001 recovery policy {policy_id!r}")
    lineage_id = f"{scenario.scenario_id}:{policy_id}"
    runtime = RecoveryRuntime(
        runtime_id=f"e001-recovery:{policy_id}",
        lineage_id=lineage_id,
        site_ids=scenario.site_ids,
        initial_membership=scenario.site_ids,
        failure_trace=_failure_trace(scenario),
    )
    snapshots: list[RuntimeSnapshot] = []
    scheduled_manifests: list[CheckpointManifest] = []
    collective_plans: list[_CollectivePlan] = []
    recovery_episodes: list[RecoveryEpisode] = []
    checkpoint_serial = 0
    attempt_serial = 0
    recovery_serial = 0
    collective_serial = 0
    pending_checkpoint_id: Optional[str] = None
    active_recovery: Optional[_ActiveRecovery] = None

    while True:
        snapshot = runtime.advance_to_decision()
        if snapshot is None:
            raise RuntimeError(
                f"{policy_id} exhausted transitions before reaching the terminal frontier"
            )
        snapshots.append(snapshot)
        if pending_checkpoint_id is not None and (
            pending_checkpoint_id in snapshot.aborted_checkpoint_ids
            or pending_checkpoint_id
            in {item.checkpoint_id for item in snapshot.committed_checkpoints}
        ):
            pending_checkpoint_id = None

        if active_recovery is not None:
            site = snapshot.site(scenario.failed_site_id)
            if site.active_recovery_id is None and site.state is SiteState.HEALTHY_READY:
                recovery_episodes.append(
                    RecoveryEpisode(
                        episode_id=active_recovery.recovery_id,
                        failure_ids=(active_recovery.failure_id,),
                        target_site_id=scenario.failed_site_id,
                        failure_observed_at_ns=(
                            active_recovery.failure_observed_at_ns
                        ),
                        preempted_attempt_ids=(
                            active_recovery.preempted_attempt_ids
                        ),
                        membership_removed_at_ns=(
                            active_recovery.failure_observed_at_ns
                        ),
                        physical_recovery_at_ns=(
                            active_recovery.physical_recovery_at_ns
                        ),
                        restore_started_at_ns=active_recovery.restore_started_at_ns,
                        restore_completed_at_ns=(
                            active_recovery.restore_completed_at_ns
                        ),
                        replay_completed_at_ns=(
                            active_recovery.replay_completed_at_ns
                        ),
                        membership_rejoined_at_ns=snapshot.timestamp_ns,
                        checkpoint_id=active_recovery.checkpoint_id,
                        checkpoint_step=active_recovery.checkpoint_step,
                        interrupted_recovery_ids=(),
                    )
                )
                active_recovery = None

        if DecisionBoundary.FAILURE_OBSERVED in snapshot.boundaries:
            if active_recovery is not None:
                raise RuntimeError(
                    "the focused E001 scenario must not interrupt an active restore"
                )
            if (
                policy_id != SYNC_POLICY_ID
                and scenario.failed_site_id in runtime.desired_membership
            ):
                runtime.request_membership(
                    tuple(
                        item
                        for item in scenario.site_ids
                        if item != scenario.failed_site_id
                    ),
                    reconfiguration_id=(
                        f"{policy_id}:remove:{snapshot.timestamp_ns}"
                    ),
                    duration_ns=scenario.membership_reconfiguration_ns,
                )
            continue

        if DecisionBoundary.PHYSICAL_RECOVERY in snapshot.boundaries:
            if snapshot.site(scenario.failed_site_id).state is SiteState.FAILED:
                continue
            if scenario.failed_site_id not in runtime.desired_membership:
                runtime.request_membership(
                    scenario.site_ids,
                    reconfiguration_id=f"{policy_id}:rejoin:{snapshot.timestamp_ns}",
                    duration_ns=scenario.membership_reconfiguration_ns,
                )
                continue

        should_begin_recovery = (
            snapshot.site(scenario.failed_site_id).state
            is SiteState.RECOVERED_UNRESTORED
            and scenario.failed_site_id in runtime.desired_membership
            and active_recovery is None
        )
        if should_begin_recovery:
            recovery_serial += 1
            plan = _recovery_plan(
                scenario,
                policy_id=policy_id,
                lineage_id=lineage_id,
                runtime=runtime,
                snapshot=snapshot,
                recovery_serial=recovery_serial,
            )
            if not plan.can_start:
                raise RuntimeError(
                    f"focused E001 recovery unexpectedly blocked: {plan.to_dict()}"
                )
            preempted = tuple(
                sorted(
                    item.attempt.attempt_id
                    for item in runtime.work_ledger.outcomes
                    if item.interruption_failure_id == plan.request.failure.failure_id
                )
            )
            runtime.begin_recovery(plan)
            active_recovery = _ActiveRecovery(
                recovery_id=plan.recovery_id,
                failure_id=plan.request.failure.failure_id,
                failure_observed_at_ns=plan.request.failure.failure_start_ns,
                physical_recovery_at_ns=plan.request.failure.recovery_observed_ns
                or snapshot.timestamp_ns,
                preempted_attempt_ids=preempted,
                restore_started_at_ns=plan.scheduled_start_ns or snapshot.timestamp_ns,
                restore_completed_at_ns=(
                    (plan.scheduled_start_ns or snapshot.timestamp_ns)
                    + scenario.fixed_restart_latency_ns
                    + plan.transfer_latency_ns
                ),
                replay_completed_at_ns=plan.scheduled_completion_ns
                or snapshot.timestamp_ns,
                checkpoint_id=plan.checkpoint.checkpoint_id,
                checkpoint_step=plan.checkpoint.step,
            )
            continue

        if any(
            runtime.site_state(site_id) is not SiteState.HEALTHY_READY
            for site_id in scenario.site_ids
        ) or runtime.effective_membership != scenario.site_ids:
            continue

        frontier = _durable_frontier(
            runtime.work_ledger,
            lineage_id=lineage_id,
            site_ids=scenario.site_ids,
            limit=scenario.target_steps,
        )
        terminal = tuple(
            item
            for item in runtime.committed_manifests
            if item.committed_step == scenario.target_steps
        )
        if frontier == scenario.target_steps and terminal:
            terminal_checkpoint = max(terminal, key=lambda item: item.commit_at_ns)
            break

        checkpoint_due = (
            frontier == scenario.target_steps
            or (
                frontier > 0
                and frontier % _checkpoint_interval(scenario, policy_id) == 0
            )
        )
        latest_checkpoint_step = max(
            (item.committed_step for item in runtime.committed_manifests),
            default=-1,
        )
        if pending_checkpoint_id is None and (
            not runtime.committed_manifests
            or (checkpoint_due and latest_checkpoint_step < frontier)
        ):
            checkpoint_serial += 1
            manifest = _checkpoint_manifest(
                scenario,
                policy_id=policy_id,
                lineage_id=lineage_id,
                checkpoint_serial=checkpoint_serial,
                committed_step=frontier,
                start_ns=snapshot.timestamp_ns,
                membership=runtime.effective_membership,
            )
            runtime.schedule_checkpoint(manifest)
            scheduled_manifests.append(manifest)
            pending_checkpoint_id = manifest.checkpoint_id
            continue

        step = frontier + 1
        completed_sites = _logical_sites_at_step(
            runtime.work_ledger,
            lineage_id=lineage_id,
            step=step,
        )
        missing_sites = tuple(
            item for item in scenario.site_ids if item not in completed_sites
        )
        collective = _collective_enabled(
            scenario,
            policy_id,
            step=step,
            start_ns=snapshot.timestamp_ns,
        )
        duration_ns = scenario.step_compute_ns + (
            scenario.dense_collective_ns if collective else 0
        )
        attempts = []
        for site_id in missing_sites:
            attempt_serial += 1
            work_attempt = _attempt(
                scenario,
                policy_id=policy_id,
                lineage_id=lineage_id,
                site_id=site_id,
                step=step,
                attempt_serial=attempt_serial,
                start_ns=snapshot.timestamp_ns,
                duration_ns=duration_ns,
            )
            runtime.submit_attempt(work_attempt)
            attempts.append(work_attempt)
        if collective:
            collective_serial += 1
            collective_plans.append(
                _CollectivePlan(
                    segment_id=(
                        f"{policy_id}:collective:{collective_serial}:step-{step}"
                    ),
                    traffic_class=(
                        "dense_collective"
                        if policy_id == SYNC_POLICY_ID
                        else "sparse_collective"
                    ),
                    attempt_ids=tuple(item.attempt_id for item in attempts),
                    start_ns=snapshot.timestamp_ns + scenario.step_compute_ns,
                    end_ns=snapshot.timestamp_ns + duration_ns,
                    link_bytes=scenario.dense_collective_link_bytes,
                )
            )

    return PolicyExecution(
        policy_id=policy_id,
        runtime_id=f"e001-recovery:{policy_id}",
        lineage_id=lineage_id,
        start_ns=0,
        end_ns=terminal_checkpoint.commit_at_ns,
        terminal_frontier=scenario.target_steps,
        terminal_checkpoint=terminal_checkpoint,
        recovery_episodes=tuple(recovery_episodes),
        snapshots=tuple(snapshots),
        work_ledger=runtime.work_ledger,
        checkpoint_manifests=runtime.committed_manifests,
        link_segments=_link_segments(
            scenario,
            runtime=runtime,
            collective_plans=collective_plans,
            scheduled_manifests=scheduled_manifests,
        ),
        learning_progress_prior=(
            scenario.target_steps * scenario.learning_prior_progress_per_step
        ),
        learning_prior_source_id=scenario.learning_prior_source_id,
        compute_energy_j_per_flop=scenario.compute_energy_j_per_flop,
        network_energy_j_per_link_byte=(
            scenario.network_energy_j_per_link_byte
        ),
    )


__all__ = [
    "ADAPTIVE_POLICY_ID",
    "ENGINE_ID",
    "E001RecoveryExecution",
    "E001RecoveryScenario",
    "EXECUTION_SCHEMA_VERSION",
    "FIXED_LOCAL_POLICY_ID",
    "LinkSegment",
    "MatchedRecoveryComparison",
    "ORACLE_POLICY_ID",
    "POLICY_IDS",
    "PolicyExecution",
    "RecoveryEpisode",
    "RecoveryFailureSpec",
    "SYNC_POLICY_ID",
    "run_e001_recovery_v2",
]
