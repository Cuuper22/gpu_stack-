"""Pure fail-stop preemption, lost-work, and checkpoint-recovery semantics.

Fail-stop means a failing site simply stops — it never emits corrupt work.

The complete :class:`FailureTrace` is environment state.  A policy receives
only :class:`FailureObservation` values returned by ``visible_at``.  In
particular, an active failure observation never carries the fixed future
recovery timestamp.  Recovery planning therefore cannot obtain future-trace
information through this API.

Work is modeled at explicit site-attempt boundaries.  An interrupted attempt
commits nothing, and its partial attempted work is lost.  Replay attempts are
identified separately so physical attempted work, durable committed work,
failure loss, replay work, and successfully recomputed work never collapse
into one counter.
"""

from __future__ import annotations

import json
import hashlib
import math
from dataclasses import dataclass, field, replace
from decimal import Decimal, InvalidOperation, ROUND_CEILING
from enum import Enum
from numbers import Real
from types import MappingProxyType
from typing import Iterable, Mapping, Optional, Sequence, Tuple, Union


JSONPrimitive = Union[None, bool, int, float, str]
JSONValue = Union[
    JSONPrimitive,
    Mapping[str, "JSONValue"],
    Sequence["JSONValue"],
]


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-blank string")
    return value.strip()


def _optional_text(value: object, field_name: str) -> Optional[str]:
    if value is None:
        return None
    return _text(value, field_name)


def _integer(value: object, field_name: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer")
    if value < minimum:
        raise ValueError(f"{field_name} must be >= {minimum}")
    return value


def _finite(value: object, field_name: str, *, minimum: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{field_name} must be a real number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{field_name} must be finite")
    if result < minimum:
        raise ValueError(f"{field_name} must be >= {minimum}")
    return result


def _positive(value: object, field_name: str) -> float:
    result = _finite(value, field_name)
    if result <= 0.0:
        raise ValueError(f"{field_name} must be > 0")
    return result


def _ordered_texts(values: object, field_name: str) -> Tuple[str, ...]:
    if isinstance(values, (str, bytes, bytearray)) or not isinstance(
        values, Iterable
    ):
        raise TypeError(f"{field_name} must be an ordered iterable of strings")
    if isinstance(values, (set, frozenset)):
        raise TypeError(f"{field_name} must be ordered, not a set")
    result = tuple(_text(value, field_name) for value in values)
    if len(result) != len(set(result)):
        raise ValueError(f"{field_name} must not contain duplicates")
    return result


def _sequence(value: object, field_name: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(
        value, Sequence
    ):
        raise TypeError(f"{field_name} must be a JSON array")
    return value


def _same_work(left: float, right: float) -> bool:
    """Compare finite accounting values exactly in their decimal representation."""
    return Decimal(str(left)) == Decimal(str(right))


def _work_sum(values: Iterable[float]) -> float:
    """Order-independent decimal sum; overflow remains visible to validation."""
    total = sum((Decimal(str(value)) for value in values), Decimal(0))
    try:
        return float(total)
    except (OverflowError, ValueError):
        return math.inf


def _sha256(value: object, field_name: str) -> str:
    result = _text(value, field_name)
    prefix = "sha256:"
    digest = result[len(prefix) :] if result.startswith(prefix) else ""
    if len(digest) != 64 or any(
        character not in "0123456789abcdef" for character in digest
    ):
        raise ValueError(
            f"{field_name} must use lowercase sha256:<64-hex-digest> form"
        )
    return result


def _serialized_claim_matches(claimed: object, expected: object) -> bool:
    """Compare derived JSON claims without Python bool/number coercion."""
    if expected is None:
        return claimed is None
    if isinstance(expected, bool):
        return type(claimed) is bool and claimed is expected
    if isinstance(expected, int):
        return type(claimed) is int and claimed == expected
    if isinstance(expected, float):
        return (
            isinstance(claimed, Real)
            and not isinstance(claimed, bool)
            and math.isfinite(float(claimed))
            and float(claimed) == expected
        )
    if isinstance(expected, str):
        return type(claimed) is str and claimed == expected
    if isinstance(expected, list):
        return (
            isinstance(claimed, list)
            and len(claimed) == len(expected)
            and all(
                _serialized_claim_matches(actual, derived)
                for actual, derived in zip(claimed, expected)
            )
        )
    return type(claimed) is type(expected) and claimed == expected


def _freeze_json(value: object, path: str) -> object:
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} contains a non-finite number")
        return value
    if isinstance(value, Mapping):
        invalid = [key for key in value if not isinstance(key, str) or not key]
        if invalid:
            raise ValueError(f"{path} keys must be non-empty strings")
        return MappingProxyType(
            {
                key: _freeze_json(value[key], f"{path}.{key}")
                for key in sorted(value)
            }
        )
    if isinstance(value, (set, frozenset)):
        raise TypeError(f"{path} must not contain unordered sets")
    if isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    ):
        return tuple(
            _freeze_json(item, f"{path}[{index}]")
            for index, item in enumerate(value)
        )
    raise TypeError(f"{path} contains a non-JSON-compatible value")


def _freeze_mapping(value: object, field_name: str) -> Mapping[str, JSONValue]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    frozen = _freeze_json(value, field_name)
    assert isinstance(frozen, Mapping)
    return frozen  # type: ignore[return-value]


def _thaw_json(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _thaw_json(value[key]) for key in sorted(value)}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


def _mapping(value: object, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    return value


def _json_dumps(value: Mapping[str, object], indent: Optional[int]) -> str:
    options: dict[str, object] = {"sort_keys": True, "allow_nan": False}
    if indent is None:
        options["separators"] = (",", ":")
    else:
        options["indent"] = indent
    return json.dumps(value, **options)


def _json_mapping(payload: str, field_name: str) -> Mapping[str, object]:
    try:
        value = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{field_name} payload is not valid JSON") from exc
    return _mapping(value, field_name)


def _ceil_duration_ns(amount: float, rate_per_second: float) -> int:
    if amount == 0.0:
        return 0
    try:
        duration = (
            Decimal(str(amount))
            / Decimal(str(rate_per_second))
            * Decimal(1_000_000_000)
        )
        if not duration.is_finite():
            raise ValueError("duration must be finite")
        return int(duration.to_integral_value(rounding=ROUND_CEILING))
    except (InvalidOperation, OverflowError, ValueError) as exc:
        raise ValueError("amount and rate produce an invalid duration") from exc


class EvidenceBasis(str, Enum):
    MEASURED = "measured"
    MODELED = "modeled"
    ASSUMED = "assumed"
    MIXED = "mixed"


@dataclass(frozen=True)
class EvidenceBoundary:
    """What evidence supports one recovery artifact and where it stops."""

    boundary_id: str
    basis: EvidenceBasis
    source_ids: Tuple[str, ...] = ()
    assumptions: Tuple[str, ...] = ()
    metadata: Mapping[str, JSONValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        basis = self.basis
        if not isinstance(basis, EvidenceBasis):
            try:
                basis = EvidenceBasis(basis)
            except (TypeError, ValueError) as exc:
                raise ValueError("basis must be a valid EvidenceBasis") from exc
        object.__setattr__(self, "boundary_id", _text(self.boundary_id, "boundary_id"))
        object.__setattr__(self, "basis", basis)
        object.__setattr__(
            self, "source_ids", _ordered_texts(self.source_ids, "source_ids")
        )
        object.__setattr__(
            self,
            "assumptions",
            _ordered_texts(self.assumptions, "assumptions"),
        )
        object.__setattr__(
            self, "metadata", _freeze_mapping(self.metadata, "evidence metadata")
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "assumptions": list(self.assumptions),
            "basis": self.basis.value,
            "boundary_id": self.boundary_id,
            "metadata": _thaw_json(self.metadata),
            "source_ids": list(self.source_ids),
        }

    def to_json(self, *, indent: Optional[int] = None) -> str:
        return _json_dumps(self.to_dict(), indent)

    def policy_safe(self) -> "EvidenceBoundary":
        """Return provenance identity without free-form future-trace channels."""
        if (
            not self.source_ids
            and not self.assumptions
            and dict(self.metadata) == {"policy_safe": True}
        ):
            return self
        return EvidenceBoundary(
            boundary_id=self.boundary_id,
            basis=self.basis,
            metadata={"policy_safe": True},
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "EvidenceBoundary":
        data = _mapping(data, "evidence boundary")
        return cls(
            boundary_id=data.get("boundary_id"),
            basis=data.get("basis"),
            source_ids=tuple(
                _sequence(data.get("source_ids", ()), "source_ids")
            ),
            assumptions=tuple(
                _sequence(data.get("assumptions", ()), "assumptions")
            ),
            metadata=_mapping(data.get("metadata", {}), "evidence metadata"),
        )

    @classmethod
    def from_json(cls, payload: str) -> "EvidenceBoundary":
        return cls.from_dict(_json_mapping(payload, "evidence boundary"))


class FailureStatus(str, Enum):
    ACTIVE = "active"
    RECOVERED = "recovered"


class FailureCauseCode(str, Enum):
    SITE_UNAVAILABLE = "site_unavailable"
    RESOURCE_UNAVAILABLE = "resource_unavailable"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class FailureObservation:
    """Policy-safe view of one failure as of one decision timestamp."""

    failure_id: str
    site_id: str
    failure_start_ns: int
    observed_at_ns: int
    status: FailureStatus
    cause: FailureCauseCode
    evidence: EvidenceBoundary
    recovery_observed_ns: Optional[int] = None

    def __post_init__(self) -> None:
        if not isinstance(self.evidence, EvidenceBoundary):
            raise TypeError("failure evidence must be an EvidenceBoundary")
        status = self.status
        if not isinstance(status, FailureStatus):
            try:
                status = FailureStatus(status)
            except (TypeError, ValueError) as exc:
                raise ValueError("status must be a valid FailureStatus") from exc
        cause = self.cause
        if not isinstance(cause, FailureCauseCode):
            try:
                cause = FailureCauseCode(cause)
            except (TypeError, ValueError) as exc:
                raise ValueError("cause must be a valid FailureCauseCode") from exc
        start = _integer(self.failure_start_ns, "failure_start_ns")
        observed = _integer(self.observed_at_ns, "observed_at_ns")
        if observed < start:
            raise ValueError("failure cannot be observed before it starts")
        recovery = self.recovery_observed_ns
        if status is FailureStatus.ACTIVE:
            if recovery is not None:
                raise ValueError(
                    "an active failure observation must not reveal future recovery"
                )
        else:
            recovery = _integer(recovery, "recovery_observed_ns")
            if recovery <= start or recovery > observed:
                raise ValueError(
                    "observed recovery must follow failure and not exceed observation time"
                )
        object.__setattr__(self, "failure_id", _text(self.failure_id, "failure_id"))
        object.__setattr__(self, "site_id", _text(self.site_id, "site_id"))
        object.__setattr__(self, "cause", cause)
        object.__setattr__(self, "failure_start_ns", start)
        object.__setattr__(self, "observed_at_ns", observed)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "recovery_observed_ns", recovery)
        object.__setattr__(self, "evidence", self.evidence.policy_safe())

    def to_dict(self) -> dict[str, object]:
        return {
            "cause": self.cause.value,
            "evidence": self.evidence.to_dict(),
            "failure_id": self.failure_id,
            "failure_start_ns": self.failure_start_ns,
            "observed_at_ns": self.observed_at_ns,
            "recovery_observed_ns": self.recovery_observed_ns,
            "site_id": self.site_id,
            "status": self.status.value,
        }

    def to_json(self, *, indent: Optional[int] = None) -> str:
        return _json_dumps(self.to_dict(), indent)

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "FailureObservation":
        data = _mapping(data, "failure observation")
        return cls(
            failure_id=data.get("failure_id"),
            site_id=data.get("site_id"),
            failure_start_ns=data.get("failure_start_ns"),
            observed_at_ns=data.get("observed_at_ns"),
            status=data.get("status"),
            cause=data.get("cause"),
            evidence=EvidenceBoundary.from_dict(
                _mapping(data.get("evidence"), "failure evidence")
            ),
            recovery_observed_ns=data.get("recovery_observed_ns"),
        )

    @classmethod
    def from_json(cls, payload: str) -> "FailureObservation":
        return cls.from_dict(_json_mapping(payload, "failure observation"))


@dataclass(frozen=True)
class FailureInterval:
    """One fixed, exogenous half-open fail-stop interval ``[start, recovery)``."""

    failure_id: str
    site_id: str
    failure_start_ns: int
    recovery_ns: int
    cause: FailureCauseCode
    evidence: EvidenceBoundary
    metadata: Mapping[str, JSONValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.evidence, EvidenceBoundary):
            raise TypeError("failure evidence must be an EvidenceBoundary")
        cause = self.cause
        if not isinstance(cause, FailureCauseCode):
            try:
                cause = FailureCauseCode(cause)
            except (TypeError, ValueError) as exc:
                raise ValueError("cause must be a valid FailureCauseCode") from exc
        start = _integer(self.failure_start_ns, "failure_start_ns")
        recovery = _integer(self.recovery_ns, "recovery_ns")
        if recovery <= start:
            raise ValueError("recovery_ns must be greater than failure_start_ns")
        object.__setattr__(self, "failure_id", _text(self.failure_id, "failure_id"))
        object.__setattr__(self, "site_id", _text(self.site_id, "site_id"))
        object.__setattr__(self, "failure_start_ns", start)
        object.__setattr__(self, "recovery_ns", recovery)
        object.__setattr__(self, "cause", cause)
        object.__setattr__(
            self, "metadata", _freeze_mapping(self.metadata, "failure metadata")
        )

    @property
    def duration_ns(self) -> int:
        return self.recovery_ns - self.failure_start_ns

    def overlaps(self, start_ns: int, end_ns: int) -> bool:
        start = _integer(start_ns, "start_ns")
        end = _integer(end_ns, "end_ns")
        if end < start:
            raise ValueError("end_ns must be >= start_ns")
        return self.failure_start_ns < end and self.recovery_ns > start

    def observation_at(self, timestamp_ns: int) -> Optional[FailureObservation]:
        timestamp = _integer(timestamp_ns, "timestamp_ns")
        if timestamp < self.failure_start_ns:
            return None
        if timestamp < self.recovery_ns:
            return FailureObservation(
                failure_id=self.failure_id,
                site_id=self.site_id,
                failure_start_ns=self.failure_start_ns,
                observed_at_ns=timestamp,
                status=FailureStatus.ACTIVE,
                cause=self.cause,
                evidence=self.evidence,
            )
        return FailureObservation(
            failure_id=self.failure_id,
            site_id=self.site_id,
            failure_start_ns=self.failure_start_ns,
            observed_at_ns=timestamp,
            status=FailureStatus.RECOVERED,
            recovery_observed_ns=self.recovery_ns,
            cause=self.cause,
            evidence=self.evidence,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "cause": self.cause.value,
            "duration_ns": self.duration_ns,
            "evidence": self.evidence.to_dict(),
            "failure_id": self.failure_id,
            "failure_start_ns": self.failure_start_ns,
            "metadata": _thaw_json(self.metadata),
            "recovery_ns": self.recovery_ns,
            "site_id": self.site_id,
        }

    def to_json(self, *, indent: Optional[int] = None) -> str:
        return _json_dumps(self.to_dict(), indent)

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "FailureInterval":
        data = _mapping(data, "failure interval")
        result = cls(
            failure_id=data.get("failure_id"),
            site_id=data.get("site_id"),
            failure_start_ns=data.get("failure_start_ns"),
            recovery_ns=data.get("recovery_ns"),
            cause=data.get("cause"),
            evidence=EvidenceBoundary.from_dict(
                _mapping(data.get("evidence"), "failure evidence")
            ),
            metadata=_mapping(data.get("metadata", {}), "failure metadata"),
        )
        claimed_duration = data.get("duration_ns")
        if "duration_ns" in data and not _serialized_claim_matches(
            claimed_duration, result.duration_ns
        ):
            raise ValueError("duration_ns is inconsistent with failure bounds")
        return result

    @classmethod
    def from_json(cls, payload: str) -> "FailureInterval":
        return cls.from_dict(_json_mapping(payload, "failure interval"))


@dataclass(frozen=True)
class FailureTrace:
    """Environment-owned fixed failure trace with a policy-safe visibility API."""

    trace_id: str
    intervals: Tuple[FailureInterval, ...]
    metadata: Mapping[str, JSONValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        intervals = tuple(self.intervals)
        if any(not isinstance(item, FailureInterval) for item in intervals):
            raise TypeError("intervals must contain only FailureInterval values")
        ids = [item.failure_id for item in intervals]
        if len(ids) != len(set(ids)):
            raise ValueError("failure interval IDs must be unique")
        intervals = tuple(
            sorted(
                intervals,
                key=lambda item: (
                    item.failure_start_ns,
                    item.recovery_ns,
                    item.site_id,
                    item.failure_id,
                ),
            )
        )
        previous_by_site: dict[str, FailureInterval] = {}
        for interval in intervals:
            previous = previous_by_site.get(interval.site_id)
            if previous is not None and interval.failure_start_ns < previous.recovery_ns:
                raise ValueError(
                    "failure intervals for one site must not overlap; merge the "
                    f"ambiguous intervals {previous.failure_id!r} and "
                    f"{interval.failure_id!r}"
                )
            previous_by_site[interval.site_id] = interval
        object.__setattr__(self, "trace_id", _text(self.trace_id, "trace_id"))
        object.__setattr__(self, "intervals", intervals)
        object.__setattr__(
            self, "metadata", _freeze_mapping(self.metadata, "failure trace metadata")
        )

    def visible_at(self, timestamp_ns: int) -> Tuple[FailureObservation, ...]:
        timestamp = _integer(timestamp_ns, "timestamp_ns")
        observations = (
            interval.observation_at(timestamp) for interval in self.intervals
        )
        return tuple(item for item in observations if item is not None)

    def active_at(self, timestamp_ns: int) -> Tuple[FailureObservation, ...]:
        return tuple(
            observation
            for observation in self.visible_at(timestamp_ns)
            if observation.status is FailureStatus.ACTIVE
        )

    def unavailable_site_ids(self, timestamp_ns: int) -> Tuple[str, ...]:
        return tuple(sorted({item.site_id for item in self.active_at(timestamp_ns)}))

    def to_dict(self) -> dict[str, object]:
        return {
            "intervals": [item.to_dict() for item in self.intervals],
            "metadata": _thaw_json(self.metadata),
            "trace_id": self.trace_id,
        }

    def to_json(self, *, indent: Optional[int] = None) -> str:
        return _json_dumps(self.to_dict(), indent)

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "FailureTrace":
        data = _mapping(data, "failure trace")
        return cls(
            trace_id=data.get("trace_id"),
            intervals=tuple(
                FailureInterval.from_dict(_mapping(item, "failure interval"))
                for item in _sequence(data.get("intervals", ()), "intervals")
            ),
            metadata=_mapping(data.get("metadata", {}), "failure trace metadata"),
        )

    @classmethod
    def from_json(cls, payload: str) -> "FailureTrace":
        return cls.from_dict(_json_mapping(payload, "failure trace"))


@dataclass(frozen=True)
class CompletedCheckpoint:
    """A checkpoint becomes visible only after all state bytes are complete."""

    checkpoint_id: str
    lineage_id: str
    step: int
    completed_at_ns: int
    state_bytes: int
    source_site_id: str
    site_membership: Tuple[str, ...]
    evidence: EvidenceBoundary
    metadata: Mapping[str, JSONValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.evidence, EvidenceBoundary):
            raise TypeError("checkpoint evidence must be an EvidenceBoundary")
        membership = _ordered_texts(self.site_membership, "site_membership")
        if not membership:
            raise ValueError("site_membership must not be empty")
        membership = tuple(sorted(membership))
        object.__setattr__(
            self, "checkpoint_id", _text(self.checkpoint_id, "checkpoint_id")
        )
        object.__setattr__(self, "lineage_id", _text(self.lineage_id, "lineage_id"))
        object.__setattr__(self, "step", _integer(self.step, "step"))
        object.__setattr__(
            self,
            "completed_at_ns",
            _integer(self.completed_at_ns, "completed_at_ns"),
        )
        object.__setattr__(
            self, "state_bytes", _integer(self.state_bytes, "state_bytes", minimum=1)
        )
        object.__setattr__(
            self, "source_site_id", _text(self.source_site_id, "source_site_id")
        )
        object.__setattr__(self, "site_membership", membership)
        metadata = _freeze_mapping(self.metadata, "checkpoint metadata")
        required_manifest_fields = (
            "state_version",
            "model_hash",
            "optimizer_hash",
            "rng_hash",
            "data_cursor_hash",
            "checkpoint_write_started_at_ns",
            "checkpoint_write_completed_at_ns",
            "manifest_committed_at_ns",
            "required_shard_ids",
            "shards",
        )
        missing = tuple(
            name for name in required_manifest_fields if name not in metadata
        )
        if missing:
            raise ValueError(
                "completed checkpoint lacks atomic manifest fields: "
                + ", ".join(missing)
            )
        state_version = _text(
            metadata["state_version"], "checkpoint metadata state_version"
        )
        for name in ("model_hash", "optimizer_hash", "rng_hash", "data_cursor_hash"):
            _sha256(metadata[name], f"checkpoint metadata {name}")
        write_started_at_ns = _integer(
            metadata["checkpoint_write_started_at_ns"],
            "checkpoint metadata checkpoint_write_started_at_ns",
        )
        write_completed_at_ns = _integer(
            metadata["checkpoint_write_completed_at_ns"],
            "checkpoint metadata checkpoint_write_completed_at_ns",
        )
        manifest_committed_at_ns = _integer(
            metadata["manifest_committed_at_ns"],
            "checkpoint metadata manifest_committed_at_ns",
        )
        if write_completed_at_ns < write_started_at_ns:
            raise ValueError("checkpoint write completion precedes its start")
        if manifest_committed_at_ns < write_completed_at_ns:
            raise ValueError("manifest commit precedes completed shard writes")
        if manifest_committed_at_ns != self.completed_at_ns:
            raise ValueError(
                "manifest_committed_at_ns must equal checkpoint completed_at_ns"
            )
        required_shard_ids = tuple(
            sorted(
                _ordered_texts(
                    _sequence(
                        metadata["required_shard_ids"],
                        "checkpoint metadata required_shard_ids",
                    ),
                    "checkpoint metadata required_shard_ids",
                )
            )
        )
        if not required_shard_ids:
            raise ValueError("completed checkpoint requires at least one shard")
        shards = _sequence(metadata["shards"], "checkpoint metadata shards")
        if not shards:
            raise ValueError("completed checkpoint manifest requires shards")
        shard_ids: list[str] = []
        shard_write_starts: list[int] = []
        shard_write_completions: list[int] = []
        partition_state_bytes = 0
        for index, raw_shard in enumerate(shards):
            shard = _mapping(raw_shard, f"checkpoint shard {index}")
            shard_id = _text(shard.get("shard_id"), "checkpoint shard_id")
            _text(shard.get("site_id"), "checkpoint shard site_id")
            source_state_version = _text(
                shard.get("source_state_version"),
                "checkpoint shard source_state_version",
            )
            if source_state_version != state_version:
                raise ValueError(
                    "checkpoint shard source state versions must be synchronized"
                )
            _text(
                shard.get("storage_location"),
                "checkpoint shard storage_location",
            )
            _text(shard.get("failure_domain"), "checkpoint shard failure_domain")
            shard_bytes = _integer(
                shard.get("state_bytes"),
                "checkpoint shard state_bytes",
                minimum=1,
            )
            _sha256(shard.get("checksum"), "checkpoint shard checksum")
            shard_write_started_at_ns = _integer(
                shard.get("write_started_at_ns"),
                "checkpoint shard write_started_at_ns",
            )
            shard_write_completed_at_ns = _integer(
                shard.get("write_completed_at_ns"),
                "checkpoint shard write_completed_at_ns",
            )
            if not (
                write_started_at_ns
                <= shard_write_started_at_ns
                <= shard_write_completed_at_ns
                <= write_completed_at_ns
            ):
                raise ValueError(
                    "checkpoint shard write interval lies outside checkpoint write"
                )
            shard_ids.append(shard_id)
            shard_write_starts.append(shard_write_started_at_ns)
            shard_write_completions.append(shard_write_completed_at_ns)
            partition_state_bytes += shard_bytes
        if len(shard_ids) != len(set(shard_ids)):
            raise ValueError("checkpoint manifest shard IDs must be unique")
        if tuple(sorted(shard_ids)) != required_shard_ids:
            raise ValueError(
                "required_shard_ids must exactly match completed manifest shards"
            )
        if partition_state_bytes != self.state_bytes:
            raise ValueError(
                "checkpoint shard partition must sum exactly to state_bytes"
            )
        if write_started_at_ns != min(shard_write_starts):
            raise ValueError(
                "checkpoint_write_started_at_ns must equal earliest shard write"
            )
        if write_completed_at_ns != max(shard_write_completions):
            raise ValueError(
                "checkpoint_write_completed_at_ns must equal latest shard write"
            )
        object.__setattr__(self, "metadata", metadata)

    @property
    def shard_source_site_ids(self) -> Tuple[str, ...]:
        shards = _sequence(self.metadata["shards"], "checkpoint metadata shards")
        return tuple(
            sorted(
                {
                    _text(
                        _mapping(shard, "checkpoint shard").get("site_id"),
                        "checkpoint shard site_id",
                    )
                    for shard in shards
                }
            )
        )

    def restore_resource_ids(self, target_site_id: str) -> Tuple[str, ...]:
        """Resources mechanically required to restore every manifest shard."""
        target = _text(target_site_id, "target_site_id")
        resources: set[str] = {f"state-io:{target}"}
        for raw_shard in _sequence(
            self.metadata["shards"], "checkpoint metadata shards"
        ):
            shard = _mapping(raw_shard, "checkpoint shard")
            source_site = _text(shard.get("site_id"), "checkpoint shard site_id")
            storage = _text(
                shard.get("storage_location"),
                "checkpoint shard storage_location",
            )
            failure_domain = _text(
                shard.get("failure_domain"), "checkpoint shard failure_domain"
            )
            resources.update(
                {
                    f"shard-source:{source_site}",
                    f"checkpoint-storage:{storage}",
                    f"failure-domain:{failure_domain}",
                    f"restore-path:{storage}->{target}",
                }
            )
        return tuple(sorted(resources))

    def to_dict(self) -> dict[str, object]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "completed_at_ns": self.completed_at_ns,
            "evidence": self.evidence.to_dict(),
            "lineage_id": self.lineage_id,
            "metadata": _thaw_json(self.metadata),
            "site_membership": list(self.site_membership),
            "source_site_id": self.source_site_id,
            "state_bytes": self.state_bytes,
            "step": self.step,
        }

    def to_json(self, *, indent: Optional[int] = None) -> str:
        return _json_dumps(self.to_dict(), indent)

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "CompletedCheckpoint":
        data = _mapping(data, "completed checkpoint")
        return cls(
            checkpoint_id=data.get("checkpoint_id"),
            lineage_id=data.get("lineage_id"),
            step=data.get("step"),
            completed_at_ns=data.get("completed_at_ns"),
            state_bytes=data.get("state_bytes"),
            source_site_id=data.get("source_site_id"),
            site_membership=tuple(
                _sequence(data.get("site_membership", ()), "site_membership")
            ),
            evidence=EvidenceBoundary.from_dict(
                _mapping(data.get("evidence"), "checkpoint evidence")
            ),
            metadata=_mapping(data.get("metadata", {}), "checkpoint metadata"),
        )

    @classmethod
    def from_json(cls, payload: str) -> "CompletedCheckpoint":
        return cls.from_dict(_json_mapping(payload, "completed checkpoint"))


@dataclass(frozen=True)
class CheckpointLedger:
    checkpoints: Tuple[CompletedCheckpoint, ...]

    def __post_init__(self) -> None:
        checkpoints = tuple(self.checkpoints)
        if any(not isinstance(item, CompletedCheckpoint) for item in checkpoints):
            raise TypeError("checkpoints must contain CompletedCheckpoint values")
        ids = [item.checkpoint_id for item in checkpoints]
        if len(ids) != len(set(ids)):
            raise ValueError("checkpoint IDs must be unique")
        frontiers = [(item.lineage_id, item.step) for item in checkpoints]
        if len(frontiers) != len(set(frontiers)):
            raise ValueError(
                "checkpoint state frontiers must be unique within a lineage"
            )
        lineages = {item.lineage_id for item in checkpoints}
        missing_genesis = sorted(
            lineage
            for lineage in lineages
            if not any(
                item.lineage_id == lineage and item.step == 0
                for item in checkpoints
            )
        )
        if missing_genesis:
            raise ValueError(
                "checkpoint lineages require an explicit step-zero genesis manifest: "
                f"{missing_genesis}"
            )
        for lineage in lineages:
            genesis = next(
                item
                for item in checkpoints
                if item.lineage_id == lineage and item.step == 0
            )
            if any(
                item.lineage_id == lineage
                and item.step > 0
                and item.completed_at_ns < genesis.completed_at_ns
                for item in checkpoints
            ):
                raise ValueError(
                    "genesis manifest must complete before later checkpoints"
                )
        object.__setattr__(
            self,
            "checkpoints",
            tuple(
                sorted(
                    checkpoints,
                    key=lambda item: (
                        item.completed_at_ns,
                        item.step,
                        item.checkpoint_id,
                    ),
                )
            ),
        )

    def visible_at(
        self, decision_time_ns: int, *, lineage_id: Optional[str] = None
    ) -> Tuple[CompletedCheckpoint, ...]:
        decision = _integer(decision_time_ns, "decision_time_ns")
        lineage = None if lineage_id is None else _text(lineage_id, "lineage_id")
        return tuple(
            checkpoint
            for checkpoint in self.checkpoints
            if checkpoint.completed_at_ns <= decision
            and (lineage is None or checkpoint.lineage_id == lineage)
        )

    def latest_at(
        self, decision_time_ns: int, *, lineage_id: str
    ) -> Optional[CompletedCheckpoint]:
        visible = self.visible_at(decision_time_ns, lineage_id=lineage_id)
        if not visible:
            return None
        return sorted(
            visible,
            key=lambda item: (
                -item.step,
                -item.completed_at_ns,
                item.checkpoint_id,
            ),
        )[0]

    def to_dict(self) -> dict[str, object]:
        return {"checkpoints": [item.to_dict() for item in self.checkpoints]}

    def to_json(self, *, indent: Optional[int] = None) -> str:
        return _json_dumps(self.to_dict(), indent)

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "CheckpointLedger":
        data = _mapping(data, "checkpoint ledger")
        return cls(
            checkpoints=tuple(
                CompletedCheckpoint.from_dict(
                    _mapping(item, "completed checkpoint")
                )
                for item in _sequence(
                    data.get("checkpoints", ()), "checkpoints"
                )
            )
        )

    @classmethod
    def from_json(cls, payload: str) -> "CheckpointLedger":
        return cls.from_dict(_json_mapping(payload, "checkpoint ledger"))


class WorkAttemptKind(str, Enum):
    FORWARD = "forward"
    REPLAY = "replay"


class WorkOutcomeDisposition(str, Enum):
    VALID_COMMITTED = "valid_committed"
    INTERRUPTED_LOST = "interrupted_lost"
    INVALIDATED_AFTER_COMMIT = "invalidated_after_commit"
    SUPERSEDED = "superseded"


@dataclass(frozen=True)
class LogicalWorkIdentity:
    """Immutable logical contribution identity, independent of execution site."""

    logical_work_id: str
    lineage_id: str
    logical_step: int
    logical_partition: str
    original_site_id: str
    state_lineage_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "logical_work_id", _text(self.logical_work_id, "logical_work_id")
        )
        object.__setattr__(self, "lineage_id", _text(self.lineage_id, "lineage_id"))
        object.__setattr__(
            self,
            "logical_step",
            _integer(self.logical_step, "logical_step", minimum=1),
        )
        object.__setattr__(
            self,
            "logical_partition",
            _text(self.logical_partition, "logical_partition"),
        )
        object.__setattr__(
            self,
            "original_site_id",
            _text(self.original_site_id, "original_site_id"),
        )
        object.__setattr__(
            self,
            "state_lineage_hash",
            _sha256(self.state_lineage_hash, "state_lineage_hash"),
        )

    @property
    def coordinate(self) -> Tuple[str, str, int]:
        return (
            self.lineage_id,
            self.original_site_id,
            self.logical_step,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "lineage_id": self.lineage_id,
            "logical_partition": self.logical_partition,
            "logical_step": self.logical_step,
            "logical_work_id": self.logical_work_id,
            "original_site_id": self.original_site_id,
            "state_lineage_hash": self.state_lineage_hash,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "LogicalWorkIdentity":
        data = _mapping(data, "logical work identity")
        return cls(
            logical_work_id=data.get("logical_work_id"),
            lineage_id=data.get("lineage_id"),
            logical_step=data.get("logical_step"),
            logical_partition=data.get("logical_partition"),
            original_site_id=data.get("original_site_id"),
            state_lineage_hash=data.get("state_lineage_hash"),
        )


@dataclass(frozen=True)
class ReplayLineageBinding:
    target_attempt_id: str
    logical_work: LogicalWorkIdentity

    def __post_init__(self) -> None:
        if not isinstance(self.logical_work, LogicalWorkIdentity):
            raise TypeError("logical_work must be a LogicalWorkIdentity")
        object.__setattr__(
            self,
            "target_attempt_id",
            _text(self.target_attempt_id, "target_attempt_id"),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "logical_work": self.logical_work.to_dict(),
            "target_attempt_id": self.target_attempt_id,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "ReplayLineageBinding":
        data = _mapping(data, "replay lineage binding")
        return cls(
            target_attempt_id=data.get("target_attempt_id"),
            logical_work=LogicalWorkIdentity.from_dict(
                _mapping(data.get("logical_work"), "logical work identity")
            ),
        )


@dataclass(frozen=True)
class SiteWorkAttempt:
    """One atomic site contribution that commits only at its planned end."""

    attempt_id: str
    lineage_id: str
    site_id: str
    step: int
    start_ns: int
    planned_end_ns: int
    planned_work: float
    work_unit: str
    kind: WorkAttemptKind
    evidence: EvidenceBoundary
    recovery_plan_id: Optional[str] = None
    supersedes_attempt_ids: Tuple[str, ...] = ()
    logical_work: Optional[LogicalWorkIdentity] = None
    replay_bindings: Tuple[ReplayLineageBinding, ...] = ()
    metadata: Mapping[str, JSONValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.evidence, EvidenceBoundary):
            raise TypeError("work-attempt evidence must be an EvidenceBoundary")
        kind = self.kind
        if not isinstance(kind, WorkAttemptKind):
            try:
                kind = WorkAttemptKind(kind)
            except (TypeError, ValueError) as exc:
                raise ValueError("kind must be a valid WorkAttemptKind") from exc
        start = _integer(self.start_ns, "start_ns")
        planned_end = _integer(self.planned_end_ns, "planned_end_ns")
        if planned_end <= start:
            raise ValueError("planned_end_ns must be greater than start_ns")
        recovery_plan_id = _optional_text(
            self.recovery_plan_id, "recovery_plan_id"
        )
        supersedes_attempt_ids = _ordered_texts(
            self.supersedes_attempt_ids, "supersedes_attempt_ids"
        )
        logical_work = self.logical_work
        replay_bindings = tuple(self.replay_bindings)
        if any(
            not isinstance(item, ReplayLineageBinding) for item in replay_bindings
        ):
            raise TypeError(
                "replay_bindings must contain ReplayLineageBinding values"
            )
        binding_keys = [
            (item.target_attempt_id, item.logical_work.logical_work_id)
            for item in replay_bindings
        ]
        if len(binding_keys) != len(set(binding_keys)):
            raise ValueError("replay lineage bindings must be unique")
        logical_binding_ids = [
            item.logical_work.logical_work_id for item in replay_bindings
        ]
        logical_binding_coordinates = [
            item.logical_work.coordinate for item in replay_bindings
        ]
        if len(logical_binding_ids) != len(set(logical_binding_ids)) or len(
            logical_binding_coordinates
        ) != len(set(logical_binding_coordinates)):
            raise ValueError(
                "a replay cannot bind one logical contribution more than once"
            )
        if kind is WorkAttemptKind.REPLAY:
            if (
                recovery_plan_id is None
                or not supersedes_attempt_ids
                or not replay_bindings
            ):
                raise ValueError(
                    "a replay attempt requires recovery_plan_id and "
                    "typed supersession bindings"
                )
            if logical_work is not None:
                raise ValueError("aggregate replay identity comes from replay_bindings")
            if set(supersedes_attempt_ids) != {
                item.target_attempt_id for item in replay_bindings
            }:
                raise ValueError(
                    "supersedes_attempt_ids must exactly match replay binding targets"
                )
        elif (
            recovery_plan_id is not None
            or supersedes_attempt_ids
            or replay_bindings
        ):
            raise ValueError(
                "a forward attempt must not name recovery or superseded attempts"
            )
        else:
            if not isinstance(logical_work, LogicalWorkIdentity):
                raise TypeError(
                    "a forward attempt requires a LogicalWorkIdentity"
                )
            if logical_work.lineage_id != _text(self.lineage_id, "lineage_id"):
                raise ValueError("logical work lineage must match attempt lineage")
            if logical_work.logical_step != _integer(
                self.step, "step", minimum=1
            ):
                raise ValueError("forward step must match logical work step")
            if logical_work.original_site_id != _text(self.site_id, "site_id"):
                raise ValueError(
                    "forward execution site must match logical original_site_id"
                )
        object.__setattr__(self, "attempt_id", _text(self.attempt_id, "attempt_id"))
        object.__setattr__(self, "lineage_id", _text(self.lineage_id, "lineage_id"))
        object.__setattr__(self, "site_id", _text(self.site_id, "site_id"))
        object.__setattr__(self, "step", _integer(self.step, "step", minimum=1))
        object.__setattr__(self, "start_ns", start)
        object.__setattr__(self, "planned_end_ns", planned_end)
        object.__setattr__(
            self, "planned_work", _positive(self.planned_work, "planned_work")
        )
        object.__setattr__(self, "work_unit", _text(self.work_unit, "work_unit"))
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "recovery_plan_id", recovery_plan_id)
        object.__setattr__(
            self, "supersedes_attempt_ids", supersedes_attempt_ids
        )
        object.__setattr__(self, "logical_work", logical_work)
        object.__setattr__(self, "replay_bindings", replay_bindings)
        object.__setattr__(
            self, "metadata", _freeze_mapping(self.metadata, "work-attempt metadata")
        )

    @property
    def planned_duration_ns(self) -> int:
        return self.planned_end_ns - self.start_ns

    def to_dict(self) -> dict[str, object]:
        return {
            "attempt_id": self.attempt_id,
            "evidence": self.evidence.to_dict(),
            "kind": self.kind.value,
            "lineage_id": self.lineage_id,
            "logical_work": (
                None if self.logical_work is None else self.logical_work.to_dict()
            ),
            "metadata": _thaw_json(self.metadata),
            "planned_duration_ns": self.planned_duration_ns,
            "planned_end_ns": self.planned_end_ns,
            "planned_work": self.planned_work,
            "recovery_plan_id": self.recovery_plan_id,
            "replay_bindings": [item.to_dict() for item in self.replay_bindings],
            "site_id": self.site_id,
            "start_ns": self.start_ns,
            "step": self.step,
            "supersedes_attempt_ids": list(self.supersedes_attempt_ids),
            "work_unit": self.work_unit,
        }

    def to_json(self, *, indent: Optional[int] = None) -> str:
        return _json_dumps(self.to_dict(), indent)

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "SiteWorkAttempt":
        data = _mapping(data, "site work attempt")
        result = cls(
            attempt_id=data.get("attempt_id"),
            lineage_id=data.get("lineage_id"),
            site_id=data.get("site_id"),
            step=data.get("step"),
            start_ns=data.get("start_ns"),
            planned_end_ns=data.get("planned_end_ns"),
            planned_work=data.get("planned_work"),
            work_unit=data.get("work_unit"),
            kind=data.get("kind"),
            recovery_plan_id=data.get("recovery_plan_id"),
            supersedes_attempt_ids=tuple(
                _sequence(
                    data.get("supersedes_attempt_ids", ()),
                    "supersedes_attempt_ids",
                )
            ),
            logical_work=(
                None
                if data.get("logical_work") is None
                else LogicalWorkIdentity.from_dict(
                    _mapping(data.get("logical_work"), "logical work identity")
                )
            ),
            replay_bindings=tuple(
                ReplayLineageBinding.from_dict(
                    _mapping(item, "replay lineage binding")
                )
                for item in _sequence(
                    data.get("replay_bindings", ()), "replay_bindings"
                )
            ),
            evidence=EvidenceBoundary.from_dict(
                _mapping(data.get("evidence"), "work-attempt evidence")
            ),
            metadata=_mapping(data.get("metadata", {}), "work-attempt metadata"),
        )
        claimed_duration = data.get("planned_duration_ns")
        if "planned_duration_ns" in data and not _serialized_claim_matches(
            claimed_duration, result.planned_duration_ns
        ):
            raise ValueError("planned_duration_ns is inconsistent with attempt bounds")
        return result

    @classmethod
    def from_json(cls, payload: str) -> "SiteWorkAttempt":
        return cls.from_dict(_json_mapping(payload, "site work attempt"))


@dataclass(frozen=True)
class WorkAttemptOutcome:
    """Mechanistic outcome of one atomic attempt under a fixed failure trace."""

    attempt: SiteWorkAttempt
    execution_end_ns: int
    interrupted: bool
    interruption_failure_id: Optional[str]
    attempted_work: float
    committed_work: float
    lost_work: float
    replayed_work: float
    recomputed_work: float
    disposition: WorkOutcomeDisposition = WorkOutcomeDisposition.VALID_COMMITTED
    invalidated_by_recovery_id: Optional[str] = None
    superseded_by_attempt_id: Optional[str] = None
    invalidation_effective_at_ns: Optional[int] = None
    supersession_effective_at_ns: Optional[int] = None

    def __post_init__(self) -> None:
        if not isinstance(self.attempt, SiteWorkAttempt):
            raise TypeError("attempt must be a SiteWorkAttempt")
        if not isinstance(self.interrupted, bool):
            raise TypeError("interrupted must be bool")
        execution_end = _integer(self.execution_end_ns, "execution_end_ns")
        if not self.attempt.start_ns <= execution_end <= self.attempt.planned_end_ns:
            raise ValueError("execution_end_ns lies outside the attempt")
        failure_id = _optional_text(
            self.interruption_failure_id, "interruption_failure_id"
        )
        disposition = self.disposition
        if not isinstance(disposition, WorkOutcomeDisposition):
            try:
                disposition = WorkOutcomeDisposition(disposition)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    "disposition must be a valid WorkOutcomeDisposition"
                ) from exc
        invalidated_by = _optional_text(
            self.invalidated_by_recovery_id, "invalidated_by_recovery_id"
        )
        superseded_by = _optional_text(
            self.superseded_by_attempt_id, "superseded_by_attempt_id"
        )
        invalidation_at = self.invalidation_effective_at_ns
        supersession_at = self.supersession_effective_at_ns
        if self.interrupted:
            if failure_id is None:
                raise ValueError("an interrupted attempt requires a failure ID")
            if execution_end >= self.attempt.planned_end_ns:
                raise ValueError("an interrupted attempt must end before planned end")
            if disposition is not WorkOutcomeDisposition.INTERRUPTED_LOST:
                raise ValueError(
                    "an interrupted attempt requires interrupted_lost disposition"
                )
            if (
                invalidated_by is not None
                or superseded_by is not None
                or invalidation_at is not None
                or supersession_at is not None
            ):
                raise ValueError(
                    "an interrupted attempt cannot be invalidated or superseded"
                )
        else:
            if failure_id is not None:
                raise ValueError("a completed attempt must not name a failure")
            if execution_end != self.attempt.planned_end_ns:
                raise ValueError("a completed attempt must end at planned_end_ns")
        attempted = _finite(self.attempted_work, "attempted_work")
        committed = _finite(self.committed_work, "committed_work")
        lost = _finite(self.lost_work, "lost_work")
        replayed = _finite(self.replayed_work, "replayed_work")
        recomputed = _finite(self.recomputed_work, "recomputed_work")
        if Decimal(str(attempted)) > Decimal(str(self.attempt.planned_work)):
            raise ValueError("attempted_work cannot exceed planned_work")
        if not _same_work(attempted, _work_sum((committed, lost))):
            raise ValueError("attempted_work must equal committed plus lost work")
        if self.interrupted:
            if committed != 0.0:
                raise ValueError("an interrupted atomic attempt commits no work")
        elif disposition is WorkOutcomeDisposition.VALID_COMMITTED:
            if not _same_work(committed, self.attempt.planned_work) or lost != 0.0:
                raise ValueError(
                    "a valid completed attempt commits all planned work"
                )
            if (
                invalidated_by is not None
                or superseded_by is not None
                or invalidation_at is not None
                or supersession_at is not None
            ):
                raise ValueError(
                    "a valid completed attempt cannot name invalidation lineage"
                )
        else:
            if committed != 0.0 or not _same_work(lost, attempted):
                raise ValueError(
                    "an invalidated or superseded attempt must move all work to loss"
                )
            if invalidated_by is None:
                raise ValueError(
                    "an invalidated or superseded attempt requires recovery lineage"
                )
            invalidation_at = _integer(
                invalidation_at, "invalidation_effective_at_ns"
            )
            if invalidation_at < execution_end:
                raise ValueError("invalidation cannot precede committed execution")
            if disposition is WorkOutcomeDisposition.SUPERSEDED:
                if superseded_by is None:
                    raise ValueError(
                        "a superseded attempt requires superseded_by_attempt_id"
                    )
                supersession_at = _integer(
                    supersession_at, "supersession_effective_at_ns"
                )
                if supersession_at < invalidation_at:
                    raise ValueError("supersession cannot precede invalidation")
            elif superseded_by is not None or supersession_at is not None:
                raise ValueError(
                    "invalidated_after_commit must not expose a future replacement"
                )
        if self.attempt.kind is WorkAttemptKind.FORWARD:
            if replayed != 0.0 or recomputed != 0.0:
                raise ValueError("forward work cannot be labeled replayed or recomputed")
        else:
            if not _same_work(replayed, attempted):
                raise ValueError("replayed_work must equal replay attempt work")
            if not _same_work(recomputed, committed):
                raise ValueError("recomputed_work must equal committed replay work")
        object.__setattr__(self, "execution_end_ns", execution_end)
        object.__setattr__(self, "interruption_failure_id", failure_id)
        object.__setattr__(self, "attempted_work", attempted)
        object.__setattr__(self, "committed_work", committed)
        object.__setattr__(self, "lost_work", lost)
        object.__setattr__(self, "replayed_work", replayed)
        object.__setattr__(self, "recomputed_work", recomputed)
        object.__setattr__(self, "disposition", disposition)
        object.__setattr__(self, "invalidated_by_recovery_id", invalidated_by)
        object.__setattr__(self, "superseded_by_attempt_id", superseded_by)
        object.__setattr__(
            self, "invalidation_effective_at_ns", invalidation_at
        )
        object.__setattr__(
            self, "supersession_effective_at_ns", supersession_at
        )

    @property
    def completed_steps(self) -> Tuple[int, ...]:
        if self.disposition is not WorkOutcomeDisposition.VALID_COMMITTED:
            return ()
        if self.attempt.kind is WorkAttemptKind.FORWARD:
            assert self.attempt.logical_work is not None
            return (self.attempt.logical_work.logical_step,)
        return tuple(
            sorted(
                {
                    binding.logical_work.logical_step
                    for binding in self.attempt.replay_bindings
                }
            )
        )

    @property
    def completed_step(self) -> Optional[int]:
        return self.completed_steps[0] if len(self.completed_steps) == 1 else None

    def invalidate(
        self,
        recovery_id: str,
        *,
        effective_at_ns: int,
        superseded_by_attempt_id: Optional[str] = None,
        supersession_effective_at_ns: Optional[int] = None,
    ) -> "WorkAttemptOutcome":
        """Move a completed contribution from final-valid work into loss."""
        if self.interrupted:
            raise ValueError("interrupted work is already lost")
        recovery = _text(recovery_id, "recovery_id")
        invalidation_at = _integer(effective_at_ns, "effective_at_ns")
        if invalidation_at < self.execution_end_ns:
            raise ValueError("invalidation cannot precede committed execution")
        replacement_id = _optional_text(
            superseded_by_attempt_id, "superseded_by_attempt_id"
        )
        if self.disposition is WorkOutcomeDisposition.SUPERSEDED:
            raise ValueError("superseded work cannot be retargeted")
        if self.disposition is WorkOutcomeDisposition.INVALIDATED_AFTER_COMMIT:
            if (
                self.invalidated_by_recovery_id != recovery
                or self.invalidation_effective_at_ns != invalidation_at
            ):
                raise ValueError("invalidation recovery lineage is immutable")
            if replacement_id is None:
                return self
            supersession_at = _integer(
                supersession_effective_at_ns,
                "supersession_effective_at_ns",
            )
            return replace(
                self,
                disposition=WorkOutcomeDisposition.SUPERSEDED,
                superseded_by_attempt_id=replacement_id,
                supersession_effective_at_ns=supersession_at,
            )
        if self.disposition is not WorkOutcomeDisposition.VALID_COMMITTED:
            raise ValueError("only completed work can be invalidated")
        supersession_at = None
        if replacement_id is not None:
            supersession_at = _integer(
                supersession_effective_at_ns,
                "supersession_effective_at_ns",
            )
        return replace(
            self,
            committed_work=0.0,
            lost_work=self.attempted_work,
            recomputed_work=0.0,
            disposition=(
                WorkOutcomeDisposition.SUPERSEDED
                if replacement_id is not None
                else WorkOutcomeDisposition.INVALIDATED_AFTER_COMMIT
            ),
            invalidated_by_recovery_id=recovery,
            superseded_by_attempt_id=replacement_id,
            invalidation_effective_at_ns=invalidation_at,
            supersession_effective_at_ns=supersession_at,
        )

    def as_of(self, timestamp_ns: int) -> "WorkAttemptOutcome":
        """Reconstruct this outcome without leaking later disposition changes."""
        timestamp = _integer(timestamp_ns, "timestamp_ns")
        if timestamp < self.execution_end_ns:
            raise ValueError("outcome is not yet visible at timestamp_ns")
        invalidation_at = self.invalidation_effective_at_ns
        if invalidation_at is None or timestamp >= invalidation_at:
            if (
                self.disposition is WorkOutcomeDisposition.SUPERSEDED
                and self.supersession_effective_at_ns is not None
                and timestamp < self.supersession_effective_at_ns
            ):
                return replace(
                    self,
                    disposition=WorkOutcomeDisposition.INVALIDATED_AFTER_COMMIT,
                    superseded_by_attempt_id=None,
                    supersession_effective_at_ns=None,
                )
            return self
        return replace(
            self,
            committed_work=self.attempted_work,
            lost_work=0.0,
            recomputed_work=(
                self.attempted_work
                if self.attempt.kind is WorkAttemptKind.REPLAY
                else 0.0
            ),
            disposition=WorkOutcomeDisposition.VALID_COMMITTED,
            invalidated_by_recovery_id=None,
            superseded_by_attempt_id=None,
            invalidation_effective_at_ns=None,
            supersession_effective_at_ns=None,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "attempt": self.attempt.to_dict(),
            "attempted_work": self.attempted_work,
            "committed_work": self.committed_work,
            "completed_step": self.completed_step,
            "completed_steps": list(self.completed_steps),
            "disposition": self.disposition.value,
            "execution_end_ns": self.execution_end_ns,
            "invalidated_by_recovery_id": self.invalidated_by_recovery_id,
            "invalidation_effective_at_ns": self.invalidation_effective_at_ns,
            "interrupted": self.interrupted,
            "interruption_failure_id": self.interruption_failure_id,
            "lost_work": self.lost_work,
            "recomputed_work": self.recomputed_work,
            "replayed_work": self.replayed_work,
            "superseded_by_attempt_id": self.superseded_by_attempt_id,
            "supersession_effective_at_ns": self.supersession_effective_at_ns,
        }

    def to_json(self, *, indent: Optional[int] = None) -> str:
        return _json_dumps(self.to_dict(), indent)

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "WorkAttemptOutcome":
        data = _mapping(data, "work-attempt outcome")
        interrupted = data.get("interrupted")
        raw_disposition = data.get("disposition")
        if raw_disposition is None:
            raw_disposition = (
                WorkOutcomeDisposition.INTERRUPTED_LOST.value
                if interrupted is True
                else WorkOutcomeDisposition.VALID_COMMITTED.value
            )
        result = cls(
            attempt=SiteWorkAttempt.from_dict(
                _mapping(data.get("attempt"), "site work attempt")
            ),
            execution_end_ns=data.get("execution_end_ns"),
            interrupted=interrupted,
            interruption_failure_id=data.get("interruption_failure_id"),
            attempted_work=data.get("attempted_work"),
            committed_work=data.get("committed_work"),
            lost_work=data.get("lost_work"),
            replayed_work=data.get("replayed_work"),
            recomputed_work=data.get("recomputed_work"),
            disposition=raw_disposition,
            invalidated_by_recovery_id=data.get("invalidated_by_recovery_id"),
            superseded_by_attempt_id=data.get("superseded_by_attempt_id"),
            invalidation_effective_at_ns=data.get(
                "invalidation_effective_at_ns"
            ),
            supersession_effective_at_ns=data.get(
                "supersession_effective_at_ns"
            ),
        )
        claimed_step = data.get("completed_step")
        if "completed_step" in data and not _serialized_claim_matches(
            claimed_step, result.completed_step
        ):
            raise ValueError("completed_step is inconsistent with attempt outcome")
        if "completed_steps" in data and not _serialized_claim_matches(
            data.get("completed_steps"), list(result.completed_steps)
        ):
            raise ValueError("completed_steps is inconsistent with attempt outcome")
        return result

    @classmethod
    def from_json(cls, payload: str) -> "WorkAttemptOutcome":
        return cls.from_dict(_json_mapping(payload, "work-attempt outcome"))


def evaluate_work_attempt(
    attempt: SiteWorkAttempt,
    failure_trace: FailureTrace,
) -> WorkAttemptOutcome:
    """Evaluate one atomic attempt against fixed exogenous intervals."""
    if not isinstance(attempt, SiteWorkAttempt):
        raise TypeError("attempt must be a SiteWorkAttempt")
    if not isinstance(failure_trace, FailureTrace):
        raise TypeError("failure_trace must be a FailureTrace")
    candidates = []
    for interval in failure_trace.intervals:
        if interval.site_id != attempt.site_id:
            continue
        if interval.overlaps(attempt.start_ns, attempt.planned_end_ns):
            candidates.append(
                (max(attempt.start_ns, interval.failure_start_ns), interval)
            )
    if not candidates:
        attempted = attempt.planned_work
        interrupted = False
        end_ns = attempt.planned_end_ns
        failure_id = None
        committed = attempted
        lost = 0.0
    else:
        end_ns, interval = min(
            candidates, key=lambda item: (item[0], item[1].failure_id)
        )
        interrupted = True
        failure_id = interval.failure_id
        elapsed_fraction = (
            (end_ns - attempt.start_ns) / attempt.planned_duration_ns
        )
        attempted = attempt.planned_work * elapsed_fraction
        committed = 0.0
        lost = attempted
    replayed = attempted if attempt.kind is WorkAttemptKind.REPLAY else 0.0
    recomputed = committed if attempt.kind is WorkAttemptKind.REPLAY else 0.0
    return WorkAttemptOutcome(
        attempt=attempt,
        execution_end_ns=end_ns,
        interrupted=interrupted,
        interruption_failure_id=failure_id,
        attempted_work=attempted,
        committed_work=committed,
        lost_work=lost,
        replayed_work=replayed,
        recomputed_work=recomputed,
        disposition=(
            WorkOutcomeDisposition.INTERRUPTED_LOST
            if interrupted
            else WorkOutcomeDisposition.VALID_COMMITTED
        ),
    )


@dataclass(frozen=True)
class WorkLedger:
    """Immutable ledger preserving explicit work-accounting relationships."""

    outcomes: Tuple[WorkAttemptOutcome, ...]
    as_of_ns: Optional[int] = None

    def __post_init__(self) -> None:
        outcomes = tuple(self.outcomes)
        if any(not isinstance(item, WorkAttemptOutcome) for item in outcomes):
            raise TypeError("outcomes must contain WorkAttemptOutcome values")
        as_of = self.as_of_ns
        if as_of is not None:
            as_of = _integer(as_of, "as_of_ns")
            if any(item.execution_end_ns > as_of for item in outcomes):
                raise ValueError("as-of work ledger contains a future outcome")
            if any(
                item.invalidation_effective_at_ns is not None
                and item.invalidation_effective_at_ns > as_of
                for item in outcomes
            ):
                raise ValueError("as-of work ledger leaks a future invalidation")
            if any(
                item.supersession_effective_at_ns is not None
                and item.supersession_effective_at_ns > as_of
                for item in outcomes
            ):
                raise ValueError("as-of work ledger leaks a future supersession")
        ids = [item.attempt.attempt_id for item in outcomes]
        if len(ids) != len(set(ids)):
            raise ValueError("work attempt IDs must be unique")
        units = {item.attempt.work_unit for item in outcomes}
        if len(units) > 1:
            raise ValueError("one work ledger cannot mix work units")
        by_id = {item.attempt.attempt_id: item for item in outcomes}
        referenced_targets: dict[str, str] = {}
        identity_registry: dict[str, LogicalWorkIdentity] = {}
        logical_amount_registry: dict[str, float] = {}

        def identities(outcome: WorkAttemptOutcome) -> Tuple[LogicalWorkIdentity, ...]:
            if outcome.attempt.kind is WorkAttemptKind.FORWARD:
                assert outcome.attempt.logical_work is not None
                return (outcome.attempt.logical_work,)
            return tuple(binding.logical_work for binding in outcome.attempt.replay_bindings)

        for outcome in outcomes:
            for identity in identities(outcome):
                prior_identity = identity_registry.get(identity.logical_work_id)
                if prior_identity is not None and prior_identity != identity:
                    raise ValueError(
                        "logical_work_id cannot change immutable state lineage"
                    )
                identity_registry[identity.logical_work_id] = identity
                if identity.lineage_id != outcome.attempt.lineage_id:
                    raise ValueError(
                        "logical work identity must match attempt lineage"
                    )
            if outcome.attempt.kind is WorkAttemptKind.FORWARD:
                assert outcome.attempt.logical_work is not None
                logical_id = outcome.attempt.logical_work.logical_work_id
                prior_amount = logical_amount_registry.get(logical_id)
                if prior_amount is not None and not _same_work(
                    prior_amount, outcome.attempt.planned_work
                ):
                    raise ValueError(
                        "logical_work_id cannot change its planned work amount"
                    )
                logical_amount_registry[logical_id] = outcome.attempt.planned_work

        for outcome in outcomes:
            if outcome.attempt.kind is not WorkAttemptKind.REPLAY:
                continue
            targets = tuple(
                by_id.get(attempt_id)
                for attempt_id in outcome.attempt.supersedes_attempt_ids
            )
            if any(item is None for item in targets):
                missing = sorted(
                    set(outcome.attempt.supersedes_attempt_ids) - set(by_id)
                )
                raise ValueError(
                    f"replay attempt references unknown superseded attempts: {missing}"
                )
            typed_targets = tuple(item for item in targets if item is not None)
            if any(
                item.attempt.lineage_id != outcome.attempt.lineage_id
                or item.attempt.work_unit != outcome.attempt.work_unit
                for item in typed_targets
            ):
                raise ValueError(
                    "replay and superseded attempts must share lineage and work unit"
                )
            if any(
                item.execution_end_ns > outcome.attempt.start_ns
                for item in typed_targets
            ):
                raise ValueError("replay cannot supersede work from its future")
            bindings_by_target: dict[str, list[LogicalWorkIdentity]] = {}
            for binding in outcome.attempt.replay_bindings:
                bindings_by_target.setdefault(binding.target_attempt_id, []).append(
                    binding.logical_work
                )
            for target in typed_targets:
                expected = tuple(
                    sorted(
                        identities(target),
                        key=lambda item: (item.coordinate, item.logical_work_id),
                    )
                )
                claimed = tuple(
                    sorted(
                        bindings_by_target.get(target.attempt.attempt_id, ()),
                        key=lambda item: (item.coordinate, item.logical_work_id),
                    )
                )
                if claimed != expected:
                    raise ValueError(
                        "replay bindings must exactly match target logical lineage"
                    )
                if (
                    target.invalidated_by_recovery_id
                    != outcome.attempt.recovery_plan_id
                ):
                    raise ValueError(
                        "replay target invalidation must match recovery_plan_id"
                    )
            if outcome.disposition is WorkOutcomeDisposition.VALID_COMMITTED:
                for item in typed_targets:
                    prior = referenced_targets.get(item.attempt.attempt_id)
                    if prior is not None and prior != outcome.attempt.attempt_id:
                        raise ValueError(
                            "one superseded attempt cannot feed multiple successful "
                            "replay attempts"
                        )
                    referenced_targets[item.attempt.attempt_id] = (
                        outcome.attempt.attempt_id
                    )
                    if (
                        item.disposition is not WorkOutcomeDisposition.SUPERSEDED
                        or item.superseded_by_attempt_id
                        != outcome.attempt.attempt_id
                        or item.supersession_effective_at_ns
                        != outcome.execution_end_ns
                    ):
                        raise ValueError(
                            "successful replay targets must carry matching "
                            "supersession at replay completion"
                        )
            target_work = _work_sum(item.attempted_work for item in typed_targets)
            if not _same_work(outcome.attempt.planned_work, target_work):
                raise ValueError(
                    "replay planned work must equal its superseded work"
                )
        for outcome in outcomes:
            if outcome.disposition is not WorkOutcomeDisposition.SUPERSEDED:
                continue
            replacement = by_id.get(outcome.superseded_by_attempt_id or "")
            if (
                replacement is None
                or replacement.disposition
                is not WorkOutcomeDisposition.VALID_COMMITTED
                or replacement.attempt.kind is not WorkAttemptKind.REPLAY
                or outcome.attempt.attempt_id
                not in replacement.attempt.supersedes_attempt_ids
            ):
                raise ValueError(
                    "superseded work must point to its committed replay outcome"
                )
        logical: dict[tuple[str, str, int], list[WorkAttemptOutcome]] = {}
        for outcome in outcomes:
            if outcome.disposition is not WorkOutcomeDisposition.VALID_COMMITTED:
                continue
            for identity in identities(outcome):
                logical.setdefault(identity.coordinate, []).append(outcome)
        for key, values in logical.items():
            distinct = {item.attempt.attempt_id for item in values}
            if len(distinct) > 1:
                raise ValueError(
                    f"logical work contribution {key!r} has multiple canonical outcomes"
                )
        object.__setattr__(
            self,
            "outcomes",
            tuple(
                sorted(
                    outcomes,
                    key=lambda item: (
                        item.attempt.start_ns,
                        item.execution_end_ns,
                        item.attempt.attempt_id,
                    ),
                )
            ),
        )
        object.__setattr__(self, "as_of_ns", as_of)
        totals = (
            self.attempted_work,
            self.committed_work,
            self.lost_work,
            self.replayed_work,
            self.recomputed_work,
        )
        if any(not math.isfinite(value) for value in totals):
            raise ValueError("work ledger aggregate accounting must be finite")
        # Sum each outcome's already-validated conservation pair before the
        # ledger reduction.  Adding two independently rounded FLOP-scale
        # aggregates can manufacture a mismatch even when every attempt
        # conserves exactly.
        accounted_work = _work_sum(
            _work_sum((item.committed_work, item.lost_work))
            for item in self.outcomes
        )
        if not _same_work(self.attempted_work, accounted_work):
            raise ValueError(
                "ledger attempted work must equal final-valid committed plus lost work"
            )
        if Decimal(str(self.replayed_work)) > Decimal(str(self.attempted_work)):
            raise ValueError("replayed work must be a subset of attempted work")
        if Decimal(str(self.recomputed_work)) > Decimal(str(self.committed_work)):
            raise ValueError("recomputed work must be a subset of committed work")

    def logical_identities_for(
        self, outcome: WorkAttemptOutcome
    ) -> Tuple[LogicalWorkIdentity, ...]:
        if outcome.attempt.kind is WorkAttemptKind.FORWARD:
            assert outcome.attempt.logical_work is not None
            return (outcome.attempt.logical_work,)
        return tuple(
            binding.logical_work for binding in outcome.attempt.replay_bindings
        )

    @property
    def canonical_contributions(
        self,
    ) -> Mapping[Tuple[str, str, int], WorkAttemptOutcome]:
        result: dict[Tuple[str, str, int], WorkAttemptOutcome] = {}
        for outcome in self.canonical_outcomes:
            for identity in self.logical_identities_for(outcome):
                result[identity.coordinate] = outcome
        return MappingProxyType(result)

    @property
    def logical_work_amounts(self) -> Mapping[str, float]:
        amounts: dict[str, float] = {}
        for outcome in self.outcomes:
            if outcome.attempt.kind is not WorkAttemptKind.FORWARD:
                continue
            assert outcome.attempt.logical_work is not None
            amounts[outcome.attempt.logical_work.logical_work_id] = (
                outcome.attempt.planned_work
            )
        return MappingProxyType(amounts)

    @property
    def work_unit(self) -> Optional[str]:
        return None if not self.outcomes else self.outcomes[0].attempt.work_unit

    @property
    def attempted_work(self) -> float:
        return _work_sum(item.attempted_work for item in self.outcomes)

    @property
    def committed_work(self) -> float:
        return _work_sum(item.committed_work for item in self.outcomes)

    @property
    def lost_work(self) -> float:
        return _work_sum(item.lost_work for item in self.outcomes)

    @property
    def replayed_work(self) -> float:
        return _work_sum(item.replayed_work for item in self.outcomes)

    @property
    def recomputed_work(self) -> float:
        return _work_sum(item.recomputed_work for item in self.outcomes)

    @property
    def canonical_outcomes(self) -> Tuple[WorkAttemptOutcome, ...]:
        return tuple(
            item
            for item in self.outcomes
            if item.disposition is WorkOutcomeDisposition.VALID_COMMITTED
        )

    def invalidate_outcomes(
        self,
        outcome_ids: Iterable[str],
        *,
        recovery_id: str,
        effective_at_ns: int,
    ) -> "WorkLedger":
        if self.as_of_ns is not None:
            raise ValueError("an immutable as-of ledger snapshot cannot be mutated")
        ids = set(_ordered_texts(outcome_ids, "outcome_ids"))
        known = {item.attempt.attempt_id for item in self.outcomes}
        missing = sorted(ids - known)
        if missing:
            raise ValueError(f"cannot invalidate unknown outcomes: {missing}")
        updated = tuple(
            item.invalidate(
                recovery_id,
                effective_at_ns=effective_at_ns,
            )
            if item.attempt.attempt_id in ids
            else item
            for item in self.outcomes
        )
        return WorkLedger(updated)

    def commit_replay(self, outcome: WorkAttemptOutcome) -> "WorkLedger":
        """Atomically supersede invalidated targets and append a committed replay."""
        if self.as_of_ns is not None:
            raise ValueError("an immutable as-of ledger snapshot cannot be mutated")
        if (
            not isinstance(outcome, WorkAttemptOutcome)
            or outcome.attempt.kind is not WorkAttemptKind.REPLAY
            or outcome.disposition is not WorkOutcomeDisposition.VALID_COMMITTED
        ):
            raise ValueError("commit_replay requires a valid committed replay outcome")
        by_id = {item.attempt.attempt_id: item for item in self.outcomes}
        if outcome.attempt.attempt_id in by_id:
            raise ValueError("replay attempt ID already exists")
        missing = sorted(set(outcome.attempt.supersedes_attempt_ids) - set(by_id))
        if missing:
            raise ValueError(f"replay references unknown targets: {missing}")
        target_ids = set(outcome.attempt.supersedes_attempt_ids)
        updated = []
        for item in self.outcomes:
            if item.attempt.attempt_id not in target_ids:
                updated.append(item)
                continue
            if (
                item.disposition
                is not WorkOutcomeDisposition.INVALIDATED_AFTER_COMMIT
            ):
                raise ValueError(
                    "committed replay targets must already be invalidated"
                )
            updated.append(
                item.invalidate(
                    outcome.attempt.recovery_plan_id or "",
                    effective_at_ns=item.invalidation_effective_at_ns,
                    superseded_by_attempt_id=outcome.attempt.attempt_id,
                    supersession_effective_at_ns=outcome.execution_end_ns,
                )
            )
        return WorkLedger(tuple(updated) + (outcome,))

    def visible_at(self, decision_time_ns: int) -> Tuple[WorkAttemptOutcome, ...]:
        decision = _integer(decision_time_ns, "decision_time_ns")
        if self.as_of_ns is not None and decision > self.as_of_ns:
            raise ValueError("an as-of snapshot cannot be extrapolated into its future")
        return tuple(
            item.as_of(decision)
            for item in self.outcomes
            if item.execution_end_ns <= decision
        )

    def snapshot_at(self, decision_time_ns: int) -> "WorkLedger":
        decision = _integer(decision_time_ns, "decision_time_ns")
        return WorkLedger(self.visible_at(decision), as_of_ns=decision)

    def _payload(self) -> dict[str, object]:
        return {
            "accounting": {
                "attempted_work": self.attempted_work,
                "committed_work": self.committed_work,
                "lost_work": self.lost_work,
                "recomputed_work": self.recomputed_work,
                "replayed_work": self.replayed_work,
                "work_unit": self.work_unit,
            },
            "as_of_ns": self.as_of_ns,
            "outcomes": [item.to_dict() for item in self.outcomes],
        }

    @property
    def ledger_digest(self) -> str:
        payload = _json_dumps(self._payload(), None).encode("utf-8")
        return f"sha256:{hashlib.sha256(payload).hexdigest()}"

    def to_dict(self) -> dict[str, object]:
        payload = self._payload()
        payload["ledger_digest"] = self.ledger_digest
        return payload

    def to_json(self, *, indent: Optional[int] = None) -> str:
        return _json_dumps(self.to_dict(), indent)

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "WorkLedger":
        data = _mapping(data, "work ledger")
        ledger = cls(
            outcomes=tuple(
                WorkAttemptOutcome.from_dict(_mapping(item, "work-attempt outcome"))
                for item in _sequence(data.get("outcomes", ()), "outcomes")
            ),
            as_of_ns=data.get("as_of_ns"),
        )
        accounting = data.get("accounting")
        if accounting is not None:
            accounting = _mapping(accounting, "work accounting")
            expected = {
                "attempted_work": ledger.attempted_work,
                "committed_work": ledger.committed_work,
                "lost_work": ledger.lost_work,
                "recomputed_work": ledger.recomputed_work,
                "replayed_work": ledger.replayed_work,
                "work_unit": ledger.work_unit,
            }
            for key, value in expected.items():
                if key not in accounting or not _serialized_claim_matches(
                    accounting.get(key), value
                ):
                    raise ValueError(f"serialized work accounting {key} is inconsistent")
        if "ledger_digest" in data and not _serialized_claim_matches(
            data.get("ledger_digest"), ledger.ledger_digest
        ):
            raise ValueError("serialized work ledger digest is inconsistent")
        return ledger

    @classmethod
    def from_json(cls, payload: str) -> "WorkLedger":
        return cls.from_dict(_json_mapping(payload, "work ledger"))


@dataclass(frozen=True)
class StepSiteContributionRequirement:
    step: int
    site_ids: Tuple[str, ...]

    def __post_init__(self) -> None:
        sites = tuple(sorted(_ordered_texts(self.site_ids, "site_ids")))
        if not sites:
            raise ValueError("step contribution site_ids must not be empty")
        object.__setattr__(self, "step", _integer(self.step, "step", minimum=1))
        object.__setattr__(self, "site_ids", sites)

    def to_dict(self) -> dict[str, object]:
        return {"site_ids": list(self.site_ids), "step": self.step}

    def to_json(self, *, indent: Optional[int] = None) -> str:
        return _json_dumps(self.to_dict(), indent)

    @classmethod
    def from_dict(
        cls, data: Mapping[str, object]
    ) -> "StepSiteContributionRequirement":
        data = _mapping(data, "step site contribution requirement")
        return cls(
            step=data.get("step"),
            site_ids=tuple(
                _sequence(data.get("site_ids", ()), "site_ids")
            ),
        )

    @classmethod
    def from_json(
        cls, payload: str
    ) -> "StepSiteContributionRequirement":
        return cls.from_dict(
            _json_mapping(payload, "step site contribution requirement")
        )


@dataclass(frozen=True)
class RecoveryRequest:
    """Policy-visible inputs frozen at one recovery decision timestamp."""

    recovery_id: str
    lineage_id: str
    decision_time_ns: int
    failure: FailureObservation
    target_site_id: str
    last_committed_step: int
    restore_bandwidth_bytes_per_second: float
    replay_work_per_second: float
    fixed_restart_latency_ns: int
    unavailable_site_ids: Tuple[str, ...]
    evidence: EvidenceBoundary
    failure_observations: Tuple[FailureObservation, ...] = ()
    available_resource_ids: Tuple[str, ...] = ()
    required_restore_resource_ids: Tuple[str, ...] = ()
    step_site_requirements: Tuple[StepSiteContributionRequirement, ...] = ()
    evidence_gaps: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.failure, FailureObservation):
            raise TypeError("failure must be a FailureObservation")
        if not isinstance(self.evidence, EvidenceBoundary):
            raise TypeError("recovery evidence must be an EvidenceBoundary")
        decision = _integer(self.decision_time_ns, "decision_time_ns")
        last_committed_step = _integer(
            self.last_committed_step, "last_committed_step"
        )
        if self.failure.observed_at_ns != decision:
            raise ValueError(
                "failure observation must be stamped at decision_time_ns"
            )
        observations = tuple(self.failure_observations) or (self.failure,)
        if any(
            not isinstance(item, FailureObservation) for item in observations
        ):
            raise TypeError(
                "failure_observations must contain FailureObservation values"
            )
        observation_ids = [item.failure_id for item in observations]
        if len(observation_ids) != len(set(observation_ids)):
            raise ValueError("failure_observations IDs must be unique")
        if any(item.observed_at_ns != decision for item in observations):
            raise ValueError(
                "all failure observations must be stamped at decision_time_ns"
            )
        matched = tuple(
            item for item in observations if item.failure_id == self.failure.failure_id
        )
        if matched != (self.failure,):
            raise ValueError(
                "primary failure must appear exactly once in failure_observations"
            )
        unavailable = tuple(
            sorted(_ordered_texts(self.unavailable_site_ids, "unavailable_site_ids"))
        )
        observed_unavailable = tuple(
            sorted(
                {
                    item.site_id
                    for item in observations
                    if item.status is FailureStatus.ACTIVE
                }
            )
        )
        if unavailable != observed_unavailable:
            raise ValueError(
                "unavailable_site_ids must equal observable active failures"
            )
        available_resources = tuple(
            sorted(
                _ordered_texts(
                    self.available_resource_ids, "available_resource_ids"
                )
            )
        )
        required_resources = tuple(
            sorted(
                _ordered_texts(
                    self.required_restore_resource_ids,
                    "required_restore_resource_ids",
                )
            )
        )
        if not required_resources:
            raise ValueError("required_restore_resource_ids must not be empty")
        requirements = tuple(self.step_site_requirements)
        if any(
            not isinstance(item, StepSiteContributionRequirement)
            for item in requirements
        ):
            raise TypeError(
                "step_site_requirements must contain "
                "StepSiteContributionRequirement values"
            )
        requirement_steps = [item.step for item in requirements]
        if len(requirement_steps) != len(set(requirement_steps)):
            raise ValueError("step_site_requirements steps must be unique")
        if any(item.step > last_committed_step for item in requirements):
            raise ValueError(
                "step_site_requirements cannot exceed last_committed_step"
            )
        requirements = tuple(sorted(requirements, key=lambda item: item.step))
        object.__setattr__(self, "recovery_id", _text(self.recovery_id, "recovery_id"))
        object.__setattr__(self, "lineage_id", _text(self.lineage_id, "lineage_id"))
        object.__setattr__(self, "decision_time_ns", decision)
        object.__setattr__(
            self, "target_site_id", _text(self.target_site_id, "target_site_id")
        )
        object.__setattr__(
            self,
            "last_committed_step",
            last_committed_step,
        )
        object.__setattr__(
            self,
            "restore_bandwidth_bytes_per_second",
            _positive(
                self.restore_bandwidth_bytes_per_second,
                "restore_bandwidth_bytes_per_second",
            ),
        )
        object.__setattr__(
            self,
            "replay_work_per_second",
            _positive(self.replay_work_per_second, "replay_work_per_second"),
        )
        object.__setattr__(
            self,
            "fixed_restart_latency_ns",
            _integer(self.fixed_restart_latency_ns, "fixed_restart_latency_ns"),
        )
        object.__setattr__(self, "unavailable_site_ids", unavailable)
        object.__setattr__(self, "failure_observations", observations)
        object.__setattr__(self, "available_resource_ids", available_resources)
        object.__setattr__(
            self, "required_restore_resource_ids", required_resources
        )
        object.__setattr__(self, "step_site_requirements", requirements)
        object.__setattr__(
            self,
            "evidence_gaps",
            _ordered_texts(self.evidence_gaps, "evidence_gaps"),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "decision_time_ns": self.decision_time_ns,
            "evidence": self.evidence.to_dict(),
            "evidence_gaps": list(self.evidence_gaps),
            "failure": self.failure.to_dict(),
            "failure_observations": [
                item.to_dict() for item in self.failure_observations
            ],
            "fixed_restart_latency_ns": self.fixed_restart_latency_ns,
            "last_committed_step": self.last_committed_step,
            "lineage_id": self.lineage_id,
            "recovery_id": self.recovery_id,
            "replay_work_per_second": self.replay_work_per_second,
            "restore_bandwidth_bytes_per_second": (
                self.restore_bandwidth_bytes_per_second
            ),
            "target_site_id": self.target_site_id,
            "unavailable_site_ids": list(self.unavailable_site_ids),
            "available_resource_ids": list(self.available_resource_ids),
            "required_restore_resource_ids": list(
                self.required_restore_resource_ids
            ),
            "step_site_requirements": [
                item.to_dict() for item in self.step_site_requirements
            ],
        }

    def to_json(self, *, indent: Optional[int] = None) -> str:
        return _json_dumps(self.to_dict(), indent)

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "RecoveryRequest":
        data = _mapping(data, "recovery request")
        return cls(
            recovery_id=data.get("recovery_id"),
            lineage_id=data.get("lineage_id"),
            decision_time_ns=data.get("decision_time_ns"),
            failure=FailureObservation.from_dict(
                _mapping(data.get("failure"), "failure observation")
            ),
            target_site_id=data.get("target_site_id"),
            last_committed_step=data.get("last_committed_step"),
            restore_bandwidth_bytes_per_second=data.get(
                "restore_bandwidth_bytes_per_second"
            ),
            replay_work_per_second=data.get("replay_work_per_second"),
            fixed_restart_latency_ns=data.get("fixed_restart_latency_ns"),
            unavailable_site_ids=tuple(
                _sequence(
                    data.get("unavailable_site_ids", ()),
                    "unavailable_site_ids",
                )
            ),
            evidence=EvidenceBoundary.from_dict(
                _mapping(data.get("evidence"), "recovery evidence")
            ),
            failure_observations=tuple(
                FailureObservation.from_dict(
                    _mapping(item, "failure observation")
                )
                for item in _sequence(
                    data.get("failure_observations", ()),
                    "failure_observations",
                )
            ),
            available_resource_ids=tuple(
                _sequence(
                    data.get("available_resource_ids", ()),
                    "available_resource_ids",
                )
            ),
            required_restore_resource_ids=tuple(
                _sequence(
                    data.get("required_restore_resource_ids", ()),
                    "required_restore_resource_ids",
                )
            ),
            step_site_requirements=tuple(
                StepSiteContributionRequirement.from_dict(
                    _mapping(item, "step site contribution requirement")
                )
                for item in _sequence(
                    data.get("step_site_requirements", ()),
                    "step_site_requirements",
                )
            ),
            evidence_gaps=tuple(
                _sequence(data.get("evidence_gaps", ()), "evidence_gaps")
            ),
        )

    @classmethod
    def from_json(cls, payload: str) -> "RecoveryRequest":
        return cls.from_dict(_json_mapping(payload, "recovery request"))


def _recovery_snapshot_accounting(
    request: RecoveryRequest,
    checkpoint: CompletedCheckpoint,
    snapshot: WorkLedger,
) -> Tuple[
    Tuple[WorkAttemptOutcome, ...],
    Tuple[WorkAttemptOutcome, ...],
    float,
    float,
]:
    if snapshot.as_of_ns != request.decision_time_ns:
        raise RecoveryPlanningError(
            "recovery work snapshot must be frozen at decision_time_ns"
        )
    required_steps = tuple(
        range(checkpoint.step + 1, request.last_committed_step + 1)
    )
    requirements_by_step = {
        item.step: item.site_ids for item in request.step_site_requirements
    }
    unexpected = sorted(set(requirements_by_step) - set(required_steps))
    if unexpected:
        raise RecoveryPlanningError(
            "step contribution requirements fall outside rollback frontier: "
            f"{unexpected}"
        )
    narrowed = sorted(
        step
        for step, site_ids in requirements_by_step.items()
        if tuple(site_ids) != checkpoint.site_membership
    )
    if narrowed:
        raise RecoveryPlanningError(
            "step contribution requirements cannot change checkpoint membership "
            f"without a membership transition contract: {narrowed}"
        )

    supporting_by_id: dict[str, WorkAttemptOutcome] = {}
    required_logical_work_ids: set[str] = set()
    missing: list[str] = []
    ambiguous: list[str] = []
    for step in required_steps:
        for site_id in checkpoint.site_membership:
            matches = tuple(
                (identity, outcome)
                for outcome in snapshot.canonical_outcomes
                for identity in snapshot.logical_identities_for(outcome)
                if identity.lineage_id == request.lineage_id
                and identity.original_site_id == site_id
                and identity.logical_step == step
            )
            label = f"step={step},site={site_id}"
            if not matches:
                missing.append(label)
            elif len(matches) > 1:
                ambiguous.append(label)
            else:
                outcome = matches[0][1]
                supporting_by_id[outcome.attempt.attempt_id] = outcome
                required_logical_work_ids.add(matches[0][0].logical_work_id)
    if missing or ambiguous:
        raise RecoveryPlanningError(
            "canonical rollback contributions are incomplete or ambiguous; "
            f"missing={missing}, ambiguous={ambiguous}"
        )
    supporting = tuple(
        supporting_by_id[key] for key in sorted(supporting_by_id)
    )
    amounts = snapshot.logical_work_amounts
    missing_amounts = sorted(required_logical_work_ids - set(amounts))
    if missing_amounts:
        raise RecoveryPlanningError(
            "canonical rollback work lacks original logical amounts: "
            f"{missing_amounts}"
        )
    rollback_work = _work_sum(
        amounts[logical_id] for logical_id in sorted(required_logical_work_ids)
    )

    lost = tuple(
        outcome
        for outcome in snapshot.outcomes
        if outcome.attempt.lineage_id == request.lineage_id
        and outcome.interruption_failure_id == request.failure.failure_id
        and any(
            identity.logical_step > checkpoint.step
            for identity in snapshot.logical_identities_for(outcome)
        )
    )
    lost = tuple(sorted(lost, key=lambda item: item.attempt.attempt_id))
    lost_work = _work_sum(item.lost_work for item in lost)
    return supporting, lost, rollback_work, lost_work


class RecoveryPlanningError(RuntimeError):
    """Raised when visible evidence cannot support a recovery plan."""


@dataclass(frozen=True)
class RecoveryPlan:
    """Checkpoint restore and replay work implied by one visible decision state."""

    request: RecoveryRequest
    checkpoint: CompletedCheckpoint
    work_snapshot: WorkLedger
    work_ledger_digest: str
    rollback_steps: int
    resume_step: int
    rollback_committed_work: float
    pre_recovery_lost_work: float
    supporting_outcome_ids: Tuple[str, ...]
    lost_outcome_ids: Tuple[str, ...]
    transfer_latency_ns: int
    replay_latency_ns: int
    recovery_latency_ns: int
    blocking_site_ids: Tuple[str, ...]
    blocking_resource_ids: Tuple[str, ...]
    scheduled_start_ns: Optional[int]
    scheduled_completion_ns: Optional[int]

    def __post_init__(self) -> None:
        if not isinstance(self.request, RecoveryRequest):
            raise TypeError("request must be a RecoveryRequest")
        if not isinstance(self.checkpoint, CompletedCheckpoint):
            raise TypeError("checkpoint must be a CompletedCheckpoint")
        if not isinstance(self.work_snapshot, WorkLedger):
            raise TypeError("work_snapshot must be a WorkLedger")
        ledger_digest = _sha256(
            self.work_ledger_digest, "work_ledger_digest"
        )
        if ledger_digest != self.work_snapshot.ledger_digest:
            raise ValueError("work_ledger_digest does not match immutable snapshot")
        if self.checkpoint.lineage_id != self.request.lineage_id:
            raise ValueError("checkpoint lineage does not match recovery request")
        if self.checkpoint.completed_at_ns > self.request.failure.failure_start_ns:
            raise ValueError("recovery plan cannot use a post-failure checkpoint")
        expected_rollback = self.request.last_committed_step - self.checkpoint.step
        if expected_rollback < 0:
            raise ValueError("checkpoint step exceeds last committed step")
        rollback = _integer(self.rollback_steps, "rollback_steps")
        if rollback != expected_rollback:
            raise ValueError("rollback_steps is inconsistent with checkpoint frontier")
        resume_step = _integer(self.resume_step, "resume_step", minimum=1)
        if resume_step != self.request.last_committed_step + 1:
            raise ValueError("resume_step must follow the last committed step")
        rollback_work = _finite(
            self.rollback_committed_work, "rollback_committed_work"
        )
        lost_work = _finite(self.pre_recovery_lost_work, "pre_recovery_lost_work")
        supporting = _ordered_texts(
            self.supporting_outcome_ids, "supporting_outcome_ids"
        )
        lost_ids = _ordered_texts(self.lost_outcome_ids, "lost_outcome_ids")
        overlap = sorted(set(supporting) & set(lost_ids))
        if overlap:
            raise ValueError(
                f"supporting and lost outcome IDs overlap: {overlap}"
            )
        (
            expected_supporting,
            expected_lost,
            expected_rollback_work,
            expected_lost_work,
        ) = _recovery_snapshot_accounting(
            self.request, self.checkpoint, self.work_snapshot
        )
        expected_supporting_ids = tuple(
            item.attempt.attempt_id for item in expected_supporting
        )
        expected_lost_ids = tuple(item.attempt.attempt_id for item in expected_lost)
        if supporting != expected_supporting_ids:
            raise ValueError(
                "supporting_outcome_ids do not match canonical as-of snapshot"
            )
        if lost_ids != expected_lost_ids:
            raise ValueError("lost_outcome_ids do not match as-of snapshot")
        if not _same_work(rollback_work, expected_rollback_work):
            raise ValueError(
                "rollback_committed_work does not match supporting outcomes"
            )
        if not _same_work(lost_work, expected_lost_work):
            raise ValueError(
                "pre_recovery_lost_work does not match lost outcomes"
            )
        if rollback > 0 and not supporting:
            raise ValueError("rollback work requires supporting committed outcomes")
        if rollback == 0 and (rollback_work != 0.0 or supporting):
            raise ValueError("zero rollback steps require zero rollback work")
        transfer = _integer(self.transfer_latency_ns, "transfer_latency_ns")
        expected_transfer = _ceil_duration_ns(
            float(self.checkpoint.state_bytes),
            self.request.restore_bandwidth_bytes_per_second,
        )
        if transfer != expected_transfer:
            raise ValueError("transfer_latency_ns is inconsistent with state bytes")
        replay = _integer(self.replay_latency_ns, "replay_latency_ns")
        expected_replay = _ceil_duration_ns(
            rollback_work, self.request.replay_work_per_second
        )
        if replay != expected_replay:
            raise ValueError("replay_latency_ns is inconsistent with rollback work")
        recovery = _integer(self.recovery_latency_ns, "recovery_latency_ns")
        expected_recovery = (
            transfer + replay + self.request.fixed_restart_latency_ns
        )
        if recovery != expected_recovery:
            raise ValueError("recovery_latency_ns is inconsistent with components")
        blocking = tuple(
            sorted(_ordered_texts(self.blocking_site_ids, "blocking_site_ids"))
        )
        expected_blocking = tuple(
            sorted(
                (
                    set(self.checkpoint.shard_source_site_ids)
                    | {self.request.target_site_id}
                )
                & set(self.request.unavailable_site_ids)
            )
        )
        if blocking != expected_blocking:
            raise ValueError("blocking_site_ids is inconsistent with visible state")
        blocking_resources = tuple(
            sorted(
                _ordered_texts(
                    self.blocking_resource_ids, "blocking_resource_ids"
                )
            )
        )
        expected_blocking_resources = tuple(
            sorted(
                (
                    set(self.request.required_restore_resource_ids)
                    | set(
                        self.checkpoint.restore_resource_ids(
                            self.request.target_site_id
                        )
                    )
                )
                - set(self.request.available_resource_ids)
            )
        )
        if blocking_resources != expected_blocking_resources:
            raise ValueError(
                "blocking_resource_ids is inconsistent with visible resources"
            )
        start = self.scheduled_start_ns
        completion = self.scheduled_completion_ns
        if blocking or blocking_resources:
            if start is not None or completion is not None:
                raise ValueError(
                    "a blocked plan must not invent a future availability timestamp"
                )
        else:
            start = _integer(start, "scheduled_start_ns")
            completion = _integer(completion, "scheduled_completion_ns")
            if start != self.request.decision_time_ns:
                raise ValueError("an unblocked plan starts at decision_time_ns")
            if completion != start + recovery:
                raise ValueError(
                    "scheduled_completion_ns must equal start plus recovery latency"
                )
        object.__setattr__(self, "rollback_steps", rollback)
        object.__setattr__(self, "resume_step", resume_step)
        object.__setattr__(self, "rollback_committed_work", rollback_work)
        object.__setattr__(self, "pre_recovery_lost_work", lost_work)
        object.__setattr__(self, "supporting_outcome_ids", supporting)
        object.__setattr__(self, "lost_outcome_ids", lost_ids)
        object.__setattr__(self, "transfer_latency_ns", transfer)
        object.__setattr__(self, "replay_latency_ns", replay)
        object.__setattr__(self, "recovery_latency_ns", recovery)
        object.__setattr__(self, "blocking_site_ids", blocking)
        object.__setattr__(
            self, "blocking_resource_ids", blocking_resources
        )
        object.__setattr__(self, "scheduled_start_ns", start)
        object.__setattr__(self, "scheduled_completion_ns", completion)
        object.__setattr__(self, "work_ledger_digest", ledger_digest)

    @property
    def recovery_id(self) -> str:
        return self.request.recovery_id

    @property
    def source_site_id(self) -> str:
        return self.checkpoint.source_site_id

    @property
    def target_site_id(self) -> str:
        return self.request.target_site_id

    @property
    def recovery_bytes(self) -> int:
        return self.checkpoint.state_bytes

    @property
    def replay_required_work(self) -> float:
        return self.rollback_committed_work

    @property
    def can_start(self) -> bool:
        return not self.blocking_site_ids and not self.blocking_resource_ids

    @property
    def evidence_boundary_ids(self) -> Tuple[str, ...]:
        by_id = {
            item.attempt.attempt_id: item for item in self.work_snapshot.outcomes
        }
        outcome_boundaries = tuple(
            sorted(
                {
                    by_id[attempt_id].attempt.evidence.boundary_id
                    for attempt_id in (
                        self.supporting_outcome_ids + self.lost_outcome_ids
                    )
                }
            )
        )
        return (
            self.request.failure.evidence.boundary_id,
            self.checkpoint.evidence.boundary_id,
            self.request.evidence.boundary_id,
        ) + outcome_boundaries

    @property
    def outcome_evidence_refs(self) -> Tuple[str, ...]:
        by_id = {
            item.attempt.attempt_id: item for item in self.work_snapshot.outcomes
        }
        return tuple(
            f"{attempt_id}:{by_id[attempt_id].attempt.evidence.boundary_id}"
            for attempt_id in self.supporting_outcome_ids + self.lost_outcome_ids
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "blocking_site_ids": list(self.blocking_site_ids),
            "blocking_resource_ids": list(self.blocking_resource_ids),
            "can_start": self.can_start,
            "checkpoint": self.checkpoint.to_dict(),
            "evidence_boundary_ids": list(self.evidence_boundary_ids),
            "fixed_restart_latency_ns": self.request.fixed_restart_latency_ns,
            "lost_outcome_ids": list(self.lost_outcome_ids),
            "outcome_evidence_refs": list(self.outcome_evidence_refs),
            "policy_information_cutoff_ns": self.request.decision_time_ns,
            "pre_recovery_lost_work": self.pre_recovery_lost_work,
            "recovery_bytes": self.recovery_bytes,
            "recovery_id": self.recovery_id,
            "recovery_latency_ns": self.recovery_latency_ns,
            "replay_latency_ns": self.replay_latency_ns,
            "replay_required_work": self.replay_required_work,
            "request": self.request.to_dict(),
            "resume_step": self.resume_step,
            "rollback_committed_work": self.rollback_committed_work,
            "rollback_steps": self.rollback_steps,
            "scheduled_completion_ns": self.scheduled_completion_ns,
            "scheduled_start_ns": self.scheduled_start_ns,
            "source_site_id": self.source_site_id,
            "supporting_outcome_ids": list(self.supporting_outcome_ids),
            "target_site_id": self.target_site_id,
            "transfer_latency_ns": self.transfer_latency_ns,
            "work_ledger_digest": self.work_ledger_digest,
            "work_snapshot": self.work_snapshot.to_dict(),
        }

    def to_json(self, *, indent: Optional[int] = None) -> str:
        return _json_dumps(self.to_dict(), indent)

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "RecoveryPlan":
        data = _mapping(data, "recovery plan")
        result = cls(
            request=RecoveryRequest.from_dict(
                _mapping(data.get("request"), "recovery request")
            ),
            checkpoint=CompletedCheckpoint.from_dict(
                _mapping(data.get("checkpoint"), "completed checkpoint")
            ),
            work_snapshot=WorkLedger.from_dict(
                _mapping(data.get("work_snapshot"), "work snapshot")
            ),
            work_ledger_digest=data.get("work_ledger_digest"),
            rollback_steps=data.get("rollback_steps"),
            resume_step=data.get("resume_step"),
            rollback_committed_work=data.get("rollback_committed_work"),
            pre_recovery_lost_work=data.get("pre_recovery_lost_work"),
            supporting_outcome_ids=tuple(
                _sequence(
                    data.get("supporting_outcome_ids", ()),
                    "supporting_outcome_ids",
                )
            ),
            lost_outcome_ids=tuple(
                _sequence(
                    data.get("lost_outcome_ids", ()), "lost_outcome_ids"
                )
            ),
            transfer_latency_ns=data.get("transfer_latency_ns"),
            replay_latency_ns=data.get("replay_latency_ns"),
            recovery_latency_ns=data.get("recovery_latency_ns"),
            blocking_site_ids=tuple(
                _sequence(
                    data.get("blocking_site_ids", ()), "blocking_site_ids"
                )
            ),
            blocking_resource_ids=tuple(
                _sequence(
                    data.get("blocking_resource_ids", ()),
                    "blocking_resource_ids",
                )
            ),
            scheduled_start_ns=data.get("scheduled_start_ns"),
            scheduled_completion_ns=data.get("scheduled_completion_ns"),
        )
        derived = {
            "can_start": result.can_start,
            "evidence_boundary_ids": list(result.evidence_boundary_ids),
            "fixed_restart_latency_ns": result.request.fixed_restart_latency_ns,
            "outcome_evidence_refs": list(result.outcome_evidence_refs),
            "policy_information_cutoff_ns": result.request.decision_time_ns,
            "recovery_bytes": result.recovery_bytes,
            "recovery_id": result.recovery_id,
            "replay_required_work": result.replay_required_work,
            "source_site_id": result.source_site_id,
            "target_site_id": result.target_site_id,
        }
        for name, expected in derived.items():
            if name in data and not _serialized_claim_matches(data[name], expected):
                raise ValueError(f"serialized recovery plan {name} is inconsistent")
        return result

    @classmethod
    def from_json(cls, payload: str) -> "RecoveryPlan":
        return cls.from_dict(_json_mapping(payload, "recovery plan"))


def plan_recovery(
    request: RecoveryRequest,
    checkpoints: CheckpointLedger,
    work: WorkLedger,
) -> RecoveryPlan:
    """Plan from the latest checkpoint and outcomes visible at the cutoff.

    The function receives a policy-safe failure observation, not the complete
    failure interval.  If the checkpoint source or target is currently
    unavailable, the result is blocked and deliberately omits a guessed future
    start or completion timestamp.
    """
    if not isinstance(request, RecoveryRequest):
        raise TypeError("request must be a RecoveryRequest")
    if not isinstance(checkpoints, CheckpointLedger):
        raise TypeError("checkpoints must be a CheckpointLedger")
    if not isinstance(work, WorkLedger):
        raise TypeError("work must be a WorkLedger")
    checkpoint = checkpoints.latest_at(
        request.failure.failure_start_ns,
        lineage_id=request.lineage_id,
    )
    if checkpoint is None:
        raise RecoveryPlanningError(
            "no completed checkpoint is visible for the recovery lineage"
        )
    if checkpoint.step > request.last_committed_step:
        raise RecoveryPlanningError(
            "latest visible checkpoint is ahead of the committed frontier"
        )

    snapshot = work.snapshot_at(request.decision_time_ns)
    supporting, lost, rollback_work, lost_work = _recovery_snapshot_accounting(
        request, checkpoint, snapshot
    )
    transfer_latency = _ceil_duration_ns(
        float(checkpoint.state_bytes),
        request.restore_bandwidth_bytes_per_second,
    )
    replay_latency = _ceil_duration_ns(
        rollback_work,
        request.replay_work_per_second,
    )
    recovery_latency = (
        transfer_latency
        + replay_latency
        + request.fixed_restart_latency_ns
    )
    blocking = tuple(
        sorted(
            (set(checkpoint.shard_source_site_ids) | {request.target_site_id})
            & set(request.unavailable_site_ids)
        )
    )
    blocking_resources = tuple(
        sorted(
            (
                set(request.required_restore_resource_ids)
                | set(checkpoint.restore_resource_ids(request.target_site_id))
            )
            - set(request.available_resource_ids)
        )
    )
    start = (
        None
        if blocking or blocking_resources
        else request.decision_time_ns
    )
    completion = None if start is None else start + recovery_latency
    return RecoveryPlan(
        request=request,
        checkpoint=checkpoint,
        work_snapshot=snapshot,
        work_ledger_digest=snapshot.ledger_digest,
        rollback_steps=request.last_committed_step - checkpoint.step,
        resume_step=request.last_committed_step + 1,
        rollback_committed_work=rollback_work,
        pre_recovery_lost_work=lost_work,
        supporting_outcome_ids=tuple(
            sorted(outcome.attempt.attempt_id for outcome in supporting)
        ),
        lost_outcome_ids=tuple(
            sorted(outcome.attempt.attempt_id for outcome in lost)
        ),
        transfer_latency_ns=transfer_latency,
        replay_latency_ns=replay_latency,
        recovery_latency_ns=recovery_latency,
        blocking_site_ids=blocking,
        blocking_resource_ids=blocking_resources,
        scheduled_start_ns=start,
        scheduled_completion_ns=completion,
    )


__all__ = [
    "CheckpointLedger",
    "CompletedCheckpoint",
    "EvidenceBasis",
    "EvidenceBoundary",
    "FailureCauseCode",
    "FailureInterval",
    "FailureObservation",
    "FailureStatus",
    "FailureTrace",
    "LogicalWorkIdentity",
    "ReplayLineageBinding",
    "RecoveryPlan",
    "RecoveryPlanningError",
    "RecoveryRequest",
    "SiteWorkAttempt",
    "StepSiteContributionRequirement",
    "WorkAttemptKind",
    "WorkAttemptOutcome",
    "WorkOutcomeDisposition",
    "WorkLedger",
    "evaluate_work_attempt",
    "plan_recovery",
]
