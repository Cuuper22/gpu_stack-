"""Build docs/data/published-runs.json for the accuracy figure.

Reads the held-out published runs (primary-source citations included) and the
prediction results, and writes one row per tier-A run: reported GPU-hours, the
one-line rule of thumb at 40 percent MFU, and the calculator's own prediction.

Run from the repository root:  python scripts/build_accuracy_figure_data.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "experiments" / "v002-graph-published-runs"
OUT = ROOT / "docs" / "data" / "published-runs.json"

MFU = 0.40
# results.json stores times as accelerator-seconds per training token.
# Times 1e12 tokens and divided by 3600 that is accelerator-hours per trillion tokens.
TO_HOURS_PER_TRILLION = 1e12 / 3600


def _cites(entry: dict, sources: dict) -> list[dict]:
    out = []
    for c in (entry or {}).get("cite", []):
        src = sources.get(c["src"], {})
        out.append(
            {
                "source": src.get("description", c["src"]),
                "url": src.get("url"),
                "where": c.get("loc"),
                "quote": c.get("quote"),
            }
        )
    return out


def main() -> None:
    held = json.loads((STUDY / "heldout-runs.json").read_text())
    results = json.loads((STUDY / "results" / "results.json").read_text())
    sources = held["sources"]
    graph = {r["id"]: r for r in results["T1_tierA"]["rows"]}

    rows = []
    for rec in held["records"]:
        if rec["tier"] != "A" or "T1" not in rec.get("used_in", []):
            continue
        g = graph[rec["id"]]
        per_tn = g["true"] * TO_HOURS_PER_TRILLION
        tokens = (rec.get("tokens") or {}).get("value")
        reported_total = rec["time"].get("accel_hours", {}).get("value")
        cites = {"params": _cites(rec["params"], sources)}
        if rec.get("tokens"):
            cites["tokens"] = _cites(rec["tokens"], sources)
        for key, entry in rec["time"].items():
            cites[key] = _cites(entry, sources)
        if rec.get("accel_count"):
            cites["accel_count"] = _cites(rec["accel_count"], sources)
        rows.append(
            {
                "id": rec["id"],
                "name": rec["name"],
                "family": rec["family"],
                "tier": "A",
                "kind": rec.get("kind", "training_run"),
                "accelerator": rec["accelerator"],
                "params": rec["params"]["value"],
                "tokens": tokens,
                "reported_gpu_hours": reported_total,
                "reported_per_trillion_tokens": round(per_tn, 1),
                "predicted_rule_40pct_mfu_per_trillion_tokens": round(
                    g["A"] * TO_HOURS_PER_TRILLION, 1
                ),
                "predicted_graph_per_trillion_tokens": round(
                    g["G1"] * TO_HOURS_PER_TRILLION, 1
                ),
                "citations": cites,
            }
        )

    arms = results["T1_tierA"]["arms"]
    doc = {
        "description": (
            "27 published runs, as accelerator-hours per trillion training tokens so that "
            "three throughput-only benchmarks (MT-NLG) can sit beside full training runs. "
            "Predicted at 40 percent MFU (6 x params x tokens / (0.4 x peak speed)) next to "
            "the calculator's own prediction, and what each paper reports. Some rows are TPU-hours."
        ),
        "built_from": [
            "experiments/v002-graph-published-runs/heldout-runs.json",
            "experiments/v002-graph-published-runs/results/results.json",
        ],
        "mfu": MFU,
        "median_error": {
            "rule_of_thumb": arms["A"]["mdape"],
            "graph": arms["G1"]["mdape"],
        },
        "rows": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)} with {len(rows)} rows")


if __name__ == "__main__":
    main()
