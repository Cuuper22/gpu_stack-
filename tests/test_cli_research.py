import json
from pathlib import Path

from gpu_stack.cli import main


def test_experiment_protocol_json_is_preregistered(capsys):
    assert main(["experiment-protocol", "E001", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["experiment_id"] == "E001"
    assert len(payload["protocol_hash"]) == 64
    assert {item["falsifier_id"] for item in payload["falsifiers"]} == {
        "e001-progress",
        "e001-wan",
        "e001-time",
    }


def test_experiment_protocol_catalog_is_available_without_claiming_execution(capsys):
    assert main(["experiment-protocol", "E006", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["experiment_id"] == "E006"
    assert payload["title"] == "Firm Grid-responsive Inference"
    assert any("no result" in note for note in payload["notes"])


def test_experiment_run_writes_full_and_observatory_artifacts(tmp_path):
    source = (
        Path(__file__).resolve().parents[1]
        / "experiments"
        / "e001-beyond-one-datacenter"
        / "screening-scenario-v1.json"
    )
    scenario = json.loads(source.read_text(encoding="utf-8"))
    scenario["total_steps"] = 3
    scenario["checkpoint_bytes"] = 0
    scenario["outages"] = []
    scenario_path = tmp_path / "scenario.json"
    scenario_path.write_text(json.dumps(scenario), encoding="utf-8")
    result_path = tmp_path / "result.json"
    observatory_path = tmp_path / "observatory.json"

    assert main(
        [
            "experiment-run",
            "E001",
            "--scenario",
            str(scenario_path),
            "--output",
            str(result_path),
            "--observatory-output",
            str(observatory_path),
        ]
    ) == 0

    result = json.loads(result_path.read_text(encoding="utf-8"))
    observatory = json.loads(observatory_path.read_text(encoding="utf-8"))
    assert result["scenario"]["total_steps"] == 3
    assert result["schema"] == "gpu-stack.e001-comparison.v1"
    assert result["traces_included"] is True
    assert len(result["artifact_sha256"]) == 64
    assert result["runs"][0]["epochs"]
    assert observatory["schema"] == "gpu-stack.causal-observatory.e001.v1"
    assert observatory["status"]["held_out_learning_validation"] is False
    assert len(observatory["observations"]) == 3
    assert observatory["missing_observation_ids"] == []
    assert observatory["source_result"]["artifact_sha256"] == result[
        "artifact_sha256"
    ]
    assert observatory["source_result"]["traces_included"] is True
