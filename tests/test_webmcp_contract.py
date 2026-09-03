"""Chrome-free contract tests for the browser-side WebMCP adapter."""

from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "docs" / "webmcp-tools.js"
OBSERVATORY_HTML = ROOT / "docs" / "observatory.html"

TOOL_ORDER = [
    "get_observatory_state",
    "compare_stress_families",
    "inspect_stress_family",
    "inspect_run",
    "trace_causal_path",
    "open_evidence",
    "compare_policies",
    "stage_conclusion",
]
EXPECTED_TOOLS = set(TOOL_ORDER)
READ_ONLY_TOOLS = set(TOOL_ORDER[:-1])

VALID_CALLS = {
    "get_observatory_state": {},
    "compare_stress_families": {},
    "inspect_stress_family": {"family_id": "E4-failure-inside-wan-collapse"},
    "inspect_run": {
        "run_id": "e001-sc1:evaluation:E6-repeated-membership-loss:future_trace_oracle"
    },
    "trace_causal_path": {
        "from_node": "site_availability",
        "to_node": "time_to_target",
    },
    "open_evidence": {
        "evidence_id": "369bc4e9b32d6e1fcdd8dadc98c830e5ac5179f4a7204a9f5194e22913fdefdf"
    },
    "compare_policies": {
        "policy_ids": ["observable_adaptive", "periodic_local"],
    },
    "stage_conclusion": {
        "conclusion_code": "abstain_without_policy_claim",
        "evidence_ids": [
            "369bc4e9b32d6e1fcdd8dadc98c830e5ac5179f4a7204a9f5194e22913fdefdf",
            "d6321d6fc4c0f71c4f14c2f799eff252348073b3fe5508783f9f078e7f5e9d76",
        ],
        "expected_state_version": 4,
    },
}

INVALID_CALLS = {
    "get_observatory_state": {"invented": True},
    "compare_stress_families": {
        "family_ids": [f"E{index}-family" for index in range(1, 8)]
    },
    "inspect_stress_family": {
        "family_id": "E1-bursty-wan",
        "include_regions": "yes",
    },
    "inspect_run": {"run_id": "run-1", "epoch_limit": 21},
    "trace_causal_path": {
        "from_node": "time_to_target",
        "to_node": "time_to_target",
    },
    "open_evidence": {"evidence_id": "contains a space"},
    "compare_policies": {"policy_ids": ["same", "same"]},
    "stage_conclusion": {
        "conclusion_code": "transferable_winner",
        "evidence_ids": ["E6-repeated-membership-loss"],
        "expected_state_version": 4,
    },
}


NODE_HARNESS = r"""
const fs = require("fs");
const vm = require("vm");
const adapterPath = process.argv[1];
const mode = process.argv[2];
const source = fs.readFileSync(adapterPath, "utf8");
const registered = [];
const invocations = [];
const events = [];

class TestCustomEvent {
  constructor(type, options = {}) { this.type = type; this.detail = options.detail; }
}

const windowObject = {
  dispatchEvent(event) { events.push({ type: event.type, detail: event.detail }); return true; },
};
if (mode !== "no_bridge") {
  windowObject.GPUStackMission = {
    async invoke(name, args, options) {
      invocations.push({ name, args, hasSignal: Boolean(options && options.signal) });
      if (mode === "large_result") {
        return { ok: true, stateVersion: 7, summary: "x".repeat(6000), rows: Array(80).fill("y".repeat(200)) };
      }
      return { ok: true, stateVersion: 7, summary: `completed ${name}` };
    },
  };
}
const documentObject = mode === "unsupported" ? {} : {
  modelContext: {
    async registerTool(tool, options) {
      registered.push({ tool, hasLifecycleSignal: Boolean(options && options.signal) });
    },
  },
};
const context = {
  window: windowObject,
  document: documentObject,
  CustomEvent: TestCustomEvent,
  AbortController,
  console,
  Promise,
  Object,
  Array,
  Number,
  String,
  Boolean,
  Set,
  Error,
  JSON,
};
vm.runInNewContext(source, context, { filename: adapterPath });

(async () => {
  const status = await windowObject.GPUStackWebMCP.ready;
  if (mode === "unsupported") {
    process.stdout.write(JSON.stringify({ supported: windowObject.GPUStackWebMCP.supported, status, events }));
    return;
  }
  if (mode === "metadata") {
    process.stdout.write(JSON.stringify({
      status,
      events,
      tools: registered.map(({ tool, hasLifecycleSignal }) => ({
        name: tool.name,
        title: tool.title,
        description: tool.description,
        inputSchema: tool.inputSchema,
        annotations: tool.annotations,
        executeType: typeof tool.execute,
        hasLifecycleSignal,
      })),
    }));
    return;
  }
  if (mode === "invoke") {
    const calls = JSON.parse(process.argv[3]);
    const results = {};
    for (const { tool } of registered) {
      results[tool.name] = await tool.execute(calls[tool.name], { signal: new AbortController().signal });
    }
    const beforeInvalid = invocations.length;
    const invalid = await registered[0].tool.execute(
      { invented: true },
      { signal: new AbortController().signal },
    );
    process.stdout.write(JSON.stringify({
      results,
      invocations,
      invalid,
      invalidReachedBridge: invocations.length !== beforeInvalid,
    }));
    return;
  }
  if (mode === "validation") {
    const calls = JSON.parse(process.argv[3]);
    const results = {};
    for (const { tool } of registered) {
      results[tool.name] = await tool.execute(calls[tool.name], { signal: new AbortController().signal });
    }
    process.stdout.write(JSON.stringify({ results, invocationCount: invocations.length }));
    return;
  }
  if (mode === "no_bridge" || mode === "large_result") {
    const result = await registered[0].tool.execute({}, { signal: new AbortController().signal });
    process.stdout.write(JSON.stringify({ result }));
    return;
  }
  throw new Error(`Unknown harness mode: ${mode}`);
})().catch((error) => { console.error(error); process.exitCode = 1; });
"""


def _node() -> str:
    executable = shutil.which("node")
    if executable is None:
        pytest.skip("Node is required for JavaScript contract execution")
    return executable


def _run_harness(mode: str, payload: object | None = None) -> dict:
    command = [_node(), "-e", NODE_HARNESS, str(ADAPTER), mode]
    if payload is not None:
        command.append(json.dumps(payload, separators=(",", ":")))
    completed = subprocess.run(
        command,
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    return json.loads(completed.stdout)


def test_adapter_parses_and_uses_current_imperative_api() -> None:
    source = ADAPTER.read_text(encoding="utf-8")
    subprocess.run(
        [_node(), "--check", str(ADAPTER)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert "document.modelContext" in source
    assert ".registerTool(" in source
    assert "navigator.modelContext" not in source
    assert "outputSchema" not in source
    assert "requestUserInteraction" not in source


def test_exact_tools_schemas_and_annotations() -> None:
    result = _run_harness("metadata")
    tools = {tool["name"]: tool for tool in result["tools"]}

    assert list(tools) == TOOL_ORDER
    assert result["status"] == {
        "supported": True,
        "registered": TOOL_ORDER,
        "failed": [],
    }
    assert any(event["type"] == "gpustack:webmcp-ready" for event in result["events"])

    for name, tool in tools.items():
        assert tool["title"].strip()
        assert tool["description"].strip()
        assert len(tool["description"]) <= 500
        assert tool["executeType"] == "function"
        assert tool["hasLifecycleSignal"] is True
        assert tool["inputSchema"]["type"] == "object"
        assert tool["inputSchema"]["additionalProperties"] is False
        assert tool["annotations"]["readOnlyHint"] is (name in READ_ONLY_TOOLS)

    assert tools["stage_conclusion"]["annotations"]["untrustedContentHint"] is True
    assert all(
        tools[name]["annotations"]["untrustedContentHint"] is False
        for name in READ_ONLY_TOOLS
    )
    assert tools["get_observatory_state"]["inputSchema"]["properties"] == {}
    assert tools["stage_conclusion"]["inputSchema"]["required"] == [
        "conclusion_code",
        "evidence_ids",
        "expected_state_version",
    ]


def test_schema_limits_match_the_grounded_artifact_contract() -> None:
    tools = {tool["name"]: tool for tool in _run_harness("metadata")["tools"]}
    schemas = {name: tool["inputSchema"] for name, tool in tools.items()}

    assert schemas["compare_stress_families"]["properties"]["family_ids"]["maxItems"] == 6
    assert schemas["inspect_run"]["properties"]["epoch_offset"]["minimum"] == 0
    assert schemas["inspect_run"]["properties"]["epoch_limit"]["maximum"] == 20
    assert schemas["trace_causal_path"]["properties"]["max_nodes"] == {
        "type": "integer",
        "minimum": 2,
        "maximum": 12,
        "default": 7,
        "description": "Maximum nodes in the returned path. Defaults to 7.",
    }
    assert schemas["compare_policies"]["properties"]["policy_ids"]["maxItems"] == 3
    assert schemas["compare_policies"]["properties"]["metric_ids"]["maxItems"] == 6
    assert schemas["stage_conclusion"]["properties"]["evidence_ids"]["maxItems"] == 8
    assert schemas["stage_conclusion"]["properties"]["conclusion_code"]["enum"] == [
        "abstain_without_policy_claim",
    ]
    assert "claim" not in schemas["stage_conclusion"]["properties"]
    assert "confidence" not in schemas["stage_conclusion"]["properties"]


def test_valid_calls_are_normalized_forwarded_and_compact() -> None:
    result = _run_harness("invoke", VALID_CALLS)

    assert len(result["invocations"]) == 8
    assert {call["name"] for call in result["invocations"]} == EXPECTED_TOOLS
    assert all(call["hasSignal"] for call in result["invocations"])
    assert all(value["ok"] is True for value in result["results"].values())
    assert all(value["tool"] == name for name, value in result["results"].items())
    assert all(
        len(json.dumps(value, separators=(",", ":"))) <= 1500
        for value in result["results"].values()
    )

    calls = {call["name"]: call["args"] for call in result["invocations"]}
    assert calls["get_observatory_state"] == {}
    assert calls["inspect_stress_family"]["include_regions"] is True
    assert calls["inspect_run"]["epoch_offset"] == 0
    assert calls["inspect_run"]["epoch_limit"] == 8
    assert calls["trace_causal_path"]["max_nodes"] == 7
    assert calls["open_evidence"]["semantic_depth"] == "researcher"


def test_invalid_arguments_fail_before_bridge() -> None:
    result = _run_harness("invoke", VALID_CALLS)
    invalid = result["invalid"]
    assert result["invalidReachedBridge"] is False
    assert invalid["ok"] is False
    assert invalid["tool"] == "get_observatory_state"
    assert invalid["code"] == "INVALID_ARGUMENT"
    assert invalid["field"] == "invented"


def test_domain_validation_rejects_bad_calls_before_bridge() -> None:
    result = _run_harness("validation", INVALID_CALLS)
    assert result["invocationCount"] == 0
    assert set(result["results"]) == EXPECTED_TOOLS
    for name, failure in result["results"].items():
        assert failure["ok"] is False, name
        assert failure["tool"] == name
        assert failure["code"] == "INVALID_ARGUMENT"
        assert failure["field"]
        assert failure["expected"]


def test_late_bound_missing_bridge_returns_recoverable_failure() -> None:
    result = _run_harness("no_bridge")["result"]
    assert result == {
        "ok": False,
        "tool": "get_observatory_state",
        "code": "BRIDGE_UNAVAILABLE",
        "message": "GPUSTACK Mission Control is still loading. Retry after the observatory is ready.",
    }


def test_large_bridge_results_are_bounded_for_agent_context() -> None:
    result = _run_harness("large_result")["result"]
    assert result["ok"] is True
    assert result["tool"] == "get_observatory_state"
    assert result["truncated"] is True
    assert len(json.dumps(result, separators=(",", ":"))) <= 1500


@pytest.mark.parametrize("name", TOOL_ORDER)
def test_each_tool_name_is_declared_once(name: str) -> None:
    source = ADAPTER.read_text(encoding="utf-8")
    declared = re.findall(r'^\s+name: "([a-z_]+)",$', source, flags=re.MULTILINE)
    assert declared.count(name) == 1


def test_feature_detection_preserves_normal_page() -> None:
    result = _run_harness("unsupported")
    assert result["supported"] is False
    assert result["status"] == {"supported": False, "registered": [], "failed": []}
    assert [event["type"] for event in result["events"]] == ["gpustack:webmcp-unavailable"]


def test_adapter_documents_late_bound_bridge_and_human_only_approval() -> None:
    source = ADAPTER.read_text(encoding="utf-8")
    assert "window.GPUStackMission.invoke(toolName, validatedArgs, { signal })" in source
    assert "approval remains an explicit page-only human act" in source
    assert "Only the human can approve, edit, or reject it" in source
    assert "Free-form agent claims are rejected" in source


def test_observatory_load_order_and_cache_keys_include_the_bridge_release() -> None:
    html = OBSERVATORY_HTML.read_text(encoding="utf-8")
    scripts = [
        'observatory.js?v=20260903.3',
        'webmcp-tools.js?v=20260903.3',
        'webmcp-mission.js?v=20260903.3',
    ]

    assert all(script in html for script in scripts)
    assert [html.index(script) for script in scripts] == sorted(html.index(script) for script in scripts)
