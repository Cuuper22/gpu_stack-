"""Preregistered experiment protocols and falsification artifacts."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, Optional, Sequence, Tuple


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _mapping(values: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(values))


EXPERIMENT_RUN_SCHEMA = "gpu-stack.experiment-run.v2"


class ExperimentStage(str, Enum):
    DESIGNED = "designed"
    VIRTUAL = "virtual"
    SHADOW = "shadow"
    CONTROLLED = "controlled"
    VALIDATED = "validated"
    FALSIFIED = "falsified"
    INCONCLUSIVE = "inconclusive"


_STAGE_ORDER = {
    ExperimentStage.DESIGNED: 0,
    ExperimentStage.VIRTUAL: 1,
    ExperimentStage.SHADOW: 2,
    ExperimentStage.CONTROLLED: 3,
    ExperimentStage.VALIDATED: 4,
}


class ComparisonOperator(str, Enum):
    LT = "lt"
    LE = "le"
    GT = "gt"
    GE = "ge"
    BETWEEN = "between"


@dataclass(frozen=True)
class MetricSpec:
    name: str
    unit: str
    description: str
    primary: bool = False

    def __post_init__(self) -> None:
        for attr in ("name", "unit", "description"):
            if not str(getattr(self, attr)).strip():
                raise ValueError(f"metric {attr} must be non-blank")

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "unit": self.unit,
            "description": self.description,
            "primary": self.primary,
        }


@dataclass(frozen=True)
class FalsifierSpec:
    """A preregistered condition that the result must satisfy to survive."""

    falsifier_id: str
    metric: str
    operator: ComparisonOperator
    threshold: float
    upper_threshold: Optional[float] = None
    description: str = ""

    def __post_init__(self) -> None:
        if not self.falsifier_id.strip() or not self.metric.strip():
            raise ValueError("falsifier id and metric must be non-blank")
        if not math.isfinite(self.threshold):
            raise ValueError("falsifier threshold must be finite")
        if self.operator is ComparisonOperator.BETWEEN:
            if self.upper_threshold is None:
                raise ValueError("between falsifier requires upper_threshold")
            if not math.isfinite(self.upper_threshold):
                raise ValueError("falsifier upper_threshold must be finite")
            if self.threshold > self.upper_threshold:
                raise ValueError("falsifier thresholds are reversed")
        elif self.upper_threshold is not None:
            raise ValueError("upper_threshold is only valid with between")

    def survives(self, value: float) -> bool:
        if not math.isfinite(value):
            return False
        if self.operator is ComparisonOperator.LT:
            return value < self.threshold
        if self.operator is ComparisonOperator.LE:
            return value <= self.threshold
        if self.operator is ComparisonOperator.GT:
            return value > self.threshold
        if self.operator is ComparisonOperator.GE:
            return value >= self.threshold
        assert self.upper_threshold is not None
        return self.threshold <= value <= self.upper_threshold

    def to_dict(self) -> dict[str, object]:
        return {
            "falsifier_id": self.falsifier_id,
            "metric": self.metric,
            "operator": self.operator.value,
            "threshold": self.threshold,
            "upper_threshold": self.upper_threshold,
            "description": self.description,
        }


@dataclass(frozen=True)
class FalsifierResult:
    falsifier_id: str
    metric: str
    observed_value: Optional[float]
    survived: Optional[bool]
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "falsifier_id": self.falsifier_id,
            "metric": self.metric,
            "observed_value": self.observed_value,
            "survived": self.survived,
            "reason": self.reason,
        }


class EvidenceRequirementStatus(str, Enum):
    SATISFIED = "satisfied"
    FAILED = "failed"
    UNRESOLVED = "unresolved"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class EvidenceRequirementSpec:
    """Mandatory non-scalar gate that must not disappear into prose notes."""

    requirement_id: str
    kind: str
    description: str
    earliest_resolvable_stage: ExperimentStage
    acceptance_rule: str
    evidence_boundary: str
    required_metrics: Tuple[str, ...] = ()
    required_panels: Tuple[str, ...] = ()
    comparison_baselines: Tuple[str, ...] = ()
    mandatory: bool = True

    def __post_init__(self) -> None:
        for attr in (
            "requirement_id",
            "kind",
            "description",
            "acceptance_rule",
            "evidence_boundary",
        ):
            value = getattr(self, attr)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"evidence requirement {attr} must be non-blank")
            object.__setattr__(self, attr, value.strip())
        if not isinstance(self.earliest_resolvable_stage, ExperimentStage):
            raise TypeError("earliest_resolvable_stage must be ExperimentStage")
        if self.earliest_resolvable_stage not in _STAGE_ORDER:
            raise ValueError(
                "earliest_resolvable_stage must be designed, virtual, shadow, "
                "controlled, or validated"
            )
        if not isinstance(self.mandatory, bool):
            raise TypeError("evidence requirement mandatory must be bool")
        for attr in (
            "required_metrics",
            "required_panels",
            "comparison_baselines",
        ):
            values = tuple(getattr(self, attr))
            if any(not isinstance(item, str) or not item.strip() for item in values):
                raise ValueError(f"evidence requirement {attr} must be non-blank")
            normalized = tuple(item.strip() for item in values)
            if len(normalized) != len(set(normalized)):
                raise ValueError(f"evidence requirement {attr} must be unique")
            object.__setattr__(self, attr, normalized)

    def to_dict(self) -> dict[str, object]:
        return {
            "requirement_id": self.requirement_id,
            "kind": self.kind,
            "description": self.description,
            "mandatory": self.mandatory,
            "earliest_resolvable_stage": self.earliest_resolvable_stage.value,
            "required_metrics": list(self.required_metrics),
            "required_panels": list(self.required_panels),
            "comparison_baselines": list(self.comparison_baselines),
            "acceptance_rule": self.acceptance_rule,
            "evidence_boundary": self.evidence_boundary,
        }


@dataclass(frozen=True)
class EvidenceRequirementResult:
    """Resolution state for one structured protocol requirement."""

    requirement_id: str
    status: EvidenceRequirementStatus
    reason: str
    evidence_refs: Tuple[str, ...] = ()
    panel_results: Mapping[str, str] = field(default_factory=dict)
    scope_reason: Optional[str] = None

    def __post_init__(self) -> None:
        for attr in ("requirement_id", "reason"):
            value = getattr(self, attr)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"evidence result {attr} must be non-blank")
            object.__setattr__(self, attr, value.strip())
        if not isinstance(self.status, EvidenceRequirementStatus):
            raise TypeError("evidence result status must be EvidenceRequirementStatus")
        refs = tuple(self.evidence_refs)
        if any(not isinstance(item, str) or not item.strip() for item in refs):
            raise ValueError("evidence_refs must contain non-blank strings")
        refs = tuple(item.strip() for item in refs)
        if len(refs) != len(set(refs)):
            raise ValueError("evidence_refs must be unique")
        if self.status in {
            EvidenceRequirementStatus.SATISFIED,
            EvidenceRequirementStatus.FAILED,
        } and not refs:
            raise ValueError("satisfied or failed requirements need evidence_refs")
        object.__setattr__(self, "evidence_refs", refs)
        panels = dict(self.panel_results)
        if any(
            not isinstance(key, str)
            or not key.strip()
            or not isinstance(value, str)
            or not value.strip()
            for key, value in panels.items()
        ):
            raise ValueError("panel_results require non-blank string keys and values")
        object.__setattr__(
            self,
            "panel_results",
            MappingProxyType(
                dict(sorted((key.strip(), value.strip()) for key, value in panels.items()))
            ),
        )
        scope_reason = self.scope_reason
        if scope_reason is not None:
            if not isinstance(scope_reason, str) or not scope_reason.strip():
                raise ValueError("scope_reason must be non-blank when present")
            scope_reason = scope_reason.strip()
        if (
            self.status is EvidenceRequirementStatus.NOT_APPLICABLE
            and scope_reason is None
        ):
            raise ValueError("not_applicable requirements need a scope_reason")
        object.__setattr__(self, "scope_reason", scope_reason)

    def to_dict(self) -> dict[str, object]:
        return {
            "requirement_id": self.requirement_id,
            "status": self.status.value,
            "reason": self.reason,
            "evidence_refs": list(self.evidence_refs),
            "panel_results": dict(self.panel_results),
            "scope_reason": self.scope_reason,
        }


@dataclass(frozen=True)
class ExperimentProtocol:
    experiment_id: str
    title: str
    question: str
    hypothesis: str
    baselines: Tuple[str, ...]
    metrics: Tuple[MetricSpec, ...]
    falsifiers: Tuple[FalsifierSpec, ...]
    independent_variables: Tuple[str, ...]
    held_out_dimensions: Tuple[str, ...]
    real_validation_requirements: Tuple[str, ...]
    seed_policy: str
    source_window: str
    evidence_requirements: Tuple[EvidenceRequirementSpec, ...] = ()
    notes: Tuple[str, ...] = ()
    schema_version: str = "2.0"

    def __post_init__(self) -> None:
        for attr in (
            "experiment_id", "title", "question", "hypothesis",
            "seed_policy", "source_window", "schema_version",
        ):
            if not str(getattr(self, attr)).strip():
                raise ValueError(f"experiment {attr} must be non-blank")
        for attr in (
            "baselines", "metrics", "falsifiers", "independent_variables",
            "held_out_dimensions", "real_validation_requirements",
        ):
            values = tuple(getattr(self, attr))
            if not values:
                raise ValueError(f"experiment {attr} must not be empty")
            object.__setattr__(self, attr, values)
        metric_names = [metric.name for metric in self.metrics]
        if len(metric_names) != len(set(metric_names)):
            raise ValueError("experiment metric names must be unique")
        if not any(metric.primary for metric in self.metrics):
            raise ValueError("experiment requires at least one primary metric")
        unknown_falsifier_metrics = sorted(
            {item.metric for item in self.falsifiers} - set(metric_names)
        )
        if unknown_falsifier_metrics:
            raise ValueError(
                "falsifiers reference unknown metrics: "
                f"{unknown_falsifier_metrics}"
            )
        falsifier_ids = [item.falsifier_id for item in self.falsifiers]
        if len(falsifier_ids) != len(set(falsifier_ids)):
            raise ValueError("experiment falsifier ids must be unique")
        evidence_requirements = tuple(self.evidence_requirements)
        if any(
            not isinstance(item, EvidenceRequirementSpec)
            for item in evidence_requirements
        ):
            raise TypeError(
                "experiment evidence_requirements must contain "
                "EvidenceRequirementSpec values"
            )
        requirement_ids = [item.requirement_id for item in evidence_requirements]
        if len(requirement_ids) != len(set(requirement_ids)):
            raise ValueError("experiment evidence requirement ids must be unique")
        if set(requirement_ids) & set(falsifier_ids):
            raise ValueError(
                "scalar falsifier and evidence requirement ids must be distinct"
            )
        unknown_requirement_metrics = sorted(
            {
                metric
                for requirement in evidence_requirements
                for metric in requirement.required_metrics
            }
            - set(metric_names)
        )
        if unknown_requirement_metrics:
            raise ValueError(
                "evidence requirements reference unknown metrics: "
                f"{unknown_requirement_metrics}"
            )
        primary_metric_names = {
            metric.name for metric in self.metrics if metric.primary
        }
        covered_primary_metrics = {
            item.metric for item in self.falsifiers
        } | {
            metric
            for requirement in evidence_requirements
            if requirement.mandatory
            for metric in requirement.required_metrics
        }
        uncovered_primary_metrics = sorted(
            primary_metric_names - covered_primary_metrics
        )
        if uncovered_primary_metrics:
            raise ValueError(
                "primary metrics require a scalar falsifier or structured "
                f"evidence requirement: {uncovered_primary_metrics}"
            )
        object.__setattr__(
            self, "evidence_requirements", evidence_requirements
        )
        object.__setattr__(self, "notes", tuple(self.notes))

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "experiment_id": self.experiment_id,
            "title": self.title,
            "question": self.question,
            "hypothesis": self.hypothesis,
            "baselines": list(self.baselines),
            "metrics": [metric.to_dict() for metric in self.metrics],
            "falsifiers": [item.to_dict() for item in self.falsifiers],
            "independent_variables": list(self.independent_variables),
            "held_out_dimensions": list(self.held_out_dimensions),
            "real_validation_requirements": list(
                self.real_validation_requirements
            ),
            "seed_policy": self.seed_policy,
            "source_window": self.source_window,
            "evidence_requirements": [
                item.to_dict() for item in self.evidence_requirements
            ],
            "notes": list(self.notes),
        }

    def canonical_json(self) -> str:
        return _canonical(self.to_dict())

    @property
    def protocol_hash(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def evaluate_falsifiers(
        self, metrics: Mapping[str, float]
    ) -> Tuple[FalsifierResult, ...]:
        results = []
        for falsifier in self.falsifiers:
            if falsifier.metric not in metrics:
                results.append(
                    FalsifierResult(
                        falsifier.falsifier_id,
                        falsifier.metric,
                        None,
                        None,
                        "metric was not reported",
                    )
                )
                continue
            value = float(metrics[falsifier.metric])
            survived = falsifier.survives(value)
            results.append(
                FalsifierResult(
                    falsifier.falsifier_id,
                    falsifier.metric,
                    value,
                    survived,
                    "threshold survived" if survived else "threshold falsified",
                )
            )
        return tuple(results)

    def build_run_artifact(
        self,
        *,
        run_id: str,
        stage: ExperimentStage,
        policy: str,
        scenario_id: str,
        metrics: Mapping[str, float],
        requirement_results: Sequence[EvidenceRequirementResult] = (),
        calibration_observation_ids: Sequence[str] = (),
        evaluation_observation_ids: Sequence[str] = (),
        assumptions: Sequence[str] = (),
        evidence_gaps: Sequence[str] = (),
        trace_uri: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> "ExperimentRunArtifact":
        """Bind a run to every scalar and structured gate in this protocol."""

        if not isinstance(stage, ExperimentStage):
            raise TypeError("stage must be ExperimentStage")
        if stage not in _STAGE_ORDER or stage is ExperimentStage.DESIGNED:
            raise ValueError(
                "run artifact stage must be virtual, shadow, controlled, or validated"
            )
        provided: dict[str, EvidenceRequirementResult] = {}
        for result in requirement_results:
            if not isinstance(result, EvidenceRequirementResult):
                raise TypeError(
                    "requirement_results must contain EvidenceRequirementResult values"
                )
            if result.requirement_id in provided:
                raise ValueError(
                    f"duplicate evidence requirement result {result.requirement_id!r}"
                )
            provided[result.requirement_id] = result
        known_ids = {item.requirement_id for item in self.evidence_requirements}
        unknown_ids = sorted(set(provided) - known_ids)
        if unknown_ids:
            raise ValueError(
                f"unknown evidence requirement results: {unknown_ids}"
            )

        resolved_results = []
        for spec in self.evidence_requirements:
            result = provided.get(spec.requirement_id)
            if result is None:
                result = EvidenceRequirementResult(
                    requirement_id=spec.requirement_id,
                    status=EvidenceRequirementStatus.UNRESOLVED,
                    reason=(
                        "not evaluated; earliest resolvable stage is "
                        f"{spec.earliest_resolvable_stage.value}"
                    ),
                )
            elif (
                result.status
                in {
                    EvidenceRequirementStatus.SATISFIED,
                    EvidenceRequirementStatus.FAILED,
                }
                and _STAGE_ORDER[stage]
                < _STAGE_ORDER[spec.earliest_resolvable_stage]
            ):
                raise ValueError(
                    f"requirement {spec.requirement_id!r} cannot resolve at "
                    f"stage {stage.value}; earliest is "
                    f"{spec.earliest_resolvable_stage.value}"
                )
            if result.status is EvidenceRequirementStatus.SATISFIED:
                missing_metrics = sorted(
                    set(spec.required_metrics) - set(metrics)
                )
                missing_panels = sorted(
                    set(spec.required_panels) - set(result.panel_results)
                )
                if missing_metrics or missing_panels:
                    raise ValueError(
                        f"satisfied requirement {spec.requirement_id!r} is "
                        "missing required evidence; "
                        f"metrics={missing_metrics}, panels={missing_panels}"
                    )
            if (
                result.status is EvidenceRequirementStatus.FAILED
                and spec.required_panels
                and not any(
                    value == EvidenceRequirementStatus.FAILED.value
                    for value in result.panel_results.values()
                )
            ):
                raise ValueError(
                    f"failed requirement {spec.requirement_id!r} must identify "
                    "at least one failed panel"
                )
            resolved_results.append(result)

        return ExperimentRunArtifact(
            run_id=run_id,
            protocol_hash=self.protocol_hash,
            experiment_id=self.experiment_id,
            stage=stage,
            policy=policy,
            scenario_id=scenario_id,
            metrics=metrics,
            falsifiers=self.evaluate_falsifiers(metrics),
            evidence_requirements=tuple(resolved_results),
            protocol_snapshot_json=self.canonical_json(),
            calibration_observation_ids=tuple(calibration_observation_ids),
            evaluation_observation_ids=tuple(evaluation_observation_ids),
            assumptions=tuple(assumptions),
            evidence_gaps=tuple(evidence_gaps),
            trace_uri=trace_uri,
            metadata={} if metadata is None else metadata,
        )


@dataclass(frozen=True)
class ExperimentRunArtifact:
    run_id: str
    protocol_hash: str
    experiment_id: str
    stage: ExperimentStage
    policy: str
    scenario_id: str
    metrics: Mapping[str, float]
    falsifiers: Tuple[FalsifierResult, ...]
    evidence_requirements: Tuple[EvidenceRequirementResult, ...]
    protocol_snapshot_json: str
    protocol_falsifier_ids: Tuple[str, ...] = field(init=False)
    protocol_requirement_ids: Tuple[str, ...] = field(init=False)
    mandatory_requirement_ids: Tuple[str, ...] = field(init=False)
    calibration_observation_ids: Tuple[str, ...] = ()
    evaluation_observation_ids: Tuple[str, ...] = ()
    assumptions: Tuple[str, ...] = ()
    evidence_gaps: Tuple[str, ...] = ()
    trace_uri: Optional[str] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for attr in ("run_id", "protocol_hash", "experiment_id", "policy", "scenario_id"):
            value = getattr(self, attr)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"run {attr} must be non-blank")
            object.__setattr__(self, attr, value.strip())
        if (
            len(self.protocol_hash) != 64
            or any(character not in "0123456789abcdef" for character in self.protocol_hash)
        ):
            raise ValueError("run protocol_hash must be lowercase SHA-256")
        if not isinstance(self.stage, ExperimentStage):
            raise TypeError("run stage must be ExperimentStage")
        if self.stage not in _STAGE_ORDER or self.stage is ExperimentStage.DESIGNED:
            raise ValueError(
                "run stage must be virtual, shadow, controlled, or validated"
            )
        if not isinstance(self.protocol_snapshot_json, str) or not self.protocol_snapshot_json.strip():
            raise ValueError("protocol_snapshot_json must be non-blank")
        try:
            protocol_snapshot = json.loads(self.protocol_snapshot_json)
        except json.JSONDecodeError as exc:
            raise ValueError("protocol_snapshot_json must contain valid JSON") from exc
        if not isinstance(protocol_snapshot, dict):
            raise ValueError("protocol_snapshot_json must contain a JSON object")
        canonical_protocol_snapshot = _canonical(protocol_snapshot)
        snapshot_hash = hashlib.sha256(
            canonical_protocol_snapshot.encode("utf-8")
        ).hexdigest()
        if snapshot_hash != self.protocol_hash:
            raise ValueError("protocol snapshot does not match protocol_hash")
        if protocol_snapshot.get("experiment_id") != self.experiment_id:
            raise ValueError("protocol snapshot experiment_id does not match run")
        raw_falsifiers = protocol_snapshot.get("falsifiers")
        raw_requirements = protocol_snapshot.get("evidence_requirements", [])
        if not isinstance(raw_falsifiers, list) or not isinstance(raw_requirements, list):
            raise ValueError(
                "protocol snapshot falsifiers and evidence_requirements must be lists"
            )
        try:
            falsifier_snapshots = {
                str(item["falsifier_id"]): item for item in raw_falsifiers
            }
            requirement_snapshots = {
                str(item["requirement_id"]): item for item in raw_requirements
            }
            protocol_falsifier_ids = tuple(
                str(item["falsifier_id"]) for item in raw_falsifiers
            )
            protocol_requirement_ids = tuple(
                str(item["requirement_id"]) for item in raw_requirements
            )
            mandatory_requirement_ids = tuple(
                str(item["requirement_id"])
                for item in raw_requirements
                if item.get("mandatory") is True
            )
        except (AttributeError, KeyError, TypeError) as exc:
            raise ValueError("protocol snapshot gate records are malformed") from exc
        object.__setattr__(
            self, "protocol_snapshot_json", canonical_protocol_snapshot
        )
        object.__setattr__(
            self, "protocol_falsifier_ids", protocol_falsifier_ids
        )
        object.__setattr__(
            self, "protocol_requirement_ids", protocol_requirement_ids
        )
        object.__setattr__(
            self, "mandatory_requirement_ids", mandatory_requirement_ids
        )
        calibration_ids = tuple(self.calibration_observation_ids)
        evaluation_ids = tuple(self.evaluation_observation_ids)
        for label, identifiers in (
            ("calibration", calibration_ids),
            ("evaluation", evaluation_ids),
        ):
            if (
                any(not isinstance(item, str) or not item.strip() for item in identifiers)
                or len(identifiers) != len(set(identifiers))
            ):
                raise ValueError(
                    f"run {label} observation IDs must be unique and non-blank"
                )
        object.__setattr__(self, "calibration_observation_ids", calibration_ids)
        object.__setattr__(self, "evaluation_observation_ids", evaluation_ids)
        if set(calibration_ids) & set(evaluation_ids):
            raise ValueError("run calibration and evaluation observations overlap")
        values = {name: float(value) for name, value in self.metrics.items()}
        if any(not name.strip() or not math.isfinite(value) for name, value in values.items()):
            raise ValueError("run metrics require non-blank names and finite values")
        object.__setattr__(self, "metrics", _mapping(values))
        falsifiers = tuple(self.falsifiers)
        if any(not isinstance(item, FalsifierResult) for item in falsifiers):
            raise TypeError("run falsifiers must contain FalsifierResult values")
        falsifier_ids = [item.falsifier_id for item in falsifiers]
        if len(falsifier_ids) != len(set(falsifier_ids)):
            raise ValueError("run falsifier result ids must be unique")
        if (
            not protocol_falsifier_ids
            or any(not isinstance(item, str) or not item.strip() for item in protocol_falsifier_ids)
            or len(protocol_falsifier_ids) != len(set(protocol_falsifier_ids))
        ):
            raise ValueError(
                "protocol_falsifier_ids must be unique non-blank identifiers"
            )
        if set(falsifier_ids) != set(protocol_falsifier_ids):
            raise ValueError(
                "run falsifier results must exactly match protocol_falsifier_ids"
            )
        for result in falsifiers:
            spec = falsifier_snapshots[result.falsifier_id]
            expected_metric = spec.get("metric")
            if result.metric != expected_metric:
                raise ValueError(
                    f"falsifier {result.falsifier_id!r} metric does not match protocol"
                )
            if expected_metric not in values:
                if result.observed_value is not None or result.survived is not None:
                    raise ValueError(
                        f"falsifier {result.falsifier_id!r} must be unresolved "
                        "when its metric is absent"
                    )
                continue
            observed_value = float(result.observed_value)
            if not math.isfinite(observed_value) or not math.isclose(
                observed_value,
                values[expected_metric],
                rel_tol=1e-12,
                abs_tol=1e-12,
            ):
                raise ValueError(
                    f"falsifier {result.falsifier_id!r} observed value does not "
                    "match run metrics"
                )
            try:
                operator = ComparisonOperator(spec["operator"])
                threshold = float(spec["threshold"])
                upper_threshold = spec.get("upper_threshold")
                expected_survival = FalsifierSpec(
                    falsifier_id=result.falsifier_id,
                    metric=result.metric,
                    operator=operator,
                    threshold=threshold,
                    upper_threshold=(
                        None
                        if upper_threshold is None
                        else float(upper_threshold)
                    ),
                ).survives(observed_value)
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(
                    f"protocol falsifier {result.falsifier_id!r} is malformed"
                ) from exc
            if result.survived is not expected_survival:
                raise ValueError(
                    f"falsifier {result.falsifier_id!r} survival state does not "
                    "match its preregistered threshold"
                )
        object.__setattr__(self, "falsifiers", falsifiers)
        object.__setattr__(
            self, "protocol_falsifier_ids", protocol_falsifier_ids
        )
        evidence_requirements = tuple(self.evidence_requirements)
        if any(
            not isinstance(item, EvidenceRequirementResult)
            for item in evidence_requirements
        ):
            raise TypeError(
                "run evidence_requirements must contain "
                "EvidenceRequirementResult values"
            )
        result_requirement_ids = [
            item.requirement_id for item in evidence_requirements
        ]
        if len(result_requirement_ids) != len(set(result_requirement_ids)):
            raise ValueError("run evidence requirement result ids must be unique")
        if (
            any(not isinstance(item, str) or not item.strip() for item in protocol_requirement_ids)
            or len(protocol_requirement_ids) != len(set(protocol_requirement_ids))
        ):
            raise ValueError(
                "protocol_requirement_ids must be unique non-blank identifiers"
            )
        if set(result_requirement_ids) != set(protocol_requirement_ids):
            raise ValueError(
                "run evidence requirement results must exactly match "
                "protocol_requirement_ids"
            )
        for result in evidence_requirements:
            spec = requirement_snapshots[result.requirement_id]
            try:
                earliest_stage = ExperimentStage(
                    spec["earliest_resolvable_stage"]
                )
                required_metrics = set(spec.get("required_metrics", ()))
                required_panels = set(spec.get("required_panels", ()))
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(
                    f"protocol evidence requirement {result.requirement_id!r} "
                    "is malformed"
                ) from exc
            if (
                result.status
                in {
                    EvidenceRequirementStatus.SATISFIED,
                    EvidenceRequirementStatus.FAILED,
                }
                and _STAGE_ORDER[self.stage] < _STAGE_ORDER[earliest_stage]
            ):
                raise ValueError(
                    f"requirement {result.requirement_id!r} resolves before its "
                    "earliest preregistered stage"
                )
            if result.status is EvidenceRequirementStatus.SATISFIED:
                if not required_metrics <= set(values) or not required_panels <= set(
                    result.panel_results
                ):
                    raise ValueError(
                        f"satisfied requirement {result.requirement_id!r} lacks "
                        "required metrics or panels"
                    )
            if (
                result.status is EvidenceRequirementStatus.FAILED
                and required_panels
                and not any(
                    value == EvidenceRequirementStatus.FAILED.value
                    for value in result.panel_results.values()
                )
            ):
                raise ValueError(
                    f"failed requirement {result.requirement_id!r} does not "
                    "identify a failed panel"
                )
        if (
            any(not isinstance(item, str) or not item.strip() for item in mandatory_requirement_ids)
            or len(mandatory_requirement_ids) != len(set(mandatory_requirement_ids))
        ):
            raise ValueError(
                "mandatory_requirement_ids must be unique non-blank identifiers"
            )
        if not set(mandatory_requirement_ids) <= set(protocol_requirement_ids):
            raise ValueError(
                "mandatory_requirement_ids must be a subset of protocol requirements"
            )
        object.__setattr__(self, "evidence_requirements", evidence_requirements)
        object.__setattr__(
            self, "protocol_requirement_ids", protocol_requirement_ids
        )
        object.__setattr__(
            self, "mandatory_requirement_ids", mandatory_requirement_ids
        )
        assumptions = tuple(self.assumptions)
        if any(not isinstance(item, str) or not item.strip() for item in assumptions):
            raise ValueError("run assumptions must be non-blank strings")
        object.__setattr__(self, "assumptions", assumptions)
        evidence_gaps = tuple(str(item).strip() for item in self.evidence_gaps)
        if any(not item for item in evidence_gaps):
            raise ValueError("run evidence gaps must be non-blank")
        object.__setattr__(self, "evidence_gaps", evidence_gaps)
        if self.trace_uri is not None and (
            not isinstance(self.trace_uri, str) or not self.trace_uri.strip()
        ):
            raise ValueError("run trace_uri must be non-blank when present")
        if isinstance(self.trace_uri, str):
            object.__setattr__(self, "trace_uri", self.trace_uri.strip())
        try:
            canonical_metadata = json.loads(_canonical(dict(self.metadata)))
        except (TypeError, ValueError) as exc:
            raise ValueError("run metadata must be finite JSON data") from exc
        object.__setattr__(self, "metadata", _mapping(canonical_metadata))

    @property
    def conclusion(self) -> str:
        states = tuple(result.survived for result in self.falsifiers)
        mandatory_results = {
            result.requirement_id: result
            for result in self.evidence_requirements
            if result.requirement_id in self.mandatory_requirement_ids
        }
        if any(state is False for state in states) or any(
            result.status is EvidenceRequirementStatus.FAILED
            for result in mandatory_results.values()
        ):
            return (
                "failed_virtual_screen"
                if self.stage is ExperimentStage.VIRTUAL
                else "falsified"
            )
        if (
            self.evidence_gaps
            or any(state is None for state in states)
            or any(
                result.status
                in {
                    EvidenceRequirementStatus.UNRESOLVED,
                    EvidenceRequirementStatus.NOT_APPLICABLE,
                }
                for result in mandatory_results.values()
            )
        ):
            return "inconclusive"
        if states and all(state is True for state in states) and all(
            result.status is EvidenceRequirementStatus.SATISFIED
            for result in mandatory_results.values()
        ):
            return (
                "survived_virtual_screen"
                if self.stage is ExperimentStage.VIRTUAL
                else f"survived_{self.stage.value}"
            )
        return "inconclusive"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": EXPERIMENT_RUN_SCHEMA,
            "run_id": self.run_id,
            "protocol_hash": self.protocol_hash,
            "protocol": json.loads(self.protocol_snapshot_json),
            "experiment_id": self.experiment_id,
            "stage": self.stage.value,
            "policy": self.policy,
            "scenario_id": self.scenario_id,
            "metrics": dict(sorted(self.metrics.items())),
            "falsifiers": [item.to_dict() for item in self.falsifiers],
            "protocol_falsifier_ids": list(self.protocol_falsifier_ids),
            "evidence_requirements": [
                item.to_dict() for item in self.evidence_requirements
            ],
            "protocol_requirement_ids": list(self.protocol_requirement_ids),
            "mandatory_requirement_ids": list(self.mandatory_requirement_ids),
            "calibration_observation_ids": list(self.calibration_observation_ids),
            "evaluation_observation_ids": list(self.evaluation_observation_ids),
            "assumptions": list(self.assumptions),
            "evidence_gaps": list(self.evidence_gaps),
            "trace_uri": self.trace_uri,
            "metadata": dict(self.metadata),
            "conclusion": self.conclusion,
        }

    def canonical_json(self) -> str:
        return _canonical(self.to_dict())


__all__ = [
    "ComparisonOperator",
    "EvidenceRequirementSpec",
    "EvidenceRequirementResult",
    "EvidenceRequirementStatus",
    "EXPERIMENT_RUN_SCHEMA",
    "ExperimentProtocol",
    "ExperimentRunArtifact",
    "ExperimentStage",
    "FalsifierResult",
    "FalsifierSpec",
    "MetricSpec",
]
