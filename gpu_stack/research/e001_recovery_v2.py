"""The preregistered E001 recovery-v2 protocol, kept apart from the v1 runner.

Preregistered means the policies, metrics, falsifiers, and evidence gates
were fixed before running, so results cannot quietly redefine success. The
full protocol here is broader than the focused four-policy recovery run
that has actually executed. E001 v1 mechanics and their persisted artifacts
keep their original protocol and interpretation untouched.
"""

from __future__ import annotations

from dataclasses import replace
from types import MappingProxyType

from .e001 import E001_PROTOCOL
from .protocols import (
    EvidenceRequirementSpec,
    ExperimentStage,
    MetricSpec,
)


E001_RECOVERY_V2_CANDIDATE_POLICY_ID = "adaptive-recovery"
E001_RECOVERY_V2_ORACLE_POLICY_ID = "future-trace-recovery-oracle"
E001_RECOVERY_V2_BASELINE_POLICY_IDS = (
    "synchronous-wait-restore",
    "fixed-local-checkpoint-restart",
    "fixed-cadence-reactive-membership",
    "power-aware-migration-without-learning-adaptation",
)
E001_RECOVERY_V2_COMPARATOR_POLICY_IDS = (
    *E001_RECOVERY_V2_BASELINE_POLICY_IDS,
    E001_RECOVERY_V2_ORACLE_POLICY_ID,
)
E001_RECOVERY_V2_POLICY_IDS = (
    E001_RECOVERY_V2_BASELINE_POLICY_IDS
    + (E001_RECOVERY_V2_CANDIDATE_POLICY_ID,)
    + (E001_RECOVERY_V2_ORACLE_POLICY_ID,)
)
E001_PARENT_BASELINE_OBLIGATION_IDS = (
    "single-site-centralized-equivalent-capacity",
    "fixed-sparse-gossip",
)
E001_RECOVERY_V2_POLICY_ROLES = MappingProxyType(
    {
        policy_id: (
            "candidate"
            if policy_id == E001_RECOVERY_V2_CANDIDATE_POLICY_ID
            else "oracle_comparator"
            if policy_id == E001_RECOVERY_V2_ORACLE_POLICY_ID
            else "baseline"
        )
        for policy_id in E001_RECOVERY_V2_POLICY_IDS
    }
)


def _parent_metric(name: str) -> MetricSpec:
    return next(metric for metric in E001_PROTOCOL.metrics if metric.name == name)


_RECOVERY_TRAFFIC_METRICS = (
    MetricSpec(
        "completed_collective_link_bytes",
        "byte",
        "Link-direction bytes in collective attempts that commit, including "
        "algorithm stages, protocol overhead, and replay collectives.",
    ),
    MetricSpec(
        "aborted_collective_link_bytes",
        "byte",
        "Link-direction bytes transmitted by collective attempts that do not "
        "commit.",
    ),
    MetricSpec(
        "remote_checkpoint_replication_link_bytes",
        "byte",
        "Link-direction bytes used to write checkpoint shards across sites.",
    ),
    MetricSpec(
        "remote_checkpoint_restore_link_bytes",
        "byte",
        "Link-direction bytes used to read checkpoint shards across sites.",
    ),
    MetricSpec(
        "recovery_state_redistribution_link_bytes",
        "byte",
        "Link-direction bytes used to hydrate or reshard state for recovery.",
    ),
    MetricSpec(
        "planned_state_migration_link_bytes",
        "byte",
        "Link-direction bytes used for non-recovery planned state migration.",
    ),
)


_RECOVERY_METRICS = (
    MetricSpec(
        "collective_payload_byte_fraction",
        "1",
        "Diagnostic v1-style payload ratio only; it is not a recovery-v2 pass gate.",
    ),
    MetricSpec(
        "attempted_collective_link_bytes",
        "byte",
        "Derived diagnostic equal to completed_collective_link_bytes plus "
        "aborted_collective_link_bytes; it is not a seventh traffic class.",
    ),
    MetricSpec(
        "total_inter_site_link_bytes",
        "byte",
        "Exact sum of the six registered, disjoint physical link-direction "
        "traffic classes in the run; every serialized segment has one class.",
    ),
    MetricSpec(
        "synchronous_recovery_baseline_total_inter_site_link_bytes",
        "byte",
        "Matched synchronous-wait-restore total over the same absolute-time trace "
        "and terminal durable-frontier target.",
    ),
    MetricSpec(
        "total_inter_site_byte_fraction",
        "1",
        "Candidate total inter-site link bytes divided by the matched synchronous "
        "recovery baseline total.",
        True,
    ),
    *_RECOVERY_TRAFFIC_METRICS,
    MetricSpec(
        "attempted_compute_flops",
        "FLOP",
        "All physically executed compute.",
    ),
    MetricSpec(
        "valid_final_state_compute_flops",
        "FLOP",
        "Executed compute retained by the terminal durable training-state lineage.",
    ),
    MetricSpec(
        "lost_compute_flops",
        "FLOP",
        "Executed compute invalidated by preemption, failure, or rollback.",
    ),
    MetricSpec(
        "replay_compute_flops",
        "FLOP",
        "Executed compute labeled as replay; a subset of attempted compute.",
    ),
    MetricSpec(
        "checkpoint_restore_bytes",
        "byte",
        "All local and remote bytes read from a committed checkpoint manifest.",
    ),
    MetricSpec(
        "checkpoint_write_bytes",
        "byte",
        "All physically written local and remote checkpoint bytes, including "
        "writes belonging to attempts that never atomically commit.",
    ),
    MetricSpec(
        "partial_checkpoint_write_bytes",
        "byte",
        "Checkpoint-write bytes from attempts without an atomic manifest commit; "
        "a subset of checkpoint_write_bytes.",
    ),
    MetricSpec(
        "membership_removed_site_ns",
        "site*ns",
        "Integrated desired-member time excluded from effective execution "
        "membership.",
    ),
    MetricSpec(
        "recovery_debt_ns",
        "ns",
        "Signed time difference for actual and matched no-failure runs to reach one "
        "identical frozen durable-frontier target, with the actual anchor after "
        "failure.",
    ),
    MetricSpec(
        "recovery_episode_count",
        "1",
        "Number of joint recovery episodes after overlapping or repeated failures "
        "before durable recovery are bundled under the frozen episode rule.",
    ),
)


_BASE_METRICS_BY_NAME = {metric.name: metric for metric in E001_PROTOCOL.metrics}
_UNCHANGED_PARENT_METRIC_NAMES = tuple(
    name
    for name in _BASE_METRICS_BY_NAME
    if name not in {"collective_payload_byte_fraction", "policy_decision_regret"}
)


def _requirement(requirement_id: str) -> EvidenceRequirementSpec:
    return next(
        requirement
        for requirement in E001_PROTOCOL.evidence_requirements
        if requirement.requirement_id == requirement_id
    )


_PARENT_REQUIREMENTS = (
    replace(
        _requirement("e001-baseline-vector-superiority"),
        required_metrics=(
            "progress_per_flop_ratio",
            "total_inter_site_byte_fraction",
            "completion_time_ratio",
            "facility_energy_to_target_j",
            "peak_wan_demand_bytes_per_second",
            "unacceptable_quality_probability",
            "policy_decision_regret",
            "nominal_90_interval_coverage",
        ),
        comparison_baselines=(
            *E001_RECOVERY_V2_BASELINE_POLICY_IDS,
            *E001_PARENT_BASELINE_OBLIGATION_IDS,
        ),
    ),
    _requirement("e001-heldout-learning-transfer"),
    replace(
        _requirement("e001-full-boundary-nonreversal"),
        required_metrics=(
            "completion_time_ratio",
            "facility_energy_to_target_j",
            "total_inter_site_link_bytes",
            "checkpoint_restore_bytes",
            "lost_compute_flops",
            "replay_compute_flops",
        ),
        required_panels=(
            "normal operation",
            "interruption",
            "recovery",
            "complete recovery horizon",
            "dynamic network and storage energy",
            "host and cooling energy",
        ),
    ),
    _requirement("e001-joint-mechanism-completeness"),
    replace(
        _requirement("e001-baseline-completeness"),
        description=(
            "Every recovery comparator and the parent centralized and sparse-gossip "
            "obligations must execute on matched traces."
        ),
        required_metrics=(
            "total_inter_site_link_bytes",
            "synchronous_recovery_baseline_total_inter_site_link_bytes",
            "recovery_debt_ns",
        ),
        required_panels=E001_RECOVERY_V2_POLICY_IDS,
        comparison_baselines=(
            *E001_RECOVERY_V2_COMPARATOR_POLICY_IDS,
            *E001_PARENT_BASELINE_OBLIGATION_IDS,
        ),
        acceptance_rule=(
            "Every named comparator executes; adaptive-recovery remains the candidate, "
            "and no omitted comparator can support a superiority claim."
        ),
        evidence_boundary=(
            "Recovery-v2 completion does not waive centralized-equivalent or "
            "fixed-sparse-gossip parent-protocol obligations."
        ),
    ),
    _requirement("e001-heldout-panel-completeness"),
    replace(
        _requirement("e001-collective-and-failure-model-admission"),
        required_metrics=(
            "total_inter_site_link_bytes",
            "synchronous_recovery_baseline_total_inter_site_link_bytes",
            "total_inter_site_byte_fraction",
            "attempted_collective_link_bytes",
            "completed_collective_link_bytes",
            "aborted_collective_link_bytes",
            "remote_checkpoint_replication_link_bytes",
            "remote_checkpoint_restore_link_bytes",
            "recovery_state_redistribution_link_bytes",
            "planned_state_migration_link_bytes",
            "checkpoint_write_bytes",
            "partial_checkpoint_write_bytes",
            "peak_wan_demand_bytes_per_second",
        ),
        required_panels=(
            "algorithm-specific completed collective",
            "collective interruption during latency",
            "collective interruption during payload",
            "mid-operation compute failure",
            "rollback after committed work",
            "checkpoint restore",
            "replay accounting",
            "membership response",
            "state movement",
            "recovery debt",
        ),
        acceptance_rule=(
            "Unique link-segment accounting, preemption, rollback, restore, replay, "
            "membership, and debt panels must all pass before traffic or interruption "
            "metrics support E001."
        ),
        evidence_boundary=(
            "Payload-only bytes, additive overlapping categories, or whole-operation "
            "postponement are insufficient."
        ),
    ),
)


_RECOVERY_REQUIREMENTS = (
    EvidenceRequirementSpec(
        requirement_id="e001-observable-failure-recovery-epochs",
        kind="observable_transition_completeness",
        description=(
            "Physical occurrence and controller observation remain distinct for "
            "failure and recovery, with immutable checkpoint, restore, and "
            "re-entry epochs."
        ),
        earliest_resolvable_stage=ExperimentStage.VIRTUAL,
        required_metrics=("recovery_episode_count",),
        required_panels=(
            "failure occurrence",
            "failure observation",
            "recovery occurrence",
            "recovery observation",
            "checkpoint commit",
            "restore completion",
            "safe re-entry",
        ),
        acceptance_rule=(
            "Each nonempty material timestamp batch produces exactly one "
            "content-addressed decision state containing every transition in "
            "canonical order; candidate-visible state changes only after observation."
        ),
        evidence_boundary=(
            "A trace that postpones whole operations or exposes physical truth before "
            "controller observation fails this gate."
        ),
    ),
    EvidenceRequirementSpec(
        requirement_id="e001-reactive-membership-without-trace-leakage",
        kind="causal_policy_information_boundary",
        description=(
            "Candidate membership decisions use only controller-observed state while "
            "engine-private physical state safely constrains execution."
        ),
        earliest_resolvable_stage=ExperimentStage.VIRTUAL,
        required_metrics=("membership_removed_site_ns",),
        required_panels=(
            "immediate failure observation",
            "delayed failure observation",
            "unannounced recovery",
            "announced curtailment",
            "recovered-but-unrestored site",
            "repeated future-prefix comparison",
            "safe explicit re-entry",
        ),
        acceptance_rule=(
            "Candidate decisions and visible-state serializations are byte-identical "
            "through identical observable prefixes; effective execution membership "
            "contains only physically healthy, state-ready sites."
        ),
        evidence_boundary=(
            "Oracle trace access, scenario closure access, private physical-state "
            "leakage, or queued future metadata fails this gate."
        ),
    ),
    EvidenceRequirementSpec(
        requirement_id="e001-preemption-replay-conservation",
        kind="mechanical_accounting_conservation",
        description=(
            "Every executed compute portion and physical link segment has one terminal "
            "disposition without double counting across rollback and replay."
        ),
        earliest_resolvable_stage=ExperimentStage.VIRTUAL,
        required_metrics=(
            "attempted_compute_flops",
            "valid_final_state_compute_flops",
            "lost_compute_flops",
            "replay_compute_flops",
            "attempted_collective_link_bytes",
            "completed_collective_link_bytes",
            "aborted_collective_link_bytes",
        ),
        required_panels=(
            "compute interruption",
            "collective interruption during latency",
            "collective interruption during payload",
            "rollback after committed work",
            "restore",
            "replay",
            "repeated interruption during restore",
            "repeated interruption during replay",
        ),
        acceptance_rule=(
            "Attempted compute equals valid-final-state plus lost compute; replay is a "
            "labeled subset; attempted collective link bytes equal completed plus "
            "aborted disjoint segments; every executed portion is invalidated at "
            "most once."
        ),
        evidence_boundary=(
            "Scheduled totals without executed portions, final validity, and terminal "
            "attempt dispositions cannot satisfy this gate."
        ),
    ),
    EvidenceRequirementSpec(
        requirement_id="e001-checkpoint-lineage-and-restore",
        kind="state_lineage_completeness",
        description=(
            "Only atomic manifests with exact shards and model, optimizer, RNG, data, "
            "membership, and failure-domain lineage may restore state."
        ),
        earliest_resolvable_stage=ExperimentStage.VIRTUAL,
        required_metrics=(
            "checkpoint_restore_bytes",
            "checkpoint_write_bytes",
            "partial_checkpoint_write_bytes",
            "remote_checkpoint_replication_link_bytes",
            "remote_checkpoint_restore_link_bytes",
        ),
        required_panels=(
            "complete checkpoint",
            "checkpoint/failure timestamp tie",
            "partial checkpoint",
            "failed local checkpoint storage",
            "remote durable checkpoint",
            "genesis rollback",
            "restored model optimizer RNG and data lineage",
        ),
        acceptance_rule=(
            "A restore references one complete content-addressed manifest; exact shard "
            "bytes and hashes reconstruct its declared state, and same-time storage "
            "failure is applied after commit but can still destroy a "
            "non-surviving shard."
        ),
        evidence_boundary=(
            "Checkpoint byte counts or partial shard writes without a surviving atomic "
            "manifest are not recovery evidence."
        ),
    ),
    EvidenceRequirementSpec(
        requirement_id="e001-recovery-baseline-completeness",
        kind="recovery_baseline_completeness",
        description=(
            "All six recovery policies execute on matched absolute-time traces, "
            "checkpoint triggers, state sizes, seeds, sample order, and accounting."
        ),
        earliest_resolvable_stage=ExperimentStage.VIRTUAL,
        required_metrics=(
            "total_inter_site_link_bytes",
            "synchronous_recovery_baseline_total_inter_site_link_bytes",
            "total_inter_site_byte_fraction",
            "recovery_debt_ns",
        ),
        required_panels=E001_RECOVERY_V2_POLICY_IDS,
        comparison_baselines=E001_RECOVERY_V2_COMPARATOR_POLICY_IDS,
        acceptance_rule=(
            "Every recovery comparator executes on the same absolute-time trace and "
            "terminal durable-frontier target; adaptive-recovery is labeled candidate."
        ),
        evidence_boundary=(
            "The future-trace policy is an oracle comparator only. Policy-decision "
            "regret remains unresolved until a scalar objective is separately frozen."
        ),
    ),
)


E001_RECOVERY_V2_PROTOCOL = replace(
    E001_PROTOCOL,
    experiment_id="E001-RECOVERY-V2",
    title="Beyond One Datacenter: Recovery Mechanics v2",
    baselines=(
        *E001_RECOVERY_V2_COMPARATOR_POLICY_IDS,
        *E001_PARENT_BASELINE_OBLIGATION_IDS,
    ),
    metrics=(
        *(_parent_metric(name) for name in _UNCHANGED_PARENT_METRIC_NAMES),
        replace(
            _parent_metric("policy_decision_regret"),
            description=(
                "Reserved parent-protocol metric; unresolved until a scalar policy "
                "objective, horizon, normalization, and oracle action space are frozen."
            ),
        ),
        *_RECOVERY_METRICS,
    ),
    falsifiers=tuple(
        replace(
            item,
            metric="total_inter_site_byte_fraction",
            description=(
                "More than 10% of the matched synchronous recovery baseline's unique "
                "physical inter-site link bytes fails the preregistered 10x reduction."
            ),
        )
        if item.falsifier_id == "e001-wan"
        else item
        for item in E001_PROTOCOL.falsifiers
    ),
    evidence_requirements=(*_PARENT_REQUIREMENTS, *_RECOVERY_REQUIREMENTS),
    notes=(
        *E001_PROTOCOL.notes,
        "The focused recovery-v2 runner executes four matched policies; the full "
        "six-policy comparator obligation remains unresolved.",
        "Checkpoint triggers are matched absolute wall-clock times; actual atomic "
        "commit times are serialized separately.",
        "Every physical link-direction segment has one traffic class; "
        "retransmissions retain their class and attempt id.",
        "Attempted collective link bytes equal completed plus aborted collective "
        "link bytes and are not an additional traffic class.",
        "Checkpoint-write diagnostics cover local and remote physical I/O; partial "
        "writes are a subset, while remote replication remains the only additive "
        "inter-site checkpoint-write traffic class.",
        "Recovery debt uses one serialized shared durable-frontier target and an "
        "actual post-failure anchor.",
        "Overlapping or repeated causal failures form one joint recovery episode "
        "unless a separate marginal estimand is preregistered.",
        "Policy-decision regret is not a recovery mechanics result until its "
        "scalar objective is preregistered.",
    ),
)


__all__ = [
    "E001_PARENT_BASELINE_OBLIGATION_IDS",
    "E001_RECOVERY_V2_BASELINE_POLICY_IDS",
    "E001_RECOVERY_V2_CANDIDATE_POLICY_ID",
    "E001_RECOVERY_V2_COMPARATOR_POLICY_IDS",
    "E001_RECOVERY_V2_ORACLE_POLICY_ID",
    "E001_RECOVERY_V2_POLICY_IDS",
    "E001_RECOVERY_V2_POLICY_ROLES",
    "E001_RECOVERY_V2_PROTOCOL",
]
