"""Contract tests for the prediction-evaluation metrics.

This module tests the arithmetic that decides whether a model's predictions
can be trusted. A prediction is compared to its held-out observation, giving
a residual (signed error plus absolute and relative forms). Residuals roll
up into interval coverage — did observations land inside the predicted
intervals as often as the nominal confidence promised? — and into ranking
quality (Spearman and tie-aware Kendall tau-b), decision regret (the cost of
picking the configuration the model preferred), and residual attribution
(splitting an error into named causes with an explicit remainder).

The tests insist the metrics refuse to flatter. No fake ratios when the
observed value is zero. No mixing nominal confidence levels in one coverage
summary — stratify by panel instead, and the panel map must partition the
predictions exactly. Tau-b goes undefined (None) when every pair is jointly
tied rather than pretending correlation. Unit mismatches, wrong observation
links, duplicate ids, and serialized derivatives that contradict their
inputs all raise. Every metric object round-trips through JSON unchanged.
"""

from datetime import datetime, timezone

import pytest

from gpu_stack.research.evaluation import (
    DecisionRegret,
    IntervalCoverage,
    KendallTauB,
    PredictionInterval,
    PredictionRecord,
    RankingCorrelation,
    ResidualAttribution,
    ResidualContribution,
    ResidualMetrics,
    attribute_residual,
    configuration_ranking_correlation,
    configuration_kendall_tau_b,
    decision_regret,
    evaluate_prediction,
    evaluate_predictions,
    summarize_interval_coverage,
    summarize_interval_coverage_stratified,
    StratifiedIntervalCoverage,
)
from gpu_stack.research.observations import (
    MeasuredValue,
    MeasurementUncertainty,
    Observation,
    Provenance,
)


def _observation(
    observation_id: str = "obs-a",
    *,
    value: float = 100.0,
    unit: str = "ms",
) -> Observation:
    return Observation(
        observation_id=observation_id,
        measured_values={
            "step_time": MeasuredValue(
                value=value,
                unit=unit,
                uncertainty=MeasurementUncertainty(standard_deviation=2.0),
            )
        },
        timestamp=datetime(2026, 7, 12, tzinfo=timezone.utc),
        topology={"configuration_id": observation_id},
        workload={"fixture": "synthetic"},
        software={"runtime": "synthetic"},
        instrumentation={"timer": "synthetic"},
        provenance=Provenance(source="synthetic test fixture"),
    )


def _prediction(
    prediction_id: str = "pred-a",
    observation_id: str = "obs-a",
    *,
    value: float = 110.0,
    unit: str = "ms",
    interval: PredictionInterval | None = None,
) -> PredictionRecord:
    return PredictionRecord(
        prediction_id=prediction_id,
        observation_id=observation_id,
        model_id="symbolic-v1",
        metric="step_time",
        predicted_value=value,
        unit=unit,
        interval=interval,
        configuration_id=observation_id,
        created_at=datetime(2026, 7, 12, 1, tzinfo=timezone.utc),
        metadata={"accounting_boundary": ["accelerator", "network"]},
    )


def test_prediction_record_validates_interval_and_round_trips():
    interval = PredictionInterval(90.0, 120.0, 0.95)
    prediction = _prediction(interval=interval)

    assert PredictionRecord.from_json(prediction.to_json()) == prediction
    with pytest.raises(ValueError, match="within its prediction interval"):
        _prediction(value=130.0, interval=interval)
    with pytest.raises(ValueError, match="lower_bound"):
        PredictionInterval(2.0, 1.0, 0.95)


def test_evaluate_prediction_reports_signed_absolute_and_relative_error():
    residual = evaluate_prediction(
        _prediction(interval=PredictionInterval(95.0, 115.0, 0.9)),
        _observation(),
    )

    assert residual.residual == 10.0
    assert residual.absolute_error == 10.0
    assert residual.relative_error == pytest.approx(0.1)
    assert residual.signed_relative_error == pytest.approx(0.1)
    assert residual.interval_covered is True
    assert residual.interval_confidence_level == 0.9


def test_evaluate_prediction_handles_zero_observation_without_fake_ratio():
    residual = evaluate_prediction(
        _prediction(value=2.0),
        _observation(value=0.0),
    )
    assert residual.absolute_error == 2.0
    assert residual.relative_error is None
    assert residual.signed_relative_error is None


def test_evaluate_prediction_rejects_wrong_link_and_units():
    with pytest.raises(ValueError, match="references.*not observation"):
        evaluate_prediction(_prediction(observation_id="obs-other"), _observation())

    with pytest.raises(ValueError, match="unit mismatch"):
        evaluate_prediction(_prediction(unit="s"), _observation())


def test_evaluate_predictions_is_deterministic_and_rejects_duplicate_ids():
    observations = (_observation("obs-a"), _observation("obs-b"))
    predictions = (
        _prediction("pred-b", "obs-b"),
        _prediction("pred-a", "obs-a"),
    )
    residuals = evaluate_predictions(predictions, observations)

    assert tuple(item.prediction_id for item in residuals) == ("pred-a", "pred-b")
    with pytest.raises(ValueError, match="duplicate prediction ID"):
        evaluate_predictions((predictions[0], predictions[0]), observations)


def test_interval_coverage_reports_empirical_and_nominal_gap():
    covered = evaluate_prediction(
        _prediction(
            "covered",
            interval=PredictionInterval(95.0, 115.0, 0.9),
        ),
        _observation(),
    )
    missed = evaluate_prediction(
        _prediction(
            "missed",
            value=120.0,
            interval=PredictionInterval(115.0, 125.0, 0.9),
        ),
        _observation(),
    )
    without_interval = evaluate_prediction(_prediction("point"), _observation())

    coverage = summarize_interval_coverage((covered, missed, without_interval))
    assert coverage.residual_count == 3
    assert coverage.interval_count == 2
    assert coverage.covered_count == 1
    assert coverage.coverage_rate == 0.5
    assert coverage.mean_nominal_confidence == pytest.approx(0.9)
    assert coverage.calibration_error == pytest.approx(-0.4)
    assert IntervalCoverage.from_json(coverage.to_json()) == coverage


def test_mixed_nominal_levels_require_confidence_and_panel_stratification():
    residuals = (
        evaluate_prediction(
            _prediction("p50", interval=PredictionInterval(90.0, 110.0, 0.5)),
            _observation(),
        ),
        evaluate_prediction(
            _prediction(
                "p90",
                value=120.0,
                interval=PredictionInterval(115.0, 125.0, 0.9),
            ),
            _observation(),
        ),
        evaluate_prediction(
            _prediction("p95", interval=PredictionInterval(90.0, 130.0, 0.95)),
            _observation(),
        ),
        evaluate_prediction(_prediction("point"), _observation()),
    )

    with pytest.raises(ValueError, match="mixed nominal confidence levels"):
        summarize_interval_coverage(residuals)

    summary = summarize_interval_coverage_stratified(
        residuals,
        panel_by_prediction_id={
            "p50": "hardware-transfer",
            "p90": "hardware-transfer",
            "p95": "workload-transfer",
            "point": "workload-transfer",
        },
    )
    hardware = summary.panel("hardware-transfer")
    workload = summary.panel("workload-transfer")
    assert summary.residual_count == 4
    assert summary.interval_count == 3
    assert summary.without_interval_count == 1
    assert tuple(level.confidence_level for level in hardware.levels) == (0.5, 0.9)
    assert hardware.levels[0].coverage_rate == 1.0
    assert hardware.levels[1].coverage_rate == 0.0
    assert workload.residual_count == 2
    assert workload.interval_count == 1
    assert workload.without_interval_count == 1
    assert workload.levels[0].confidence_level == 0.95
    assert StratifiedIntervalCoverage.from_json(summary.to_json()) == summary


def test_stratified_coverage_requires_an_exact_panel_partition():
    residual = evaluate_prediction(
        _prediction("p90", interval=PredictionInterval(90.0, 120.0, 0.9)),
        _observation(),
    )
    with pytest.raises(ValueError, match="exactly the residual prediction IDs"):
        summarize_interval_coverage_stratified(
            (residual,), panel_by_prediction_id={}
        )


def test_configuration_ranking_correlation_is_tie_aware_and_dependency_free():
    perfect = configuration_ranking_correlation(
        {"a": 1.0, "b": 2.0, "c": 3.0},
        {"a": 10.0, "b": 20.0, "c": 30.0},
    )
    reversed_ranking = configuration_ranking_correlation(
        {"a": 1.0, "b": 2.0, "c": 3.0},
        {"a": 30.0, "b": 20.0, "c": 10.0},
    )
    tied = configuration_ranking_correlation(
        {"a": 1.0, "b": 1.0, "c": 3.0},
        {"a": 2.0, "b": 2.0, "c": 4.0},
    )

    assert perfect.spearman_correlation == pytest.approx(1.0)
    assert reversed_ranking.spearman_correlation == pytest.approx(-1.0)
    assert tied.spearman_correlation == pytest.approx(1.0)
    assert perfect.predicted_order == ("a", "b", "c")
    assert RankingCorrelation.from_json(perfect.to_json()) == perfect


def test_kendall_tau_b_is_distinct_from_spearman_and_reports_pair_ties():
    predicted = {"a": 1.0, "b": 2.0, "c": 3.0, "d": 4.0}
    observed = {"a": 1.0, "b": 3.0, "c": 2.0, "d": 4.0}
    spearman = configuration_ranking_correlation(predicted, observed)
    kendall = configuration_kendall_tau_b(predicted, observed)

    assert spearman.spearman_correlation == pytest.approx(0.8)
    assert kendall.tau_b == pytest.approx(2.0 / 3.0)
    assert kendall.concordant_pairs == 5
    assert kendall.discordant_pairs == 1
    assert kendall.tau_b != pytest.approx(spearman.spearman_correlation)

    tied = configuration_kendall_tau_b(
        {"a": 1.0, "b": 1.0, "c": 3.0},
        {"a": 1.0, "b": 2.0, "c": 3.0},
    )
    assert tied.concordant_pairs == 2
    assert tied.predicted_only_ties == 1
    assert tied.observed_only_ties == 0
    assert tied.joint_ties == 0
    assert tied.tau_b == pytest.approx(2.0 / (6.0 ** 0.5))
    assert KendallTauB.from_json(tied.to_json()) == tied


def test_kendall_tau_b_is_undefined_when_every_pair_is_jointly_tied():
    result = configuration_kendall_tau_b(
        {"a": 1.0, "b": 1.0},
        {"a": 2.0, "b": 2.0},
    )
    assert result.joint_ties == 1
    assert result.comparable_pair_count == 0
    assert result.tau_b is None


def test_configuration_ranking_requires_identical_configuration_sets():
    with pytest.raises(ValueError, match="configurations differ"):
        configuration_ranking_correlation(
            {"a": 1.0, "b": 2.0},
            {"a": 1.0, "c": 2.0},
        )


def test_decision_regret_measures_consequence_in_both_objective_directions():
    minimize = decision_regret(
        predicted={"a": 1.0, "b": 2.0, "c": 3.0},
        observed={"a": 5.0, "b": 2.0, "c": 4.0},
    )
    maximize = decision_regret(
        predicted={"a": 9.0, "b": 8.0},
        observed={"a": 4.0, "b": 10.0},
        objective="maximize",
    )

    assert minimize.selected_configuration == "a"
    assert minimize.optimal_configuration == "b"
    assert minimize.regret == 3.0
    assert minimize.relative_regret == 1.5
    assert minimize.is_optimal is False
    assert maximize.regret == 6.0
    assert DecisionRegret.from_json(minimize.to_json()) == minimize


def test_residual_attribution_preserves_sign_and_explicit_remainder():
    residual = evaluate_prediction(_prediction(), _observation())
    complete = attribute_residual(
        residual,
        {
            "collective_contention": 6.0,
            "kernel_launch_overhead": 4.0,
        },
    )
    partial = attribute_residual(
        residual,
        (
            ResidualContribution(
                "collective_contention",
                6.0,
                metadata={"method": "counterfactual ablation"},
            ),
        ),
    )

    assert complete.attributed_total == 10.0
    assert complete.unattributed_residual == 0.0
    assert complete.is_complete is True
    assert complete.prediction_id == residual.prediction_id
    assert tuple(item.component for item in complete.contributions) == (
        "collective_contention",
        "kernel_launch_overhead",
    )
    assert partial.unattributed_residual == 4.0
    assert partial.is_complete is False
    assert ResidualAttribution.from_json(complete.to_json()) == complete


def test_residual_metrics_reject_inconsistent_serialized_derivatives():
    residual = evaluate_prediction(_prediction(), _observation())
    serialized = residual.to_dict()
    serialized["absolute_error"] = 999.0

    with pytest.raises(ValueError, match="absolute_error is inconsistent"):
        ResidualMetrics.from_dict(serialized)
