"""PW3 rack-boundary telemetry with explicit clocks and evidence boundaries.

This module is deliberately a measurement substrate, not a power model.  It
binds every local GPU by its NVML UUID and process-local CUDA index, records
external meters without silently aggregating or interpolating them, and emits
an explicit absence record whenever a configured channel is not observed.

The JSONL format is append-by-chunk.  Each completed chunk contains a trailer
whose SHA-256 covers the exact UTF-8 bytes of its header and data records.  A
previous-chunk digest in the next header makes resumed streams hash chained.
Resolved authentication material is kept in request-local variables and is
never returned in manifests, diagnostics, or serialized configuration.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
import base64
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import re
import ssl
import sys
import threading
import time
from typing import Any, Callable, Mapping, Protocol, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen


CHANNEL_MANIFEST_SCHEMA = "gpu-stack.telemetry-channel-manifest.v1"
SAMPLE_SCHEMA = "gpu-stack.telemetry-sample.v1"
CLOCK_OFFSET_SCHEMA = "gpu-stack.telemetry-clock-offset.v1"
MISSING_CHANNEL_SCHEMA = "gpu-stack.telemetry-missing-channel.v1"
CHUNK_SCHEMA = "gpu-stack.telemetry-jsonl-chunk.v1"
SESSION_SCHEMA = "gpu-stack.e002-pw3-telemetry-session.v1"
CONFIG_SCHEMA = "gpu-stack.e002-pw3-telemetry-config.v1"
PHASE_MARKER_SCHEMA = "gpu-stack.e002-pw3-phase-marker.v1"
ENGINE_ID = "gpu-stack.e002-pw3-rack-telemetry.v1"

HOST_REFERENCE_CLOCK_ID = "host-perf-counter"
UTC_CLOCK_ID = "utc"

GPU_BOARD_BOUNDARY = "gpu-board"
RACK_AC_INPUT_BOUNDARY = "rack-ac-input"
STORAGE_ACTIVITY_BOUNDARY = "storage-activity"
STORAGE_POWER_BOUNDARY = "storage-power"
COOLING_BOUNDARY = "cooling"

_ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_STREAM_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
_SAMPLE_KINDS = {
    "gauge",
    "cumulative_counter",
    "interval_average",
    "interval_total",
    "state",
}
_QUALITY_STATUSES = {
    "observed",
    "counter_reset",
    "stale",
    "clock_uncertain",
}


class TelemetryError(RuntimeError):
    """Base exception for the PW3 telemetry substrate."""


class TelemetryConfigurationError(TelemetryError):
    """Raised when a channel, source, or stream is ambiguously configured."""


class TelemetryBindingError(TelemetryError):
    """Raised when a requested CUDA-index/UUID binding cannot be proven."""


class TelemetrySourceError(TelemetryError):
    """Raised when an observation source cannot return admissible evidence."""


class MissingCredentialEnvironment(TelemetrySourceError):
    """Raised with environment-variable names, never credential values."""

    def __init__(self, environment_names: Sequence[str]) -> None:
        names = tuple(sorted(set(environment_names)))
        self.environment_names = names
        super().__init__(
            "required credential environment variable(s) are unset: "
            + ", ".join(names)
        )


class MissingRequiredChannels(TelemetryError):
    """Raised only on an explicit strict availability check."""

    def __init__(self, records: Sequence["MissingChannelRecord"]) -> None:
        required = tuple(record for record in records if record.required)
        self.records = required
        super().__init__(
            "required telemetry channel(s) were not observed: "
            + ", ".join(record.channel_id for record in required)
        )


def _utc_iso(utc_ns: int) -> str:
    return (
        datetime.fromtimestamp(utc_ns / 1_000_000_000, timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def _canonical_line(record: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(
            record,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )


def _decode_nvml_text(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="strict")
    return str(value)


def _normalized_gpu_uuid(value: Any) -> str:
    if isinstance(value, bytes):
        try:
            text = value.decode("ascii")
        except UnicodeDecodeError:
            text = value.hex()
    else:
        text = str(value)
    lowered = text.strip().lower()
    if lowered.startswith("gpu-"):
        lowered = lowered[4:]
    return re.sub(r"[^0-9a-f]", "", lowered)


def _finite_number(value: Any, *, field_name: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TelemetrySourceError(f"{field_name} is not numeric")
    if not math.isfinite(float(value)):
        raise TelemetrySourceError(f"{field_name} is not finite")
    return value


def _exception_detail(error: BaseException) -> str:
    """Return a diagnostic that cannot include HTTP auth headers or bodies."""

    if isinstance(error, MissingCredentialEnvironment):
        return str(error)
    if isinstance(error, HTTPError):
        return f"HTTP request failed with status {error.code}"
    if isinstance(error, URLError):
        return f"HTTP transport failed: {type(error.reason).__name__}"
    return f"{type(error).__name__}: {error}"


def _reason_code(error: BaseException) -> str:
    if isinstance(error, MissingCredentialEnvironment):
        return "credential_environment_missing"
    if isinstance(error, HTTPError):
        return "http_status_error"
    if isinstance(error, URLError):
        return "http_transport_error"
    if isinstance(error, TelemetryBindingError):
        return "identity_binding_failed"
    if isinstance(error, FileNotFoundError):
        return "source_not_found"
    if isinstance(error, PermissionError):
        return "source_permission_denied"
    return "source_observation_failed"


@dataclass(frozen=True)
class ChannelManifest:
    """The complete interpretation contract for one scalar channel."""

    channel_id: str
    boundary: str
    source_id: str
    metric: str
    unit: str
    sample_kind: str
    clock_id: str
    nominal_period_ns: int
    integration_window_ns: int
    uncertainty_ns: int
    required: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "channel_id",
            "boundary",
            "source_id",
            "metric",
            "unit",
            "clock_id",
        ):
            if not str(getattr(self, name)).strip():
                raise TelemetryConfigurationError(f"{name} cannot be empty")
        if self.sample_kind not in _SAMPLE_KINDS:
            raise TelemetryConfigurationError(
                f"unsupported sample_kind: {self.sample_kind}"
            )
        for name in (
            "nominal_period_ns",
            "integration_window_ns",
            "uncertainty_ns",
        ):
            if int(getattr(self, name)) < 0:
                raise TelemetryConfigurationError(f"{name} cannot be negative")

    def to_record(self) -> dict[str, Any]:
        return {
            "record_type": "channel_manifest",
            "schema": CHANNEL_MANIFEST_SCHEMA,
            "channel_id": self.channel_id,
            "boundary": self.boundary,
            "source_id": self.source_id,
            "metric": self.metric,
            "unit": self.unit,
            "sample_kind": self.sample_kind,
            "clock_id": self.clock_id,
            "nominal_period_ns": self.nominal_period_ns,
            "integration_window_ns": self.integration_window_ns,
            "uncertainty_ns": self.uncertainty_ns,
            "required": self.required,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class SampleQuality:
    status: str = "observed"
    uncertainty_ns: int = 0
    flags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.status not in _QUALITY_STATUSES:
            raise TelemetryConfigurationError(
                f"unsupported sample quality status: {self.status}"
            )
        if self.uncertainty_ns < 0:
            raise TelemetryConfigurationError(
                "sample uncertainty cannot be negative"
            )
        prohibited = {"modeled", "imputed", "interpolated"}
        if prohibited.intersection(flag.lower() for flag in self.flags):
            raise TelemetryConfigurationError(
                "modeled or imputed values are not telemetry samples"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "uncertainty_ns": self.uncertainty_ns,
            "flags": list(self.flags),
        }


@dataclass(frozen=True)
class TelemetrySample:
    """One directly observed value with both UTC and local-clock support."""

    channel_id: str
    utc_interval_start_ns: int
    utc_interval_end_ns: int
    reference_interval_start_ns: int
    reference_interval_end_ns: int
    value: int | float
    sequence: int
    quality: SampleQuality

    def __post_init__(self) -> None:
        if self.utc_interval_end_ns < self.utc_interval_start_ns:
            raise TelemetryConfigurationError("UTC sample interval is reversed")
        if self.reference_interval_end_ns < self.reference_interval_start_ns:
            raise TelemetryConfigurationError(
                "reference sample interval is reversed"
            )
        _finite_number(self.value, field_name="sample value")
        if self.sequence < 0:
            raise TelemetryConfigurationError("sample sequence cannot be negative")

    def to_record(self) -> dict[str, Any]:
        return {
            "record_type": "sample",
            "schema": SAMPLE_SCHEMA,
            "channel_id": self.channel_id,
            "utc_interval_start_ns": self.utc_interval_start_ns,
            "utc_interval_end_ns": self.utc_interval_end_ns,
            "utc_interval_start": _utc_iso(self.utc_interval_start_ns),
            "utc_interval_end": _utc_iso(self.utc_interval_end_ns),
            "reference_interval_start_ns": self.reference_interval_start_ns,
            "reference_interval_end_ns": self.reference_interval_end_ns,
            "value": self.value,
            "sequence": self.sequence,
            "quality": self.quality.to_dict(),
        }


@dataclass(frozen=True)
class ClockOffsetRecord:
    """Observed relation ``reference = source + offset`` between clocks."""

    clock_id: str
    reference_clock_id: str
    local_interval_start_ns: int
    local_interval_end_ns: int
    observed_at_utc_ns: int
    offset_to_reference_ns: int
    uncertainty_ns: int
    sequence: int
    method: str
    quality: str = "observed"

    def __post_init__(self) -> None:
        if self.local_interval_end_ns < self.local_interval_start_ns:
            raise TelemetryConfigurationError("clock interval is reversed")
        if self.uncertainty_ns < 0:
            raise TelemetryConfigurationError(
                "clock uncertainty cannot be negative"
            )
        if self.quality not in {"observed", "stale", "clock_uncertain"}:
            raise TelemetryConfigurationError(
                f"unsupported clock quality: {self.quality}"
            )

    def to_record(self) -> dict[str, Any]:
        return {
            "record_type": "clock_offset",
            "schema": CLOCK_OFFSET_SCHEMA,
            "clock_id": self.clock_id,
            "reference_clock_id": self.reference_clock_id,
            "local_interval_start_ns": self.local_interval_start_ns,
            "local_interval_end_ns": self.local_interval_end_ns,
            "observed_at_utc_ns": self.observed_at_utc_ns,
            "observed_at_utc": _utc_iso(self.observed_at_utc_ns),
            "offset_to_reference_ns": self.offset_to_reference_ns,
            "uncertainty_ns": self.uncertainty_ns,
            "sequence": self.sequence,
            "method": self.method,
            "quality": self.quality,
        }


@dataclass(frozen=True)
class MissingChannelRecord:
    """An explicit absence record; it is never converted into a sample."""

    channel_id: str
    source_id: str
    metric: str
    required: bool
    utc_observed_ns: int
    reference_observed_ns: int
    sequence: int
    reason_code: str
    detail: str

    def to_record(self) -> dict[str, Any]:
        return {
            "record_type": "missing_channel",
            "schema": MISSING_CHANNEL_SCHEMA,
            "channel_id": self.channel_id,
            "source_id": self.source_id,
            "metric": self.metric,
            "required": self.required,
            "utc_observed_ns": self.utc_observed_ns,
            "utc_observed": _utc_iso(self.utc_observed_ns),
            "reference_observed_ns": self.reference_observed_ns,
            "sequence": self.sequence,
            "reason_code": self.reason_code,
            "detail": self.detail,
            "substitution": None,
        }


@dataclass(frozen=True)
class SourceDiagnostic:
    source_id: str
    utc_observed_ns: int
    reference_observed_ns: int
    status: str
    detail: str

    def to_record(self) -> dict[str, Any]:
        return {
            "record_type": "source_diagnostic",
            "source_id": self.source_id,
            "utc_observed_ns": self.utc_observed_ns,
            "utc_observed": _utc_iso(self.utc_observed_ns),
            "reference_observed_ns": self.reference_observed_ns,
            "status": self.status,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class SourcePollResult:
    samples: tuple[TelemetrySample, ...] = ()
    missing_channels: tuple[MissingChannelRecord, ...] = ()
    clock_offsets: tuple[ClockOffsetRecord, ...] = ()
    diagnostics: tuple[SourceDiagnostic, ...] = ()


@dataclass(frozen=True)
class TelemetryBatch:
    samples: tuple[TelemetrySample, ...]
    missing_channels: tuple[MissingChannelRecord, ...]
    clock_offsets: tuple[ClockOffsetRecord, ...]
    diagnostics: tuple[SourceDiagnostic, ...]

    @property
    def missing_required_channels(self) -> tuple[MissingChannelRecord, ...]:
        return tuple(record for record in self.missing_channels if record.required)

    def require_complete(self) -> None:
        missing = self.missing_required_channels
        if missing:
            raise MissingRequiredChannels(missing)


class HostReferenceClock:
    """Relate ``perf_counter_ns`` to UTC with a measured bracket."""

    def __init__(self, clock_id: str = HOST_REFERENCE_CLOCK_ID) -> None:
        self.clock_id = clock_id
        self._lock = threading.Lock()
        self._record: ClockOffsetRecord | None = None
        self._sequence = 0
        self._perf_resolution_ns = max(
            1,
            math.ceil(time.get_clock_info("perf_counter").resolution * 1e9),
        )
        self._wall_resolution_ns = max(
            1,
            math.ceil(time.get_clock_info("time").resolution * 1e9),
        )

    @staticmethod
    def now_reference_ns() -> int:
        return time.perf_counter_ns()

    def calibrate(self, attempts: int = 9) -> ClockOffsetRecord:
        if attempts <= 0:
            raise TelemetryConfigurationError("clock attempts must be positive")
        candidates: list[tuple[int, int, int, int]] = []
        for _ in range(attempts):
            local_start = time.perf_counter_ns()
            utc_ns = time.time_ns()
            local_end = time.perf_counter_ns()
            midpoint = local_start + (local_end - local_start) // 2
            uncertainty = (
                (local_end - local_start + 1) // 2
                + self._perf_resolution_ns
                + self._wall_resolution_ns
            )
            candidates.append((uncertainty, local_start, local_end, utc_ns))
        uncertainty, local_start, local_end, utc_ns = min(candidates)
        midpoint = local_start + (local_end - local_start) // 2
        with self._lock:
            record = ClockOffsetRecord(
                clock_id=self.clock_id,
                reference_clock_id=UTC_CLOCK_ID,
                local_interval_start_ns=local_start,
                local_interval_end_ns=local_end,
                observed_at_utc_ns=utc_ns,
                offset_to_reference_ns=utc_ns - midpoint,
                uncertainty_ns=uncertainty,
                sequence=self._sequence,
                method="minimum-bracket perf_counter_ns/time_ns midpoint",
            )
            self._sequence += 1
            self._record = record
            return record

    def current_offset(self) -> ClockOffsetRecord:
        with self._lock:
            record = self._record
        return record if record is not None else self.calibrate()

    def reference_to_utc_interval(
        self,
        reference_start_ns: int,
        reference_end_ns: int,
        *,
        additional_uncertainty_ns: int = 0,
    ) -> tuple[int, int, int]:
        record = self.current_offset()
        uncertainty = record.uncertainty_ns + additional_uncertainty_ns
        return (
            reference_start_ns
            + record.offset_to_reference_ns
            - uncertainty,
            reference_end_ns
            + record.offset_to_reference_ns
            + uncertainty,
            uncertainty,
        )

    def utc_to_reference_interval(
        self,
        utc_start_ns: int,
        utc_end_ns: int,
        *,
        additional_uncertainty_ns: int = 0,
    ) -> tuple[int, int, int]:
        record = self.current_offset()
        uncertainty = record.uncertainty_ns + additional_uncertainty_ns
        return (
            utc_start_ns
            - record.offset_to_reference_ns
            - uncertainty,
            utc_end_ns
            - record.offset_to_reference_ns
            + uncertainty,
            uncertainty,
        )


class _Sequencer:
    def __init__(self) -> None:
        self._values: dict[str, int] = {}
        self._lock = threading.Lock()

    def next(self, key: str) -> int:
        with self._lock:
            value = self._values.get(key, 0)
            self._values[key] = value + 1
            return value


@dataclass(frozen=True)
class _ObservationWindow:
    reference_start_ns: int
    reference_end_ns: int
    utc_start_ns: int
    utc_end_ns: int
    uncertainty_ns: int


def _observation_window(
    clock: HostReferenceClock,
    reference_start_ns: int,
    reference_end_ns: int,
    *,
    additional_uncertainty_ns: int = 0,
) -> _ObservationWindow:
    utc_start, utc_end, uncertainty = clock.reference_to_utc_interval(
        reference_start_ns,
        reference_end_ns,
        additional_uncertainty_ns=additional_uncertainty_ns,
    )
    return _ObservationWindow(
        reference_start_ns=reference_start_ns,
        reference_end_ns=reference_end_ns,
        utc_start_ns=utc_start,
        utc_end_ns=utc_end,
        uncertainty_ns=uncertainty,
    )


def _missing_record(
    manifest: ChannelManifest,
    clock: HostReferenceClock,
    sequencer: _Sequencer,
    *,
    reason_code: str,
    detail: str,
) -> MissingChannelRecord:
    reference_ns = clock.now_reference_ns()
    utc_start, utc_end, _ = clock.reference_to_utc_interval(
        reference_ns, reference_ns
    )
    return MissingChannelRecord(
        channel_id=manifest.channel_id,
        source_id=manifest.source_id,
        metric=manifest.metric,
        required=manifest.required,
        utc_observed_ns=utc_start + (utc_end - utc_start) // 2,
        reference_observed_ns=reference_ns,
        sequence=sequencer.next(manifest.channel_id),
        reason_code=reason_code,
        detail=detail,
    )


@dataclass(frozen=True)
class GpuTarget:
    """A frozen process-local CUDA slot bound to a stable physical UUID."""

    local_cuda_index: int
    gpu_uuid: str
    required: bool = True

    def __post_init__(self) -> None:
        if self.local_cuda_index < 0:
            raise TelemetryConfigurationError(
                "local CUDA index cannot be negative"
            )
        if not self.gpu_uuid.strip():
            raise TelemetryConfigurationError(
                "a stable GPU UUID is required for a frozen target"
            )


@dataclass(frozen=True)
class GpuIdentity:
    local_cuda_index: int
    nvml_index: int
    gpu_uuid: str
    pci_bus_id: str
    name: str

    @property
    def source_id(self) -> str:
        return f"nvml:{self.gpu_uuid}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "local_cuda_index": self.local_cuda_index,
            "nvml_index": self.nvml_index,
            "gpu_uuid": self.gpu_uuid,
            "pci_bus_id": self.pci_bus_id,
            "name": self.name,
        }


@dataclass(frozen=True)
class _PhysicalGpu:
    nvml_index: int
    handle: Any
    gpu_uuid: str
    pci_bus_id: str
    name: str


def _gpu_channel_id(gpu_uuid: str, metric: str) -> str:
    return f"gpu.{gpu_uuid}.{metric}"


class NvmlGpuTelemetrySource:
    """Poll all bound GPUs independently; no index-zero inheritance from PW2."""

    source_id = "nvml-gpu-set"

    _CHANNELS = (
        ("board_energy_total", "gpu_board_energy_total", "J", "cumulative_counter"),
        ("board_power", "gpu_board_power", "W", "gauge"),
        ("gpu_utilization", "gpu_utilization", "percent", "gauge"),
        (
            "memory_utilization",
            "gpu_memory_utilization",
            "percent",
            "gauge",
        ),
        ("temperature", "gpu_temperature", "degC", "gauge"),
        ("sm_clock", "gpu_sm_clock", "MHz", "gauge"),
        ("memory_clock", "gpu_memory_clock", "MHz", "gauge"),
    )

    def __init__(
        self,
        *,
        nominal_period_ns: int,
        targets: Sequence[GpuTarget] = (),
        cuda_indices: Sequence[int] = (),
        cuda_visible_devices: str | None = None,
        required_ancillary_metrics: Sequence[str] = (),
        clock_id: str = HOST_REFERENCE_CLOCK_ID,
        pynvml_module: Any | None = None,
        require_cuda_runtime_binding: bool = True,
    ) -> None:
        if nominal_period_ns <= 0:
            raise TelemetryConfigurationError(
                "NVML nominal period must be positive"
            )
        self.nominal_period_ns = nominal_period_ns
        self.targets = tuple(targets)
        self.cuda_indices = tuple(int(index) for index in cuda_indices)
        if self.targets and self.cuda_indices:
            raise TelemetryConfigurationError(
                "configure frozen GPU targets or discovery CUDA indices, not both"
            )
        if any(index < 0 for index in self.cuda_indices):
            raise TelemetryConfigurationError(
                "discovery CUDA indices cannot be negative"
            )
        if len(set(self.cuda_indices)) != len(self.cuda_indices):
            raise TelemetryConfigurationError(
                "duplicate discovery CUDA index"
            )
        if len({target.local_cuda_index for target in self.targets}) != len(
            self.targets
        ):
            raise TelemetryConfigurationError("duplicate local CUDA target index")
        if len({target.gpu_uuid for target in self.targets}) != len(self.targets):
            raise TelemetryConfigurationError("duplicate target GPU UUID")
        self.cuda_visible_devices = cuda_visible_devices
        self.required_ancillary_metrics = frozenset(required_ancillary_metrics)
        known_metrics = {item[1] for item in self._CHANNELS}
        unknown = self.required_ancillary_metrics - known_metrics
        if unknown:
            raise TelemetryConfigurationError(
                "unknown required NVML metric(s): " + ", ".join(sorted(unknown))
            )
        self.clock_id = clock_id
        self.require_cuda_runtime_binding = require_cuda_runtime_binding
        self._pynvml = pynvml_module
        self._owns_nvml = False
        self._bindings: tuple[tuple[GpuIdentity, Any], ...] = ()
        self._manifests = self._target_manifests()
        self._sample_sequence = _Sequencer()
        self._missing_sequence = _Sequencer()
        self._last_energy_mj: dict[str, int] = {}

    @property
    def identities(self) -> tuple[GpuIdentity, ...]:
        return tuple(identity for identity, _ in self._bindings)

    @property
    def manifests(self) -> tuple[ChannelManifest, ...]:
        return self._manifests

    def _target_manifests(self) -> tuple[ChannelManifest, ...]:
        manifests: list[ChannelManifest] = []
        for target in self.targets:
            manifests.extend(
                self._manifests_for_gpu(
                    gpu_uuid=target.gpu_uuid,
                    local_cuda_index=target.local_cuda_index,
                    nvml_index=None,
                    target_required=target.required,
                )
            )
        return tuple(manifests)

    def _manifests_for_gpu(
        self,
        *,
        gpu_uuid: str,
        local_cuda_index: int,
        nvml_index: int | None,
        target_required: bool,
    ) -> tuple[ChannelManifest, ...]:
        records: list[ChannelManifest] = []
        for suffix, metric, unit, sample_kind in self._CHANNELS:
            required = (
                target_required
                if metric == "gpu_board_energy_total"
                else metric in self.required_ancillary_metrics
            )
            records.append(
                ChannelManifest(
                    channel_id=_gpu_channel_id(gpu_uuid, suffix),
                    boundary=GPU_BOARD_BOUNDARY,
                    source_id=f"nvml:{gpu_uuid}",
                    metric=metric,
                    unit=unit,
                    sample_kind=sample_kind,
                    clock_id=self.clock_id,
                    nominal_period_ns=self.nominal_period_ns,
                    integration_window_ns=0,
                    uncertainty_ns=0,
                    required=required,
                    metadata={
                        "gpu_uuid": gpu_uuid,
                        "local_cuda_index": local_cuda_index,
                        "nvml_index": nvml_index,
                        "stable_identity_binding": (
                            "NVML UUID plus process-local CUDA index"
                        ),
                        "instantaneous_ancillary": metric
                        != "gpu_board_energy_total",
                    },
                )
            )
        return tuple(records)

    def _enumerate_physical(self) -> tuple[_PhysicalGpu, ...]:
        assert self._pynvml is not None
        pynvml = self._pynvml
        devices: list[_PhysicalGpu] = []
        for index in range(int(pynvml.nvmlDeviceGetCount())):
            handle = pynvml.nvmlDeviceGetHandleByIndex(index)
            pci = pynvml.nvmlDeviceGetPciInfo(handle)
            pci_bus_id = _decode_nvml_text(
                getattr(pci, "busId", getattr(pci, "busIdLegacy", ""))
            )
            devices.append(
                _PhysicalGpu(
                    nvml_index=index,
                    handle=handle,
                    gpu_uuid=_decode_nvml_text(
                        pynvml.nvmlDeviceGetUUID(handle)
                    ),
                    pci_bus_id=pci_bus_id,
                    name=_decode_nvml_text(pynvml.nvmlDeviceGetName(handle)),
                )
            )
        return tuple(devices)

    def _visible_physical(
        self, physical: Sequence[_PhysicalGpu]
    ) -> tuple[_PhysicalGpu, ...]:
        visible = self.cuda_visible_devices
        if visible is None:
            visible = os.environ.get("CUDA_VISIBLE_DEVICES")
        if visible is None:
            return tuple(physical)
        tokens = tuple(token.strip() for token in visible.split(",") if token.strip())
        if not tokens or tokens == ("-1",):
            return ()
        selected: list[_PhysicalGpu] = []
        for token in tokens:
            if token.upper().startswith("MIG-"):
                raise TelemetryBindingError(
                    "MIG CUDA visibility requires MIG-instance UUID discovery; "
                    "a physical-GPU binding would be ambiguous"
                )
            if token.isdecimal():
                matches = [gpu for gpu in physical if gpu.nvml_index == int(token)]
            else:
                matches = [
                    gpu
                    for gpu in physical
                    if gpu.gpu_uuid.lower().startswith(token.lower())
                ]
            if len(matches) != 1:
                raise TelemetryBindingError(
                    f"CUDA_VISIBLE_DEVICES token {token!r} matched "
                    f"{len(matches)} physical GPUs"
                )
            if matches[0] in selected:
                raise TelemetryBindingError(
                    f"CUDA_VISIBLE_DEVICES repeats GPU {matches[0].gpu_uuid}"
                )
            selected.append(matches[0])
        return tuple(selected)

    @staticmethod
    def _runtime_cuda_uuid(local_cuda_index: int) -> Any | None:
        try:
            torch = importlib.import_module("torch")
            if not bool(torch.cuda.is_available()):
                return None
            properties = torch.cuda.get_device_properties(local_cuda_index)
        except Exception:
            return None
        return getattr(properties, "uuid", None)

    def _verify_runtime_bindings(
        self, bindings: Sequence[tuple[GpuIdentity, Any]]
    ) -> None:
        if not self.require_cuda_runtime_binding:
            return
        for identity, _ in bindings:
            runtime_uuid = self._runtime_cuda_uuid(
                identity.local_cuda_index
            )
            if runtime_uuid is None:
                raise TelemetryBindingError(
                    "CUDA runtime did not expose a UUID for local index "
                    f"{identity.local_cuda_index}; NVML index order is not "
                    "accepted as a substitute"
                )
            if _normalized_gpu_uuid(runtime_uuid) != _normalized_gpu_uuid(
                identity.gpu_uuid
            ):
                raise TelemetryBindingError(
                    f"CUDA index {identity.local_cuda_index} UUID does not "
                    f"match NVML UUID {identity.gpu_uuid}"
                )

    def open(self) -> None:
        if self._bindings:
            return
        pynvml = self._pynvml
        if pynvml is None:
            try:
                pynvml = importlib.import_module("pynvml")
            except Exception as error:
                raise TelemetrySourceError("pynvml is unavailable") from error
            self._pynvml = pynvml
        try:
            pynvml.nvmlInit()
            self._owns_nvml = True
            physical = self._enumerate_physical()
            visible = self._visible_physical(physical)
            if self.targets:
                bindings: list[tuple[GpuIdentity, Any]] = []
                for target in self.targets:
                    if target.local_cuda_index >= len(visible):
                        raise TelemetryBindingError(
                            f"CUDA index {target.local_cuda_index} is not visible"
                        )
                    gpu = visible[target.local_cuda_index]
                    if gpu.gpu_uuid != target.gpu_uuid:
                        raise TelemetryBindingError(
                            f"CUDA index {target.local_cuda_index} resolved to "
                            f"{gpu.gpu_uuid}, expected {target.gpu_uuid}"
                        )
                    identity = GpuIdentity(
                        local_cuda_index=target.local_cuda_index,
                        nvml_index=gpu.nvml_index,
                        gpu_uuid=gpu.gpu_uuid,
                        pci_bus_id=gpu.pci_bus_id,
                        name=gpu.name,
                    )
                    bindings.append((identity, gpu.handle))
            elif self.cuda_indices:
                bindings = []
                for local_index in self.cuda_indices:
                    if local_index >= len(visible):
                        raise TelemetryBindingError(
                            f"CUDA index {local_index} is not visible"
                        )
                    gpu = visible[local_index]
                    bindings.append(
                        (
                            GpuIdentity(
                                local_cuda_index=local_index,
                                nvml_index=gpu.nvml_index,
                                gpu_uuid=gpu.gpu_uuid,
                                pci_bus_id=gpu.pci_bus_id,
                                name=gpu.name,
                            ),
                            gpu.handle,
                        )
                    )
            else:
                bindings = [
                    (
                        GpuIdentity(
                            local_cuda_index=local_index,
                            nvml_index=gpu.nvml_index,
                            gpu_uuid=gpu.gpu_uuid,
                            pci_bus_id=gpu.pci_bus_id,
                            name=gpu.name,
                        ),
                        gpu.handle,
                    )
                    for local_index, gpu in enumerate(visible)
                ]
            if not bindings:
                raise TelemetryBindingError("no CUDA-visible NVML GPU was bound")
            self._verify_runtime_bindings(bindings)
            self._bindings = tuple(bindings)
            target_required = {
                target.gpu_uuid: target.required for target in self.targets
            }
            self._manifests = tuple(
                manifest
                for identity, _ in self._bindings
                for manifest in self._manifests_for_gpu(
                    gpu_uuid=identity.gpu_uuid,
                    local_cuda_index=identity.local_cuda_index,
                    nvml_index=identity.nvml_index,
                    target_required=target_required.get(identity.gpu_uuid, True),
                )
            )
        except Exception:
            if self._owns_nvml:
                try:
                    pynvml.nvmlShutdown()
                finally:
                    self._owns_nvml = False
            raise

    def close(self) -> None:
        self._bindings = ()
        if self._owns_nvml and self._pynvml is not None:
            try:
                self._pynvml.nvmlShutdown()
            finally:
                self._owns_nvml = False

    def _capture(
        self,
        clock: HostReferenceClock,
        callback: Callable[[], Any],
    ) -> tuple[Any, _ObservationWindow]:
        reference_start = clock.now_reference_ns()
        value = callback()
        reference_end = clock.now_reference_ns()
        return value, _observation_window(clock, reference_start, reference_end)

    def _sample(
        self,
        manifest: ChannelManifest,
        value: int | float,
        window: _ObservationWindow,
        *,
        status: str = "observed",
        flags: tuple[str, ...] = (),
    ) -> TelemetrySample:
        return TelemetrySample(
            channel_id=manifest.channel_id,
            utc_interval_start_ns=window.utc_start_ns,
            utc_interval_end_ns=window.utc_end_ns,
            reference_interval_start_ns=window.reference_start_ns,
            reference_interval_end_ns=window.reference_end_ns,
            value=_finite_number(value, field_name=manifest.metric),
            sequence=self._sample_sequence.next(manifest.channel_id),
            quality=SampleQuality(
                status=status,
                uncertainty_ns=window.uncertainty_ns
                + manifest.uncertainty_ns,
                flags=flags,
            ),
        )

    def poll(self, clock: HostReferenceClock) -> SourcePollResult:
        if not self._bindings or self._pynvml is None:
            raise TelemetrySourceError("NVML source is not open")
        if clock.clock_id != self.clock_id:
            raise TelemetryConfigurationError(
                f"NVML manifests use {self.clock_id}, collector uses "
                f"{clock.clock_id}"
            )
        pynvml = self._pynvml
        manifest_by_id = {item.channel_id: item for item in self._manifests}
        samples: list[TelemetrySample] = []
        missing: list[MissingChannelRecord] = []

        def observe(
            identity: GpuIdentity,
            suffix: str,
            callback: Callable[[], Any],
            transform: Callable[[Any], int | float] = lambda value: value,
        ) -> tuple[Any, _ObservationWindow] | None:
            channel_id = _gpu_channel_id(identity.gpu_uuid, suffix)
            manifest = manifest_by_id[channel_id]
            try:
                raw, window = self._capture(clock, callback)
                value = transform(raw)
                samples.append(self._sample(manifest, value, window))
                return raw, window
            except Exception as error:
                missing.append(
                    _missing_record(
                        manifest,
                        clock,
                        self._missing_sequence,
                        reason_code=_reason_code(error),
                        detail=_exception_detail(error),
                    )
                )
                return None

        for identity, handle in self._bindings:
            energy_id = _gpu_channel_id(identity.gpu_uuid, "board_energy_total")
            energy_manifest = manifest_by_id[energy_id]
            try:
                energy_mj_raw, energy_window = self._capture(
                    clock,
                    lambda handle=handle: int(
                        pynvml.nvmlDeviceGetTotalEnergyConsumption(handle)
                    ),
                )
                energy_mj = int(energy_mj_raw)
                previous = self._last_energy_mj.get(identity.gpu_uuid)
                status = "observed"
                flags: tuple[str, ...] = ()
                if previous is not None and energy_mj < previous:
                    status = "counter_reset"
                    flags = ("counter_decreased",)
                self._last_energy_mj[identity.gpu_uuid] = energy_mj
                samples.append(
                    self._sample(
                        energy_manifest,
                        energy_mj / 1000.0,
                        energy_window,
                        status=status,
                        flags=flags,
                    )
                )
            except Exception as error:
                missing.append(
                    _missing_record(
                        energy_manifest,
                        clock,
                        self._missing_sequence,
                        reason_code=_reason_code(error),
                        detail=_exception_detail(error),
                    )
                )

            observe(
                identity,
                "board_power",
                lambda handle=handle: pynvml.nvmlDeviceGetPowerUsage(handle),
                lambda value: float(value) / 1000.0,
            )
            utilization_id = _gpu_channel_id(
                identity.gpu_uuid, "gpu_utilization"
            )
            memory_utilization_id = _gpu_channel_id(
                identity.gpu_uuid, "memory_utilization"
            )
            try:
                utilization, utilization_window = self._capture(
                    clock,
                    lambda handle=handle: pynvml.nvmlDeviceGetUtilizationRates(
                        handle
                    ),
                )
                samples.extend(
                    (
                        self._sample(
                            manifest_by_id[utilization_id],
                            int(utilization.gpu),
                            utilization_window,
                        ),
                        self._sample(
                            manifest_by_id[memory_utilization_id],
                            int(utilization.memory),
                            utilization_window,
                        ),
                    )
                )
            except Exception as error:
                for channel_id in (utilization_id, memory_utilization_id):
                    missing.append(
                        _missing_record(
                            manifest_by_id[channel_id],
                            clock,
                            self._missing_sequence,
                            reason_code=_reason_code(error),
                            detail=_exception_detail(error),
                        )
                    )
            observe(
                identity,
                "temperature",
                lambda handle=handle: pynvml.nvmlDeviceGetTemperature(
                    handle, pynvml.NVML_TEMPERATURE_GPU
                ),
                int,
            )
            observe(
                identity,
                "sm_clock",
                lambda handle=handle: pynvml.nvmlDeviceGetClockInfo(
                    handle, pynvml.NVML_CLOCK_SM
                ),
                int,
            )
            observe(
                identity,
                "memory_clock",
                lambda handle=handle: pynvml.nvmlDeviceGetClockInfo(
                    handle, pynvml.NVML_CLOCK_MEM
                ),
                int,
            )
        return SourcePollResult(
            samples=tuple(samples), missing_channels=tuple(missing)
        )


@dataclass(frozen=True)
class HttpAuthEnvironment:
    """Names of credential variables; resolved values are never retained."""

    bearer_token_env: str | None = None
    basic_username_env: str | None = None
    basic_password_env: str | None = None
    header_value_env: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.bearer_token_env and (
            self.basic_username_env or self.basic_password_env
        ):
            raise TelemetryConfigurationError(
                "bearer and basic authentication cannot both be configured"
            )
        if bool(self.basic_username_env) != bool(self.basic_password_env):
            raise TelemetryConfigurationError(
                "basic auth requires both username and password env names"
            )
        names = [
            name
            for name in (
                self.bearer_token_env,
                self.basic_username_env,
                self.basic_password_env,
                *self.header_value_env.values(),
            )
            if name is not None
        ]
        invalid = [name for name in names if not _ENV_NAME.fullmatch(name)]
        if invalid:
            raise TelemetryConfigurationError(
                "invalid credential environment name(s): "
                + ", ".join(invalid)
            )
        for header in self.header_value_env:
            if not header.strip() or "\n" in header or "\r" in header:
                raise TelemetryConfigurationError("invalid auth header name")

    def environment_names(self) -> tuple[str, ...]:
        return tuple(
            name
            for name in (
                self.bearer_token_env,
                self.basic_username_env,
                self.basic_password_env,
                *self.header_value_env.values(),
            )
            if name is not None
        )

    def resolved_headers(self) -> dict[str, str]:
        missing = [name for name in self.environment_names() if name not in os.environ]
        if missing:
            raise MissingCredentialEnvironment(missing)
        headers = {
            header: os.environ[env_name]
            for header, env_name in self.header_value_env.items()
        }
        if self.bearer_token_env:
            headers["Authorization"] = (
                "Bearer " + os.environ[self.bearer_token_env]
            )
        elif self.basic_username_env and self.basic_password_env:
            raw = (
                os.environ[self.basic_username_env]
                + ":"
                + os.environ[self.basic_password_env]
            ).encode("utf-8")
            headers["Authorization"] = (
                "Basic " + base64.b64encode(raw).decode("ascii")
            )
        return headers

    def to_dict(self) -> dict[str, Any]:
        return {
            "bearer_token_env": self.bearer_token_env,
            "basic_username_env": self.basic_username_env,
            "basic_password_env": self.basic_password_env,
            "header_value_env": dict(self.header_value_env),
        }


@dataclass(frozen=True)
class HttpEndpoint:
    url: str
    timeout_seconds: float = 5.0
    max_response_bytes: int = 8 * 1024 * 1024
    auth: HttpAuthEnvironment = field(default_factory=HttpAuthEnvironment)
    ca_file: str | None = None

    def __post_init__(self) -> None:
        parsed = urlsplit(self.url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise TelemetryConfigurationError(
                "telemetry endpoint must be an absolute HTTP(S) URL"
            )
        if parsed.username is not None or parsed.password is not None:
            raise TelemetryConfigurationError(
                "URL userinfo is forbidden; use authentication env names"
            )
        if self.timeout_seconds <= 0:
            raise TelemetryConfigurationError("HTTP timeout must be positive")
        if self.max_response_bytes <= 0:
            raise TelemetryConfigurationError(
                "HTTP response bound must be positive"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "timeout_seconds": self.timeout_seconds,
            "max_response_bytes": self.max_response_bytes,
            "auth_environment": self.auth.to_dict(),
            "ca_file": self.ca_file,
        }


def _url_with_query(url: str, additions: Mapping[str, str]) -> str:
    parsed = urlsplit(url)
    query = parse_qsl(parsed.query, keep_blank_values=True)
    query.extend(additions.items())
    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            urlencode(query),
            parsed.fragment,
        )
    )


def _http_get(
    endpoint: HttpEndpoint,
    clock: HostReferenceClock,
    *,
    query: Mapping[str, str] | None = None,
    accept: str = "application/json",
) -> tuple[bytes, _ObservationWindow]:
    headers = {"Accept": accept, **endpoint.auth.resolved_headers()}
    request = Request(
        _url_with_query(endpoint.url, query or {}),
        method="GET",
        headers=headers,
    )
    context = None
    if urlsplit(endpoint.url).scheme == "https":
        context = ssl.create_default_context(cafile=endpoint.ca_file)
    reference_start = clock.now_reference_ns()
    try:
        with urlopen(
            request,
            timeout=endpoint.timeout_seconds,
            context=context,
        ) as response:
            body = response.read(endpoint.max_response_bytes + 1)
    finally:
        reference_end = clock.now_reference_ns()
    if len(body) > endpoint.max_response_bytes:
        raise TelemetrySourceError("HTTP telemetry response exceeds byte bound")
    return body, _observation_window(clock, reference_start, reference_end)


JsonPathPart = str | int


def _json_path(value: Any, path: Sequence[JsonPathPart]) -> Any:
    current = value
    for part in path:
        if isinstance(part, int):
            if not isinstance(current, list):
                raise TelemetrySourceError(
                    f"JSON path expected list before index {part}"
                )
            current = current[part]
        else:
            if not isinstance(current, Mapping) or part not in current:
                raise TelemetrySourceError(
                    f"JSON path component {part!r} is absent"
                )
            current = current[part]
    return current


def _timestamp_ns(value: Any, unit: str) -> int:
    if unit == "iso8601":
        if not isinstance(value, str):
            raise TelemetrySourceError("ISO-8601 timestamp is not text")
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            raise TelemetrySourceError("ISO-8601 timestamp lacks timezone")
        return int(parsed.timestamp() * 1_000_000_000)
    numeric = _finite_number(value, field_name="source timestamp")
    scale = {
        "seconds": 1_000_000_000,
        "milliseconds": 1_000_000,
        "microseconds": 1_000,
        "nanoseconds": 1,
    }.get(unit)
    if scale is None:
        raise TelemetryConfigurationError(f"unsupported timestamp unit: {unit}")
    return int(float(numeric) * scale)


def _reported_utc_window(
    manifest: ChannelManifest,
    clock: HostReferenceClock,
    *,
    utc_end_ns: int,
    utc_start_ns: int | None = None,
) -> _ObservationWindow:
    start = (
        utc_start_ns
        if utc_start_ns is not None
        else utc_end_ns - manifest.integration_window_ns
    )
    reference_start, reference_end, uncertainty = (
        clock.utc_to_reference_interval(
            start,
            utc_end_ns,
            additional_uncertainty_ns=manifest.uncertainty_ns,
        )
    )
    return _ObservationWindow(
        reference_start_ns=reference_start,
        reference_end_ns=reference_end,
        utc_start_ns=start - manifest.uncertainty_ns,
        utc_end_ns=utc_end_ns + manifest.uncertainty_ns,
        uncertainty_ns=uncertainty,
    )


@dataclass(frozen=True)
class HttpJsonChannel:
    manifest: ChannelManifest
    value_path: tuple[JsonPathPart, ...]
    value_scale: float = 1.0
    timestamp_path: tuple[JsonPathPart, ...] | None = None
    interval_start_path: tuple[JsonPathPart, ...] | None = None
    interval_end_path: tuple[JsonPathPart, ...] | None = None
    timestamp_unit: str = "seconds"

    def __post_init__(self) -> None:
        if not math.isfinite(self.value_scale):
            raise TelemetryConfigurationError("HTTP value scale is not finite")
        has_interval = (
            self.interval_start_path is not None
            or self.interval_end_path is not None
        )
        if has_interval and (
            self.interval_start_path is None or self.interval_end_path is None
        ):
            raise TelemetryConfigurationError(
                "source intervals require both start and end JSON paths"
            )
        if has_interval and self.timestamp_path is not None:
            raise TelemetryConfigurationError(
                "configure a source timestamp or a source interval, not both"
            )
        if (has_interval or self.timestamp_path is not None) and (
            self.manifest.clock_id != UTC_CLOCK_ID
        ):
            raise TelemetryConfigurationError(
                "JSON epoch/ISO timestamps must declare clock_id='utc'; "
                "non-UTC source clocks require an explicit offset adapter"
            )


class HttpJsonTelemetrySource:
    """Ingest directly metered PDU, storage-power, or cooling JSON channels."""

    def __init__(
        self,
        *,
        source_id: str,
        endpoint: HttpEndpoint,
        channels: Sequence[HttpJsonChannel],
    ) -> None:
        if not source_id.strip():
            raise TelemetryConfigurationError("HTTP source_id cannot be empty")
        self.source_id = source_id
        self.endpoint = endpoint
        self.channels = tuple(channels)
        self._manifests = tuple(channel.manifest for channel in self.channels)
        if any(item.source_id != source_id for item in self._manifests):
            raise TelemetryConfigurationError(
                "HTTP channel source_id does not match its source"
            )
        if len({item.channel_id for item in self._manifests}) != len(
            self._manifests
        ):
            raise TelemetryConfigurationError("duplicate HTTP channel ID")
        self._sample_sequence = _Sequencer()
        self._missing_sequence = _Sequencer()

    @property
    def manifests(self) -> tuple[ChannelManifest, ...]:
        return self._manifests

    def open(self) -> None:
        return None

    def close(self) -> None:
        return None

    def poll(self, clock: HostReferenceClock) -> SourcePollResult:
        try:
            body, request_window = _http_get(self.endpoint, clock)
            payload = json.loads(body.decode("utf-8"))
        except Exception as error:
            missing = tuple(
                _missing_record(
                    manifest,
                    clock,
                    self._missing_sequence,
                    reason_code=_reason_code(error),
                    detail=_exception_detail(error),
                )
                for manifest in self._manifests
            )
            return SourcePollResult(missing_channels=missing)

        samples: list[TelemetrySample] = []
        missing: list[MissingChannelRecord] = []
        for channel in self.channels:
            manifest = channel.manifest
            try:
                raw_value = _json_path(payload, channel.value_path)
                numeric = _finite_number(raw_value, field_name=manifest.metric)
                value = float(numeric) * channel.value_scale
                if channel.interval_start_path is not None:
                    start = _timestamp_ns(
                        _json_path(payload, channel.interval_start_path),
                        channel.timestamp_unit,
                    )
                    assert channel.interval_end_path is not None
                    end = _timestamp_ns(
                        _json_path(payload, channel.interval_end_path),
                        channel.timestamp_unit,
                    )
                    window = _reported_utc_window(
                        manifest, clock, utc_start_ns=start, utc_end_ns=end
                    )
                    flags = ("source_reported_utc_interval",)
                elif channel.timestamp_path is not None:
                    end = _timestamp_ns(
                        _json_path(payload, channel.timestamp_path),
                        channel.timestamp_unit,
                    )
                    window = _reported_utc_window(
                        manifest, clock, utc_end_ns=end
                    )
                    flags = ("source_reported_utc_timestamp",)
                else:
                    if manifest.clock_id != clock.clock_id:
                        raise TelemetryConfigurationError(
                            "receipt-timed HTTP channels must use the host "
                            "reference clock"
                        )
                    window = _observation_window(
                        clock,
                        request_window.reference_start_ns,
                        request_window.reference_end_ns,
                        additional_uncertainty_ns=manifest.uncertainty_ns,
                    )
                    flags = ("http_request_interval",)
                samples.append(
                    TelemetrySample(
                        channel_id=manifest.channel_id,
                        utc_interval_start_ns=window.utc_start_ns,
                        utc_interval_end_ns=window.utc_end_ns,
                        reference_interval_start_ns=window.reference_start_ns,
                        reference_interval_end_ns=window.reference_end_ns,
                        value=value,
                        sequence=self._sample_sequence.next(
                            manifest.channel_id
                        ),
                        quality=SampleQuality(
                            status="observed",
                            uncertainty_ns=window.uncertainty_ns,
                            flags=flags,
                        ),
                    )
                )
            except Exception as error:
                missing.append(
                    _missing_record(
                        manifest,
                        clock,
                        self._missing_sequence,
                        reason_code=_reason_code(error),
                        detail=_exception_detail(error),
                    )
                )
        return SourcePollResult(
            samples=tuple(samples), missing_channels=tuple(missing)
        )


@dataclass(frozen=True)
class PrometheusQueryChannel:
    manifest: ChannelManifest
    query: str
    expected_labels: Mapping[str, str] = field(default_factory=dict)
    value_scale: float = 1.0
    max_staleness_ns: int | None = None

    def __post_init__(self) -> None:
        if not self.query.strip():
            raise TelemetryConfigurationError("Prometheus query cannot be empty")
        if self.manifest.clock_id != UTC_CLOCK_ID:
            raise TelemetryConfigurationError(
                "Prometheus result timestamps must declare clock_id='utc'"
            )
        if not math.isfinite(self.value_scale):
            raise TelemetryConfigurationError(
                "Prometheus value scale is not finite"
            )
        if self.max_staleness_ns is not None and self.max_staleness_ns < 0:
            raise TelemetryConfigurationError(
                "Prometheus staleness limit cannot be negative"
            )


def _prometheus_value(
    payload: Any, expected_labels: Mapping[str, str]
) -> tuple[int, float]:
    if not isinstance(payload, Mapping) or payload.get("status") != "success":
        raise TelemetrySourceError("Prometheus API response is not successful")
    data = payload.get("data")
    if not isinstance(data, Mapping):
        raise TelemetrySourceError("Prometheus API data is absent")
    result_type = data.get("resultType")
    result = data.get("result")
    if result_type == "scalar":
        candidates = [({}, result)]
    elif result_type == "vector" and isinstance(result, list):
        candidates = [
            (item.get("metric", {}), item.get("value"))
            for item in result
            if isinstance(item, Mapping)
        ]
    else:
        raise TelemetrySourceError(
            f"Prometheus instant query returned unsupported {result_type!r}"
        )
    matches = [
        value
        for labels, value in candidates
        if isinstance(labels, Mapping)
        and all(str(labels.get(key)) == expected for key, expected in expected_labels.items())
    ]
    if len(matches) != 1:
        raise TelemetrySourceError(
            "Prometheus query must resolve to exactly one observed series; "
            f"resolved {len(matches)}"
        )
    pair = matches[0]
    if not isinstance(pair, (list, tuple)) or len(pair) != 2:
        raise TelemetrySourceError("Prometheus sample pair is malformed")
    timestamp = _timestamp_ns(pair[0], "seconds")
    try:
        value = float(pair[1])
    except (TypeError, ValueError) as error:
        raise TelemetrySourceError("Prometheus sample is not numeric") from error
    _finite_number(value, field_name="Prometheus sample")
    return timestamp, value


class PrometheusTelemetrySource:
    """Ingest scalar PromQL results without implicit series reduction."""

    def __init__(
        self,
        *,
        source_id: str,
        endpoint: HttpEndpoint,
        channels: Sequence[PrometheusQueryChannel],
    ) -> None:
        if not source_id.strip():
            raise TelemetryConfigurationError(
                "Prometheus source_id cannot be empty"
            )
        self.source_id = source_id
        self.endpoint = endpoint
        self.channels = tuple(channels)
        self._manifests = tuple(channel.manifest for channel in self.channels)
        if any(item.source_id != source_id for item in self._manifests):
            raise TelemetryConfigurationError(
                "Prometheus channel source_id does not match its source"
            )
        if len({item.channel_id for item in self._manifests}) != len(
            self._manifests
        ):
            raise TelemetryConfigurationError("duplicate Prometheus channel ID")
        self._sample_sequence = _Sequencer()
        self._missing_sequence = _Sequencer()

    @property
    def manifests(self) -> tuple[ChannelManifest, ...]:
        return self._manifests

    def open(self) -> None:
        return None

    def close(self) -> None:
        return None

    def poll(self, clock: HostReferenceClock) -> SourcePollResult:
        samples: list[TelemetrySample] = []
        missing: list[MissingChannelRecord] = []
        for channel in self.channels:
            manifest = channel.manifest
            try:
                body, request_window = _http_get(
                    self.endpoint,
                    clock,
                    query={
                        "query": channel.query,
                        "time": str(time.time_ns() / 1_000_000_000),
                    },
                )
                payload = json.loads(body.decode("utf-8"))
                utc_end, raw_value = _prometheus_value(
                    payload, channel.expected_labels
                )
                window = _reported_utc_window(
                    manifest, clock, utc_end_ns=utc_end
                )
                request_midpoint_utc = request_window.utc_start_ns + (
                    request_window.utc_end_ns - request_window.utc_start_ns
                ) // 2
                age_ns = request_midpoint_utc - utc_end
                status = "observed"
                flags: tuple[str, ...] = ("prometheus_source_timestamp",)
                if (
                    channel.max_staleness_ns is not None
                    and age_ns > channel.max_staleness_ns
                ):
                    status = "stale"
                    flags += ("staleness_limit_exceeded",)
                elif age_ns < -manifest.uncertainty_ns:
                    status = "clock_uncertain"
                    flags += ("source_timestamp_in_future",)
                samples.append(
                    TelemetrySample(
                        channel_id=manifest.channel_id,
                        utc_interval_start_ns=window.utc_start_ns,
                        utc_interval_end_ns=window.utc_end_ns,
                        reference_interval_start_ns=window.reference_start_ns,
                        reference_interval_end_ns=window.reference_end_ns,
                        value=raw_value * channel.value_scale,
                        sequence=self._sample_sequence.next(
                            manifest.channel_id
                        ),
                        quality=SampleQuality(
                            status=status,
                            uncertainty_ns=window.uncertainty_ns,
                            flags=flags,
                        ),
                    )
                )
            except Exception as error:
                missing.append(
                    _missing_record(
                        manifest,
                        clock,
                        self._missing_sequence,
                        reason_code=_reason_code(error),
                        detail=_exception_detail(error),
                    )
                )
        return SourcePollResult(
            samples=tuple(samples), missing_channels=tuple(missing)
        )


@dataclass(frozen=True)
class ProcDiskTarget:
    device: str
    required_activity: bool = True

    def __post_init__(self) -> None:
        if not self.device.strip() or any(character.isspace() for character in self.device):
            raise TelemetryConfigurationError("invalid /proc disk device name")


class ProcDiskStatsSource:
    """Read Linux storage activity counters, never estimate storage power.

    Linux defines the sector counters in ``/proc/diskstats`` in 512-byte
    sectors.  The resulting byte counters are observed activity only.  This
    source intentionally exposes no watts or joules channel; storage power must
    come from a separately configured physical meter or exporter.
    """

    source_id = "linux:/proc/diskstats"
    _SECTOR_BYTES = 512
    _METRICS = (
        (
            "read_bytes_total",
            "storage_read_bytes_total",
            "byte",
            2,
            "cumulative_counter",
            _SECTOR_BYTES,
        ),
        (
            "write_bytes_total",
            "storage_write_bytes_total",
            "byte",
            6,
            "cumulative_counter",
            _SECTOR_BYTES,
        ),
        (
            "read_operations_total",
            "storage_read_operations_total",
            "operation",
            0,
            "cumulative_counter",
            1,
        ),
        (
            "write_operations_total",
            "storage_write_operations_total",
            "operation",
            4,
            "cumulative_counter",
            1,
        ),
        (
            "io_time_total",
            "storage_io_time_total",
            "ms",
            9,
            "cumulative_counter",
            1,
        ),
        (
            "queue_depth",
            "storage_queue_depth",
            "operation",
            8,
            "gauge",
            1,
        ),
    )

    def __init__(
        self,
        *,
        targets: Sequence[ProcDiskTarget],
        nominal_period_ns: int,
        proc_path: str | Path = "/proc/diskstats",
        clock_id: str = HOST_REFERENCE_CLOCK_ID,
        source_id: str = "linux:/proc/diskstats",
    ) -> None:
        if nominal_period_ns <= 0:
            raise TelemetryConfigurationError(
                "/proc nominal period must be positive"
            )
        self.targets = tuple(targets)
        if len({target.device for target in self.targets}) != len(self.targets):
            raise TelemetryConfigurationError("duplicate /proc disk target")
        self.nominal_period_ns = nominal_period_ns
        self.proc_path = Path(proc_path)
        self.clock_id = clock_id
        if not source_id.strip():
            raise TelemetryConfigurationError(
                "/proc source_id cannot be empty"
            )
        self.source_id = source_id
        self._sample_sequence = _Sequencer()
        self._missing_sequence = _Sequencer()
        self._last_values: dict[str, int] = {}
        self._manifests = tuple(
            ChannelManifest(
                channel_id=f"storage.{target.device}.{suffix}",
                boundary=STORAGE_ACTIVITY_BOUNDARY,
                source_id=f"{self.source_id}:{target.device}",
                metric=metric,
                unit=unit,
                sample_kind=sample_kind,
                clock_id=self.clock_id,
                nominal_period_ns=self.nominal_period_ns,
                integration_window_ns=0,
                uncertainty_ns=0,
                required=target.required_activity,
                metadata={
                    "device": target.device,
                    "activity_only": True,
                    "power_inferred": False,
                },
            )
            for target in self.targets
            for suffix, metric, unit, _, sample_kind, _ in self._METRICS
        )

    @property
    def manifests(self) -> tuple[ChannelManifest, ...]:
        return self._manifests

    def open(self) -> None:
        if not sys.platform.startswith("linux"):
            raise TelemetrySourceError(
                "/proc/diskstats storage activity requires Linux"
            )
        if not self.proc_path.is_file():
            raise FileNotFoundError(self.proc_path)

    def close(self) -> None:
        return None

    def poll(self, clock: HostReferenceClock) -> SourcePollResult:
        if clock.clock_id != self.clock_id:
            raise TelemetryConfigurationError(
                f"/proc manifests use {self.clock_id}, collector uses "
                f"{clock.clock_id}"
            )
        reference_start = clock.now_reference_ns()
        text = self.proc_path.read_text(encoding="utf-8")
        reference_end = clock.now_reference_ns()
        window = _observation_window(clock, reference_start, reference_end)
        rows: dict[str, tuple[int, ...]] = {}
        for line in text.splitlines():
            fields = line.split()
            if len(fields) < 14:
                continue
            try:
                rows[fields[2]] = tuple(int(value) for value in fields[3:])
            except ValueError:
                continue
        manifest_by_id = {item.channel_id: item for item in self._manifests}
        samples: list[TelemetrySample] = []
        missing: list[MissingChannelRecord] = []
        for target in self.targets:
            row = rows.get(target.device)
            if row is None:
                for suffix, _, _, _, _, _ in self._METRICS:
                    manifest = manifest_by_id[
                        f"storage.{target.device}.{suffix}"
                    ]
                    missing.append(
                        _missing_record(
                            manifest,
                            clock,
                            self._missing_sequence,
                            reason_code="device_not_present",
                            detail=(
                                f"device {target.device!r} is absent from "
                                "/proc/diskstats"
                            ),
                        )
                    )
                continue
            for (
                suffix,
                _,
                _,
                field_index,
                sample_kind,
                multiplier,
            ) in self._METRICS:
                manifest = manifest_by_id[f"storage.{target.device}.{suffix}"]
                raw = row[field_index]
                value = raw * multiplier
                previous = self._last_values.get(manifest.channel_id)
                status = "observed"
                flags: tuple[str, ...] = ()
                if (
                    sample_kind == "cumulative_counter"
                    and previous is not None
                    and value < previous
                ):
                    status = "counter_reset"
                    flags = ("counter_decreased",)
                self._last_values[manifest.channel_id] = value
                samples.append(
                    TelemetrySample(
                        channel_id=manifest.channel_id,
                        utc_interval_start_ns=window.utc_start_ns,
                        utc_interval_end_ns=window.utc_end_ns,
                        reference_interval_start_ns=window.reference_start_ns,
                        reference_interval_end_ns=window.reference_end_ns,
                        value=value,
                        sequence=self._sample_sequence.next(
                            manifest.channel_id
                        ),
                        quality=SampleQuality(
                            status=status,
                            uncertainty_ns=window.uncertainty_ns,
                            flags=flags,
                        ),
                    )
                )
        return SourcePollResult(
            samples=tuple(samples), missing_channels=tuple(missing)
        )


class TelemetrySource(Protocol):
    source_id: str

    @property
    def manifests(self) -> tuple[ChannelManifest, ...]: ...

    def open(self) -> None: ...

    def close(self) -> None: ...

    def poll(self, clock: HostReferenceClock) -> SourcePollResult: ...


class TelemetryCollector:
    """Align sources and prove channel availability without imputation."""

    def __init__(
        self,
        sources: Sequence[TelemetrySource],
        *,
        clock: HostReferenceClock | None = None,
        clock_recalibration_period_ns: int = 60_000_000_000,
    ) -> None:
        if clock_recalibration_period_ns <= 0:
            raise TelemetryConfigurationError(
                "clock recalibration period must be positive"
            )
        self.sources = tuple(sources)
        if len({source.source_id for source in self.sources}) != len(self.sources):
            raise TelemetryConfigurationError("duplicate telemetry source_id")
        self.clock = clock or HostReferenceClock()
        self.clock_recalibration_period_ns = clock_recalibration_period_ns
        self._opened = False
        self._open_errors: dict[str, BaseException] = {}
        self._missing_sequence = _Sequencer()
        self._last_clock_calibration_reference_ns: int | None = None
        self._pending_clock_record: ClockOffsetRecord | None = None
        self._manifests: tuple[ChannelManifest, ...] = ()

    @property
    def manifests(self) -> tuple[ChannelManifest, ...]:
        return self._manifests

    def open(self) -> tuple[ChannelManifest, ...]:
        if self._opened:
            return self._manifests
        self._pending_clock_record = self.clock.calibrate()
        self._last_clock_calibration_reference_ns = self.clock.now_reference_ns()
        manifests: list[ChannelManifest] = []
        for source in self.sources:
            try:
                source.open()
            except Exception as error:
                self._open_errors[source.source_id] = error
            manifests.extend(source.manifests)
        duplicates = sorted(
            channel_id
            for channel_id in {item.channel_id for item in manifests}
            if sum(item.channel_id == channel_id for item in manifests) > 1
        )
        if duplicates:
            for source in reversed(self.sources):
                try:
                    source.close()
                except Exception:
                    pass
            raise TelemetryConfigurationError(
                "duplicate channel ID(s): " + ", ".join(duplicates)
            )
        self._manifests = tuple(manifests)
        self._opened = True
        return self._manifests

    def close(self) -> None:
        errors: list[str] = []
        for source in reversed(self.sources):
            try:
                source.close()
            except Exception as error:
                errors.append(f"{source.source_id}: {_exception_detail(error)}")
        self._opened = False
        if errors:
            raise TelemetrySourceError(
                "telemetry source close failure(s): " + "; ".join(errors)
            )

    def _clock_records_if_due(self) -> tuple[ClockOffsetRecord, ...]:
        records: list[ClockOffsetRecord] = []
        if self._pending_clock_record is not None:
            records.append(self._pending_clock_record)
            self._pending_clock_record = None
        now = self.clock.now_reference_ns()
        if (
            self._last_clock_calibration_reference_ns is None
            or now - self._last_clock_calibration_reference_ns
            >= self.clock_recalibration_period_ns
        ):
            records.append(self.clock.calibrate())
            self._last_clock_calibration_reference_ns = now
        return tuple(records)

    def poll_once(self) -> TelemetryBatch:
        if not self._opened:
            raise TelemetrySourceError("telemetry collector is not open")
        samples: list[TelemetrySample] = []
        missing: list[MissingChannelRecord] = []
        clocks = list(self._clock_records_if_due())
        diagnostics: list[SourceDiagnostic] = []
        for source in self.sources:
            source_manifests = {item.channel_id: item for item in source.manifests}
            error = self._open_errors.get(source.source_id)
            if error is None:
                try:
                    result = source.poll(self.clock)
                except Exception as poll_error:
                    error = poll_error
                else:
                    unknown_samples = sorted(
                        sample.channel_id
                        for sample in result.samples
                        if sample.channel_id not in source_manifests
                    )
                    if unknown_samples:
                        error = TelemetryConfigurationError(
                            "source returned undeclared channel(s): "
                            + ", ".join(unknown_samples)
                        )
                    else:
                        samples.extend(result.samples)
                        missing.extend(result.missing_channels)
                        clocks.extend(result.clock_offsets)
                        diagnostics.extend(result.diagnostics)
            if error is not None:
                reference_ns = self.clock.now_reference_ns()
                utc_start, utc_end, _ = self.clock.reference_to_utc_interval(
                    reference_ns, reference_ns
                )
                diagnostics.append(
                    SourceDiagnostic(
                        source_id=source.source_id,
                        utc_observed_ns=utc_start + (utc_end - utc_start) // 2,
                        reference_observed_ns=reference_ns,
                        status="unavailable",
                        detail=_exception_detail(error),
                    )
                )
                missing.extend(
                    _missing_record(
                        manifest,
                        self.clock,
                        self._missing_sequence,
                        reason_code=_reason_code(error),
                        detail=_exception_detail(error),
                    )
                    for manifest in source_manifests.values()
                )

        sample_ids = {sample.channel_id for sample in samples}
        already_missing = {record.channel_id for record in missing}
        for manifest in self._manifests:
            if (
                manifest.channel_id not in sample_ids
                and manifest.channel_id not in already_missing
            ):
                missing.append(
                    _missing_record(
                        manifest,
                        self.clock,
                        self._missing_sequence,
                        reason_code="not_observed_in_poll",
                        detail="source returned neither a sample nor an error",
                    )
                )
        duplicates = sorted(
            channel_id
            for channel_id in sample_ids
            if sum(sample.channel_id == channel_id for sample in samples) > 1
        )
        if duplicates:
            raise TelemetryConfigurationError(
                "multiple samples for a channel in one poll: "
                + ", ".join(duplicates)
            )
        return TelemetryBatch(
            samples=tuple(samples),
            missing_channels=tuple(missing),
            clock_offsets=tuple(clocks),
            diagnostics=tuple(diagnostics),
        )


@dataclass(frozen=True)
class ChunkDescriptor:
    path: str
    chunk_index: int
    record_count: int
    content_bytes: int
    content_sha256: str
    previous_chunk_content_sha256: str | None
    file_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "chunk_index": self.chunk_index,
            "record_count": self.record_count,
            "content_bytes": self.content_bytes,
            "content_sha256": self.content_sha256,
            "previous_chunk_content_sha256": (
                self.previous_chunk_content_sha256
            ),
            "file_bytes": self.file_bytes,
        }


def inspect_jsonl_chunk(path: str | Path) -> ChunkDescriptor:
    """Verify and describe one finalized JSONL chunk."""

    chunk_path = Path(path)
    lines = chunk_path.read_bytes().splitlines(keepends=True)
    if len(lines) < 2 or any(not line.endswith(b"\n") for line in lines):
        raise TelemetrySourceError(f"incomplete JSONL chunk: {chunk_path}")
    try:
        header = json.loads(lines[0])
        trailer = json.loads(lines[-1])
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise TelemetrySourceError(
            f"invalid JSONL chunk envelope: {chunk_path}"
        ) from error
    if (
        header.get("record_type") != "chunk_header"
        or trailer.get("record_type") != "chunk_footer"
        or header.get("schema") != CHUNK_SCHEMA
        or trailer.get("schema") != CHUNK_SCHEMA
    ):
        raise TelemetrySourceError(f"invalid JSONL chunk schema: {chunk_path}")
    content = b"".join(lines[:-1])
    digest = hashlib.sha256(content).hexdigest()
    record_count = len(lines) - 2
    if digest != trailer.get("content_sha256"):
        raise TelemetrySourceError(f"JSONL content hash mismatch: {chunk_path}")
    if len(content) != int(trailer.get("content_bytes", -1)):
        raise TelemetrySourceError(f"JSONL content byte mismatch: {chunk_path}")
    if record_count != int(trailer.get("record_count", -1)):
        raise TelemetrySourceError(f"JSONL record count mismatch: {chunk_path}")
    if header.get("chunk_index") != trailer.get("chunk_index"):
        raise TelemetrySourceError(f"JSONL chunk index mismatch: {chunk_path}")
    return ChunkDescriptor(
        path=str(chunk_path),
        chunk_index=int(header["chunk_index"]),
        record_count=record_count,
        content_bytes=len(content),
        content_sha256=digest,
        previous_chunk_content_sha256=header.get(
            "previous_chunk_content_sha256"
        ),
        file_bytes=chunk_path.stat().st_size,
    )


class ChunkedJsonlWriter:
    """Write atomic, hash-chained JSONL chunks with exact content digests."""

    def __init__(
        self,
        output_directory: str | Path,
        *,
        stream_id: str,
        max_records_per_chunk: int = 100_000,
        max_content_bytes_per_chunk: int = 64 * 1024 * 1024,
        resume: bool = False,
    ) -> None:
        if not _STREAM_ID.fullmatch(stream_id):
            raise TelemetryConfigurationError("invalid JSONL stream_id")
        if max_records_per_chunk <= 0 or max_content_bytes_per_chunk <= 0:
            raise TelemetryConfigurationError(
                "JSONL chunk limits must be positive"
            )
        self.output_directory = Path(output_directory)
        self.stream_id = stream_id
        self.max_records_per_chunk = max_records_per_chunk
        self.max_content_bytes_per_chunk = max_content_bytes_per_chunk
        self.output_directory.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._chunk_index = 0
        self._previous_hash: str | None = None
        self._file: Any | None = None
        self._part_path: Path | None = None
        self._final_path: Path | None = None
        self._hasher: Any | None = None
        self._content_bytes = 0
        self._record_count = 0
        self._closed = False
        self._descriptors: list[ChunkDescriptor] = []
        existing = sorted(
            self.output_directory.glob(f"{self.stream_id}-[0-9]*.jsonl")
        )
        parts = sorted(
            self.output_directory.glob(f"{self.stream_id}-[0-9]*.jsonl.part")
        )
        if parts:
            raise TelemetryConfigurationError(
                "unfinished JSONL chunk(s) require explicit operator recovery: "
                + ", ".join(str(path) for path in parts)
            )
        if existing and not resume:
            raise TelemetryConfigurationError(
                "JSONL stream already exists; pass resume=True after preserving it"
            )
        if resume:
            previous: str | None = None
            expected_index = 0
            for path in existing:
                descriptor = inspect_jsonl_chunk(path)
                if descriptor.chunk_index != expected_index:
                    raise TelemetryConfigurationError(
                        "existing JSONL chunk sequence is not contiguous"
                    )
                if descriptor.previous_chunk_content_sha256 != previous:
                    raise TelemetryConfigurationError(
                        "existing JSONL chunk hash chain is broken"
                    )
                self._descriptors.append(descriptor)
                previous = descriptor.content_sha256
                expected_index += 1
            self._chunk_index = expected_index
            self._previous_hash = previous

    @property
    def descriptors(self) -> tuple[ChunkDescriptor, ...]:
        with self._lock:
            return tuple(self._descriptors)

    def _open_chunk_locked(self) -> None:
        final_path = self.output_directory / (
            f"{self.stream_id}-{self._chunk_index:06d}.jsonl"
        )
        part_path = Path(str(final_path) + ".part")
        if final_path.exists() or part_path.exists():
            raise TelemetryConfigurationError(
                f"refusing to overwrite telemetry chunk {final_path}"
            )
        file_handle = part_path.open("xb")
        self._file = file_handle
        self._part_path = part_path
        self._final_path = final_path
        self._hasher = hashlib.sha256()
        self._content_bytes = 0
        self._record_count = 0
        header = {
            "record_type": "chunk_header",
            "schema": CHUNK_SCHEMA,
            "engine_id": ENGINE_ID,
            "stream_id": self.stream_id,
            "chunk_index": self._chunk_index,
            "previous_chunk_content_sha256": self._previous_hash,
            "opened_at_utc": _utc_iso(time.time_ns()),
            "hash_scope": "exact UTF-8 header and data-record bytes, excluding footer",
        }
        line = _canonical_line(header)
        file_handle.write(line)
        self._hasher.update(line)
        self._content_bytes += len(line)

    def _finalize_locked(self) -> ChunkDescriptor | None:
        if self._file is None:
            return None
        assert self._hasher is not None
        assert self._part_path is not None and self._final_path is not None
        digest = self._hasher.hexdigest()
        footer = {
            "record_type": "chunk_footer",
            "schema": CHUNK_SCHEMA,
            "stream_id": self.stream_id,
            "chunk_index": self._chunk_index,
            "record_count": self._record_count,
            "content_bytes": self._content_bytes,
            "content_sha256": digest,
            "previous_chunk_content_sha256": self._previous_hash,
            "closed_at_utc": _utc_iso(time.time_ns()),
        }
        self._file.write(_canonical_line(footer))
        self._file.flush()
        os.fsync(self._file.fileno())
        self._file.close()
        os.replace(self._part_path, self._final_path)
        descriptor = ChunkDescriptor(
            path=str(self._final_path),
            chunk_index=self._chunk_index,
            record_count=self._record_count,
            content_bytes=self._content_bytes,
            content_sha256=digest,
            previous_chunk_content_sha256=self._previous_hash,
            file_bytes=self._final_path.stat().st_size,
        )
        self._descriptors.append(descriptor)
        self._previous_hash = digest
        self._chunk_index += 1
        self._file = None
        self._part_path = None
        self._final_path = None
        self._hasher = None
        self._content_bytes = 0
        self._record_count = 0
        return descriptor

    def write(self, record: Mapping[str, Any]) -> None:
        line = _canonical_line(record)
        with self._lock:
            if self._closed:
                raise TelemetrySourceError("JSONL writer is closed")
            if self._file is None:
                self._open_chunk_locked()
            if self._record_count > 0 and (
                self._record_count >= self.max_records_per_chunk
                or self._content_bytes + len(line)
                > self.max_content_bytes_per_chunk
            ):
                self._finalize_locked()
                self._open_chunk_locked()
            assert self._file is not None and self._hasher is not None
            self._file.write(line)
            self._hasher.update(line)
            self._content_bytes += len(line)
            self._record_count += 1

    def flush_chunk(self) -> ChunkDescriptor | None:
        with self._lock:
            if self._closed:
                raise TelemetrySourceError("JSONL writer is closed")
            return self._finalize_locked()

    def close(self) -> tuple[ChunkDescriptor, ...]:
        with self._lock:
            if not self._closed:
                self._finalize_locked()
                self._closed = True
            return tuple(self._descriptors)

    def __enter__(self) -> "ChunkedJsonlWriter":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()


class TelemetryRecorder:
    """Persist a collector session while keeping validity failures visible."""

    def __init__(
        self,
        collector: TelemetryCollector,
        writer: ChunkedJsonlWriter,
        *,
        session_id: str,
        run_id: str,
    ) -> None:
        if not session_id.strip() or not run_id.strip():
            raise TelemetryConfigurationError(
                "telemetry session_id and run_id are required"
            )
        self.collector = collector
        self.writer = writer
        self.session_id = session_id
        self.run_id = run_id
        self._started = False
        self._closed = False

    def start(self) -> tuple[ChannelManifest, ...]:
        if self._started:
            return self.collector.manifests
        manifests = self.collector.open()
        self.writer.write(
            {
                "record_type": "session",
                "schema": SESSION_SCHEMA,
                "engine_id": ENGINE_ID,
                "session_id": self.session_id,
                "run_id": self.run_id,
                "opened_at_utc": _utc_iso(time.time_ns()),
                "reference_clock_id": self.collector.clock.clock_id,
                "value_policy": "observed-only; missing required channels are not modeled",
            }
        )
        for manifest in manifests:
            self.writer.write(manifest.to_record())
        self._started = True
        return manifests

    def poll_once(self, *, require_complete: bool = False) -> TelemetryBatch:
        if not self._started:
            self.start()
        batch = self.collector.poll_once()
        for clock_record in batch.clock_offsets:
            self.writer.write(clock_record.to_record())
        for diagnostic in batch.diagnostics:
            self.writer.write(diagnostic.to_record())
        for sample in batch.samples:
            self.writer.write(sample.to_record())
        for missing in batch.missing_channels:
            self.writer.write(missing.to_record())
        self.writer.write(
            {
                "record_type": "availability",
                "session_id": self.session_id,
                "run_id": self.run_id,
                "observed_channel_count": len(batch.samples),
                "missing_channel_count": len(batch.missing_channels),
                "missing_required_channel_ids": sorted(
                    {
                        record.channel_id
                        for record in batch.missing_required_channels
                    }
                ),
                "modeled_substitution_count": 0,
            }
        )
        if require_complete:
            batch.require_complete()
        return batch

    def run_until(
        self,
        stop_event: threading.Event,
        *,
        poll_period_ns: int,
        require_complete: bool = False,
    ) -> None:
        if poll_period_ns <= 0:
            raise TelemetryConfigurationError("poll period must be positive")
        if not self._started:
            self.start()
        next_poll = self.collector.clock.now_reference_ns()
        while not stop_event.is_set():
            self.poll_once(require_complete=require_complete)
            next_poll += poll_period_ns
            remaining_ns = next_poll - self.collector.clock.now_reference_ns()
            if remaining_ns <= 0:
                next_poll = self.collector.clock.now_reference_ns()
                continue
            stop_event.wait(remaining_ns / 1_000_000_000)

    def close(self) -> tuple[ChunkDescriptor, ...]:
        if self._closed:
            return self.writer.descriptors
        collector_error: BaseException | None = None
        try:
            if self._started:
                self.collector.close()
        except BaseException as error:
            collector_error = error
        descriptors = self.writer.close()
        self._closed = True
        if collector_error is not None:
            raise collector_error
        return descriptors

    def __enter__(self) -> "TelemetryRecorder":
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()


def _as_mapping(value: Any, *, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TelemetryConfigurationError(f"{name} must be an object")
    return value


def _as_sequence(value: Any, *, name: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TelemetryConfigurationError(f"{name} must be an array")
    return value


def _known_keys(
    value: Mapping[str, Any], allowed: set[str], *, name: str
) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise TelemetryConfigurationError(
            f"unknown {name} field(s): " + ", ".join(unknown)
        )


def _normalize_json_path(value: Any, *, name: str) -> list[str | int] | None:
    if value is None:
        return None
    parts = _as_sequence(value, name=name)
    normalized: list[str | int] = []
    for part in parts:
        if isinstance(part, bool) or not isinstance(part, (str, int)):
            raise TelemetryConfigurationError(
                f"{name} parts must be strings or integer indices"
            )
        normalized.append(part)
    return normalized


_MANIFEST_CONFIG_FIELDS = {
    "channel_id",
    "boundary",
    "metric",
    "unit",
    "sample_kind",
    "clock_id",
    "nominal_period_ns",
    "integration_window_ns",
    "uncertainty_ns",
    "required",
    "metadata",
}


def _normalize_manifest_config(
    raw: Mapping[str, Any], *, extra_fields: set[str], name: str
) -> dict[str, Any]:
    _known_keys(raw, _MANIFEST_CONFIG_FIELDS | extra_fields, name=name)
    required_fields = _MANIFEST_CONFIG_FIELDS - {"required", "metadata"}
    missing = sorted(required_fields - set(raw))
    if missing:
        raise TelemetryConfigurationError(
            f"missing {name} field(s): " + ", ".join(missing)
        )
    normalized = {key: raw[key] for key in required_fields}
    normalized["required"] = bool(raw.get("required", False))
    metadata = raw.get("metadata", {})
    normalized["metadata"] = dict(
        _as_mapping(metadata, name=f"{name}.metadata")
    )
    for key in extra_fields:
        if key in raw:
            normalized[key] = raw[key]
    return normalized


def _normalize_endpoint_config(value: Any, *, name: str) -> dict[str, Any]:
    endpoint = _as_mapping(value, name=name)
    _known_keys(
        endpoint,
        {"url", "timeout_seconds", "max_response_bytes", "auth_env", "ca_file"},
        name=name,
    )
    if "url" not in endpoint:
        raise TelemetryConfigurationError(f"{name}.url is required")
    auth = _as_mapping(endpoint.get("auth_env", {}), name=f"{name}.auth_env")
    _known_keys(
        auth,
        {
            "bearer_token_env",
            "basic_username_env",
            "basic_password_env",
            "header_value_env",
        },
        name=f"{name}.auth_env",
    )
    header_env = _as_mapping(
        auth.get("header_value_env", {}),
        name=f"{name}.auth_env.header_value_env",
    )
    normalized_auth = {
        "bearer_token_env": auth.get("bearer_token_env"),
        "basic_username_env": auth.get("basic_username_env"),
        "basic_password_env": auth.get("basic_password_env"),
        "header_value_env": {
            str(header): str(env_name)
            for header, env_name in header_env.items()
        },
    }
    return {
        "url": str(endpoint["url"]),
        "timeout_seconds": float(endpoint.get("timeout_seconds", 5.0)),
        "max_response_bytes": int(
            endpoint.get("max_response_bytes", 8 * 1024 * 1024)
        ),
        "auth_env": normalized_auth,
        "ca_file": endpoint.get("ca_file"),
    }


def _normalize_source_config(value: Any, *, index: int) -> dict[str, Any]:
    source = _as_mapping(value, name=f"sources[{index}]")
    kind = str(source.get("kind", ""))
    source_id = str(source.get("source_id", ""))
    if not kind or not source_id:
        raise TelemetryConfigurationError(
            f"sources[{index}] requires kind and source_id"
        )
    if kind == "http_json":
        _known_keys(
            source,
            {"kind", "source_id", "endpoint", "channels"},
            name=f"sources[{index}]",
        )
        channels = _as_sequence(
            source.get("channels", ()), name=f"sources[{index}].channels"
        )
        extra = {
            "value_path",
            "value_scale",
            "timestamp_path",
            "interval_start_path",
            "interval_end_path",
            "timestamp_unit",
        }
        normalized_channels: list[dict[str, Any]] = []
        for channel_index, channel_value in enumerate(channels):
            channel = _normalize_manifest_config(
                _as_mapping(
                    channel_value,
                    name=f"sources[{index}].channels[{channel_index}]",
                ),
                extra_fields=extra,
                name=f"sources[{index}].channels[{channel_index}]",
            )
            if "value_path" not in channel:
                raise TelemetryConfigurationError(
                    f"sources[{index}].channels[{channel_index}].value_path "
                    "is required"
                )
            for path_name in (
                "value_path",
                "timestamp_path",
                "interval_start_path",
                "interval_end_path",
            ):
                if path_name in channel:
                    channel[path_name] = _normalize_json_path(
                        channel[path_name],
                        name=(
                            f"sources[{index}].channels[{channel_index}]."
                            f"{path_name}"
                        ),
                    )
            channel["value_scale"] = float(channel.get("value_scale", 1.0))
            channel["timestamp_unit"] = str(
                channel.get("timestamp_unit", "seconds")
            )
            normalized_channels.append(channel)
        return {
            "kind": kind,
            "source_id": source_id,
            "endpoint": _normalize_endpoint_config(
                source.get("endpoint"), name=f"sources[{index}].endpoint"
            ),
            "channels": normalized_channels,
        }
    if kind == "prometheus":
        _known_keys(
            source,
            {"kind", "source_id", "endpoint", "channels"},
            name=f"sources[{index}]",
        )
        channels = _as_sequence(
            source.get("channels", ()), name=f"sources[{index}].channels"
        )
        extra = {
            "query",
            "expected_labels",
            "value_scale",
            "max_staleness_ns",
        }
        normalized_channels = []
        for channel_index, channel_value in enumerate(channels):
            channel = _normalize_manifest_config(
                _as_mapping(
                    channel_value,
                    name=f"sources[{index}].channels[{channel_index}]",
                ),
                extra_fields=extra,
                name=f"sources[{index}].channels[{channel_index}]",
            )
            if "query" not in channel:
                raise TelemetryConfigurationError(
                    f"sources[{index}].channels[{channel_index}].query is required"
                )
            labels = _as_mapping(
                channel.get("expected_labels", {}),
                name=(
                    f"sources[{index}].channels[{channel_index}]."
                    "expected_labels"
                ),
            )
            channel["query"] = str(channel["query"])
            channel["expected_labels"] = {
                str(key): str(label) for key, label in labels.items()
            }
            channel["value_scale"] = float(channel.get("value_scale", 1.0))
            if channel.get("max_staleness_ns") is not None:
                channel["max_staleness_ns"] = int(
                    channel["max_staleness_ns"]
                )
            normalized_channels.append(channel)
        return {
            "kind": kind,
            "source_id": source_id,
            "endpoint": _normalize_endpoint_config(
                source.get("endpoint"), name=f"sources[{index}].endpoint"
            ),
            "channels": normalized_channels,
        }
    if kind == "proc_diskstats":
        _known_keys(
            source,
            {
                "kind",
                "source_id",
                "targets",
                "nominal_period_ns",
                "proc_path",
                "clock_id",
            },
            name=f"sources[{index}]",
        )
        if "nominal_period_ns" not in source:
            raise TelemetryConfigurationError(
                f"sources[{index}].nominal_period_ns is required"
            )
        targets = _as_sequence(
            source.get("targets", ()), name=f"sources[{index}].targets"
        )
        normalized_targets: list[dict[str, Any]] = []
        for target_index, target_value in enumerate(targets):
            target = _as_mapping(
                target_value,
                name=f"sources[{index}].targets[{target_index}]",
            )
            _known_keys(
                target,
                {"device", "required_activity"},
                name=f"sources[{index}].targets[{target_index}]",
            )
            if "device" not in target:
                raise TelemetryConfigurationError(
                    f"sources[{index}].targets[{target_index}].device is required"
                )
            normalized_targets.append(
                {
                    "device": str(target["device"]),
                    "required_activity": bool(
                        target.get("required_activity", True)
                    ),
                }
            )
        return {
            "kind": kind,
            "source_id": source_id,
            "targets": normalized_targets,
            "nominal_period_ns": int(source["nominal_period_ns"]),
            "proc_path": str(source.get("proc_path", "/proc/diskstats")),
            "clock_id": str(
                source.get("clock_id", HOST_REFERENCE_CLOCK_ID)
            ),
        }
    raise TelemetryConfigurationError(
        f"sources[{index}] has unsupported kind {kind!r}"
    )


@dataclass(frozen=True)
class TelemetryConfig:
    schema: str
    poll_period_ns: int
    clock_recalibration_period_ns: int
    max_records_per_chunk: int
    max_content_bytes_per_chunk: int
    required_channels: tuple[str, ...]
    rack_state_channels: Mapping[str, str]
    sources: tuple[Mapping[str, Any], ...]
    config_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "poll_period_ns": self.poll_period_ns,
            "clock_recalibration_period_ns": (
                self.clock_recalibration_period_ns
            ),
            "chunking": {
                "max_records_per_chunk": self.max_records_per_chunk,
                "max_content_bytes_per_chunk": (
                    self.max_content_bytes_per_chunk
                ),
            },
            "required_channels": list(self.required_channels),
            "rack_state_channels": dict(self.rack_state_channels),
            "sources": [dict(source) for source in self.sources],
            "config_sha256": self.config_sha256,
        }


def parse_telemetry_config(payload: Mapping[str, Any]) -> TelemetryConfig:
    """Validate and normalize a telemetry config already loaded as JSON."""

    _known_keys(
        payload,
        {
            "schema",
            "poll_period_ns",
            "clock_recalibration_period_ns",
            "chunking",
            "required_channels",
            "rack_state_channels",
            "sources",
        },
        name="telemetry config",
    )
    if payload.get("schema") != CONFIG_SCHEMA:
        raise TelemetryConfigurationError(
            f"telemetry config schema must equal {CONFIG_SCHEMA!r}"
        )
    poll_period_ns = int(payload.get("poll_period_ns", 100_000_000))
    clock_period_ns = int(
        payload.get("clock_recalibration_period_ns", 60_000_000_000)
    )
    if poll_period_ns <= 0 or clock_period_ns <= 0:
        raise TelemetryConfigurationError(
            "telemetry poll and clock periods must be positive"
        )
    chunking = _as_mapping(
        payload.get("chunking", {}), name="telemetry config.chunking"
    )
    _known_keys(
        chunking,
        {"max_records_per_chunk", "max_content_bytes_per_chunk"},
        name="telemetry config.chunking",
    )
    max_records = int(chunking.get("max_records_per_chunk", 100_000))
    max_bytes = int(
        chunking.get("max_content_bytes_per_chunk", 64 * 1024 * 1024)
    )
    if max_records <= 0 or max_bytes <= 0:
        raise TelemetryConfigurationError(
            "telemetry chunk limits must be positive"
        )
    required_values = _as_sequence(
        payload.get("required_channels", ()),
        name="telemetry config.required_channels",
    )
    required_channels = tuple(str(value) for value in required_values)
    if len(set(required_channels)) != len(required_channels):
        raise TelemetryConfigurationError("duplicate required channel ID")
    rack_state_raw = _as_mapping(
        payload.get("rack_state_channels", {}),
        name="telemetry config.rack_state_channels",
    )
    rack_state_channels = {
        str(alias): str(channel_id)
        for alias, channel_id in rack_state_raw.items()
    }
    source_values = _as_sequence(
        payload.get("sources", ()), name="telemetry config.sources"
    )
    sources = tuple(
        _normalize_source_config(value, index=index)
        for index, value in enumerate(source_values)
    )
    normalized_without_hash = {
        "schema": CONFIG_SCHEMA,
        "poll_period_ns": poll_period_ns,
        "clock_recalibration_period_ns": clock_period_ns,
        "chunking": {
            "max_records_per_chunk": max_records,
            "max_content_bytes_per_chunk": max_bytes,
        },
        "required_channels": list(required_channels),
        "rack_state_channels": rack_state_channels,
        "sources": list(sources),
    }
    config_sha256 = hashlib.sha256(
        json.dumps(
            normalized_without_hash,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    return TelemetryConfig(
        schema=CONFIG_SCHEMA,
        poll_period_ns=poll_period_ns,
        clock_recalibration_period_ns=clock_period_ns,
        max_records_per_chunk=max_records,
        max_content_bytes_per_chunk=max_bytes,
        required_channels=required_channels,
        rack_state_channels=rack_state_channels,
        sources=sources,
        config_sha256=config_sha256,
    )


def load_telemetry_config(path: str | Path) -> TelemetryConfig:
    """Load the frozen external telemetry description from a JSON file."""

    config_path = Path(path)
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise TelemetryConfigurationError(
            f"cannot load telemetry config {config_path}"
        ) from error
    return parse_telemetry_config(
        _as_mapping(payload, name="telemetry config")
    )


def _endpoint_from_config(raw: Mapping[str, Any]) -> HttpEndpoint:
    auth_raw = _as_mapping(raw["auth_env"], name="endpoint.auth_env")
    return HttpEndpoint(
        url=str(raw["url"]),
        timeout_seconds=float(raw["timeout_seconds"]),
        max_response_bytes=int(raw["max_response_bytes"]),
        auth=HttpAuthEnvironment(
            bearer_token_env=auth_raw.get("bearer_token_env"),
            basic_username_env=auth_raw.get("basic_username_env"),
            basic_password_env=auth_raw.get("basic_password_env"),
            header_value_env=dict(
                _as_mapping(
                    auth_raw.get("header_value_env", {}),
                    name="endpoint.auth_env.header_value_env",
                )
            ),
        ),
        ca_file=raw.get("ca_file"),
    )


def _channel_manifest_from_config(
    raw: Mapping[str, Any],
    *,
    source_id: str,
    required_channels: frozenset[str],
) -> ChannelManifest:
    channel_id = str(raw["channel_id"])
    return ChannelManifest(
        channel_id=channel_id,
        boundary=str(raw["boundary"]),
        source_id=source_id,
        metric=str(raw["metric"]),
        unit=str(raw["unit"]),
        sample_kind=str(raw["sample_kind"]),
        clock_id=str(raw["clock_id"]),
        nominal_period_ns=int(raw["nominal_period_ns"]),
        integration_window_ns=int(raw["integration_window_ns"]),
        uncertainty_ns=int(raw["uncertainty_ns"]),
        required=bool(raw.get("required", False))
        or channel_id in required_channels,
        metadata=dict(
            _as_mapping(raw.get("metadata", {}), name="channel.metadata")
        ),
    )


def _external_sources(config: TelemetryConfig) -> tuple[TelemetrySource, ...]:
    required = frozenset(config.required_channels)
    sources: list[TelemetrySource] = []
    for raw in config.sources:
        kind = str(raw["kind"])
        source_id = str(raw["source_id"])
        if kind == "http_json":
            channels: list[HttpJsonChannel] = []
            for channel_raw in _as_sequence(
                raw["channels"], name=f"{source_id}.channels"
            ):
                channel = _as_mapping(
                    channel_raw, name=f"{source_id}.channel"
                )
                channels.append(
                    HttpJsonChannel(
                        manifest=_channel_manifest_from_config(
                            channel,
                            source_id=source_id,
                            required_channels=required,
                        ),
                        value_path=tuple(channel["value_path"]),
                        value_scale=float(channel.get("value_scale", 1.0)),
                        timestamp_path=(
                            tuple(channel["timestamp_path"])
                            if channel.get("timestamp_path") is not None
                            else None
                        ),
                        interval_start_path=(
                            tuple(channel["interval_start_path"])
                            if channel.get("interval_start_path") is not None
                            else None
                        ),
                        interval_end_path=(
                            tuple(channel["interval_end_path"])
                            if channel.get("interval_end_path") is not None
                            else None
                        ),
                        timestamp_unit=str(
                            channel.get("timestamp_unit", "seconds")
                        ),
                    )
                )
            sources.append(
                HttpJsonTelemetrySource(
                    source_id=source_id,
                    endpoint=_endpoint_from_config(
                        _as_mapping(raw["endpoint"], name=f"{source_id}.endpoint")
                    ),
                    channels=channels,
                )
            )
        elif kind == "prometheus":
            prometheus_channels: list[PrometheusQueryChannel] = []
            for channel_raw in _as_sequence(
                raw["channels"], name=f"{source_id}.channels"
            ):
                channel = _as_mapping(
                    channel_raw, name=f"{source_id}.channel"
                )
                prometheus_channels.append(
                    PrometheusQueryChannel(
                        manifest=_channel_manifest_from_config(
                            channel,
                            source_id=source_id,
                            required_channels=required,
                        ),
                        query=str(channel["query"]),
                        expected_labels=dict(
                            _as_mapping(
                                channel.get("expected_labels", {}),
                                name=f"{source_id}.expected_labels",
                            )
                        ),
                        value_scale=float(channel.get("value_scale", 1.0)),
                        max_staleness_ns=(
                            int(channel["max_staleness_ns"])
                            if channel.get("max_staleness_ns") is not None
                            else None
                        ),
                    )
                )
            sources.append(
                PrometheusTelemetrySource(
                    source_id=source_id,
                    endpoint=_endpoint_from_config(
                        _as_mapping(raw["endpoint"], name=f"{source_id}.endpoint")
                    ),
                    channels=prometheus_channels,
                )
            )
        elif kind == "proc_diskstats":
            targets = tuple(
                ProcDiskTarget(
                    device=str(target["device"]),
                    required_activity=bool(
                        target.get("required_activity", True)
                    ),
                )
                for target in (
                    _as_mapping(value, name=f"{source_id}.target")
                    for value in _as_sequence(
                        raw["targets"], name=f"{source_id}.targets"
                    )
                )
            )
            proc_source = ProcDiskStatsSource(
                targets=targets,
                nominal_period_ns=int(raw["nominal_period_ns"]),
                proc_path=str(raw["proc_path"]),
                clock_id=str(raw["clock_id"]),
                source_id=source_id,
            )
            proc_source._manifests = tuple(
                replace(
                    manifest,
                    required=manifest.required
                    or manifest.channel_id in required,
                )
                for manifest in proc_source.manifests
            )
            sources.append(proc_source)
        else:
            raise TelemetryConfigurationError(
                f"unsupported normalized source kind: {kind}"
            )
    declared = {
        manifest.channel_id
        for source in sources
        for manifest in source.manifests
    }
    undeclared_required = sorted(required - declared)
    if undeclared_required:
        raise TelemetryConfigurationError(
            "required channel(s) are not declared by any source: "
            + ", ".join(undeclared_required)
        )
    undeclared_rack_state = sorted(
        channel_id
        for channel_id in config.rack_state_channels.values()
        if channel_id not in declared
    )
    if undeclared_rack_state:
        raise TelemetryConfigurationError(
            "rack-state channel(s) are not declared by any source: "
            + ", ".join(undeclared_rack_state)
        )
    return tuple(sources)


def _safe_stream_id(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-.")
    if not safe:
        safe = "telemetry"
    return safe


@dataclass(frozen=True)
class TelemetrySessionResult:
    session_id: str
    run_id: str
    channel_manifests: tuple[Mapping[str, Any], ...]
    chunks: tuple[Mapping[str, Any], ...]
    samples: tuple[Mapping[str, Any], ...]
    latest: Mapping[str, Mapping[str, Any]]
    previous: Mapping[str, Mapping[str, Any]]
    visible_rack_state: Mapping[str, Any]
    missing_required_channel_ids: tuple[str, ...]
    clock_offsets: tuple[Mapping[str, Any], ...]
    phase_markers: tuple[Mapping[str, Any], ...]
    terminal_error: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "run_id": self.run_id,
            "channel_manifests": [dict(value) for value in self.channel_manifests],
            "chunks": [dict(value) for value in self.chunks],
            "samples": [dict(value) for value in self.samples],
            "latest": {
                key: dict(value) for key, value in self.latest.items()
            },
            "previous": {
                key: dict(value) for key, value in self.previous.items()
            },
            "visible_rack_state": dict(self.visible_rack_state),
            "missing_required_channel_ids": list(
                self.missing_required_channel_ids
            ),
            "clock_offsets": [dict(value) for value in self.clock_offsets],
            "phase_markers": [dict(value) for value in self.phase_markers],
            "terminal_error": self.terminal_error,
        }


class _BackgroundTelemetrySession:
    def __init__(
        self,
        *,
        recorder: TelemetryRecorder,
        poll_period_ns: int,
        rack_state_channels: Mapping[str, str] | None = None,
        metadata_records: Sequence[Mapping[str, Any]] = (),
    ) -> None:
        self.recorder = recorder
        self.poll_period_ns = poll_period_ns
        self.rack_state_channels = dict(rack_state_channels or {})
        self.metadata_records = tuple(metadata_records)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._state_lock = threading.Lock()
        self._samples: list[dict[str, Any]] = []
        self._latest: dict[str, dict[str, Any]] = {}
        self._previous: dict[str, dict[str, Any]] = {}
        self._clock_offsets: list[dict[str, Any]] = []
        self._phase_markers: list[dict[str, Any]] = []
        self._missing_required_ever: set[str] = set()
        self._missing_required_current: set[str] = set()
        self._terminal_error: str | None = None
        self._phase_sequence = 0
        self._manifests: tuple[ChannelManifest, ...] = ()
        self._result: TelemetrySessionResult | None = None

    @property
    def latest(self) -> dict[str, dict[str, Any]]:
        with self._state_lock:
            return {key: dict(value) for key, value in self._latest.items()}

    @property
    def previous(self) -> dict[str, dict[str, Any]]:
        with self._state_lock:
            return {key: dict(value) for key, value in self._previous.items()}

    def _visible_state_locked(self) -> dict[str, Any]:
        visible: dict[str, Any] = {}
        for alias, channel_id in self.rack_state_channels.items():
            record = self._latest.get(channel_id)
            visible[alias] = record.get("value") if record is not None else None
        rack_channel = self.rack_state_channels.get("rack_power_w")
        if rack_channel:
            latest = self._latest.get(rack_channel)
            previous = self._previous.get(rack_channel)
            visible["previous_rack_power_w"] = (
                previous.get("value") if previous is not None else None
            )
            interval_ns = _sample_midpoint_delta_ns(previous, latest)
            visible["rack_power_interval_ns"] = interval_ns
            visible["rack_ramp_w_per_s"] = _observed_rate(
                previous, latest, interval_ns, allow_negative=True
            )
        storage_channel = self.rack_state_channels.get(
            "storage_write_bytes_total"
        )
        if storage_channel:
            latest = self._latest.get(storage_channel)
            previous = self._previous.get(storage_channel)
            visible["previous_storage_write_bytes_total"] = (
                previous.get("value") if previous is not None else None
            )
            interval_ns = _sample_midpoint_delta_ns(previous, latest)
            visible["storage_write_interval_ns"] = interval_ns
            visible["storage_write_rate_bytes_s"] = _observed_rate(
                previous, latest, interval_ns, allow_negative=False
            )
            visible["storage_write_bytes_per_s"] = visible[
                "storage_write_rate_bytes_s"
            ]
        uncertainties = [
            int(record.get("quality", {}).get("uncertainty_ns", 0))
            for record in self._latest.values()
        ]
        clock_uncertainty = (
            self.recorder.collector.clock.current_offset().uncertainty_ns
        )
        visible["clock_uncertainty_ns"] = max(
            uncertainties, default=clock_uncertainty
        )
        visible["reference_time_ns"] = (
            self.recorder.collector.clock.now_reference_ns()
        )
        configured_missing = [
            channel_id
            for channel_id in self.rack_state_channels.values()
            if channel_id not in self._latest
        ]
        latest_quality = {
            str(record.get("quality", {}).get("status", "clock_uncertain"))
            for record in self._latest.values()
        }
        if configured_missing or self._missing_required_current:
            visible["quality"] = "missing"
        elif latest_quality - {"observed"}:
            visible["quality"] = "degraded"
        else:
            visible["quality"] = "good"
        visible.setdefault("rack_power_w", None)
        visible.setdefault("rack_ramp_w_per_s", None)
        visible.setdefault("storage_write_bytes_per_s", None)
        visible.setdefault("storage_queue_depth", None)
        return visible

    def snapshot(self) -> dict[str, Any]:
        with self._state_lock:
            return {
                "latest": {
                    key: dict(value) for key, value in self._latest.items()
                },
                "previous": {
                    key: dict(value) for key, value in self._previous.items()
                },
                "visible_rack_state": self._visible_state_locked(),
                "latest_clock_offset": (
                    dict(self._clock_offsets[-1])
                    if self._clock_offsets
                    else None
                ),
                "reference_clock_id": (
                    self.recorder.collector.clock.clock_id
                ),
                "currently_missing_required_channel_ids": sorted(
                    self._missing_required_current
                ),
                "ever_missing_required_channel_ids": sorted(
                    self._missing_required_ever
                ),
                "terminal_error": self._terminal_error,
            }

    def start(self) -> tuple[ChannelManifest, ...]:
        if self._thread is not None:
            return self._manifests
        self._manifests = self.recorder.start()
        for record in self.metadata_records:
            self.recorder.writer.write(record)
        self._thread = threading.Thread(
            target=self._run,
            name=f"telemetry-{_safe_stream_id(self.recorder.session_id)}",
            daemon=True,
        )
        self._thread.start()
        return self._manifests

    def _accept_batch(self, batch: TelemetryBatch) -> None:
        sample_records = [sample.to_record() for sample in batch.samples]
        clock_records = [record.to_record() for record in batch.clock_offsets]
        with self._state_lock:
            for record in sample_records:
                channel_id = str(record["channel_id"])
                if channel_id in self._latest:
                    self._previous[channel_id] = self._latest[channel_id]
                self._latest[channel_id] = record
                self._samples.append(record)
            self._clock_offsets.extend(clock_records)
            current = {
                record.channel_id
                for record in batch.missing_required_channels
            }
            self._missing_required_current = current
            self._missing_required_ever.update(current)

    def _run(self) -> None:
        next_poll = self.recorder.collector.clock.now_reference_ns()
        try:
            while not self._stop_event.is_set():
                batch = self.recorder.poll_once()
                self._accept_batch(batch)
                next_poll += self.poll_period_ns
                remaining = (
                    next_poll
                    - self.recorder.collector.clock.now_reference_ns()
                )
                if remaining <= 0:
                    next_poll = (
                        self.recorder.collector.clock.now_reference_ns()
                    )
                    continue
                self._stop_event.wait(remaining / 1_000_000_000)
        except BaseException as error:
            with self._state_lock:
                self._terminal_error = _exception_detail(error)
            self._stop_event.set()

    def mark_phase(
        self,
        phase: str,
        event: str = "start",
        metadata: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        if not phase.strip() or not event.strip():
            raise TelemetryConfigurationError(
                "phase and phase event cannot be empty"
            )
        if self._thread is None:
            raise TelemetrySourceError("telemetry session is not started")
        clock = self.recorder.collector.clock
        reference_ns = clock.now_reference_ns()
        utc_start, utc_end, uncertainty = clock.reference_to_utc_interval(
            reference_ns, reference_ns
        )
        with self._state_lock:
            sequence = self._phase_sequence
            self._phase_sequence += 1
        record = {
            "record_type": "phase_marker",
            "schema": PHASE_MARKER_SCHEMA,
            "session_id": self.recorder.session_id,
            "run_id": self.recorder.run_id,
            "phase": phase,
            "event": event,
            "sequence": sequence,
            "utc_interval_start_ns": utc_start,
            "utc_interval_end_ns": utc_end,
            "utc_interval_start": _utc_iso(utc_start),
            "utc_interval_end": _utc_iso(utc_end),
            "reference_interval_start_ns": reference_ns,
            "reference_interval_end_ns": reference_ns,
            "clock_uncertainty_ns": uncertainty,
            "metadata": dict(metadata or {}),
        }
        self.recorder.writer.write(record)
        with self._state_lock:
            self._phase_markers.append(dict(record))
        return record

    def stop(self) -> TelemetrySessionResult:
        if self._result is not None:
            return self._result
        if self._thread is None:
            self.start()
        assert self._thread is not None
        self._stop_event.set()
        self._thread.join()
        try:
            descriptors = self.recorder.close()
        except BaseException as error:
            descriptors = self.recorder.writer.descriptors
            with self._state_lock:
                if self._terminal_error is None:
                    self._terminal_error = _exception_detail(error)
        with self._state_lock:
            self._result = TelemetrySessionResult(
                session_id=self.recorder.session_id,
                run_id=self.recorder.run_id,
                channel_manifests=tuple(
                    manifest.to_record() for manifest in self._manifests
                ),
                chunks=tuple(descriptor.to_dict() for descriptor in descriptors),
                samples=tuple(dict(record) for record in self._samples),
                latest={
                    key: dict(value) for key, value in self._latest.items()
                },
                previous={
                    key: dict(value) for key, value in self._previous.items()
                },
                visible_rack_state=self._visible_state_locked(),
                missing_required_channel_ids=tuple(
                    sorted(self._missing_required_ever)
                ),
                clock_offsets=tuple(
                    dict(record) for record in self._clock_offsets
                ),
                phase_markers=tuple(
                    dict(record) for record in self._phase_markers
                ),
                terminal_error=self._terminal_error,
            )
            return self._result


def _sample_midpoint_delta_ns(
    previous: Mapping[str, Any] | None,
    latest: Mapping[str, Any] | None,
) -> int | None:
    if previous is None or latest is None:
        return None
    previous_midpoint = int(previous["reference_interval_start_ns"]) + (
        int(previous["reference_interval_end_ns"])
        - int(previous["reference_interval_start_ns"])
    ) // 2
    latest_midpoint = int(latest["reference_interval_start_ns"]) + (
        int(latest["reference_interval_end_ns"])
        - int(latest["reference_interval_start_ns"])
    ) // 2
    delta = latest_midpoint - previous_midpoint
    return delta if delta > 0 else None


def _observed_rate(
    previous: Mapping[str, Any] | None,
    latest: Mapping[str, Any] | None,
    interval_ns: int | None,
    *,
    allow_negative: bool,
) -> float | None:
    if previous is None or latest is None or interval_ns is None:
        return None
    if (
        previous.get("quality", {}).get("status") != "observed"
        or latest.get("quality", {}).get("status") != "observed"
    ):
        return None
    delta = float(latest["value"]) - float(previous["value"])
    if delta < 0 and not allow_negative:
        return None
    return delta / (interval_ns / 1_000_000_000)


class GpuTelemetrySampler:
    """One-rank facade for a UUID-bound GPU telemetry stream."""

    def __init__(
        self,
        cuda_index: int,
        output_dir: str | Path,
        run_id: str,
        rank: int,
        poll_ns: int,
        *,
        expected_uuid: str | None = None,
    ) -> None:
        if cuda_index < 0 or rank < 0 or poll_ns <= 0:
            raise TelemetryConfigurationError(
                "GPU CUDA index/rank must be nonnegative and poll_ns positive"
            )
        target = (
            (GpuTarget(cuda_index, expected_uuid, required=True),)
            if expected_uuid is not None
            else ()
        )
        source = NvmlGpuTelemetrySource(
            nominal_period_ns=poll_ns,
            targets=target,
            cuda_indices=() if target else (cuda_index,),
        )
        collector = TelemetryCollector((source,))
        stream_id = _safe_stream_id(
            f"{run_id}.rank-{rank}.gpu-{cuda_index}"
        )
        writer = ChunkedJsonlWriter(
            output_dir,
            stream_id=stream_id,
        )
        recorder = TelemetryRecorder(
            collector,
            writer,
            session_id=f"{run_id}:gpu-rank-{rank}",
            run_id=run_id,
        )
        self.cuda_index = cuda_index
        self.rank = rank
        self.poll_ns = poll_ns
        self.expected_uuid = expected_uuid
        self._source = source
        self._session = _BackgroundTelemetrySession(
            recorder=recorder,
            poll_period_ns=poll_ns,
            metadata_records=(
                {
                    "record_type": "gpu_rank_binding_request",
                    "run_id": run_id,
                    "rank": rank,
                    "local_cuda_index": cuda_index,
                    "expected_gpu_uuid": expected_uuid,
                },
            ),
        )

    @property
    def identities(self) -> tuple[GpuIdentity, ...]:
        return self._source.identities

    @property
    def latest(self) -> dict[str, dict[str, Any]]:
        return self._session.latest

    def snapshot(self) -> dict[str, Any]:
        return self._session.snapshot()

    def start(self) -> tuple[ChannelManifest, ...]:
        return self._session.start()

    def mark_phase(
        self,
        phase: str,
        event: str = "start",
        metadata: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        return self._session.mark_phase(phase, event, metadata)

    def stop(self) -> TelemetrySessionResult:
        return self._session.stop()


class ExternalTelemetrySession:
    """Live rack/PDU/storage/cooling session built from a frozen config."""

    def __init__(
        self,
        config: TelemetryConfig | Mapping[str, Any],
        output_dir: str | Path,
        run_id: str,
    ) -> None:
        self.config = (
            config
            if isinstance(config, TelemetryConfig)
            else parse_telemetry_config(config)
        )
        sources = _external_sources(self.config)
        collector = TelemetryCollector(
            sources,
            clock_recalibration_period_ns=(
                self.config.clock_recalibration_period_ns
            ),
        )
        writer = ChunkedJsonlWriter(
            output_dir,
            stream_id=_safe_stream_id(f"{run_id}.external"),
            max_records_per_chunk=self.config.max_records_per_chunk,
            max_content_bytes_per_chunk=(
                self.config.max_content_bytes_per_chunk
            ),
        )
        recorder = TelemetryRecorder(
            collector,
            writer,
            session_id=f"{run_id}:external",
            run_id=run_id,
        )
        self._session = _BackgroundTelemetrySession(
            recorder=recorder,
            poll_period_ns=self.config.poll_period_ns,
            rack_state_channels=self.config.rack_state_channels,
            metadata_records=(
                {
                    "record_type": "telemetry_config",
                    **self.config.to_dict(),
                },
            ),
        )

    @property
    def latest(self) -> dict[str, dict[str, Any]]:
        return self._session.latest

    def snapshot(self) -> dict[str, Any]:
        return self._session.snapshot()

    def start(self) -> tuple[ChannelManifest, ...]:
        return self._session.start()

    def mark_phase(
        self,
        phase: str,
        event: str = "start",
        metadata: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        return self._session.mark_phase(phase, event, metadata)

    def stop(self) -> TelemetrySessionResult:
        return self._session.stop()


def read_chunk_samples(path: str | Path) -> tuple[dict[str, Any], ...]:
    """Verify a finalized chunk and return only its raw sample records."""

    chunk_path = Path(path)
    inspect_jsonl_chunk(chunk_path)
    samples: list[dict[str, Any]] = []
    with chunk_path.open("r", encoding="utf-8", newline="") as handle:
        for line in handle:
            record = json.loads(line)
            if record.get("record_type") == "sample":
                samples.append(record)
    return tuple(samples)


__all__ = [
    "CHANNEL_MANIFEST_SCHEMA",
    "CHUNK_SCHEMA",
    "CLOCK_OFFSET_SCHEMA",
    "COOLING_BOUNDARY",
    "CONFIG_SCHEMA",
    "ENGINE_ID",
    "GPU_BOARD_BOUNDARY",
    "HOST_REFERENCE_CLOCK_ID",
    "MISSING_CHANNEL_SCHEMA",
    "PHASE_MARKER_SCHEMA",
    "RACK_AC_INPUT_BOUNDARY",
    "SAMPLE_SCHEMA",
    "SESSION_SCHEMA",
    "STORAGE_ACTIVITY_BOUNDARY",
    "STORAGE_POWER_BOUNDARY",
    "UTC_CLOCK_ID",
    "ChannelManifest",
    "ChunkDescriptor",
    "ChunkedJsonlWriter",
    "ClockOffsetRecord",
    "ExternalTelemetrySession",
    "GpuIdentity",
    "GpuTelemetrySampler",
    "GpuTarget",
    "HostReferenceClock",
    "HttpAuthEnvironment",
    "HttpEndpoint",
    "HttpJsonChannel",
    "HttpJsonTelemetrySource",
    "MissingChannelRecord",
    "MissingCredentialEnvironment",
    "MissingRequiredChannels",
    "NvmlGpuTelemetrySource",
    "ProcDiskStatsSource",
    "ProcDiskTarget",
    "PrometheusQueryChannel",
    "PrometheusTelemetrySource",
    "SampleQuality",
    "SourceDiagnostic",
    "SourcePollResult",
    "TelemetryBatch",
    "TelemetryBindingError",
    "TelemetryCollector",
    "TelemetryConfig",
    "TelemetryConfigurationError",
    "TelemetryError",
    "TelemetryRecorder",
    "TelemetrySample",
    "TelemetrySessionResult",
    "TelemetrySource",
    "TelemetrySourceError",
    "inspect_jsonl_chunk",
    "load_telemetry_config",
    "parse_telemetry_config",
    "read_chunk_samples",
]
