"""CLI handlers for preregistered GPUSTACK research experiments."""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
from typing import Any

from .research.e001 import E001Scenario, run_e001
from .research.e001_recovery_artifact import build_e001_recovery_result
from .research.e001_recovery_runner import (
    E001RecoveryScenario,
    run_e001_recovery_v2,
)
from .research.e001_recovery_v2 import E001_RECOVERY_V2_PROTOCOL
from .research.observations import Observation
from .research.observatory import build_e001_observatory_artifact
from .research.observatory_recovery import (
    build_e001_recovery_observatory_artifact,
)
from .research.programs import protocol_for


def _write_json_artifact(payload: dict[str, Any], output: str) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if output == "-":
        print(text, end="")
        return
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _load_observations(paths: list[str] | None) -> tuple[Observation, ...]:
    if paths:
        documents = tuple(Path(path) for path in paths)
    else:
        default_root = resources.files("gpu_stack").joinpath(
            "data",
            "observations",
            "literature",
            "e001-one-step-delay",
        )
        documents = tuple(
            sorted(
                (
                    entry
                    for entry in default_root.iterdir()
                    if entry.is_file() and entry.name.endswith(".json")
                ),
                key=lambda entry: entry.name,
            )
        )
    return tuple(
        Observation.from_json(document.read_text(encoding="utf-8"))
        for document in documents
    )


def cmd_experiment_protocol(args) -> int:
    protocol = (
        E001_RECOVERY_V2_PROTOCOL
        if args.experiment == "E001-RECOVERY-V2"
        else protocol_for(args.experiment)
    )
    payload = protocol.to_dict()
    payload["protocol_hash"] = protocol.protocol_hash
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False))
        return 0
    print(f"{protocol.experiment_id}: {protocol.title}")
    print(f"protocol_hash: {protocol.protocol_hash}")
    print(f"question: {protocol.question}")
    print(f"hypothesis: {protocol.hypothesis}")
    print("falsifiers:")
    for item in protocol.falsifiers:
        bound = item.operator.value + " " + str(item.threshold)
        if item.upper_threshold is not None:
            bound += " .. " + str(item.upper_threshold)
        print(f"  {item.falsifier_id}: {item.metric} {bound}")
    print("structured evidence requirements:")
    if not protocol.evidence_requirements:
        print("  none")
    for item in protocol.evidence_requirements:
        required = "mandatory" if item.mandatory else "optional"
        print(
            f"  {item.requirement_id}: {required}; earliest "
            f"{item.earliest_resolvable_stage.value}; {item.acceptance_rule}"
        )
    return 0


def cmd_experiment_run(args) -> int:
    if args.experiment == "E001-RECOVERY-V2":
        path = Path(args.scenario)
        scenario = E001RecoveryScenario.from_json_path(path)
        execution = run_e001_recovery_v2(scenario)
        result_payload = build_e001_recovery_result(execution)
        _write_json_artifact(result_payload, args.output)
        if args.observatory_output:
            _write_json_artifact(
                build_e001_recovery_observatory_artifact(
                    result_payload,
                    source_uri=None if args.output == "-" else args.output,
                ),
                args.observatory_output,
            )
        return 0
    if args.experiment != "E001":
        raise ValueError(f"unknown experiment {args.experiment!r}")
    path = Path(args.scenario)
    scenario = E001Scenario.from_json(path.read_text(encoding="utf-8"))
    comparison = run_e001(scenario)
    result_payload = comparison.to_dict(include_traces=True)
    _write_json_artifact(
        result_payload,
        args.output,
    )
    if args.observatory_output:
        _write_json_artifact(
            build_e001_observatory_artifact(
                comparison,
                _load_observations(args.observation),
                source_result={
                    "schema": result_payload["schema"],
                    "artifact_sha256": result_payload["artifact_sha256"],
                    "scenario_sha256": result_payload["scenario_hash"],
                    "engine_source_sha256": result_payload["engine"][
                        "source_sha256"
                    ],
                    "traces_included": result_payload["traces_included"],
                    "uri": None if args.output == "-" else args.output,
                },
            ),
            args.observatory_output,
        )
    return 0


__all__ = ["cmd_experiment_protocol", "cmd_experiment_run"]
