"""Tests for the research prediction-backend routing layer.

A ``CompositeWorldModel`` holds several prediction backends and routes each
``PredictionRequest`` to the one backend whose declared capability matches
the target. Routing must be deterministic and honest: when two backends
both claim a target, the model refuses with an "ambiguous" error unless an
explicit route names the winner, and a backend never receives a request it
declared it cannot serve (missing required inputs, unsupported
interventions).

The rest of the module pins the data contracts. A ``PredictionEstimate``
must be internally consistent — intervals need both bounds, the value must
sit inside them, confidence lives strictly in (0, 1) and requires an
interval. Both request and estimate reject booleans posing as numbers,
non-finite floats, and blank identity strings, and normalize integer inputs
to floats. Strictness here keeps every downstream evaluation trustworthy.
"""

from dataclasses import dataclass

import pytest

from gpu_stack.research.backends import (
    BackendCapability,
    BackendRoutingError,
    CompositeWorldModel,
    PredictionEstimate,
    PredictionRequest,
)


@dataclass(frozen=True)
class FakeBackend:
    name: str
    capability: BackendCapability

    def predict(self, request: PredictionRequest) -> PredictionEstimate:
        return PredictionEstimate(
            target=request.target,
            value=float(request.inputs["x"]),
            unit="s",
            backend=self.name,
            lower=0.5,
            upper=2.0,
            confidence=0.9,
            assumptions=("test-only",),
            provenance=("fixture",),
        )


def test_composite_routes_one_declared_backend():
    backend = FakeBackend(
        "timing",
        BackendCapability(
            targets=("training.*",),
            supports_temporal=True,
            required_inputs=("x",),
            fidelity="test",
        ),
    )
    model = CompositeWorldModel((backend,))
    result = model.predict(
        PredictionRequest(
            target="training.step_time",
            scenario_id="fixture",
            inputs={"x": 1.0},
            timestamp_s=2.0,
        )
    )
    assert result.value == 1.0
    assert result.backend == "timing"


def test_overlapping_backends_require_explicit_route():
    first = FakeBackend("a", BackendCapability(("training.*",), fidelity="test"))
    second = FakeBackend("b", BackendCapability(("training.step_time",), fidelity="test"))
    request = PredictionRequest("training.step_time", "fixture", {"x": 1.0})
    with pytest.raises(BackendRoutingError, match="ambiguous"):
        CompositeWorldModel((first, second)).predict(request)

    routed = CompositeWorldModel(
        (first, second), routes={"training.step_time": "b"}
    )
    assert routed.predict(request).backend == "b"


def test_backend_boundary_rejects_missing_inputs_and_unsupported_actions():
    backend = FakeBackend(
        "static",
        BackendCapability(("power",), required_inputs=("x",), fidelity="test"),
    )
    model = CompositeWorldModel((backend,))
    with pytest.raises(BackendRoutingError, match="missing inputs"):
        model.predict(PredictionRequest("power", "fixture"))
    with pytest.raises(BackendRoutingError, match="does not support interventions"):
        model.predict(
            PredictionRequest(
                "power", "fixture", {"x": 1.0}, intervention={"cap_w": 10}
            )
        )


def test_prediction_interval_contract_is_strict():
    with pytest.raises(ValueError, match="both lower and upper"):
        PredictionEstimate("x", 1.0, "s", "fake", lower=0.0)
    with pytest.raises(ValueError, match="inside"):
        PredictionEstimate("x", 3.0, "s", "fake", lower=0.0, upper=2.0)


@pytest.mark.parametrize("timestamp", [float("nan"), float("inf"), float("-inf")])
def test_prediction_request_rejects_nonfinite_timestamps(timestamp):
    with pytest.raises(ValueError, match="timestamp_s must be finite"):
        PredictionRequest("x", "scenario", timestamp_s=timestamp)


def test_prediction_request_rejects_bool_timestamp_and_normalizes_reals():
    with pytest.raises(TypeError, match="timestamp_s must be a real number"):
        PredictionRequest("x", "scenario", timestamp_s=True)
    with pytest.raises(ValueError, match="timestamp_s must be nonnegative"):
        PredictionRequest("x", "scenario", timestamp_s=-0.1)
    assert PredictionRequest("x", "scenario", timestamp_s=2).timestamp_s == 2.0


def test_prediction_identity_fields_require_strings():
    with pytest.raises(ValueError, match="target must be non-blank"):
        PredictionRequest(1, "scenario")
    with pytest.raises(ValueError, match="scenario_id must be non-blank"):
        PredictionRequest("x", 1)
    with pytest.raises(ValueError, match="unit must be non-blank"):
        PredictionEstimate("x", 1.0, 1, "fake")


@pytest.mark.parametrize("value", [True, False])
def test_prediction_estimate_rejects_bool_numeric_fields(value):
    with pytest.raises(TypeError, match="value must be a real number"):
        PredictionEstimate("x", value, "s", "fake")
    with pytest.raises(TypeError, match="lower must be a real number"):
        PredictionEstimate("x", 1.0, "s", "fake", lower=value, upper=2.0)
    with pytest.raises(TypeError, match="upper must be a real number"):
        PredictionEstimate("x", 1.0, "s", "fake", lower=0.0, upper=value)
    with pytest.raises(TypeError, match="confidence must be a real number"):
        PredictionEstimate(
            "x", 1.0, "s", "fake", lower=0.0, upper=2.0, confidence=value
        )


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_prediction_estimate_rejects_every_nonfinite_numeric_field(value):
    with pytest.raises(ValueError, match="value must be finite"):
        PredictionEstimate("x", value, "s", "fake")
    with pytest.raises(ValueError, match="lower must be finite"):
        PredictionEstimate("x", 1.0, "s", "fake", lower=value, upper=2.0)
    with pytest.raises(ValueError, match="upper must be finite"):
        PredictionEstimate("x", 1.0, "s", "fake", lower=0.0, upper=value)
    with pytest.raises(ValueError, match="confidence must be finite"):
        PredictionEstimate(
            "x", 1.0, "s", "fake", lower=0.0, upper=2.0, confidence=value
        )


def test_prediction_estimate_validates_order_confidence_and_normalizes_reals():
    with pytest.raises(ValueError, match="lower bound exceeds upper"):
        PredictionEstimate("x", 1.0, "s", "fake", lower=2.0, upper=0.0)
    for confidence in (0.0, 1.0, -0.1, 1.1):
        with pytest.raises(ValueError, match="strictly in"):
            PredictionEstimate(
                "x",
                1.0,
                "s",
                "fake",
                lower=0.0,
                upper=2.0,
                confidence=confidence,
            )
    with pytest.raises(ValueError, match="requires an interval"):
        PredictionEstimate("x", 1.0, "s", "fake", confidence=0.9)

    estimate = PredictionEstimate(
        "x", 1, "s", "fake", lower=0, upper=2, confidence=0.9
    )
    assert estimate.value == 1.0
    assert estimate.lower == 0.0
    assert estimate.upper == 2.0
