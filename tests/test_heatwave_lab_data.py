"""The Heatwave site data is rebuilt from committed result files.

The e003 blocks (packing, outage, cost, audit) come from files inside this
repo, so they can be rebuilt here and compared with the committed site data.
The blocks that read the Heatwave repo are not rebuilt here; the test only
checks that they report a pending state when that repo is not given.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_heatwave_lab_data.py"
LAB = ROOT / "docs" / "data" / "e003-heatwave-lab-v1.json"
STORY = ROOT / "docs" / "data" / "e003-heatwave-story-v1.json"


def _builder():
    spec = importlib.util.spec_from_file_location("build_heatwave_lab_data", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _roundtrip(x):
    return json.loads(json.JSONEncoder(allow_nan=False).encode(x))


def test_e003_blocks_match_committed_data():
    b = _builder()
    lab = json.loads(LAB.read_text())
    for name, fn in [("packing", b.packing_block), ("outage", b.outage_block), ("cost", b.cost_block), ("audit", b.audit_block)]:
        assert _roundtrip(fn()) == lab[name], f"{name} block differs from {LAB.name}; rebuild with the script"


def test_story_file_is_lab_file_without_replay_traces():
    lab = json.loads(LAB.read_text())
    story = json.loads(STORY.read_text())
    assert "runs" in lab["packing"]["trace"]
    assert "runs" not in story["packing"]["trace"]
    for key in ("outage", "cost", "audit", "ablation", "story_numbers"):
        assert story[key] == lab[key]


def test_heatwave_repo_blocks_are_pending_without_the_repo():
    b = _builder()
    blocks = b.heatwave_blocks(None)
    assert blocks, "expected the Heatwave repo blocks to be present"
    for name, block in blocks.items():
        assert block.get("status") == "pending", f"{name} should be pending when no Heatwave repo is given"


def test_story_numbers_have_unique_ids_and_sources():
    lab = json.loads(LAB.read_text())
    ids = [n["id"] for n in lab["story_numbers"]]
    assert len(ids) == len(set(ids))
    for n in lab["story_numbers"]:
        assert n["text"] and n["source"], n["id"]
