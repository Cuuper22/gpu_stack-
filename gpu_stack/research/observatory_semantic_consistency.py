"""Three-depth observatory projection for E001-SC1.

The experiment runner owns training, accounting, comparator selection, paired
intervals, and falsifier outcomes.  This module turns that persisted evidence
into two browser artifacts: a compact explanation and a separately loaded raw
optimizer-commit trace.  The browser never recomputes a scientific result.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from itertools import product
from typing import Any


SCHEMA = "gpu-stack.causal-observatory.e001-semantic-consistency.v1"
RAW_SCHEMA = "gpu-stack.causal-observatory.e001-semantic-consistency.raw.v1"
RESULT_SCHEMA = "gpu-stack.e001-semantic-consistency-result.v1"

_HEX = frozenset("0123456789abcdef")
_ADAPTIVE = "observable_adaptive"
_ORACLE = "future_trace_oracle"

_EFFECT_SPECS: tuple[dict[str, Any], ...] = (
    {
        "effect_id": "adaptive_minus_best_fixed_final_nll",
        "aliases": (
            "adaptive_minus_best_fixed_final_nll",
            "adaptive_minus_comparator_final_nll",
            "adaptive_minus_fixed_final_nll",
        ),
        "label": "Held-out learning",
        "outcome_id": "adaptive_learning_noninferiority",
        "format": "signed",
        "boundary": "Paired 90% upper bound must be at most +0.01 NLL.",
        "evidence_class": "observed",
    },
    {
        "effect_id": "adaptive_to_best_fixed_inter_site_payload_ratio",
        "aliases": (
            "adaptive_to_best_fixed_inter_site_payload_ratio",
            "adaptive_to_comparator_inter_site_payload_ratio",
            "adaptive_to_fixed_inter_site_payload_ratio",
            "inter_site_payload_ratio",
        ),
        "label": "Inter-site payload",
        "outcome_id": "adaptive_inter_site_payload_ratio",
        "format": "ratio",
        "boundary": "Paired 90% ratio upper bound must be at most 0.20×.",
        "evidence_class": "observed",
    },
    {
        "effect_id": "adaptive_to_best_fixed_modeled_completion_time_ratio",
        "aliases": (
            "adaptive_to_best_fixed_modeled_completion_time_ratio",
            "adaptive_to_comparator_modeled_completion_time_ratio",
            "adaptive_to_fixed_modeled_completion_time_ratio",
            "modeled_completion_time_ratio",
        ),
        "label": "Virtual completion time",
        "outcome_id": "adaptive_modeled_completion_time_ratio",
        "format": "ratio",
        "boundary": "Paired 90% ratio upper bound must be at most 0.90×.",
        "evidence_class": "modeled",
    },
    {
        "effect_id": "adaptive_normalized_oracle_regret",
        "aliases": (
            "adaptive_normalized_oracle_regret",
            "normalized_oracle_regret",
            "oracle_regret",
        ),
        "label": "Hindsight policy-envelope gap",
        "outcome_id": "adaptive_normalized_oracle_regret",
        "format": "ratio",
        "boundary": "Paired 90% whole-policy-envelope regret upper bound must be at most 0.10.",
        "evidence_class": "modeled",
    },
)


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _artifact_hash(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _json_clone(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True, allow_nan=False))


def _mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be an object")
    return value


def _array(value: object, name: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(
        value, Sequence
    ):
        raise TypeError(f"{name} must be an array")
    return value


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-blank string")
    return value.strip()


def _sha256(value: object, name: str) -> str:
    digest = _text(value, name)
    if len(digest) != 64 or any(character not in _HEX for character in digest):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return digest


def _finite(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _first(mapping: Mapping[str, Any], names: Sequence[str]) -> Any:
    for name in names:
        if name in mapping:
            return mapping[name]
    return None


def _validate_source_result(result: Mapping[str, Any]) -> None:
    if result.get("schema") != RESULT_SCHEMA:
        raise ValueError("source result schema is not E001-SC1")
    if result.get("experiment_id") != "E001-SC1":
        raise ValueError("source result experiment_id is not E001-SC1")
    _text(result.get("scenario_id"), "scenario_id")
    claimed_hash = _sha256(result.get("artifact_sha256"), "artifact_sha256")
    unhashed = dict(result)
    del unhashed["artifact_sha256"]
    if _artifact_hash(unhashed) != claimed_hash:
        raise ValueError("source result artifact_sha256 does not match its payload")

    _mapping(result.get("work_contract"), "work_contract")
    _mapping(result.get("summary"), "summary")
    _mapping(result.get("falsifiers"), "falsifiers")
    _mapping(result.get("uncertainty"), "uncertainty")
    comparator = _mapping(
        result.get("comparator_selection"), "comparator_selection"
    )
    selected = comparator.get("selected_policy_id") or comparator.get(
        "selected_comparator"
    )
    _text(selected, "comparator_selection.selected_policy_id")
    selection_split = comparator.get("selection_split", "calibration_only")
    if selection_split != "calibration_only":
        raise ValueError("fixed comparator was not selected on calibration only")
    evaluation_used = comparator.get(
        "evaluation_data_used", comparator.get("uses_evaluation_data", False)
    )
    if evaluation_used is not False:
        raise ValueError("fixed comparator selection used evaluation data")

    runs = _array(result.get("runs"), "runs")
    if not runs:
        raise ValueError("source result has no runs")
    run_ids: set[str] = set()
    for index, raw_run in enumerate(runs):
        run = _mapping(raw_run, f"runs[{index}]")
        run_id = _text(run.get("run_id"), f"runs[{index}].run_id")
        if run_id in run_ids:
            raise ValueError(f"duplicate run_id: {run_id}")
        run_ids.add(run_id)
        _text(run.get("policy_id"), f"runs[{index}].policy_id")
        _text(
            run.get("family_or_stratum_id"),
            f"runs[{index}].family_or_stratum_id",
        )
        _array(run.get("epoch_trace"), f"runs[{index}].epoch_trace")

    families = _array(result.get("family_results"), "family_results")
    if not families:
        raise ValueError("source result has no evaluation-family results")
    for index, raw_family in enumerate(families):
        family = _mapping(raw_family, f"family_results[{index}]")
        _text(family.get("family_id"), f"family_results[{index}].family_id")


def _selected_comparator(result: Mapping[str, Any]) -> str:
    comparator = _mapping(result["comparator_selection"], "comparator_selection")
    return _text(
        comparator.get("selected_policy_id")
        or comparator.get("selected_comparator"),
        "comparator_selection.selected_policy_id",
    )


def _source_result_binding(
    result: Mapping[str, Any], source_uri: str | None
) -> dict[str, Any]:
    binding: dict[str, Any] = {
        "schema": result["schema"],
        "artifact_sha256": result["artifact_sha256"],
        "uri": source_uri,
    }
    for key in ("engine_id", "scenario_sha256", "engine_source_sha256"):
        if key in result:
            binding[key] = _json_clone(result[key])
    if "bindings" in result:
        binding["bindings"] = _json_clone(result["bindings"])
    return binding


def _run_index(result: Mapping[str, Any]) -> dict[tuple[str, str], Mapping[str, Any]]:
    index: dict[tuple[str, str], Mapping[str, Any]] = {}
    for raw_run in result["runs"]:
        run = _mapping(raw_run, "run")
        if run.get("split") != "evaluation":
            continue
        index[(str(run["family_or_stratum_id"]), str(run["policy_id"]))] = run
    return index


def _effect_source(result: Mapping[str, Any]) -> Mapping[str, Any]:
    uncertainty = _mapping(result["uncertainty"], "uncertainty")
    raw = uncertainty.get("paired_effects")
    if isinstance(raw, Mapping):
        return raw
    summary = _mapping(result["summary"], "summary")
    raw = summary.get("paired_effects")
    return raw if isinstance(raw, Mapping) else {}


def _falsifier_outcomes(result: Mapping[str, Any]) -> Mapping[str, Any]:
    falsifiers = _mapping(result["falsifiers"], "falsifiers")
    raw = falsifiers.get("outcomes")
    if isinstance(raw, Mapping):
        return raw
    return falsifiers


def _effect_interval(effect: Mapping[str, Any]) -> tuple[float | None, float | None, float | None]:
    median = _finite(
        _first(effect, ("median", "estimate", "point_estimate", "value"))
    )
    lower = _finite(
        _first(
            effect,
            ("lower", "lower_bound", "interval_lower", "p05"),
        )
    )
    upper = _finite(
        _first(
            effect,
            ("upper", "upper_bound", "interval_upper", "p95"),
        )
    )
    interval = effect.get("interval")
    if isinstance(interval, Mapping):
        lower = lower if lower is not None else _finite(
            _first(interval, ("lower", "lower_bound", "p05"))
        )
        upper = upper if upper is not None else _finite(
            _first(interval, ("upper", "upper_bound", "p95"))
        )
    return median, lower, upper


def _format_number(value: float | None, *, signed: bool = False) -> str:
    if value is None:
        return "not reported"
    if signed:
        return f"{value:+.4f}"
    return f"{value:.4f}".rstrip("0").rstrip(".")


def _format_effect(value: float | None, kind: str) -> str:
    if value is None:
        return "not reported"
    if kind == "ratio":
        return f"{value:.3f}×"
    return _format_number(value, signed=kind == "signed")


def _effect_passed(
    outcome_id: str,
    effect: Mapping[str, Any],
    outcomes: Mapping[str, Any],
) -> bool | None:
    if isinstance(effect.get("passed"), bool):
        return bool(effect["passed"])
    outcome = outcomes.get(outcome_id)
    if isinstance(outcome, bool):
        return outcome
    if isinstance(outcome, Mapping) and isinstance(outcome.get("passed"), bool):
        return bool(outcome["passed"])
    return None


def _paired_effects(result: Mapping[str, Any]) -> list[dict[str, Any]]:
    source = _effect_source(result)
    outcomes = _falsifier_outcomes(result)
    projected: list[dict[str, Any]] = []
    for spec in _EFFECT_SPECS:
        raw = _first(source, spec["aliases"])
        effect = raw if isinstance(raw, Mapping) else {}
        median, lower, upper = _effect_interval(effect)
        confidence = _finite(
            _first(effect, ("confidence_level", "coverage", "level"))
        )
        if confidence is None:
            paired_interval = _mapping(
                result["uncertainty"], "uncertainty"
            ).get("paired_interval")
            if isinstance(paired_interval, Mapping):
                confidence = _finite(paired_interval.get("confidence_level"))
        interval_name = (
            f"{confidence * 100:.0f}% paired interval"
            if confidence is not None
            else "Paired interval"
        )
        passed = _effect_passed(
            str(spec["outcome_id"]), effect, outcomes
        )
        if lower is None or upper is None:
            interval_display = f"{interval_name}: not reported"
        else:
            interval_display = (
                f"{interval_name}: "
                f"{_format_effect(lower, str(spec['format']))} to "
                f"{_format_effect(upper, str(spec['format']))}"
            )
        meaning = (
            "This frozen gate passed."
            if passed is True
            else "This frozen gate failed."
            if passed is False
            else "The result does not contain enough valid evidence to score this gate."
        )
        projected.append(
            {
                "effect_id": spec["effect_id"],
                "label": spec["label"],
                "display_value": _format_effect(median, str(spec["format"])),
                "median": median,
                "lower": lower,
                "upper": upper,
                "interval_display": interval_display,
                "boundary": spec["boundary"],
                "meaning": meaning,
                "passed": passed,
                "evidence_class": spec["evidence_class"],
                "source": _json_clone(effect) if effect else None,
            }
        )
    return projected


def _ratio(numerator: object, denominator: object) -> float | None:
    top = _finite(numerator)
    bottom = _finite(denominator)
    if top is None or bottom is None or bottom == 0.0:
        return None
    return top / bottom


def _run_metric(run: Mapping[str, Any] | None, *path: str) -> Any:
    value: Any = run
    for key in path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value


def _transition_reason(epoch: Mapping[str, Any]) -> str:
    transition = epoch.get("mode_transition")
    if isinstance(transition, Mapping):
        for key in ("reason", "visible_reason", "trigger"):
            if transition.get(key):
                return str(transition[key])
    abstention = epoch.get("abstention_state")
    if isinstance(abstention, Mapping) and abstention.get("abstained"):
        reasons = abstention.get("reasons")
        if isinstance(reasons, Sequence) and not isinstance(reasons, str):
            return "abstained: " + ", ".join(str(reason) for reason in reasons)
        return "controller abstained to its frozen fallback"
    return str(epoch.get("action") or "recorded controller action")


def _mode_intervals(run: Mapping[str, Any]) -> list[dict[str, Any]]:
    trace = _array(run.get("epoch_trace", []), "epoch_trace")
    intervals: list[dict[str, Any]] = []
    for raw_epoch in trace:
        epoch = _mapping(raw_epoch, "epoch_trace entry")
        start = int(epoch.get("wall_tick", len(intervals)))
        mode = str(epoch.get("selected_mode") or epoch.get("action") or "unmeasured")
        reason = _transition_reason(epoch)
        if intervals and intervals[-1]["mode"] == mode:
            intervals[-1]["end_tick"] = max(intervals[-1]["end_tick"], start + 1)
            continue
        intervals.append(
            {
                "start_tick": start,
                "end_tick": start + 1,
                "mode": mode,
                "reason": reason,
                "evidence_class": "observed",
            }
        )
    return intervals


def _event_reason(value: object) -> str:
    if isinstance(value, Mapping):
        for key in ("reason", "event", "action", "site_id", "site"):
            if value.get(key) is not None:
                return str(value[key])
        return _canonical_json(value)
    return str(value)


def _timeline_events(run: Mapping[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for raw_epoch in _array(run.get("epoch_trace", []), "epoch_trace"):
        epoch = _mapping(raw_epoch, "epoch_trace entry")
        tick = int(epoch.get("wall_tick", 0))
        membership = epoch.get("membership_events")
        if isinstance(membership, Mapping):
            for key, kind in (
                ("departures", "membership_departure"),
                ("rejoins", "membership_rejoin"),
            ):
                values = membership.get(key, [])
                if isinstance(values, Sequence) and not isinstance(values, str):
                    for value in values:
                        events.append(
                            {
                                "tick": tick,
                                "event_kind": kind,
                                "reason": _event_reason(value),
                                "evidence_class": "observed",
                            }
                        )
        for field, kind in (
            ("merge_events", "merge"),
            ("recovery_events", "recovery"),
        ):
            values = epoch.get(field, [])
            if isinstance(values, Sequence) and not isinstance(values, str):
                for value in values:
                    events.append(
                        {
                            "tick": tick,
                            "event_kind": kind,
                            "reason": _event_reason(value),
                            "evidence_class": "observed",
                        }
                    )
        abstention = epoch.get("abstention_state")
        if isinstance(abstention, Mapping) and abstention.get("abstained"):
            events.append(
                {
                    "tick": tick,
                    "event_kind": "abstention",
                    "reason": _transition_reason(epoch),
                    "evidence_class": "observed",
                }
            )
    return events


def _timeline_run(run: Mapping[str, Any], *, role: str | None = None) -> dict[str, Any]:
    return {
        "run_id": run["run_id"],
        "policy_id": run["policy_id"],
        "policy_role": role or run.get("policy_role", "evaluation arm"),
        "mode_intervals": _mode_intervals(run),
        "events": _timeline_events(run),
    }


def _timing_sensitivity_completion(
    run: Mapping[str, Any],
    *,
    bandwidth_multiplier: float,
    compute_rate_multiplier: float,
    wan_round_trip_seconds: float,
) -> float | None:
    """Re-evaluate only the frozen virtual timing formula at one envelope corner."""

    if bandwidth_multiplier <= 0.0 or compute_rate_multiplier <= 0.0:
        return None
    trace = run.get("epoch_trace")
    if not isinstance(trace, Sequence) or isinstance(trace, str) or not trace:
        return None
    total = 0.0
    for raw_epoch in trace:
        epoch = _mapping(raw_epoch, "epoch_trace entry")
        modeled_compute = _finite(epoch.get("modeled_compute_seconds"))
        stress = epoch.get("stress")
        if modeled_compute is None or not isinstance(stress, Mapping):
            return None
        bandwidth = _finite(stress.get("bandwidth_bytes_per_second"))
        if bandwidth is None:
            return None
        total += modeled_compute / compute_rate_multiplier
        wan_events = epoch.get("wan_events", [])
        if not isinstance(wan_events, Sequence) or isinstance(wan_events, str):
            return None
        for raw_event in wan_events:
            event = _mapping(raw_event, "wan event")
            payload = _finite(event.get("payload_bytes"))
            if payload is None:
                return None
            if payload <= 0.0:
                continue
            realized_bandwidth = bandwidth * bandwidth_multiplier
            if realized_bandwidth <= 0.0:
                return None
            total += payload / realized_bandwidth + wan_round_trip_seconds
    return total


def _explicit_ranking_regions(
    family: Mapping[str, Any], comparator: str
) -> list[dict[str, Any]] | None:
    raw_regions = family.get("ranking_regions")
    if not isinstance(raw_regions, Sequence) or isinstance(raw_regions, str):
        epistemic = family.get("epistemic_infrastructure")
        if isinstance(epistemic, Mapping):
            raw_regions = epistemic.get("ranking_regions")
    if not isinstance(raw_regions, Sequence) or isinstance(raw_regions, str):
        return None
    regions: list[dict[str, Any]] = []
    for index, raw_region in enumerate(raw_regions):
        region = _mapping(raw_region, "ranking region")
        state = str(
            region.get("state")
            or region.get("ranking_state")
            or "unmeasured"
        )
        regions.append(
            {
                "region_id": str(region.get("region_id") or f"region-{index + 1}"),
                "region_label": str(
                    region.get("region_label")
                    or region.get("label")
                    or f"Region {index + 1}"
                ),
                "lower": float(index),
                "upper": float(index + 1),
                "state": state,
                "comparator_policy_id": str(
                    region.get("comparator_policy_id") or comparator
                ),
                "reason": str(
                    region.get("reason")
                    or region.get("interpretation")
                    or "No region interpretation was reported."
                ),
                "coordinates": _json_clone(
                    region.get("coordinates")
                    or region.get("infrastructure_realization")
                    or {}
                ),
            }
        )
    return regions


def _ranking_regions(
    result: Mapping[str, Any],
    family: Mapping[str, Any],
    adaptive: Mapping[str, Any] | None,
    fixed: Mapping[str, Any] | None,
    comparator: str,
    learning_delta: float | None,
) -> list[dict[str, Any]]:
    explicit = _explicit_ranking_regions(family, comparator)
    if explicit is not None:
        return explicit
    if adaptive is None or fixed is None:
        return [
            {
                "region_id": "missing-paired-runs",
                "region_label": "Missing pair",
                "lower": 0.0,
                "upper": 1.0,
                "state": "unmeasured",
                "comparator_policy_id": comparator,
                "reason": "The paired adaptive and fixed traces required for timing sensitivity are missing.",
            }
        ]

    envelope = _mapping(result["uncertainty"], "uncertainty").get(
        "epistemic_infrastructure_envelope"
    )
    if not isinstance(envelope, Mapping):
        return [
            {
                "region_id": "missing-envelope",
                "region_label": "No envelope",
                "lower": 0.0,
                "upper": 1.0,
                "state": "unmeasured",
                "comparator_policy_id": comparator,
                "reason": "No frozen epistemic infrastructure envelope is bound to this result.",
            }
        ]

    def endpoints(name: str) -> tuple[float, ...]:
        raw = envelope.get(name)
        if not isinstance(raw, Sequence) or isinstance(raw, str):
            return ()
        values = tuple(value for item in raw if (value := _finite(item)) is not None)
        return values

    bandwidth_values = endpoints("bandwidth_realization_multiplier")
    compute_values = endpoints("compute_rate_realization_multiplier")
    rtt_values = endpoints("wan_round_trip_seconds")
    if not bandwidth_values or not compute_values or not rtt_values:
        return [
            {
                "region_id": "incomplete-envelope",
                "region_label": "Incomplete envelope",
                "lower": 0.0,
                "upper": 1.0,
                "state": "unmeasured",
                "comparator_policy_id": comparator,
                "reason": "The frozen bandwidth, compute-rate, or WAN-round-trip endpoints are incomplete.",
            }
        ]

    margin = _finite(
        _mapping(result["comparator_selection"], "comparator_selection").get(
            "quality_margin_nll"
        )
    )
    invalid_reason: str | None = None
    if bool(adaptive.get("diverged")) or bool(fixed.get("diverged")):
        invalid_reason = "At least one paired run diverged, so timing cannot establish a policy winner."
    elif _run_metric(adaptive, "exact_accounting", "work_contract_violations") or _run_metric(
        fixed, "exact_accounting", "work_contract_violations"
    ):
        invalid_reason = "At least one paired run violated the equal-work contract."
    elif learning_delta is None or margin is None:
        invalid_reason = "Learning noninferiority could not be scored for this family."
    elif learning_delta > margin:
        invalid_reason = (
            f"Adaptive final NLL was {learning_delta:+.4f} above the comparator, "
            f"outside the +{margin:.4f} family-level margin."
        )
    elif int(adaptive.get("abstention_count", 0)) > 0 or int(
        adaptive.get("out_of_distribution_epoch_count", 0)
    ) > 0:
        invalid_reason = "The observable controller left calibrated state support and explicitly abstained."

    regions: list[dict[str, Any]] = []
    corners = tuple(product(bandwidth_values, compute_values, rtt_values))
    for index, (bandwidth, compute, rtt) in enumerate(corners):
        adaptive_time = _timing_sensitivity_completion(
            adaptive,
            bandwidth_multiplier=bandwidth,
            compute_rate_multiplier=compute,
            wan_round_trip_seconds=rtt,
        )
        fixed_time = _timing_sensitivity_completion(
            fixed,
            bandwidth_multiplier=bandwidth,
            compute_rate_multiplier=compute,
            wan_round_trip_seconds=rtt,
        )
        if invalid_reason is not None:
            state = (
                "abstain"
                if int(adaptive.get("abstention_count", 0)) > 0
                or int(adaptive.get("out_of_distribution_epoch_count", 0)) > 0
                else "unsupported"
            )
            reason = invalid_reason
        elif adaptive_time is None or fixed_time is None:
            state = "unmeasured"
            reason = "The exact trace lacks a timing input required to project this envelope corner."
        else:
            tolerance = max(abs(adaptive_time), abs(fixed_time), 1.0) * 1e-12
            if adaptive_time < fixed_time - tolerance:
                state = "adaptive_wins"
            elif fixed_time < adaptive_time - tolerance:
                state = "fixed_wins"
            else:
                state = "uncertain"
            reason = (
                f"Timing-formula sensitivity only: adaptive {adaptive_time:.3f}s; "
                f"{comparator} {fixed_time:.3f}s. Learning is held at the measured paired result."
            )
        regions.append(
            {
                "region_id": f"b{bandwidth:g}-c{compute:g}-rtt{rtt:g}",
                "region_label": (
                    f"B {bandwidth:g}× · C {compute:g}× · RTT {rtt * 1000:g} ms"
                ),
                "lower": float(index),
                "upper": float(index + 1),
                "state": state,
                "comparator_policy_id": comparator,
                "reason": reason,
                "coordinates": {
                    "bandwidth_realization_multiplier": bandwidth,
                    "compute_rate_realization_multiplier": compute,
                    "wan_round_trip_seconds": rtt,
                },
                "adaptive_modeled_completion_seconds": adaptive_time,
                "comparator_modeled_completion_seconds": fixed_time,
            }
        )
    return regions


def _ranking_state(
    family: Mapping[str, Any],
    adaptive: Mapping[str, Any] | None,
    regions: Sequence[Mapping[str, Any]],
) -> tuple[str, str | None]:
    if adaptive is not None and (
        int(adaptive.get("abstention_count", 0)) > 0
        or int(adaptive.get("out_of_distribution_epoch_count", 0)) > 0
    ):
        return "abstain", (
            f"Controller abstained {int(adaptive['abstention_count'])} time(s) "
            "outside calibrated state support."
        )
    explicit = family.get("ranking_state")
    if explicit:
        return str(explicit), None
    states = {str(region.get("state", "unmeasured")) for region in regions}
    if not states or states == {"unmeasured"}:
        return "unmeasured", None
    if len(states) > 1:
        return "rank_reverses", None
    return next(iter(states)), None


def _family_projection(
    result: Mapping[str, Any],
    family: Mapping[str, Any],
    run_index: Mapping[tuple[str, str], Mapping[str, Any]],
    comparator: str,
) -> dict[str, Any]:
    family_id = str(family["family_id"])
    adaptive = run_index.get((family_id, _ADAPTIVE))
    fixed = run_index.get((family_id, comparator))
    oracle = run_index.get((family_id, _ORACLE))
    family_effects = family.get("paired_effects")
    if not isinstance(family_effects, Mapping):
        family_effects = {}

    learning_delta = _finite(
        _first(
            family_effects,
            (
                "adaptive_minus_comparator_final_nll",
                "adaptive_minus_best_fixed_final_nll",
                "final_nll_difference",
            ),
        )
    )
    if learning_delta is None and adaptive is not None and fixed is not None:
        adaptive_nll = _finite(adaptive.get("final_held_out_nll"))
        fixed_nll = _finite(fixed.get("final_held_out_nll"))
        if adaptive_nll is not None and fixed_nll is not None:
            learning_delta = adaptive_nll - fixed_nll

    completion_ratio = _finite(
        _first(
            family_effects,
            (
                "adaptive_to_comparator_modeled_completion_time_ratio",
                "adaptive_to_best_fixed_modeled_completion_time_ratio",
                "modeled_completion_time_ratio",
            ),
        )
    )
    if completion_ratio is None:
        completion_ratio = _ratio(
            _run_metric(adaptive, "modeled_infrastructure", "completion_seconds"),
            _run_metric(fixed, "modeled_infrastructure", "completion_seconds"),
        )

    wan_ratio = _finite(
        _first(
            family_effects,
            (
                "adaptive_to_comparator_inter_site_payload_ratio",
                "adaptive_to_best_fixed_inter_site_payload_ratio",
                "inter_site_payload_ratio",
            ),
        )
    )
    if wan_ratio is None:
        wan_ratio = _ratio(
            _run_metric(
                adaptive, "modeled_infrastructure", "inter_site_payload_bytes"
            ),
            _run_metric(fixed, "modeled_infrastructure", "inter_site_payload_bytes"),
        )

    adaptive_replayed = _finite(
        _run_metric(adaptive, "exact_accounting", "replayed_tokens")
    )
    fixed_replayed = _finite(
        _run_metric(fixed, "exact_accounting", "replayed_tokens")
    )
    adaptive_energy = _finite(
        _run_metric(
            adaptive, "measured_local_device_energy", "idle_subtracted_energy_j"
        )
    )
    fixed_energy = _finite(
        _run_metric(
            fixed, "measured_local_device_energy", "idle_subtracted_energy_j"
        )
    )
    regions = _ranking_regions(
        result,
        family,
        adaptive,
        fixed,
        comparator,
        learning_delta,
    )
    ranking_state, abstention_reason = _ranking_state(
        family, adaptive, regions
    )
    timeline_runs: list[dict[str, Any]] = []
    if adaptive is not None:
        timeline_runs.append(_timeline_run(adaptive, role="observable controller"))
    if fixed is not None:
        timeline_runs.append(_timeline_run(fixed, role="calibration-selected fixed comparator"))
    if oracle is not None:
        selected_schedule = oracle.get("selected_whole_policy_schedule")
        selected_run = (
            run_index.get((family_id, str(selected_schedule)))
            if selected_schedule
            else None
        )
        oracle_timeline = _timeline_run(
            selected_run or oracle,
            role="hindsight whole-policy envelope",
        )
        oracle_timeline["source_run_id"] = oracle_timeline["run_id"]
        oracle_timeline["run_id"] = oracle["run_id"]
        oracle_timeline["policy_id"] = _ORACLE
        oracle_timeline["selected_whole_policy_schedule"] = selected_schedule
        timeline_runs.append(oracle_timeline)

    if adaptive_energy is None or fixed_energy is None:
        energy_display = "not measured for both paired runs"
    else:
        energy_display = (
            f"{adaptive_energy:.1f} J adaptive / {fixed_energy:.1f} J fixed local device"
        )
    replay_display = (
        "not reported"
        if adaptive_replayed is None or fixed_replayed is None
        else f"{int(adaptive_replayed):,} adaptive / {int(fixed_replayed):,} fixed tokens"
    )
    return {
        "family_id": family_id,
        "learning_delta": learning_delta,
        "learning_delta_display": _format_number(learning_delta, signed=True),
        "completion_ratio": completion_ratio,
        "completion_ratio_display": _format_effect(completion_ratio, "ratio"),
        "wan_ratio": wan_ratio,
        "wan_ratio_display": _format_effect(wan_ratio, "ratio"),
        "replayed_work_display": replay_display,
        "energy_display": energy_display,
        "ranking_state": ranking_state,
        "abstention_reason": abstention_reason,
        "regions": regions,
        "timeline_runs": timeline_runs,
        "source": _json_clone(family),
    }


def _all_pass(result: Mapping[str, Any]) -> bool | None:
    falsifiers = _mapping(result["falsifiers"], "falsifiers")
    if isinstance(falsifiers.get("all_pass"), bool):
        return bool(falsifiers["all_pass"])
    summary = _mapping(result["summary"], "summary")
    if isinstance(summary.get("all_falsifiers_pass"), bool):
        return bool(summary["all_falsifiers_pass"])
    return None


def _conclusion(result: Mapping[str, Any]) -> str:
    summary = _mapping(result["summary"], "summary")
    conclusion = summary.get("conclusion") or summary.get("status")
    if conclusion:
        return str(conclusion)
    all_pass = _all_pass(result)
    if all_pass is True:
        return "small_model_observable_semantic_slack_survives"
    if all_pass is False:
        return "small_model_observable_semantic_slack_falsified"
    return "insufficient_valid_evidence"


def _plain_status(result: Mapping[str, Any], comparator: str) -> tuple[str, str]:
    conclusion = _conclusion(result)
    all_pass = _all_pass(result)
    if conclusion == "abstain_without_policy_claim":
        return (
            "The controller left calibrated territory and abstained",
            "At least one untouched stress family crossed the calibrated visible-state envelope. "
            f"The fallback is recorded, but no transferable winner claim follows against {comparator}.",
        )
    if all_pass is True:
        return (
            "Adaptive switching survived every frozen gate",
            "On six untouched stress families, the observable controller preserved "
            f"small-model learning and beat the calibration-selected {comparator} "
            "on the preregistered communication, virtual-time, regret, and validity gates.",
        )
    if all_pass is False:
        return (
            "Adaptive switching did not survive the frozen test",
            f"The observable controller did not clear every frozen gate against {comparator}. "
            "The failed effects remain visible below; no controller-win claim follows.",
        )
    return (
        "The evidence does not support a final controller claim",
        f"The persisted result is {conclusion.replace('_', ' ')}. Missing or invalid gates "
        f"prevent a winner claim against {comparator}.",
    )


def _cards(
    result: Mapping[str, Any],
    effects: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for effect in effects:
        passed = effect.get("passed")
        cards.append(
            {
                "label": effect["label"],
                "value": effect["display_value"],
                "detail": f"{effect['interval_display']}. {effect['boundary']}",
                "state": "pass" if passed is True else "fail" if passed is False else "unresolved",
                "evidence_class": effect["evidence_class"],
            }
        )
    evaluation_runs = [
        run
        for run in result["runs"]
        if run.get("split") == "evaluation" and run.get("policy_id") == _ADAPTIVE
    ]
    abstentions = sum(int(run.get("abstention_count", 0)) for run in evaluation_runs)
    violations = sum(
        len(
            _run_metric(run, "exact_accounting", "work_contract_violations")
            or []
        )
        for run in evaluation_runs
    )
    cards.extend(
        (
            {
                "label": "Controller abstentions",
                "value": f"{abstentions:,}",
                "detail": "An abstention is a recorded fallback outside calibrated visible-state support, not a hidden policy choice.",
                "state": "pass" if abstentions == 0 else "unresolved",
                "evidence_class": "observed",
            },
            {
                "label": "Equal-work violations",
                "value": f"{violations:,}",
                "detail": "Exact token, sample, and optimizer-lineage accounting must remain intact before timing or learning comparisons are admissible.",
                "state": "pass" if violations == 0 else "fail",
                "evidence_class": "observed",
            },
        )
    )
    return cards


def _evidence_boundary(result: Mapping[str, Any]) -> dict[str, Any]:
    raw = result.get("evidence_boundary")
    source = raw if isinstance(raw, Mapping) else {}
    stage = str(source.get("stage") or "measured_small_model_plus_virtual_datacenter")
    boundary = {
        "stage": stage,
        "plain_boundary": (
            "Held-out loss and optimizer state are measured here. One post-warm local-step benchmark is frozen for every arm's modeled timing; per-arm wall-clock and device-energy observations are execution-order-confounded and excluded from policy ranking. "
            "Token, lineage, replay, and payload totals are exact accounting. WAN and completion time are virtual-model outputs; facility energy and frontier-scale transfer remain unresolved."
        ),
        "measured_here": _json_clone(source.get("measured_learning", [])),
        "exact_accounting": _json_clone(source.get("exact_accounting", [])),
        "modeled": _json_clone(source.get("modeled_infrastructure", [])),
        "unresolved": _json_clone(
            source.get("unresolved_frontier_scale_transfer", [])
        ),
    }
    for key in (
        "measured_here",
        "exact_accounting",
        "modeled",
        "assumed",
        "prior",
        "unresolved",
        "can_resolve",
        "cannot_resolve",
    ):
        if key in source:
            boundary[key] = _json_clone(source[key])
    boundary["source"] = _json_clone(source)
    return boundary


def _run_ledger(result: Mapping[str, Any]) -> list[dict[str, Any]]:
    ledger: list[dict[str, Any]] = []
    for raw_run in result["runs"]:
        run = copy.deepcopy(dict(_mapping(raw_run, "run")))
        trace = run.pop("epoch_trace")
        run["epoch_count"] = len(trace)
        ledger.append(_json_clone(run))
    return ledger


def build_e001_semantic_consistency_raw_artifact(
    result: Mapping[str, Any],
) -> dict[str, Any]:
    """Preserve every optimizer-commit epoch in a separately loadable artifact."""

    _validate_source_result(result)
    payload: dict[str, Any] = {
        "schema": RAW_SCHEMA,
        "experiment_id": result["experiment_id"],
        "scenario_id": result["scenario_id"],
        "source_result": _source_result_binding(result, None),
        "evidence_boundary": _evidence_boundary(result),
        "epoch_count": sum(len(run["epoch_trace"]) for run in result["runs"]),
        "runs": _json_clone(result["runs"]),
    }
    payload["artifact_sha256"] = _artifact_hash(payload)
    return payload


def build_e001_semantic_consistency_observatory_artifact(
    result: Mapping[str, Any],
    *,
    source_uri: str | None = None,
    raw_trace_uri: str = "e001-semantic-consistency-raw-v1.json",
    raw_trace_sha256: str | None = None,
) -> dict[str, Any]:
    """Project one validated E001-SC1 result; never inspect evaluation data in JS."""

    _validate_source_result(result)
    if raw_trace_sha256 is not None:
        _sha256(raw_trace_sha256, "raw_trace_sha256")
    comparator = _selected_comparator(result)
    effects = _paired_effects(result)
    run_index = _run_index(result)
    families = [
        _family_projection(
            result,
            _mapping(family, "family result"),
            run_index,
            comparator,
        )
        for family in result["family_results"]
    ]
    headline, plain_answer = _plain_status(result, comparator)
    all_pass = _all_pass(result)
    conclusion = _conclusion(result)
    uncertainty = _mapping(result["uncertainty"], "uncertainty")
    paired_interval = uncertainty.get("paired_interval")
    confidence = (
        _finite(paired_interval.get("confidence_level"))
        if isinstance(paired_interval, Mapping)
        else None
    )
    if confidence is None:
        for raw_effect in _effect_source(result).values():
            if isinstance(raw_effect, Mapping):
                confidence = _finite(raw_effect.get("confidence_level"))
                if confidence is not None:
                    break
    interval_label = (
        f"{confidence * 100:.0f}% paired bootstrap intervals"
        if confidence is not None
        else "paired intervals reported by the engine"
    )
    epoch_count = sum(len(run["epoch_trace"]) for run in result["runs"])
    narrative_family = families[0]["family_id"] if families else None
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "experiment_id": result["experiment_id"],
        "scenario_id": result["scenario_id"],
        "semantic_depths": ["freshman", "researcher", "full_trace"],
        "question": _mapping(result["summary"], "summary").get(
            "research_question",
            "Can observable training-system state identify useful semantic slack across changing network, compute, and membership conditions?",
        ),
        "source_result": _source_result_binding(result, source_uri),
        "status": {
            "conclusion": conclusion,
            "all_falsifiers_pass": all_pass,
            "stage": _evidence_boundary(result)["stage"],
            "validation": "valid for scoring" if all_pass is not None else "insufficient valid evidence",
            "plain_answer": plain_answer,
        },
        "comparison": {
            "selected_fixed_policy_id": comparator,
            "selection_split": "calibration_only",
            "evaluation_data_used": False,
            "selection": _json_clone(result["comparator_selection"]),
        },
        "work_contract": _json_clone(result["work_contract"]),
        "freshman": {
            "headline": headline,
            "plain_answer": plain_answer,
            "boundary": "This is measured small-model learning inside a virtual two-site datacenter, not a frontier-scale or facility-energy result.",
            "explanation": (
                "Every arm receives the same ordered token quotas and must finish the same useful work. "
                "The cards separate measured learning, exact work and communication accounting, modeled virtual time, and unresolved transfer."
            ),
            "cards": _cards(result, effects),
        },
        "researcher": {
            "explanation": (
                "The fixed comparator is selected on calibration only. Effects pair adaptive and fixed runs within each untouched stress family; sampling intervals and infrastructure-model sensitivity are not conflated."
            ),
            "interval_label": interval_label,
            "paired_effects": effects,
            "family_results": families,
            "ranking_map": {
                "domain": {
                    "label": "Enumerated epistemic infrastructure regions",
                    "lower": 0.0,
                    "upper": float(
                        max((len(family["regions"]) for family in families), default=1)
                    ),
                    "unit": "region index",
                },
                "families": [
                    {
                        "family_id": family["family_id"],
                        "regions": family["regions"],
                    }
                    for family in families
                ],
            },
        },
        "evidence_boundary": _evidence_boundary(result),
        "full_trace": {
            "narrative_family_id": narrative_family,
            "run_ledger": _run_ledger(result),
            "raw_trace_artifact": {
                "schema": RAW_SCHEMA,
                "uri": raw_trace_uri,
                "artifact_sha256": raw_trace_sha256,
                "epoch_count": epoch_count,
            },
            "assumptions": _json_clone(result.get("assumptions", [])),
            "uncertainty": _json_clone(result["uncertainty"]),
            "missing_evidence": _json_clone(result.get("missing_evidence", [])),
            "bindings": _json_clone(result.get("bindings", {})),
        },
    }
    payload["artifact_sha256"] = _artifact_hash(payload)
    return payload


__all__ = [
    "RAW_SCHEMA",
    "RESULT_SCHEMA",
    "SCHEMA",
    "build_e001_semantic_consistency_observatory_artifact",
    "build_e001_semantic_consistency_raw_artifact",
]
