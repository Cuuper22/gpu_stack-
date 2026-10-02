"""Build docs/data/published-runs.json for the accuracy figure.

Reads the 27 published runs in gpu_stack/data/published_runs.json (citations
included) and the calculator, and writes one row per run: reported GPU-hours,
the one-line rule of thumb at 40 percent MFU, and the calculator's own
prediction. Everything is per trillion training tokens so that the three
throughput-only MT-NLG rows can sit beside full training runs.

Run from the repository root:  python scripts/build_accuracy_figure_data.py
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gpu_stack import calculator  # noqa: E402

OUT = ROOT / "docs" / "data" / "published-runs.json"
MFU = 0.40
PER_TRILLION_TOKENS = 1e12


def _cites(entries: list[dict] | None, sources: dict) -> list[dict]:
    out = []
    for c in entries or []:
        src = sources.get(c["src"], {})
        out.append(
            {
                "source": src.get("what", c["src"]),
                "url": src.get("url"),
                "where": c.get("where"),
                "quote": c.get("quote"),
            }
        )
    return out


def _median_error(pairs: list[tuple[float, float]]) -> float:
    return statistics.median(abs(pred / rep - 1.0) for pred, rep in pairs)


def main() -> None:
    doc = calculator.load_published_runs()
    sources = doc["sources"]
    rows = []
    rule_pairs: list[tuple[float, float]] = []
    graph_pairs: list[tuple[float, float]] = []
    for r in doc["runs"]:
        hw = doc["hardware"][r["accelerator"]]
        chip = calculator.GPU(
            r["accelerator"], r["accelerator"], hw["peak_flops_dense_16bit"], hw["tdp_w"] or 0.0,
            0.0, 0.0, "", "",
        )
        est = calculator.estimate(
            r["params"], r["tokens"], gpu=chip, n_gpus=r["n_gpus"] or 1024, gpu_price=0.0
        )
        scale = PER_TRILLION_TOKENS / r["tokens"]
        reported = r["gpu_hours"] * scale
        rule = 6.0 * r["params"] * r["tokens"] / (MFU * hw["peak_flops_dense_16bit"]) / 3600.0 * scale
        graph = est.gpu_hours * scale
        rule_pairs.append((rule, reported))
        graph_pairs.append((graph, reported))
        benchmark = "one training step" in (r.get("note") or "")
        rows.append(
            {
                "id": r["id"],
                "name": r["name"],
                "family": r["family"],
                "tier": "A",
                "kind": "throughput_benchmark" if benchmark else "training_run",
                "accelerator": r["accelerator"],
                "params": r["params"],
                "tokens": None if benchmark else r["tokens"],
                "reported_gpu_hours": None if benchmark else r["gpu_hours"],
                "reported_per_trillion_tokens": round(reported, 1),
                "predicted_rule_40pct_mfu_per_trillion_tokens": round(rule, 1),
                "predicted_graph_per_trillion_tokens": round(graph, 1),
                "citations": {
                    "params": _cites(r.get("params_cite"), sources),
                    "reported": _cites(r.get("cite"), sources),
                    "accelerator": _cites(hw.get("cite"), sources),
                },
            }
        )

    out = {
        "description": (
            "27 published runs, as accelerator-hours per trillion training tokens so that "
            "three throughput-only benchmarks (MT-NLG) can sit beside full training runs. "
            "Predicted at 40 percent MFU (6 x params x tokens / (0.4 x peak speed)) next to "
            "the calculator's own prediction, and what each paper reports. Some rows are TPU-hours."
        ),
        "built_from": [
            "gpu_stack/data/published_runs.json",
            "gpu_stack/calculator.py",
        ],
        "mfu": MFU,
        "median_error": {
            "rule_of_thumb": _median_error(rule_pairs),
            "graph": _median_error(graph_pairs),
        },
        "rows": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)} with {len(rows)} rows")


if __name__ == "__main__":
    main()
