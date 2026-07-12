"""Measured observation artifacts and leakage-safe dataset splits.

The symbolic registry describes an assumed world.  This module describes the
world that was actually measured.  Keeping those concepts separate makes it
possible to calibrate against one set of runs and evaluate against another
without quietly turning fitted scenarios into evidence for themselves.

All public artifacts are immutable, validate at construction time, and expose
deterministic, JSON-friendly serialisation.  Domain-specific context remains
structured metadata rather than a fixed hardware schema because workloads,
topologies, and instrumentation evolve faster than the observation envelope.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import math
from numbers import Real
from types import MappingProxyType
from typing import Iterable, Mapping, Optional, Sequence, Tuple, Union


JSONPrimitive = Union[None, bool, int, float, str]
JSONValue = Union[
    JSONPrimitive,
    Mapping[str, "JSONValue"],
    Sequence["JSONValue"],
]


def _require_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-blank string")
    return value.strip()


def _optional_text(value: object, field_name: str) -> Optional[str]:
    if value is None:
        return None
    return _require_text(value, field_name)


def _finite_float(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{field_name} must be a real number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{field_name} must be finite")
    return result


def _normalise_datetime(value: object, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must include a timezone")
    return value.astimezone(timezone.utc)


def _datetime_to_json(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _datetime_from_json(value: object, field_name: str) -> datetime:
    text = _require_text(value, field_name)
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an ISO-8601 datetime") from exc
    return _normalise_datetime(parsed, field_name)


def _freeze_json(value: object, path: str) -> object:
    """Validate and recursively freeze a JSON-compatible value."""
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} contains a non-finite number")
        return value
    if isinstance(value, Mapping):
        invalid_keys = [key for key in value if not isinstance(key, str) or not key]
        if invalid_keys:
            raise ValueError(f"{path} keys must be non-empty strings")
        frozen = {}
        for key in sorted(value):
            frozen[key] = _freeze_json(value[key], f"{path}.{key}")
        return MappingProxyType(frozen)
    if isinstance(value, (set, frozenset)):
        raise TypeError(f"{path} must not contain unordered sets")
    if isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    ):
        return tuple(
            _freeze_json(item, f"{path}[{index}]")
            for index, item in enumerate(value)
        )
    raise TypeError(
        f"{path} contains {type(value).__name__}, which is not JSON-compatible"
    )


def _freeze_mapping(
    value: object,
    field_name: str,
    *,
    require_nonempty: bool = False,
) -> Mapping[str, JSONValue]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    if require_nonempty and not value:
        raise ValueError(f"{field_name} must not be empty")
    frozen = _freeze_json(value, field_name)
    assert isinstance(frozen, Mapping)
    return frozen  # type: ignore[return-value]


def _thaw_json(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _thaw_json(value[key]) for key in sorted(value)}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


def _json_dumps(data: Mapping[str, object], indent: Optional[int]) -> str:
    kwargs = {"sort_keys": True, "allow_nan": False}
    if indent is None:
        kwargs["separators"] = (",", ":")
    else:
        kwargs["indent"] = indent
    return json.dumps(data, **kwargs)


def _mapping_from(data: object, field_name: str) -> Mapping[str, object]:
    if not isinstance(data, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    return data


@dataclass(frozen=True)
class MeasurementUncertainty:
    """Uncertainty reported by the measurement process.

    At least one representation is required: a standard deviation or a
    bounded interval.  An interval confidence level is optional because some
    instruments publish tolerance bounds without a probabilistic coverage
    claim.  No uncertainty is inferred by GPUSTACK.
    """

    standard_deviation: Optional[float] = None
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    confidence_level: Optional[float] = None
    distribution: Optional[str] = None
    notes: Optional[str] = None

    def __post_init__(self) -> None:
        standard_deviation = self.standard_deviation
        if standard_deviation is not None:
            standard_deviation = _finite_float(
                standard_deviation, "standard_deviation"
            )
            if standard_deviation < 0.0:
                raise ValueError("standard_deviation must be >= 0")

        has_lower = self.lower_bound is not None
        has_upper = self.upper_bound is not None
        if has_lower != has_upper:
            raise ValueError("lower_bound and upper_bound must be supplied together")
        lower_bound = self.lower_bound
        upper_bound = self.upper_bound
        if has_lower:
            lower_bound = _finite_float(lower_bound, "lower_bound")
            upper_bound = _finite_float(upper_bound, "upper_bound")
            assert upper_bound is not None
            if lower_bound > upper_bound:
                raise ValueError("lower_bound must be <= upper_bound")

        if standard_deviation is None and not has_lower:
            raise ValueError(
                "measurement uncertainty requires standard_deviation or bounds"
            )

        confidence_level = self.confidence_level
        if confidence_level is not None:
            confidence_level = _finite_float(confidence_level, "confidence_level")
            if not 0.0 < confidence_level <= 1.0:
                raise ValueError("confidence_level must be in (0, 1]")
            if not has_lower:
                raise ValueError("confidence_level requires lower/upper bounds")

        object.__setattr__(self, "standard_deviation", standard_deviation)
        object.__setattr__(self, "lower_bound", lower_bound)
        object.__setattr__(self, "upper_bound", upper_bound)
        object.__setattr__(self, "confidence_level", confidence_level)
        object.__setattr__(
            self, "distribution", _optional_text(self.distribution, "distribution")
        )
        object.__setattr__(self, "notes", _optional_text(self.notes, "notes"))

    def to_dict(self) -> dict[str, object]:
        return {
            "confidence_level": self.confidence_level,
            "distribution": self.distribution,
            "lower_bound": self.lower_bound,
            "notes": self.notes,
            "standard_deviation": self.standard_deviation,
            "upper_bound": self.upper_bound,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "MeasurementUncertainty":
        data = _mapping_from(data, "measurement uncertainty")
        return cls(
            standard_deviation=data.get("standard_deviation"),
            lower_bound=data.get("lower_bound"),
            upper_bound=data.get("upper_bound"),
            confidence_level=data.get("confidence_level"),
            distribution=data.get("distribution"),
            notes=data.get("notes"),
        )


@dataclass(frozen=True)
class MeasuredValue:
    """One observed metric with units and instrument-reported uncertainty."""

    value: float
    unit: str
    uncertainty: MeasurementUncertainty
    metadata: Mapping[str, JSONValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.uncertainty, MeasurementUncertainty):
            raise TypeError("uncertainty must be a MeasurementUncertainty")
        value = _finite_float(self.value, "value")
        unit = _require_text(self.unit, "unit")
        if (
            self.uncertainty.lower_bound is not None
            and not self.uncertainty.lower_bound <= value <= self.uncertainty.upper_bound
        ):
            raise ValueError("measured value must lie within its uncertainty bounds")
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "unit", unit)
        object.__setattr__(
            self, "metadata", _freeze_mapping(self.metadata, "measurement metadata")
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "metadata": _thaw_json(self.metadata),
            "uncertainty": self.uncertainty.to_dict(),
            "unit": self.unit,
            "value": self.value,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "MeasuredValue":
        data = _mapping_from(data, "measured value")
        uncertainty = _mapping_from(data.get("uncertainty"), "uncertainty")
        return cls(
            value=data.get("value"),
            unit=data.get("unit"),
            uncertainty=MeasurementUncertainty.from_dict(uncertainty),
            metadata=_mapping_from(data.get("metadata", {}), "metadata"),
        )


# A concise synonym for callers that naturally model each value as a
# measurement.  It is an alias, not a subclass, so type checks remain exact.
Measurement = MeasuredValue


@dataclass(frozen=True)
class Provenance:
    """Where an observation came from and how its identity can be audited."""

    source: str
    uri: Optional[str] = None
    citation: Optional[str] = None
    checksum: Optional[str] = None
    license: Optional[str] = None
    retrieved_at: Optional[datetime] = None
    notes: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if isinstance(self.notes, (str, bytes, bytearray)):
            raise TypeError("notes must be an iterable of strings, not a string")
        notes = tuple(_require_text(note, "provenance note") for note in self.notes)
        retrieved_at = self.retrieved_at
        if retrieved_at is not None:
            retrieved_at = _normalise_datetime(retrieved_at, "retrieved_at")
        object.__setattr__(self, "source", _require_text(self.source, "source"))
        object.__setattr__(self, "uri", _optional_text(self.uri, "uri"))
        object.__setattr__(self, "citation", _optional_text(self.citation, "citation"))
        object.__setattr__(self, "checksum", _optional_text(self.checksum, "checksum"))
        object.__setattr__(self, "license", _optional_text(self.license, "license"))
        object.__setattr__(self, "retrieved_at", retrieved_at)
        object.__setattr__(self, "notes", notes)

    def to_dict(self) -> dict[str, object]:
        return {
            "checksum": self.checksum,
            "citation": self.citation,
            "license": self.license,
            "notes": list(self.notes),
            "retrieved_at": (
                _datetime_to_json(self.retrieved_at)
                if self.retrieved_at is not None
                else None
            ),
            "source": self.source,
            "uri": self.uri,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "Provenance":
        data = _mapping_from(data, "provenance")
        retrieved_at = data.get("retrieved_at")
        return cls(
            source=data.get("source"),
            uri=data.get("uri"),
            citation=data.get("citation"),
            checksum=data.get("checksum"),
            license=data.get("license"),
            retrieved_at=(
                _datetime_from_json(retrieved_at, "retrieved_at")
                if retrieved_at is not None
                else None
            ),
            notes=tuple(data.get("notes", ())),
        )


@dataclass(frozen=True)
class Observation:
    """A versioned measurement of one workload/topology configuration."""

    observation_id: str
    measured_values: Mapping[str, MeasuredValue]
    timestamp: datetime
    topology: Mapping[str, JSONValue]
    workload: Mapping[str, JSONValue]
    software: Mapping[str, JSONValue]
    instrumentation: Mapping[str, JSONValue]
    provenance: Provenance
    metadata: Mapping[str, JSONValue] = field(default_factory=dict)
    schema_version: str = "1.0"

    def __post_init__(self) -> None:
        if not isinstance(self.measured_values, Mapping):
            raise TypeError("measured_values must be a mapping")
        if not self.measured_values:
            raise ValueError("measured_values must not be empty")
        invalid_metrics = [
            metric
            for metric in self.measured_values
            if not isinstance(metric, str) or not metric.strip()
        ]
        if invalid_metrics:
            raise ValueError("measured_values keys must be non-blank metric names")
        measured_values = {}
        for metric in sorted(self.measured_values):
            metric_name = _require_text(metric, "metric name")
            if metric_name in measured_values:
                raise ValueError(
                    f"measured_values contains duplicate normalized metric {metric_name!r}"
                )
            measurement = self.measured_values[metric]
            if not isinstance(measurement, MeasuredValue):
                raise TypeError(
                    f"measured_values[{metric_name!r}] must be a MeasuredValue"
                )
            measured_values[metric_name] = measurement
        if not isinstance(self.provenance, Provenance):
            raise TypeError("provenance must be a Provenance")

        object.__setattr__(
            self, "observation_id", _require_text(self.observation_id, "observation_id")
        )
        object.__setattr__(
            self, "measured_values", MappingProxyType(measured_values)
        )
        object.__setattr__(
            self, "timestamp", _normalise_datetime(self.timestamp, "timestamp")
        )
        for field_name in ("topology", "workload", "software", "instrumentation"):
            object.__setattr__(
                self,
                field_name,
                _freeze_mapping(
                    getattr(self, field_name), field_name, require_nonempty=True
                ),
            )
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata, "metadata"))
        object.__setattr__(
            self, "schema_version", _require_text(self.schema_version, "schema_version")
        )

    @property
    def measurements(self) -> Mapping[str, MeasuredValue]:
        """Compatibility/readability alias for :attr:`measured_values`."""
        return self.measured_values

    def to_dict(self) -> dict[str, object]:
        return {
            "instrumentation": _thaw_json(self.instrumentation),
            "measured_values": {
                metric: self.measured_values[metric].to_dict()
                for metric in sorted(self.measured_values)
            },
            "metadata": _thaw_json(self.metadata),
            "observation_id": self.observation_id,
            "provenance": self.provenance.to_dict(),
            "schema_version": self.schema_version,
            "software": _thaw_json(self.software),
            "timestamp": _datetime_to_json(self.timestamp),
            "topology": _thaw_json(self.topology),
            "workload": _thaw_json(self.workload),
        }

    def to_json(self, *, indent: Optional[int] = None) -> str:
        return _json_dumps(self.to_dict(), indent)

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "Observation":
        data = _mapping_from(data, "observation")
        raw_values = _mapping_from(data.get("measured_values"), "measured_values")
        measured_values = {
            metric: MeasuredValue.from_dict(_mapping_from(value, str(metric)))
            for metric, value in raw_values.items()
        }
        return cls(
            observation_id=data.get("observation_id"),
            measured_values=measured_values,
            timestamp=_datetime_from_json(data.get("timestamp"), "timestamp"),
            topology=_mapping_from(data.get("topology"), "topology"),
            workload=_mapping_from(data.get("workload"), "workload"),
            software=_mapping_from(data.get("software"), "software"),
            instrumentation=_mapping_from(
                data.get("instrumentation"), "instrumentation"
            ),
            provenance=Provenance.from_dict(
                _mapping_from(data.get("provenance"), "provenance")
            ),
            metadata=_mapping_from(data.get("metadata", {}), "metadata"),
            schema_version=data.get("schema_version", "1.0"),
        )

    @classmethod
    def from_json(cls, payload: str) -> "Observation":
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValueError("observation payload is not valid JSON") from exc
        return cls.from_dict(_mapping_from(data, "observation"))


def _freeze_observation_ids(
    values: object,
    field_name: str,
) -> Tuple[str, ...]:
    if isinstance(values, (str, bytes, bytearray)) or not isinstance(
        values, Iterable
    ):
        raise TypeError(f"{field_name} must be an iterable of observation IDs")
    if isinstance(values, (set, frozenset)):
        raise TypeError(f"{field_name} must be ordered, not a set")
    ids = tuple(_require_text(value, "observation ID") for value in values)
    if not ids:
        raise ValueError(f"{field_name} must not be empty")
    duplicates = sorted({value for value in ids if ids.count(value) > 1})
    if duplicates:
        raise ValueError(f"{field_name} contains duplicate IDs: {duplicates}")
    return ids


@dataclass(frozen=True)
class CalibrationSplit:
    """Observation IDs that a model may use for fitting or calibration."""

    observation_ids: Tuple[str, ...]
    name: str = "calibration"
    metadata: Mapping[str, JSONValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "observation_ids",
            _freeze_observation_ids(self.observation_ids, "calibration observation_ids"),
        )
        object.__setattr__(self, "name", _require_text(self.name, "name"))
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata, "metadata"))

    def to_dict(self) -> dict[str, object]:
        return {
            "metadata": _thaw_json(self.metadata),
            "name": self.name,
            "observation_ids": list(self.observation_ids),
        }

    def to_json(self, *, indent: Optional[int] = None) -> str:
        return _json_dumps(self.to_dict(), indent)

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "CalibrationSplit":
        data = _mapping_from(data, "calibration split")
        return cls(
            observation_ids=tuple(data.get("observation_ids", ())),
            name=data.get("name", "calibration"),
            metadata=_mapping_from(data.get("metadata", {}), "metadata"),
        )


@dataclass(frozen=True)
class EvaluationSplit:
    """Held-out observation IDs that must never be used for fitting."""

    observation_ids: Tuple[str, ...]
    name: str = "evaluation"
    metadata: Mapping[str, JSONValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "observation_ids",
            _freeze_observation_ids(self.observation_ids, "evaluation observation_ids"),
        )
        object.__setattr__(self, "name", _require_text(self.name, "name"))
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata, "metadata"))

    def to_dict(self) -> dict[str, object]:
        return {
            "metadata": _thaw_json(self.metadata),
            "name": self.name,
            "observation_ids": list(self.observation_ids),
        }

    def to_json(self, *, indent: Optional[int] = None) -> str:
        return _json_dumps(self.to_dict(), indent)

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "EvaluationSplit":
        data = _mapping_from(data, "evaluation split")
        return cls(
            observation_ids=tuple(data.get("observation_ids", ())),
            name=data.get("name", "evaluation"),
            metadata=_mapping_from(data.get("metadata", {}), "metadata"),
        )


@dataclass(frozen=True)
class CalibrationEvaluationSplit:
    """A leakage-safe calibration/evaluation partition.

    The constructor rejects any observation ID that appears on both sides.
    ``validate_observations`` additionally proves that every referenced ID
    exists in a concrete observation collection.
    """

    split_id: str
    calibration: CalibrationSplit
    evaluation: EvaluationSplit
    metadata: Mapping[str, JSONValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.calibration, CalibrationSplit):
            raise TypeError("calibration must be a CalibrationSplit")
        if not isinstance(self.evaluation, EvaluationSplit):
            raise TypeError("evaluation must be an EvaluationSplit")
        overlap = sorted(
            set(self.calibration.observation_ids)
            & set(self.evaluation.observation_ids)
        )
        if overlap:
            raise ValueError(
                "calibration and evaluation splits overlap: " f"{overlap}"
            )
        object.__setattr__(self, "split_id", _require_text(self.split_id, "split_id"))
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata, "metadata"))

    @property
    def calibration_ids(self) -> Tuple[str, ...]:
        return self.calibration.observation_ids

    @property
    def evaluation_ids(self) -> Tuple[str, ...]:
        return self.evaluation.observation_ids

    @classmethod
    def from_ids(
        cls,
        *,
        split_id: str,
        calibration_ids: Sequence[str],
        evaluation_ids: Sequence[str],
        metadata: Optional[Mapping[str, JSONValue]] = None,
    ) -> "CalibrationEvaluationSplit":
        if isinstance(calibration_ids, (set, frozenset)) or isinstance(
            evaluation_ids, (set, frozenset)
        ):
            raise TypeError("split observation IDs must be ordered, not sets")
        return cls(
            split_id=split_id,
            calibration=CalibrationSplit(tuple(calibration_ids)),
            evaluation=EvaluationSplit(tuple(evaluation_ids)),
            metadata=metadata if metadata is not None else {},
        )

    def validate_observations(
        self,
        observations: Iterable[Observation],
        *,
        require_complete_partition: bool = False,
    ) -> None:
        ids = []
        for observation in observations:
            if not isinstance(observation, Observation):
                raise TypeError("observations must contain only Observation objects")
            ids.append(observation.observation_id)
        duplicate_ids = sorted({value for value in ids if ids.count(value) > 1})
        if duplicate_ids:
            raise ValueError(f"observation collection has duplicate IDs: {duplicate_ids}")
        available = set(ids)
        referenced = set(self.calibration_ids) | set(self.evaluation_ids)
        missing = sorted(referenced - available)
        if missing:
            raise ValueError(f"split references unknown observation IDs: {missing}")
        if require_complete_partition:
            unassigned = sorted(available - referenced)
            if unassigned:
                raise ValueError(f"observations are not assigned to the split: {unassigned}")

    def to_dict(self) -> dict[str, object]:
        return {
            "calibration": self.calibration.to_dict(),
            "evaluation": self.evaluation.to_dict(),
            "metadata": _thaw_json(self.metadata),
            "split_id": self.split_id,
        }

    def to_json(self, *, indent: Optional[int] = None) -> str:
        return _json_dumps(self.to_dict(), indent)

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "CalibrationEvaluationSplit":
        data = _mapping_from(data, "calibration/evaluation split")
        return cls(
            split_id=data.get("split_id"),
            calibration=CalibrationSplit.from_dict(
                _mapping_from(data.get("calibration"), "calibration")
            ),
            evaluation=EvaluationSplit.from_dict(
                _mapping_from(data.get("evaluation"), "evaluation")
            ),
            metadata=_mapping_from(data.get("metadata", {}), "metadata"),
        )

    @classmethod
    def from_json(cls, payload: str) -> "CalibrationEvaluationSplit":
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValueError("split payload is not valid JSON") from exc
        return cls.from_dict(_mapping_from(data, "calibration/evaluation split"))


# Useful generic names for higher-level benchmark runners.
ObservationSplit = CalibrationEvaluationSplit
DatasetSplit = CalibrationEvaluationSplit


__all__ = [
    "JSONPrimitive",
    "JSONValue",
    "MeasurementUncertainty",
    "MeasuredValue",
    "Measurement",
    "Provenance",
    "Observation",
    "CalibrationSplit",
    "EvaluationSplit",
    "CalibrationEvaluationSplit",
    "ObservationSplit",
    "DatasetSplit",
]
