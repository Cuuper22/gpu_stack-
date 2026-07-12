"""Held-out prediction evaluation for measured GPUSTACK observations.

The functions here deliberately operate on stable records and plain mappings.
They do not know how a prediction was produced, so symbolic, learned-residual,
and baseline models can be compared against the exact same observations and
accounting boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import json
import math
from types import MappingProxyType
from typing import Iterable, Mapping, Optional, Sequence, Tuple, Union

from .observations import (
    JSONValue,
    Observation,
    _datetime_from_json,
    _datetime_to_json,
    _finite_float,
    _freeze_mapping,
    _json_dumps,
    _mapping_from,
    _normalise_datetime,
    _optional_text,
    _require_text,
    _thaw_json,
)


@dataclass(frozen=True)
class PredictionInterval:
    """A model-reported prediction interval at a named confidence level."""

    lower_bound: float
    upper_bound: float
    confidence_level: float

    def __post_init__(self) -> None:
        lower_bound = _finite_float(self.lower_bound, "lower_bound")
        upper_bound = _finite_float(self.upper_bound, "upper_bound")
        confidence_level = _finite_float(self.confidence_level, "confidence_level")
        if lower_bound > upper_bound:
            raise ValueError("lower_bound must be <= upper_bound")
        if not 0.0 < confidence_level <= 1.0:
            raise ValueError("confidence_level must be in (0, 1]")
        object.__setattr__(self, "lower_bound", lower_bound)
        object.__setattr__(self, "upper_bound", upper_bound)
        object.__setattr__(self, "confidence_level", confidence_level)

    def contains(self, value: float) -> bool:
        value = _finite_float(value, "value")
        return self.lower_bound <= value <= self.upper_bound

    def to_dict(self) -> dict[str, float]:
        return {
            "confidence_level": self.confidence_level,
            "lower_bound": self.lower_bound,
            "upper_bound": self.upper_bound,
        }

    def to_json(self, *, indent: Optional[int] = None) -> str:
        return _json_dumps(self.to_dict(), indent)

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "PredictionInterval":
        data = _mapping_from(data, "prediction interval")
        return cls(
            lower_bound=data.get("lower_bound"),
            upper_bound=data.get("upper_bound"),
            confidence_level=data.get("confidence_level"),
        )

    @classmethod
    def from_json(cls, payload: str) -> "PredictionInterval":
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValueError("prediction interval payload is not valid JSON") from exc
        return cls.from_dict(_mapping_from(data, "prediction interval"))


@dataclass(frozen=True)
class PredictionRecord:
    """One model prediction linked to one observed metric."""

    prediction_id: str
    observation_id: str
    model_id: str
    metric: str
    predicted_value: float
    unit: str
    interval: Optional[PredictionInterval] = None
    configuration_id: Optional[str] = None
    created_at: Optional[datetime] = None
    metadata: Mapping[str, JSONValue] = field(default_factory=dict)
    schema_version: str = "1.0"

    def __post_init__(self) -> None:
        if self.interval is not None and not isinstance(
            self.interval, PredictionInterval
        ):
            raise TypeError("interval must be a PredictionInterval or None")
        predicted_value = _finite_float(self.predicted_value, "predicted_value")
        if self.interval is not None and not self.interval.contains(predicted_value):
            raise ValueError("predicted_value must lie within its prediction interval")
        created_at = self.created_at
        if created_at is not None:
            created_at = _normalise_datetime(created_at, "created_at")
        object.__setattr__(
            self, "prediction_id", _require_text(self.prediction_id, "prediction_id")
        )
        object.__setattr__(
            self, "observation_id", _require_text(self.observation_id, "observation_id")
        )
        object.__setattr__(self, "model_id", _require_text(self.model_id, "model_id"))
        object.__setattr__(self, "metric", _require_text(self.metric, "metric"))
        object.__setattr__(
            self, "predicted_value", predicted_value
        )
        object.__setattr__(self, "unit", _require_text(self.unit, "unit"))
        object.__setattr__(
            self,
            "configuration_id",
            _optional_text(self.configuration_id, "configuration_id"),
        )
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata, "metadata"))
        object.__setattr__(
            self, "schema_version", _require_text(self.schema_version, "schema_version")
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "configuration_id": self.configuration_id,
            "created_at": (
                _datetime_to_json(self.created_at)
                if self.created_at is not None
                else None
            ),
            "interval": self.interval.to_dict() if self.interval is not None else None,
            "metadata": _thaw_json(self.metadata),
            "metric": self.metric,
            "model_id": self.model_id,
            "observation_id": self.observation_id,
            "predicted_value": self.predicted_value,
            "prediction_id": self.prediction_id,
            "schema_version": self.schema_version,
            "unit": self.unit,
        }

    def to_json(self, *, indent: Optional[int] = None) -> str:
        return _json_dumps(self.to_dict(), indent)

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "PredictionRecord":
        data = _mapping_from(data, "prediction")
        interval = data.get("interval")
        created_at = data.get("created_at")
        return cls(
            prediction_id=data.get("prediction_id"),
            observation_id=data.get("observation_id"),
            model_id=data.get("model_id"),
            metric=data.get("metric"),
            predicted_value=data.get("predicted_value"),
            unit=data.get("unit"),
            interval=(
                PredictionInterval.from_dict(_mapping_from(interval, "interval"))
                if interval is not None
                else None
            ),
            configuration_id=data.get("configuration_id"),
            created_at=(
                _datetime_from_json(created_at, "created_at")
                if created_at is not None
                else None
            ),
            metadata=_mapping_from(data.get("metadata", {}), "metadata"),
            schema_version=data.get("schema_version", "1.0"),
        )

    @classmethod
    def from_json(cls, payload: str) -> "PredictionRecord":
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValueError("prediction payload is not valid JSON") from exc
        return cls.from_dict(_mapping_from(data, "prediction"))


Prediction = PredictionRecord


def _json_mapping(payload: str, label: str) -> Mapping[str, object]:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} payload is not valid JSON") from exc
    return _mapping_from(data, label)


@dataclass(frozen=True)
class ResidualMetrics:
    """Error metrics for one prediction, with ``prediction - observation`` sign."""

    prediction_id: str
    observation_id: str
    model_id: str
    metric: str
    unit: str
    predicted_value: float
    observed_value: float
    configuration_id: Optional[str] = None
    interval_covered: Optional[bool] = None
    interval_confidence_level: Optional[float] = None
    residual: float = field(init=False)
    absolute_error: float = field(init=False)
    relative_error: Optional[float] = field(init=False)
    signed_relative_error: Optional[float] = field(init=False)

    def __post_init__(self) -> None:
        predicted_value = _finite_float(self.predicted_value, "predicted_value")
        observed_value = _finite_float(self.observed_value, "observed_value")
        residual = predicted_value - observed_value
        relative_error = (
            abs(residual) / abs(observed_value) if observed_value != 0.0 else None
        )
        signed_relative_error = (
            residual / abs(observed_value) if observed_value != 0.0 else None
        )
        confidence = self.interval_confidence_level
        if self.interval_covered is None:
            if confidence is not None:
                raise ValueError(
                    "interval_confidence_level requires interval_covered"
                )
        else:
            if not isinstance(self.interval_covered, bool):
                raise TypeError("interval_covered must be bool or None")
            if confidence is None:
                raise ValueError(
                    "interval_covered requires interval_confidence_level"
                )
            confidence = _finite_float(confidence, "interval_confidence_level")
            if not 0.0 < confidence <= 1.0:
                raise ValueError("interval_confidence_level must be in (0, 1]")

        object.__setattr__(
            self, "prediction_id", _require_text(self.prediction_id, "prediction_id")
        )
        object.__setattr__(
            self, "observation_id", _require_text(self.observation_id, "observation_id")
        )
        object.__setattr__(self, "model_id", _require_text(self.model_id, "model_id"))
        object.__setattr__(self, "metric", _require_text(self.metric, "metric"))
        object.__setattr__(self, "unit", _require_text(self.unit, "unit"))
        object.__setattr__(
            self,
            "configuration_id",
            _optional_text(self.configuration_id, "configuration_id"),
        )
        object.__setattr__(self, "predicted_value", predicted_value)
        object.__setattr__(self, "observed_value", observed_value)
        object.__setattr__(self, "interval_confidence_level", confidence)
        object.__setattr__(self, "residual", residual)
        object.__setattr__(self, "absolute_error", abs(residual))
        object.__setattr__(self, "relative_error", relative_error)
        object.__setattr__(self, "signed_relative_error", signed_relative_error)

    def to_dict(self) -> dict[str, object]:
        return {
            "absolute_error": self.absolute_error,
            "configuration_id": self.configuration_id,
            "interval_confidence_level": self.interval_confidence_level,
            "interval_covered": self.interval_covered,
            "metric": self.metric,
            "model_id": self.model_id,
            "observation_id": self.observation_id,
            "observed_value": self.observed_value,
            "predicted_value": self.predicted_value,
            "prediction_id": self.prediction_id,
            "relative_error": self.relative_error,
            "residual": self.residual,
            "signed_relative_error": self.signed_relative_error,
            "unit": self.unit,
        }

    def to_json(self, *, indent: Optional[int] = None) -> str:
        return _json_dumps(self.to_dict(), indent)

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "ResidualMetrics":
        data = _mapping_from(data, "residual metrics")
        result = cls(
            prediction_id=data.get("prediction_id"),
            observation_id=data.get("observation_id"),
            model_id=data.get("model_id"),
            metric=data.get("metric"),
            unit=data.get("unit"),
            predicted_value=data.get("predicted_value"),
            observed_value=data.get("observed_value"),
            configuration_id=data.get("configuration_id"),
            interval_covered=data.get("interval_covered"),
            interval_confidence_level=data.get("interval_confidence_level"),
        )
        for name in (
            "residual",
            "absolute_error",
            "relative_error",
            "signed_relative_error",
        ):
            if name not in data:
                continue
            claimed = data[name]
            computed = getattr(result, name)
            if claimed is None and computed is None:
                continue
            if claimed is None or computed is None:
                raise ValueError(f"serialized {name} is inconsistent with values")
            claimed_float = _finite_float(claimed, name)
            if not math.isclose(claimed_float, computed, rel_tol=1e-12, abs_tol=1e-12):
                raise ValueError(f"serialized {name} is inconsistent with values")
        return result

    @classmethod
    def from_json(cls, payload: str) -> "ResidualMetrics":
        return cls.from_dict(_json_mapping(payload, "residual metrics"))


def evaluate_prediction(
    prediction: PredictionRecord,
    observation: Observation,
) -> ResidualMetrics:
    """Evaluate one prediction against its exact linked observation."""
    if not isinstance(prediction, PredictionRecord):
        raise TypeError("prediction must be a PredictionRecord")
    if not isinstance(observation, Observation):
        raise TypeError("observation must be an Observation")
    if prediction.observation_id != observation.observation_id:
        raise ValueError(
            f"prediction references {prediction.observation_id!r}, not "
            f"observation {observation.observation_id!r}"
        )
    if prediction.metric not in observation.measured_values:
        raise ValueError(
            f"observation {observation.observation_id!r} has no measured metric "
            f"{prediction.metric!r}"
        )
    measured = observation.measured_values[prediction.metric]
    if prediction.unit != measured.unit:
        raise ValueError(
            f"unit mismatch for {prediction.metric!r}: prediction uses "
            f"{prediction.unit!r}, observation uses {measured.unit!r}"
        )
    covered = (
        prediction.interval.contains(measured.value)
        if prediction.interval is not None
        else None
    )
    return ResidualMetrics(
        prediction_id=prediction.prediction_id,
        observation_id=observation.observation_id,
        model_id=prediction.model_id,
        metric=prediction.metric,
        unit=prediction.unit,
        predicted_value=prediction.predicted_value,
        observed_value=measured.value,
        configuration_id=prediction.configuration_id,
        interval_covered=covered,
        interval_confidence_level=(
            prediction.interval.confidence_level
            if prediction.interval is not None
            else None
        ),
    )


def evaluate_predictions(
    predictions: Iterable[PredictionRecord],
    observations: Union[Iterable[Observation], Mapping[str, Observation]],
) -> Tuple[ResidualMetrics, ...]:
    """Evaluate records deterministically after rejecting duplicate IDs."""
    observation_values = (
        observations.values() if isinstance(observations, Mapping) else observations
    )
    by_observation_id = {}
    for observation in observation_values:
        if not isinstance(observation, Observation):
            raise TypeError("observations must contain only Observation objects")
        if observation.observation_id in by_observation_id:
            raise ValueError(
                f"duplicate observation ID {observation.observation_id!r}"
            )
        by_observation_id[observation.observation_id] = observation

    by_prediction_id = {}
    for prediction in predictions:
        if not isinstance(prediction, PredictionRecord):
            raise TypeError("predictions must contain only PredictionRecord objects")
        if prediction.prediction_id in by_prediction_id:
            raise ValueError(f"duplicate prediction ID {prediction.prediction_id!r}")
        by_prediction_id[prediction.prediction_id] = prediction

    residuals = []
    for prediction_id in sorted(by_prediction_id):
        prediction = by_prediction_id[prediction_id]
        observation = by_observation_id.get(prediction.observation_id)
        if observation is None:
            raise ValueError(
                f"prediction {prediction_id!r} references unknown observation "
                f"{prediction.observation_id!r}"
            )
        residuals.append(evaluate_prediction(prediction, observation))
    return tuple(residuals)


@dataclass(frozen=True)
class IntervalCoverage:
    """Aggregate empirical coverage of model-reported intervals."""

    residual_count: int
    interval_count: int
    covered_count: int
    coverage_rate: Optional[float]
    mean_nominal_confidence: Optional[float]
    calibration_error: Optional[float]

    def __post_init__(self) -> None:
        for name in ("residual_count", "interval_count", "covered_count"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if self.interval_count > self.residual_count:
            raise ValueError("interval_count cannot exceed residual_count")
        if self.covered_count > self.interval_count:
            raise ValueError("covered_count cannot exceed interval_count")

        if self.interval_count == 0:
            if any(
                value is not None
                for value in (
                    self.coverage_rate,
                    self.mean_nominal_confidence,
                    self.calibration_error,
                )
            ):
                raise ValueError("coverage statistics must be None without intervals")
            return

        expected_rate = self.covered_count / self.interval_count
        coverage_rate = _finite_float(self.coverage_rate, "coverage_rate")
        confidence = _finite_float(
            self.mean_nominal_confidence, "mean_nominal_confidence"
        )
        calibration_error = _finite_float(self.calibration_error, "calibration_error")
        if not math.isclose(coverage_rate, expected_rate, abs_tol=1e-12):
            raise ValueError("coverage_rate is inconsistent with interval counts")
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("mean_nominal_confidence must be in [0, 1]")
        if not math.isclose(
            calibration_error, coverage_rate - confidence, abs_tol=1e-12
        ):
            raise ValueError("calibration_error must equal coverage - confidence")
        object.__setattr__(self, "coverage_rate", coverage_rate)
        object.__setattr__(self, "mean_nominal_confidence", confidence)
        object.__setattr__(self, "calibration_error", calibration_error)

    def to_dict(self) -> dict[str, object]:
        return {
            "calibration_error": self.calibration_error,
            "coverage_rate": self.coverage_rate,
            "covered_count": self.covered_count,
            "interval_count": self.interval_count,
            "mean_nominal_confidence": self.mean_nominal_confidence,
            "residual_count": self.residual_count,
        }

    def to_json(self, *, indent: Optional[int] = None) -> str:
        return _json_dumps(self.to_dict(), indent)

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "IntervalCoverage":
        data = _mapping_from(data, "interval coverage")
        return cls(
            residual_count=data.get("residual_count"),
            interval_count=data.get("interval_count"),
            covered_count=data.get("covered_count"),
            coverage_rate=data.get("coverage_rate"),
            mean_nominal_confidence=data.get("mean_nominal_confidence"),
            calibration_error=data.get("calibration_error"),
        )

    @classmethod
    def from_json(cls, payload: str) -> "IntervalCoverage":
        return cls.from_dict(_json_mapping(payload, "interval coverage"))


@dataclass(frozen=True)
class IntervalCoverageLevel:
    """Coverage for one exact nominal level inside one evaluation panel."""

    confidence_level: float
    interval_count: int
    covered_count: int
    coverage_rate: float
    calibration_error: float

    def __post_init__(self) -> None:
        confidence = _finite_float(self.confidence_level, "confidence_level")
        if not 0.0 < confidence <= 1.0:
            raise ValueError("confidence_level must be in (0, 1]")
        for name in ("interval_count", "covered_count"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if self.interval_count == 0:
            raise ValueError("an interval coverage level requires at least one interval")
        if self.covered_count > self.interval_count:
            raise ValueError("covered_count cannot exceed interval_count")
        coverage_rate = _finite_float(self.coverage_rate, "coverage_rate")
        calibration_error = _finite_float(
            self.calibration_error, "calibration_error"
        )
        expected_rate = self.covered_count / self.interval_count
        if not math.isclose(coverage_rate, expected_rate, abs_tol=1e-12):
            raise ValueError("coverage_rate is inconsistent with interval counts")
        if not math.isclose(
            calibration_error,
            coverage_rate - confidence,
            abs_tol=1e-12,
        ):
            raise ValueError(
                "calibration_error must equal coverage - confidence_level"
            )
        object.__setattr__(self, "confidence_level", confidence)
        object.__setattr__(self, "coverage_rate", coverage_rate)
        object.__setattr__(self, "calibration_error", calibration_error)

    def to_dict(self) -> dict[str, object]:
        return {
            "calibration_error": self.calibration_error,
            "confidence_level": self.confidence_level,
            "coverage_rate": self.coverage_rate,
            "covered_count": self.covered_count,
            "interval_count": self.interval_count,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "IntervalCoverageLevel":
        data = _mapping_from(data, "interval coverage level")
        return cls(
            confidence_level=data.get("confidence_level"),
            interval_count=data.get("interval_count"),
            covered_count=data.get("covered_count"),
            coverage_rate=data.get("coverage_rate"),
            calibration_error=data.get("calibration_error"),
        )


@dataclass(frozen=True)
class IntervalCoveragePanel:
    """Confidence-stratified coverage for one independent evaluation panel."""

    panel_id: str
    residual_count: int
    interval_count: int
    levels: Tuple[IntervalCoverageLevel, ...]

    def __post_init__(self) -> None:
        panel_id = _require_text(self.panel_id, "panel_id")
        for name in ("residual_count", "interval_count"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if self.interval_count > self.residual_count:
            raise ValueError("interval_count cannot exceed residual_count")
        levels = tuple(self.levels)
        if any(not isinstance(level, IntervalCoverageLevel) for level in levels):
            raise TypeError("levels must contain only IntervalCoverageLevel values")
        confidences = [level.confidence_level for level in levels]
        if len(confidences) != len(set(confidences)):
            raise ValueError("panel confidence levels must be unique")
        if tuple(confidences) != tuple(sorted(confidences)):
            raise ValueError("panel confidence levels must be sorted")
        if sum(level.interval_count for level in levels) != self.interval_count:
            raise ValueError("panel level counts must sum to interval_count")
        object.__setattr__(self, "panel_id", panel_id)
        object.__setattr__(self, "levels", levels)

    @property
    def without_interval_count(self) -> int:
        return self.residual_count - self.interval_count

    def to_dict(self) -> dict[str, object]:
        return {
            "interval_count": self.interval_count,
            "levels": [level.to_dict() for level in self.levels],
            "panel_id": self.panel_id,
            "residual_count": self.residual_count,
            "without_interval_count": self.without_interval_count,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "IntervalCoveragePanel":
        data = _mapping_from(data, "interval coverage panel")
        panel = cls(
            panel_id=data.get("panel_id"),
            residual_count=data.get("residual_count"),
            interval_count=data.get("interval_count"),
            levels=tuple(
                IntervalCoverageLevel.from_dict(
                    _mapping_from(item, "interval coverage level")
                )
                for item in data.get("levels", ())
            ),
        )
        claimed_without = data.get("without_interval_count")
        if claimed_without is not None and claimed_without != panel.without_interval_count:
            raise ValueError("without_interval_count is inconsistent with counts")
        return panel


@dataclass(frozen=True)
class StratifiedIntervalCoverage:
    """Coverage kept separate by panel and exact nominal confidence level."""

    residual_count: int
    interval_count: int
    panels: Tuple[IntervalCoveragePanel, ...]

    def __post_init__(self) -> None:
        for name in ("residual_count", "interval_count"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if self.interval_count > self.residual_count:
            raise ValueError("interval_count cannot exceed residual_count")
        panels = tuple(self.panels)
        if not panels:
            raise ValueError("stratified coverage requires at least one panel")
        if any(not isinstance(panel, IntervalCoveragePanel) for panel in panels):
            raise TypeError("panels must contain only IntervalCoveragePanel values")
        panel_ids = [panel.panel_id for panel in panels]
        if len(panel_ids) != len(set(panel_ids)):
            raise ValueError("stratified coverage panel IDs must be unique")
        if tuple(panel_ids) != tuple(sorted(panel_ids)):
            raise ValueError("stratified coverage panels must be sorted by ID")
        if sum(panel.residual_count for panel in panels) != self.residual_count:
            raise ValueError("panel residual counts must sum to residual_count")
        if sum(panel.interval_count for panel in panels) != self.interval_count:
            raise ValueError("panel interval counts must sum to interval_count")
        object.__setattr__(self, "panels", panels)

    @property
    def without_interval_count(self) -> int:
        return self.residual_count - self.interval_count

    def panel(self, panel_id: str) -> IntervalCoveragePanel:
        panel_id = _require_text(panel_id, "panel_id")
        for panel in self.panels:
            if panel.panel_id == panel_id:
                return panel
        raise KeyError(f"unknown interval-coverage panel {panel_id!r}")

    def to_dict(self) -> dict[str, object]:
        return {
            "interval_count": self.interval_count,
            "panels": [panel.to_dict() for panel in self.panels],
            "residual_count": self.residual_count,
            "without_interval_count": self.without_interval_count,
        }

    def to_json(self, *, indent: Optional[int] = None) -> str:
        return _json_dumps(self.to_dict(), indent)

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "StratifiedIntervalCoverage":
        data = _mapping_from(data, "stratified interval coverage")
        result = cls(
            residual_count=data.get("residual_count"),
            interval_count=data.get("interval_count"),
            panels=tuple(
                IntervalCoveragePanel.from_dict(
                    _mapping_from(item, "interval coverage panel")
                )
                for item in data.get("panels", ())
            ),
        )
        claimed_without = data.get("without_interval_count")
        if claimed_without is not None and claimed_without != result.without_interval_count:
            raise ValueError("without_interval_count is inconsistent with counts")
        return result

    @classmethod
    def from_json(cls, payload: str) -> "StratifiedIntervalCoverage":
        return cls.from_dict(_json_mapping(payload, "stratified interval coverage"))


def summarize_interval_coverage_stratified(
    residuals: Iterable[ResidualMetrics],
    *,
    panel_by_prediction_id: Optional[Mapping[str, str]] = None,
) -> StratifiedIntervalCoverage:
    """Summarize without pooling confidence levels or evaluation panels.

    When a panel mapping is supplied it must cover every residual exactly. This
    prevents omissions or an implicit catch-all panel from changing coverage.
    """
    residuals = tuple(residuals)
    for residual in residuals:
        if not isinstance(residual, ResidualMetrics):
            raise TypeError("residuals must contain only ResidualMetrics")
    prediction_ids = [residual.prediction_id for residual in residuals]
    if len(prediction_ids) != len(set(prediction_ids)):
        raise ValueError("residual prediction IDs must be unique for panel grouping")

    if panel_by_prediction_id is None:
        assignments = {prediction_id: "all" for prediction_id in prediction_ids}
    else:
        if not isinstance(panel_by_prediction_id, Mapping):
            raise TypeError("panel_by_prediction_id must be a mapping")
        supplied_ids = set(panel_by_prediction_id)
        expected_ids = set(prediction_ids)
        if supplied_ids != expected_ids:
            raise ValueError(
                "panel mapping must contain exactly the residual prediction IDs; "
                f"missing={sorted(expected_ids - supplied_ids)}, "
                f"unknown={sorted(supplied_ids - expected_ids)}"
            )
        assignments = {
            prediction_id: _require_text(
                panel_by_prediction_id[prediction_id],
                f"panel for prediction {prediction_id!r}",
            )
            for prediction_id in prediction_ids
        }

    grouped: dict[str, list[ResidualMetrics]] = {}
    for residual in residuals:
        grouped.setdefault(assignments[residual.prediction_id], []).append(residual)
    if not grouped:
        grouped["all"] = []

    panels = []
    for panel_id in sorted(grouped):
        panel_residuals = tuple(grouped[panel_id])
        by_confidence: dict[float, list[ResidualMetrics]] = {}
        for residual in panel_residuals:
            if residual.interval_covered is None:
                continue
            confidence = residual.interval_confidence_level
            assert confidence is not None
            by_confidence.setdefault(confidence, []).append(residual)
        levels = []
        for confidence in sorted(by_confidence):
            level_residuals = by_confidence[confidence]
            covered_count = sum(
                residual.interval_covered is True for residual in level_residuals
            )
            coverage_rate = covered_count / len(level_residuals)
            levels.append(
                IntervalCoverageLevel(
                    confidence_level=confidence,
                    interval_count=len(level_residuals),
                    covered_count=covered_count,
                    coverage_rate=coverage_rate,
                    calibration_error=coverage_rate - confidence,
                )
            )
        panels.append(
            IntervalCoveragePanel(
                panel_id=panel_id,
                residual_count=len(panel_residuals),
                interval_count=sum(level.interval_count for level in levels),
                levels=tuple(levels),
            )
        )
    return StratifiedIntervalCoverage(
        residual_count=len(residuals),
        interval_count=sum(panel.interval_count for panel in panels),
        panels=tuple(panels),
    )


def summarize_interval_coverage(
    residuals: Iterable[ResidualMetrics],
) -> IntervalCoverage:
    """Summarize one nominal level, rejecting scientifically invalid pooling."""
    residuals = tuple(residuals)
    for residual in residuals:
        if not isinstance(residual, ResidualMetrics):
            raise TypeError("residuals must contain only ResidualMetrics")
    with_intervals = tuple(
        residual for residual in residuals if residual.interval_covered is not None
    )
    if not with_intervals:
        return IntervalCoverage(
            residual_count=len(residuals),
            interval_count=0,
            covered_count=0,
            coverage_rate=None,
            mean_nominal_confidence=None,
            calibration_error=None,
        )
    confidence_levels = {
        residual.interval_confidence_level for residual in with_intervals
    }
    if len(confidence_levels) != 1:
        raise ValueError(
            "mixed nominal confidence levels cannot be pooled; use "
            "summarize_interval_coverage_stratified"
        )
    covered_count = sum(residual.interval_covered is True for residual in with_intervals)
    coverage_rate = covered_count / len(with_intervals)
    mean_confidence = next(iter(confidence_levels))
    assert mean_confidence is not None
    return IntervalCoverage(
        residual_count=len(residuals),
        interval_count=len(with_intervals),
        covered_count=covered_count,
        coverage_rate=coverage_rate,
        mean_nominal_confidence=mean_confidence,
        calibration_error=coverage_rate - mean_confidence,
    )


interval_coverage = summarize_interval_coverage
stratified_interval_coverage = summarize_interval_coverage_stratified


def _validated_scores(
    values: Mapping[str, float], field_name: str
) -> Mapping[str, float]:
    if not isinstance(values, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    if not values:
        raise ValueError(f"{field_name} must not be empty")
    invalid_keys = [key for key in values if not isinstance(key, str) or not key.strip()]
    if invalid_keys:
        raise ValueError(f"{field_name} configuration IDs must be non-blank strings")
    result = {}
    for configuration_id in sorted(values):
        key = _require_text(configuration_id, f"{field_name} configuration ID")
        if key in result:
            raise ValueError(
                f"{field_name} contains duplicate normalized configuration ID {key!r}"
            )
        result[key] = _finite_float(values[configuration_id], f"{field_name}[{key!r}]")
    return MappingProxyType(result)


def _average_ranks(values: Sequence[float]) -> Tuple[float, ...]:
    ordered_indices = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    start = 0
    while start < len(ordered_indices):
        end = start + 1
        value = values[ordered_indices[start]]
        while end < len(ordered_indices) and values[ordered_indices[end]] == value:
            end += 1
        average_rank = ((start + 1) + end) / 2.0
        for position in range(start, end):
            ranks[ordered_indices[position]] = average_rank
        start = end
    return tuple(ranks)


def _pearson(left: Sequence[float], right: Sequence[float]) -> Optional[float]:
    if len(left) < 2:
        return None
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    numerator = sum(
        (x - left_mean) * (y - right_mean) for x, y in zip(left, right)
    )
    left_ss = sum((x - left_mean) ** 2 for x in left)
    right_ss = sum((y - right_mean) ** 2 for y in right)
    if left_ss == 0.0 or right_ss == 0.0:
        return None
    return numerator / math.sqrt(left_ss * right_ss)


@dataclass(frozen=True)
class RankingCorrelation:
    """Spearman correlation and deterministic orders for configurations."""

    configuration_count: int
    spearman_correlation: Optional[float]
    predicted_order: Tuple[str, ...]
    observed_order: Tuple[str, ...]
    higher_is_better: bool
    top_choice_matches: bool

    def __post_init__(self) -> None:
        if (
            isinstance(self.configuration_count, bool)
            or not isinstance(self.configuration_count, int)
            or self.configuration_count < 1
        ):
            raise ValueError("configuration_count must be a positive integer")
        predicted_order = tuple(self.predicted_order)
        observed_order = tuple(self.observed_order)
        if len(predicted_order) != self.configuration_count or len(
            observed_order
        ) != self.configuration_count:
            raise ValueError("orders must match configuration_count")
        if len(set(predicted_order)) != self.configuration_count or len(
            set(observed_order)
        ) != self.configuration_count:
            raise ValueError("configuration orders must not contain duplicate IDs")
        if any(not isinstance(item, str) or not item.strip() for item in predicted_order):
            raise ValueError("configuration orders require non-blank string IDs")
        if set(predicted_order) != set(observed_order):
            raise ValueError("predicted and observed orders must contain the same IDs")
        if not isinstance(self.higher_is_better, bool):
            raise TypeError("higher_is_better must be bool")
        if not isinstance(self.top_choice_matches, bool):
            raise TypeError("top_choice_matches must be bool")
        if self.top_choice_matches != (predicted_order[0] == observed_order[0]):
            raise ValueError("top_choice_matches is inconsistent with the orders")
        correlation = self.spearman_correlation
        if correlation is not None:
            correlation = _finite_float(correlation, "spearman_correlation")
            if not -1.0 <= correlation <= 1.0:
                raise ValueError("spearman_correlation must be in [-1, 1]")
            object.__setattr__(self, "spearman_correlation", correlation)
        object.__setattr__(self, "predicted_order", predicted_order)
        object.__setattr__(self, "observed_order", observed_order)

    def to_dict(self) -> dict[str, object]:
        return {
            "configuration_count": self.configuration_count,
            "higher_is_better": self.higher_is_better,
            "observed_order": list(self.observed_order),
            "predicted_order": list(self.predicted_order),
            "spearman_correlation": self.spearman_correlation,
            "top_choice_matches": self.top_choice_matches,
        }

    def to_json(self, *, indent: Optional[int] = None) -> str:
        return _json_dumps(self.to_dict(), indent)

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "RankingCorrelation":
        data = _mapping_from(data, "ranking correlation")
        return cls(
            configuration_count=data.get("configuration_count"),
            spearman_correlation=data.get("spearman_correlation"),
            predicted_order=tuple(data.get("predicted_order", ())),
            observed_order=tuple(data.get("observed_order", ())),
            higher_is_better=data.get("higher_is_better"),
            top_choice_matches=data.get("top_choice_matches"),
        )

    @classmethod
    def from_json(cls, payload: str) -> "RankingCorrelation":
        return cls.from_dict(_json_mapping(payload, "ranking correlation"))


def configuration_ranking_correlation(
    predicted: Mapping[str, float],
    observed: Mapping[str, float],
    *,
    higher_is_better: bool = False,
) -> RankingCorrelation:
    """Compute tie-aware Spearman correlation without a statistics dependency."""
    if not isinstance(higher_is_better, bool):
        raise TypeError("higher_is_better must be bool")
    predicted = _validated_scores(predicted, "predicted")
    observed = _validated_scores(observed, "observed")
    predicted_ids = set(predicted)
    observed_ids = set(observed)
    if predicted_ids != observed_ids:
        missing_predicted = sorted(observed_ids - predicted_ids)
        missing_observed = sorted(predicted_ids - observed_ids)
        raise ValueError(
            "predicted and observed configurations differ; "
            f"missing predicted={missing_predicted}, missing observed={missing_observed}"
        )
    configuration_ids = sorted(predicted)
    predicted_values = [predicted[key] for key in configuration_ids]
    observed_values = [observed[key] for key in configuration_ids]
    correlation = _pearson(
        _average_ranks(predicted_values), _average_ranks(observed_values)
    )
    if correlation is not None:
        correlation = max(-1.0, min(1.0, correlation))
    direction = -1.0 if higher_is_better else 1.0
    predicted_order = tuple(
        sorted(configuration_ids, key=lambda key: (direction * predicted[key], key))
    )
    observed_order = tuple(
        sorted(configuration_ids, key=lambda key: (direction * observed[key], key))
    )
    return RankingCorrelation(
        configuration_count=len(configuration_ids),
        spearman_correlation=correlation,
        predicted_order=predicted_order,
        observed_order=observed_order,
        higher_is_better=higher_is_better,
        top_choice_matches=predicted_order[0] == observed_order[0],
    )


ranking_correlation = configuration_ranking_correlation


@dataclass(frozen=True)
class KendallTauB:
    """Tie-aware Kendall tau-b with its complete pair accounting."""

    configuration_count: int
    pair_count: int
    concordant_pairs: int
    discordant_pairs: int
    predicted_only_ties: int
    observed_only_ties: int
    joint_ties: int
    tau_b: Optional[float]

    def __post_init__(self) -> None:
        for name in (
            "configuration_count",
            "pair_count",
            "concordant_pairs",
            "discordant_pairs",
            "predicted_only_ties",
            "observed_only_ties",
            "joint_ties",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if self.configuration_count < 1:
            raise ValueError("configuration_count must be a positive integer")
        expected_pairs = (
            self.configuration_count * (self.configuration_count - 1) // 2
        )
        if self.pair_count != expected_pairs:
            raise ValueError("pair_count is inconsistent with configuration_count")
        classified_pairs = (
            self.concordant_pairs
            + self.discordant_pairs
            + self.predicted_only_ties
            + self.observed_only_ties
            + self.joint_ties
        )
        if classified_pairs != self.pair_count:
            raise ValueError("Kendall pair classes must sum to pair_count")
        comparable = self.concordant_pairs + self.discordant_pairs
        denominator = math.sqrt(
            (comparable + self.predicted_only_ties)
            * (comparable + self.observed_only_ties)
        )
        if denominator == 0.0:
            if self.tau_b is not None:
                raise ValueError("tau_b must be None when all usable pairs are tied")
            return
        tau_b = _finite_float(self.tau_b, "tau_b")
        expected_tau = (
            self.concordant_pairs - self.discordant_pairs
        ) / denominator
        if not math.isclose(tau_b, expected_tau, abs_tol=1e-12):
            raise ValueError("tau_b is inconsistent with pair counts")
        if not -1.0 <= tau_b <= 1.0:
            raise ValueError("tau_b must be in [-1, 1]")
        object.__setattr__(self, "tau_b", tau_b)

    @property
    def comparable_pair_count(self) -> int:
        return self.concordant_pairs + self.discordant_pairs

    def to_dict(self) -> dict[str, object]:
        return {
            "comparable_pair_count": self.comparable_pair_count,
            "concordant_pairs": self.concordant_pairs,
            "configuration_count": self.configuration_count,
            "discordant_pairs": self.discordant_pairs,
            "joint_ties": self.joint_ties,
            "observed_only_ties": self.observed_only_ties,
            "pair_count": self.pair_count,
            "predicted_only_ties": self.predicted_only_ties,
            "tau_b": self.tau_b,
        }

    def to_json(self, *, indent: Optional[int] = None) -> str:
        return _json_dumps(self.to_dict(), indent)

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "KendallTauB":
        data = _mapping_from(data, "Kendall tau-b")
        result = cls(
            configuration_count=data.get("configuration_count"),
            pair_count=data.get("pair_count"),
            concordant_pairs=data.get("concordant_pairs"),
            discordant_pairs=data.get("discordant_pairs"),
            predicted_only_ties=data.get("predicted_only_ties"),
            observed_only_ties=data.get("observed_only_ties"),
            joint_ties=data.get("joint_ties"),
            tau_b=data.get("tau_b"),
        )
        claimed_comparable = data.get("comparable_pair_count")
        if (
            claimed_comparable is not None
            and claimed_comparable != result.comparable_pair_count
        ):
            raise ValueError(
                "comparable_pair_count is inconsistent with Kendall pair counts"
            )
        return result

    @classmethod
    def from_json(cls, payload: str) -> "KendallTauB":
        return cls.from_dict(_json_mapping(payload, "Kendall tau-b"))


def configuration_kendall_tau_b(
    predicted: Mapping[str, float],
    observed: Mapping[str, float],
) -> KendallTauB:
    """Compute Kendall tau-b directly, including ties in either score vector."""
    predicted = _validated_scores(predicted, "predicted")
    observed = _validated_scores(observed, "observed")
    predicted_ids = set(predicted)
    observed_ids = set(observed)
    if predicted_ids != observed_ids:
        missing_predicted = sorted(observed_ids - predicted_ids)
        missing_observed = sorted(predicted_ids - observed_ids)
        raise ValueError(
            "predicted and observed configurations differ; "
            f"missing predicted={missing_predicted}, missing observed={missing_observed}"
        )
    configuration_ids = sorted(predicted)
    concordant = 0
    discordant = 0
    predicted_only_ties = 0
    observed_only_ties = 0
    joint_ties = 0
    for left_index, left_id in enumerate(configuration_ids):
        for right_id in configuration_ids[left_index + 1 :]:
            predicted_delta = predicted[left_id] - predicted[right_id]
            observed_delta = observed[left_id] - observed[right_id]
            if predicted_delta == 0.0 and observed_delta == 0.0:
                joint_ties += 1
            elif predicted_delta == 0.0:
                predicted_only_ties += 1
            elif observed_delta == 0.0:
                observed_only_ties += 1
            elif predicted_delta * observed_delta > 0.0:
                concordant += 1
            else:
                discordant += 1
    comparable = concordant + discordant
    denominator = math.sqrt(
        (comparable + predicted_only_ties)
        * (comparable + observed_only_ties)
    )
    tau_b = None if denominator == 0.0 else (concordant - discordant) / denominator
    pair_count = len(configuration_ids) * (len(configuration_ids) - 1) // 2
    return KendallTauB(
        configuration_count=len(configuration_ids),
        pair_count=pair_count,
        concordant_pairs=concordant,
        discordant_pairs=discordant,
        predicted_only_ties=predicted_only_ties,
        observed_only_ties=observed_only_ties,
        joint_ties=joint_ties,
        tau_b=tau_b,
    )


kendall_tau_b = configuration_kendall_tau_b


@dataclass(frozen=True)
class DecisionRegret:
    """Observed cost of acting on the model's preferred configuration."""

    objective: str
    selected_configuration: str
    optimal_configuration: str
    selected_predicted_value: float
    selected_observed_value: float
    optimal_observed_value: float
    regret: float
    relative_regret: Optional[float]
    is_optimal: bool

    def __post_init__(self) -> None:
        if self.objective not in {"minimize", "maximize"}:
            raise ValueError("objective must be 'minimize' or 'maximize'")
        object.__setattr__(
            self,
            "selected_configuration",
            _require_text(self.selected_configuration, "selected_configuration"),
        )
        object.__setattr__(
            self,
            "optimal_configuration",
            _require_text(self.optimal_configuration, "optimal_configuration"),
        )
        for name in (
            "selected_predicted_value",
            "selected_observed_value",
            "optimal_observed_value",
            "regret",
        ):
            object.__setattr__(self, name, _finite_float(getattr(self, name), name))
        if self.regret < 0.0:
            raise ValueError("regret must be non-negative")
        expected_regret = (
            self.selected_observed_value - self.optimal_observed_value
            if self.objective == "minimize"
            else self.optimal_observed_value - self.selected_observed_value
        )
        if expected_regret < -1e-12:
            raise ValueError("optimal_observed_value is not optimal for the objective")
        expected_regret = max(0.0, expected_regret)
        if not math.isclose(self.regret, expected_regret, abs_tol=1e-12):
            raise ValueError("regret is inconsistent with the observed values")
        expected_relative = (
            self.regret / abs(self.optimal_observed_value)
            if self.optimal_observed_value != 0.0
            else None
        )
        if self.relative_regret is not None:
            relative_regret = _finite_float(self.relative_regret, "relative_regret")
            if relative_regret < 0.0:
                raise ValueError("relative_regret must be non-negative")
            if expected_relative is None or not math.isclose(
                relative_regret, expected_relative, abs_tol=1e-12
            ):
                raise ValueError("relative_regret is inconsistent with regret")
            object.__setattr__(self, "relative_regret", relative_regret)
        elif expected_relative is not None:
            raise ValueError("relative_regret is required when the optimum is nonzero")
        if not isinstance(self.is_optimal, bool):
            raise TypeError("is_optimal must be bool")
        if self.is_optimal != (self.regret == 0.0):
            raise ValueError("is_optimal is inconsistent with regret")

    def to_dict(self) -> dict[str, object]:
        return {
            "is_optimal": self.is_optimal,
            "objective": self.objective,
            "optimal_configuration": self.optimal_configuration,
            "optimal_observed_value": self.optimal_observed_value,
            "regret": self.regret,
            "relative_regret": self.relative_regret,
            "selected_configuration": self.selected_configuration,
            "selected_observed_value": self.selected_observed_value,
            "selected_predicted_value": self.selected_predicted_value,
        }

    def to_json(self, *, indent: Optional[int] = None) -> str:
        return _json_dumps(self.to_dict(), indent)

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "DecisionRegret":
        data = _mapping_from(data, "decision regret")
        return cls(
            objective=data.get("objective"),
            selected_configuration=data.get("selected_configuration"),
            optimal_configuration=data.get("optimal_configuration"),
            selected_predicted_value=data.get("selected_predicted_value"),
            selected_observed_value=data.get("selected_observed_value"),
            optimal_observed_value=data.get("optimal_observed_value"),
            regret=data.get("regret"),
            relative_regret=data.get("relative_regret"),
            is_optimal=data.get("is_optimal"),
        )

    @classmethod
    def from_json(cls, payload: str) -> "DecisionRegret":
        return cls.from_dict(_json_mapping(payload, "decision regret"))


def decision_regret(
    predicted: Mapping[str, float],
    observed: Mapping[str, float],
    *,
    objective: str = "minimize",
) -> DecisionRegret:
    """Measure the held-out consequence of the decision induced by a model."""
    if objective not in {"minimize", "maximize"}:
        raise ValueError("objective must be 'minimize' or 'maximize'")
    predicted = _validated_scores(predicted, "predicted")
    observed = _validated_scores(observed, "observed")
    if set(predicted) != set(observed):
        raise ValueError("predicted and observed must contain identical configurations")
    sign = 1.0 if objective == "minimize" else -1.0
    selected = min(predicted, key=lambda key: (sign * predicted[key], key))
    optimal = min(observed, key=lambda key: (sign * observed[key], key))
    if objective == "minimize":
        regret = observed[selected] - observed[optimal]
    else:
        regret = observed[optimal] - observed[selected]
    regret = max(0.0, regret)
    denominator = abs(observed[optimal])
    relative_regret = regret / denominator if denominator != 0.0 else None
    return DecisionRegret(
        objective=objective,
        selected_configuration=selected,
        optimal_configuration=optimal,
        selected_predicted_value=predicted[selected],
        selected_observed_value=observed[selected],
        optimal_observed_value=observed[optimal],
        regret=regret,
        relative_regret=relative_regret,
        is_optimal=regret == 0.0,
    )


compute_decision_regret = decision_regret


@dataclass(frozen=True)
class ResidualContribution:
    """One named, signed contribution to ``prediction - observation``."""

    component: str
    contribution: float
    description: Optional[str] = None
    metadata: Mapping[str, JSONValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "component", _require_text(self.component, "component"))
        object.__setattr__(
            self, "contribution", _finite_float(self.contribution, "contribution")
        )
        object.__setattr__(
            self, "description", _optional_text(self.description, "description")
        )
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata, "metadata"))

    def to_dict(self) -> dict[str, object]:
        return {
            "component": self.component,
            "contribution": self.contribution,
            "description": self.description,
            "metadata": _thaw_json(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "ResidualContribution":
        data = _mapping_from(data, "residual contribution")
        return cls(
            component=data.get("component"),
            contribution=data.get("contribution"),
            description=data.get("description"),
            metadata=_mapping_from(data.get("metadata", {}), "metadata"),
        )


@dataclass(frozen=True)
class ResidualAttribution:
    """Named residual contributions plus an explicit unattributed remainder."""

    residual: float
    contributions: Tuple[ResidualContribution, ...]
    prediction_id: Optional[str] = None
    observation_id: Optional[str] = None
    metric: Optional[str] = None
    tolerance: float = 1e-9
    metadata: Mapping[str, JSONValue] = field(default_factory=dict)
    attributed_total: float = field(init=False)
    unattributed_residual: float = field(init=False)
    is_complete: bool = field(init=False)

    def __post_init__(self) -> None:
        residual = _finite_float(self.residual, "residual")
        tolerance = _finite_float(self.tolerance, "tolerance")
        if tolerance < 0.0:
            raise ValueError("tolerance must be >= 0")
        contributions = tuple(self.contributions)
        if not contributions:
            raise ValueError("contributions must not be empty")
        if any(not isinstance(item, ResidualContribution) for item in contributions):
            raise TypeError("contributions must contain ResidualContribution objects")
        component_names = [item.component for item in contributions]
        duplicate_names = sorted(
            {name for name in component_names if component_names.count(name) > 1}
        )
        if duplicate_names:
            raise ValueError(f"duplicate residual components: {duplicate_names}")
        contributions = tuple(sorted(contributions, key=lambda item: item.component))
        attributed_total = math.fsum(item.contribution for item in contributions)
        unattributed = residual - attributed_total
        object.__setattr__(self, "residual", residual)
        object.__setattr__(self, "tolerance", tolerance)
        object.__setattr__(self, "contributions", contributions)
        object.__setattr__(
            self, "prediction_id", _optional_text(self.prediction_id, "prediction_id")
        )
        object.__setattr__(
            self, "observation_id", _optional_text(self.observation_id, "observation_id")
        )
        object.__setattr__(self, "metric", _optional_text(self.metric, "metric"))
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata, "metadata"))
        object.__setattr__(self, "attributed_total", attributed_total)
        object.__setattr__(self, "unattributed_residual", unattributed)
        object.__setattr__(self, "is_complete", abs(unattributed) <= tolerance)

    def to_dict(self) -> dict[str, object]:
        return {
            "attributed_total": self.attributed_total,
            "contributions": [item.to_dict() for item in self.contributions],
            "is_complete": self.is_complete,
            "metadata": _thaw_json(self.metadata),
            "metric": self.metric,
            "observation_id": self.observation_id,
            "prediction_id": self.prediction_id,
            "residual": self.residual,
            "tolerance": self.tolerance,
            "unattributed_residual": self.unattributed_residual,
        }

    def to_json(self, *, indent: Optional[int] = None) -> str:
        return _json_dumps(self.to_dict(), indent)

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "ResidualAttribution":
        data = _mapping_from(data, "residual attribution")
        raw_contributions = data.get("contributions", ())
        if isinstance(raw_contributions, (str, bytes, bytearray)) or not isinstance(
            raw_contributions, Iterable
        ):
            raise TypeError("contributions must be an iterable")
        result = cls(
            residual=data.get("residual"),
            contributions=tuple(
                ResidualContribution.from_dict(
                    _mapping_from(item, "residual contribution")
                )
                for item in raw_contributions
            ),
            prediction_id=data.get("prediction_id"),
            observation_id=data.get("observation_id"),
            metric=data.get("metric"),
            tolerance=data.get("tolerance", 1e-9),
            metadata=_mapping_from(data.get("metadata", {}), "metadata"),
        )
        for name in ("attributed_total", "unattributed_residual"):
            if name in data and not math.isclose(
                _finite_float(data[name], name),
                getattr(result, name),
                rel_tol=1e-12,
                abs_tol=1e-12,
            ):
                raise ValueError(f"serialized {name} is inconsistent")
        if "is_complete" in data and data["is_complete"] is not result.is_complete:
            raise ValueError("serialized is_complete is inconsistent")
        return result

    @classmethod
    def from_json(cls, payload: str) -> "ResidualAttribution":
        return cls.from_dict(_json_mapping(payload, "residual attribution"))


def attribute_residual(
    residual: Union[ResidualMetrics, float],
    contributions: Union[
        Mapping[str, float], Iterable[ResidualContribution]
    ],
    *,
    tolerance: float = 1e-9,
    metadata: Optional[Mapping[str, JSONValue]] = None,
) -> ResidualAttribution:
    """Build a deterministic residual attribution without inventing causes."""
    if isinstance(contributions, Mapping):
        contribution_records = tuple(
            ResidualContribution(component=name, contribution=value)
            for name, value in contributions.items()
        )
    else:
        contribution_records = tuple(contributions)

    if isinstance(residual, ResidualMetrics):
        residual_value = residual.residual
        prediction_id = residual.prediction_id
        observation_id = residual.observation_id
        metric = residual.metric
    else:
        residual_value = _finite_float(residual, "residual")
        prediction_id = None
        observation_id = None
        metric = None
    return ResidualAttribution(
        residual=residual_value,
        contributions=contribution_records,
        prediction_id=prediction_id,
        observation_id=observation_id,
        metric=metric,
        tolerance=tolerance,
        metadata=metadata if metadata is not None else {},
    )


__all__ = [
    "PredictionInterval",
    "PredictionRecord",
    "Prediction",
    "ResidualMetrics",
    "evaluate_prediction",
    "evaluate_predictions",
    "IntervalCoverage",
    "IntervalCoverageLevel",
    "IntervalCoveragePanel",
    "StratifiedIntervalCoverage",
    "summarize_interval_coverage",
    "summarize_interval_coverage_stratified",
    "interval_coverage",
    "stratified_interval_coverage",
    "RankingCorrelation",
    "configuration_ranking_correlation",
    "ranking_correlation",
    "KendallTauB",
    "configuration_kendall_tau_b",
    "kendall_tau_b",
    "DecisionRegret",
    "decision_regret",
    "compute_decision_regret",
    "ResidualContribution",
    "ResidualAttribution",
    "attribute_residual",
]
