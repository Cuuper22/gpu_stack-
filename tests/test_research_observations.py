"""Contracts for immutable measured observations and held-out splits."""

from datetime import datetime, timedelta, timezone
import json

import pytest

from gpu_stack.research.observations import (
    CalibrationEvaluationSplit,
    CalibrationSplit,
    EvaluationSplit,
    MeasuredValue,
    MeasurementUncertainty,
    Observation,
    Provenance,
)


def _observation(observation_id: str = "obs-a") -> Observation:
    return Observation(
        observation_id=observation_id,
        measured_values={
            "training.tokens_per_second": MeasuredValue(
                value=1000.0,
                unit="token/s",
                uncertainty=MeasurementUncertainty(
                    standard_deviation=12.0,
                    lower_bound=976.0,
                    upper_bound=1024.0,
                    confidence_level=0.95,
                    distribution="normal",
                ),
                metadata={"aggregation": "mean", "sample_count": 20},
            )
        },
        timestamp=datetime(
            2026, 7, 12, 11, 30, tzinfo=timezone(timedelta(hours=-7))
        ),
        topology={
            "sites": [{"site_id": "sfo", "gpu_count": 8}],
            "interconnect": "NVLink",
        },
        workload={"model": "synthetic-transformer", "mode": "training"},
        software={"framework": "pytorch", "version": "test-fixture"},
        instrumentation={"collector": "synthetic-fixture", "sampling_hz": 10},
        provenance=Provenance(
            source="synthetic test fixture",
            uri="https://example.invalid/observations/obs-a",
            retrieved_at=datetime(2026, 7, 12, 19, 0, tzinfo=timezone.utc),
            notes=("Not a hardware claim.",),
        ),
        metadata={"tags": ["held-out", "synthetic"]},
    )


def test_measurement_uncertainty_requires_an_explicit_representation():
    with pytest.raises(ValueError, match="requires standard_deviation or bounds"):
        MeasurementUncertainty()

    with pytest.raises(ValueError, match="supplied together"):
        MeasurementUncertainty(lower_bound=1.0)

    with pytest.raises(ValueError, match="confidence_level"):
        MeasurementUncertainty(standard_deviation=1.0, confidence_level=0.95)


def test_measured_value_rejects_nonfinite_and_inconsistent_bounds():
    uncertainty = MeasurementUncertainty(lower_bound=9.0, upper_bound=11.0)
    with pytest.raises(ValueError, match="must be finite"):
        MeasuredValue(float("nan"), "W", uncertainty)
    with pytest.raises(ValueError, match="within its uncertainty bounds"):
        MeasuredValue(12.0, "W", uncertainty)


def test_observation_copies_and_deeply_freezes_all_inputs():
    topology = {"sites": [{"site_id": "sfo", "gpu_count": 8}]}
    measured_values = {
        "power": MeasuredValue(
            100.0,
            "W",
            MeasurementUncertainty(standard_deviation=1.0),
        )
    }
    observation = Observation(
        observation_id="immutable",
        measured_values=measured_values,
        timestamp=datetime(2026, 7, 12, tzinfo=timezone.utc),
        topology=topology,
        workload={"model": "fixture"},
        software={"runtime": "fixture"},
        instrumentation={"meter": "fixture"},
        provenance=Provenance(source="synthetic fixture"),
    )

    topology["sites"][0]["gpu_count"] = 16
    measured_values["other"] = measured_values["power"]

    assert observation.topology["sites"][0]["gpu_count"] == 8
    assert tuple(observation.measured_values) == ("power",)
    with pytest.raises(TypeError):
        observation.topology["new"] = "value"
    with pytest.raises(TypeError):
        observation.topology["sites"][0]["gpu_count"] = 32


def test_observation_requires_a_timezone_and_complete_context():
    kwargs = _observation().to_dict()
    kwargs["timestamp"] = datetime(2026, 7, 12)
    kwargs["measured_values"] = _observation().measured_values
    kwargs["provenance"] = _observation().provenance

    with pytest.raises(ValueError, match="timezone"):
        Observation(**kwargs)

    kwargs["timestamp"] = datetime(2026, 7, 12, tzinfo=timezone.utc)
    kwargs["topology"] = {}
    with pytest.raises(ValueError, match="topology must not be empty"):
        Observation(**kwargs)


def test_observation_serialization_is_canonical_and_round_trips():
    observation = _observation()
    payload = observation.to_json()
    decoded = json.loads(payload)

    assert decoded["timestamp"] == "2026-07-12T18:30:00Z"
    assert payload == observation.to_json()
    assert Observation.from_json(payload) == observation
    assert list(decoded["measured_values"]) == ["training.tokens_per_second"]


def test_split_rejects_duplicates_and_calibration_evaluation_leakage():
    with pytest.raises(ValueError, match="duplicate IDs"):
        CalibrationSplit(("obs-a", "obs-a"))

    with pytest.raises(ValueError, match="overlap.*obs-b"):
        CalibrationEvaluationSplit(
            split_id="leaky",
            calibration=CalibrationSplit(("obs-a", "obs-b")),
            evaluation=EvaluationSplit(("obs-b", "obs-c")),
        )


def test_split_validates_references_and_complete_partition():
    split = CalibrationEvaluationSplit.from_ids(
        split_id="benchmark-v1",
        calibration_ids=("obs-a",),
        evaluation_ids=("obs-b",),
        metadata={"withholding_axis": "topology"},
    )
    observations = (_observation("obs-a"), _observation("obs-b"))

    split.validate_observations(observations, require_complete_partition=True)
    assert CalibrationEvaluationSplit.from_json(split.to_json()) == split

    with pytest.raises(ValueError, match="unknown observation IDs.*obs-b"):
        split.validate_observations(observations[:1])

    with pytest.raises(ValueError, match="not assigned.*obs-c"):
        split.validate_observations(
            observations + (_observation("obs-c"),),
            require_complete_partition=True,
        )
