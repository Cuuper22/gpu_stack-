(() => {
  "use strict";

  const SEMANTIC_URL = "data/e001-semantic-consistency-v1.json";
  const SCREENING_URL = "data/e001-screening-v1.json";
  const PROJECTION_URL = "data/webmcp-run-projection-v1.json.gz";
  const STORAGE_KEY = "gpustack.webmcp.mission.v1";
  const MAX_RECEIPTS = 40;
  const CANONICAL_CONCLUSIONS = Object.freeze({
    abstain_without_policy_claim: "The observable adaptive controller does not earn a transferable winner claim: it abstained under out-of-distribution stress, and every frozen aggregate gate failed.",
  });
  const RECEIPT_ORIGIN_LABELS = Object.freeze({
    webmcp: "WEBMCP",
    local_tour: "LOCAL TOUR",
    human: "HUMAN",
  });
  const REGISTERED_METRICS = Object.freeze([
    "final_held_out_nll",
    "modeled_completion_seconds",
    "inter_site_payload_bytes",
    "controller_abstentions",
    "support_envelope_flag_count",
    "replayed_tokens",
    "divergence_count",
  ]);

  const EMPTY_PENDING_HTML = `
    <div class="mission-empty">
      <span class="mission-empty-mark" aria-hidden="true"></span>
      <div>
        <strong>No conclusion is staged</strong>
        <p>Agent evidence bundles land here before they can become a recorded decision.</p>
      </div>
    </div>`;

  class MissionError extends Error {
    constructor(code, message, extra = {}) {
      super(message);
      this.name = "MissionError";
      this.code = code;
      this.extra = extra;
    }
  }

  const dom = {};
  let semanticPromise = null;
  let screeningPromise = null;
  let projectionPromise = null;
  let tourRunning = false;
  let editingProposal = false;
  let missionState = loadMissionState();

  function initialMissionState() {
    return {
      stateVersion: 1,
      nextReceipt: 1,
      nextProposal: 1,
      pending: null,
      approved: [],
      receipts: [],
    };
  }

  function isRecord(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }

  function loadMissionState() {
    const fallback = initialMissionState();
    try {
      const parsed = JSON.parse(window.sessionStorage.getItem(STORAGE_KEY) || "null");
      if (!isRecord(parsed)) return fallback;
      return {
        stateVersion: Number.isInteger(parsed.stateVersion) && parsed.stateVersion > 0 ? parsed.stateVersion : 1,
        nextReceipt: Number.isInteger(parsed.nextReceipt) && parsed.nextReceipt > 0 ? parsed.nextReceipt : 1,
        nextProposal: Number.isInteger(parsed.nextProposal) && parsed.nextProposal > 0 ? parsed.nextProposal : 1,
        pending: isRecord(parsed.pending) ? parsed.pending : null,
        approved: Array.isArray(parsed.approved) ? parsed.approved.slice(-8) : [],
        receipts: Array.isArray(parsed.receipts) ? parsed.receipts.slice(-MAX_RECEIPTS) : [],
      };
    } catch (_error) {
      return fallback;
    }
  }

  function persist() {
    try {
      window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(missionState));
    } catch (_error) {
      // The mission stays fully functional when storage is disabled.
    }
  }

  function abortIfNeeded(signal) {
    if (signal && signal.aborted) throw signal.reason || new DOMException("Aborted", "AbortError");
  }

  async function fetchArtifact(url, signal) {
    abortIfNeeded(signal);
    const response = await fetch(url, { cache: "no-store", headers: { Accept: "application/json" }, signal });
    if (!response.ok) throw new MissionError("ARTIFACT_UNAVAILABLE", `${url} returned HTTP ${response.status}.`);
    return response.json();
  }

  async function fetchGzipArtifact(url, signal) {
    abortIfNeeded(signal);
    const response = await fetch(url, { cache: "no-store", headers: { Accept: "application/gzip" }, signal });
    if (!response.ok) throw new MissionError("ARTIFACT_UNAVAILABLE", `${url} returned HTTP ${response.status}.`);
    if (typeof DecompressionStream !== "function") {
      throw new MissionError("DECOMPRESSION_UNAVAILABLE", "This browser cannot open the bounded gzip projection.");
    }
    const compressed = await response.arrayBuffer();
    const bytes = new Uint8Array(compressed);
    if (bytes[0] !== 0x1f || bytes[1] !== 0x8b) {
      return JSON.parse(new TextDecoder().decode(bytes));
    }
    const stream = new Blob([compressed]).stream().pipeThrough(new DecompressionStream("gzip"));
    return new Response(stream).json();
  }

  function semanticArtifact(signal) {
    semanticPromise ||= fetchArtifact(SEMANTIC_URL, signal).then((value) => {
      if (value?.schema !== "gpu-stack.causal-observatory.e001-semantic-consistency.v1") {
        throw new MissionError("ARTIFACT_INVALID", "The E001-SC1 compact artifact has an unsupported schema.");
      }
      return value;
    }).catch((error) => {
      semanticPromise = null;
      throw error;
    });
    return semanticPromise;
  }

  function screeningArtifact(signal) {
    screeningPromise ||= fetchArtifact(SCREENING_URL, signal).then((value) => {
      if (value?.schema !== "gpu-stack.causal-observatory.e001.v1") {
        throw new MissionError("ARTIFACT_INVALID", "The E001 screening artifact has an unsupported schema.");
      }
      return value;
    }).catch((error) => {
      screeningPromise = null;
      throw error;
    });
    return screeningPromise;
  }

  function runProjection(signal) {
    projectionPromise ||= fetchGzipArtifact(PROJECTION_URL, signal).then((value) => {
      if (value?.schema !== "gpustack.webmcp-run-projection.v1" || !Array.isArray(value.epoch_columns)) {
        throw new MissionError("PROJECTION_INVALID", "The bounded epoch projection has an unsupported schema.");
      }
      return value;
    }).catch((error) => {
      projectionPromise = null;
      throw error;
    });
    return projectionPromise;
  }

  async function observatory() {
    const bridge = window.GPUStackObservatory;
    if (!bridge || typeof bridge.whenReady !== "function") {
      throw new MissionError("OBSERVATORY_UNAVAILABLE", "The visible observatory bridge is not ready.");
    }
    await bridge.whenReady();
    return bridge;
  }

  function setStatus(message, state = "ready") {
    if (!dom.status) return;
    dom.status.textContent = message;
    document.body.dataset.missionStatus = state;
  }

  function evidenceIdsFromReceipt(receipt) {
    return Array.isArray(receipt.evidenceIds) ? receipt.evidenceIds.slice(0, 4) : [];
  }

  function addReceipt(tool, status, summary, options = {}) {
    const receipt = {
      receiptId: `wmcp-${String(missionState.nextReceipt).padStart(4, "0")}`,
      tool,
      status,
      summary: String(summary || "Action completed.").slice(0, 260),
      evidenceIds: Array.isArray(options.evidenceIds) ? options.evidenceIds.slice(0, 8) : [],
      delta: options.delta ? String(options.delta).slice(0, 180) : "No model mutation",
      origin: options.origin || "webmcp",
      timestamp: new Date().toISOString(),
    };
    missionState.nextReceipt += 1;
    missionState.receipts.push(receipt);
    missionState.receipts = missionState.receipts.slice(-MAX_RECEIPTS);
    persist();
    renderMission();
    return receipt;
  }

  function resultWithReceipt(result, receipt) {
    return {
      ...result,
      state_version: missionState.stateVersion,
      receipt_id: receipt.receiptId,
      human_approval_required: Boolean(missionState.pending),
    };
  }

  function familyList(semantic) {
    return Array.isArray(semantic?.researcher?.family_results) ? semantic.researcher.family_results : [];
  }

  function runLedger(semantic) {
    return Array.isArray(semantic?.full_trace?.run_ledger) ? semantic.full_trace.run_ledger : [];
  }

  function totalAbstentions(semantic) {
    return runLedger(semantic)
      .filter((run) => run.split === "evaluation" && run.policy_id === "observable_adaptive")
      .reduce((total, run) => total + Number(run.abstention_count || 0), 0);
  }

  function adaptiveRunForFamily(semantic, familyId) {
    return runLedger(semantic).find(
      (run) => run.family_or_stratum_id === familyId && run.policy_id === "observable_adaptive" && run.split === "evaluation",
    );
  }

  function scrollToId(id) {
    const target = document.getElementById(id);
    if (target) target.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  function clearHighlights() {
    document.querySelectorAll(".is-mission-evidence").forEach((node) => node.classList.remove("is-mission-evidence"));
  }

  function highlight(selector) {
    clearHighlights();
    const target = document.querySelector(selector);
    if (target) {
      target.classList.add("is-mission-evidence");
      target.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }

  function compactFamily(family, semantic) {
    const adaptiveRun = adaptiveRunForFamily(semantic, family.family_id);
    return {
      family_id: family.family_id,
      ranking_state: family.ranking_state,
      learning_delta: roundNumber(family.learning_delta),
      completion_ratio: roundNumber(family.completion_ratio),
      wan_ratio: roundNumber(family.wan_ratio),
      abstentions: adaptiveRun ? adaptiveRun.abstention_count : 0,
    };
  }

  function roundNumber(value, digits = 6) {
    return Number.isFinite(value) ? Number(value.toFixed(digits)) : null;
  }

  async function getObservatoryState(_args, context) {
    const [semantic, screening, bridge] = await Promise.all([
      semanticArtifact(context.signal),
      screeningArtifact(context.signal),
      observatory(),
    ]);
    abortIfNeeded(context.signal);
    const effects = semantic.researcher.paired_effects || [];
    const families = familyList(semantic);
    const view = bridge.getState();
    const receipt = addReceipt("get_observatory_state", "complete", "Read the immutable audit state and registered evidence IDs.", {
      evidenceIds: [semantic.artifact_sha256],
      origin: context.origin,
    });
    return resultWithReceipt({
      ok: true,
      active_view: {
        experiment: view.experiment,
        depth: view.depth,
        selected_family: view.semanticFamily || null,
        selected_run: view.semanticRun || null,
      },
      artifact: {
        experiment_id: semantic.experiment_id,
        sha256: semantic.artifact_sha256,
        families: families.length,
        runs: runLedger(semantic).length,
        epochs: semantic.full_trace.raw_trace_artifact.epoch_count || 12981,
      },
      evidence_boundary: {
        measured: "learning + exact accounting",
        modeled: "virtual infrastructure",
        unresolved: "frontier/facility transfer",
      },
      frozen_result: {
        conclusion: semantic.status.conclusion,
        all_falsifiers_pass: semantic.status.all_falsifiers_pass,
        failed_gate_count: effects.filter((effect) => effect.passed === false).length,
        abstentions: totalAbstentions(semantic),
      },
      registered_ids: {
        families: families.map((family) => family.family_id),
        policies: ["observable_adaptive", semantic.comparison.selected_fixed_policy_id],
        causal_nodes: screening.causal_graph.nodes.map((node) => node.node_id),
        failed_gates: effects.filter((effect) => effect.passed === false).map((effect) => effect.effect_id),
      },
      pending_proposal: missionState.pending ? missionState.pending.proposalId : null,
      suggested_next: "compare_stress_families",
    }, receipt);
  }

  async function compareStressFamilies(args, context) {
    const semantic = await semanticArtifact(context.signal);
    abortIfNeeded(context.signal);
    const families = familyList(semantic);
    const selectedIds = args.family_ids || families.map((family) => family.family_id);
    const unknown = selectedIds.find((id) => !families.some((family) => family.family_id === id));
    if (unknown) {
      throw new MissionError("UNKNOWN_FAMILY", `No held-out family named ${unknown}.`, {
        available_ids: families.map((family) => family.family_id),
      });
    }
    const rows = selectedIds.map((id) => compactFamily(families.find((family) => family.family_id === id), semantic));
    const bridge = await observatory();
    await bridge.selectView({ experiment: "E001-SC1", depth: "researcher", semanticFamily: rows[0].family_id, semanticRun: "" });
    scrollToId("semantic-consistency-v1");
    const receipt = addReceipt("compare_stress_families", "complete", `Compared ${rows.length} held-out stress families; none establishes an adaptive transferable win.`, {
      evidenceIds: selectedIds,
      delta: `Visible family → ${rows[0].family_id}`,
      origin: context.origin,
    });
    return resultWithReceipt({
      ok: true,
      comparator: semantic.comparison.selected_fixed_policy_id,
      candidate: "observable_adaptive",
      families: rows,
      shared_fields: {
        replayed_work: "0 adaptive / 0 fixed tokens in every held-out family",
        energy: "not measured for both paired runs",
      },
      counts: rows.reduce((result, row) => {
        result[row.ranking_state] = (result[row.ranking_state] || 0) + 1;
        return result;
      }, {}),
      aggregate_conclusion: semantic.status.conclusion,
    }, receipt);
  }

  async function inspectStressFamily(args, context) {
    const semantic = await semanticArtifact(context.signal);
    const family = familyList(semantic).find((entry) => entry.family_id === args.family_id);
    if (!family) {
      throw new MissionError("UNKNOWN_FAMILY", `No held-out family named ${args.family_id}.`, {
        available_ids: familyList(semantic).map((entry) => entry.family_id),
      });
    }
    const linkedRuns = runLedger(semantic)
      .filter((run) => run.family_or_stratum_id === family.family_id && run.split === "evaluation")
      .filter((run) => ["observable_adaptive", semantic.comparison.selected_fixed_policy_id].includes(run.policy_id))
      .map((run) => run.run_id);
    const bridge = await observatory();
    await bridge.selectView({ experiment: "E001-SC1", depth: "researcher", semanticFamily: family.family_id, semanticRun: "" });
    highlight(`[data-family-id="${CSS.escape(family.family_id)}"]`);
    const result = compactFamily(family, semantic);
    result.abstention_reason = family.abstention_reason || null;
    result.replayed_work = family.replayed_work_display;
    result.energy = family.energy_display;
    if (args.include_regions) {
      result.regions = (family.regions || []).slice(0, 8).map((region) => ({
        region_id: region.region_id,
        state: region.state,
        bandwidth_x: roundNumber(region.coordinates?.bandwidth_realization_multiplier),
        compute_x: roundNumber(region.coordinates?.compute_rate_realization_multiplier),
        rtt_s: roundNumber(region.coordinates?.wan_round_trip_seconds),
      }));
    }
    const receipt = addReceipt("inspect_stress_family", "complete", `Opened ${family.family_id}: ${family.ranking_state}, ${result.abstentions} adaptive abstentions.`, {
      evidenceIds: [family.family_id, ...linkedRuns.slice(0, 2)],
      delta: `Visible family → ${family.family_id}`,
      origin: context.origin,
    });
    return resultWithReceipt({ ok: true, family: result, linked_run_ids: linkedRuns }, receipt);
  }

  function projectedEpochRows(projection, runId, offset, requestedLimit) {
    const run = projection.runs.find((entry) => entry.run_id === runId);
    if (!run) return null;
    const columnIndexes = [0, 1, 3, 5, 6, 7, 9, 14, 23, 28];
    const returnedLimit = Math.min(requestedLimit, 6);
    return {
      columns: columnIndexes.map((index) => projection.epoch_columns[index]),
      rows: run.epochs.slice(offset, offset + returnedLimit).map((row) => columnIndexes.map((index) => row[index])),
      returned: Math.min(returnedLimit, Math.max(0, run.epoch_count - offset)),
      next_offset: offset + returnedLimit < run.epoch_count ? offset + returnedLimit : null,
      total_epochs: run.epoch_count,
      context_limit_applied: requestedLimit > returnedLimit,
    };
  }

  async function inspectRun(args, context) {
    const [semantic, projection] = await Promise.all([
      semanticArtifact(context.signal),
      runProjection(context.signal),
    ]);
    abortIfNeeded(context.signal);
    const run = runLedger(semantic).find((entry) => entry.run_id === args.run_id);
    if (!run) {
      throw new MissionError("UNKNOWN_RUN", `No compact run named ${args.run_id}.`, {
        hint: "Call get_observatory_state or inspect_stress_family for exact run IDs.",
      });
    }
    if (args.epoch_offset >= run.epoch_count) {
      throw new MissionError("EPOCH_OFFSET_OUT_OF_RANGE", `epoch_offset must be below ${run.epoch_count}.`);
    }
    if (projection.source_artifact_sha256 !== semantic.full_trace.raw_trace_artifact.artifact_sha256) {
      throw new MissionError("HASH_MISMATCH", "The bounded projection is not bound to this compact artifact's raw trace.");
    }
    const page = projectedEpochRows(projection, run.run_id, args.epoch_offset, args.epoch_limit);
    const bridge = await observatory();
    await bridge.selectView({
      experiment: "E001-SC1",
      depth: "researcher",
      semanticFamily: run.family_or_stratum_id,
      semanticRun: run.run_id,
    });
    scrollToId("semantic-consistency-timeline-title");
    const receipt = addReceipt("inspect_run", "complete", `Opened ${run.run_id} and epoch page ${args.epoch_offset}–${args.epoch_offset + page.returned - 1}.`, {
      evidenceIds: [run.run_id, projection.source_artifact_sha256],
      delta: `Visible run → ${run.run_id}`,
      origin: context.origin,
    });
    return resultWithReceipt({
      ok: true,
      run: {
        run_id: run.run_id,
        family_id: run.family_or_stratum_id,
        policy_id: run.policy_id,
        split: run.split,
        seed: run.seed,
        epoch_count: run.epoch_count,
        controller_abstentions: run.policy_id === "observable_adaptive" ? run.abstention_count : null,
        support_envelope_flag_count: run.out_of_distribution_epoch_count,
        final_held_out_nll: run.final_held_out_nll,
        completion_seconds: run.modeled_infrastructure?.completion_seconds,
        inter_site_payload_bytes: run.modeled_infrastructure?.inter_site_payload_bytes,
      },
      epoch_page: page,
      source_raw_sha256: projection.source_artifact_sha256,
    }, receipt);
  }

  function shortestCausalPath(graph, fromNode, toNode) {
    const queue = [[fromNode, [], [fromNode]]];
    const visited = new Set([fromNode]);
    while (queue.length) {
      const [current, pathEdges, pathNodes] = queue.shift();
      for (const edge of graph.edges.filter((candidate) => candidate.source === current)) {
        const nextEdges = [...pathEdges, edge];
        const nextNodes = [...pathNodes, edge.target];
        if (edge.target === toNode) return { edges: nextEdges, nodeIds: nextNodes };
        if (!visited.has(edge.target)) {
          visited.add(edge.target);
          queue.push([edge.target, nextEdges, nextNodes]);
        }
      }
    }
    return null;
  }

  async function traceCausalPath(args, context) {
    const screening = await screeningArtifact(context.signal);
    const graph = screening.causal_graph;
    const nodes = new Map(graph.nodes.map((node) => [node.node_id, node]));
    if (!nodes.has(args.from_node) || !nodes.has(args.to_node)) {
      const unknown = !nodes.has(args.from_node) ? args.from_node : args.to_node;
      throw new MissionError("UNKNOWN_CAUSAL_NODE", `No conceptual evidence node named ${unknown}.`, {
        available_ids: [...nodes.keys()],
      });
    }
    const path = shortestCausalPath(graph, args.from_node, args.to_node);
    if (!path) throw new MissionError("NO_CAUSAL_PATH", `No directed path connects ${args.from_node} to ${args.to_node}.`);
    if (path.nodeIds.length > args.max_nodes) {
      throw new MissionError("PATH_LIMIT_EXCEEDED", `The shortest path needs ${path.nodeIds.length} nodes; max_nodes is ${args.max_nodes}.`);
    }
    const bridge = await observatory();
    await bridge.focusCausalPath(path.nodeIds, path.edges);
    scrollToId("causal-field-title");
    const nodeRows = path.nodeIds.map((id) => {
      const node = nodes.get(id);
      return { node_id: id, label: node.label, evidence_class: node.evidence_class };
    });
    const receipt = addReceipt("trace_causal_path", "complete", `Highlighted the ${path.nodeIds.length}-node path from ${args.from_node} to ${args.to_node}.`, {
      evidenceIds: path.nodeIds,
      delta: `${path.nodeIds.length} causal nodes highlighted`,
      origin: context.origin,
    });
    return resultWithReceipt({
      ok: true,
      nodes: nodeRows,
      edges: path.edges,
      boundary: "A directed evidence path is not proof that every downstream quantity is measured.",
    }, receipt);
  }

  async function resolveEvidence(evidenceId, depth, navigate, signal) {
    const [semantic, screening] = await Promise.all([semanticArtifact(signal), screeningArtifact(signal)]);
    const bridge = await observatory();
    const artifactAliases = new Set([semantic.artifact_sha256, `sha256:${semantic.artifact_sha256}`, `artifact:${semantic.artifact_sha256}`]);
    const rawHash = semantic.full_trace.raw_trace_artifact.artifact_sha256;
    const rawAliases = new Set([rawHash, `sha256:${rawHash}`, `artifact:${rawHash}`]);
    if (artifactAliases.has(evidenceId)) {
      if (navigate) {
        await bridge.selectView({ experiment: "E001-SC1", depth });
        scrollToId("semantic-consistency-v1");
      }
      return {
        evidence_id: evidenceId,
        kind: "compact_artifact",
        sha256: semantic.artifact_sha256,
        schema: semantic.schema,
        conclusion: semantic.status.conclusion,
        boundary: semantic.evidence_boundary?.plain_boundary,
      };
    }
    if (rawAliases.has(evidenceId)) {
      if (navigate) {
        await bridge.selectView({ experiment: "E001-SC1", depth: "full_trace" });
        scrollToId("semantic-consistency-raw-details");
      }
      return {
        evidence_id: evidenceId,
        kind: "raw_artifact_binding",
        sha256: rawHash,
        schema: semantic.full_trace.raw_trace_artifact.schema,
        epoch_count: semantic.full_trace.raw_trace_artifact.epoch_count || 12981,
        boundary: "Use inspect_run for bounded rows; the authoritative raw artifact is not dumped into agent context.",
      };
    }
    const effect = semantic.researcher.paired_effects.find((entry) => entry.effect_id === evidenceId);
    if (effect) {
      if (navigate) {
        await bridge.selectView({ experiment: "E001-SC1", depth: depth === "freshman" ? "researcher" : depth });
        highlight(`[data-effect-id="${CSS.escape(evidenceId)}"]`);
      }
      return {
        evidence_id: evidenceId,
        kind: "frozen_gate",
        label: effect.label,
        value: effect.display_value,
        interval: effect.interval_display,
        boundary: effect.boundary,
        passed: effect.passed,
        evidence_class: effect.evidence_class,
      };
    }
    const family = familyList(semantic).find((entry) => entry.family_id === evidenceId);
    if (family) {
      if (navigate) {
        await bridge.selectView({ experiment: "E001-SC1", depth: "researcher", semanticFamily: family.family_id, semanticRun: "" });
        highlight(`[data-family-id="${CSS.escape(evidenceId)}"]`);
      }
      return { evidence_id: evidenceId, kind: "held_out_family", ...compactFamily(family, semantic) };
    }
    const run = runLedger(semantic).find((entry) => entry.run_id === evidenceId);
    if (run) {
      if (navigate) {
        await bridge.selectView({ experiment: "E001-SC1", depth: "researcher", semanticFamily: run.family_or_stratum_id, semanticRun: run.run_id });
        scrollToId("semantic-consistency-timeline-title");
      }
      return {
        evidence_id: evidenceId,
        kind: "run",
        family_id: run.family_or_stratum_id,
        policy_id: run.policy_id,
        final_held_out_nll: run.final_held_out_nll,
        completion_seconds: run.modeled_infrastructure?.completion_seconds,
        controller_abstentions: run.policy_id === "observable_adaptive" ? run.abstention_count : null,
        support_envelope_flag_count: run.out_of_distribution_epoch_count,
        work_contract_violations: run.exact_accounting?.work_contract_violations || [],
      };
    }
    const observation = (screening.observations || []).find((entry) => entry.observation_id === evidenceId);
    if (observation) {
      if (navigate) {
        await bridge.selectView({ experiment: "E001", depth });
        scrollToId("source-observations-title");
      }
      return {
        evidence_id: evidenceId,
        kind: "source_observation",
        citation: observation.provenance?.citation,
        uri: observation.provenance?.uri,
        license: observation.provenance?.license,
        measured_values: Object.fromEntries(Object.entries(observation.measured_values || {}).map(([metric, record]) => [metric, {
          value: record.value,
          unit: record.unit,
          lower_bound: record.uncertainty?.lower_bound,
          upper_bound: record.uncertainty?.upper_bound,
        }])),
        scope: observation.provenance?.notes?.[0],
      };
    }
    const causalNode = screening.causal_graph.nodes.find((entry) => entry.node_id === evidenceId);
    if (causalNode) {
      if (navigate) await bridge.focusCausalPath([causalNode.node_id], []);
      return {
        evidence_id: evidenceId,
        kind: "causal_node",
        label: causalNode.label,
        evidence_class: causalNode.evidence_class,
        explanation: causalNode[depth],
      };
    }
    const ledgers = [...(semantic.full_trace.assumptions || []), ...(semantic.full_trace.missing_evidence || [])];
    const ledgerEntry = ledgers.find((entry) => [entry.assumption_id, entry.evidence_id, entry.id].includes(evidenceId));
    if (ledgerEntry) {
      if (navigate) {
        await bridge.selectView({ experiment: "E001-SC1", depth: "full_trace" });
        scrollToId("semantic-consistency-assumptions");
      }
      return { evidence_id: evidenceId, kind: "evidence_boundary", entry: ledgerEntry };
    }
    throw new MissionError("UNKNOWN_EVIDENCE", `No registered evidence named ${evidenceId}.`, {
      hint: "Call get_observatory_state for registered family, run, causal-node, and effect IDs.",
    });
  }

  async function openEvidence(args, context) {
    const evidence = await resolveEvidence(args.evidence_id, args.semantic_depth, true, context.signal);
    const receipt = addReceipt("open_evidence", "complete", `Opened ${evidence.kind}: ${args.evidence_id}.`, {
      evidenceIds: [args.evidence_id],
      delta: `Evidence focus → ${args.evidence_id}`,
      origin: context.origin,
    });
    return resultWithReceipt({ ok: true, evidence }, receipt);
  }

  function median(values) {
    const ordered = values.filter(Number.isFinite).sort((a, b) => a - b);
    if (!ordered.length) return null;
    const middle = Math.floor(ordered.length / 2);
    return ordered.length % 2 ? ordered[middle] : (ordered[middle - 1] + ordered[middle]) / 2;
  }

  function metricValue(run, metricId) {
    const values = {
      final_held_out_nll: run.final_held_out_nll,
      modeled_completion_seconds: run.modeled_infrastructure?.completion_seconds,
      inter_site_payload_bytes: run.modeled_infrastructure?.inter_site_payload_bytes,
      controller_abstentions: run.policy_id === "observable_adaptive" ? run.abstention_count : null,
      support_envelope_flag_count: run.out_of_distribution_epoch_count,
      replayed_tokens: run.exact_accounting?.replayed_tokens,
      divergence_count: run.diverged ? 1 : 0,
    };
    return values[metricId];
  }

  async function comparePolicies(args, context) {
    const semantic = await semanticArtifact(context.signal);
    const ledger = runLedger(semantic);
    const availablePolicies = [...new Set(ledger.map((run) => run.policy_id))];
    const policyIds = args.policy_ids || ["observable_adaptive", semantic.comparison.selected_fixed_policy_id];
    const metricIds = args.metric_ids || REGISTERED_METRICS.slice(0, 6);
    const unknownPolicy = policyIds.find((id) => !availablePolicies.includes(id));
    const unknownMetric = metricIds.find((id) => !REGISTERED_METRICS.includes(id));
    if (unknownPolicy) throw new MissionError("UNKNOWN_POLICY", `No registered policy named ${unknownPolicy}.`, { available_ids: availablePolicies });
    if (unknownMetric) throw new MissionError("UNKNOWN_METRIC", `No registered comparison metric named ${unknownMetric}.`, { available_ids: REGISTERED_METRICS });
    const rows = policyIds.map((policyId) => {
      const runs = ledger.filter((run) => run.split === "evaluation" && run.policy_id === policyId);
      const metrics = {};
      metricIds.forEach((metricId) => {
        const values = runs
          .map((run) => metricValue(run, metricId))
          .filter((value) => value !== null && value !== undefined)
          .map(Number)
          .filter(Number.isFinite);
        if (!values.length) {
          metrics[metricId] = null;
        } else {
          metrics[metricId] = ["controller_abstentions", "support_envelope_flag_count", "divergence_count", "replayed_tokens"].includes(metricId)
            ? values.reduce((sum, value) => sum + value, 0)
            : median(values);
        }
      });
      return { policy_id: policyId, evaluation_runs: runs.length, metrics };
    });
    const bridge = await observatory();
    await bridge.selectView({ experiment: "E001-SC1", depth: "researcher" });
    scrollToId("semantic-consistency-effects-title");
    const receipt = addReceipt("compare_policies", "complete", `Compared ${policyIds.join(" vs ")} on ${metricIds.length} registered metrics.`, {
      evidenceIds: semantic.researcher.paired_effects.map((effect) => effect.effect_id),
      delta: "Aggregate gate evidence in view",
      origin: context.origin,
    });
    return resultWithReceipt({
      ok: true,
      evaluation_split_only: true,
      comparator_frozen_before_evaluation: semantic.comparison.selection.frozen_before_evaluation,
      policies: rows,
      frozen_gates: semantic.researcher.paired_effects.map((effect) => ({
        effect_id: effect.effect_id,
        passed: effect.passed,
      })),
      conclusion: semantic.status.conclusion,
    }, receipt);
  }

  async function stageConclusion(args, context) {
    const semantic = await semanticArtifact(context.signal);
    if (args.expected_state_version !== missionState.stateVersion) {
      throw new MissionError("STALE_STATE", `Expected state version ${args.expected_state_version}, but current version is ${missionState.stateVersion}.`, {
        current_state_version: missionState.stateVersion,
      });
    }
    if (missionState.pending) {
      throw new MissionError("PENDING_REVIEW_EXISTS", `Human review is already pending for ${missionState.pending.proposalId}. Approve or reject it before staging another conclusion.`, {
        pending_proposal: missionState.pending.proposalId,
      });
    }
    if (args.conclusion_code !== semantic.status.conclusion || !CANONICAL_CONCLUSIONS[args.conclusion_code]) {
      throw new MissionError("EVIDENCE_CONFLICT", `The immutable artifact serializes ${semantic.status.conclusion}; a different conclusion cannot be staged.`, {
        frozen_conclusion: semantic.status.conclusion,
      });
    }
    const resolved = [];
    for (const evidenceId of args.evidence_ids) {
      resolved.push(await resolveEvidence(evidenceId, "researcher", false, context.signal));
    }
    abortIfNeeded(context.signal);
    const proposal = {
      proposalId: `proposal-${String(missionState.nextProposal).padStart(3, "0")}`,
      claim: CANONICAL_CONCLUSIONS[args.conclusion_code],
      conclusionCode: args.conclusion_code,
      evidenceIds: [...args.evidence_ids],
      evidenceKinds: resolved.map((entry) => entry.kind),
      confidence: "abstain",
      frozenConclusion: semantic.status.conclusion,
      createdAt: new Date().toISOString(),
    };
    missionState.nextProposal += 1;
    missionState.stateVersion += 1;
    missionState.pending = proposal;
    editingProposal = false;
    persist();
    renderMission();
    scrollToId("pending-changes-title");
    const receipt = addReceipt("stage_conclusion", "pending", `Staged ${proposal.proposalId}; human approval remains required.`, {
      evidenceIds: proposal.evidenceIds,
      delta: `Pending proposal → ${proposal.proposalId}`,
      origin: context.origin,
    });
    return resultWithReceipt({
      ok: true,
      proposal_id: proposal.proposalId,
      status: "pending_human_review",
      conclusion_code: proposal.conclusionCode,
      confidence: proposal.confidence,
      evidence_ids: proposal.evidenceIds,
      frozen_conclusion: proposal.frozenConclusion,
      next_action: "A human must approve, edit, or reject in the visible pending tray.",
    }, receipt);
  }

  const HANDLERS = Object.freeze({
    get_observatory_state: getObservatoryState,
    compare_stress_families: compareStressFamilies,
    inspect_stress_family: inspectStressFamily,
    inspect_run: inspectRun,
    trace_causal_path: traceCausalPath,
    open_evidence: openEvidence,
    compare_policies: comparePolicies,
    stage_conclusion: stageConclusion,
  });

  async function invoke(toolName, args = {}, options = {}) {
    const handler = HANDLERS[toolName];
    if (!handler) return { ok: false, code: "UNKNOWN_TOOL", message: `No mission handler named ${toolName}.` };
    const context = { signal: options.signal, origin: options.origin || "webmcp" };
    setStatus(`${toolName.replaceAll("_", " ")}…`, "working");
    try {
      abortIfNeeded(context.signal);
      const result = await handler(args, context);
      if (toolName !== "stage_conclusion") abortIfNeeded(context.signal);
      refreshRegistrationStatus();
      return result;
    } catch (error) {
      if (error?.name === "AbortError") throw error;
      const code = error instanceof MissionError ? error.code : "MISSION_ERROR";
      const message = error instanceof Error ? error.message : "Mission execution failed.";
      const receipt = addReceipt(toolName, "failed", message, { origin: context.origin });
      refreshRegistrationStatus("error");
      return {
        ok: false,
        code,
        message,
        ...(error instanceof MissionError ? error.extra : {}),
        state_version: missionState.stateVersion,
        receipt_id: receipt.receiptId,
      };
    }
  }

  function escapeText(value) {
    return String(value ?? "");
  }

  function renderPending() {
    if (!dom.pending) return;
    const proposal = missionState.pending;
    dom.pending.replaceChildren();
    if (!proposal) {
      dom.pending.innerHTML = EMPTY_PENDING_HTML;
    } else {
      const card = document.createElement("article");
      card.className = "mission-change";
      card.dataset.kind = "conclusion";
      card.dataset.changeId = proposal.proposalId;
      card.setAttribute("aria-selected", "true");
      const title = document.createElement("h3");
      title.textContent = `${proposal.proposalId} · ${proposal.confidence}`;
      const claim = editingProposal ? document.createElement("textarea") : document.createElement("p");
      if (editingProposal) {
        claim.id = "mission-claim-editor";
        claim.className = "mission-claim-editor";
        claim.value = proposal.claim;
        claim.maxLength = 600;
        claim.setAttribute("aria-label", "Edit staged conclusion");
      } else {
        claim.textContent = proposal.claim;
      }
      const evidence = document.createElement("p");
      const evidenceLabel = document.createElement("strong");
      evidenceLabel.textContent = "Evidence: ";
      evidence.append(evidenceLabel, document.createTextNode(proposal.evidenceIds.join(" · ")));
      const boundary = document.createElement("p");
      boundary.textContent = `Frozen result: ${proposal.frozenConclusion}. Approval has not occurred.`;
      card.append(title, claim, evidence, boundary);
      dom.pending.append(card);
    }
    dom.pendingCount.textContent = proposal ? "1 staged" : "0 staged";
    [dom.approve, dom.reject, dom.edit].forEach((button) => { button.disabled = !proposal; });
    dom.edit.textContent = editingProposal ? "Save" : "Edit";
  }

  function renderReceipts() {
    if (!dom.receipts) return;
    dom.receipts.replaceChildren();
    if (!missionState.receipts.length) {
      const item = document.createElement("li");
      item.className = "mission-empty mission-empty--receipt";
      item.innerHTML = `<span class="mission-empty-mark" aria-hidden="true"></span><div><strong>No WebMCP calls yet</strong><p>Semantic calls appear with evidence IDs and visible state deltas.</p></div>`;
      dom.receipts.append(item);
    } else {
      [...missionState.receipts].reverse().forEach((receipt) => {
        const item = document.createElement("li");
        item.className = "webmcp-receipt";
        item.dataset.status = receipt.status;
        const heading = document.createElement("strong");
        const originLabel = RECEIPT_ORIGIN_LABELS[receipt.origin] || String(receipt.origin || "webmcp").toUpperCase();
        heading.textContent = `${originLabel} · ${receipt.tool.replaceAll("_", " ")} · ${receipt.status}`;
        const summary = document.createElement("p");
        summary.textContent = receipt.summary;
        const metadata = document.createElement("p");
        metadata.className = "receipt-delta";
        const time = document.createElement("time");
        time.dateTime = receipt.timestamp;
        time.textContent = new Date(receipt.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
        metadata.append(document.createTextNode(`${receipt.receiptId} · ${receipt.delta} · `), time);
        item.append(heading, summary, metadata);
        const evidenceIds = evidenceIdsFromReceipt(receipt);
        if (evidenceIds.length) {
          const evidence = document.createElement("p");
          evidence.className = "receipt-evidence";
          evidence.textContent = `Evidence: ${evidenceIds.join(" · ")}`;
          item.append(evidence);
        }
        dom.receipts.append(item);
      });
    }
    dom.receiptCount.textContent = `${missionState.receipts.length} item${missionState.receipts.length === 1 ? "" : "s"}`;
    dom.undo.disabled = missionState.approved.length === 0;
  }

  function renderMission() {
    renderPending();
    renderReceipts();
  }

  async function approvePending() {
    if (!missionState.pending) return;
    const approved = { ...missionState.pending, approvedAt: new Date().toISOString() };
    missionState.approved.push(approved);
    missionState.approved = missionState.approved.slice(-8);
    missionState.pending = null;
    missionState.stateVersion += 1;
    editingProposal = false;
    persist();
    addReceipt("human_approve", "approved", `Human recorded ${approved.proposalId}.`, {
      evidenceIds: approved.evidenceIds,
      delta: `Recorded conclusion → ${approved.proposalId}`,
      origin: "human",
    });
    setStatus("Human decision recorded · undo available", "ready");
    window.GPUStackObservatory?.announce("Staged conclusion approved and recorded by the human reviewer.");
  }

  function rejectPending() {
    if (!missionState.pending) return;
    const rejected = missionState.pending;
    missionState.pending = null;
    missionState.stateVersion += 1;
    editingProposal = false;
    persist();
    addReceipt("human_reject", "rejected", `Human rejected ${rejected.proposalId}.`, {
      evidenceIds: rejected.evidenceIds,
      delta: `Rejected proposal → ${rejected.proposalId}`,
      origin: "human",
    });
    setStatus("Proposal rejected · evidence remains visible", "ready");
  }

  function editPending() {
    if (!missionState.pending) return;
    if (!editingProposal) {
      editingProposal = true;
      renderMission();
      document.getElementById("mission-claim-editor")?.focus();
      return;
    }
    const editor = document.getElementById("mission-claim-editor");
    const claim = editor ? editor.value.trim() : "";
    if (!claim) {
      setStatus("A staged conclusion cannot be empty", "error");
      return;
    }
    missionState.pending.claim = claim.slice(0, 600);
    missionState.stateVersion += 1;
    editingProposal = false;
    persist();
    addReceipt("human_edit", "pending", `Human edited ${missionState.pending.proposalId}; approval is still required.`, {
      evidenceIds: missionState.pending.evidenceIds,
      delta: `Edited proposal → ${missionState.pending.proposalId}`,
      origin: "human",
    });
  }

  function undoApproved() {
    const undone = missionState.approved.pop();
    if (!undone) return;
    missionState.stateVersion += 1;
    persist();
    addReceipt("human_undo", "complete", `Human undid recorded decision ${undone.proposalId}.`, {
      evidenceIds: undone.evidenceIds,
      delta: `Removed recorded conclusion → ${undone.proposalId}`,
      origin: "human",
    });
    setStatus("Last recorded conclusion undone", "ready");
  }

  async function resetMission() {
    missionState = initialMissionState();
    editingProposal = false;
    try { window.sessionStorage.removeItem(STORAGE_KEY); } catch (_error) { /* no-op */ }
    renderMission();
    clearHighlights();
    const bridge = await observatory();
    await bridge.selectView({ experiment: "E001-SC1", depth: "freshman", semanticFamily: "", semanticRun: "" }, { replace: true });
    refreshRegistrationStatus();
  }

  function pause(milliseconds) {
    return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
  }

  async function runTour() {
    if (tourRunning) return;
    tourRunning = true;
    dom.tour.disabled = true;
    try {
      await invoke("get_observatory_state", {}, { origin: "local_tour" });
      await pause(220);
      await invoke("compare_stress_families", {}, { origin: "local_tour" });
      await pause(220);
      await invoke("inspect_stress_family", { family_id: "E6-repeated-membership-loss", include_regions: false }, { origin: "local_tour" });
      await pause(220);
      await invoke("trace_causal_path", { from_node: "site_availability", to_node: "time_to_target", max_nodes: 7 }, { origin: "local_tour" });
      await pause(220);
      await invoke("open_evidence", { evidence_id: "adaptive_minus_best_fixed_final_nll", semantic_depth: "researcher" }, { origin: "local_tour" });
      await pause(220);
      await invoke("stage_conclusion", {
        conclusion_code: "abstain_without_policy_claim",
        evidence_ids: [
          "E6-repeated-membership-loss",
          "adaptive_minus_best_fixed_final_nll",
          "adaptive_to_best_fixed_inter_site_payload_ratio",
          "adaptive_to_best_fixed_modeled_completion_time_ratio",
        ],
        expected_state_version: missionState.stateVersion,
      }, { origin: "local_tour" });
      setStatus("Audit staged · waiting for human approval", "waiting");
    } finally {
      tourRunning = false;
      dom.tour.disabled = false;
    }
  }

  function cacheDOM() {
    dom.status = document.getElementById("mission-status");
    dom.pending = document.getElementById("pending-changes");
    dom.pendingCount = document.getElementById("pending-change-count");
    dom.receipts = document.getElementById("webmcp-receipts");
    dom.receiptCount = document.getElementById("webmcp-receipt-count");
    dom.approve = document.getElementById("mission-approve");
    dom.reject = document.getElementById("mission-reject");
    dom.edit = document.getElementById("mission-edit");
    dom.undo = document.getElementById("mission-undo");
    dom.reset = document.getElementById("mission-reset");
    dom.tour = document.getElementById("mission-tour");
  }

  function refreshRegistrationStatus(forcedState) {
    if (!forcedState && missionState.pending) {
      setStatus("Audit staged · waiting for human approval", "waiting");
      return;
    }
    const webmcp = window.GPUStackWebMCP;
    if (webmcp?.supported) {
      webmcp.ready.then((status) => {
        const failed = status.failed?.length || 0;
        setStatus(failed ? `${status.registered.length} tools ready · ${failed} failed` : `${status.registered.length} WebMCP tools ready`, failed ? "error" : (forcedState || "ready"));
      });
    } else {
      setStatus("Manual audit ready · WebMCP unavailable in this browser", forcedState || "fallback");
    }
  }

  function bindUI() {
    dom.approve.addEventListener("click", approvePending);
    dom.reject.addEventListener("click", rejectPending);
    dom.edit.addEventListener("click", editPending);
    dom.undo.addEventListener("click", undoApproved);
    dom.reset.addEventListener("click", () => { resetMission().catch(() => setStatus("Reset failed", "error")); });
    dom.tour.addEventListener("click", () => { runTour().catch((error) => setStatus(error.message || "Tour failed", "error")); });
    window.addEventListener("gpustack:webmcp-ready", () => refreshRegistrationStatus());
    window.addEventListener("gpustack:webmcp-unavailable", () => refreshRegistrationStatus());
  }

  async function init() {
    document.body.dataset.missionMode = "active";
    cacheDOM();
    bindUI();
    renderMission();
    refreshRegistrationStatus();
    try {
      await Promise.all([semanticArtifact(), screeningArtifact(), observatory()]);
      refreshRegistrationStatus();
    } catch (error) {
      setStatus(`Evidence unavailable · ${error.message}`, "error");
    }
  }

  window.GPUStackMission = Object.freeze({
    version: "1.0.0",
    invoke,
    getState() {
      return JSON.parse(JSON.stringify(missionState));
    },
  });

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
  else init();
})();
