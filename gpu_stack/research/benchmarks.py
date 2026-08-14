"""Leakage-safe held-out benchmarks for GPUSTACK prediction backends.

A benchmark here measures the thing the research program actually needs:
does a model predict unseen configurations well enough to choose the right
intervention? Leakage-safe means the observations used to calibrate a model
are strictly separated from the ones used to evaluate it. Beyond residuals
and interval coverage, ranking error and decision regret are first-class
outputs — merely producing a resolved number does not count as success.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from statistics import fmean, median
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Tuple

from .backends import (
    BackendCapability,
    CompositeWorldModel,
    PredictionEstimate,
    PredictionRequest,
    WorldModelBackend,
)
from .evaluation import (
    DecisionRegret,
    IntervalCoverage,
    KendallTauB,
    PredictionInterval,
    PredictionRecord,
    RankingCorrelation,
    ResidualMetrics,
    configuration_ranking_correlation,
    configuration_kendall_tau_b,
    decision_regret,
    evaluate_predictions,
    summarize_interval_coverage,
)
from .observations import CalibrationEvaluationSplit, Observation


def _nonblank(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-blank string")
    return value.strip()


@dataclass(frozen=True)
class BenchmarkAggregation:
    """Preregistered reducer and independent-cluster boundary for decisions."""

    reducer: str = "mean"
    cluster_boundary: str = "case_id"

    def __post_init__(self) -> None:
        reducer = _nonblank(self.reducer, "aggregation reducer").lower()
        if reducer not in {"mean", "median"}:
            raise ValueError("aggregation reducer must be 'mean' or 'median'")
        object.__setattr__(self, "reducer", reducer)
        object.__setattr__(
            self,
            "cluster_boundary",
            _nonblank(self.cluster_boundary, "aggregation cluster_boundary"),
        )

    def reduce(self, values: Iterable[float]) -> float:
        """Reduce one frozen replicate or cluster collection."""
        values = tuple(values)
        if not values:
            raise ValueError("aggregation requires at least one value")
        for value in values:
            if isinstance(value, bool):
                raise TypeError("aggregation values must be real numbers")
            if not math.isfinite(float(value)):
                raise ValueError("aggregation values must be finite")
        if self.reducer == "mean":
            return float(fmean(values))
        return float(median(values))

    def to_dict(self) -> dict[str, str]:
        return {
            "cluster_boundary": self.cluster_boundary,
            "reducer": self.reducer,
        }


@dataclass(frozen=True)
class BenchmarkCase:
    """One held-out observation and the exact request made of the model."""

    case_id: str
    observation_id: str
    configuration_id: str
    request: PredictionRequest
    cluster_id: str | None = None

    def __post_init__(self) -> None:
        for name in ("case_id", "observation_id", "configuration_id"):
            object.__setattr__(self, name, _nonblank(getattr(self, name), name))
        if not isinstance(self.request, PredictionRequest):
            raise TypeError("benchmark request must be a PredictionRequest")
        cluster_id = self.case_id if self.cluster_id is None else self.cluster_id
        object.__setattr__(self, "cluster_id", _nonblank(cluster_id, "cluster_id"))

    def to_dict(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "observation_id": self.observation_id,
            "configuration_id": self.configuration_id,
            "cluster_id": self.cluster_id,
            "request": self.request.to_dict(),
        }


@dataclass(frozen=True)
class BenchmarkDefinition:
    """Frozen held-out benchmark contract for one decision metric."""

    benchmark_id: str
    metric: str
    objective: str
    split: CalibrationEvaluationSplit
    cases: Tuple[BenchmarkCase, ...]
    description: str = ""
    held_out_dimensions: Tuple[str, ...] = ()
    aggregation: BenchmarkAggregation | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "benchmark_id", _nonblank(self.benchmark_id, "benchmark_id"))
        object.__setattr__(self, "metric", _nonblank(self.metric, "metric"))
        if self.objective not in {"minimize", "maximize"}:
            raise ValueError("benchmark objective must be 'minimize' or 'maximize'")
        if not isinstance(self.split, CalibrationEvaluationSplit):
            raise TypeError("benchmark split must be a CalibrationEvaluationSplit")
        cases = tuple(self.cases)
        if not cases:
            raise ValueError("benchmark requires at least one evaluation case")
        if not all(isinstance(case, BenchmarkCase) for case in cases):
            raise TypeError("benchmark cases must contain BenchmarkCase values")
        case_ids = [case.case_id for case in cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("benchmark case IDs must be unique")
        configuration_ids = [case.configuration_id for case in cases]
        has_replicates = len(configuration_ids) != len(set(configuration_ids))
        aggregation = self.aggregation
        if aggregation is None:
            if has_replicates:
                raise ValueError(
                    "repeated benchmark configurations require an explicit "
                    "preregistered aggregation reducer and cluster boundary"
                )
            aggregation = BenchmarkAggregation()
        elif not isinstance(aggregation, BenchmarkAggregation):
            raise TypeError("benchmark aggregation must be a BenchmarkAggregation")
        evaluation_ids = set(self.split.evaluation_ids)
        non_evaluation = sorted(
            case.observation_id for case in cases
            if case.observation_id not in evaluation_ids
        )
        if non_evaluation:
            raise ValueError(
                "benchmark cases must use only evaluation observations; "
                f"invalid IDs={non_evaluation}"
            )
        mismatched_targets = sorted(
            case.request.target for case in cases
            if case.request.target != self.metric
        )
        if mismatched_targets:
            raise ValueError(
                "benchmark request targets must match metric; "
                f"mismatches={mismatched_targets}"
            )
        object.__setattr__(self, "cases", cases)
        object.__setattr__(self, "aggregation", aggregation)
        object.__setattr__(
            self,
            "held_out_dimensions",
            tuple(_nonblank(item, "held_out_dimension") for item in self.held_out_dimensions),
        )

    @property
    def higher_is_better(self) -> bool:
        return self.objective == "maximize"

    def to_dict(self) -> dict[str, object]:
        return {
            "benchmark_id": self.benchmark_id,
            "metric": self.metric,
            "objective": self.objective,
            "description": self.description,
            "held_out_dimensions": list(self.held_out_dimensions),
            "aggregation": self.aggregation.to_dict(),
            "split": self.split.to_dict(),
            "cases": [case.to_dict() for case in self.cases],
        }


@dataclass(frozen=True)
class ConfigurationAggregate:
    """One configuration after replicate-to-cluster-to-configuration reduction."""

    configuration_id: str
    replicate_count: int
    predicted_value: float
    observed_value: float
    cluster_predicted_values: Mapping[str, float]
    cluster_observed_values: Mapping[str, float]

    def __post_init__(self) -> None:
        configuration_id = _nonblank(self.configuration_id, "configuration_id")
        if (
            isinstance(self.replicate_count, bool)
            or not isinstance(self.replicate_count, int)
            or self.replicate_count < 1
        ):
            raise ValueError("replicate_count must be a positive integer")
        predicted = dict(self.cluster_predicted_values)
        observed = dict(self.cluster_observed_values)
        if not predicted or set(predicted) != set(observed):
            raise ValueError(
                "cluster prediction and observation mappings must be non-empty "
                "and contain identical cluster IDs"
            )
        normalized_predicted = {}
        normalized_observed = {}
        for cluster_id in sorted(predicted):
            normalized_id = _nonblank(cluster_id, "cluster_id")
            if normalized_id in normalized_predicted:
                raise ValueError(
                    f"duplicate normalized cluster ID {normalized_id!r}"
                )
            predicted_value = float(predicted[cluster_id])
            observed_value = float(observed[cluster_id])
            if not math.isfinite(predicted_value) or not math.isfinite(observed_value):
                raise ValueError("cluster aggregate values must be finite")
            normalized_predicted[normalized_id] = predicted_value
            normalized_observed[normalized_id] = observed_value
        if self.replicate_count < len(normalized_predicted):
            raise ValueError("replicate_count cannot be smaller than cluster_count")
        predicted_value = float(self.predicted_value)
        observed_value = float(self.observed_value)
        if not math.isfinite(predicted_value) or not math.isfinite(observed_value):
            raise ValueError("configuration aggregate values must be finite")
        object.__setattr__(self, "configuration_id", configuration_id)
        object.__setattr__(self, "predicted_value", predicted_value)
        object.__setattr__(self, "observed_value", observed_value)
        object.__setattr__(
            self,
            "cluster_predicted_values",
            MappingProxyType(normalized_predicted),
        )
        object.__setattr__(
            self,
            "cluster_observed_values",
            MappingProxyType(normalized_observed),
        )

    @property
    def cluster_count(self) -> int:
        return len(self.cluster_predicted_values)

    def to_dict(self) -> dict[str, object]:
        return {
            "cluster_count": self.cluster_count,
            "cluster_observed_values": dict(self.cluster_observed_values),
            "cluster_predicted_values": dict(self.cluster_predicted_values),
            "configuration_id": self.configuration_id,
            "observed_value": self.observed_value,
            "predicted_value": self.predicted_value,
            "replicate_count": self.replicate_count,
        }


@dataclass(frozen=True)
class BenchmarkReport:
    """Complete held-out evidence for prediction and induced decisions."""

    benchmark_id: str
    model_id: str
    metric: str
    objective: str
    predictions: Tuple[PredictionRecord, ...]
    residuals: Tuple[ResidualMetrics, ...]
    interval_coverage: IntervalCoverage
    ranking: RankingCorrelation
    decision_regret: DecisionRegret
    held_out_dimensions: Tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    kendall_tau_b: KendallTauB | None = None
    aggregation: BenchmarkAggregation = field(default_factory=BenchmarkAggregation)
    configuration_aggregates: Tuple[ConfigurationAggregate, ...] = ()

    def __post_init__(self) -> None:
        for name in ("benchmark_id", "model_id", "metric"):
            object.__setattr__(self, name, _nonblank(getattr(self, name), name))
        if self.objective not in {"minimize", "maximize"}:
            raise ValueError("report objective must be 'minimize' or 'maximize'")
        if not isinstance(self.interval_coverage, IntervalCoverage):
            raise TypeError("report interval_coverage must be IntervalCoverage")
        if not isinstance(self.ranking, RankingCorrelation):
            raise TypeError("report ranking must be RankingCorrelation")
        if not isinstance(self.decision_regret, DecisionRegret):
            raise TypeError("report decision_regret must be DecisionRegret")
        if self.kendall_tau_b is not None and not isinstance(
            self.kendall_tau_b, KendallTauB
        ):
            raise TypeError("report kendall_tau_b must be KendallTauB or None")
        if not isinstance(self.aggregation, BenchmarkAggregation):
            raise TypeError("report aggregation must be BenchmarkAggregation")
        aggregates = tuple(self.configuration_aggregates)
        if any(not isinstance(item, ConfigurationAggregate) for item in aggregates):
            raise TypeError(
                "configuration_aggregates must contain ConfigurationAggregate values"
            )
        aggregate_ids = [item.configuration_id for item in aggregates]
        if len(aggregate_ids) != len(set(aggregate_ids)):
            raise ValueError("configuration aggregate IDs must be unique")
        if aggregates and tuple(aggregate_ids) != tuple(sorted(aggregate_ids)):
            raise ValueError("configuration aggregates must be sorted by ID")
        if aggregates:
            aggregate_id_set = set(aggregate_ids)
            if aggregate_id_set != set(self.ranking.predicted_order):
                raise ValueError(
                    "configuration aggregates and ranking must contain the same IDs"
                )
            if self.kendall_tau_b is not None and (
                self.kendall_tau_b.configuration_count != len(aggregates)
            ):
                raise ValueError(
                    "Kendall configuration_count must match configuration aggregates"
                )
            if {
                self.decision_regret.selected_configuration,
                self.decision_regret.optimal_configuration,
            } - aggregate_id_set:
                raise ValueError(
                    "decision regret references a configuration absent from aggregates"
                )
            for aggregate in aggregates:
                expected_predicted = self.aggregation.reduce(
                    aggregate.cluster_predicted_values.values()
                )
                expected_observed = self.aggregation.reduce(
                    aggregate.cluster_observed_values.values()
                )
                if not math.isclose(
                    aggregate.predicted_value,
                    expected_predicted,
                    rel_tol=1e-12,
                    abs_tol=1e-12,
                ):
                    raise ValueError(
                        "configuration predicted value does not match the "
                        "preregistered cluster reducer"
                    )
                if not math.isclose(
                    aggregate.observed_value,
                    expected_observed,
                    rel_tol=1e-12,
                    abs_tol=1e-12,
                ):
                    raise ValueError(
                        "configuration observed value does not match the "
                        "preregistered cluster reducer"
                    )
        object.__setattr__(self, "predictions", tuple(self.predictions))
        object.__setattr__(self, "residuals", tuple(self.residuals))
        object.__setattr__(self, "held_out_dimensions", tuple(self.held_out_dimensions))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))
        object.__setattr__(self, "configuration_aggregates", aggregates)

    @property
    def mean_absolute_error(self) -> float:
        return fmean(residual.absolute_error for residual in self.residuals)

    def to_dict(self) -> dict[str, object]:
        return {
            "benchmark_id": self.benchmark_id,
            "model_id": self.model_id,
            "metric": self.metric,
            "objective": self.objective,
            "held_out_dimensions": list(self.held_out_dimensions),
            "summary": {
                "case_count": len(self.residuals),
                "mean_absolute_error": self.mean_absolute_error,
                "interval_coverage": self.interval_coverage.to_dict(),
                "ranking": self.ranking.to_dict(),
                "kendall_tau_b": (
                    None
                    if self.kendall_tau_b is None
                    else self.kendall_tau_b.to_dict()
                ),
                "decision_regret": self.decision_regret.to_dict(),
                "aggregation": self.aggregation.to_dict(),
                "configuration_count": len(self.configuration_aggregates),
            },
            "configuration_aggregates": [
                aggregate.to_dict() for aggregate in self.configuration_aggregates
            ],
            "predictions": [prediction.to_dict() for prediction in self.predictions],
            "residuals": [residual.to_dict() for residual in self.residuals],
            "metadata": dict(self.metadata),
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(), sort_keys=True, indent=2, allow_nan=False
        )


def _aggregate_configuration_scores(
    definition: BenchmarkDefinition,
    predictions_by_case_id: Mapping[str, PredictionRecord],
    residuals_by_prediction_id: Mapping[str, ResidualMetrics],
) -> Tuple[ConfigurationAggregate, ...]:
    """Apply the frozen reducer within clusters, then equally across clusters."""
    aggregation = definition.aggregation
    assert aggregation is not None
    grouped: dict[
        str,
        dict[str, list[tuple[float, float]]],
    ] = {}
    for case in definition.cases:
        prediction = predictions_by_case_id[case.case_id]
        residual = residuals_by_prediction_id[prediction.prediction_id]
        assert case.cluster_id is not None
        grouped.setdefault(case.configuration_id, {}).setdefault(
            case.cluster_id, []
        ).append((prediction.predicted_value, residual.observed_value))

    aggregates = []
    for configuration_id in sorted(grouped):
        clusters = grouped[configuration_id]
        cluster_predicted = {}
        cluster_observed = {}
        replicate_count = 0
        for cluster_id in sorted(clusters):
            replicates = clusters[cluster_id]
            replicate_count += len(replicates)
            cluster_predicted[cluster_id] = aggregation.reduce(
                value[0] for value in replicates
            )
            cluster_observed[cluster_id] = aggregation.reduce(
                value[1] for value in replicates
            )
        aggregates.append(
            ConfigurationAggregate(
                configuration_id=configuration_id,
                replicate_count=replicate_count,
                predicted_value=aggregation.reduce(
                    cluster_predicted.values()
                ),
                observed_value=aggregation.reduce(
                    cluster_observed.values()
                ),
                cluster_predicted_values=cluster_predicted,
                cluster_observed_values=cluster_observed,
            )
        )
    return tuple(aggregates)


def run_benchmark(
    definition: BenchmarkDefinition,
    model: WorldModelBackend | CompositeWorldModel,
    observations: Iterable[Observation],
    *,
    model_id: str | None = None,
) -> BenchmarkReport:
    """Run one backend over the benchmark's held-out cases and score everything.

    The model sees only the preregistered evaluation partition; calibration
    observations never appear in the requests. The report bundles residuals,
    interval coverage, ranking correlation, and decision regret.
    """

    observations = tuple(observations)
    aggregation = definition.aggregation
    assert aggregation is not None
    definition.split.validate_observations(observations)
    by_id = {observation.observation_id: observation for observation in observations}
    model_label = _nonblank(
        model_id or getattr(model, "name", "composite-world-model"),
        "model_id",
    )

    predictions = []
    predictions_by_case_id = {}
    for case in definition.cases:
        estimate = model.predict(case.request)
        if estimate.target != definition.metric:
            raise ValueError(
                f"model returned target {estimate.target!r} for metric "
                f"{definition.metric!r}"
            )
        interval = None
        if estimate.lower is not None:
            if estimate.confidence is None:
                raise ValueError(
                    "benchmark intervals require a nominal confidence level"
                )
            interval = PredictionInterval(
                lower_bound=estimate.lower,
                upper_bound=estimate.upper,
                confidence_level=estimate.confidence,
            )
        prediction = PredictionRecord(
            prediction_id=(
                f"{definition.benchmark_id}:{model_label}:{case.case_id}"
            ),
            observation_id=case.observation_id,
            model_id=model_label,
            metric=definition.metric,
            unit=estimate.unit,
            predicted_value=estimate.value,
            configuration_id=case.configuration_id,
            interval=interval,
            metadata={
                "backend": estimate.backend,
                "assumptions": list(estimate.assumptions),
                "provenance": list(estimate.provenance),
                "diagnostics": dict(estimate.diagnostics),
                "scenario_id": case.request.scenario_id,
                "benchmark_case_id": case.case_id,
                "cluster_id": case.cluster_id,
                "cluster_boundary": aggregation.cluster_boundary,
            },
        )
        predictions.append(prediction)
        predictions_by_case_id[case.case_id] = prediction

    residuals = evaluate_predictions(predictions, by_id)
    residuals_by_prediction_id = {
        residual.prediction_id: residual for residual in residuals
    }
    configuration_aggregates = _aggregate_configuration_scores(
        definition,
        predictions_by_case_id,
        residuals_by_prediction_id,
    )
    predicted_by_configuration = {
        aggregate.configuration_id: aggregate.predicted_value
        for aggregate in configuration_aggregates
    }
    observed_by_configuration = {
        aggregate.configuration_id: aggregate.observed_value
        for aggregate in configuration_aggregates
    }
    return BenchmarkReport(
        benchmark_id=definition.benchmark_id,
        model_id=model_label,
        metric=definition.metric,
        objective=definition.objective,
        predictions=tuple(predictions),
        residuals=residuals,
        interval_coverage=summarize_interval_coverage(residuals),
        ranking=configuration_ranking_correlation(
            predicted_by_configuration,
            observed_by_configuration,
            higher_is_better=definition.higher_is_better,
        ),
        decision_regret=decision_regret(
            predicted_by_configuration,
            observed_by_configuration,
            objective=definition.objective,
        ),
        held_out_dimensions=definition.held_out_dimensions,
        kendall_tau_b=configuration_kendall_tau_b(
            predicted_by_configuration,
            observed_by_configuration,
        ),
        aggregation=aggregation,
        configuration_aggregates=configuration_aggregates,
        metadata={
            "calibration_observation_ids": list(definition.split.calibration_ids),
            "evaluation_observation_ids": [
                case.observation_id for case in definition.cases
            ],
            "aggregation_order": [
                "replicates_within_cluster",
                "equal_weight_across_clusters",
                "configuration_ranking_and_regret",
            ],
        },
    )


@dataclass(frozen=True)
class CalibrationMeanBackend:
    """A deliberately simple baseline fitted only on calibration observations."""

    target: str
    unit: str
    value: float
    calibration_observation_ids: Tuple[str, ...]
    name: str = "calibration-mean"

    def __post_init__(self) -> None:
        for field_name in ("target", "unit", "name"):
            object.__setattr__(
                self, field_name, _nonblank(getattr(self, field_name), field_name)
            )
        value = float(self.value)
        if not math.isfinite(value):
            raise ValueError("baseline value must be finite")
        ids = tuple(self.calibration_observation_ids)
        if not ids or len(ids) != len(set(ids)):
            raise ValueError("baseline requires unique calibration observation IDs")
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "calibration_observation_ids", ids)

    @classmethod
    def fit(
        cls,
        observations: Iterable[Observation],
        split: CalibrationEvaluationSplit,
        metric: str,
        *,
        name: str = "calibration-mean",
    ) -> "CalibrationMeanBackend":
        observations = tuple(observations)
        split.validate_observations(observations)
        by_id = {observation.observation_id: observation for observation in observations}
        measurements = []
        for observation_id in split.calibration_ids:
            observation = by_id[observation_id]
            if metric not in observation.measured_values:
                raise ValueError(
                    f"calibration observation {observation_id!r} has no {metric!r}"
                )
            measurements.append(observation.measured_values[metric])
        units = {measurement.unit for measurement in measurements}
        if len(units) != 1:
            raise ValueError("calibration measurements use inconsistent units")
        return cls(
            target=metric,
            unit=units.pop(),
            value=fmean(measurement.value for measurement in measurements),
            calibration_observation_ids=split.calibration_ids,
            name=name,
        )

    @property
    def capability(self) -> BackendCapability:
        return BackendCapability(
            targets=(self.target,),
            fidelity="calibration-mean-baseline",
        )

    def predict(self, request: PredictionRequest) -> PredictionEstimate:
        if request.target != self.target:
            raise ValueError(
                f"baseline for {self.target!r} cannot predict {request.target!r}"
            )
        return PredictionEstimate(
            target=self.target,
            value=self.value,
            unit=self.unit,
            backend=self.name,
            assumptions=("constant mean across the calibration partition",),
            provenance=self.calibration_observation_ids,
            diagnostics={"scenario_id": request.scenario_id},
        )


__all__ = [
    "BenchmarkAggregation",
    "BenchmarkCase",
    "BenchmarkDefinition",
    "BenchmarkReport",
    "CalibrationMeanBackend",
    "ConfigurationAggregate",
    "run_benchmark",
]
