"""Deterministic transition runtime for fail-stop recovery semantics.

The runtime advances one decision boundary at a time.  Its private transition
queue contains the complete exogenous failure trace, while public snapshots
contain only failure transitions already processed.  Events use half-open
intervals.  At one timestamp, operation, checkpoint, restore, and
reconfiguration completions are processed before failure observations, so
work and control transitions ending exactly when a failure starts are durable.
The whole timestamp is emitted as one immutable decision batch.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Iterable, Mapping, Optional, Sequence, Tuple

from .recovery import (
    CheckpointLedger,
    CompletedCheckpoint,
    EvidenceBoundary,
    FailureInterval,
    FailureObservation,
    FailureStatus,
    FailureTrace,
    ReplayLineageBinding,
    RecoveryPlan,
    SiteWorkAttempt,
    WorkAttemptKind,
    WorkAttemptOutcome,
    WorkLedger,
    evaluate_work_attempt,
)


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-blank string")
    return value.strip()


def _integer(value: object, field_name: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer")
    if value < minimum:
        raise ValueError(f"{field_name} must be >= {minimum}")
    return value


def _sha256(value: object, field_name: str) -> str:
    value = _text(value, field_name)
    digest = value.removeprefix("sha256:")
    if (
        not value.startswith("sha256:")
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        raise ValueError(
            f"{field_name} must be 'sha256:' followed by 64 lowercase hex digits"
        )
    return value


def _ordered_ids(
    values: object,
    field_name: str,
    *,
    nonempty: bool = False,
) -> Tuple[str, ...]:
    if isinstance(values, (str, bytes, bytearray)) or not isinstance(
        values, Iterable
    ):
        raise TypeError(f"{field_name} must be an ordered iterable")
    if isinstance(values, (set, frozenset)):
        raise TypeError(f"{field_name} must be ordered, not a set")
    result = tuple(_text(item, field_name) for item in values)
    if nonempty and not result:
        raise ValueError(f"{field_name} must not be empty")
    if len(result) != len(set(result)):
        raise ValueError(f"{field_name} must not contain duplicates")
    return result


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
        if any(not isinstance(key, str) or not key for key in value):
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


def _freeze_mapping(value: object, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    frozen = _freeze_json(value, field_name)
    assert isinstance(frozen, Mapping)
    return frozen


def _thaw(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _thaw(value[key]) for key in sorted(value)}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
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


class DecisionBoundary(str, Enum):
    INITIAL = "initial"
    OPERATION_COMPLETION = "operation_completion"
    CHECKPOINT_COMMIT = "checkpoint_commit"
    FAILURE_OBSERVED = "failure_observed"
    PHYSICAL_RECOVERY = "physical_recovery"
    RESTORE_COMPLETION = "restore_completion"
    RECONFIGURATION_COMPLETION = "reconfiguration_completion"


class SiteState(str, Enum):
    HEALTHY_READY = "healthy_ready"
    FAILED = "failed"
    RECOVERED_UNRESTORED = "recovered_unrestored"
    RESTORING = "restoring"


_BOUNDARY_PRIORITY = {
    DecisionBoundary.OPERATION_COMPLETION: 10,
    DecisionBoundary.CHECKPOINT_COMMIT: 20,
    DecisionBoundary.RESTORE_COMPLETION: 30,
    DecisionBoundary.RECONFIGURATION_COMPLETION: 40,
    DecisionBoundary.FAILURE_OBSERVED: 50,
    DecisionBoundary.PHYSICAL_RECOVERY: 60,
}


@dataclass(frozen=True)
class DecisionBatchMember:
    boundary: DecisionBoundary
    boundary_id: str
    object_id: str
    site_id: Optional[str] = None

    def __post_init__(self) -> None:
        boundary = self.boundary
        if not isinstance(boundary, DecisionBoundary):
            try:
                boundary = DecisionBoundary(boundary)
            except (TypeError, ValueError) as exc:
                raise ValueError("boundary must be a valid DecisionBoundary") from exc
        object.__setattr__(self, "boundary", boundary)
        object.__setattr__(self, "boundary_id", _text(self.boundary_id, "boundary_id"))
        object.__setattr__(self, "object_id", _text(self.object_id, "object_id"))
        if self.site_id is not None:
            object.__setattr__(self, "site_id", _text(self.site_id, "site_id"))

    def to_dict(self) -> dict[str, object]:
        return {
            "boundary": self.boundary.value,
            "boundary_id": self.boundary_id,
            "object_id": self.object_id,
            "site_id": self.site_id,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "DecisionBatchMember":
        data = _mapping(data, "decision batch member")
        return cls(
            boundary=data.get("boundary"),
            boundary_id=data.get("boundary_id"),
            object_id=data.get("object_id"),
            site_id=data.get("site_id"),
        )


@dataclass(frozen=True)
class CheckpointShard:
    shard_id: str
    site_id: str
    source_state_version: str
    storage_location: str
    failure_domain: str
    state_bytes: int
    checksum: str
    write_started_at_ns: int
    write_completed_at_ns: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "shard_id", _text(self.shard_id, "shard_id"))
        object.__setattr__(self, "site_id", _text(self.site_id, "site_id"))
        object.__setattr__(
            self,
            "source_state_version",
            _text(self.source_state_version, "source_state_version"),
        )
        object.__setattr__(
            self,
            "storage_location",
            _text(self.storage_location, "storage_location"),
        )
        object.__setattr__(
            self,
            "failure_domain",
            _text(self.failure_domain, "failure_domain"),
        )
        object.__setattr__(
            self, "state_bytes", _integer(self.state_bytes, "state_bytes", minimum=1)
        )
        object.__setattr__(self, "checksum", _sha256(self.checksum, "checksum"))
        write_started = _integer(self.write_started_at_ns, "write_started_at_ns")
        write_completed = _integer(
            self.write_completed_at_ns,
            "write_completed_at_ns",
        )
        if write_completed < write_started:
            raise ValueError("shard write completion precedes write start")
        object.__setattr__(self, "write_started_at_ns", write_started)
        object.__setattr__(self, "write_completed_at_ns", write_completed)

    def to_dict(self) -> dict[str, object]:
        return {
            "checksum": self.checksum,
            "failure_domain": self.failure_domain,
            "shard_id": self.shard_id,
            "site_id": self.site_id,
            "source_state_version": self.source_state_version,
            "state_bytes": self.state_bytes,
            "storage_location": self.storage_location,
            "write_completed_at_ns": self.write_completed_at_ns,
            "write_started_at_ns": self.write_started_at_ns,
        }

    def to_json(self, *, indent: Optional[int] = None) -> str:
        return _json_dumps(self.to_dict(), indent)

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "CheckpointShard":
        data = _mapping(data, "checkpoint shard")
        return cls(
            shard_id=data.get("shard_id"),
            site_id=data.get("site_id"),
            source_state_version=data.get("source_state_version"),
            storage_location=data.get("storage_location"),
            failure_domain=data.get("failure_domain"),
            state_bytes=data.get("state_bytes"),
            checksum=data.get("checksum"),
            write_started_at_ns=data.get("write_started_at_ns"),
            write_completed_at_ns=data.get("write_completed_at_ns"),
        )

    @classmethod
    def from_json(cls, payload: str) -> "CheckpointShard":
        return cls.from_dict(_json_mapping(payload, "checkpoint shard"))


@dataclass(frozen=True)
class CheckpointManifest:
    """Structurally complete logical shard manifest, invisible until commit."""

    checkpoint_id: str
    lineage_id: str
    committed_step: int
    state_version: str
    model_hash: str
    optimizer_hash: str
    rng_hash: str
    data_cursor_hash: str
    state_bytes: int
    required_shard_ids: Tuple[str, ...]
    shards: Tuple[CheckpointShard, ...]
    site_membership: Tuple[str, ...]
    recovery_source_site_id: str
    checkpoint_write_started_at_ns: int
    checkpoint_write_completed_at_ns: int
    manifest_committed_at_ns: int
    evidence: EvidenceBoundary
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.evidence, EvidenceBoundary):
            raise TypeError("manifest evidence must be an EvidenceBoundary")
        shards = tuple(self.shards)
        if not shards or any(not isinstance(item, CheckpointShard) for item in shards):
            raise TypeError("shards must contain at least one CheckpointShard")
        shard_ids = [item.shard_id for item in shards]
        if len(shard_ids) != len(set(shard_ids)):
            raise ValueError("checkpoint shard IDs must be unique")
        shards = tuple(sorted(shards, key=lambda item: item.shard_id))
        shard_ids = [item.shard_id for item in shards]
        required_shard_ids = tuple(
            sorted(
                _ordered_ids(
                    self.required_shard_ids,
                    "required_shard_ids",
                    nonempty=True,
                )
            )
        )
        if required_shard_ids != tuple(shard_ids):
            raise ValueError("required_shard_ids must exactly equal listed shard IDs")
        state_bytes = _integer(self.state_bytes, "state_bytes", minimum=1)
        if sum(item.state_bytes for item in shards) != state_bytes:
            raise ValueError("logical checkpoint shard bytes must sum exactly to state_bytes")
        membership = tuple(
            sorted(_ordered_ids(self.site_membership, "site_membership", nonempty=True))
        )
        source = _text(self.recovery_source_site_id, "recovery_source_site_id")
        if source not in {item.site_id for item in shards}:
            raise ValueError("recovery coordinator must be one of the shard sites")
        state_version = _text(self.state_version, "state_version")
        if any(item.source_state_version != state_version for item in shards):
            raise ValueError("every shard source_state_version must equal state_version")
        write_started = _integer(
            self.checkpoint_write_started_at_ns,
            "checkpoint_write_started_at_ns",
        )
        write_completed = _integer(
            self.checkpoint_write_completed_at_ns,
            "checkpoint_write_completed_at_ns",
        )
        manifest_committed = _integer(
            self.manifest_committed_at_ns,
            "manifest_committed_at_ns",
        )
        if not write_started <= write_completed <= manifest_committed:
            raise ValueError(
                "checkpoint timing must satisfy write start <= write completion "
                "<= manifest commit"
            )
        if any(
            item.write_started_at_ns < write_started
            or item.write_completed_at_ns > write_completed
            for item in shards
        ):
            raise ValueError("shard write interval lies outside checkpoint write interval")
        if write_started != min(item.write_started_at_ns for item in shards):
            raise ValueError("checkpoint write start must equal earliest shard write start")
        if write_completed != max(item.write_completed_at_ns for item in shards):
            raise ValueError(
                "checkpoint write completion must equal latest shard write completion"
            )
        object.__setattr__(
            self, "checkpoint_id", _text(self.checkpoint_id, "checkpoint_id")
        )
        object.__setattr__(self, "lineage_id", _text(self.lineage_id, "lineage_id"))
        object.__setattr__(
            self, "committed_step", _integer(self.committed_step, "committed_step")
        )
        object.__setattr__(self, "state_version", state_version)
        object.__setattr__(self, "model_hash", _sha256(self.model_hash, "model_hash"))
        object.__setattr__(
            self, "optimizer_hash", _sha256(self.optimizer_hash, "optimizer_hash")
        )
        object.__setattr__(self, "rng_hash", _sha256(self.rng_hash, "rng_hash"))
        object.__setattr__(
            self,
            "data_cursor_hash",
            _sha256(self.data_cursor_hash, "data_cursor_hash"),
        )
        object.__setattr__(self, "state_bytes", state_bytes)
        object.__setattr__(self, "required_shard_ids", required_shard_ids)
        object.__setattr__(self, "shards", shards)
        object.__setattr__(self, "site_membership", membership)
        object.__setattr__(self, "recovery_source_site_id", source)
        object.__setattr__(
            self, "checkpoint_write_started_at_ns", write_started
        )
        object.__setattr__(
            self, "checkpoint_write_completed_at_ns", write_completed
        )
        object.__setattr__(
            self, "manifest_committed_at_ns", manifest_committed
        )
        object.__setattr__(
            self, "metadata", _freeze_mapping(self.metadata, "manifest metadata")
        )

    @property
    def commit_at_ns(self) -> int:
        return self.manifest_committed_at_ns

    @property
    def is_genesis(self) -> bool:
        return self.committed_step == 0

    def as_completed_checkpoint(self) -> CompletedCheckpoint:
        return CompletedCheckpoint(
            checkpoint_id=self.checkpoint_id,
            lineage_id=self.lineage_id,
            step=self.committed_step,
            completed_at_ns=self.commit_at_ns,
            state_bytes=self.state_bytes,
            source_site_id=self.recovery_source_site_id,
            site_membership=self.site_membership,
            evidence=self.evidence,
            metadata={
                "state_version": self.state_version,
                "model_hash": self.model_hash,
                "optimizer_hash": self.optimizer_hash,
                "rng_hash": self.rng_hash,
                "data_cursor_hash": self.data_cursor_hash,
                "checkpoint_write_started_at_ns": self.checkpoint_write_started_at_ns,
                "checkpoint_write_completed_at_ns": self.checkpoint_write_completed_at_ns,
                "manifest_committed_at_ns": self.manifest_committed_at_ns,
                "required_shard_ids": list(self.required_shard_ids),
                "shards": [item.to_dict() for item in self.shards],
                "manifest_metadata": _thaw(self.metadata),
            },
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "checkpoint_write_completed_at_ns": self.checkpoint_write_completed_at_ns,
            "checkpoint_write_started_at_ns": self.checkpoint_write_started_at_ns,
            "committed_step": self.committed_step,
            "data_cursor_hash": self.data_cursor_hash,
            "evidence": self.evidence.to_dict(),
            "lineage_id": self.lineage_id,
            "manifest_committed_at_ns": self.manifest_committed_at_ns,
            "metadata": _thaw(self.metadata),
            "model_hash": self.model_hash,
            "optimizer_hash": self.optimizer_hash,
            "recovery_source_site_id": self.recovery_source_site_id,
            "required_shard_ids": list(self.required_shard_ids),
            "rng_hash": self.rng_hash,
            "shards": [item.to_dict() for item in self.shards],
            "site_membership": list(self.site_membership),
            "state_version": self.state_version,
            "state_bytes": self.state_bytes,
        }

    def to_json(self, *, indent: Optional[int] = None) -> str:
        return _json_dumps(self.to_dict(), indent)

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "CheckpointManifest":
        data = _mapping(data, "checkpoint manifest")
        result = cls(
            checkpoint_id=data.get("checkpoint_id"),
            lineage_id=data.get("lineage_id"),
            committed_step=data.get("committed_step"),
            state_version=data.get("state_version"),
            model_hash=data.get("model_hash"),
            optimizer_hash=data.get("optimizer_hash"),
            rng_hash=data.get("rng_hash"),
            data_cursor_hash=data.get("data_cursor_hash"),
            state_bytes=data.get("state_bytes"),
            required_shard_ids=tuple(data.get("required_shard_ids", ())),
            shards=tuple(
                CheckpointShard.from_dict(_mapping(item, "checkpoint shard"))
                for item in data.get("shards", ())
            ),
            site_membership=tuple(data.get("site_membership", ())),
            recovery_source_site_id=data.get("recovery_source_site_id"),
            checkpoint_write_started_at_ns=data.get(
                "checkpoint_write_started_at_ns"
            ),
            checkpoint_write_completed_at_ns=data.get(
                "checkpoint_write_completed_at_ns"
            ),
            manifest_committed_at_ns=data.get("manifest_committed_at_ns"),
            evidence=EvidenceBoundary.from_dict(
                _mapping(data.get("evidence"), "manifest evidence")
            ),
            metadata=_mapping(data.get("metadata", {}), "manifest metadata"),
        )
        return result

    @classmethod
    def from_json(cls, payload: str) -> "CheckpointManifest":
        return cls.from_dict(_json_mapping(payload, "checkpoint manifest"))


@dataclass(frozen=True)
class RestoreTransferOutcome:
    """Deterministic byte accounting for one shard in a restore attempt."""

    recovery_id: str
    checkpoint_id: str
    shard_id: str
    source_site_id: str
    target_site_id: str
    recovery_start_ns: int
    transfer_start_ns: int
    planned_end_ns: int
    execution_end_ns: int
    state_bytes: int
    interrupted: bool
    interruption_failure_id: Optional[str]
    attempted_bytes: int
    completed_bytes: int
    lost_bytes: int

    def __post_init__(self) -> None:
        recovery_start = _integer(self.recovery_start_ns, "recovery_start_ns")
        transfer_start = _integer(self.transfer_start_ns, "transfer_start_ns")
        planned_end = _integer(self.planned_end_ns, "planned_end_ns")
        execution_end = _integer(self.execution_end_ns, "execution_end_ns")
        state_bytes = _integer(self.state_bytes, "state_bytes", minimum=1)
        if not recovery_start <= transfer_start < planned_end:
            raise ValueError(
                "restore timing must satisfy recovery_start <= transfer_start "
                "< planned_end"
            )
        if not recovery_start <= execution_end <= planned_end:
            raise ValueError("restore execution_end_ns lies outside the attempt")
        if not isinstance(self.interrupted, bool):
            raise TypeError("interrupted must be bool")
        failure_id = self.interruption_failure_id
        if self.interrupted:
            if failure_id is None:
                raise ValueError("an interrupted restore requires a failure ID")
            failure_id = _text(failure_id, "interruption_failure_id")
            if execution_end >= planned_end:
                raise ValueError("an interrupted restore must end before planned_end_ns")
        else:
            if failure_id is not None:
                raise ValueError("a completed restore must not name a failure")
            if execution_end != planned_end:
                raise ValueError("a completed restore must end at planned_end_ns")
        attempted = _integer(self.attempted_bytes, "attempted_bytes")
        completed = _integer(self.completed_bytes, "completed_bytes")
        lost = _integer(self.lost_bytes, "lost_bytes")
        if attempted > state_bytes:
            raise ValueError("attempted_bytes cannot exceed shard state_bytes")
        if attempted != completed + lost:
            raise ValueError("attempted_bytes must equal completed_bytes plus lost_bytes")
        if self.interrupted:
            if completed != 0 or lost != attempted:
                raise ValueError("an interrupted restore loses all attempted bytes")
        elif completed != state_bytes or lost != 0:
            raise ValueError("a completed restore commits every state byte")
        object.__setattr__(self, "recovery_id", _text(self.recovery_id, "recovery_id"))
        object.__setattr__(
            self, "checkpoint_id", _text(self.checkpoint_id, "checkpoint_id")
        )
        object.__setattr__(self, "shard_id", _text(self.shard_id, "shard_id"))
        object.__setattr__(
            self, "source_site_id", _text(self.source_site_id, "source_site_id")
        )
        object.__setattr__(
            self, "target_site_id", _text(self.target_site_id, "target_site_id")
        )
        object.__setattr__(self, "recovery_start_ns", recovery_start)
        object.__setattr__(self, "transfer_start_ns", transfer_start)
        object.__setattr__(self, "planned_end_ns", planned_end)
        object.__setattr__(self, "execution_end_ns", execution_end)
        object.__setattr__(self, "state_bytes", state_bytes)
        object.__setattr__(self, "interruption_failure_id", failure_id)
        object.__setattr__(self, "attempted_bytes", attempted)
        object.__setattr__(self, "completed_bytes", completed)
        object.__setattr__(self, "lost_bytes", lost)

    @property
    def fixed_restart_latency_ns(self) -> int:
        return self.transfer_start_ns - self.recovery_start_ns

    @property
    def transfer_latency_ns(self) -> int:
        return self.planned_end_ns - self.transfer_start_ns

    @property
    def inter_site(self) -> bool:
        return self.source_site_id != self.target_site_id

    def to_dict(self) -> dict[str, object]:
        return {
            "attempted_bytes": self.attempted_bytes,
            "checkpoint_id": self.checkpoint_id,
            "completed_bytes": self.completed_bytes,
            "execution_end_ns": self.execution_end_ns,
            "fixed_restart_latency_ns": self.fixed_restart_latency_ns,
            "inter_site": self.inter_site,
            "interrupted": self.interrupted,
            "interruption_failure_id": self.interruption_failure_id,
            "lost_bytes": self.lost_bytes,
            "planned_end_ns": self.planned_end_ns,
            "recovery_id": self.recovery_id,
            "recovery_start_ns": self.recovery_start_ns,
            "shard_id": self.shard_id,
            "source_site_id": self.source_site_id,
            "state_bytes": self.state_bytes,
            "target_site_id": self.target_site_id,
            "transfer_latency_ns": self.transfer_latency_ns,
            "transfer_start_ns": self.transfer_start_ns,
        }

    def to_json(self, *, indent: Optional[int] = None) -> str:
        return _json_dumps(self.to_dict(), indent)

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "RestoreTransferOutcome":
        data = _mapping(data, "restore transfer outcome")
        result = cls(
            recovery_id=data.get("recovery_id"),
            checkpoint_id=data.get("checkpoint_id"),
            shard_id=data.get("shard_id"),
            source_site_id=data.get("source_site_id"),
            target_site_id=data.get("target_site_id"),
            recovery_start_ns=data.get("recovery_start_ns"),
            transfer_start_ns=data.get("transfer_start_ns"),
            planned_end_ns=data.get("planned_end_ns"),
            execution_end_ns=data.get("execution_end_ns"),
            state_bytes=data.get("state_bytes"),
            interrupted=data.get("interrupted"),
            interruption_failure_id=data.get("interruption_failure_id"),
            attempted_bytes=data.get("attempted_bytes"),
            completed_bytes=data.get("completed_bytes"),
            lost_bytes=data.get("lost_bytes"),
        )
        for name, expected in (
            ("fixed_restart_latency_ns", result.fixed_restart_latency_ns),
            ("transfer_latency_ns", result.transfer_latency_ns),
        ):
            if name in data:
                claimed = _integer(data[name], name)
                if claimed != expected:
                    raise ValueError(
                        f"serialized restore transfer {name} is inconsistent"
                    )
        if "inter_site" in data:
            claimed_inter_site = data["inter_site"]
            if (
                not isinstance(claimed_inter_site, bool)
                or claimed_inter_site is not result.inter_site
            ):
                raise ValueError(
                    "serialized restore transfer inter_site is inconsistent"
                )
        return result

    @classmethod
    def from_json(cls, payload: str) -> "RestoreTransferOutcome":
        return cls.from_dict(_json_mapping(payload, "restore transfer outcome"))


@dataclass(frozen=True)
class SiteRuntimeSnapshot:
    site_id: str
    state: SiteState
    active_failure_ids: Tuple[str, ...]
    in_flight_attempt_id: Optional[str]
    active_recovery_id: Optional[str]

    def __post_init__(self) -> None:
        state = self.state
        if not isinstance(state, SiteState):
            try:
                state = SiteState(state)
            except (TypeError, ValueError) as exc:
                raise ValueError("state must be a valid SiteState") from exc
        object.__setattr__(self, "site_id", _text(self.site_id, "site_id"))
        object.__setattr__(self, "state", state)
        object.__setattr__(
            self,
            "active_failure_ids",
            tuple(sorted(_ordered_ids(self.active_failure_ids, "active_failure_ids"))),
        )
        if self.in_flight_attempt_id is not None:
            object.__setattr__(
                self,
                "in_flight_attempt_id",
                _text(self.in_flight_attempt_id, "in_flight_attempt_id"),
            )
        if self.active_recovery_id is not None:
            object.__setattr__(
                self,
                "active_recovery_id",
                _text(self.active_recovery_id, "active_recovery_id"),
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "active_failure_ids": list(self.active_failure_ids),
            "active_recovery_id": self.active_recovery_id,
            "in_flight_attempt_id": self.in_flight_attempt_id,
            "site_id": self.site_id,
            "state": self.state.value,
        }

    def to_json(self, *, indent: Optional[int] = None) -> str:
        return _json_dumps(self.to_dict(), indent)

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "SiteRuntimeSnapshot":
        data = _mapping(data, "site runtime snapshot")
        return cls(
            site_id=data.get("site_id"),
            state=data.get("state"),
            active_failure_ids=tuple(data.get("active_failure_ids", ())),
            in_flight_attempt_id=data.get("in_flight_attempt_id"),
            active_recovery_id=data.get("active_recovery_id"),
        )

    @classmethod
    def from_json(cls, payload: str) -> "SiteRuntimeSnapshot":
        return cls.from_dict(_json_mapping(payload, "site runtime snapshot"))


@dataclass(frozen=True)
class RuntimeSnapshot:
    """One immutable decision view.

    Each ``FailureObservation.observed_at_ns`` is the snapshot's policy
    information cutoff, as required by ``RecoveryRequest``.  Detection time is
    stable and separate in ``failure_first_observed_at_ns``.
    """

    runtime_id: str
    lineage_id: str
    timestamp_ns: int
    batch: Tuple[DecisionBatchMember, ...]
    desired_membership: Tuple[str, ...]
    effective_membership: Tuple[str, ...]
    sites: Tuple[SiteRuntimeSnapshot, ...]
    observed_failures: Tuple[FailureObservation, ...]
    failure_first_observed_at_ns: Mapping[str, int]
    committed_checkpoints: Tuple[CheckpointManifest, ...]
    aborted_checkpoint_ids: Tuple[str, ...]
    restore_transfers: Tuple[RestoreTransferOutcome, ...]
    work: WorkLedger

    def __post_init__(self) -> None:
        timestamp_ns = _integer(self.timestamp_ns, "timestamp_ns")
        batch = tuple(self.batch)
        if not batch or any(not isinstance(item, DecisionBatchMember) for item in batch):
            raise TypeError("batch must contain at least one DecisionBatchMember")
        boundary_ids = [item.boundary_id for item in batch]
        if len(boundary_ids) != len(set(boundary_ids)):
            raise ValueError("decision batch boundary IDs must be unique")
        initial_members = tuple(
            item for item in batch if item.boundary is DecisionBoundary.INITIAL
        )
        if initial_members and (
            len(initial_members) != 1
            or batch[0].boundary is not DecisionBoundary.INITIAL
        ):
            raise ValueError("INITIAL must be the first member of its decision batch")
        ordered_members = batch[1:] if initial_members else batch
        keys = tuple(
            (_BOUNDARY_PRIORITY[item.boundary], item.boundary_id)
            for item in ordered_members
        )
        if keys != tuple(sorted(keys)):
            raise ValueError("decision batch members must preserve transition order")
        sites = tuple(self.sites)
        if any(not isinstance(item, SiteRuntimeSnapshot) for item in sites):
            raise TypeError("sites must contain SiteRuntimeSnapshot values")
        site_ids = [item.site_id for item in sites]
        if len(site_ids) != len(set(site_ids)) or tuple(site_ids) != tuple(
            sorted(site_ids)
        ):
            raise ValueError("site snapshots must be unique and sorted")
        if any(
            item.site_id is not None and item.site_id not in site_ids
            for item in batch
        ):
            raise ValueError("decision batch references an unknown site")
        desired = tuple(
            sorted(_ordered_ids(self.desired_membership, "desired_membership"))
        )
        effective = tuple(
            sorted(_ordered_ids(self.effective_membership, "effective_membership"))
        )
        if set(desired) - set(site_ids) or set(effective) - set(site_ids):
            raise ValueError("snapshot membership references an unknown site")
        # During a pending reconfiguration desired membership is the target,
        # while effective membership remains the last completed layout.  They
        # intentionally need not be subsets of one another.
        failures = tuple(self.observed_failures)
        if any(not isinstance(item, FailureObservation) for item in failures):
            raise TypeError("observed_failures must contain FailureObservation values")
        failure_ids = [item.failure_id for item in failures]
        if len(failure_ids) != len(set(failure_ids)):
            raise ValueError("observed failure IDs must be unique")
        if any(item.observed_at_ns != timestamp_ns for item in failures):
            raise ValueError(
                "failure observed_at_ns must equal the snapshot policy cutoff"
            )
        first_observed_raw = _mapping(
            self.failure_first_observed_at_ns,
            "failure_first_observed_at_ns",
        )
        first_observed = {
            _text(failure_id, "failure_first_observed_at_ns key"): _integer(
                timestamp,
                f"failure_first_observed_at_ns[{failure_id!r}]",
            )
            for failure_id, timestamp in first_observed_raw.items()
        }
        failures_by_id = {item.failure_id: item for item in failures}
        if set(first_observed) != set(failures_by_id):
            raise ValueError(
                "failure_first_observed_at_ns must exactly cover observed failures"
            )
        for failure_id, timestamp in first_observed.items():
            observation = failures_by_id[failure_id]
            if not (
                observation.failure_start_ns
                <= timestamp
                <= observation.observed_at_ns
            ):
                raise ValueError(
                    "first observed timestamp must lie between failure start and "
                    "the policy cutoff"
                )
        if not isinstance(self.work, WorkLedger):
            raise TypeError("work must be a WorkLedger")
        if self.work.as_of_ns != timestamp_ns:
            raise ValueError(
                "snapshot work ledger must be frozen exactly at timestamp_ns"
            )
        checkpoints = tuple(self.committed_checkpoints)
        if any(not isinstance(item, CheckpointManifest) for item in checkpoints):
            raise TypeError("committed checkpoints must contain manifests")
        if any(item.commit_at_ns > timestamp_ns for item in checkpoints):
            raise ValueError("committed checkpoint exceeds snapshot timestamp")
        if any(
            item.execution_end_ns > timestamp_ns for item in self.work.outcomes
        ):
            raise ValueError("work outcome exceeds snapshot timestamp")
        restore_transfers = tuple(self.restore_transfers)
        if any(
            not isinstance(item, RestoreTransferOutcome)
            for item in restore_transfers
        ):
            raise TypeError(
                "restore_transfers must contain RestoreTransferOutcome values"
            )
        transfer_ids = [
            (item.recovery_id, item.shard_id) for item in restore_transfers
        ]
        if len(transfer_ids) != len(set(transfer_ids)):
            raise ValueError("restore transfer recovery/shard IDs must be unique")
        if any(item.execution_end_ns > timestamp_ns for item in restore_transfers):
            raise ValueError("restore transfer outcome exceeds snapshot timestamp")
        transfers_by_recovery: dict[str, list[RestoreTransferOutcome]] = {}
        for item in restore_transfers:
            transfers_by_recovery.setdefault(item.recovery_id, []).append(item)
        for recovery_id, items in transfers_by_recovery.items():
            reference = items[0]
            manifests_by_id = {
                item.checkpoint_id: item for item in checkpoints
            }
            manifest = manifests_by_id.get(reference.checkpoint_id)
            if manifest is None:
                raise ValueError("restore transfer references an uncommitted checkpoint")
            expected_shards = {
                item.shard_id: (item.site_id, item.state_bytes)
                for item in manifest.shards
            }
            actual_shards = {
                item.shard_id: (item.source_site_id, item.state_bytes)
                for item in items
            }
            if actual_shards != expected_shards:
                raise ValueError(
                    "restore transfer shards do not match the checkpoint manifest"
                )
            if any(
                (
                    item.checkpoint_id,
                    item.target_site_id,
                    item.recovery_start_ns,
                    item.transfer_start_ns,
                    item.planned_end_ns,
                    item.execution_end_ns,
                    item.interrupted,
                    item.interruption_failure_id,
                )
                != (
                    reference.checkpoint_id,
                    reference.target_site_id,
                    reference.recovery_start_ns,
                    reference.transfer_start_ns,
                    reference.planned_end_ns,
                    reference.execution_end_ns,
                    reference.interrupted,
                    reference.interruption_failure_id,
                )
                for item in items
            ):
                raise ValueError(
                    f"restore shards for recovery {recovery_id!r} disagree"
                )
            total_state_bytes = sum(item.state_bytes for item in items)
            transfer_duration = (
                reference.planned_end_ns - reference.transfer_start_ns
            )
            elapsed_transfer = max(
                0,
                reference.execution_end_ns - reference.transfer_start_ns,
            )
            expected_attempted = (
                total_state_bytes
                if not reference.interrupted
                else (total_state_bytes * elapsed_transfer) // transfer_duration
            )
            if sum(item.attempted_bytes for item in items) != expected_attempted:
                raise ValueError(
                    "restore shard attempted bytes do not form an exact partition"
                )
        object.__setattr__(self, "runtime_id", _text(self.runtime_id, "runtime_id"))
        object.__setattr__(self, "lineage_id", _text(self.lineage_id, "lineage_id"))
        object.__setattr__(self, "timestamp_ns", timestamp_ns)
        object.__setattr__(self, "batch", batch)
        object.__setattr__(self, "desired_membership", desired)
        object.__setattr__(self, "effective_membership", effective)
        object.__setattr__(self, "sites", sites)
        object.__setattr__(
            self,
            "observed_failures",
            tuple(
                sorted(
                    failures,
                    key=lambda item: (item.failure_start_ns, item.failure_id),
                )
            ),
        )
        object.__setattr__(
            self,
            "failure_first_observed_at_ns",
            MappingProxyType(dict(sorted(first_observed.items()))),
        )
        object.__setattr__(
            self,
            "committed_checkpoints",
            tuple(
                sorted(
                    checkpoints,
                    key=lambda item: (item.commit_at_ns, item.checkpoint_id),
                )
            ),
        )
        object.__setattr__(
            self,
            "aborted_checkpoint_ids",
            tuple(
                sorted(
                    _ordered_ids(
                        self.aborted_checkpoint_ids, "aborted_checkpoint_ids"
                    )
                )
            ),
        )
        object.__setattr__(
            self,
            "restore_transfers",
            tuple(
                sorted(
                    restore_transfers,
                    key=lambda item: (
                        item.recovery_start_ns,
                        item.execution_end_ns,
                        item.recovery_id,
                        item.shard_id,
                    ),
                )
            ),
        )

    def site(self, site_id: str) -> SiteRuntimeSnapshot:
        site_id = _text(site_id, "site_id")
        for site in self.sites:
            if site.site_id == site_id:
                return site
        raise KeyError(f"unknown site {site_id!r}")

    @property
    def boundaries(self) -> Tuple[DecisionBoundary, ...]:
        return tuple(item.boundary for item in self.batch)

    @property
    def boundary_ids(self) -> Tuple[str, ...]:
        return tuple(item.boundary_id for item in self.batch)

    @property
    def inter_site_restore_attempted_bytes(self) -> int:
        return sum(
            item.attempted_bytes for item in self.restore_transfers if item.inter_site
        )

    @property
    def inter_site_restore_completed_bytes(self) -> int:
        return sum(
            item.completed_bytes for item in self.restore_transfers if item.inter_site
        )

    @property
    def inter_site_restore_lost_bytes(self) -> int:
        return sum(
            item.lost_bytes for item in self.restore_transfers if item.inter_site
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "aborted_checkpoint_ids": list(self.aborted_checkpoint_ids),
            "batch": [item.to_dict() for item in self.batch],
            "committed_checkpoints": [
                item.to_dict() for item in self.committed_checkpoints
            ],
            "desired_membership": list(self.desired_membership),
            "effective_membership": list(self.effective_membership),
            "failure_first_observed_at_ns": dict(
                self.failure_first_observed_at_ns
            ),
            "lineage_id": self.lineage_id,
            "observed_failures": [
                item.to_dict() for item in self.observed_failures
            ],
            "runtime_id": self.runtime_id,
            "restore_transfers": [
                item.to_dict() for item in self.restore_transfers
            ],
            "sites": [item.to_dict() for item in self.sites],
            "timestamp_ns": self.timestamp_ns,
            "work": self.work.to_dict(),
        }

    def to_json(self, *, indent: Optional[int] = None) -> str:
        return _json_dumps(self.to_dict(), indent)

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "RuntimeSnapshot":
        data = _mapping(data, "runtime snapshot")
        return cls(
            runtime_id=data.get("runtime_id"),
            lineage_id=data.get("lineage_id"),
            timestamp_ns=data.get("timestamp_ns"),
            batch=tuple(
                DecisionBatchMember.from_dict(
                    _mapping(item, "decision batch member")
                )
                for item in data.get("batch", ())
            ),
            desired_membership=tuple(data.get("desired_membership", ())),
            effective_membership=tuple(data.get("effective_membership", ())),
            sites=tuple(
                SiteRuntimeSnapshot.from_dict(_mapping(item, "site snapshot"))
                for item in data.get("sites", ())
            ),
            observed_failures=tuple(
                FailureObservation.from_dict(_mapping(item, "failure observation"))
                for item in data.get("observed_failures", ())
            ),
            failure_first_observed_at_ns=_mapping(
                data.get("failure_first_observed_at_ns", {}),
                "failure_first_observed_at_ns",
            ),
            committed_checkpoints=tuple(
                CheckpointManifest.from_dict(_mapping(item, "checkpoint manifest"))
                for item in data.get("committed_checkpoints", ())
            ),
            aborted_checkpoint_ids=tuple(data.get("aborted_checkpoint_ids", ())),
            restore_transfers=tuple(
                RestoreTransferOutcome.from_dict(
                    _mapping(item, "restore transfer outcome")
                )
                for item in data.get("restore_transfers", ())
            ),
            work=WorkLedger.from_dict(_mapping(data.get("work"), "work ledger")),
        )

    @classmethod
    def from_json(cls, payload: str) -> "RuntimeSnapshot":
        return cls.from_dict(_json_mapping(payload, "runtime snapshot"))


@dataclass(frozen=True)
class _Transition:
    transition_id: str
    timestamp_ns: int
    boundary: DecisionBoundary
    object_id: str
    site_id: Optional[str] = None

    @property
    def sort_key(self) -> tuple[int, int, str]:
        return (
            self.timestamp_ns,
            _BOUNDARY_PRIORITY[self.boundary],
            self.transition_id,
        )


@dataclass
class _RecoverySession:
    plan: RecoveryPlan
    restore_transition_id: str
    recovery_start_ns: int
    transfer_start_ns: int
    transfer_end_ns: int
    restore_shards: Tuple[CheckpointShard, ...]
    restore_source_site_ids: Tuple[str, ...]
    restore_complete: bool = False
    replay_attempt_id: Optional[str] = None


class RecoveryRuntime:
    """Small mutable kernel producing immutable policy decision snapshots."""

    def __init__(
        self,
        *,
        runtime_id: str,
        lineage_id: str,
        site_ids: Sequence[str],
        initial_membership: Sequence[str],
        failure_trace: FailureTrace,
        start_ns: int = 0,
    ) -> None:
        if not isinstance(failure_trace, FailureTrace):
            raise TypeError("failure_trace must be a FailureTrace")
        sites = tuple(sorted(_ordered_ids(site_ids, "site_ids", nonempty=True)))
        membership = tuple(
            sorted(
                _ordered_ids(
                    initial_membership,
                    "initial_membership",
                    nonempty=True,
                )
            )
        )
        if set(membership) - set(sites):
            raise ValueError("initial_membership references an unknown site")
        start = _integer(start_ns, "start_ns")
        for interval in failure_trace.intervals:
            if interval.site_id not in sites:
                raise ValueError(
                    f"failure {interval.failure_id!r} references unknown site"
                )
            if interval.failure_start_ns < start:
                raise ValueError("failure trace starts before runtime start")

        self._runtime_id = _text(runtime_id, "runtime_id")
        self._lineage_id = _text(lineage_id, "lineage_id")
        self._site_ids = sites
        self._now_ns = start
        self._failure_trace = failure_trace
        self._interval_by_id = {
            item.failure_id: item for item in failure_trace.intervals
        }
        self._states = {site_id: SiteState.HEALTHY_READY for site_id in sites}
        self._desired_membership = membership
        self._effective_membership = membership
        self._transitions: dict[str, _Transition] = {}
        self._in_flight: dict[str, SiteWorkAttempt] = {}
        self._used_attempt_ids: set[str] = set()
        self._outcomes: list[WorkAttemptOutcome] = []
        self._pending_manifests: dict[str, CheckpointManifest] = {}
        self._committed_manifests: list[CheckpointManifest] = []
        self._aborted_checkpoint_ids: set[str] = set()
        self._observed_failure_ids: set[str] = set()
        self._failure_first_observed_at_ns: dict[str, int] = {}
        self._active_failure_ids: dict[str, set[str]] = {
            site_id: set() for site_id in sites
        }
        self._recovered_failure_ids: set[str] = set()
        self._recoveries: dict[str, _RecoverySession] = {}
        self._used_recovery_ids: set[str] = set()
        self._restore_transfers: list[RestoreTransferOutcome] = []
        self._pending_reconfiguration_id: Optional[str] = None
        self._initial_emitted = False
        self._last_snapshot: Optional[RuntimeSnapshot] = None

        for interval in failure_trace.intervals:
            self._schedule_transition(
                _Transition(
                    transition_id=f"failure:{interval.failure_id}:observed",
                    timestamp_ns=interval.failure_start_ns,
                    boundary=DecisionBoundary.FAILURE_OBSERVED,
                    object_id=interval.failure_id,
                    site_id=interval.site_id,
                )
            )
            self._schedule_transition(
                _Transition(
                    transition_id=f"failure:{interval.failure_id}:physical-recovery",
                    timestamp_ns=interval.recovery_ns,
                    boundary=DecisionBoundary.PHYSICAL_RECOVERY,
                    object_id=interval.failure_id,
                    site_id=interval.site_id,
                )
            )

    @property
    def current_time_ns(self) -> int:
        return self._now_ns

    @property
    def desired_membership(self) -> Tuple[str, ...]:
        return self._desired_membership

    @property
    def effective_membership(self) -> Tuple[str, ...]:
        return self._effective_membership

    @property
    def work_ledger(self) -> WorkLedger:
        return WorkLedger(tuple(self._outcomes))

    @property
    def checkpoint_ledger(self) -> CheckpointLedger:
        return CheckpointLedger(
            tuple(item.as_completed_checkpoint() for item in self._committed_manifests)
        )

    @property
    def committed_manifests(self) -> Tuple[CheckpointManifest, ...]:
        return tuple(self._committed_manifests)

    @property
    def last_snapshot(self) -> Optional[RuntimeSnapshot]:
        return self._last_snapshot

    @property
    def restore_transfers(self) -> Tuple[RestoreTransferOutcome, ...]:
        return tuple(self._restore_transfers)

    def site_state(self, site_id: str) -> SiteState:
        site_id = _text(site_id, "site_id")
        try:
            return self._states[site_id]
        except KeyError as exc:
            raise KeyError(f"unknown site {site_id!r}") from exc

    def _schedule_transition(self, transition: _Transition) -> None:
        if transition.timestamp_ns < self._now_ns:
            raise ValueError("transition precedes current runtime time")
        if transition.transition_id in self._transitions:
            raise ValueError(f"duplicate transition ID {transition.transition_id!r}")
        self._transitions[transition.transition_id] = transition

    def _cancel_transition(self, transition_id: str) -> None:
        self._transitions.pop(transition_id, None)

    def _require_decision_time_drained(self) -> None:
        if not self._initial_emitted:
            raise RuntimeError(
                "advance_to_decision() must emit INITIAL before policy mutates "
                "the runtime"
            )
        pending = tuple(
            sorted(
                (
                    item
                    for item in self._transitions.values()
                    if item.timestamp_ns == self._now_ns
                ),
                key=lambda item: item.sort_key,
            )
        )
        if pending:
            raise RuntimeError(
                "advance_to_decision() must drain all transitions at the current "
                "timestamp before policy mutates the runtime"
            )

    def submit_attempt(self, attempt: SiteWorkAttempt) -> None:
        self._require_decision_time_drained()
        if isinstance(attempt, SiteWorkAttempt) and attempt.kind is WorkAttemptKind.REPLAY:
            raise ValueError("replay attempts are scheduled by the recovery runtime")
        self._register_attempt(attempt)

    def _register_attempt(self, attempt: SiteWorkAttempt) -> None:
        if not isinstance(attempt, SiteWorkAttempt):
            raise TypeError("attempt must be a SiteWorkAttempt")
        if attempt.lineage_id != self._lineage_id:
            raise ValueError("attempt lineage does not match runtime")
        if attempt.start_ns != self._now_ns:
            raise ValueError("attempt must start at current decision time")
        if attempt.site_id not in self._states:
            raise ValueError("attempt references an unknown site")
        if attempt.site_id in self._in_flight:
            raise ValueError("site already has an in-flight attempt")
        if attempt.attempt_id in self._used_attempt_ids:
            raise ValueError("attempt ID is already used")
        state = self._states[attempt.site_id]
        if attempt.kind is WorkAttemptKind.FORWARD:
            if state is not SiteState.HEALTHY_READY:
                raise ValueError("forward work requires HEALTHY_READY site state")
            if attempt.site_id not in self._effective_membership:
                raise ValueError("forward work requires effective membership")
            if (
                self._pending_reconfiguration_id is not None
                and attempt.site_id not in self._desired_membership
            ):
                raise ValueError(
                    "forward work cannot start on a site pending membership removal"
                )
        else:
            session = self._recoveries.get(attempt.recovery_plan_id)
            if session is None or session.plan.target_site_id != attempt.site_id:
                raise ValueError("replay attempt has no active recovery session")
            if not session.restore_complete:
                raise ValueError("replay work cannot start before restore completion")
            if session.replay_attempt_id != attempt.attempt_id:
                raise ValueError("replay attempt does not match the recovery session")
            if state is not SiteState.RESTORING:
                raise ValueError("replay work requires RESTORING site state")
        self._schedule_transition(
            _Transition(
                transition_id=f"attempt:{attempt.attempt_id}:complete",
                timestamp_ns=attempt.planned_end_ns,
                boundary=DecisionBoundary.OPERATION_COMPLETION,
                object_id=attempt.attempt_id,
                site_id=attempt.site_id,
            )
        )
        self._in_flight[attempt.site_id] = attempt
        self._used_attempt_ids.add(attempt.attempt_id)

    def schedule_checkpoint(self, manifest: CheckpointManifest) -> None:
        self._require_decision_time_drained()
        if not isinstance(manifest, CheckpointManifest):
            raise TypeError("manifest must be a CheckpointManifest")
        if manifest.lineage_id != self._lineage_id:
            raise ValueError("checkpoint lineage does not match runtime")
        if manifest.commit_at_ns <= self._now_ns:
            raise ValueError("checkpoint commit must follow current decision time")
        if manifest.checkpoint_write_started_at_ns < self._now_ns:
            raise ValueError("checkpoint write starts before current decision time")
        all_ids = {
            item.checkpoint_id for item in self._committed_manifests
        } | set(self._pending_manifests) | self._aborted_checkpoint_ids
        if manifest.checkpoint_id in all_ids:
            raise ValueError("checkpoint ID is already used")
        if set(manifest.site_membership) != set(self._effective_membership):
            raise ValueError(
                "checkpoint membership must equal effective membership when scheduled"
            )
        self._pending_manifests[manifest.checkpoint_id] = manifest
        self._schedule_transition(
            _Transition(
                transition_id=f"checkpoint:{manifest.checkpoint_id}:commit",
                timestamp_ns=manifest.commit_at_ns,
                boundary=DecisionBoundary.CHECKPOINT_COMMIT,
                object_id=manifest.checkpoint_id,
            )
        )

    def request_membership(
        self,
        desired_membership: Sequence[str],
        *,
        reconfiguration_id: str,
        duration_ns: int,
    ) -> None:
        self._require_decision_time_drained()
        if self._pending_reconfiguration_id is not None:
            raise ValueError("a membership reconfiguration is already pending")
        desired = tuple(
            sorted(
                _ordered_ids(
                    desired_membership,
                    "desired_membership",
                    nonempty=True,
                )
            )
        )
        if set(desired) - set(self._site_ids):
            raise ValueError("desired membership references an unknown site")
        removed = set(self._effective_membership) - set(desired)
        busy_removed = tuple(sorted(removed & set(self._in_flight)))
        if busy_removed:
            raise ValueError(
                "membership removal requires quiescent sites; in-flight work on "
                + ", ".join(busy_removed)
            )
        reconfiguration_id = _text(reconfiguration_id, "reconfiguration_id")
        duration = _integer(duration_ns, "duration_ns", minimum=1)
        self._desired_membership = desired
        self._pending_reconfiguration_id = reconfiguration_id
        self._schedule_transition(
            _Transition(
                transition_id=f"reconfiguration:{reconfiguration_id}:complete",
                timestamp_ns=self._now_ns + duration,
                boundary=DecisionBoundary.RECONFIGURATION_COMPLETION,
                object_id=reconfiguration_id,
            )
        )

    def begin_recovery(self, plan: RecoveryPlan) -> None:
        self._require_decision_time_drained()
        if not isinstance(plan, RecoveryPlan):
            raise TypeError("plan must be a RecoveryPlan")
        if plan.request.lineage_id != self._lineage_id:
            raise ValueError("recovery lineage does not match runtime")
        if plan.request.decision_time_ns != self._now_ns:
            raise ValueError("recovery plan must be made at current decision time")
        if not plan.can_start or plan.scheduled_start_ns != self._now_ns:
            raise ValueError("recovery plan is blocked or not scheduled now")
        if plan.recovery_id in self._used_recovery_ids:
            raise ValueError("recovery ID is already used")
        current_work_snapshot = self.work_ledger.snapshot_at(self._now_ns)
        if (
            plan.work_ledger_digest != current_work_snapshot.ledger_digest
            or plan.work_snapshot != current_work_snapshot
        ):
            raise ValueError(
                "recovery plan is not bound to the current as-of work ledger"
            )
        manifests_by_id = {
            item.checkpoint_id: item for item in self._committed_manifests
        }
        if plan.checkpoint.checkpoint_id not in manifests_by_id:
            raise ValueError("recovery checkpoint is not committed in this runtime")
        manifest = manifests_by_id[plan.checkpoint.checkpoint_id]
        if manifest.as_completed_checkpoint() != plan.checkpoint:
            raise ValueError("recovery checkpoint does not match committed manifest")
        derived_restore_resources = set(
            plan.checkpoint.restore_resource_ids(plan.target_site_id)
        )
        if not derived_restore_resources <= set(
            plan.request.available_resource_ids
        ):
            raise ValueError(
                "recovery plan claims startability without every derived shard "
                "restore resource"
            )
        if plan.request.failure.failure_id not in self._observed_failure_ids:
            raise ValueError("recovery failure is outside the observed prefix")
        policy_observations = self._policy_failure_observations()
        if plan.request.failure_observations != policy_observations:
            raise ValueError(
                "recovery failure observations do not match the policy-visible prefix"
            )
        observed = {
            item.failure_id: item for item in policy_observations
        }[plan.request.failure.failure_id]
        if observed != plan.request.failure:
            raise ValueError("recovery failure observation is stale or inconsistent")
        target = plan.target_site_id
        if target not in self._states:
            raise ValueError("recovery target is not a runtime site")
        if target in self._in_flight:
            raise ValueError("recovery target has an in-flight attempt")
        if self._states[target] not in {
            SiteState.RECOVERED_UNRESTORED,
            SiteState.HEALTHY_READY,
        }:
            raise ValueError("recovery target is not available for restore")
        restore_source_site_ids = tuple(
            sorted({item.site_id for item in manifest.shards})
        )
        unavailable_sources = tuple(
            site_id
            for site_id in restore_source_site_ids
            if site_id in self._states
            and self._states[site_id] is not SiteState.HEALTHY_READY
        )
        if unavailable_sources:
            raise ValueError("one or more recovery shard sources are not HEALTHY_READY")
        restore_latency = (
            plan.request.fixed_restart_latency_ns + plan.transfer_latency_ns
        )
        transfer_start_ns = (
            self._now_ns + plan.request.fixed_restart_latency_ns
        )
        transfer_end_ns = transfer_start_ns + plan.transfer_latency_ns
        transition_id = f"recovery:{plan.recovery_id}:restore-complete"
        replay_attempt_id = (
            None
            if not plan.supporting_outcome_ids
            else f"{self._runtime_id}:{plan.recovery_id}:replay"
        )
        updated_work = self.work_ledger
        if plan.supporting_outcome_ids:
            updated_work = updated_work.invalidate_outcomes(
                plan.supporting_outcome_ids,
                recovery_id=plan.recovery_id,
                effective_at_ns=self._now_ns,
            )
        self._schedule_transition(
            _Transition(
                transition_id=transition_id,
                timestamp_ns=self._now_ns + restore_latency,
                boundary=DecisionBoundary.RESTORE_COMPLETION,
                object_id=plan.recovery_id,
                site_id=target,
            )
        )
        self._outcomes = list(updated_work.outcomes)
        self._recoveries[plan.recovery_id] = _RecoverySession(
            plan=plan,
            restore_transition_id=transition_id,
            recovery_start_ns=self._now_ns,
            transfer_start_ns=transfer_start_ns,
            transfer_end_ns=transfer_end_ns,
            restore_shards=manifest.shards,
            restore_source_site_ids=restore_source_site_ids,
            replay_attempt_id=replay_attempt_id,
        )
        self._used_recovery_ids.add(plan.recovery_id)
        self._states[target] = SiteState.RESTORING
        self._remove_effective_site(target)

    def advance_to_decision(self) -> Optional[RuntimeSnapshot]:
        if not self._initial_emitted:
            self._initial_emitted = True
            batch = [
                DecisionBatchMember(
                    boundary=DecisionBoundary.INITIAL,
                    boundary_id=f"{self._runtime_id}:initial",
                    object_id=self._runtime_id,
                )
            ]
            while True:
                candidates = tuple(
                    item
                    for item in self._transitions.values()
                    if item.timestamp_ns == self._now_ns
                )
                if not candidates:
                    break
                transition = min(candidates, key=lambda item: item.sort_key)
                del self._transitions[transition.transition_id]
                self._apply_transition(transition)
                batch.append(
                    DecisionBatchMember(
                        boundary=transition.boundary,
                        boundary_id=transition.transition_id,
                        object_id=transition.object_id,
                        site_id=transition.site_id,
                    )
                )
            snapshot = self._snapshot(
                tuple(batch)
            )
            self._last_snapshot = snapshot
            return snapshot
        if not self._transitions:
            return None
        timestamp_ns = min(item.timestamp_ns for item in self._transitions.values())
        self._now_ns = timestamp_ns
        batch = []
        while True:
            candidates = tuple(
                item
                for item in self._transitions.values()
                if item.timestamp_ns == timestamp_ns
            )
            if not candidates:
                break
            transition = min(candidates, key=lambda item: item.sort_key)
            del self._transitions[transition.transition_id]
            self._apply_transition(transition)
            batch.append(
                DecisionBatchMember(
                    boundary=transition.boundary,
                    boundary_id=transition.transition_id,
                    object_id=transition.object_id,
                    site_id=transition.site_id,
                )
            )
        snapshot = self._snapshot(tuple(batch))
        self._last_snapshot = snapshot
        return snapshot

    def _apply_transition(self, transition: _Transition) -> None:
        if transition.boundary is DecisionBoundary.OPERATION_COMPLETION:
            self._complete_attempt(transition)
        elif transition.boundary is DecisionBoundary.CHECKPOINT_COMMIT:
            self._commit_checkpoint(transition)
        elif transition.boundary is DecisionBoundary.FAILURE_OBSERVED:
            self._observe_failure(transition)
        elif transition.boundary is DecisionBoundary.PHYSICAL_RECOVERY:
            self._observe_physical_recovery(transition)
        elif transition.boundary is DecisionBoundary.RESTORE_COMPLETION:
            self._complete_restore(transition)
        elif transition.boundary is DecisionBoundary.RECONFIGURATION_COMPLETION:
            self._complete_reconfiguration(transition)
        else:
            raise RuntimeError(f"unsupported transition {transition.boundary.value}")

    def _complete_attempt(self, transition: _Transition) -> None:
        assert transition.site_id is not None
        attempt = self._in_flight.pop(transition.site_id, None)
        if attempt is None or attempt.attempt_id != transition.object_id:
            raise RuntimeError("operation completion has no matching in-flight attempt")
        outcome = evaluate_work_attempt(
            attempt,
            FailureTrace(f"{self._runtime_id}:empty", ()),
        )
        if attempt.kind is WorkAttemptKind.REPLAY:
            assert attempt.recovery_plan_id is not None
            session = self._recoveries.get(attempt.recovery_plan_id)
            if session is None:
                raise RuntimeError("replay completion has no active recovery")
            if not math.isclose(
                outcome.recomputed_work,
                session.plan.replay_required_work,
                rel_tol=1e-12,
                abs_tol=1e-12,
            ):
                raise RuntimeError("replay completion does not satisfy recovery plan")
            committed = self.work_ledger.commit_replay(outcome)
            self._outcomes = list(committed.outcomes)
            del self._recoveries[attempt.recovery_plan_id]
            self._states[attempt.site_id] = SiteState.HEALTHY_READY
            self._refresh_ready_site(attempt.site_id)
        else:
            self._outcomes.append(outcome)

    def _commit_checkpoint(self, transition: _Transition) -> None:
        manifest = self._pending_manifests.pop(transition.object_id, None)
        if manifest is None:
            raise RuntimeError("checkpoint transition has no pending manifest")
        runtime_dependency_sites = set(manifest.site_membership) | {
            item.site_id
            for item in manifest.shards
            if item.site_id in self._states
        }
        ready = all(
            self._states[site_id] is SiteState.HEALTHY_READY
            for site_id in runtime_dependency_sites
        )
        if not ready or set(manifest.site_membership) != set(
            self._effective_membership
        ):
            self._aborted_checkpoint_ids.add(manifest.checkpoint_id)
            return
        lineage_manifests = tuple(
            item
            for item in self._committed_manifests
            if item.lineage_id == manifest.lineage_id
        )
        if not lineage_manifests and not manifest.is_genesis:
            self._aborted_checkpoint_ids.add(manifest.checkpoint_id)
            return
        if any(
            item.lineage_id == manifest.lineage_id
            and item.committed_step == manifest.committed_step
            for item in self._committed_manifests
        ):
            self._aborted_checkpoint_ids.add(manifest.checkpoint_id)
            return
        latest_step = (
            0
            if not self._committed_manifests
            else self._committed_manifests[-1].committed_step
        )
        ledger = self.work_ledger
        completed_sites_by_step: dict[int, set[str]] = {}
        for outcome in ledger.canonical_outcomes:
            for identity in ledger.logical_identities_for(outcome):
                completed_sites_by_step.setdefault(
                    identity.logical_step, set()
                ).add(identity.original_site_id)
        required_sites = set(manifest.site_membership)
        frontier = latest_step
        while required_sites <= completed_sites_by_step.get(frontier + 1, set()):
            frontier += 1
        if not latest_step <= manifest.committed_step <= frontier:
            self._aborted_checkpoint_ids.add(manifest.checkpoint_id)
            return
        self._committed_manifests.append(manifest)
        self._committed_manifests.sort(
            key=lambda item: (item.commit_at_ns, item.checkpoint_id)
        )

    def _observe_failure(self, transition: _Transition) -> None:
        interval = self._interval_by_id[transition.object_id]
        site_id = interval.site_id
        self._observed_failure_ids.add(interval.failure_id)
        self._failure_first_observed_at_ns.setdefault(
            interval.failure_id,
            self._now_ns,
        )
        self._active_failure_ids[site_id].add(interval.failure_id)

        attempt = self._in_flight.pop(site_id, None)
        if attempt is not None:
            completion_id = f"attempt:{attempt.attempt_id}:complete"
            self._cancel_transition(completion_id)
            outcome = evaluate_work_attempt(
                attempt,
                FailureTrace(
                    f"{self._runtime_id}:{interval.failure_id}",
                    (interval,),
                ),
            )
            self._outcomes.append(outcome)
            if attempt.kind is WorkAttemptKind.REPLAY:
                assert attempt.recovery_plan_id is not None
                self._cancel_recovery(
                    attempt.recovery_plan_id,
                    interruption_failure_id=interval.failure_id,
                )

        for recovery_id, session in tuple(self._recoveries.items()):
            target_failed = session.plan.target_site_id == site_id
            source_failed_during_restore = (
                not session.restore_complete
                and site_id in session.restore_source_site_ids
            )
            if target_failed or source_failed_during_restore:
                self._cancel_recovery(
                    recovery_id,
                    interruption_failure_id=interval.failure_id,
                )

        affected_checkpoints = []
        for checkpoint_id, manifest in self._pending_manifests.items():
            shard_sites = {item.site_id for item in manifest.shards}
            if site_id in set(manifest.site_membership) | shard_sites:
                affected_checkpoints.append(checkpoint_id)
        for checkpoint_id in affected_checkpoints:
            self._pending_manifests.pop(checkpoint_id)
            self._aborted_checkpoint_ids.add(checkpoint_id)
            self._cancel_transition(f"checkpoint:{checkpoint_id}:commit")

        self._states[site_id] = SiteState.FAILED
        self._remove_effective_site(site_id)

    def _observe_physical_recovery(self, transition: _Transition) -> None:
        interval = self._interval_by_id[transition.object_id]
        site_id = interval.site_id
        self._recovered_failure_ids.add(interval.failure_id)
        self._active_failure_ids[site_id].discard(interval.failure_id)
        if self._active_failure_ids[site_id]:
            self._states[site_id] = SiteState.FAILED
        else:
            self._states[site_id] = SiteState.RECOVERED_UNRESTORED
        self._remove_effective_site(site_id)

    def _complete_restore(self, transition: _Transition) -> None:
        session = self._recoveries.get(transition.object_id)
        if session is None:
            raise RuntimeError("restore completion has no active recovery")
        plan = session.plan
        target = plan.target_site_id
        if self._states[target] is not SiteState.RESTORING:
            raise RuntimeError("restore target is not RESTORING")
        self._record_restore_transfer(session, interrupted=False)
        session.restore_complete = True
        if plan.replay_required_work == 0.0:
            del self._recoveries[plan.recovery_id]
            self._states[target] = SiteState.HEALTHY_READY
            self._refresh_ready_site(target)
            return
        if plan.replay_latency_ns <= 0:
            raise RuntimeError("positive replay work requires positive latency")
        attempt_id = f"{self._runtime_id}:{plan.recovery_id}:replay"
        session.replay_attempt_id = attempt_id
        snapshot_by_id = {
            item.attempt.attempt_id: item
            for item in plan.work_snapshot.outcomes
        }
        replay_bindings = tuple(
            ReplayLineageBinding(
                target_attempt_id=target_id,
                logical_work=identity,
            )
            for target_id in plan.supporting_outcome_ids
            for identity in plan.work_snapshot.logical_identities_for(
                snapshot_by_id[target_id]
            )
        )
        replay_steps = tuple(
            binding.logical_work.logical_step for binding in replay_bindings
        )
        attempt = SiteWorkAttempt(
            attempt_id=attempt_id,
            lineage_id=self._lineage_id,
            site_id=target,
            step=max(replay_steps),
            start_ns=self._now_ns,
            planned_end_ns=self._now_ns + plan.replay_latency_ns,
            planned_work=plan.replay_required_work,
            work_unit=(self.work_ledger.work_unit or "work_unit"),
            kind=WorkAttemptKind.REPLAY,
            recovery_plan_id=plan.recovery_id,
            supersedes_attempt_ids=plan.supporting_outcome_ids,
            replay_bindings=replay_bindings,
            evidence=plan.request.evidence,
            metadata={
                "checkpoint_id": plan.checkpoint.checkpoint_id,
                "rollback_steps": plan.rollback_steps,
            },
        )
        self._register_attempt(attempt)

    def _complete_reconfiguration(self, transition: _Transition) -> None:
        if self._pending_reconfiguration_id != transition.object_id:
            raise RuntimeError("reconfiguration completion does not match pending ID")
        self._pending_reconfiguration_id = None
        self._effective_membership = tuple(
            site_id
            for site_id in self._desired_membership
            if self._states[site_id] is SiteState.HEALTHY_READY
        )

    def _record_restore_transfer(
        self,
        session: _RecoverySession,
        *,
        interrupted: bool,
        interruption_failure_id: Optional[str] = None,
    ) -> None:
        if session.restore_complete:
            return
        if interrupted:
            transfer_duration = session.transfer_end_ns - session.transfer_start_ns
            elapsed_transfer = min(
                transfer_duration,
                max(0, self._now_ns - session.transfer_start_ns),
            )
            execution_end_ns = self._now_ns
        else:
            transfer_duration = session.transfer_end_ns - session.transfer_start_ns
            elapsed_transfer = transfer_duration
            execution_end_ns = session.transfer_end_ns
        cumulative_state_bytes = 0
        allocated_attempted_bytes = 0
        for shard in session.restore_shards:
            cumulative_state_bytes += shard.state_bytes
            cumulative_attempted_bytes = (
                cumulative_state_bytes * elapsed_transfer
            ) // transfer_duration
            attempted = cumulative_attempted_bytes - allocated_attempted_bytes
            allocated_attempted_bytes = cumulative_attempted_bytes
            completed = 0 if interrupted else shard.state_bytes
            lost = attempted if interrupted else 0
            self._restore_transfers.append(
                RestoreTransferOutcome(
                    recovery_id=session.plan.recovery_id,
                    checkpoint_id=session.plan.checkpoint.checkpoint_id,
                    shard_id=shard.shard_id,
                    source_site_id=shard.site_id,
                    target_site_id=session.plan.target_site_id,
                    recovery_start_ns=session.recovery_start_ns,
                    transfer_start_ns=session.transfer_start_ns,
                    planned_end_ns=session.transfer_end_ns,
                    execution_end_ns=execution_end_ns,
                    state_bytes=shard.state_bytes,
                    interrupted=interrupted,
                    interruption_failure_id=interruption_failure_id,
                    attempted_bytes=attempted,
                    completed_bytes=completed,
                    lost_bytes=lost,
                )
            )
        self._restore_transfers.sort(
            key=lambda item: (
                item.recovery_start_ns,
                item.execution_end_ns,
                item.recovery_id,
                item.shard_id,
            )
        )

    def _cancel_recovery(
        self,
        recovery_id: str,
        *,
        interruption_failure_id: Optional[str] = None,
    ) -> None:
        session = self._recoveries.pop(recovery_id, None)
        if session is None:
            return
        if not session.restore_complete:
            if interruption_failure_id is None:
                raise RuntimeError(
                    "canceling an active restore requires an interruption failure ID"
                )
            self._record_restore_transfer(
                session,
                interrupted=True,
                interruption_failure_id=interruption_failure_id,
            )
        self._cancel_transition(session.restore_transition_id)
        if session.replay_attempt_id is not None:
            self._cancel_transition(
                f"attempt:{session.replay_attempt_id}:complete"
            )
        target = session.plan.target_site_id
        if self._states[target] is SiteState.RESTORING:
            self._states[target] = SiteState.RECOVERED_UNRESTORED
            self._remove_effective_site(target)

    def _remove_effective_site(self, site_id: str) -> None:
        self._effective_membership = tuple(
            item for item in self._effective_membership if item != site_id
        )

    def _refresh_ready_site(self, site_id: str) -> None:
        if self._pending_reconfiguration_id is not None:
            return
        if site_id not in self._desired_membership:
            return
        self._effective_membership = tuple(
            sorted(set(self._effective_membership) | {site_id})
        )

    def _policy_failure_observations(self) -> Tuple[FailureObservation, ...]:
        observations = []
        for failure_id in sorted(
            self._observed_failure_ids,
            key=lambda item: (
                self._interval_by_id[item].failure_start_ns,
                item,
            ),
        ):
            interval = self._interval_by_id[failure_id]
            if failure_id in self._recovered_failure_ids:
                observations.append(
                    FailureObservation(
                        failure_id=failure_id,
                        site_id=interval.site_id,
                        failure_start_ns=interval.failure_start_ns,
                        observed_at_ns=self._now_ns,
                        status=FailureStatus.RECOVERED,
                        recovery_observed_ns=interval.recovery_ns,
                        cause=interval.cause,
                        evidence=interval.evidence,
                    )
                )
            else:
                observations.append(
                    FailureObservation(
                        failure_id=failure_id,
                        site_id=interval.site_id,
                        failure_start_ns=interval.failure_start_ns,
                        observed_at_ns=self._now_ns,
                        status=FailureStatus.ACTIVE,
                        cause=interval.cause,
                        evidence=interval.evidence,
                    )
                )
        return tuple(observations)

    def _snapshot(
        self,
        batch: Tuple[DecisionBatchMember, ...],
    ) -> RuntimeSnapshot:
        recovery_by_site = {
            session.plan.target_site_id: recovery_id
            for recovery_id, session in self._recoveries.items()
        }
        sites = []
        for site_id in self._site_ids:
            attempt = self._in_flight.get(site_id)
            sites.append(
                SiteRuntimeSnapshot(
                    site_id=site_id,
                    state=self._states[site_id],
                    active_failure_ids=tuple(
                        sorted(self._active_failure_ids[site_id])
                    ),
                    in_flight_attempt_id=(
                        None if attempt is None else attempt.attempt_id
                    ),
                    active_recovery_id=recovery_by_site.get(site_id),
                )
            )
        return RuntimeSnapshot(
            runtime_id=self._runtime_id,
            lineage_id=self._lineage_id,
            timestamp_ns=self._now_ns,
            batch=batch,
            desired_membership=self._desired_membership,
            effective_membership=self._effective_membership,
            sites=tuple(sites),
            observed_failures=self._policy_failure_observations(),
            failure_first_observed_at_ns=self._failure_first_observed_at_ns,
            committed_checkpoints=tuple(self._committed_manifests),
            aborted_checkpoint_ids=tuple(sorted(self._aborted_checkpoint_ids)),
            restore_transfers=tuple(self._restore_transfers),
            work=self.work_ledger.snapshot_at(self._now_ns),
        )


__all__ = [
    "CheckpointManifest",
    "CheckpointShard",
    "DecisionBatchMember",
    "DecisionBoundary",
    "RecoveryRuntime",
    "RestoreTransferOutcome",
    "RuntimeSnapshot",
    "SiteRuntimeSnapshot",
    "SiteState",
]
