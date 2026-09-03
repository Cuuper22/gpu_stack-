#!/usr/bin/env python3
"""Build the bounded WebMCP epoch projection from the immutable E001-SC1 trace.

The source artifact is intentionally large (roughly 72 MB).  WebMCP tools must
not return or eagerly load that file, so this script preserves the audit fields
needed by ``inspect_run`` while dropping tensors, replica state, and hashes that
are not useful in a short agent interaction.
"""

from __future__ import annotations

import argparse
import gzip
import io
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "docs" / "data" / "e001-semantic-consistency-raw-v1.json"
DEFAULT_OUTPUT = ROOT / "docs" / "data" / "webmcp-run-projection-v1.json.gz"


def _event_count(value: Any, *keys: str) -> int:
    if isinstance(value, list):
        return len(value)
    if not isinstance(value, dict):
        return 0
    return sum(len(value.get(key, [])) for key in keys if isinstance(value.get(key), list))


EPOCH_COLUMNS = [
    "index",
    "wall_tick",
    "logical_tick_before",
    "logical_tick_after",
    "action",
    "selected_mode",
    "commit_outcome",
    "abstained",
    "abstention_reasons",
    "ood",
    "ood_dimensions",
    "active_site_count",
    "wan_bandwidth_bytes_per_second",
    "wan_round_trip_seconds",
    "modeled_completion_seconds",
    "modeled_compute_seconds",
    "modeled_wan_seconds",
    "held_out_nll",
    "recent_gradient_norm",
    "attempted_tokens",
    "useful_tokens",
    "replayed_tokens",
    "discarded_tokens",
    "membership_event_count",
    "merge_event_count",
    "recovery_event_count",
    "wan_event_count",
    "mode_transition_from",
    "mode_transition_to",
]


def _compact_epoch(epoch: dict[str, Any], index: int) -> list[Any]:
    abstention = epoch.get("abstention_state") or {}
    ood = epoch.get("ood_state") or {}
    stress = epoch.get("stress") or {}
    accounting = epoch.get("exact_accounting") or {}
    feature_vector = ood.get("feature_vector") or {}
    transition = epoch.get("mode_transition") or {}
    return [
        index,
        epoch.get("wall_tick"),
        epoch.get("logical_tick_before"),
        epoch.get("logical_tick_after"),
        epoch.get("action"),
        epoch.get("selected_mode"),
        epoch.get("commit_outcome"),
        bool(abstention.get("abstained")),
        abstention.get("reasons") or [],
        bool(ood.get("is_out_of_distribution")),
        ood.get("dimensions") or [],
        feature_vector.get("active_site_count", len(stress.get("active_sites") or [])),
        feature_vector.get(
            "wan_bandwidth_bytes_per_second", stress.get("bandwidth_bytes_per_second")
        ),
        feature_vector.get("wan_latency_seconds"),
        epoch.get("modeled_completion_seconds"),
        epoch.get("modeled_compute_seconds"),
        epoch.get("modeled_wan_seconds"),
        epoch.get("held_out_nll"),
        epoch.get("recent_gradient_norm"),
        accounting.get("attempted_tokens"),
        accounting.get("useful_tokens"),
        accounting.get("replayed_tokens"),
        accounting.get("discarded_tokens"),
        _event_count(epoch.get("membership_events"), "departures", "rejoins"),
        _event_count(epoch.get("merge_events")),
        _event_count(epoch.get("recovery_events")),
        _event_count(epoch.get("wan_events")),
        transition.get("from_mode") if transition else None,
        transition.get("to_mode") if transition else None,
    ]


def build_projection(source: dict[str, Any]) -> dict[str, Any]:
    runs = []
    projected_epoch_count = 0
    for run in source.get("runs", []):
        epoch_trace = [
            _compact_epoch(epoch, index)
            for index, epoch in enumerate(run.get("epoch_trace", []))
        ]
        projected_epoch_count += len(epoch_trace)
        runs.append(
            {
                "run_id": run.get("run_id"),
                "family_or_stratum_id": run.get("family_or_stratum_id"),
                "policy_id": run.get("policy_id"),
                "split": run.get("split"),
                "seed": run.get("seed"),
                "epoch_count": len(epoch_trace),
                "epochs": epoch_trace,
            }
        )

    return {
        "schema": "gpustack.webmcp-run-projection.v1",
        "experiment_id": source.get("experiment_id"),
        "source_schema": source.get("schema"),
        "source_artifact_sha256": source.get("artifact_sha256"),
        "source_epoch_count": source.get("epoch_count"),
        "projected_epoch_count": projected_epoch_count,
        "projection_boundary": (
            "Rows follow epoch_columns. Lossless for listed scalar audit fields; omits tensors, replica state, sample hashes, "
            "and descriptive local-device energy. The immutable raw artifact remains authoritative."
        ),
        "epoch_columns": EPOCH_COLUMNS,
        "runs": runs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    with args.source.open(encoding="utf-8") as handle:
        source = json.load(handle)
    projection = build_projection(source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(projection, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
    if args.output.suffix == ".gz":
        buffer = io.BytesIO()
        with gzip.GzipFile(filename="", mode="wb", fileobj=buffer, compresslevel=9, mtime=0) as handle:
            handle.write(payload)
        args.output.write_bytes(buffer.getvalue())
    else:
        args.output.write_bytes(payload)

    print(
        f"wrote {args.output} with {len(projection['runs'])} runs and "
        f"{projection['projected_epoch_count']} epochs"
    )


if __name__ == "__main__":
    main()
