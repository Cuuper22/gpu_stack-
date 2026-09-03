from __future__ import annotations

import json
import gzip
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "data"


def test_webmcp_projection_is_bound_complete_and_columnar() -> None:
    with gzip.open(DATA / "webmcp-run-projection-v1.json.gz", "rt", encoding="utf-8") as handle:
        projection = json.load(handle)
    compact = json.loads((DATA / "e001-semantic-consistency-v1.json").read_text())

    raw_binding = compact["full_trace"]["raw_trace_artifact"]
    compact_runs = compact["full_trace"]["run_ledger"]
    projected_runs = projection["runs"]
    columns = projection["epoch_columns"]

    assert projection["schema"] == "gpustack.webmcp-run-projection.v1"
    assert projection["experiment_id"] == compact["experiment_id"] == "E001-SC1"
    assert projection["source_artifact_sha256"] == raw_binding["artifact_sha256"]
    assert projection["source_schema"] == raw_binding["schema"]
    assert projection["source_epoch_count"] == projection["projected_epoch_count"] == 12_981
    assert len(projected_runs) == len(compact_runs) == 56
    assert {run["run_id"] for run in projected_runs} == {run["run_id"] for run in compact_runs}
    assert sum(run["epoch_count"] for run in projected_runs) == 12_981

    assert len(columns) == len(set(columns)) == 29
    assert columns[:7] == [
        "index",
        "wall_tick",
        "logical_tick_before",
        "logical_tick_after",
        "action",
        "selected_mode",
        "commit_outcome",
    ]
    assert "abstained" in columns
    assert "ood" in columns
    assert "modeled_completion_seconds" in columns

    for run in projected_runs:
        assert run["epoch_count"] == len(run["epochs"])
        assert all(isinstance(row, list) and len(row) == len(columns) for row in run["epochs"])


def test_projection_does_not_copy_heavy_raw_records() -> None:
    projection_path = DATA / "webmcp-run-projection-v1.json.gz"
    with gzip.open(projection_path, "rt", encoding="utf-8") as handle:
        projection_text = handle.read()

    for forbidden in (
        "replica_lineages",
        "replica_disagreement_before",
        "replica_disagreement_after",
        "sample_commitments",
        "token_batch_sha256",
        "model_state_sha256",
        "optimizer_state_sha256",
    ):
        assert forbidden not in projection_text

    assert projection_path.stat().st_size < 300_000
