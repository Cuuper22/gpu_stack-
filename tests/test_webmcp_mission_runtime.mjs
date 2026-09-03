import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import { fileURLToPath } from "node:url";


const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");


async function makeRuntime() {
  const registrations = new Map();
  const selections = [];
  const paths = [];
  const storage = new Map();
  const document = {
    readyState: "loading",
    body: { dataset: {} },
    addEventListener() {},
    getElementById() { return null; },
    querySelector() { return null; },
    querySelectorAll() { return []; },
    modelContext: {
      async registerTool(definition) {
        registrations.set(definition.name, definition);
      },
    },
  };
  const window = {
    document,
    sessionStorage: {
      getItem(key) { return storage.get(key) ?? null; },
      setItem(key, value) { storage.set(key, value); },
      removeItem(key) { storage.delete(key); },
    },
    dispatchEvent() {},
    setTimeout,
    GPUStackObservatory: {
      version: "test",
      async whenReady() {},
      getState() {
        return {
          experiment: "E001-SC1",
          depth: "freshman",
          semanticFamily: "E1-bursty-wan",
          semanticRun: "e001-sc1:evaluation:E1-bursty-wan:observable_adaptive",
        };
      },
      async selectView(patch) {
        selections.push(patch);
        return patch;
      },
      async focusCausalPath(nodeIds, edges) {
        paths.push({ nodeIds, edges });
      },
      announce() {},
    },
  };

  const context = vm.createContext({
    AbortController,
    CSS: { escape: (value) => String(value) },
    CustomEvent: class CustomEvent {
      constructor(type, options = {}) { this.type = type; this.detail = options.detail; }
    },
    DOMException,
    Blob,
    DecompressionStream,
    Response,
    URL,
    console,
    document,
    fetch: async (url) => {
      const filename = path.join(ROOT, "docs", String(url));
      try {
        const body = await fs.readFile(filename);
        return {
          ok: true,
          status: 200,
          async arrayBuffer() { return body.buffer.slice(body.byteOffset, body.byteOffset + body.byteLength); },
          async json() { return JSON.parse(body.toString("utf8")); },
        };
      } catch (_error) {
        return { ok: false, status: 404, async json() { throw new Error("not found"); } };
      }
    },
    setTimeout,
    window,
  });
  window.window = window;

  const toolsSource = await fs.readFile(path.join(ROOT, "docs", "webmcp-tools.js"), "utf8");
  vm.runInContext(toolsSource, context, { filename: "webmcp-tools.js" });
  await window.GPUStackWebMCP.ready;

  const missionSource = await fs.readFile(path.join(ROOT, "docs", "webmcp-mission.js"), "utf8");
  vm.runInContext(missionSource, context, { filename: "webmcp-mission.js" });

  return { window, registrations, selections, paths, context };
}


function executor(runtime) {
  return (name, args) => {
    runtime.context.__args = JSON.stringify(args);
    const realmArgs = vm.runInContext("JSON.parse(__args)", runtime.context);
    return runtime.registrations.get(name).execute(realmArgs, { signal: new AbortController().signal });
  };
}


test("all eight WebMCP registrations execute against immutable evidence", async () => {
  const runtime = await makeRuntime();
  assert.equal(runtime.registrations.size, 8);
  const execute = executor(runtime);

  const state = await execute("get_observatory_state", {});
  assert.equal(state.ok, true);
  assert.ok(state.artifact, JSON.stringify(state));
  assert.equal(state.artifact.families, 6);
  assert.equal(state.artifact.runs, 56);
  assert.equal(state.artifact.epochs, 12981);
  assert.equal(state.frozen_result.abstentions, 104);
  assert.equal(state.frozen_result.all_falsifiers_pass, false);
  assert.deepEqual(Array.from(state.registered_ids.policies), ["observable_adaptive", "periodic_local"]);
  assert.equal(state.registered_ids.families.length, 6);
  assert.equal(state.registered_ids.causal_nodes.length, 7);
  assert.equal(state.registered_ids.failed_gates.length, 4);
  assert.equal(state.evidence_boundary.unresolved, "frontier/facility transfer");
  assert.ok(JSON.stringify(state).length <= 1500, `state result exceeded budget: ${JSON.stringify(state).length}`);
  assert.equal(state.truncated, undefined);

  const families = await execute("compare_stress_families", {});
  assert.equal(families.ok, true);
  assert.equal(families.families.length, 6);
  assert.equal(families.aggregate_conclusion, "abstain_without_policy_claim");
  assert.equal(families.truncated, undefined);

  const family = await execute("inspect_stress_family", {
    family_id: "E6-repeated-membership-loss",
    include_regions: true,
  });
  assert.equal(family.ok, true);
  assert.equal(family.family.abstentions, 24);
  assert.equal(family.family.regions.length, 8);
  assert.equal(family.truncated, undefined);

  const runId = "e001-sc1:evaluation:E6-repeated-membership-loss:observable_adaptive";
  const run = await execute("inspect_run", { run_id: runId, epoch_offset: 158, epoch_limit: 6 });
  assert.equal(run.ok, true);
  assert.equal(run.run.final_held_out_nll, 1.063824194483459);
  assert.equal(run.run.controller_abstentions, 24);
  assert.equal(run.run.support_envelope_flag_count, 24);
  assert.equal(run.epoch_page.rows.length, 6);
  assert.equal(run.epoch_page.context_limit_applied, false);
  assert.equal(run.source_raw_sha256, "d6321d6fc4c0f71c4f14c2f799eff252348073b3fe5508783f9f078e7f5e9d76");
  assert.ok(JSON.stringify(run).length <= 1450, `run result left too little budget headroom: ${JSON.stringify(run).length}`);
  assert.equal(run.truncated, undefined);

  const trace = await execute("trace_causal_path", {
    from_node: "site_availability",
    to_node: "time_to_target",
    max_nodes: 7,
  });
  assert.equal(trace.ok, true);
  assert.deepEqual(
    Array.from(trace.nodes, (node) => node.node_id),
    ["site_availability", "mechanical_elapsed_time", "time_to_target"],
  );
  assert.equal(trace.truncated, undefined);

  const evidence = await execute("open_evidence", {
    evidence_id: "adaptive_minus_best_fixed_final_nll",
    semantic_depth: "researcher",
  });
  assert.equal(evidence.ok, true);
  assert.equal(evidence.evidence.passed, false);
  assert.equal(evidence.truncated, undefined);

  const artifactEvidence = await execute("open_evidence", {
    evidence_id: "369bc4e9b32d6e1fcdd8dadc98c830e5ac5179f4a7204a9f5194e22913fdefdf",
    semantic_depth: "full_trace",
  });
  assert.equal(artifactEvidence.ok, true);
  assert.equal(artifactEvidence.evidence.kind, "compact_artifact");
  assert.equal(artifactEvidence.truncated, undefined);

  const policies = await execute("compare_policies", {});
  assert.equal(policies.ok, true);
  assert.equal(policies.policies.length, 2);
  assert.equal(policies.comparator_frozen_before_evaluation, true);
  assert.equal(policies.policies[0].metrics.controller_abstentions, 104);
  assert.equal(policies.policies[1].metrics.controller_abstentions, null);
  assert.equal(policies.policies[0].metrics.support_envelope_flag_count, 104);
  assert.equal(policies.policies[1].metrics.support_envelope_flag_count, 104);
  assert.equal(policies.truncated, undefined);

  const rejectedOverclaim = await execute("stage_conclusion", {
    conclusion_code: "transferable_winner",
    evidence_ids: ["E6-repeated-membership-loss"],
    expected_state_version: state.state_version,
  });
  assert.equal(rejectedOverclaim.ok, false);
  assert.equal(rejectedOverclaim.code, "INVALID_ARGUMENT");

  const staged = await execute("stage_conclusion", {
    conclusion_code: "abstain_without_policy_claim",
    evidence_ids: [
      "adaptive_minus_best_fixed_final_nll",
      "E6-repeated-membership-loss",
      runId,
      "e001-sc1:evaluation:E6-repeated-membership-loss:periodic_local",
      "369bc4e9b32d6e1fcdd8dadc98c830e5ac5179f4a7204a9f5194e22913fdefdf",
      "d6321d6fc4c0f71c4f14c2f799eff252348073b3fe5508783f9f078e7f5e9d76",
    ],
    expected_state_version: state.state_version,
  });
  assert.equal(staged.ok, true);
  assert.equal(staged.status, "pending_human_review");
  assert.equal(staged.conclusion_code, "abstain_without_policy_claim");
  assert.equal(staged.truncated, undefined);
  assert.equal(runtime.window.GPUStackMission.getState().pending.proposalId, staged.proposal_id);
  assert.ok(runtime.selections.length >= 5);
  assert.equal(runtime.paths.length, 1);
});


test("adapter rejects invalid and stale calls without mutating approval state", async () => {
  const runtime = await makeRuntime();
  const execute = executor(runtime);

  const invalid = await execute("inspect_run", { run_id: "bad id with spaces" });
  assert.equal(invalid.ok, false);
  assert.equal(invalid.code, "INVALID_ARGUMENT");

  const unknown = await execute("inspect_stress_family", { family_id: "E99-missing" });
  assert.equal(unknown.ok, false);
  assert.equal(unknown.code, "UNKNOWN_FAMILY");

  const staged = await execute("stage_conclusion", {
    conclusion_code: "abstain_without_policy_claim",
    evidence_ids: ["adaptive_minus_best_fixed_final_nll"],
    expected_state_version: 1,
  });
  assert.equal(staged.ok, true);

  const occupied = await execute("stage_conclusion", {
    conclusion_code: "abstain_without_policy_claim",
    evidence_ids: ["adaptive_minus_best_fixed_final_nll"],
    expected_state_version: 2,
  });
  assert.equal(occupied.ok, false);
  assert.equal(occupied.code, "PENDING_REVIEW_EXISTS");

  const stale = await execute("stage_conclusion", {
    conclusion_code: "abstain_without_policy_claim",
    evidence_ids: ["adaptive_minus_best_fixed_final_nll"],
    expected_state_version: 1,
  });
  assert.equal(stale.ok, false);
  assert.equal(stale.code, "STALE_STATE");
  assert.equal(runtime.window.GPUStackMission.getState().approved.length, 0);
});
