"""Contract tests for the ``Preset.evaluate_targets`` report artifact.

``evaluate_targets`` takes labeled target variables, resolves each one under
a preset's assignments, and returns a structured report. Each target lands in
one of three states: "ok" (resolved, with a trace), "issues" (inputs missing
or constraints violated, with per-variable diagnostics and per-family
summaries of what is missing), or "error" (the target name is not even a
registered variable).

These tests pin the report's contract: diagnostics classify each missing
input by family and boundary category; the report-level missing-family
summaries deduplicate names shared across targets while per-target counts
stay exact; all counts and label tuples agree between the object and its
``to_dict()`` export; and a fully-resolvable preset yields empty summaries.
The ``_field``/``_optional_field`` helpers read both dict and attribute
styles so the implementation can pick either representation.
"""

from gpu_stack.presets import hardware, scenarios


def _field(obj, name):
    if isinstance(obj, dict):
        return obj[name]
    return getattr(obj, name)


def _optional_field(obj, name, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _target_evaluations(report):
    targets = _optional_field(report, "targets")
    if targets is None:
        targets = _optional_field(report, "target_evaluations")
    if targets is None:
        targets = _optional_field(report, "evaluations")
    assert targets is not None
    return targets


def _target_evaluation(report, label):
    targets = _target_evaluations(report)
    if isinstance(targets, dict):
        return targets[label]
    return next(item for item in targets if _field(item, "label") == label)


def _family_key(summary):
    return _field(summary, "family")


def _summary_key(summary):
    return (
        _field(summary, "family"),
        _field(summary, "boundary_category"),
        _field(summary, "primitive_boundary"),
    )


def _missing_family_summaries(target):
    summaries = _optional_field(target, "missing_family_summaries")
    if summaries is None:
        summaries = _optional_field(target, "missing_families")
    assert summaries is not None
    return summaries


def test_preset_evaluate_targets_reports_resolved_target_artifact():
    preset = scenarios.pythia_70m_dgx_h100_us_2024_industrial_power

    report = preset.evaluate_targets(
        (("tokens_per_second", "training.tokens_per_sec"),)
    )
    target = _target_evaluation(report, "tokens_per_second")

    assert _field(target, "status") == "ok"
    assert _field(target, "target") == "training.tokens_per_sec"
    assert isinstance(_field(target, "value"), str)
    assert _field(target, "missing_count") == 0
    assert _field(target, "violated_constraint_count") == 0
    assert "training.eq.tokens_per_sec" in _field(target, "trace_equations")


def test_preset_evaluate_targets_reports_unresolved_cost_artifact_metadata():
    preset = scenarios.pythia_70m_dgx_h100_us_2024_industrial_power

    report = preset.evaluate_targets(
        (("cost_per_token", scenarios.COST_PER_TOKEN_TARGET),)
    )
    target = _target_evaluation(report, "cost_per_token")

    assert _field(target, "status") == "issues"
    assert _field(target, "target") == scenarios.COST_PER_TOKEN_TARGET
    assert _field(target, "missing_count") > 0
    assert _field(target, "violated_constraint_count") == 0

    unresolved_inputs = _field(target, "unresolved_inputs")
    diagnostics = {_field(item, "variable"): item for item in unresolved_inputs}
    assert "cluster.node.cpu.power_per_cpu" in diagnostics
    assert _field(diagnostics["cluster.node.cpu.power_per_cpu"], "family") == (
        "cluster.node"
    )
    assert _field(
        diagnostics["cluster.node.cpu.power_per_cpu"],
        "boundary_category",
    ) == "primitive-root"
    assert _field(
        diagnostics["cluster.node.cpu.power_per_cpu"],
        "primitive_boundary",
    ) is True

    summaries = {
        _family_key(summary): summary
        for summary in _missing_family_summaries(target)
    }
    assert "cluster.node" in summaries
    assert _field(summaries["cluster.node"], "count") > 0
    assert "cluster.node.storage_power" in _field(summaries["cluster.node"], "names")
    assert "econ.asset" in summaries
    assert "thermal.water" in summaries


def test_preset_evaluate_targets_report_exposes_aggregate_missing_families():
    preset = scenarios.pythia_70m_dgx_h100_us_2024_industrial_power

    report = preset.evaluate_targets(
        (("cost_per_token", scenarios.COST_PER_TOKEN_TARGET),)
    )
    target = _target_evaluation(report, "cost_per_token")

    report_summaries = {
        _family_key(summary): summary
        for summary in _missing_family_summaries(report)
    }
    target_summaries = {
        _family_key(summary): summary
        for summary in _missing_family_summaries(target)
    }

    assert "cluster.node" in report_summaries
    assert _field(report_summaries["cluster.node"], "count") == _field(
        target_summaries["cluster.node"],
        "count",
    )
    assert "cluster.node.storage_power" in _field(
        report_summaries["cluster.node"],
        "names",
    )
    assert "econ.asset" in report_summaries
    assert "thermal.water" in report_summaries

    data = report.to_dict()
    dict_summaries = {
        _family_key(summary): summary
        for summary in data["missing_family_summaries"]
    }
    assert dict_summaries.keys() == report_summaries.keys()
    assert "cluster.node.storage_power" in _field(
        dict_summaries["cluster.node"],
        "names",
    )
    assert data["targets"]["cost_per_token"]["missing_family_summaries"]


def test_preset_evaluate_targets_deduplicates_aggregate_missing_families():
    preset = scenarios.pythia_70m_dgx_h100_us_2024_industrial_power

    report = preset.evaluate_targets(
        (
            ("run_cost", scenarios.DENSE_TRAINING_COST_TARGETS["run_cost"]),
            ("cost_per_token", scenarios.COST_PER_TOKEN_TARGET),
        )
    )
    run_cost = _target_evaluation(report, "run_cost")
    cost_per_token = _target_evaluation(report, "cost_per_token")

    run_missing = set(_field(run_cost, "missing_names"))
    cost_missing = set(_field(cost_per_token, "missing_names"))
    aggregate_missing = {
        name
        for summary in _missing_family_summaries(report)
        for name in _field(summary, "names")
    }

    assert run_missing & cost_missing
    assert aggregate_missing == run_missing | cost_missing
    assert sum(
        _field(summary, "count")
        for summary in _missing_family_summaries(report)
    ) == len(aggregate_missing)
    assert len(aggregate_missing) < (
        _field(run_cost, "missing_count")
        + _field(cost_per_token, "missing_count")
    )

    report_summaries = {
        _summary_key(summary): summary
        for summary in _missing_family_summaries(report)
    }
    run_summaries = {
        _summary_key(summary): summary
        for summary in _missing_family_summaries(run_cost)
    }
    cost_summaries = {
        _summary_key(summary): summary
        for summary in _missing_family_summaries(cost_per_token)
    }
    assert report_summaries.keys() == run_summaries.keys() == cost_summaries.keys()
    for key, report_summary in report_summaries.items():
        assert _field(report_summary, "names") == _field(run_summaries[key], "names")
        assert _field(report_summary, "names") == _field(cost_summaries[key], "names")
        assert _field(report_summary, "count") == _field(run_summaries[key], "count")
        assert _field(report_summary, "count") == _field(cost_summaries[key], "count")

    for target in (run_cost, cost_per_token):
        assert sum(
            _field(summary, "count")
            for summary in _missing_family_summaries(target)
        ) == _field(target, "missing_count")


def test_preset_evaluate_targets_report_has_no_aggregate_missing_families_for_euv():
    preset = scenarios.euv_tin120_lpp_source_context_assumption

    report = preset.evaluate_targets(scenarios.EUV_TIN120_SOURCE_TARGETS.items())

    assert _field(report, "status") == "ok"
    assert _field(report, "issue_count") == 0
    assert _missing_family_summaries(report) == ()

    for target in _target_evaluations(report):
        assert _field(target, "status") == "ok"
        assert _missing_family_summaries(target) == ()

    data = report.to_dict()
    assert data["missing_family_summaries"] == ()


def test_preset_evaluate_targets_report_counts_and_dict_export():
    preset = scenarios.pythia_70m_dgx_h100_us_2024_industrial_power

    report = preset.evaluate_targets(
        (
            ("tokens_per_second", "training.tokens_per_sec"),
            ("cost_per_token", scenarios.COST_PER_TOKEN_TARGET),
        )
    )

    targets = _target_evaluations(report)
    assert _field(report, "issue_count") == sum(
        _field(target, "issue_count") for target in targets
    )
    assert _field(report, "issue_count") > 0
    assert _field(report, "assignment_count") == len(preset.assignments)
    assert _field(report, "variant_count") == len(preset.variants)
    assert _field(report, "ok_count") == 1
    assert _field(report, "issues_count") == 1
    assert _field(report, "error_count") == 0
    assert _field(report, "target_labels") == (
        "tokens_per_second",
        "cost_per_token",
    )
    assert _field(report, "ok_target_labels") == ("tokens_per_second",)
    assert _field(report, "issue_target_labels") == ("cost_per_token",)
    assert _field(report, "error_target_labels") == ()

    if hasattr(report, "to_dict"):
        data = report.to_dict()
        assert data["issue_count"] == _field(report, "issue_count")
        assert data["ok_count"] == 1
        assert data["issues_count"] == 1
        assert data["error_count"] == 0
        assert data["target_labels"] == (
            "tokens_per_second",
            "cost_per_token",
        )
        assert data["ok_target_labels"] == ("tokens_per_second",)
        assert data["issue_target_labels"] == ("cost_per_token",)
        assert data["error_target_labels"] == ()
        assert data["assignment_count"] == len(preset.assignments)
        assert data["variant_count"] == len(preset.variants)
        assert data["targets"]["tokens_per_second"]["status"] == "ok"
        assert data["targets"]["cost_per_token"]["status"] == "issues"


def test_preset_evaluate_targets_report_labels_error_targets():
    report = hardware.demo_rack.evaluate_targets(
        (
            ("peak_flops", "cluster.rack.peak_flops"),
            ("unknown_target", "not.a.registered.variable"),
        )
    )
    target = _target_evaluation(report, "unknown_target")

    assert _field(target, "status") == "error"
    assert _field(target, "issue_count") == 1
    assert _field(report, "issue_count") == 1
    assert _field(report, "ok_count") == 1
    assert _field(report, "issues_count") == 1
    assert _field(report, "error_count") == 1
    assert _field(report, "target_labels") == ("peak_flops", "unknown_target")
    assert _field(report, "ok_target_labels") == ("peak_flops",)
    assert _field(report, "issue_target_labels") == ("unknown_target",)
    assert _field(report, "error_target_labels") == ("unknown_target",)

    data = report.to_dict()
    assert data["issue_count"] == 1
    assert data["issues_count"] == 1
    assert data["error_count"] == 1
    assert data["issue_target_labels"] == ("unknown_target",)
    assert data["targets"]["unknown_target"]["status"] == "error"
