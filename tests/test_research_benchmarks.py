"""Tests for the research benchmark harness.

A benchmark asks: how well does a prediction backend forecast held-out
measurements? A ``BenchmarkDefinition`` names a metric, a calibration/
evaluation split of observations, and evaluation cases; ``run_benchmark``
scores a backend against them with error, ranking, and decision-regret
statistics. Decision regret is the cost of trusting the model: pick the
configuration the model predicts is best, then measure how much worse it
actually is than the true best.

Most of these tests defend against ways a benchmark can quietly flatter the
model. A case may never point at a calibration observation — that is data
leakage, and construction rejects it. Repeated runs of one configuration
must be declared up front with a preregistered aggregation (mean or median
over an explicit cluster boundary, e.g. trace_id) and are cluster-reduced
before ranking and regret, so a configuration cannot win by being sampled
more often.
"""

from datetime import datetime, timezone

import pytest

from gpu_stack.research.backends import (
    BackendCapability,
    PredictionEstimate,
    PredictionRequest,
)
from gpu_stack.research.benchmarks import (
    BenchmarkAggregation,
    BenchmarkCase,
    BenchmarkDefinition,
    CalibrationMeanBackend,
    run_benchmark,
)
from gpu_stack.research.observations import (
    CalibrationEvaluationSplit,
    MeasurementUncertainty,
    MeasuredValue,
    Observation,
    Provenance,
)


def _observation(observation_id: str, value: float) -> Observation:
    return Observation(
        observation_id=observation_id,
        measured_values={
            "training.step_time": MeasuredValue(
                value=value,
                unit="s",
                uncertainty=MeasurementUncertainty(standard_deviation=0.1),
            )
        },
        timestamp=datetime(2026, 7, 12, tzinfo=timezone.utc),
        topology={"site": observation_id},
        workload={"model": "fixture"},
        software={"runtime": "fixture"},
        instrumentation={"clock": "monotonic"},
        provenance=Provenance(source="test fixture"),
    )


def _split() -> CalibrationEvaluationSplit:
    return CalibrationEvaluationSplit.from_ids(
        split_id="held-out-sites",
        calibration_ids=("cal-a", "cal-b"),
        evaluation_ids=("eval-fast", "eval-slow"),
    )


class InputPredictionBackend:
    name = "input-prediction"
    capability = BackendCapability(
        targets=("training.step_time",),
        required_inputs=("prediction",),
        fidelity="test",
    )

    def predict(self, request: PredictionRequest) -> PredictionEstimate:
        return PredictionEstimate(
            target=request.target,
            value=request.inputs["prediction"],
            unit="s",
            backend=self.name,
        )


def test_calibration_mean_baseline_and_report_measure_decision_regret():
    observations = (
        _observation("cal-a", 5.0),
        _observation("cal-b", 7.0),
        _observation("eval-fast", 3.0),
        _observation("eval-slow", 9.0),
    )
    split = _split()
    model = CalibrationMeanBackend.fit(
        observations, split, "training.step_time"
    )
    definition = BenchmarkDefinition(
        benchmark_id="site-holdout",
        metric="training.step_time",
        objective="minimize",
        split=split,
        cases=(
            BenchmarkCase(
                "fast",
                "eval-fast",
                "fast",
                PredictionRequest("training.step_time", "fast"),
            ),
            BenchmarkCase(
                "slow",
                "eval-slow",
                "slow",
                PredictionRequest("training.step_time", "slow"),
            ),
        ),
        held_out_dimensions=("site",),
    )

    report = run_benchmark(definition, model, observations)

    assert report.mean_absolute_error == 3.0
    assert report.interval_coverage.interval_count == 0
    assert report.ranking.spearman_correlation is None
    assert report.kendall_tau_b.tau_b is None
    assert report.decision_regret.selected_configuration == "fast"
    assert report.decision_regret.regret == 0.0
    assert report.to_dict()["metadata"]["calibration_observation_ids"] == [
        "cal-a",
        "cal-b",
    ]


def test_benchmark_rejects_calibration_observation_as_evaluation_case():
    split = _split()
    with pytest.raises(ValueError, match="evaluation observations"):
        BenchmarkDefinition(
            benchmark_id="leak",
            metric="training.step_time",
            objective="minimize",
            split=split,
            cases=(
                BenchmarkCase(
                    "leak",
                    "cal-a",
                    "leak",
                    PredictionRequest("training.step_time", "leak"),
                ),
            ),
        )


def test_repeated_configurations_are_cluster_reduced_before_rank_and_regret():
    evaluation_values = {
        "a-trace-1-window-1": 10.0,
        "a-trace-1-window-2": 14.0,
        "a-trace-2": 18.0,
        "b-trace-1": 5.0,
        "b-trace-2": 7.0,
    }
    observations = (
        _observation("cal-a", 5.0),
        _observation("cal-b", 7.0),
        *(
            _observation(observation_id, value)
            for observation_id, value in evaluation_values.items()
        ),
    )
    split = CalibrationEvaluationSplit.from_ids(
        split_id="replicated-traces",
        calibration_ids=("cal-a", "cal-b"),
        evaluation_ids=tuple(evaluation_values),
    )
    definition = BenchmarkDefinition(
        benchmark_id="replicated-configurations",
        metric="training.step_time",
        objective="minimize",
        split=split,
        aggregation=BenchmarkAggregation(
            reducer="mean",
            cluster_boundary="trace_id",
        ),
        cases=(
            BenchmarkCase(
                "a-t1-w1",
                "a-trace-1-window-1",
                "a",
                PredictionRequest(
                    "training.step_time", "a-t1-w1", {"prediction": 0.0}
                ),
                cluster_id="trace-1",
            ),
            BenchmarkCase(
                "a-t1-w2",
                "a-trace-1-window-2",
                "a",
                PredictionRequest(
                    "training.step_time", "a-t1-w2", {"prediction": 100.0}
                ),
                cluster_id="trace-1",
            ),
            BenchmarkCase(
                "a-t2",
                "a-trace-2",
                "a",
                PredictionRequest(
                    "training.step_time", "a-t2", {"prediction": 10.0}
                ),
                cluster_id="trace-2",
            ),
            BenchmarkCase(
                "b-t1",
                "b-trace-1",
                "b",
                PredictionRequest(
                    "training.step_time", "b-t1", {"prediction": 20.0}
                ),
                cluster_id="trace-1",
            ),
            BenchmarkCase(
                "b-t2",
                "b-trace-2",
                "b",
                PredictionRequest(
                    "training.step_time", "b-t2", {"prediction": 40.0}
                ),
                cluster_id="trace-2",
            ),
        ),
    )

    report = run_benchmark(definition, InputPredictionBackend(), observations)
    aggregates = {
        aggregate.configuration_id: aggregate
        for aggregate in report.configuration_aggregates
    }
    assert aggregates["a"].replicate_count == 3
    assert aggregates["a"].cluster_count == 2
    assert aggregates["a"].cluster_predicted_values == {
        "trace-1": 50.0,
        "trace-2": 10.0,
    }
    assert aggregates["a"].cluster_observed_values == {
        "trace-1": 12.0,
        "trace-2": 18.0,
    }
    assert aggregates["a"].predicted_value == 30.0
    assert aggregates["a"].observed_value == 15.0
    assert aggregates["b"].predicted_value == 30.0
    assert aggregates["b"].observed_value == 6.0
    assert report.decision_regret.selected_configuration == "a"
    assert report.decision_regret.optimal_configuration == "b"
    assert report.decision_regret.regret == 9.0
    assert report.to_dict()["summary"]["aggregation"] == {
        "cluster_boundary": "trace_id",
        "reducer": "mean",
    }


def test_benchmark_aggregation_is_preregistered_and_case_cluster_defaults_are_explicit():
    with pytest.raises(ValueError, match="mean.*median"):
        BenchmarkAggregation(reducer="last", cluster_boundary="trace")
    with pytest.raises(ValueError, match="cluster_boundary"):
        BenchmarkAggregation(reducer="mean", cluster_boundary=" ")

    case = BenchmarkCase(
        "case-a",
        "eval-fast",
        "a",
        PredictionRequest("training.step_time", "case-a"),
    )
    assert case.cluster_id == "case-a"
    assert BenchmarkAggregation().to_dict() == {
        "cluster_boundary": "case_id",
        "reducer": "mean",
    }


def test_repeated_configurations_require_explicit_preregistered_aggregation():
    split = _split()
    with pytest.raises(ValueError, match="explicit preregistered aggregation"):
        BenchmarkDefinition(
            benchmark_id="implicit-replicates",
            metric="training.step_time",
            objective="minimize",
            split=split,
            cases=(
                BenchmarkCase(
                    "fast-a",
                    "eval-fast",
                    "same-configuration",
                    PredictionRequest("training.step_time", "fast-a"),
                ),
                BenchmarkCase(
                    "slow-a",
                    "eval-slow",
                    "same-configuration",
                    PredictionRequest("training.step_time", "slow-a"),
                ),
            ),
        )
