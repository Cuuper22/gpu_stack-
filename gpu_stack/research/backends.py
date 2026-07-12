"""Composable prediction backends for the GPUSTACK virtual datacenter.

GPUSTACK should not reimplement every specialist simulator.  This module gives
the research layer a strict adapter boundary for operator simulators, measured
surrogates, grid solvers, learning-dynamics models, and future live telemetry
services.  Routing is explicit: overlapping backends are an error unless the
caller supplies a target route.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from numbers import Real
from types import MappingProxyType
from typing import Any, Mapping, Optional, Protocol, Sequence, Tuple, runtime_checkable


def _frozen_mapping(values: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(values))


def _finite_float(value: object, field_name: str) -> float:
    """Return a finite real while rejecting bool's integer masquerade."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"prediction {field_name} must be a real number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"prediction {field_name} must be finite")
    return result


@dataclass(frozen=True)
class BackendCapability:
    """A backend's declared modeling boundary."""

    targets: Tuple[str, ...]
    supports_temporal: bool = False
    supports_interventions: bool = False
    required_inputs: Tuple[str, ...] = ()
    fidelity: str = "unspecified"

    def __post_init__(self) -> None:
        targets = tuple(dict.fromkeys(str(item).strip() for item in self.targets))
        required = tuple(
            dict.fromkeys(str(item).strip() for item in self.required_inputs)
        )
        if not targets or any(not item for item in targets):
            raise ValueError("backend capability requires non-blank targets")
        if any(not item for item in required):
            raise ValueError("backend required inputs must be non-blank")
        if not str(self.fidelity).strip():
            raise ValueError("backend fidelity must be non-blank")
        object.__setattr__(self, "targets", targets)
        object.__setattr__(self, "required_inputs", required)
        object.__setattr__(self, "fidelity", str(self.fidelity).strip())

    def handles(self, target: str) -> bool:
        """Return true for exact targets or a declared ``prefix.*`` family."""
        return any(
            target == declared
            or (declared.endswith(".*") and target.startswith(declared[:-1]))
            for declared in self.targets
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "targets": list(self.targets),
            "supports_temporal": self.supports_temporal,
            "supports_interventions": self.supports_interventions,
            "required_inputs": list(self.required_inputs),
            "fidelity": self.fidelity,
        }


@dataclass(frozen=True)
class PredictionRequest:
    """One prediction query presented to a world-model backend."""

    target: str
    scenario_id: str
    inputs: Mapping[str, Any] = field(default_factory=dict)
    context: Mapping[str, Any] = field(default_factory=dict)
    intervention: Optional[Mapping[str, Any]] = None
    timestamp_s: Optional[float] = None

    def __post_init__(self) -> None:
        if not isinstance(self.target, str) or not self.target.strip():
            raise ValueError("prediction target must be non-blank")
        if not isinstance(self.scenario_id, str) or not self.scenario_id.strip():
            raise ValueError("prediction scenario_id must be non-blank")
        timestamp_s = self.timestamp_s
        if timestamp_s is not None:
            timestamp_s = _finite_float(timestamp_s, "timestamp_s")
            if timestamp_s < 0:
                raise ValueError("prediction timestamp_s must be nonnegative")
        object.__setattr__(self, "target", self.target.strip())
        object.__setattr__(self, "scenario_id", self.scenario_id.strip())
        object.__setattr__(self, "timestamp_s", timestamp_s)
        object.__setattr__(self, "inputs", _frozen_mapping(self.inputs))
        object.__setattr__(self, "context", _frozen_mapping(self.context))
        if self.intervention is not None:
            object.__setattr__(
                self, "intervention", _frozen_mapping(self.intervention)
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "target": self.target,
            "scenario_id": self.scenario_id,
            "inputs": dict(self.inputs),
            "context": dict(self.context),
            "intervention": (
                None if self.intervention is None else dict(self.intervention)
            ),
            "timestamp_s": self.timestamp_s,
        }


@dataclass(frozen=True)
class PredictionEstimate:
    """A backend estimate with its epistemic boundary attached."""

    target: str
    value: float
    unit: str
    backend: str
    lower: Optional[float] = None
    upper: Optional[float] = None
    confidence: Optional[float] = None
    assumptions: Tuple[str, ...] = ()
    provenance: Tuple[str, ...] = ()
    diagnostics: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("target", "unit", "backend"):
            field_value = getattr(self, name)
            if not isinstance(field_value, str) or not field_value.strip():
                raise ValueError(f"prediction {name} must be non-blank")
        value = _finite_float(self.value, "value")
        if (self.lower is None) != (self.upper is None):
            raise ValueError("prediction interval requires both lower and upper")
        lower = self.lower
        upper = self.upper
        if lower is not None:
            lower = _finite_float(lower, "lower")
            upper = _finite_float(upper, "upper")
            if lower > upper:
                raise ValueError("prediction lower bound exceeds upper bound")
            if not lower <= value <= upper:
                raise ValueError("prediction value must lie inside its interval")
        confidence = self.confidence
        if confidence is not None:
            confidence = _finite_float(confidence, "confidence")
            if not 0.0 < confidence < 1.0:
                raise ValueError(
                    "prediction confidence must lie strictly in (0, 1)"
                )
        if confidence is not None and lower is None:
            raise ValueError("prediction confidence requires an interval")
        object.__setattr__(self, "target", self.target.strip())
        object.__setattr__(self, "unit", self.unit.strip())
        object.__setattr__(self, "backend", self.backend.strip())
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "lower", lower)
        object.__setattr__(self, "upper", upper)
        object.__setattr__(self, "confidence", confidence)
        object.__setattr__(self, "assumptions", tuple(self.assumptions))
        object.__setattr__(self, "provenance", tuple(self.provenance))
        object.__setattr__(self, "diagnostics", _frozen_mapping(self.diagnostics))

    def to_dict(self) -> dict[str, object]:
        return {
            "target": self.target,
            "value": self.value,
            "unit": self.unit,
            "backend": self.backend,
            "lower": self.lower,
            "upper": self.upper,
            "confidence": self.confidence,
            "assumptions": list(self.assumptions),
            "provenance": list(self.provenance),
            "diagnostics": dict(self.diagnostics),
        }


@runtime_checkable
class WorldModelBackend(Protocol):
    """Protocol implemented by specialist simulators and measured surrogates."""

    @property
    def name(self) -> str: ...

    @property
    def capability(self) -> BackendCapability: ...

    def predict(self, request: PredictionRequest) -> PredictionEstimate: ...


class BackendRoutingError(RuntimeError):
    """Raised when a composite model cannot select one backend honestly."""


@dataclass(frozen=True)
class CompositeWorldModel:
    """Explicit router across complementary virtual-datacenter backends."""

    backends: Tuple[WorldModelBackend, ...]
    routes: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        backends = tuple(self.backends)
        if not backends:
            raise ValueError("composite world model requires at least one backend")
        names = [backend.name for backend in backends]
        if len(names) != len(set(names)) or any(not name.strip() for name in names):
            raise ValueError("backend names must be unique and non-blank")
        unknown_routes = sorted(set(self.routes.values()) - set(names))
        if unknown_routes:
            raise ValueError(f"routes reference unknown backends: {unknown_routes}")
        object.__setattr__(self, "backends", backends)
        object.__setattr__(self, "routes", _frozen_mapping(self.routes))

    def backend_for(self, request: PredictionRequest) -> WorldModelBackend:
        by_name = {backend.name: backend for backend in self.backends}
        routed_name = self.routes.get(request.target)
        if routed_name is not None:
            backend = by_name[routed_name]
            if not backend.capability.handles(request.target):
                raise BackendRoutingError(
                    f"backend {routed_name!r} is routed to {request.target!r} "
                    "but does not declare that capability"
                )
            self._validate_request(backend, request)
            return backend

        candidates = tuple(
            backend
            for backend in self.backends
            if backend.capability.handles(request.target)
        )
        if not candidates:
            raise BackendRoutingError(
                f"no backend declares target {request.target!r}"
            )
        if len(candidates) > 1:
            raise BackendRoutingError(
                f"target {request.target!r} is ambiguous across backends: "
                f"{sorted(backend.name for backend in candidates)}; add an explicit route"
            )
        self._validate_request(candidates[0], request)
        return candidates[0]

    @staticmethod
    def _validate_request(
        backend: WorldModelBackend, request: PredictionRequest
    ) -> None:
        missing = sorted(
            set(backend.capability.required_inputs) - set(request.inputs)
        )
        if missing:
            raise BackendRoutingError(
                f"backend {backend.name!r} requires missing inputs: {missing}"
            )
        if request.intervention is not None and not (
            backend.capability.supports_interventions
        ):
            raise BackendRoutingError(
                f"backend {backend.name!r} does not support interventions"
            )
        if request.timestamp_s is not None and not backend.capability.supports_temporal:
            raise BackendRoutingError(
                f"backend {backend.name!r} does not support temporal requests"
            )

    def predict(self, request: PredictionRequest) -> PredictionEstimate:
        backend = self.backend_for(request)
        estimate = backend.predict(request)
        if estimate.target != request.target:
            raise BackendRoutingError(
                f"backend {backend.name!r} returned target {estimate.target!r} "
                f"for request {request.target!r}"
            )
        if estimate.backend != backend.name:
            raise BackendRoutingError(
                f"backend {backend.name!r} returned mismatched backend label "
                f"{estimate.backend!r}"
            )
        return estimate

    def to_dict(self) -> dict[str, object]:
        return {
            "backends": [
                {
                    "name": backend.name,
                    "capability": backend.capability.to_dict(),
                }
                for backend in sorted(self.backends, key=lambda item: item.name)
            ],
            "routes": dict(sorted(self.routes.items())),
        }


__all__ = [
    "BackendCapability",
    "BackendRoutingError",
    "CompositeWorldModel",
    "PredictionEstimate",
    "PredictionRequest",
    "WorldModelBackend",
]
