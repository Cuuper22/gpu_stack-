(() => {
  "use strict";

  const ARTIFACT_URL = "data/e001-screening-v1.json";
  const ARTIFACT_SCHEMA = "gpu-stack.causal-observatory.e001.v1";
  const RECOVERY_ARTIFACT_URL = "data/e001-recovery-v2.json";
  const RECOVERY_ARTIFACT_SCHEMA = "gpu-stack.causal-observatory.e001-recovery.v2";
  const LEARNING_ARTIFACT_URL = "data/e001-learning-v1.json";
  const EQUAL_WORK_ARTIFACT_URL = "data/e001-equal-work-v1.json";
  const EQUAL_WORK_ARTIFACT_SCHEMA = "gpu-stack.causal-observatory.e001-equal-work.v1";
  const CHECKPOINT_POWER_ARTIFACT_URL = "data/e002-checkpoint-power-v1.json";
  const CHECKPOINT_POWER_ARTIFACT_SCHEMA = "gpu-stack.causal-observatory.e002-checkpoint-power.v1";
  const CHECKPOINT_POWER_RAW_ARTIFACT_URL = "data/e002-checkpoint-power-raw-v1.json";
  const CHECKPOINT_POWER_RAW_ARTIFACT_SCHEMA = "gpu-stack.causal-observatory.e002-checkpoint-power.raw.v1";
  const CHECKPOINT_ENERGY_ARTIFACT_URL = "data/e002-checkpoint-energy-v2.json";
  const CHECKPOINT_ENERGY_ARTIFACT_SCHEMA = "gpu-stack.causal-observatory.e002-checkpoint-energy.v2";
  const CHECKPOINT_ENERGY_RAW_ARTIFACT_URL = "data/e002-checkpoint-energy-raw-v2.json";
  const CHECKPOINT_ENERGY_RAW_ARTIFACT_SCHEMA = "gpu-stack.causal-observatory.e002-checkpoint-energy.raw.v2";
  const RACK_DEPHASING_ARTIFACT_URL = "data/e002-rack-dephasing-v3.json";
  const RACK_DEPHASING_ARTIFACT_SCHEMA = "gpu-stack.causal-observatory.e002-rack-dephasing.v3";
  const SEMANTIC_CONSISTENCY_ARTIFACT_URL = "data/e001-semantic-consistency-v1.json";
  const SEMANTIC_CONSISTENCY_ARTIFACT_SCHEMA = "gpu-stack.causal-observatory.e001-semantic-consistency.v1";
  const SEMANTIC_CONSISTENCY_RAW_ARTIFACT_URL = "data/e001-semantic-consistency-raw-v1.json";
  const SEMANTIC_CONSISTENCY_RAW_ARTIFACT_SCHEMA = "gpu-stack.causal-observatory.e001-semantic-consistency.raw.v1";
  const SVG_NS = "http://www.w3.org/2000/svg";
  const VALID_DEPTHS = new Set(["freshman", "researcher", "full_trace"]);
  const VALID_EXPERIMENTS = new Set(["E001-SC1", "E001"]);
  const VALID_POLICIES = new Set(["synchronous", "fixed_local", "adaptive_cadence"]);
  const VALID_UNCERTAINTY = new Set(["intervals", "point"]);
  const VALID_RACK_COMPARATORS = new Set(["synchronized", "random_jitter"]);
  const POLICY_ORDER = ["synchronous", "fixed_local", "adaptive_cadence"];
  const POLICY_LABELS = {
    synchronous: "Synchronous",
    fixed_local: "Fixed local",
    adaptive_cadence: "Adaptive cadence",
  };
  const RECOVERY_ROLE_LABELS = {
    failure: "Failure",
    preemption: "Preemption",
    checkpoint_restore: "Restore",
    state_transfer: "State transfer",
    replay: "Replay",
    membership_rejoin: "Rejoin",
    resynchronize: "Resynchronize",
    availability_recovery: "Availability restored",
    durable_progress_recovery: "Durable frontier recovered",
  };
  const RECOVERY_POLICY_LABELS = {
    "synchronous-wait-restore": "Synchronous wait + restore",
    "fixed-local-checkpoint-restart": "Fixed-local checkpoint restart",
    "adaptive-recovery": "Adaptive recovery",
    "future-trace-recovery-oracle": "Future-trace recovery oracle",
  };
  const RECOVERY_POLICY_ROLES = {
    "synchronous-wait-restore": "baseline",
    "fixed-local-checkpoint-restart": "baseline",
    "adaptive-recovery": "candidate",
    "future-trace-recovery-oracle": "oracle_comparator",
  };
  const RECOVERY_BYTE_CLASSES = [
    ["completed_collective_link_bytes", "completed collective", "var(--obs-cobalt)"],
    ["aborted_collective_link_bytes", "aborted collective", "var(--obs-red)"],
    ["remote_checkpoint_replication_link_bytes", "checkpoint replication", "var(--obs-event-checkpoint)"],
    ["remote_checkpoint_restore_link_bytes", "checkpoint restore", "#8c74bd"],
    ["recovery_state_redistribution_link_bytes", "recovery redistribution", "var(--obs-orange)"],
    ["planned_state_migration_link_bytes", "planned migration", "var(--obs-teal)"],
  ];
  const LEARNING_POLICY_ORDER = ["synchronous_reference", "fixed_interrupted", "adaptive_interrupted"];
  const LEARNING_POLICY_LABELS = {
    synchronous_reference: "Synchronous reference",
    fixed_interrupted: "Fixed-local interrupted",
    adaptive_interrupted: "Adaptive interrupted",
  };
  const EVIDENCE_LABELS = {
    observed: "OBSERVED",
    modeled: "MODELED",
    assumed: "ASSUMED",
    prior: "PRIOR · NOT FITTED",
    unmeasured: "UNMEASURED",
  };
  const EVENT_MEANINGS = {
    compute: "Accelerators reserve site compute resources for a modeled work interval.",
    collective: "A modeled synchronization payload reserves a WAN or fabric resource.",
    state_transfer: "Modeled training state moves between named resources.",
    checkpoint: "Modeled checkpoint bytes reserve site checkpoint I/O.",
    failure: "The scenario reserves operational resources to represent an assumed interruption.",
    recovery: "The assumed interruption interval ends. This is not a measured repair event.",
    power: "A modeled power event changes an explicit facility resource.",
    cooling: "A modeled cooling event changes an explicit facility resource.",
    grid: "A modeled grid event changes an explicit facility resource.",
  };

  const SAFE_SCENARIO = Object.freeze({
    scenario_id: "e001-three-site-h100-screening-v1",
    sites: ["west", "central", "east"].map((siteId) => ({
      site_id: siteId,
      accelerator_type: "NVIDIA H100 SXM 80GB",
      accelerator_count: 256,
      accelerator_flops_per_second: 500000000000000,
    })),
    links: [
      { link_id: "west-central", site_a: "west", site_b: "central", bandwidth_bytes_per_second: 3125000000, latency_ns: 20000000, available: true },
      { link_id: "central-east", site_a: "central", site_b: "east", bandwidth_bytes_per_second: 3125000000, latency_ns: 20000000, available: true },
    ],
    total_steps: 120,
    gradient_bytes: 140000000000,
    checkpoint_bytes: 1120000000000,
    outages: [
      { event_id: "central-curtailment-1", site_id: "central", failure_start_ns: 100000000000, recovery_ns: 130000000000, duration_ns: 30000000000, cause: "screening curtailment event" },
    ],
  });

  const CONCEPTUAL_NODES = Object.freeze([
    {
      node_id: "site_availability",
      label: "Site availability",
      evidence_class: "assumed",
      freshman: "A site can lose power and stop contributing work.",
      researcher: "The scenario injects fixed-time site outages that reserve operational resources.",
      full_trace: "Failure and recovery timestamps are scenario inputs; no fleet incidence model is fitted.",
    },
    {
      node_id: "membership",
      label: "Training membership",
      evidence_class: "unmeasured",
      freshman: "The run could decide which sites still participate.",
      researcher: "Reactive membership during an active outage is not implemented in this mechanics screen.",
      full_trace: "The current runtime has operation-boundary decisions but no resumable mid-operation health callback.",
    },
    {
      node_id: "sync_cadence",
      label: "Synchronization cadence",
      evidence_class: "modeled",
      freshman: "Sites can train locally for more steps before they talk.",
      researcher: "The adaptive-cadence policy changes local steps from the previous cycle's communication-phase fraction.",
      full_trace: "Every decision is recorded before the next compute epoch is queued.",
    },
    {
      node_id: "collective_payload",
      label: "Cross-site collective payload",
      evidence_class: "modeled",
      freshman: "Talking less often sends fewer bytes between datacenters.",
      researcher: "The metric sums one gradient payload per modeled WAN link and synchronization cycle.",
      full_trace: "This is payload-link bytes, not a complete algorithm-specific all-reduce traffic model.",
    },
    {
      node_id: "mechanical_elapsed_time",
      label: "Mechanical elapsed time",
      evidence_class: "modeled",
      freshman: "Compute, communication, checkpoints, and interruptions all consume time.",
      researcher: "Successive epochs enforce compute-before-collective causality and shared-resource contention.",
      full_trace: "Overlapping failure postpones a whole operation; preemption, lost work, and recovery replay are not modeled yet.",
    },
    {
      node_id: "learning_progress",
      label: "Learning progress per FLOP",
      evidence_class: "prior",
      freshman: "We do not yet know how much extra local training changes what the model learns.",
      researcher: "A wide sensitivity prior requires attached one-step final-loss observations.",
      full_trace: "The source does not identify progress per FLOP or multi-step transfer, so the learning falsifier is unresolved.",
    },
    {
      node_id: "time_to_target",
      label: "Time to a held-out target",
      evidence_class: "unmeasured",
      freshman: "The real question stays unanswered until training quality is measured.",
      researcher: "Prior-projected equivalent-progress time is shown only as sensitivity, never as a falsifier result.",
      full_trace: "No held-out multi-site learning observation is attached to E001's current artifact.",
    },
  ]);

  const CONCEPTUAL_EDGES = Object.freeze([
    { source: "site_availability", target: "membership", relation: "constrains" },
    { source: "site_availability", target: "mechanical_elapsed_time", relation: "delays" },
    { source: "membership", target: "sync_cadence", relation: "changes feasible policy" },
    { source: "sync_cadence", target: "collective_payload", relation: "controls frequency" },
    { source: "sync_cadence", target: "learning_progress", relation: "changes staleness" },
    { source: "collective_payload", target: "mechanical_elapsed_time", relation: "consumes WAN phase" },
    { source: "mechanical_elapsed_time", target: "time_to_target", relation: "contributes" },
    { source: "learning_progress", target: "time_to_target", relation: "required but unvalidated" },
  ]);

  const dom = {};
  let artifact = null;
  let artifactError = null;
  let recoveryArtifact = null;
  let recoveryArtifactError = null;
  let learningArtifact = null;
  let learningArtifactError = null;
  let equalWorkArtifact = null;
  let equalWorkArtifactError = null;
  let checkpointPowerArtifact = null;
  let checkpointPowerArtifactError = null;
  let checkpointPowerRawArtifact = null;
  let checkpointPowerRawArtifactError = null;
  let checkpointPowerRawLoad = null;
  let checkpointEnergyArtifact = null;
  let checkpointEnergyArtifactError = null;
  let checkpointEnergyRawArtifact = null;
  let checkpointEnergyRawArtifactError = null;
  let checkpointEnergyRawLoad = null;
  let rackDephasingArtifact = null;
  let rackDephasingArtifactError = null;
  let semanticConsistencyArtifact = null;
  let semanticConsistencyArtifactError = null;
  let semanticConsistencyRawArtifact = null;
  let semanticConsistencyRawArtifactError = null;
  let semanticConsistencyRawLoad = null;
  let state = readStateFromURL();
  let timelineScale = null;
  let transientInspector = false;
  let inspectorHidden = false;
  let siteRailInitialized = false;
  let resizeFrame = 0;
  let resolveObservatoryReady;
  const observatoryReady = new Promise((resolve) => { resolveObservatoryReady = resolve; });

  class ArtifactContractError extends Error {}

  function byId(id) {
    return document.getElementById(id);
  }

  function element(tagName, className, text) {
    const node = document.createElement(tagName);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = String(text);
    return node;
  }

  function svgElement(tagName, attributes = {}) {
    const node = document.createElementNS(SVG_NS, tagName);
    Object.entries(attributes).forEach(([name, value]) => {
      if (value !== undefined && value !== null) node.setAttribute(name, String(value));
    });
    return node;
  }

  function finiteNumber(value) {
    return typeof value === "number" && Number.isFinite(value);
  }

  function normalizedEvidence(value) {
    const normalized = String(value || "unmeasured").toLowerCase();
    return Object.prototype.hasOwnProperty.call(EVIDENCE_LABELS, normalized) ? normalized : "unmeasured";
  }

  function policyLabel(value) {
    return POLICY_LABELS[value] || String(value || "Unknown policy").replaceAll("_", " ");
  }

  function conclusionLabel(value) {
    if (value === "failed_virtual_screen") return "failed virtual screen";
    if (value === "survived_virtual_screen") return "survived virtual screen";
    if (value === "falsified") return "failed virtual screen";
    if (value === "inconclusive") return "inconclusive";
    if (value === "baseline") return "baseline comparator";
    return String(value || "not reported").replaceAll("_", " ");
  }

  // Freshman translation layer. Each entry is a plain-language companion for
  // one persisted conclusion string, shown only at freshman depth and clearly
  // marked as a companion. The artifact wording itself stays verbatim
  // everywhere it is quoted. A conclusion without an entry simply shows no
  // companion. Nothing here changes a value or a verdict; it only restates.
  const PLAIN_WORDS = {
    abstain_without_policy_claim:
      "We stress-tested the controller in conditions it had never seen. It noticed it was out of its depth, logged an honest fallback 104 times, and declined to call itself the winner. That refusal is the result, and it is the most trustworthy behavior a controller can show.",
    candidate_falsified_equal_canonical_work:
      "With the workload held exactly equal, the adaptive policy kept learning quality and finished sooner, but drew more energy than the rule frozen before the run allowed. The experiment's own rule killed the claim. That is the system working.",
    candidate_falsified_small_model_calibration:
      "On this small test model, the clever adaptive policy did not beat the boring baseline. The hypothesis lost, and the loss is recorded instead of retried until it flattered us.",
    checkpoint_cadence_attributed_sparse_continuation_survives:
      "Checkpoint timing really was the cause of the extra energy draw, and the lighter checkpointing variant passed every gate. One real causal result, valid for one GPU on one workload, and not a datacenter claim.",
    measurement_invalid:
      "The power meter turned out to sample about 25 times slower than requested, so every energy number from this run was thrown out instead of quietly kept. A broken measurement gets recorded as broken.",
    inconclusive_frontier_hypothesis:
      "The virtual mechanics ran and every event is inspectable, but nothing here proves the big multi-datacenter question either way yet.",
    protocol_failed_calibration_validity:
      "The experiment's own preflight checks failed, so it stopped before making any claim.",
    protocol_failed_warm_start_not_late_stage:
      "The experiment's own preflight checks failed, so it stopped before making any claim.",
  };

  function setPlainWords(id, conclusionKey) {
    const target = document.getElementById(id);
    if (!target) return;
    const text = PLAIN_WORDS[String(conclusionKey || "")];
    if (text) {
      target.textContent = text;
      target.classList.add("has-text");
    } else {
      target.textContent = "";
      target.classList.remove("has-text");
    }
  }

  function evidenceGlyph(evidenceClass) {
    const kind = normalizedEvidence(evidenceClass);
    const glyph = element("span", `evidence-glyph evidence-glyph--${kind}`);
    glyph.setAttribute("aria-hidden", "true");
    return glyph;
  }

  function evidenceTag(evidenceClass, overrideLabel) {
    const kind = normalizedEvidence(evidenceClass);
    const tag = element("span", "evidence-tag");
    tag.dataset.evidence = kind;
    tag.append(evidenceGlyph(kind), document.createTextNode(overrideLabel || EVIDENCE_LABELS[kind]));
    return tag;
  }

  function formatDecimal(value, digits = 3) {
    return finiteNumber(value) ? value.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits }) : "unmeasured";
  }

  function formatRatio(value) {
    return finiteNumber(value) ? value.toLocaleString("en-US", { minimumFractionDigits: 3, maximumFractionDigits: 4 }) : "unmeasured";
  }

  function formatSecondsFromNs(value, options = {}) {
    if (!finiteNumber(value)) return "unmeasured";
    const seconds = value / 1e9;
    const digits = options.fixed !== undefined ? options.fixed : seconds < 10 ? 3 : seconds < 1000 ? 1 : 0;
    return `${seconds.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits })} s`;
  }

  function formatSeconds(value, digits = 1) {
    if (!finiteNumber(value)) return "unmeasured";
    return `${value.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits })} s`;
  }

  function formatBytes(value) {
    if (!finiteNumber(value)) return "unmeasured";
    const units = ["B", "kB", "MB", "GB", "TB", "PB", "EB"];
    let amount = Math.abs(value);
    let unitIndex = 0;
    while (amount >= 1000 && unitIndex < units.length - 1) {
      amount /= 1000;
      unitIndex += 1;
    }
    const signed = value < 0 ? -amount : amount;
    const digits = amount >= 100 ? 0 : amount >= 10 ? 1 : 2;
    return `${signed.toLocaleString("en-US", { maximumFractionDigits: digits })} ${units[unitIndex]}`;
  }

  function formatEnergy(value) {
    if (!finiteNumber(value)) return "unmeasured";
    if (Math.abs(value) >= 3.6e9) return `${(value / 3.6e9).toLocaleString("en-US", { maximumFractionDigits: 2 })} MWh`;
    if (Math.abs(value) >= 3.6e6) return `${(value / 3.6e6).toLocaleString("en-US", { maximumFractionDigits: 2 })} kWh`;
    if (Math.abs(value) >= 1000) return `${(value / 1000).toLocaleString("en-US", { maximumFractionDigits: 2 })} kJ`;
    return `${value.toLocaleString("en-US", { maximumFractionDigits: 2 })} J`;
  }

  function formatPower(value) {
    if (!finiteNumber(value)) return "not reported";
    if (Math.abs(value) >= 1e6) return `${(value / 1e6).toLocaleString("en-US", { maximumFractionDigits: 2 })} MW`;
    if (Math.abs(value) >= 1000) return `${(value / 1000).toLocaleString("en-US", { maximumFractionDigits: 1 })} kW`;
    return `${value.toLocaleString("en-US", { maximumFractionDigits: 1 })} W`;
  }

  function formatRate(value) {
    if (!finiteNumber(value)) return "not reported";
    if (Math.abs(value) >= 1e12) return `${(value / 1e12).toLocaleString("en-US", { maximumFractionDigits: 1 })} TFLOP/s`;
    return `${value.toLocaleString("en-US", { maximumFractionDigits: 1 })} FLOP/s`;
  }

  function compactTime(seconds) {
    if (!finiteNumber(seconds)) return "not run";
    if (seconds >= 3600) return `${(seconds / 3600).toLocaleString("en-US", { maximumFractionDigits: 1 })} h`;
    if (seconds >= 60) return `${(seconds / 60).toLocaleString("en-US", { maximumFractionDigits: 1 })} min`;
    return `${seconds.toLocaleString("en-US", { maximumFractionDigits: seconds < 10 ? 2 : 1 })} s`;
  }

  function sanitizeState(candidate) {
    const timeCandidate = Number(candidate.time);
    return {
      experiment: VALID_EXPERIMENTS.has(candidate.experiment) ? candidate.experiment : "E001-SC1",
      policy: VALID_POLICIES.has(candidate.policy) ? candidate.policy : "synchronous",
      node: typeof candidate.node === "string" && candidate.node.trim() && candidate.node.length <= 300 ? candidate.node : "event:central-curtailment-1",
      event: typeof candidate.event === "string" && candidate.event.trim() && candidate.event.length <= 300 ? candidate.event : "central-curtailment-1",
      time: Number.isFinite(timeCandidate) && timeCandidate >= 0 ? timeCandidate : 100,
      depth: VALID_DEPTHS.has(candidate.depth) ? candidate.depth : "freshman",
      uncertainty: VALID_UNCERTAINTY.has(candidate.uncertainty) ? candidate.uncertainty : "intervals",
      rackBlock: typeof candidate.rackBlock === "string" && candidate.rackBlock.length <= 80 ? candidate.rackBlock : "",
      rackComparator: VALID_RACK_COMPARATORS.has(candidate.rackComparator) ? candidate.rackComparator : "synchronized",
      semanticFamily: typeof candidate.semanticFamily === "string" && candidate.semanticFamily.length <= 120 ? candidate.semanticFamily : "",
      semanticRun: typeof candidate.semanticRun === "string" && candidate.semanticRun.length <= 180 ? candidate.semanticRun : "",
    };
  }

  function readStateFromURL() {
    const parameters = new URLSearchParams(window.location.search);
    return sanitizeState(Object.fromEntries(parameters.entries()));
  }

  function writeStateToURL(replace = false) {
    const url = new URL(window.location.href);
    url.searchParams.set("experiment", state.experiment);
    url.searchParams.set("policy", state.policy);
    url.searchParams.set("node", state.node);
    url.searchParams.set("event", state.event);
    url.searchParams.set("time", String(Math.round(state.time * 1000000) / 1000000));
    url.searchParams.set("depth", state.depth);
    url.searchParams.set("uncertainty", state.uncertainty);
    if (state.rackBlock) url.searchParams.set("rackBlock", state.rackBlock);
    else url.searchParams.delete("rackBlock");
    url.searchParams.set("rackComparator", state.rackComparator);
    if (state.semanticFamily) url.searchParams.set("semanticFamily", state.semanticFamily);
    else url.searchParams.delete("semanticFamily");
    if (state.semanticRun) url.searchParams.set("semanticRun", state.semanticRun);
    else url.searchParams.delete("semanticRun");
    const method = replace ? "replaceState" : "pushState";
    window.history[method]({ ...state }, "", url);
  }

  function commitState(patch, options = {}) {
    state = sanitizeState({ ...state, ...patch });
    writeStateToURL(Boolean(options.replace));
    if (options.timelineOnly) {
      updateTimelineScrubber();
    } else {
      renderAll();
    }
  }

  function announce(message) {
    dom.srstatus.textContent = "";
    window.setTimeout(() => { dom.srstatus.textContent = message; }, 10);
  }

  async function copyText(text, confirmation) {
    try {
      let copied = false;
      if (navigator.clipboard && window.isSecureContext) {
        try {
          await navigator.clipboard.writeText(text);
          copied = true;
        } catch (_clipboardError) {
          copied = false;
        }
      }
      if (!copied) {
        const textarea = document.createElement("textarea");
        textarea.value = text;
        textarea.setAttribute("readonly", "");
        textarea.style.position = "fixed";
        textarea.style.opacity = "0";
        document.body.append(textarea);
        textarea.select();
        copied = document.execCommand("copy");
        textarea.remove();
      }
      if (!copied) throw new Error("browser rejected both clipboard copy paths");
      announce(confirmation);
      return true;
    } catch (_error) {
      announce("Copy failed. The selected value remains visible.");
      return false;
    }
  }

  function showShareFeedback(copied) {
    const label = dom.sharestate.querySelector("span");
    if (!label) return;
    window.clearTimeout(showShareFeedback.resetTimer);
    label.textContent = copied ? "Copied" : "Copy failed";
    dom.sharestate.dataset.copyStatus = copied ? "copied" : "failed";
    showShareFeedback.resetTimer = window.setTimeout(() => {
      label.textContent = "Share state";
      delete dom.sharestate.dataset.copyStatus;
    }, 5000);
  }

  function validateArtifact(value) {
    if (!value || typeof value !== "object" || Array.isArray(value)) throw new ArtifactContractError("artifact root is not an object");
    if (value.schema !== ARTIFACT_SCHEMA) throw new ArtifactContractError(`unsupported schema: ${String(value.schema || "missing")}`);
    if (value.experiment_id !== "E001") throw new ArtifactContractError("artifact experiment_id is not E001");
    if (!value.status || typeof value.status !== "object") throw new ArtifactContractError("artifact status is missing");
    if (!value.scenario || !Array.isArray(value.scenario.sites) || !Array.isArray(value.scenario.links)) throw new ArtifactContractError("artifact scenario is incomplete");
    if (!value.causal_graph || !Array.isArray(value.causal_graph.nodes) || !Array.isArray(value.causal_graph.edges)) throw new ArtifactContractError("artifact causal graph is incomplete");
    if (!Array.isArray(value.runs) || !value.timeline || typeof value.timeline !== "object") throw new ArtifactContractError("artifact runs or timeline are missing");
    if (!Array.isArray(value.observations) || !Array.isArray(value.missing_observation_ids)) throw new ArtifactContractError("artifact observation projection is missing");
    value.observations.forEach((observation) => {
      if (!observation || typeof observation !== "object" || typeof observation.observation_id !== "string" || !observation.measured_values || typeof observation.measured_values !== "object" || !observation.provenance || typeof observation.provenance !== "object") throw new ArtifactContractError("artifact contains an invalid observation projection");
    });
    if (value.missing_observation_ids.some((observationId) => typeof observationId !== "string" || !observationId)) throw new ArtifactContractError("artifact contains an invalid missing observation ID");
    return value;
  }

  function validateRecoveryArtifact(value) {
    if (!value || typeof value !== "object" || Array.isArray(value)) throw new ArtifactContractError("recovery artifact root is not an object");
    if (value.schema !== RECOVERY_ARTIFACT_SCHEMA) throw new ArtifactContractError(`unsupported recovery schema: ${String(value.schema || "missing")}`);
    if (value.experiment_id !== "E001-RECOVERY-V2") throw new ArtifactContractError("recovery artifact experiment_id is not E001-RECOVERY-V2");
    const requiredObjects = ["source_result", "status", "matched_trace", "matched_frontier", "comparison", "causal_graph", "result_scope"];
    requiredObjects.forEach((key) => {
      if (!value[key] || typeof value[key] !== "object" || Array.isArray(value[key])) throw new ArtifactContractError(`recovery artifact ${key} is missing`);
    });
    if (typeof value.artifact_sha256 !== "string" || !/^[0-9a-f]{64}$/.test(value.artifact_sha256)) throw new ArtifactContractError("recovery artifact sha256 is invalid");
    if (typeof value.protocol_hash !== "string" || !value.protocol_hash) throw new ArtifactContractError("recovery artifact protocol_hash is missing");
    if (!Array.isArray(value.semantic_depths) || value.semantic_depths.join("|") !== "freshman|researcher|full_trace") throw new ArtifactContractError("recovery artifact semantic_depths are invalid");
    if (!Array.isArray(value.runs) || value.runs.length !== 4) throw new ArtifactContractError("recovery artifact requires exactly four matched policy runs");
    const arrayKeys = ["recovery_episodes", "decision_batches", "work_dispositions", "link_segments", "state_snapshots", "falsifiers", "evidence_requirements"];
    value.runs.forEach((run) => {
      if (!run || typeof run !== "object" || Array.isArray(run) || typeof run.policy_id !== "string" || !run.policy_id || typeof run.policy_role !== "string") throw new ArtifactContractError("recovery artifact contains an invalid run identity");
      if (!Object.prototype.hasOwnProperty.call(RECOVERY_POLICY_ROLES, run.policy_id) || RECOVERY_POLICY_ROLES[run.policy_id] !== run.policy_role) throw new ArtifactContractError(`recovery run ${String(run.policy_id || "unknown")} has an invalid policy role`);
      if (!run.summary || typeof run.summary !== "object" || Array.isArray(run.summary) || !run.metrics || typeof run.metrics !== "object" || Array.isArray(run.metrics)) throw new ArtifactContractError(`recovery run ${String(run.policy_id || "unknown")} lacks summary or metrics`);
      if (!run.checkpoint_lineage || typeof run.checkpoint_lineage !== "object" || Array.isArray(run.checkpoint_lineage)) throw new ArtifactContractError(`recovery run ${run.policy_id} lacks checkpoint_lineage`);
      arrayKeys.forEach((key) => {
        if (!Array.isArray(run[key])) throw new ArtifactContractError(`recovery run ${run.policy_id} lacks ${key}`);
      });
    });
    if (new Set(value.runs.map((run) => run.policy_id)).size !== 4) throw new ArtifactContractError("recovery artifact policy runs are not unique");
    return value;
  }

  function validateLearningArtifact(value) {
    const record = (candidate) => candidate && typeof candidate === "object" && !Array.isArray(candidate);
    if (!record(value)) throw new ArtifactContractError("learning artifact root is not an object");
    if (typeof value.schema !== "string" || !value.schema) throw new ArtifactContractError("learning artifact schema is missing");
    if (typeof value.artifact_sha256 !== "string" || !/^(?:sha256:)?[0-9a-f]{64}$/.test(value.artifact_sha256)) throw new ArtifactContractError("learning artifact sha256 is invalid");
    ["source_learning_result", "conclusion", "policy_comparison", "paired_effect", "falsifier_results"].forEach((key) => {
      if (!record(value[key])) throw new ArtifactContractError(`learning artifact ${key} is missing`);
    });
    if (typeof value.conclusion.status !== "string" || typeof value.conclusion.plain_answer !== "string") throw new ArtifactContractError("learning artifact conclusion is incomplete");
    if (value.target === undefined || value.target === null) throw new ArtifactContractError("learning artifact target is missing");
    LEARNING_POLICY_ORDER.forEach((armId) => {
      if (!record(value.policy_comparison[armId])) throw new ArtifactContractError(`learning artifact policy_comparison.${armId} is missing`);
    });
    ["learning_curves", "evaluation_pairs", "run_details"].forEach((key) => {
      if (!Array.isArray(value[key])) throw new ArtifactContractError(`learning artifact ${key} is missing`);
    });
    if (!Array.isArray(value.paired_effect.values)) throw new ArtifactContractError("learning artifact paired_effect.values is missing");
    if (value.dataset === undefined || value.runtime === undefined || value.evidence_boundary === undefined) throw new ArtifactContractError("learning artifact evidence provenance is incomplete");
    return value;
  }

  function validateEqualWorkArtifact(value) {
    const record = (candidate) => candidate && typeof candidate === "object" && !Array.isArray(candidate);
    if (!record(value)) throw new ArtifactContractError("equal-work artifact root is not an object");
    if (value.schema !== EQUAL_WORK_ARTIFACT_SCHEMA) throw new ArtifactContractError(`unsupported equal-work schema: ${String(value.schema || "missing")}`);
    if (value.experiment_id !== "E001-LC3") throw new ArtifactContractError("equal-work artifact experiment_id is not E001-LC3");
    if (typeof value.artifact_sha256 !== "string" || !/^[0-9a-f]{64}$/.test(value.artifact_sha256)) throw new ArtifactContractError("equal-work artifact sha256 is invalid");
    ["canonical_target", "conclusion", "policy_comparison", "paired_effects", "falsifier_results", "falsifier_labels", "evidence_boundary", "mechanics_bridge", "source_result"].forEach((key) => {
      if (!record(value[key])) throw new ArtifactContractError(`equal-work artifact ${key} is missing`);
    });
    ["fixed_interrupted", "adaptive_interrupted"].forEach((policyKey) => {
      if (!record(value.policy_comparison[policyKey])) throw new ArtifactContractError(`equal-work artifact policy_comparison.${policyKey} is missing`);
    });
    ["adaptive_minus_fixed_nll", "attempted_flop_savings", "opportunity_tick_savings", "adaptive_to_fixed_device_energy_ratio"].forEach((effectKey) => {
      const effect = value.paired_effects[effectKey];
      if (!record(effect) || !Array.isArray(effect.values)) throw new ArtifactContractError(`equal-work artifact paired_effects.${effectKey} is missing`);
    });
    if (!finiteNumber(value.canonical_target.canonical_tokens) || !finiteNumber(value.noninferiority_margin_nll)) throw new ArtifactContractError("equal-work target or NLL margin is missing");
    if (!Array.isArray(value.evaluation_pairs) || value.evaluation_pairs.length !== 6) throw new ArtifactContractError("equal-work artifact requires six evaluation pairs");
    if (!Array.isArray(value.run_details) || value.run_details.length !== 16) throw new ArtifactContractError("equal-work artifact requires 16 run records");
    if (!Array.isArray(value.source_lc2_protocol_results) || value.source_lc2_protocol_results.length !== 2) throw new ArtifactContractError("equal-work artifact requires two LC2 protocol predecessors");
    return value;
  }

  function validateCheckpointPowerArtifact(value) {
    const record = (candidate) => candidate && typeof candidate === "object" && !Array.isArray(candidate);
    if (!record(value)) throw new ArtifactContractError("checkpoint-power artifact root is not an object");
    if (value.schema !== CHECKPOINT_POWER_ARTIFACT_SCHEMA) throw new ArtifactContractError(`unsupported checkpoint-power schema: ${String(value.schema || "missing")}`);
    if (value.experiment_id !== "E002-PW1") throw new ArtifactContractError("checkpoint-power artifact experiment_id is not E002-PW1");
    if (value.artifact_state !== "measurement_invalid") throw new ArtifactContractError("checkpoint-power artifact state is not measurement_invalid");
    if (typeof value.artifact_sha256 !== "string" || !/^[0-9a-f]{64}$/.test(value.artifact_sha256)) throw new ArtifactContractError("checkpoint-power artifact sha256 is invalid");
    ["freshman", "researcher", "full_trace", "next_experiment", "evidence_boundary", "facility_bridge", "source_result"].forEach((key) => {
      if (!record(value[key])) throw new ArtifactContractError(`checkpoint-power artifact ${key} is missing`);
    });
    if (!Array.isArray(value.freshman.cards) || value.freshman.cards.length !== 4) throw new ArtifactContractError("checkpoint-power freshman cards are incomplete");
    if (value.researcher.measurement_valid !== false || !Array.isArray(value.researcher.invalidators) || value.researcher.invalidators.length !== 2) throw new ArtifactContractError("checkpoint-power invalidators are incomplete");
    if (!record(value.researcher.logger) || value.researcher.logger.boundary_hit !== true) throw new ArtifactContractError("checkpoint-power logger boundary is missing");
    if (!Array.isArray(value.researcher.arm_rows) || value.researcher.arm_rows.length !== 4) throw new ArtifactContractError("checkpoint-power arm matrix is incomplete");
    if (!Array.isArray(value.researcher.calibration_equivalence) || value.researcher.calibration_equivalence.length !== 4) throw new ArtifactContractError("checkpoint-power controls are incomplete");
    if (!record(value.researcher.raw_inadmissible_signals)) throw new ArtifactContractError("checkpoint-power raw contrasts are missing");
    if (value.full_trace.run_count !== 32 || !Array.isArray(value.full_trace.run_ledger) || value.full_trace.run_ledger.length !== 32) throw new ArtifactContractError("checkpoint-power run ledger requires 32 records");
    if (!record(value.full_trace.raw_trace_artifact) || value.full_trace.raw_trace_artifact.run_count !== 32) throw new ArtifactContractError("checkpoint-power raw trace binding is incomplete");
    if (!record(value.full_trace.warm_start) || value.full_trace.warm_start.binding_passed !== true || value.full_trace.warm_start.checkpoint_sha256 !== value.full_trace.warm_start.observed_checkpoint_sha256) throw new ArtifactContractError("checkpoint-power warm-state identity did not bind exactly");
    return value;
  }

  function validateCheckpointPowerRawArtifact(value) {
    const record = (candidate) => candidate && typeof candidate === "object" && !Array.isArray(candidate);
    if (!record(value)) throw new ArtifactContractError("checkpoint-power raw artifact root is not an object");
    if (value.schema !== CHECKPOINT_POWER_RAW_ARTIFACT_SCHEMA) throw new ArtifactContractError(`unsupported checkpoint-power raw schema: ${String(value.schema || "missing")}`);
    if (value.experiment_id !== "E002-PW1") throw new ArtifactContractError("checkpoint-power raw experiment_id is not E002-PW1");
    if (typeof value.artifact_sha256 !== "string" || !/^[0-9a-f]{64}$/.test(value.artifact_sha256)) throw new ArtifactContractError("checkpoint-power raw artifact sha256 is invalid");
    if (checkpointPowerArtifact && value.artifact_sha256 !== checkpointPowerArtifact.full_trace.raw_trace_artifact.artifact_sha256) throw new ArtifactContractError("checkpoint-power raw artifact hash does not match the compact binding");
    if (!Array.isArray(value.runs) || value.runs.length !== 32) throw new ArtifactContractError("checkpoint-power raw artifact requires 32 runs");
    value.runs.forEach((run) => {
      if (!record(run) || typeof run.run_id !== "string" || !record(run.telemetry_trace) || !Array.isArray(run.telemetry_trace.points) || !Array.isArray(run.phase_intervals)) throw new ArtifactContractError("checkpoint-power raw artifact contains an invalid run");
    });
    return value;
  }

  function validateCheckpointEnergyArtifact(value) {
    const record = (candidate) => candidate && typeof candidate === "object" && !Array.isArray(candidate);
    if (!record(value)) throw new ArtifactContractError("checkpoint-energy artifact root is not an object");
    if (value.schema !== CHECKPOINT_ENERGY_ARTIFACT_SCHEMA) throw new ArtifactContractError(`unsupported checkpoint-energy schema: ${String(value.schema || "missing")}`);
    if (value.experiment_id !== "E002-PW2") throw new ArtifactContractError("checkpoint-energy artifact experiment_id is not E002-PW2");
    if (value.artifact_state !== "checkpoint_cadence_attributed_sparse_continuation_survives") throw new ArtifactContractError("checkpoint-energy artifact state is not the frozen PW2 conclusion");
    if (typeof value.artifact_sha256 !== "string" || !/^[0-9a-f]{64}$/.test(value.artifact_sha256)) throw new ArtifactContractError("checkpoint-energy artifact sha256 is invalid");
    ["freshman", "researcher", "full_trace", "next_experiment", "evidence_boundary", "facility_bridge", "source_result"].forEach((key) => {
      if (!record(value[key])) throw new ArtifactContractError(`checkpoint-energy artifact ${key} is missing`);
    });
    if (!Array.isArray(value.freshman.cards) || value.freshman.cards.length !== 4) throw new ArtifactContractError("checkpoint-energy freshman cards are incomplete");
    if (value.researcher.measurement_valid !== true || !Array.isArray(value.researcher.active_invalidators) || value.researcher.active_invalidators.length !== 0) throw new ArtifactContractError("checkpoint-energy measurement validity is inconsistent");
    ["counter_calibration", "phase_support", "primary_total_interaction", "checkpoint_related_group_interaction", "mechanism_gates", "salvage_gates", "sparse_continuation_salvage"].forEach((key) => {
      if (!record(value.researcher[key])) throw new ArtifactContractError(`checkpoint-energy researcher.${key} is missing`);
    });
    if (Object.values(value.researcher.mechanism_gates).length !== 3 || Object.values(value.researcher.mechanism_gates).some((passed) => passed !== true)) throw new ArtifactContractError("checkpoint-energy mechanism gates did not all pass");
    if (Object.values(value.researcher.salvage_gates).length !== 8 || Object.values(value.researcher.salvage_gates).some((passed) => passed !== true)) throw new ArtifactContractError("checkpoint-energy salvage gates did not all pass");
    if (value.full_trace.run_count !== 32 || !Array.isArray(value.full_trace.run_ledger) || value.full_trace.run_ledger.length !== 32) throw new ArtifactContractError("checkpoint-energy run ledger requires 32 records");
    if (!record(value.full_trace.raw_trace_artifact) || value.full_trace.raw_trace_artifact.run_count !== 32) throw new ArtifactContractError("checkpoint-energy raw trace binding is incomplete");
    if (!record(value.full_trace.warm_start) || value.full_trace.warm_start.binding_passed !== true || value.full_trace.warm_start.checkpoint_sha256 !== value.full_trace.warm_start.observed_checkpoint_sha256) throw new ArtifactContractError("checkpoint-energy warm-state identity did not bind exactly");
    if (value.full_trace.pw1_failure_binding_verified !== true || value.facility_bridge.facility_claim_allowed !== false) throw new ArtifactContractError("checkpoint-energy predecessor or facility boundary is inconsistent");
    return value;
  }

  function validateCheckpointEnergyRawArtifact(value) {
    const record = (candidate) => candidate && typeof candidate === "object" && !Array.isArray(candidate);
    if (!record(value)) throw new ArtifactContractError("checkpoint-energy raw artifact root is not an object");
    if (value.schema !== CHECKPOINT_ENERGY_RAW_ARTIFACT_SCHEMA) throw new ArtifactContractError(`unsupported checkpoint-energy raw schema: ${String(value.schema || "missing")}`);
    if (value.experiment_id !== "E002-PW2") throw new ArtifactContractError("checkpoint-energy raw experiment_id is not E002-PW2");
    if (typeof value.artifact_sha256 !== "string" || !/^[0-9a-f]{64}$/.test(value.artifact_sha256)) throw new ArtifactContractError("checkpoint-energy raw artifact sha256 is invalid");
    if (checkpointEnergyArtifact && value.artifact_sha256 !== checkpointEnergyArtifact.full_trace.raw_trace_artifact.artifact_sha256) throw new ArtifactContractError("checkpoint-energy raw artifact hash does not match the compact binding");
    if (!Array.isArray(value.runs) || value.runs.length !== 32) throw new ArtifactContractError("checkpoint-energy raw artifact requires 32 runs");
    value.runs.forEach((run) => {
      if (!record(run) || typeof run.run_id !== "string" || !record(run.telemetry_trace) || !Array.isArray(run.telemetry_trace.points) || !Array.isArray(run.phase_intervals)) throw new ArtifactContractError("checkpoint-energy raw artifact contains an invalid run");
    });
    return value;
  }

  function validateRackDephasingArtifact(value) {
    const record = (candidate) => candidate && typeof candidate === "object" && !Array.isArray(candidate);
    if (!record(value)) throw new ArtifactContractError("rack-dephasing artifact root is not an object");
    if (value.schema !== RACK_DEPHASING_ARTIFACT_SCHEMA) throw new ArtifactContractError(`unsupported rack-dephasing schema: ${String(value.schema || "missing")}`);
    if (value.experiment_id !== "E002-PW3") throw new ArtifactContractError("rack-dephasing artifact experiment_id is not E002-PW3");
    if (typeof value.artifact_sha256 !== "string" || !/^[0-9a-f]{64}$/.test(value.artifact_sha256)) throw new ArtifactContractError("rack-dephasing artifact sha256 is invalid");
    ["freshman", "researcher", "full_trace", "source_result", "evidence_boundary", "next_experiment"].forEach((key) => {
      if (!record(value[key])) throw new ArtifactContractError(`rack-dephasing artifact ${key} is missing`);
    });
    if (!Array.isArray(value.freshman.cards) || value.freshman.cards.length !== 4) throw new ArtifactContractError("rack-dephasing freshman cards are incomplete");
    if (!Array.isArray(value.researcher.active_invalidators) || !Array.isArray(value.researcher.waveform_blocks)) throw new ArtifactContractError("rack-dephasing researcher evidence is incomplete");
    if (!Array.isArray(value.full_trace.blocks) || !finiteNumber(value.full_trace.block_count) || !finiteNumber(value.full_trace.arm_count)) throw new ArtifactContractError("rack-dephasing full trace is incomplete");
    value.researcher.waveform_blocks.forEach((block) => {
      if (!record(block) || typeof block.block_id !== "string" || !Array.isArray(block.arms)) throw new ArtifactContractError("rack-dephasing waveform block is invalid");
      block.arms.forEach((arm) => {
        if (!record(arm) || typeof arm.policy_id !== "string" || !record(arm.event_summary) || !Array.isArray(arm.event_summary.display_events)) throw new ArtifactContractError("rack-dephasing waveform arm is invalid");
      });
    });
    return value;
  }

  function validateSemanticConsistencyArtifact(value) {
    const record = (candidate) => candidate && typeof candidate === "object" && !Array.isArray(candidate);
    if (!record(value)) throw new ArtifactContractError("semantic-consistency artifact root is not an object");
    if (value.schema !== SEMANTIC_CONSISTENCY_ARTIFACT_SCHEMA) throw new ArtifactContractError(`unsupported semantic-consistency schema: ${String(value.schema || "missing")}`);
    if (value.experiment_id !== "E001-SC1") throw new ArtifactContractError("semantic-consistency experiment_id is not E001-SC1");
    if (typeof value.artifact_sha256 !== "string" || !/^[0-9a-f]{64}$/.test(value.artifact_sha256)) throw new ArtifactContractError("semantic-consistency artifact sha256 is invalid");
    ["source_result", "status", "comparison", "freshman", "researcher", "full_trace", "evidence_boundary"].forEach((key) => {
      if (!record(value[key])) throw new ArtifactContractError(`semantic-consistency artifact ${key} is missing`);
    });
    if (!Array.isArray(value.semantic_depths) || value.semantic_depths.join("|") !== "freshman|researcher|full_trace") throw new ArtifactContractError("semantic-consistency semantic_depths are invalid");
    if (!Array.isArray(value.freshman.cards) || value.freshman.cards.length < 4) throw new ArtifactContractError("semantic-consistency freshman cards are incomplete");
    if (!Array.isArray(value.researcher.paired_effects) || !value.researcher.paired_effects.length) throw new ArtifactContractError("semantic-consistency paired effects are missing");
    if (!Array.isArray(value.researcher.family_results) || !value.researcher.family_results.length) throw new ArtifactContractError("semantic-consistency family results are missing");
    if (!record(value.researcher.ranking_map) || !Array.isArray(value.researcher.ranking_map.families)) throw new ArtifactContractError("semantic-consistency ranking map is missing");
    if (!Array.isArray(value.full_trace.run_ledger) || !value.full_trace.run_ledger.length) throw new ArtifactContractError("semantic-consistency run ledger is missing");
    if (!record(value.full_trace.raw_trace_artifact)) throw new ArtifactContractError("semantic-consistency raw trace binding is missing");
    ["assumptions", "missing_evidence"].forEach((key) => {
      if (!Array.isArray(value.full_trace[key])) throw new ArtifactContractError(`semantic-consistency ${key} ledger is missing`);
    });
    return value;
  }

  function validateSemanticConsistencyRawArtifact(value) {
    const record = (candidate) => candidate && typeof candidate === "object" && !Array.isArray(candidate);
    if (!record(value)) throw new ArtifactContractError("semantic-consistency raw artifact root is not an object");
    if (value.schema !== SEMANTIC_CONSISTENCY_RAW_ARTIFACT_SCHEMA) throw new ArtifactContractError(`unsupported semantic-consistency raw schema: ${String(value.schema || "missing")}`);
    if (value.experiment_id !== "E001-SC1") throw new ArtifactContractError("semantic-consistency raw experiment_id is not E001-SC1");
    if (typeof value.artifact_sha256 !== "string" || !/^[0-9a-f]{64}$/.test(value.artifact_sha256)) throw new ArtifactContractError("semantic-consistency raw artifact sha256 is invalid");
    const binding = semanticConsistencyArtifact && semanticConsistencyArtifact.full_trace.raw_trace_artifact;
    if (binding && typeof binding.artifact_sha256 === "string" && binding.artifact_sha256 && value.artifact_sha256 !== binding.artifact_sha256) throw new ArtifactContractError("semantic-consistency raw artifact hash does not match the compact binding");
    if (!Array.isArray(value.runs) || !value.runs.length) throw new ArtifactContractError("semantic-consistency raw artifact has no runs");
    value.runs.forEach((run) => {
      if (!record(run) || typeof run.run_id !== "string" || !Array.isArray(run.epoch_trace)) throw new ArtifactContractError("semantic-consistency raw artifact contains an invalid run");
    });
    return value;
  }

  async function loadArtifact() {
    try {
      const response = await fetch(ARTIFACT_URL, { cache: "no-store", headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error(`artifact request returned ${response.status}`);
      artifact = validateArtifact(await response.json());
      artifactError = null;
      document.body.dataset.dataState = "ready";
    } catch (error) {
      artifact = null;
      artifactError = error;
      document.body.dataset.dataState = error instanceof ArtifactContractError ? "invalid" : "missing";
    }
    renderAll();
  }

  async function loadRecoveryArtifact() {
    try {
      const response = await fetch(RECOVERY_ARTIFACT_URL, { cache: "no-store", headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error(`recovery artifact request returned ${response.status}`);
      recoveryArtifact = validateRecoveryArtifact(await response.json());
      recoveryArtifactError = null;
      document.body.dataset.recoveryState = "ready";
    } catch (error) {
      recoveryArtifact = null;
      recoveryArtifactError = error;
      document.body.dataset.recoveryState = error instanceof ArtifactContractError ? "invalid" : "missing";
    }
    renderRecoveryV2();
  }

  async function loadLearningArtifact() {
    try {
      const response = await fetch(LEARNING_ARTIFACT_URL, { cache: "no-store", headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error(`learning artifact request returned ${response.status}`);
      learningArtifact = validateLearningArtifact(await response.json());
      learningArtifactError = null;
      document.body.dataset.learningState = "ready";
    } catch (error) {
      learningArtifact = null;
      learningArtifactError = error;
      document.body.dataset.learningState = error instanceof ArtifactContractError ? "invalid" : "missing";
    }
    renderLearningV1();
  }

  async function loadEqualWorkArtifact() {
    try {
      const response = await fetch(EQUAL_WORK_ARTIFACT_URL, { cache: "no-store", headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error(`equal-work artifact request returned ${response.status}`);
      equalWorkArtifact = validateEqualWorkArtifact(await response.json());
      equalWorkArtifactError = null;
      document.body.dataset.equalWorkState = "ready";
    } catch (error) {
      equalWorkArtifact = null;
      equalWorkArtifactError = error;
      document.body.dataset.equalWorkState = error instanceof ArtifactContractError ? "invalid" : "missing";
    }
    renderEqualWorkV1();
  }

  async function loadCheckpointPowerArtifact() {
    try {
      const response = await fetch(CHECKPOINT_POWER_ARTIFACT_URL, { cache: "no-store", headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error(`checkpoint-power artifact request returned ${response.status}`);
      checkpointPowerArtifact = validateCheckpointPowerArtifact(await response.json());
      checkpointPowerArtifactError = null;
      document.body.dataset.checkpointPowerState = "ready";
    } catch (error) {
      checkpointPowerArtifact = null;
      checkpointPowerArtifactError = error;
      document.body.dataset.checkpointPowerState = error instanceof ArtifactContractError ? "invalid" : "missing";
    }
    renderCheckpointPowerV1();
  }

  async function loadCheckpointPowerRawArtifact() {
    if (checkpointPowerRawArtifact) return checkpointPowerRawArtifact;
    if (checkpointPowerRawLoad) return checkpointPowerRawLoad;
    dom.checkpointpowerrawstate.textContent = "Loading the separate raw point artifact…";
    checkpointPowerRawLoad = (async () => {
      try {
        const response = await fetch(CHECKPOINT_POWER_RAW_ARTIFACT_URL, { cache: "no-store", headers: { Accept: "application/json" } });
        if (!response.ok) throw new Error(`checkpoint-power raw artifact request returned ${response.status}`);
        checkpointPowerRawArtifact = validateCheckpointPowerRawArtifact(await response.json());
        checkpointPowerRawArtifactError = null;
        document.body.dataset.checkpointPowerRawState = "ready";
        renderCheckpointPowerRawTrace();
        return checkpointPowerRawArtifact;
      } catch (error) {
        checkpointPowerRawArtifact = null;
        checkpointPowerRawArtifactError = error;
        document.body.dataset.checkpointPowerRawState = error instanceof ArtifactContractError ? "invalid" : "missing";
        dom.checkpointpowerrawstate.textContent = `Raw trace unavailable: ${error.message}`;
        throw error;
      } finally {
        checkpointPowerRawLoad = null;
      }
    })();
    return checkpointPowerRawLoad;
  }

  async function loadCheckpointEnergyArtifact() {
    try {
      const response = await fetch(CHECKPOINT_ENERGY_ARTIFACT_URL, { cache: "no-store", headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error(`checkpoint-energy artifact request returned ${response.status}`);
      checkpointEnergyArtifact = validateCheckpointEnergyArtifact(await response.json());
      checkpointEnergyArtifactError = null;
      document.body.dataset.checkpointEnergyState = "ready";
    } catch (error) {
      checkpointEnergyArtifact = null;
      checkpointEnergyArtifactError = error;
      document.body.dataset.checkpointEnergyState = error instanceof ArtifactContractError ? "invalid" : "missing";
    }
    renderCheckpointEnergyV2();
  }

  async function loadCheckpointEnergyRawArtifact() {
    if (checkpointEnergyRawArtifact) return checkpointEnergyRawArtifact;
    if (checkpointEnergyRawLoad) return checkpointEnergyRawLoad;
    dom.checkpointenergyrawstate.textContent = "Loading the separate cumulative-counter point artifact…";
    checkpointEnergyRawLoad = (async () => {
      try {
        const response = await fetch(CHECKPOINT_ENERGY_RAW_ARTIFACT_URL, { cache: "no-store", headers: { Accept: "application/json" } });
        if (!response.ok) throw new Error(`checkpoint-energy raw artifact request returned ${response.status}`);
        checkpointEnergyRawArtifact = validateCheckpointEnergyRawArtifact(await response.json());
        checkpointEnergyRawArtifactError = null;
        document.body.dataset.checkpointEnergyRawState = "ready";
        renderCheckpointEnergyRawTrace();
        return checkpointEnergyRawArtifact;
      } catch (error) {
        checkpointEnergyRawArtifact = null;
        checkpointEnergyRawArtifactError = error;
        document.body.dataset.checkpointEnergyRawState = error instanceof ArtifactContractError ? "invalid" : "missing";
        dom.checkpointenergyrawstate.textContent = `Raw counter trace unavailable: ${error.message}`;
        throw error;
      } finally {
        checkpointEnergyRawLoad = null;
      }
    })();
    return checkpointEnergyRawLoad;
  }

  async function loadRackDephasingArtifact() {
    try {
      const response = await fetch(RACK_DEPHASING_ARTIFACT_URL, { cache: "no-store", headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error(`rack-dephasing artifact request returned ${response.status}`);
      rackDephasingArtifact = validateRackDephasingArtifact(await response.json());
      rackDephasingArtifactError = null;
      document.body.dataset.rackDephasingState = "ready";
    } catch (error) {
      rackDephasingArtifact = null;
      rackDephasingArtifactError = error;
      document.body.dataset.rackDephasingState = error instanceof ArtifactContractError ? "invalid" : "missing";
    }
    renderRackDephasingV3();
  }

  async function loadSemanticConsistencyArtifact() {
    try {
      const response = await fetch(SEMANTIC_CONSISTENCY_ARTIFACT_URL, { cache: "no-store", headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error(`semantic-consistency artifact request returned ${response.status}`);
      semanticConsistencyArtifact = validateSemanticConsistencyArtifact(await response.json());
      semanticConsistencyArtifactError = null;
      document.body.dataset.semanticConsistencyState = "ready";
    } catch (error) {
      semanticConsistencyArtifact = null;
      semanticConsistencyArtifactError = error;
      document.body.dataset.semanticConsistencyState = error instanceof ArtifactContractError ? "invalid" : "missing";
    }
    renderAll();
  }

  async function loadSemanticConsistencyRawArtifact() {
    if (semanticConsistencyRawArtifact) return semanticConsistencyRawArtifact;
    if (semanticConsistencyRawLoad) return semanticConsistencyRawLoad;
    dom.semanticconsistencyrawstate.textContent = "Loading the separately bound optimizer-commit trace…";
    semanticConsistencyRawLoad = (async () => {
      try {
        const binding = semanticConsistencyArtifact && semanticConsistencyArtifact.full_trace.raw_trace_artifact;
        const uri = binding && typeof binding.uri === "string" && binding.uri ? binding.uri : SEMANTIC_CONSISTENCY_RAW_ARTIFACT_URL;
        const response = await fetch(uri.startsWith("data/") ? uri : `data/${uri}`, { cache: "no-store", headers: { Accept: "application/json" } });
        if (!response.ok) throw new Error(`semantic-consistency raw artifact request returned ${response.status}`);
        semanticConsistencyRawArtifact = validateSemanticConsistencyRawArtifact(await response.json());
        semanticConsistencyRawArtifactError = null;
        document.body.dataset.semanticConsistencyRawState = "ready";
        renderSemanticConsistencyTrace();
        return semanticConsistencyRawArtifact;
      } catch (error) {
        semanticConsistencyRawArtifact = null;
        semanticConsistencyRawArtifactError = error;
        document.body.dataset.semanticConsistencyRawState = error instanceof ArtifactContractError ? "invalid" : "missing";
        dom.semanticconsistencyrawstate.textContent = `Raw epoch trace unavailable: ${error.message}`;
        throw error;
      } finally {
        semanticConsistencyRawLoad = null;
      }
    })();
    return semanticConsistencyRawLoad;
  }

  function cacheDOM() {
    [
      "experiment-select", "share-state", "plain-answer", "artifact-state", "stage-boundary",
      "site-field-source", "site-viewport", "site-rail", "site-position", "causal-svg",
      "causal-fallback", "evidence-inspector", "inspector-title", "inspector-body", "inspector-close",
      "timeline-svg", "timeline-viewport", "timeline-readout", "time-scrubber", "previous-event",
      "next-event", "timeline-fallback", "uncertainty-select", "comparison-body", "comparison-boundary",
      "source-observation-body", "prior-parameters", "decision-ledger-body", "raw-trace-summary",
      "raw-trace-json", "source-chain-item", "source-chain-label", "source-chain-evidence", "footer-evidence-state", "sr-status",
      "recovery-v2", "recovery-v2-state", "recovery-depth-copy", "recovery-timeline-svg",
      "recovery-timeline-fallback", "recovery-work-bars", "recovery-byte-bars",
      "recovery-completion-ruler", "recovery-learning-boundary", "recovery-learning-trace",
      "learning-v1", "learning-v1-state", "learning-insight-title", "learning-plain-answer",
      "learning-depth-trace", "learning-policy-grid", "learning-curves-svg", "learning-curve-values",
      "learning-paired-svg", "learning-paired-summary", "learning-gate-strip", "learning-evidence-boundary",
      "learning-evaluation-pairs", "learning-run-details", "learning-provenance-json",
      "equal-work-v1", "equal-work-v1-state", "equal-work-insight-title", "equal-work-plain-answer",
      "equal-work-depth-trace", "equal-work-freshman-grid", "equal-work-policy-grid", "equal-work-effect-grid",
      "equal-work-checkpoint-clue", "equal-work-gate-strip", "equal-work-evidence-boundary",
      "equal-work-evaluation-pairs", "equal-work-run-details", "equal-work-predecessors",
      "equal-work-bridge", "equal-work-provenance-json",
      "checkpoint-power-v1", "checkpoint-power-v1-state", "checkpoint-power-insight-title",
      "checkpoint-power-plain-answer", "checkpoint-power-decision", "checkpoint-power-depth-trace",
      "checkpoint-power-freshman-grid", "checkpoint-power-invalidators", "checkpoint-power-logger",
      "checkpoint-power-arm-grid", "checkpoint-power-control-grid", "checkpoint-power-contrast-label",
      "checkpoint-power-contrast-grid", "checkpoint-power-next-question", "checkpoint-power-next-frozen",
      "checkpoint-power-next-evidence", "checkpoint-power-evidence-boundary", "checkpoint-power-run-select",
      "checkpoint-power-run-ledger", "checkpoint-power-phase-metrics", "checkpoint-power-provenance-json",
      "checkpoint-power-raw-details", "checkpoint-power-raw-state", "checkpoint-power-raw-meta",
      "checkpoint-power-raw-points",
      "checkpoint-energy-v2", "checkpoint-energy-v2-state", "checkpoint-energy-insight-title",
      "checkpoint-energy-plain-answer", "checkpoint-energy-mechanism", "checkpoint-energy-depth-trace",
      "checkpoint-energy-freshman-grid", "checkpoint-energy-validity-grid", "checkpoint-energy-effect-grid",
      "checkpoint-energy-support-grid", "checkpoint-energy-exploratory", "checkpoint-energy-mechanism-gates",
      "checkpoint-energy-salvage-gates", "checkpoint-energy-evidence-boundary", "checkpoint-energy-next-question",
      "checkpoint-energy-run-select", "checkpoint-energy-run-ledger", "checkpoint-energy-counter-summary",
      "checkpoint-energy-phase-metrics", "checkpoint-energy-provenance-json", "checkpoint-energy-raw-details",
      "checkpoint-energy-raw-state", "checkpoint-energy-raw-meta", "checkpoint-energy-raw-points",
      "rack-dephasing-v3", "rack-dephasing-v3-state", "rack-dephasing-eyebrow",
      "rack-dephasing-insight-title", "rack-dephasing-plain-answer", "rack-dephasing-boundary-short",
      "rack-dephasing-freshman-copy", "rack-dephasing-researcher-copy", "rack-dephasing-depth-trace",
      "rack-dephasing-freshman-grid", "rack-dephasing-block-select", "rack-dephasing-comparator-select",
      "rack-dephasing-waveform-svg", "rack-dephasing-waveform-desc", "rack-dephasing-waveform-fallback",
      "rack-dephasing-effect-grid", "rack-dephasing-policy-body", "rack-dephasing-gate-summary",
      "rack-dephasing-gate-strip", "rack-dephasing-evidence-boundary", "rack-dephasing-next-question",
      "rack-dephasing-event-body", "rack-dephasing-trace-summary", "rack-dephasing-raw-manifest",
      "rack-dephasing-provenance-json",
    ].forEach((id) => { dom[id.replaceAll("-", "")] = byId(id); });
    [
      "experiment-kicker-code", "experiment-kicker-name", "experiment-question",
      "semantic-consistency-v1", "semantic-consistency-v1-state", "semantic-consistency-eyebrow",
      "semantic-consistency-insight-title", "semantic-consistency-plain-answer", "semantic-consistency-boundary-short",
      "semantic-consistency-freshman-copy", "semantic-consistency-researcher-copy", "semantic-consistency-depth-trace",
      "semantic-consistency-freshman-grid", "semantic-consistency-effects-note", "semantic-consistency-effect-grid",
      "semantic-consistency-ranking-svg", "semantic-consistency-ranking-fallback", "semantic-consistency-family-select",
      "semantic-consistency-timeline-svg", "semantic-consistency-timeline-fallback", "semantic-consistency-family-body",
      "semantic-consistency-evidence-boundary", "semantic-consistency-missing-short", "semantic-consistency-run-select",
      "semantic-consistency-epoch-body", "semantic-consistency-assumptions", "semantic-consistency-uncertainty",
      "semantic-consistency-missing-evidence", "semantic-consistency-provenance-json", "semantic-consistency-raw-details",
      "semantic-consistency-raw-state", "semantic-consistency-raw-meta",
    ].forEach((id) => { dom[id.replaceAll("-", "")] = byId(id); });
    dom.researchBand = document.querySelector(".research-band");
    dom.depthButtons = [...document.querySelectorAll(".depth-control button")];
    dom.experimentViews = [...document.querySelectorAll("[data-experiment-view]")];
  }

  function bindStaticInteractions() {
    dom.depthButtons.forEach((button) => {
      button.addEventListener("click", () => commitState({ depth: button.dataset.depth }));
    });
    dom.experimentselect.addEventListener("change", () => commitState({ experiment: dom.experimentselect.value }));
    dom.uncertaintyselect.addEventListener("change", () => commitState({ uncertainty: dom.uncertaintyselect.value }));
    dom.sharestate.addEventListener("click", async () => {
      writeStateToURL(true);
      showShareFeedback(await copyText(window.location.href, "State URL copied."));
    });
    dom.inspectorclose.addEventListener("click", () => {
      if (window.matchMedia("(max-width: 760px)").matches) {
        transientInspector = false;
        dom.evidenceinspector.classList.remove("is-transient");
      } else {
        inspectorHidden = true;
        dom.evidenceinspector.classList.add("is-hidden");
        dom.researchBand.classList.add("inspector-hidden");
      }
    });
    dom.timescrubber.addEventListener("input", () => {
      state = sanitizeState({ ...state, time: Number(dom.timescrubber.value) });
      writeStateToURL(true);
      updateTimelineScrubber();
    });
    dom.timescrubber.addEventListener("change", () => writeStateToURL(false));
    dom.previousevent.addEventListener("click", () => selectAdjacentEvent(-1));
    dom.nextevent.addEventListener("click", () => selectAdjacentEvent(1));
    dom.checkpointpowerrunselect.addEventListener("change", () => {
      renderCheckpointPowerPhaseMetrics();
      if (checkpointPowerRawArtifact) renderCheckpointPowerRawTrace();
    });
    dom.checkpointpowerrawdetails.addEventListener("toggle", () => {
      if (!dom.checkpointpowerrawdetails.open || state.depth !== "full_trace") return;
      loadCheckpointPowerRawArtifact().catch(() => {});
    });
    dom.checkpointenergyrunselect.addEventListener("change", () => {
      renderCheckpointEnergyPhaseMetrics();
      if (checkpointEnergyRawArtifact) renderCheckpointEnergyRawTrace();
    });
    dom.checkpointenergyrawdetails.addEventListener("toggle", () => {
      if (!dom.checkpointenergyrawdetails.open || state.depth !== "full_trace") return;
      loadCheckpointEnergyRawArtifact().catch(() => {});
    });
    dom.rackdephasingblockselect.addEventListener("change", () => {
      commitState({ rackBlock: dom.rackdephasingblockselect.value });
    });
    dom.rackdephasingcomparatorselect.addEventListener("change", () => {
      commitState({ rackComparator: dom.rackdephasingcomparatorselect.value });
    });
    dom.semanticconsistencyfamilyselect.addEventListener("change", () => {
      commitState({ semanticFamily: dom.semanticconsistencyfamilyselect.value, semanticRun: "" });
    });
    dom.semanticconsistencyrunselect.addEventListener("change", () => {
      commitState({ semanticRun: dom.semanticconsistencyrunselect.value });
    });
    dom.semanticconsistencyrawdetails.addEventListener("toggle", () => {
      if (!dom.semanticconsistencyrawdetails.open || state.depth !== "full_trace") return;
      loadSemanticConsistencyRawArtifact().catch(() => {});
    });
    dom.timelineviewport.addEventListener("keydown", (event) => {
      if (event.target !== dom.timelineviewport) return;
      if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
        event.preventDefault();
        selectAdjacentEvent(event.key === "ArrowLeft" ? -1 : 1);
      }
    });
    dom.siteviewport.addEventListener("scroll", updateSitePosition, { passive: true });
    window.addEventListener("popstate", () => {
      state = readStateFromURL();
      transientInspector = false;
      renderAll();
    });
    window.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && transientInspector) {
        transientInspector = false;
        dom.evidenceinspector.classList.remove("is-transient");
        announce("Evidence sheet closed.");
      }
    });
    window.addEventListener("resize", () => {
      if (resizeFrame) window.cancelAnimationFrame(resizeFrame);
      resizeFrame = window.requestAnimationFrame(() => {
        resizeFrame = 0;
        renderCausalGraph();
        renderTimeline();
        renderRackDephasingWaveform();
        renderSemanticConsistencyRanking();
        renderSemanticConsistencyTimeline();
      });
    }, { passive: true });
  }

  function init() {
    cacheDOM();
    bindStaticInteractions();
    writeStateToURL(true);
    renderAll();
    loadArtifact();
    loadRecoveryArtifact();
    loadLearningArtifact();
    loadEqualWorkArtifact();
    loadCheckpointPowerArtifact();
    loadCheckpointEnergyArtifact();
    loadRackDephasingArtifact();
    loadSemanticConsistencyArtifact();
    resolveObservatoryReady();
    document.dispatchEvent(new CustomEvent("gpustack:observatory-ready"));
  }

  document.addEventListener("DOMContentLoaded", init, { once: true });

  function renderAll() {
    document.body.dataset.depth = state.depth;
    document.body.dataset.experiment = state.experiment;
    dom.depthButtons.forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.depth === state.depth)));
    dom.experimentselect.value = state.experiment;
    dom.uncertaintyselect.value = state.uncertainty;
    renderStatus();
    renderSiteRail();
    renderCausalGraph();
    renderComparison();
    renderTimeline();
    renderInspector();
    renderSourceObservations();
    renderPriorParameters();
    renderDecisionLedger();
    renderRawTrace();
    renderRecoveryV2();
    renderLearningV1();
    renderEqualWorkV1();
    renderCheckpointPowerV1();
    renderCheckpointEnergyV2();
    renderRackDephasingV3();
    renderSemanticConsistencyV1();
    renderExperimentView();
    if (state.experiment === "E001-SC1" && state.depth === "full_trace" && dom.semanticconsistencyrawdetails?.open && semanticConsistencyArtifact && !semanticConsistencyRawArtifact && !semanticConsistencyRawLoad && !semanticConsistencyRawArtifactError) {
      loadSemanticConsistencyRawArtifact().catch(() => {});
    }
  }

  function renderExperimentView() {
    dom.experimentViews.forEach((view) => {
      view.hidden = view.dataset.experimentView !== state.experiment;
    });
  }

  function recoveryRuns() {
    return recoveryArtifact && Array.isArray(recoveryArtifact.runs) ? recoveryArtifact.runs : [];
  }

  function recoveryPolicyLabel(policyId) {
    if (Object.prototype.hasOwnProperty.call(RECOVERY_POLICY_LABELS, policyId)) return RECOVERY_POLICY_LABELS[policyId];
    return String(policyId || "unknown policy")
      .split(/[-_]/g)
      .filter(Boolean)
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ");
  }

  function formatFlops(value) {
    if (!finiteNumber(value)) return "unmeasured";
    const magnitude = Math.abs(value);
    if (magnitude >= 1e18) return `${(value / 1e18).toLocaleString("en-US", { maximumFractionDigits: 2 })} EFLOP`;
    if (magnitude >= 1e15) return `${(value / 1e15).toLocaleString("en-US", { maximumFractionDigits: 2 })} PFLOP`;
    if (magnitude >= 1e12) return `${(value / 1e12).toLocaleString("en-US", { maximumFractionDigits: 2 })} TFLOP`;
    return `${value.toLocaleString("en-US", { maximumFractionDigits: 2 })} FLOP`;
  }

  function recoveryRecordTime(record) {
    if (finiteNumber(record.start_ns)) return record.start_ns;
    if (finiteNumber(record.timestamp_ns)) return record.timestamp_ns;
    if (finiteNumber(record.at_ns)) return record.at_ns;
    if (finiteNumber(record.applied_at_ns)) return record.applied_at_ns;
    return null;
  }

  function recoveryRecordEnd(record, startNs) {
    if (finiteNumber(record.end_ns)) return Math.max(startNs, record.end_ns);
    if (finiteNumber(record.completed_at_ns)) return Math.max(startNs, record.completed_at_ns);
    return startNs;
  }

  function recoveryRecordId(record, fallback) {
    const candidates = [record.event_id, record.milestone_id, record.record_id, record.attempt_id, record.decision_id, record.transition_id];
    const found = candidates.find((value) => typeof value === "string" && value);
    return found || fallback;
  }

  function recoveryRecordsForRun(run) {
    const records = [];
    const seenObjects = new Set();
    const seenRecords = new Set();
    const visit = (value, path) => {
      if (!value || typeof value !== "object" || seenObjects.has(value)) return;
      seenObjects.add(value);
      if (Array.isArray(value)) {
        value.forEach((item, index) => visit(item, `${path}[${index}]`));
        return;
      }
      if (typeof value.recovery_role === "string" && Object.prototype.hasOwnProperty.call(RECOVERY_ROLE_LABELS, value.recovery_role)) {
        const startNs = recoveryRecordTime(value);
        if (finiteNumber(startNs)) {
          const endNs = recoveryRecordEnd(value, startNs);
          const recordId = recoveryRecordId(value, path);
          const key = `${recordId}|${value.recovery_role}|${startNs}|${endNs}`;
          if (!seenRecords.has(key)) {
            seenRecords.add(key);
            records.push({ ...value, event_id: recordId, start_ns: startNs, end_ns: endNs, policy_id: run.policy_id });
          }
        }
      }
      Object.entries(value).forEach(([key, nested]) => {
        if (key !== "metadata") visit(nested, `${path}.${key}`);
      });
    };
    (Array.isArray(run.recovery_episodes) ? run.recovery_episodes : []).forEach((episode, index) => visit(episode, `recovery_episodes[${index}]`));
    return records.sort((a, b) => a.start_ns - b.start_ns || a.end_ns - b.end_ns || String(a.event_id).localeCompare(String(b.event_id)));
  }

  function renderRecoveryTimeline() {
    const svg = dom.recoverytimelinesvg;
    svg.replaceChildren();
    const title = svgElement("title", { id: "recovery-timeline-title" });
    title.textContent = "Aligned four-policy recovery timeline";
    const description = svgElement("desc", { id: "recovery-timeline-desc" });
    svg.append(title, description);

    const runs = recoveryRuns();
    const recordsByPolicy = runs.map((run) => ({ run, records: recoveryRecordsForRun(run) }));
    const records = recordsByPolicy.flatMap((entry) => entry.records);
    if (!records.length) {
      svg.setAttribute("viewBox", "0 0 1000 180");
      svg.setAttribute("height", "180");
      description.textContent = "The recovery artifact contains no timeline records with explicit recovery roles.";
      const empty = svgElement("text", { x: 500, y: 92, "text-anchor": "middle", class: "recovery-policy-label" });
      empty.textContent = "RECOVERY TIMELINE UNAVAILABLE IN ARTIFACT";
      svg.append(empty);
      renderRecoveryTimelineFallback(recordsByPolicy);
      return;
    }

    const minNs = Math.min(...records.map((record) => record.start_ns));
    const maxNs = Math.max(...records.map((record) => record.end_ns), minNs + 1);
    const left = 240;
    const right = 975;
    const axisY = 30;
    const rowHeight = 90;
    const height = 58 + rowHeight * recordsByPolicy.length;
    const scaleX = (value) => left + (value - minNs) / (maxNs - minNs) * (right - left);
    svg.setAttribute("viewBox", `0 0 1000 ${height}`);
    svg.setAttribute("height", String(height));
    description.textContent = "Four ordered policy tracks share one artifact time scale. Intervals show restore and replay; milestone marks show failure, preemption, recovery, and rejoin.";
    svg.append(svgElement("line", { x1: left, x2: right, y1: axisY, y2: axisY, class: "recovery-axis" }));
    for (let tickIndex = 0; tickIndex <= 5; tickIndex += 1) {
      const fraction = tickIndex / 5;
      const timestamp = minNs + fraction * (maxNs - minNs);
      const x = left + fraction * (right - left);
      svg.append(svgElement("line", { x1: x, x2: x, y1: axisY, y2: height - 12, class: "recovery-gridline" }));
      const tick = svgElement("text", { x, y: axisY - 8, "text-anchor": tickIndex === 0 ? "start" : tickIndex === 5 ? "end" : "middle", class: "recovery-tick" });
      tick.textContent = formatSecondsFromNs(timestamp, { fixed: timestamp / 1e9 < 10 ? 2 : 1 });
      svg.append(tick);
    }

    recordsByPolicy.forEach(({ run, records: policyRecords }, runIndex) => {
      const top = 52 + runIndex * rowHeight;
      const baseline = top + 28;
      const policy = svgElement("text", { x: 10, y: top + 4, class: "recovery-policy-label" });
      policy.dataset.policyRole = run.policy_role || "comparator";
      policy.textContent = recoveryPolicyLabel(run.policy_id);
      const role = svgElement("text", { x: 10, y: top + 20, class: "recovery-event-id" });
      role.textContent = String(run.policy_role || "comparator").replaceAll("_", " ").toUpperCase();
      svg.append(policy, role, svgElement("line", { x1: left, x2: right, y1: baseline, y2: baseline, class: "recovery-track" }));

      policyRecords.forEach((record, recordIndex) => {
        const x = scaleX(record.start_ns);
        const intervalWidth = Math.max(0, scaleX(record.end_ns) - x);
        const milestone = intervalWidth < 2;
        const y = baseline + 10 + recordIndex % 3 * 14;
        const mark = svgElement(milestone ? "rect" : "rect", {
          x: milestone ? x - 4 : x,
          y,
          width: milestone ? 8 : Math.max(3, intervalWidth),
          height: milestone ? 8 : 9,
          transform: milestone ? `rotate(45 ${x} ${y + 4})` : undefined,
          class: "recovery-event",
          "data-role": record.recovery_role,
        });
        const markTitle = svgElement("title");
        markTitle.textContent = `${RECOVERY_ROLE_LABELS[record.recovery_role]}: ${record.event_id}, ${formatSecondsFromNs(record.start_ns)} to ${formatSecondsFromNs(record.end_ns)}`;
        mark.append(markTitle);
        svg.append(mark);
        if (!milestone && intervalWidth > 42) {
          const label = svgElement("text", { x: x + 4, y: y + 8, class: "recovery-event-label" });
          label.textContent = RECOVERY_ROLE_LABELS[record.recovery_role].toUpperCase();
          svg.append(label);
        }
        if (state.depth === "full_trace" && recordIndex < 3) {
          const id = svgElement("text", { x: Math.min(right - 100, x + 3), y: y + 20, class: "recovery-event-id" });
          id.textContent = String(record.event_id).slice(0, 28);
          svg.append(id);
        }
      });

      const failure = policyRecords.find((record) => record.recovery_role === "failure");
      const recovered = policyRecords.find((record) => record.recovery_role === "durable_progress_recovery");
      if (failure && recovered && recovered.start_ns >= failure.start_ns) {
        const startX = scaleX(failure.start_ns);
        const endX = scaleX(recovered.start_ns);
        const bracketY = top + 4;
        svg.append(svgElement("path", { d: `M${startX} ${bracketY + 7}V${bracketY}H${endX}V${bracketY + 7}`, class: "recovery-debt-bracket" }));
        const label = svgElement("text", { x: (startX + endX) / 2, y: bracketY - 3, "text-anchor": "middle", class: "recovery-debt-label" });
        label.textContent = `DURABLE RECOVERY ${formatSecondsFromNs(recovered.start_ns - failure.start_ns)}`;
        svg.append(label);
      }
    });
    renderRecoveryTimelineFallback(recordsByPolicy);
  }

  function renderRecoveryTimelineFallback(recordsByPolicy) {
    dom.recoverytimelinefallback.replaceChildren();
    recordsByPolicy.forEach(({ run, records }) => {
      const heading = element("h3", "", `${recoveryPolicyLabel(run.policy_id)} · ${String(run.policy_role || "comparator").replaceAll("_", " ")}`);
      dom.recoverytimelinefallback.append(heading);
      if (!records.length) {
        dom.recoverytimelinefallback.append(element("p", "", "No explicit recovery-role timeline records were projected."));
        return;
      }
      const table = element("table", "recovery-timeline-table");
      const head = element("thead");
      const headRow = element("tr");
      ["Role", "Starts", "Ends", "Record"].forEach((label) => headRow.append(element("th", "", label)));
      head.append(headRow);
      const body = element("tbody");
      records.forEach((record) => {
        const row = element("tr");
        row.append(
          element("td", "", RECOVERY_ROLE_LABELS[record.recovery_role]),
          element("td", "", formatSecondsFromNs(record.start_ns)),
          element("td", "", formatSecondsFromNs(record.end_ns)),
          element("td", "", record.event_id),
        );
        body.append(row);
      });
      table.append(head, body);
      dom.recoverytimelinefallback.append(table);
    });
  }

  function recoveryMeasureRow(run, track, value, legend) {
    const row = element("div", "recovery-policy-measure");
    row.dataset.policyRole = run.policy_role || "comparator";
    const label = element("span", "recovery-measure-label");
    label.title = `${recoveryPolicyLabel(run.policy_id)} · ${String(run.policy_role || "comparator").replaceAll("_", " ")}`;
    label.append(
      document.createTextNode(recoveryPolicyLabel(run.policy_id)),
      element("small", "", String(run.policy_role || "comparator").replaceAll("_", " ")),
    );
    row.append(label, track, element("span", "recovery-measure-value", value));
    if (legend) row.append(legend);
    return row;
  }

  function renderRecoveryWorkBars() {
    dom.recoveryworkbars.replaceChildren();
    recoveryRuns().forEach((run) => {
      const metrics = run.metrics || {};
      const attempted = metrics.attempted_compute_flops;
      const retained = metrics.valid_final_state_compute_flops;
      const lost = metrics.lost_compute_flops;
      const replay = metrics.replay_compute_flops;
      const track = element("div", "recovery-stack");
      const retainedSegment = element("span", "recovery-stack-segment");
      retainedSegment.dataset.work = "retained";
      retainedSegment.style.width = finiteNumber(attempted) && attempted > 0 && finiteNumber(retained) ? `${Math.max(0, Math.min(100, retained / attempted * 100))}%` : "0%";
      const lostSegment = element("span", "recovery-stack-segment");
      lostSegment.dataset.work = "lost";
      lostSegment.style.width = finiteNumber(attempted) && attempted > 0 && finiteNumber(lost) ? `${Math.max(0, Math.min(100, lost / attempted * 100))}%` : "0%";
      track.append(retainedSegment, lostSegment);
      const legend = element("div", "recovery-stack-legend");
      legend.append(
        element("span", "", `retained ${formatFlops(retained)}`),
        element("span", "", `lost ${formatFlops(lost)}`),
        element("span", "", `replayed subset ${formatFlops(replay)}`),
      );
      dom.recoveryworkbars.append(recoveryMeasureRow(run, track, `attempted ${formatFlops(attempted)}`, legend));
    });
  }

  function renderRecoveryByteBars() {
    dom.recoverybytebars.replaceChildren();
    recoveryRuns().forEach((run) => {
      const metrics = run.metrics || {};
      const total = metrics.total_inter_site_link_bytes;
      const track = element("div", "recovery-stack");
      const legend = element("div", "recovery-stack-legend");
      RECOVERY_BYTE_CLASSES.forEach(([key, label, color]) => {
        const value = metrics[key];
        const segment = element("span", "recovery-stack-segment recovery-byte-segment");
        segment.dataset.byteClass = key;
        segment.style.width = finiteNumber(total) && total > 0 && finiteNumber(value) ? `${Math.max(0, Math.min(100, value / total * 100))}%` : "0%";
        segment.title = `${label}: ${formatBytes(value)}`;
        track.append(segment);
        const legendItem = element("span");
        const swatch = element("i");
        swatch.style.setProperty("--legend-color", color);
        legendItem.append(swatch, document.createTextNode(`${label} ${formatBytes(value)}`));
        legend.append(legendItem);
      });
      dom.recoverybytebars.append(recoveryMeasureRow(run, track, `total ${formatBytes(total)}`, legend));
    });
  }

  function recoveryCompletionNs(run) {
    const summary = run && run.summary && typeof run.summary === "object" ? run.summary : {};
    const keys = ["mechanical_completion_ns", "durable_frontier_reached_at_ns", "completion_time_ns", "terminal_time_ns"];
    const key = keys.find((candidate) => finiteNumber(summary[candidate]));
    if (key) return summary[key];
    const durableRecovery = recoveryRecordsForRun(run).find((record) => record.recovery_role === "durable_progress_recovery");
    return durableRecovery ? durableRecovery.start_ns : null;
  }

  function renderRecoveryCompletion() {
    dom.recoverycompletionruler.replaceChildren();
    const runs = recoveryRuns();
    const completions = runs.map((run) => recoveryCompletionNs(run));
    const finiteCompletions = completions.filter(finiteNumber);
    const maxCompletion = finiteCompletions.length ? Math.max(...finiteCompletions) : null;
    runs.forEach((run, index) => {
      const completion = completions[index];
      const track = element("div", "recovery-completion-track");
      if (finiteNumber(completion) && finiteNumber(maxCompletion) && maxCompletion > 0) {
        const mark = element("span", "recovery-completion-mark");
        mark.style.left = `${Math.max(0, Math.min(100, completion / maxCompletion * 100))}%`;
        track.append(mark);
      }
      const debt = run.metrics && finiteNumber(run.metrics.recovery_debt_ns) ? formatSecondsFromNs(run.metrics.recovery_debt_ns, { fixed: 1 }) : null;
      const note = finiteNumber(completion) ? `${formatSecondsFromNs(completion)}${debt ? ` · debt ${debt}` : ""}` : "completion anchor not reported";
      dom.recoverycompletionruler.append(recoveryMeasureRow(run, track, note));
    });
    dom.recoverycompletionruler.append(element("span", "recovery-completion-axis"));
  }

  function renderRecoveryV2() {
    if (!dom.recoveryv2) return;
    if (!recoveryArtifact) {
      dom.recoveryv2.hidden = true;
      return;
    }
    dom.recoveryv2.hidden = false;
    const status = recoveryArtifact.status || {};
    const protocol = String(recoveryArtifact.protocol_hash || "not reported").slice(0, 12);
    dom.recoveryv2state.textContent = `${String(status.conclusion || "inconclusive").replaceAll("_", " ")} · MODELED mechanics · protocol ${protocol}`;
    renderRecoveryTimeline();
    renderRecoveryWorkBars();
    renderRecoveryByteBars();
    renderRecoveryCompletion();
    const unsupported = recoveryArtifact.result_scope && Array.isArray(recoveryArtifact.result_scope.unsupported) ? recoveryArtifact.result_scope.unsupported : [];
    dom.recoverylearningtrace.textContent = unsupported.length
      ? `Recovery-v2 boundary: ${unsupported.join("; ")}. LC1 below is a separate local small-model calibration.`
      : "Recovery-v2 has no held-out recovery-quality observation; LC1 below is separate evidence.";
  }

  function canonicalLearningArmId(value) {
    const normalized = String(value || "").toLowerCase().replaceAll("-", "_");
    if (normalized.includes("synchronous")) return "synchronous_reference";
    if (normalized.includes("fixed")) return "fixed_interrupted";
    if (normalized.includes("adaptive")) return "adaptive_interrupted";
    return normalized || "unknown_arm";
  }

  function learningArmLabel(value, fallback) {
    const armId = canonicalLearningArmId(value);
    return String(fallback || LEARNING_POLICY_LABELS[armId] || value || "Unknown arm").replaceAll("_", " ");
  }

  function learningMetric(record, key) {
    if (!record || typeof record !== "object") return null;
    const value = record[key];
    if (finiteNumber(value)) return value;
    if (value && typeof value === "object") {
      if (finiteNumber(value.median)) return value.median;
      if (finiteNumber(value.value)) return value.value;
    }
    return null;
  }

  function firstLearningMetric(record, keys) {
    for (const key of keys) {
      const value = learningMetric(record, key);
      if (finiteNumber(value)) return value;
    }
    return null;
  }

  function formatLearningNll(value) {
    return finiteNumber(value) ? value.toLocaleString("en-US", { minimumFractionDigits: 3, maximumFractionDigits: 4 }) : "not reported";
  }

  function formatLearningTokens(value) {
    return finiteNumber(value) ? Math.round(value).toLocaleString("en-US") : "not reported";
  }

  function formatScientific(value, digits = 3) {
    return finiteNumber(value) ? value.toExponential(digits) : "not reported";
  }

  function formatLearningEnergy(value) {
    if (!finiteNumber(value)) return "not reported";
    return value >= 1000 ? `${(value / 1000).toLocaleString("en-US", { maximumFractionDigits: 2 })} kJ` : `${value.toLocaleString("en-US", { maximumFractionDigits: 2 })} J`;
  }

  function formatLearningSeconds(value) {
    return finiteNumber(value) ? `${value.toLocaleString("en-US", { maximumFractionDigits: 2 })} s` : "not reported";
  }

  function learningTargetNll() {
    if (!learningArtifact) return null;
    if (finiteNumber(learningArtifact.target)) return learningArtifact.target;
    return firstLearningMetric(learningArtifact.target, ["held_out_nll", "target_held_out_nll", "value"]);
  }

  function learningInsightTitle(status) {
    const normalized = String(status || "").toLowerCase();
    if (normalized.includes("falsif")) return "Adaptive recovery lost the paired learning-efficiency test";
    if (normalized.includes("surviv")) return "Adaptive recovery survived the paired learning-efficiency test";
    if (normalized.includes("inconclusive")) return "The paired calibration did not separate the policies";
    return String(status || "Measured learning calibration").replaceAll("_", " ");
  }

  function renderLearningPolicyCards() {
    dom.learningpolicygrid.replaceChildren();
    const comparison = learningArtifact.policy_comparison;
    LEARNING_POLICY_ORDER.forEach((armId) => {
      const arm = comparison[armId] || {};
      const card = element("article", "learning-policy-card");
      card.dataset.arm = armId;
      const heading = element("header");
      const runCount = learningMetric(arm, "run_count");
      heading.append(
        element("h3", "", LEARNING_POLICY_LABELS[armId]),
        element("span", "learning-arm-role", `${finiteNumber(runCount) ? `${runCount}-run median · ` : "median · "}${armId === "synchronous_reference" ? "reference" : "interrupted"}`),
      );
      const triad = element("dl", "learning-metric-triad");
      const primary = [
        ["Final held-out NLL", formatLearningNll(learningMetric(arm, "final_held_out_nll")), "lower is better"],
        ["Attempted tokens", formatLearningTokens(learningMetric(arm, "attempted_tokens")), "physical work"],
        ["Progress / FLOP", formatScientific(learningMetric(arm, "progress_per_flop")), "higher is better"],
      ];
      primary.forEach(([term, value, note]) => {
        const metric = element("div", "learning-primary-metric");
        metric.append(element("dt", "", term), element("dd", "", value), element("small", "", note));
        triad.append(metric);
      });
      const supporting = element("dl", "learning-supporting-metrics");
      [
        ["Energy", formatLearningEnergy(learningMetric(arm, "energy_j"))],
        ["Active time", formatLearningSeconds(learningMetric(arm, "active_seconds"))],
        ["Target tick", finiteNumber(learningMetric(arm, "ticks_to_target")) ? String(learningMetric(arm, "ticks_to_target")) : "not reached"],
      ].forEach(([term, value]) => supporting.append(element("dt", "", term), element("dd", "", value)));
      card.append(heading, triad, supporting);
      dom.learningpolicygrid.append(card);
    });
  }

  function renderLearningCurves() {
    const svg = dom.learningcurvessvg;
    svg.replaceChildren();
    dom.learningcurvevalues.replaceChildren();
    const title = svgElement("title", { id: "learning-curves-svg-title" });
    title.textContent = "Median held-out negative log likelihood by wall tick";
    const description = svgElement("desc", { id: "learning-curves-svg-desc" });
    svg.append(title, description);
    const curves = learningArtifact.learning_curves.map((curve) => ({
      ...curve,
      arm_id: canonicalLearningArmId(curve.arm_id),
      points: Array.isArray(curve.points) ? curve.points.filter((point) => point && finiteNumber(point.wall_tick) && finiteNumber(point.median_nll)) : [],
    })).filter((curve) => curve.points.length && !String(curve.label || "").toLowerCase().includes("no failure"));
    if (!curves.length) {
      svg.setAttribute("viewBox", "0 0 1000 180");
      description.textContent = "No finite median learning-curve points were reported.";
      const empty = svgElement("text", { x: 500, y: 92, "text-anchor": "middle", class: "learning-chart-empty" });
      empty.textContent = "LEARNING CURVES UNAVAILABLE";
      svg.append(empty);
      return;
    }
    const target = learningTargetNll();
    const allPoints = curves.flatMap((curve) => curve.points);
    const maxTick = Math.max(...allPoints.map((point) => point.wall_tick), 1);
    const nllValues = allPoints.map((point) => point.median_nll);
    if (finiteNumber(target)) nllValues.push(target);
    let minNll = Math.min(...nllValues);
    let maxNll = Math.max(...nllValues);
    const nllSpan = Math.max(maxNll - minNll, Math.abs(maxNll || 1) * 0.04, 0.05);
    minNll -= nllSpan * 0.12;
    maxNll += nllSpan * 0.12;
    const left = 72;
    const right = 760;
    const top = 28;
    const bottom = 282;
    const x = (tick) => left + tick / maxTick * (right - left);
    const y = (nll) => top + (maxNll - nll) / (maxNll - minNll) * (bottom - top);
    svg.setAttribute("viewBox", "0 0 1000 330");
    description.textContent = `Three directly labeled median learning curves share a wall-tick axis. The held-out NLL target is ${formatLearningNll(target)}; lower values are better.`;
    for (let tickIndex = 0; tickIndex <= 4; tickIndex += 1) {
      const fraction = tickIndex / 4;
      const yValue = maxNll - fraction * (maxNll - minNll);
      const yPosition = top + fraction * (bottom - top);
      svg.append(svgElement("line", { x1: left, x2: right, y1: yPosition, y2: yPosition, class: "learning-gridline" }));
      const label = svgElement("text", { x: left - 10, y: yPosition + 4, "text-anchor": "end", class: "learning-axis-label" });
      label.textContent = yValue.toFixed(2);
      svg.append(label);
    }
    for (let tickIndex = 0; tickIndex <= 4; tickIndex += 1) {
      const fraction = tickIndex / 4;
      const tick = Math.round(maxTick * fraction);
      const label = svgElement("text", { x: x(tick), y: bottom + 24, "text-anchor": "middle", class: "learning-axis-label" });
      label.textContent = tick.toLocaleString("en-US");
      svg.append(label);
    }
    svg.append(
      svgElement("line", { x1: left, x2: left, y1: top, y2: bottom, class: "learning-axis" }),
      svgElement("line", { x1: left, x2: right, y1: bottom, y2: bottom, class: "learning-axis" }),
    );
    const xTitle = svgElement("text", { x: (left + right) / 2, y: 324, "text-anchor": "middle", class: "learning-axis-title" });
    xTitle.textContent = "WALL TICK";
    const yTitle = svgElement("text", { x: 17, y: (top + bottom) / 2, transform: `rotate(-90 17 ${(top + bottom) / 2})`, "text-anchor": "middle", class: "learning-axis-title" });
    yTitle.textContent = "HELD-OUT NLL ↓";
    svg.append(xTitle, yTitle);
    if (finiteNumber(target)) {
      const targetY = y(target);
      svg.append(svgElement("line", { x1: left, x2: right, y1: targetY, y2: targetY, class: "learning-target-line" }));
      const targetLabel = svgElement("text", { x: right - 4, y: targetY - 6, "text-anchor": "end", class: "learning-target-label" });
      targetLabel.textContent = `TARGET ${formatLearningNll(target)}`;
      svg.append(targetLabel);
    }
    curves.forEach((curve, curveIndex) => {
      const ordered = [...curve.points].sort((a, b) => a.wall_tick - b.wall_tick);
      const path = svgElement("path", {
        d: ordered.map((point, index) => `${index ? "L" : "M"}${x(point.wall_tick).toFixed(2)} ${y(point.median_nll).toFixed(2)}`).join(" "),
        class: "learning-curve",
        "data-arm": curve.arm_id,
      });
      svg.append(path);
      ordered.forEach((point) => svg.append(svgElement("circle", { cx: x(point.wall_tick), cy: y(point.median_nll), r: 2.8, class: "learning-curve-point", "data-arm": curve.arm_id })));
      const finalPoint = ordered[ordered.length - 1];
      const labelY = bottom - 80 + curveIndex * 36;
      svg.append(svgElement("line", { x1: x(finalPoint.wall_tick), x2: 780, y1: y(finalPoint.median_nll), y2: labelY - 4, class: "learning-label-leader", "data-arm": curve.arm_id }));
      const endLabel = svgElement("text", { x: 790, y: labelY, class: "learning-curve-label", "data-arm": curve.arm_id });
      endLabel.textContent = `${learningArmLabel(curve.arm_id, curve.label)} · ${formatLearningNll(finalPoint.median_nll)}`;
      svg.append(endLabel);
      const listItem = element("li");
      listItem.dataset.arm = curve.arm_id;
      listItem.append(element("span", "", learningArmLabel(curve.arm_id, curve.label)), element("strong", "", `${formatLearningNll(finalPoint.median_nll)} NLL at tick ${finalPoint.wall_tick.toLocaleString("en-US")}`));
      dom.learningcurvevalues.append(listItem);
    });
  }

  function pairedEffectValue(rawValue) {
    if (finiteNumber(rawValue)) return rawValue;
    return firstLearningMetric(rawValue, ["value", "effect", "tau", "direct_interrupted_difference", "adaptive_minus_fixed"]);
  }

  function renderLearningPairedEffect() {
    const svg = dom.learningpairedsvg;
    svg.replaceChildren();
    const title = svgElement("title", { id: "learning-paired-svg-title" });
    title.textContent = "Six paired adaptive-minus-fixed learning-efficiency effects";
    const description = svgElement("desc", { id: "learning-paired-svg-desc" });
    svg.append(title, description);
    const effect = learningArtifact.paired_effect;
    const pairs = Array.isArray(learningArtifact.evaluation_pairs) ? learningArtifact.evaluation_pairs : [];
    const values = effect.values.map((rawValue, index) => ({
      label: rawValue && typeof rawValue === "object" && rawValue.stratum_id ? String(rawValue.stratum_id) : pairs[index] && pairs[index].stratum_id ? String(pairs[index].stratum_id) : `E${index + 1}`,
      value: pairedEffectValue(rawValue),
    })).filter((entry) => finiteNumber(entry.value));
    const median = pairedEffectValue(effect.median);
    const lower = pairedEffectValue(effect.lower_bound);
    const upper = pairedEffectValue(effect.upper_bound);
    const domainValues = [0, ...values.map((entry) => entry.value), median, lower, upper].filter(finiteNumber);
    if (!values.length || !domainValues.length) {
      svg.setAttribute("viewBox", "0 0 1000 180");
      description.textContent = "No finite paired effects were reported.";
      const empty = svgElement("text", { x: 500, y: 92, "text-anchor": "middle", class: "learning-chart-empty" });
      empty.textContent = "PAIRED EFFECTS UNAVAILABLE";
      svg.append(empty);
      dom.learningpairedsummary.textContent = "Paired interval not reported.";
      return;
    }
    let domainMin = Math.min(...domainValues);
    let domainMax = Math.max(...domainValues);
    const span = Math.max(domainMax - domainMin, Math.max(Math.abs(domainMin), Math.abs(domainMax), 1e-16) * 0.2);
    domainMin -= span * 0.12;
    domainMax += span * 0.12;
    const left = 155;
    const right = 750;
    const firstY = 48;
    const rowGap = 34;
    const intervalY = firstY + values.length * rowGap + 16;
    const height = intervalY + 72;
    const x = (value) => left + (value - domainMin) / (domainMax - domainMin) * (right - left);
    svg.setAttribute("viewBox", `0 0 1000 ${height}`);
    description.textContent = "Each row is one matched stratum. Effects left of zero favor fixed-local recovery; effects right of zero favor adaptive recovery. The final row shows the reported median interval.";
    const zeroX = x(0);
    svg.append(svgElement("line", { x1: zeroX, x2: zeroX, y1: 24, y2: intervalY + 16, class: "learning-zero-line" }));
    values.forEach((entry, index) => {
      const rowY = firstY + index * rowGap;
      svg.append(svgElement("line", { x1: left, x2: right, y1: rowY, y2: rowY, class: "learning-effect-track" }));
      const rowLabel = svgElement("text", { x: left - 12, y: rowY + 4, "text-anchor": "end", class: "learning-effect-label" });
      rowLabel.textContent = entry.label;
      const point = svgElement("circle", { cx: x(entry.value), cy: rowY, r: 5, class: "learning-effect-point" });
      const pointTitle = svgElement("title");
      pointTitle.textContent = `${entry.label}: adaptive minus fixed is ${formatScientific(entry.value)}`;
      point.append(pointTitle);
      const valueLabel = svgElement("text", { x: 780, y: rowY + 4, class: "learning-effect-value" });
      valueLabel.textContent = formatScientific(entry.value);
      svg.append(rowLabel, point, valueLabel);
    });
    if (finiteNumber(lower) && finiteNumber(upper) && finiteNumber(median)) {
      svg.append(
        svgElement("line", { x1: left, x2: right, y1: intervalY, y2: intervalY, class: "learning-effect-track" }),
        svgElement("line", { x1: x(lower), x2: x(upper), y1: intervalY, y2: intervalY, class: "learning-interval-line" }),
        svgElement("line", { x1: x(lower), x2: x(lower), y1: intervalY - 7, y2: intervalY + 7, class: "learning-interval-cap" }),
        svgElement("line", { x1: x(upper), x2: x(upper), y1: intervalY - 7, y2: intervalY + 7, class: "learning-interval-cap" }),
      );
      const medianMark = svgElement("rect", { x: x(median) - 5, y: intervalY - 5, width: 10, height: 10, transform: `rotate(45 ${x(median)} ${intervalY})`, class: "learning-interval-median" });
      const intervalLabel = svgElement("text", { x: left - 12, y: intervalY + 4, "text-anchor": "end", class: "learning-effect-label" });
      intervalLabel.textContent = "MEDIAN INTERVAL";
      svg.append(intervalLabel, medianMark);
    }
    const fixedLabel = svgElement("text", { x: left, y: height - 18, class: "learning-effect-direction" });
    fixedLabel.textContent = "← FIXED BETTER";
    const adaptiveLabel = svgElement("text", { x: right, y: height - 18, "text-anchor": "end", class: "learning-effect-direction" });
    adaptiveLabel.textContent = "ADAPTIVE BETTER →";
    svg.append(fixedLabel, adaptiveLabel);
    const confidence = finiteNumber(effect.confidence_level) ? `${Math.round(effect.confidence_level * 100)}%` : "reported";
    dom.learningpairedsummary.textContent = finiteNumber(median) && finiteNumber(lower) && finiteNumber(upper)
      ? `${confidence} paired-median interval: ${formatScientific(lower)} to ${formatScientific(upper)}; median ${formatScientific(median)}. Positive values favor adaptive recovery.`
      : "The artifact reports stratum effects without a complete interval.";
  }

  function renderLearningGates() {
    dom.learninggatestrip.replaceChildren();
    Object.entries(learningArtifact.falsifier_results).forEach(([gateId, passed]) => {
      const gate = element("div", "learning-gate");
      const labels = learningArtifact.falsifier_labels && typeof learningArtifact.falsifier_labels === "object" ? learningArtifact.falsifier_labels : {};
      const label = typeof labels[gateId] === "string" ? labels[gateId] : gateId.replaceAll("_", " ");
      gate.dataset.passed = String(passed === true);
      gate.setAttribute("aria-label", `${label}: ${passed === true ? "pass" : "fail"}`);
      gate.append(
        element("span", "learning-gate-state", passed === true ? "PASS" : "FAIL"),
        element("span", "learning-gate-label", label),
      );
      dom.learninggatestrip.append(gate);
    });
  }

  function learningBoundaryText(boundary) {
    if (typeof boundary === "string") return boundary;
    if (Array.isArray(boundary)) return boundary.map(String).join("; ");
    if (!boundary || typeof boundary !== "object") return "No evidence boundary was reported.";
    const clauses = [];
    if (typeof boundary.summary === "string") clauses.push(boundary.summary);
    if (Array.isArray(boundary.supported)) clauses.push(`Supports: ${boundary.supported.join("; ")}`);
    if (Array.isArray(boundary.unsupported)) clauses.push(`Does not support: ${boundary.unsupported.join("; ")}`);
    if (!clauses.length) clauses.push(Object.entries(boundary).map(([key, value]) => `${key.replaceAll("_", " ")}: ${Array.isArray(value) ? value.join("; ") : String(value)}`).join(". "));
    return clauses.join(". ");
  }

  function renderLearningTrace() {
    dom.learningevaluationpairs.replaceChildren();
    learningArtifact.evaluation_pairs.forEach((pair, index) => {
      const row = element("tr");
      const fixed = firstLearningMetric(pair, ["fixed_interrupted_progress_per_flop", "fixed_progress_per_flop"]);
      const adaptive = firstLearningMetric(pair, ["adaptive_interrupted_progress_per_flop", "adaptive_progress_per_flop"]);
      const difference = firstLearningMetric(pair, ["direct_interrupted_difference", "tau", "adaptive_minus_fixed"]);
      row.append(
        element("td", "", String(pair.stratum_id || pair.pair_id || `E${index + 1}`)),
        element("td", "", formatScientific(fixed)),
        element("td", "", formatScientific(adaptive)),
        element("td", "", formatScientific(difference)),
      );
      dom.learningevaluationpairs.append(row);
    });
    if (!learningArtifact.evaluation_pairs.length) {
      const row = element("tr");
      const cell = element("td", "", "No paired evaluation rows reported.");
      cell.colSpan = 4;
      row.append(cell);
      dom.learningevaluationpairs.append(row);
    }
    dom.learningrundetails.replaceChildren();
    learningArtifact.run_details.forEach((run, index) => {
      const energy = firstLearningMetric(run, ["energy_j", "idle_subtracted_energy_j", "raw_energy_j"])
        ?? (run.energy && firstLearningMetric(run.energy, ["idle_subtracted_energy_j", "raw_energy_j"]));
      const row = element("tr");
      row.append(
        element("td", "", String(run.run_id || run.arm_id || run.label || `run ${index + 1}`)),
        element("td", "", String(run.stratum_id || "not reported")),
        element("td", "", formatLearningNll(firstLearningMetric(run, ["final_held_out_nll", "median_final_held_out_nll"]))),
        element("td", "", formatLearningTokens(firstLearningMetric(run, ["attempted_tokens"]))),
        element("td", "", formatLearningEnergy(energy)),
        element("td", "", formatLearningSeconds(firstLearningMetric(run, ["active_seconds", "local_wall_clock_seconds", "physical_wall_clock_seconds"]))),
      );
      dom.learningrundetails.append(row);
    });
    if (!learningArtifact.run_details.length) {
      const row = element("tr");
      const cell = element("td", "", "No run-level rows reported.");
      cell.colSpan = 6;
      row.append(cell);
      dom.learningrundetails.append(row);
    }
    const provenance = {
      schema: learningArtifact.schema,
      artifact_sha256: learningArtifact.artifact_sha256,
      source_learning_result: learningArtifact.source_learning_result,
      target: learningArtifact.target,
      dataset: learningArtifact.dataset,
      runtime: learningArtifact.runtime,
    };
    dom.learningprovenancejson.textContent = JSON.stringify(provenance, null, 2);
    const sourceHash = learningArtifact.source_learning_result && (learningArtifact.source_learning_result.artifact_sha256 || learningArtifact.source_learning_result.sha256);
    dom.learningdepthtrace.textContent = `${learningArtifact.evaluation_pairs.length} paired strata · ${learningArtifact.run_details.length} run records · source ${String(sourceHash || "hash not reported")}.`;
  }

  function renderLearningV1() {
    if (!dom.learningv1) return;
    if (!learningArtifact) {
      dom.learningv1.hidden = true;
      return;
    }
    dom.learningv1.hidden = false;
    const conclusion = learningArtifact.conclusion;
    const hash = String(learningArtifact.artifact_sha256).replace(/^sha256:/, "").slice(0, 12);
    dom.learningv1state.textContent = `${String(conclusion.status).replaceAll("_", " ")} · OBSERVED learning · artifact ${hash}`;
    dom.learninginsighttitle.textContent = learningInsightTitle(conclusion.status);
    dom.learningplainanswer.textContent = conclusion.plain_answer;
    setPlainWords("learning-plain-words", conclusion.status);
    dom.learningevidenceboundary.textContent = learningBoundaryText(learningArtifact.evidence_boundary);
    renderLearningPolicyCards();
    renderLearningCurves();
    renderLearningPairedEffect();
    renderLearningGates();
    renderLearningTrace();
  }

  function formatEqualWorkPercent(value, digits = 2) {
    return finiteNumber(value) ? `${(value * 100).toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits })}%` : "not reported";
  }

  function formatEqualWorkRatio(value, digits = 3) {
    return finiteNumber(value) ? `${value.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits })}×` : "not reported";
  }

  function equalWorkEnergyLimit() {
    if (!equalWorkArtifact) return null;
    const label = equalWorkArtifact.falsifier_labels.device_energy_ratio_bounded;
    const match = typeof label === "string" ? label.match(/within\s+([0-9]+(?:\.[0-9]+)?)%/i) : null;
    return match ? 1 + Number(match[1]) / 100 : null;
  }

  function equalWorkPolicyLabel(policyId) {
    if (policyId === "fixed-local-checkpoint-restart") return "Fixed-local restart";
    if (policyId === "adaptive-survivor-continuation") return "Adaptive survivor continuation";
    return String(policyId || "unknown policy").replaceAll("-", " ");
  }

  function appendMetricDefinition(list, term, value, note) {
    const metric = element("div", "equal-work-metric");
    metric.append(element("dt", "", term), element("dd", "", value));
    if (note) metric.append(element("small", "", note));
    list.append(metric);
  }

  function renderEqualWorkFreshmanSummary() {
    dom.equalworkfreshmangrid.replaceChildren();
    const target = equalWorkArtifact.canonical_target.canonical_tokens;
    const effects = equalWorkArtifact.paired_effects;
    const cards = [
      {
        state: "pass",
        kicker: "Fair endpoint",
        value: formatLearningTokens(target),
        title: "useful tokens each",
        body: "Both policies delivered the exact same amount of training that the model actually kept.",
      },
      {
        state: "pass",
        kicker: "Redo avoided",
        value: formatEqualWorkPercent(effects.attempted_flop_savings.median),
        title: "less attempted work",
        body: `${formatEqualWorkPercent(effects.attempted_flop_savings.lower_bound)} to ${formatEqualWorkPercent(effects.attempted_flop_savings.upper_bound)} across the paired 90% interval.`,
      },
      {
        state: "pass",
        kicker: "Schedule saved",
        value: String(effects.opportunity_tick_savings.median),
        title: "fewer opportunity ticks",
        body: "Adaptive reached the equal-work frontier sooner on all six frozen failure schedules.",
      },
      {
        state: "fail",
        kicker: "Why LC3 failed",
        value: formatEqualWorkRatio(effects.adaptive_to_fixed_device_energy_ratio.median),
        title: "device-energy ratio",
        body: `${formatEqualWorkRatio(effects.adaptive_to_fixed_device_energy_ratio.lower_bound)} to ${formatEqualWorkRatio(effects.adaptive_to_fixed_device_energy_ratio.upper_bound)}; the frozen limit was ${formatEqualWorkRatio(equalWorkEnergyLimit())}.`,
      },
    ];
    cards.forEach((entry) => {
      const card = element("article", "equal-work-plain-card");
      card.dataset.state = entry.state;
      card.append(
        element("p", "equal-work-plain-kicker", entry.kicker),
        element("strong", "equal-work-plain-value", entry.value),
        element("h3", "", entry.title),
        element("p", "equal-work-plain-body", entry.body),
      );
      dom.equalworkfreshmangrid.append(card);
    });
  }

  function renderEqualWorkPolicyCards() {
    dom.equalworkpolicygrid.replaceChildren();
    ["fixed_interrupted", "adaptive_interrupted"].forEach((policyKey) => {
      const policy = equalWorkArtifact.policy_comparison[policyKey];
      const card = element("article", "equal-work-policy-card");
      card.dataset.policy = policyKey.startsWith("adaptive") ? "adaptive" : "fixed";
      const header = element("header");
      header.append(
        element("h4", "", policy.label || equalWorkPolicyLabel(policy.policy_id)),
        element("span", "", `${policy.run_count}-run median`),
      );
      const metrics = element("dl", "equal-work-policy-metrics");
      appendMetricDefinition(metrics, "Final held-out NLL", formatLearningNll(policy.final_held_out_nll), "lower is better");
      appendMetricDefinition(metrics, "Attempted / useful tokens", `${formatLearningTokens(policy.attempted_tokens)} / ${formatLearningTokens(policy.canonical_tokens)}`, "physical / canonical work");
      appendMetricDefinition(metrics, "Opportunity ticks", policy.opportunity_ticks.toLocaleString("en-US"), "schedule ruler");
      appendMetricDefinition(metrics, "Training-device energy", formatLearningEnergy(policy.training_device_energy_j), "idle subtracted");
      appendMetricDefinition(metrics, "Local active time", formatLearningSeconds(policy.local_active_seconds), "not datacenter elapsed time");
      appendMetricDefinition(metrics, "Checkpoint writes", `${policy.checkpoint_count.toLocaleString("en-US")} · ${formatBytes(policy.checkpoint_bytes)}`, "count · bytes");
      card.append(header, metrics);
      dom.equalworkpolicygrid.append(card);
    });
  }

  function renderEqualWorkEffects() {
    dom.equalworkeffectgrid.replaceChildren();
    const effects = equalWorkArtifact.paired_effects;
    const margin = equalWorkArtifact.noninferiority_margin_nll;
    const energyLimit = equalWorkEnergyLimit();
    const definitions = [
      {
        id: "learning",
        label: "Learning preserved",
        value: `+${effects.adaptive_minus_fixed_nll.median.toFixed(5)} Δ NLL`,
        interval: `90% interval +${effects.adaptive_minus_fixed_nll.lower_bound.toFixed(5)} to +${effects.adaptive_minus_fixed_nll.upper_bound.toFixed(5)}`,
        bound: `frozen noninferiority margin ≤ ${margin.toFixed(5)}`,
        passed: equalWorkArtifact.falsifier_results.learning_noninferior === true,
      },
      {
        id: "work",
        label: "Attempted work saved",
        value: formatEqualWorkPercent(effects.attempted_flop_savings.median),
        interval: `90% interval ${formatEqualWorkPercent(effects.attempted_flop_savings.lower_bound)} to ${formatEqualWorkPercent(effects.attempted_flop_savings.upper_bound)}`,
        bound: "positive saving required",
        passed: equalWorkArtifact.falsifier_results.attempted_flop_saving_positive === true,
      },
      {
        id: "ticks",
        label: "Schedule ticks saved",
        value: `${effects.opportunity_tick_savings.median.toLocaleString("en-US")} ticks`,
        interval: `90% interval ${effects.opportunity_tick_savings.lower_bound.toLocaleString("en-US")} to ${effects.opportunity_tick_savings.upper_bound.toLocaleString("en-US")}`,
        bound: "all six schedules favored adaptive",
        passed: equalWorkArtifact.falsifier_results.opportunity_tick_saving_material === true,
      },
      {
        id: "energy",
        label: "Device energy bounded",
        value: formatEqualWorkRatio(effects.adaptive_to_fixed_device_energy_ratio.median),
        interval: `90% interval ${formatEqualWorkRatio(effects.adaptive_to_fixed_device_energy_ratio.lower_bound)} to ${formatEqualWorkRatio(effects.adaptive_to_fixed_device_energy_ratio.upper_bound)}`,
        bound: `frozen upper bound ≤ ${formatEqualWorkRatio(energyLimit)}`,
        passed: equalWorkArtifact.falsifier_results.device_energy_ratio_bounded === true,
      },
    ];
    definitions.forEach((definition) => {
      const card = element("article", "equal-work-effect-card");
      card.dataset.effect = definition.id;
      card.dataset.passed = String(definition.passed);
      const status = element("span", "equal-work-effect-status", definition.passed ? "PASS" : "FAIL");
      const header = element("header");
      header.append(element("h4", "", definition.label), status);
      card.append(
        header,
        element("strong", "equal-work-effect-value", definition.value),
        element("p", "equal-work-effect-interval", definition.interval),
        element("p", "equal-work-effect-bound", definition.bound),
      );
      dom.equalworkeffectgrid.append(card);
    });
  }

  function renderEqualWorkGates() {
    dom.equalworkgatestrip.replaceChildren();
    const entries = Object.entries(equalWorkArtifact.falsifier_results)
      .sort((left, right) => Number(left[1] === true) - Number(right[1] === true));
    entries.forEach(([gateId, passed]) => {
      const label = equalWorkArtifact.falsifier_labels[gateId] || gateId.replaceAll("_", " ");
      const gate = element("div", "equal-work-gate");
      gate.dataset.passed = String(passed === true);
      gate.setAttribute("aria-label", `${label}: ${passed === true ? "pass" : "fail"}`);
      gate.append(
        element("span", "equal-work-gate-state", passed === true ? "PASS" : "FAIL"),
        element("span", "equal-work-gate-label", label),
      );
      dom.equalworkgatestrip.append(gate);
    });
  }

  function renderEqualWorkTrace() {
    dom.equalworkevaluationpairs.replaceChildren();
    equalWorkArtifact.evaluation_pairs.forEach((pair) => {
      const row = element("tr");
      row.append(
        element("td", "", pair.stratum_id),
        element("td", "", formatLearningNll(pair.fixed_final_held_out_nll)),
        element("td", "", formatLearningNll(pair.adaptive_final_held_out_nll)),
        element("td", "", `${pair.adaptive_minus_fixed_final_nll >= 0 ? "+" : ""}${pair.adaptive_minus_fixed_final_nll.toFixed(6)}`),
        element("td", "", formatEqualWorkPercent(pair.attempted_flop_saving_fraction)),
        element("td", "", pair.opportunity_tick_saving.toLocaleString("en-US")),
        element("td", "", formatEqualWorkRatio(pair.adaptive_to_fixed_device_energy_ratio)),
      );
      dom.equalworkevaluationpairs.append(row);
    });

    dom.equalworkrundetails.replaceChildren();
    equalWorkArtifact.run_details.forEach((run) => {
      const row = element("tr");
      row.append(
        element("td", "", run.run_id),
        element("td", "", `${run.split} · ${run.stratum_id}`),
        element("td", "", equalWorkPolicyLabel(run.policy_id)),
        element("td", "", run.interrupted ? "yes" : "no"),
        element("td", "", formatLearningNll(run.final_held_out_nll)),
        element("td", "", `${formatLearningTokens(run.attempted_tokens)} / ${formatLearningTokens(run.canonical_tokens)}`),
        element("td", "", run.opportunity_ticks.toLocaleString("en-US")),
        element("td", "", formatLearningEnergy(run.training_device_energy_j)),
        element("td", "", `${run.checkpoint_count.toLocaleString("en-US")} · ${formatBytes(run.checkpoint_bytes)}`),
      );
      dom.equalworkrundetails.append(row);
    });

    dom.equalworkpredecessors.replaceChildren();
    equalWorkArtifact.source_lc2_protocol_results.forEach((predecessor) => {
      const row = element("tr");
      row.append(
        element("td", "", predecessor.path),
        element("td", "", predecessor.conclusion.replaceAll("_", " ")),
        element("td", "equal-work-hash", predecessor.artifact_sha256),
      );
      dom.equalworkpredecessors.append(row);
    });

    const bridge = equalWorkArtifact.mechanics_bridge;
    dom.equalworkbridge.replaceChildren();
    dom.equalworkbridge.append(
      element("p", "equal-work-bridge-boundary", bridge.plain_boundary),
      element("p", "equal-work-bridge-class", `Evidence class: ${String(bridge.evidence_class).replaceAll("_", " ")}. Recovery source: ${bridge.source_recovery_artifact_sha256}.`),
    );
    const columns = element("div", "equal-work-bridge-columns");
    [
      ["Assumptions", bridge.assumptions],
      ["Non-comparabilities", bridge.non_comparabilities],
    ].forEach(([title, values]) => {
      const section = element("section");
      section.append(element("h4", "", title));
      const list = element("ul");
      values.forEach((value) => list.append(element("li", "", value)));
      section.append(list);
      columns.append(section);
    });
    dom.equalworkbridge.append(columns);

    const provenance = {
      schema: equalWorkArtifact.schema,
      artifact_sha256: equalWorkArtifact.artifact_sha256,
      source_result: equalWorkArtifact.source_result,
      source_learning_result: equalWorkArtifact.source_learning_result,
      source_recovery_result: equalWorkArtifact.source_recovery_result,
      source_lc2_protocol_results: equalWorkArtifact.source_lc2_protocol_results,
      dataset: equalWorkArtifact.dataset,
      runtime: equalWorkArtifact.runtime,
      warm_start_checkpoint_sha256: equalWorkArtifact.warm_start && equalWorkArtifact.warm_start.checkpoint_sha256,
      mechanics_bridge: equalWorkArtifact.mechanics_bridge,
    };
    dom.equalworkprovenancejson.textContent = JSON.stringify(provenance, null, 2);
    dom.equalworkdepthtrace.textContent = `${equalWorkArtifact.evaluation_pairs.length} paired evaluation rows · ${equalWorkArtifact.run_details.length} run records · ${equalWorkArtifact.source_lc2_protocol_results.length} LC2 protocol predecessors · source result ${equalWorkArtifact.source_result.artifact_sha256}.`;
  }

  function renderEqualWorkV1() {
    if (!dom.equalworkv1) return;
    if (!equalWorkArtifact) {
      dom.equalworkv1.hidden = true;
      return;
    }
    dom.equalworkv1.hidden = false;
    const conclusion = equalWorkArtifact.conclusion;
    dom.equalworkv1state.textContent = `${String(conclusion.status).replaceAll("_", " ")} · OBSERVED local learning · artifact ${equalWorkArtifact.artifact_sha256.slice(0, 12)}`;
    dom.equalworkinsighttitle.textContent = "Adaptive kept the learning and saved work, but missed the energy bound";
    dom.equalworkplainanswer.textContent = conclusion.plain_answer;
    setPlainWords("equal-work-plain-words", conclusion.status);
    dom.equalworkevidenceboundary.textContent = learningBoundaryText(equalWorkArtifact.evidence_boundary);
    const fixed = equalWorkArtifact.policy_comparison.fixed_interrupted;
    const adaptive = equalWorkArtifact.policy_comparison.adaptive_interrupted;
    const checkpointRatio = adaptive.checkpoint_bytes / fixed.checkpoint_bytes;
    dom.equalworkcheckpointclue.textContent = `Adaptive wrote ${formatBytes(adaptive.checkpoint_bytes)} across ${adaptive.checkpoint_count} checkpoints versus fixed at ${formatBytes(fixed.checkpoint_bytes)} across ${fixed.checkpoint_count}. That is ${formatEqualWorkRatio(checkpointRatio)} the checkpoint bytes, alongside more local active time. The association motivates phase-level power attribution; it does not identify the energy cause.`;
    renderEqualWorkFreshmanSummary();
    renderEqualWorkPolicyCards();
    renderEqualWorkEffects();
    renderEqualWorkGates();
    renderEqualWorkTrace();
  }

  function checkpointPowerHumanLabel(value) {
    return String(value || "not reported")
      .replaceAll("_", " ")
      .replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  function checkpointPowerInterval(effect, formatter) {
    if (!effect || !finiteNumber(effect.lower_bound) || !finiteNumber(effect.median) || !finiteNumber(effect.upper_bound)) return "interval not reported";
    return `${formatter(effect.median)} median · 90% interval ${formatter(effect.lower_bound)} to ${formatter(effect.upper_bound)}`;
  }

  function renderCheckpointPowerFreshman() {
    dom.checkpointpowerfreshmangrid.replaceChildren();
    checkpointPowerArtifact.freshman.cards.forEach((entry) => {
      const card = element("article", "checkpoint-power-plain-card");
      card.dataset.state = entry.state;
      card.append(
        element("p", "checkpoint-power-plain-label", entry.label),
        element("strong", "checkpoint-power-plain-value", entry.value),
        element("p", "checkpoint-power-plain-detail", entry.detail),
      );
      dom.checkpointpowerfreshmangrid.append(card);
    });
  }

  function renderCheckpointPowerValidity() {
    const researcher = checkpointPowerArtifact.researcher;
    dom.checkpointpowerinvalidators.replaceChildren();
    researcher.invalidators.forEach((invalidator, index) => {
      const item = element("article", "checkpoint-power-invalidator");
      item.append(
        element("span", "checkpoint-power-invalidator-number", String(index + 1)),
        element("div", "", checkpointPowerHumanLabel(invalidator)),
        element("strong", "", "ACTIVE · CLAIM BLOCKED"),
      );
      dom.checkpointpowerinvalidators.append(item);
    });

    const logger = researcher.logger;
    const ratio = logger.effective_update_period_ms / logger.requested_poll_ms;
    dom.checkpointpowerlogger.replaceChildren();
    const heading = element("header");
    heading.append(element("h4", "", "Logger calibration"), element("span", "checkpoint-power-boundary-badge", logger.boundary_hit ? "BOUNDARY HIT" : "inside boundary"));
    const comparison = element("div", "checkpoint-power-poll-comparison");
    [
      ["Requested poll", `${logger.requested_poll_ms.toLocaleString("en-US", { maximumFractionDigits: 1 })} ms`],
      ["Effective update", `${logger.effective_update_period_ms.toLocaleString("en-US", { maximumFractionDigits: 3 })} ms`],
    ].forEach(([label, value]) => {
      const metric = element("div");
      metric.append(element("span", "", label), element("strong", "", value));
      comparison.append(metric);
    });
    const detail = element("p", "", `${ratio.toLocaleString("en-US", { maximumFractionDigits: 1 })}× coarser than requested · selected delay ${logger.selected_delay_ms.toLocaleString("en-US", { maximumFractionDigits: 1 })} ms · correlation ${logger.selected_correlation.toLocaleString("en-US", { maximumFractionDigits: 3 })}.`);
    dom.checkpointpowerlogger.append(heading, comparison, detail);
  }

  function renderCheckpointPowerArms() {
    dom.checkpointpowerarmgrid.replaceChildren();
    checkpointPowerArtifact.researcher.arm_rows.forEach((arm) => {
      const card = element("article", "checkpoint-power-arm-card");
      card.dataset.arm = arm.arm_code;
      const header = element("header");
      header.append(
        element("span", "checkpoint-power-arm-code", arm.arm_code),
        element("div", "", `${checkpointPowerHumanLabel(arm.checkpoint_cadence)} cadence · ${checkpointPowerHumanLabel(arm.continuation)}`),
        element("strong", "", `${arm.run_count}-run median`),
      );
      const metrics = element("dl", "checkpoint-power-arm-metrics");
      [
        ["Final held-out NLL", formatLearningNll(arm.median_final_held_out_nll)],
        ["Attempted tokens", formatLearningTokens(arm.median_attempted_tokens)],
        ["Opportunity ticks", arm.median_opportunity_ticks.toLocaleString("en-US")],
        ["Checkpoints", `${arm.median_checkpoint_count.toLocaleString("en-US")} · ${formatBytes(arm.median_checkpoint_bytes)}`],
        ["Raw board energy", `${formatLearningEnergy(arm.median_idle_subtracted_gpu_board_energy_j)} · INADMISSIBLE`],
      ].forEach(([term, value]) => {
        const metric = element("div");
        metric.append(element("dt", "", term), element("dd", "", value));
        metrics.append(metric);
      });
      card.append(header, metrics);
      dom.checkpointpowerarmgrid.append(card);
    });
  }

  function renderCheckpointPowerControls() {
    dom.checkpointpowercontrolgrid.replaceChildren();
    checkpointPowerArtifact.researcher.calibration_equivalence.forEach((control) => {
      const card = element("article", "checkpoint-power-control-card");
      const title = element("h4", "", `${control.block_id} · ${checkpointPowerHumanLabel(control.checkpoint_cadence)} cadence`);
      const checks = element("ul");
      [
        ["Training state", control.state_exactly_equal],
        ["Attempted work", control.work_exactly_equal],
        ["Final NLL", control.final_nll_exactly_equal],
      ].forEach(([label, passed]) => {
        const item = element("li");
        item.dataset.passed = String(passed === true);
        item.append(element("strong", "", passed === true ? "EXACT" : "MISMATCH"), document.createTextNode(` ${label}`));
        checks.append(item);
      });
      card.append(title, checks);
      dom.checkpointpowercontrolgrid.append(card);
    });
  }

  function checkpointPowerContrastCard(title, value, detail) {
    const card = element("article", "checkpoint-power-contrast-card");
    card.setAttribute("aria-label", `${title}, inadmissible diagnostic`);
    card.append(
      element("span", "checkpoint-power-inadmissible", "INADMISSIBLE"),
      element("h4", "", title),
      element("strong", "checkpoint-power-contrast-value", value),
      element("p", "", detail),
    );
    return card;
  }

  function renderCheckpointPowerContrasts() {
    const signals = checkpointPowerArtifact.researcher.raw_inadmissible_signals;
    dom.checkpointpowercontrastlabel.textContent = signals.label;
    dom.checkpointpowercontrastgrid.replaceChildren();
    dom.checkpointpowercontrastgrid.append(
      checkpointPowerContrastCard(
        "Total cadence × continuation interaction",
        formatScientific(signals.primary_total_interaction.median),
        `${checkpointPowerInterval(signals.primary_total_interaction, (value) => formatScientific(value))} J per canonical token.`,
      ),
      checkpointPowerContrastCard(
        "Checkpoint-related interaction",
        formatScientific(signals.checkpoint_related_interaction.median),
        `${checkpointPowerInterval(signals.checkpoint_related_interaction, (value) => formatScientific(value))} J per canonical token.`,
      ),
      checkpointPowerContrastCard(
        "LC3 corner energy ratio",
        formatEqualWorkRatio(signals.lc3_corner_reproduction.dense_continue_to_sparse_restart_energy_ratio.median),
        `${checkpointPowerInterval(signals.lc3_corner_reproduction.dense_continue_to_sparse_restart_energy_ratio, (value) => formatEqualWorkRatio(value))}. Penalty reproduced: ${signals.lc3_corner_reproduction.penalty_reproduced ? "yes" : "no"}.`,
      ),
      checkpointPowerContrastCard(
        "Sparse continuation energy ratio",
        formatEqualWorkRatio(signals.sparse_continuation_salvage.device_energy_ratio.median),
        `${checkpointPowerInterval(signals.sparse_continuation_salvage.device_energy_ratio, (value) => formatEqualWorkRatio(value))}. This does not qualify sparse continuation as passing.`,
      ),
    );
  }

  function renderCheckpointPowerRedirect() {
    const next = checkpointPowerArtifact.next_experiment;
    dom.checkpointpowernextquestion.textContent = `${next.id}: ${next.question}`;
    dom.checkpointpowernextfrozen.replaceChildren();
    next.do_not_change.forEach((value) => dom.checkpointpowernextfrozen.append(element("li", "", value)));
    dom.checkpointpowernextevidence.replaceChildren();
    next.required_new_evidence.forEach((value) => dom.checkpointpowernextevidence.append(element("li", "", value)));
  }

  function checkpointPowerSelectedRun() {
    if (!checkpointPowerArtifact) return null;
    const runId = dom.checkpointpowerrunselect.value;
    return checkpointPowerArtifact.full_trace.run_ledger.find((run) => run.run_id === runId) || checkpointPowerArtifact.full_trace.run_ledger[0] || null;
  }

  function renderCheckpointPowerRunSelector() {
    const previous = dom.checkpointpowerrunselect.value;
    dom.checkpointpowerrunselect.replaceChildren();
    checkpointPowerArtifact.full_trace.run_ledger.forEach((run) => {
      const option = element("option", "", `${run.block_id} · ${run.arm_code} · ${run.run_id}`);
      option.value = run.run_id;
      dom.checkpointpowerrunselect.append(option);
    });
    if (checkpointPowerArtifact.full_trace.run_ledger.some((run) => run.run_id === previous)) dom.checkpointpowerrunselect.value = previous;
  }

  function renderCheckpointPowerLedger() {
    dom.checkpointpowerrunledger.replaceChildren();
    checkpointPowerArtifact.full_trace.run_ledger.forEach((run) => {
      const row = element("tr");
      row.append(
        element("td", "", run.run_id),
        element("td", "", `${run.split} · ${run.block_id} · ${run.execution_order_id}/${run.execution_position}`),
        element("td", "", `${run.arm_code} · ${run.checkpoint_cadence} · ${run.continuation}`),
        element("td", "", `${formatLearningTokens(run.attempted_tokens)} / ${formatLearningTokens(run.canonical_tokens)}`),
        element("td", "", formatLearningNll(run.final_held_out_nll)),
        element("td", "", `${run.raw_sample_count.toLocaleString("en-US")} / ${run.effective_power_update_count.toLocaleString("en-US")}`),
        element("td", "checkpoint-power-inadmissible-cell", `${formatLearningEnergy(run.idle_subtracted_gpu_board_energy_j)} · inadmissible`),
        element("td", "", `${run.checkpoint_count.toLocaleString("en-US")} · ${formatBytes(run.checkpoint_bytes)}`),
        element("td", "checkpoint-power-hash", run.raw_trace_sha256),
      );
      dom.checkpointpowerrunledger.append(row);
    });
  }

  function renderCheckpointPowerPhaseMetrics() {
    dom.checkpointpowerphasemetrics.replaceChildren();
    const run = checkpointPowerSelectedRun();
    if (!run || !run.phase_metrics || typeof run.phase_metrics !== "object") return;
    Object.entries(run.phase_metrics).forEach(([phase, metrics]) => {
      const row = element("tr");
      row.append(
        element("td", "", phase),
        element("td", "", formatLearningSeconds(metrics.duration_seconds)),
        element("td", "checkpoint-power-inadmissible-cell", formatLearningEnergy(metrics.idle_subtracted_energy_j)),
        element("td", "checkpoint-power-inadmissible-cell", formatScientific(metrics.idle_subtracted_energy_j_per_canonical_token)),
        element("td", "", finiteNumber(metrics.pooled_effective_update_equivalents) ? metrics.pooled_effective_update_equivalents.toLocaleString("en-US", { maximumFractionDigits: 3 }) : "not reported"),
      );
      dom.checkpointpowerphasemetrics.append(row);
    });
  }

  function renderCheckpointPowerProvenance() {
    const trace = checkpointPowerArtifact.full_trace;
    const provenance = {
      schema: checkpointPowerArtifact.schema,
      artifact_sha256: checkpointPowerArtifact.artifact_sha256,
      source_result: checkpointPowerArtifact.source_result,
      scenario_sha256: trace.scenario_sha256,
      engine: trace.engine,
      source_bindings: trace.source_bindings,
      warm_start: trace.warm_start,
      runtime: trace.runtime,
      raw_trace_artifact: trace.raw_trace_artifact,
      facility_bridge: checkpointPowerArtifact.facility_bridge,
      evidence_boundary: checkpointPowerArtifact.evidence_boundary,
    };
    dom.checkpointpowerprovenancejson.textContent = JSON.stringify(provenance, null, 2);
    dom.checkpointpowerdepthtrace.textContent = `${trace.run_ledger.length} run records · ${trace.raw_trace_artifact.point_count.toLocaleString("en-US")} raw points available on demand · compact artifact ${checkpointPowerArtifact.artifact_sha256} · raw artifact ${trace.raw_trace_artifact.artifact_sha256}.`;
  }

  function checkpointPowerPhaseAtTimestamp(timestamp, windows) {
    const match = windows.find((window) => timestamp >= window.start_seconds && timestamp <= window.end_seconds);
    return match ? match.phase : "outside labeled phase";
  }

  function renderCheckpointPowerRawTrace() {
    if (!checkpointPowerRawArtifact) return;
    const selected = checkpointPowerSelectedRun();
    const rawRun = selected && checkpointPowerRawArtifact.runs.find((run) => run.run_id === selected.run_id);
    dom.checkpointpowerrawpoints.replaceChildren();
    if (!rawRun) {
      dom.checkpointpowerrawstate.textContent = "The selected run is absent from the bound raw artifact.";
      dom.checkpointpowerrawmeta.textContent = "";
      return;
    }
    const trace = rawRun.telemetry_trace;
    dom.checkpointpowerrawstate.textContent = `Raw point artifact loaded · ${checkpointPowerRawArtifact.artifact_sha256} · ${checkpointPowerRawArtifact.boundary}`;
    dom.checkpointpowerrawmeta.textContent = `${rawRun.run_id} · ${trace.points.length.toLocaleString("en-US")} points · poll ${finiteNumber(trace.poll_seconds) ? `${(trace.poll_seconds * 1000).toLocaleString("en-US", { maximumFractionDigits: 3 })} ms` : "not reported"} · run trace ${rawRun.raw_trace_sha256}.`;
    const windows = Array.isArray(trace.phase_windows) ? trace.phase_windows : rawRun.phase_intervals;
    trace.points.forEach((point, index) => {
      const power = finiteNumber(point.gpu_board_power_w) ? point.gpu_board_power_w : point.power_w;
      const row = element("tr");
      row.append(
        element("td", "", String(index + 1)),
        element("td", "", `${finiteNumber(point.timestamp) ? point.timestamp.toFixed(6) : "not reported"} s · ${finiteNumber(point.monotonic_ns) ? point.monotonic_ns.toLocaleString("en-US") : "?"} ns`),
        element("td", "", checkpointPowerPhaseAtTimestamp(point.timestamp, windows)),
        element("td", "", finiteNumber(power) ? `${power.toLocaleString("en-US", { maximumFractionDigits: 3 })} W` : "not reported"),
        element("td", "", finiteNumber(point.gpu_utilization_percent) ? `${point.gpu_utilization_percent}%` : "not reported"),
        element("td", "", finiteNumber(point.memory_utilization_percent) ? `${point.memory_utilization_percent}%` : "not reported"),
        element("td", "", `${finiteNumber(point.sm_clock_mhz) ? point.sm_clock_mhz.toLocaleString("en-US") : "?"} / ${finiteNumber(point.memory_clock_mhz) ? point.memory_clock_mhz.toLocaleString("en-US") : "?"} MHz`),
        element("td", "", finiteNumber(point.temperature_c) ? `${point.temperature_c} °C` : "not reported"),
        element("td", "", String(point.performance_state ?? point.pstate ?? "not reported")),
      );
      dom.checkpointpowerrawpoints.append(row);
    });
  }

  function renderCheckpointPowerTrace() {
    renderCheckpointPowerRunSelector();
    renderCheckpointPowerLedger();
    renderCheckpointPowerPhaseMetrics();
    renderCheckpointPowerProvenance();
    if (checkpointPowerRawArtifact) renderCheckpointPowerRawTrace();
  }

  function renderCheckpointPowerV1() {
    if (!dom.checkpointpowerv1) return;
    if (!checkpointPowerArtifact) {
      dom.checkpointpowerv1.hidden = true;
      return;
    }
    dom.checkpointpowerv1.hidden = false;
    const freshman = checkpointPowerArtifact.freshman;
    dom.checkpointpowerv1state.textContent = `measurement invalid · 32/32 runs · artifact ${checkpointPowerArtifact.artifact_sha256.slice(0, 12)}`;
    dom.checkpointpowerinsighttitle.textContent = freshman.headline;
    dom.checkpointpowerplainanswer.textContent = freshman.plain_answer;
    setPlainWords("checkpoint-power-plain-words", "measurement_invalid");
    dom.checkpointpowerdecision.textContent = freshman.decision;
    const boundary = checkpointPowerArtifact.facility_bridge.plain_boundary;
    const unmeasured = checkpointPowerArtifact.evidence_boundary.unmeasured.join(", ");
    dom.checkpointpowerevidenceboundary.textContent = `${boundary} Unmeasured: ${unmeasured}.`;
    renderCheckpointPowerFreshman();
    renderCheckpointPowerValidity();
    renderCheckpointPowerArms();
    renderCheckpointPowerControls();
    renderCheckpointPowerContrasts();
    renderCheckpointPowerRedirect();
    renderCheckpointPowerTrace();
  }

  function renderCheckpointEnergyFreshman() {
    dom.checkpointenergyfreshmangrid.replaceChildren();
    checkpointEnergyArtifact.freshman.cards.forEach((entry) => {
      const card = element("article", "checkpoint-energy-plain-card");
      card.dataset.state = entry.state;
      card.append(
        element("p", "checkpoint-energy-plain-label", entry.label),
        element("strong", "checkpoint-energy-plain-value", entry.value),
        element("p", "checkpoint-energy-plain-detail", entry.detail),
      );
      dom.checkpointenergyfreshmangrid.append(card);
    });
  }

  function renderCheckpointEnergyValidity() {
    dom.checkpointenergyvaliditygrid.replaceChildren();
    const researcher = checkpointEnergyArtifact.researcher;
    const counter = researcher.counter_calibration;
    const evaluationRuns = checkpointEnergyArtifact.full_trace.run_ledger.filter((run) => run.split === "evaluation");
    const updateCounts = evaluationRuns.map((run) => run.effective_counter_update_count).filter(finiteNumber);
    const cards = [
      ["Measurement", "VALID", `${researcher.active_invalidators.length} active invalidators`],
      ["Effective counter period", `${counter.effective_update_period_ms.toLocaleString("en-US", { maximumFractionDigits: 2 })} ms`, `${counter.api} · supported`],
      ["Evaluation support", `${Math.min(...updateCounts)}–${Math.max(...updateCounts)} updates`, `${evaluationRuns.length} evaluation arm runs`],
      ["Calibration trace", `${counter.effective_update_count.toLocaleString("en-US")} updates`, `${counter.poll_count.toLocaleString("en-US")} polls · requested ${counter.requested_poll_interval_ms.toLocaleString("en-US")} ms`],
    ];
    cards.forEach(([label, value, detail], index) => {
      const card = element("article", "checkpoint-energy-validity-card");
      card.dataset.primary = String(index === 0);
      card.append(element("p", "", label), element("strong", "", value), element("small", "", detail));
      dom.checkpointenergyvaliditygrid.append(card);
    });
  }

  function checkpointEnergyEffectCard(title, effect, plainMeaning, status = "SUPPORTED") {
    const card = element("article", "checkpoint-energy-effect-card");
    card.dataset.status = status.toLowerCase().replaceAll(" ", "-");
    card.append(
      element("span", "checkpoint-energy-effect-status", status),
      element("h4", "", title),
      element("strong", "checkpoint-energy-effect-value", `${formatScientific(effect.median)} J / canonical token`),
      element("p", "checkpoint-energy-effect-interval", `90% interval ${formatScientific(effect.lower_bound)} to ${formatScientific(effect.upper_bound)}`),
      element("p", "checkpoint-energy-effect-meaning", plainMeaning),
    );
    return card;
  }

  function renderCheckpointEnergyEffects() {
    dom.checkpointenergyeffectgrid.replaceChildren();
    const researcher = checkpointEnergyArtifact.researcher;
    dom.checkpointenergyeffectgrid.append(
      checkpointEnergyEffectCard(
        "Total cadence × continuation interaction",
        researcher.primary_total_interaction,
        "The full interaction stayed positive: dense checkpoint cadence increased the continuation energy cost.",
      ),
      checkpointEnergyEffectCard(
        "Checkpoint-related phase group",
        researcher.checkpoint_related_group_interaction,
        "The preregistered checkpoint group also stayed positive, locating part of the mechanism in checkpoint cadence.",
      ),
      checkpointEnergyEffectCard(
        "Idle-subtracted interaction sensitivity",
        researcher.idle_subtracted_interaction_sensitivity,
        "This sensitivity interval crosses zero. It was not the frozen decision metric, but it shows that the attribution is not robust to estimated idle-baseline subtraction.",
        "SENSITIVITY · INCONCLUSIVE",
      ),
    );
  }

  function renderCheckpointEnergyPhaseSupport() {
    const support = checkpointEnergyArtifact.researcher.phase_support;
    dom.checkpointenergysupportgrid.replaceChildren();
    [
      ["Sparse snapshot pool", support.pooled_checkpoint_snapshot_updates_by_cadence.sparse, "checkpoint snapshots"],
      ["Dense snapshot pool", support.pooled_checkpoint_snapshot_updates_by_cadence.dense, "checkpoint snapshots"],
      ["Sparse checkpoint group", support.pooled_checkpoint_related_updates_by_cadence.sparse, "preregistered group"],
      ["Dense checkpoint group", support.pooled_checkpoint_related_updates_by_cadence.dense, "preregistered group"],
    ].forEach(([label, value, detail]) => {
      const card = element("article", "checkpoint-energy-support-card");
      card.append(
        element("p", "", label),
        element("strong", "", `${Math.round(value).toLocaleString("en-US")} updates`),
        element("small", "", `${detail} · supported`),
      );
      dom.checkpointenergysupportgrid.append(card);
    });

    dom.checkpointenergyexploratory.replaceChildren();
    const header = element("header");
    header.append(
      element("span", "checkpoint-energy-exploratory-badge", "EXPLORATORY ONLY"),
      element("p", "", `${checkpointEnergyArtifact.researcher.rare_phase_boundary}. The frozen individual-phase minimum is 30 effective updates.`),
    );
    const grid = element("div", "checkpoint-energy-exploratory-grid");
    ["sparse", "dense"].forEach((cadence) => {
      const column = element("section");
      column.append(element("h4", "", `${checkpointPowerHumanLabel(cadence)} cadence`));
      const list = element("ul");
      Object.entries(support.individual_phase_support_by_cadence[cadence])
        .filter(([, phase]) => String(phase.evidence_class).startsWith("exploratory"))
        .forEach(([phaseId, phase]) => {
          const item = element("li");
          item.append(
            element("span", "", phaseId),
            element("strong", "", `${phase.effective_update_equivalents.toLocaleString("en-US", { maximumFractionDigits: 2 })} / ${phase.minimum_required.toLocaleString("en-US")} updates`),
          );
          list.append(item);
        });
      column.append(list);
      grid.append(column);
    });
    dom.checkpointenergyexploratory.append(header, grid);
  }

  function renderCheckpointEnergyGateStrip(container, gates) {
    container.replaceChildren();
    Object.entries(gates).forEach(([gateId, passed]) => {
      const gate = element("div", "checkpoint-energy-gate");
      gate.dataset.passed = String(passed === true);
      gate.append(
        element("span", "checkpoint-energy-gate-state", passed === true ? "PASS" : "FAIL"),
        element("span", "checkpoint-energy-gate-label", checkpointPowerHumanLabel(gateId)),
      );
      container.append(gate);
    });
  }

  function renderCheckpointEnergyGates() {
    renderCheckpointEnergyGateStrip(dom.checkpointenergymechanismgates, checkpointEnergyArtifact.researcher.mechanism_gates);
    renderCheckpointEnergyGateStrip(dom.checkpointenergysalvagegates, checkpointEnergyArtifact.researcher.salvage_gates);
  }

  function checkpointEnergySelectedRun() {
    if (!checkpointEnergyArtifact) return null;
    const runId = dom.checkpointenergyrunselect.value;
    return checkpointEnergyArtifact.full_trace.run_ledger.find((run) => run.run_id === runId) || checkpointEnergyArtifact.full_trace.run_ledger[0] || null;
  }

  function renderCheckpointEnergyRunSelector() {
    const previous = dom.checkpointenergyrunselect.value;
    dom.checkpointenergyrunselect.replaceChildren();
    checkpointEnergyArtifact.full_trace.run_ledger.forEach((run) => {
      const option = element("option", "", `${run.block_id} · ${run.arm_code} · ${run.run_id}`);
      option.value = run.run_id;
      dom.checkpointenergyrunselect.append(option);
    });
    if (checkpointEnergyArtifact.full_trace.run_ledger.some((run) => run.run_id === previous)) dom.checkpointenergyrunselect.value = previous;
  }

  function renderCheckpointEnergyLedger() {
    dom.checkpointenergyrunledger.replaceChildren();
    checkpointEnergyArtifact.full_trace.run_ledger.forEach((run) => {
      const row = element("tr");
      row.append(
        element("td", "", run.run_id),
        element("td", "", `${run.split} · ${run.block_id} · ${run.execution_order_id}/${run.execution_position}`),
        element("td", "", `${run.arm_code} · ${run.checkpoint_cadence} · ${run.continuation}`),
        element("td", "", `${formatLearningTokens(run.attempted_tokens)} / ${formatLearningTokens(run.canonical_tokens)}`),
        element("td", "", formatLearningNll(run.final_held_out_nll)),
        element("td", "", `${run.raw_poll_count.toLocaleString("en-US")} / ${run.effective_counter_update_count.toLocaleString("en-US")}`),
        element("td", "", formatLearningEnergy(run.raw_run_energy_j)),
        element("td", "", `${run.checkpoint_count.toLocaleString("en-US")} · ${formatBytes(run.checkpoint_bytes)}`),
        element("td", "checkpoint-energy-hash", run.raw_counter_trace_sha256),
      );
      dom.checkpointenergyrunledger.append(row);
    });
  }

  function renderCheckpointEnergyPhaseMetrics() {
    dom.checkpointenergyphasemetrics.replaceChildren();
    dom.checkpointenergycountersummary.replaceChildren();
    const run = checkpointEnergySelectedRun();
    if (!run || !run.phase_metrics || typeof run.phase_metrics !== "object") return;
    const counterDeltaJ = (run.counter_end_mj - run.counter_start_mj) / 1000;
    [
      ["Counter start", `${run.counter_start_mj.toLocaleString("en-US")} mJ`],
      ["Counter end", `${run.counter_end_mj.toLocaleString("en-US")} mJ`],
      ["Observed delta", formatLearningEnergy(counterDeltaJ)],
      ["Polls / effective updates", `${run.raw_poll_count.toLocaleString("en-US")} / ${run.effective_counter_update_count.toLocaleString("en-US")}`],
    ].forEach(([label, value]) => {
      const metric = element("div");
      metric.append(element("span", "", label), element("strong", "", value));
      dom.checkpointenergycountersummary.append(metric);
    });
    Object.entries(run.phase_metrics).forEach(([phase, metrics]) => {
      const evidenceClass = run.individual_phase_evidence_class && run.individual_phase_evidence_class[phase];
      const row = element("tr");
      row.dataset.evidenceClass = String(evidenceClass || "not_reported");
      row.append(
        element("td", "", phase),
        element("td", "", checkpointPowerHumanLabel(evidenceClass)),
        element("td", "", formatLearningSeconds(metrics.duration_seconds)),
        element("td", "", formatLearningEnergy(metrics.energy_j)),
        element("td", "", formatScientific(metrics.energy_j_per_canonical_token)),
        element("td", "", finiteNumber(metrics.counter_update_count) ? metrics.counter_update_count.toLocaleString("en-US") : "not reported"),
        element("td", "", finiteNumber(metrics.pooled_effective_update_equivalents) ? metrics.pooled_effective_update_equivalents.toLocaleString("en-US", { maximumFractionDigits: 3 }) : "not reported"),
      );
      dom.checkpointenergyphasemetrics.append(row);
    });
  }

  function renderCheckpointEnergyProvenance() {
    const trace = checkpointEnergyArtifact.full_trace;
    const provenance = {
      schema: checkpointEnergyArtifact.schema,
      artifact_sha256: checkpointEnergyArtifact.artifact_sha256,
      source_result: checkpointEnergyArtifact.source_result,
      scenario_sha256: trace.scenario_sha256,
      engine: trace.engine,
      source_bindings: trace.source_bindings,
      pw1_failure_binding_verified: trace.pw1_failure_binding_verified,
      warm_start: trace.warm_start,
      runtime: trace.runtime,
      raw_trace_artifact: trace.raw_trace_artifact,
      counter_calibration: checkpointEnergyArtifact.researcher.counter_calibration,
      facility_bridge: checkpointEnergyArtifact.facility_bridge,
      evidence_boundary: checkpointEnergyArtifact.evidence_boundary,
    };
    dom.checkpointenergyprovenancejson.textContent = JSON.stringify(provenance, null, 2);
    dom.checkpointenergydepthtrace.textContent = `${trace.run_ledger.length} run records · ${trace.raw_trace_artifact.poll_count.toLocaleString("en-US")} raw polls and ${trace.raw_trace_artifact.effective_update_count.toLocaleString("en-US")} effective counter updates available on demand · compact artifact ${checkpointEnergyArtifact.artifact_sha256} · raw artifact ${trace.raw_trace_artifact.artifact_sha256}.`;
  }

  function renderCheckpointEnergyRawTrace() {
    if (!checkpointEnergyRawArtifact) return;
    const selected = checkpointEnergySelectedRun();
    const rawRun = selected && checkpointEnergyRawArtifact.runs.find((run) => run.run_id === selected.run_id);
    dom.checkpointenergyrawpoints.replaceChildren();
    if (!rawRun) {
      dom.checkpointenergyrawstate.textContent = "The selected run is absent from the bound raw counter artifact.";
      dom.checkpointenergyrawmeta.textContent = "";
      return;
    }
    const trace = rawRun.telemetry_trace;
    dom.checkpointenergyrawstate.textContent = `Raw cumulative-counter artifact loaded · ${checkpointEnergyRawArtifact.artifact_sha256} · ${checkpointEnergyRawArtifact.boundary}`;
    dom.checkpointenergyrawmeta.textContent = `${rawRun.run_id} · ${trace.points.length.toLocaleString("en-US")} polls · counter trace ${rawRun.raw_counter_trace_sha256}.`;
    const windows = Array.isArray(trace.phase_windows) ? trace.phase_windows : rawRun.phase_intervals;
    trace.points.forEach((point, index) => {
      const cumulative = finiteNumber(point.cumulative_gpu_board_energy_mj) ? point.cumulative_gpu_board_energy_mj : point.total_energy_mj;
      const power = finiteNumber(point.instantaneous_gpu_board_power_w_ancillary) ? point.instantaneous_gpu_board_power_w_ancillary : point.gpu_board_power_w;
      const row = element("tr");
      row.dataset.counterUpdate = String(point.effective_counter_update === true);
      row.append(
        element("td", "", String(index + 1)),
        element("td", "", `${finiteNumber(point.timestamp) ? point.timestamp.toFixed(6) : "not reported"} s · ${finiteNumber(point.monotonic_ns) ? point.monotonic_ns.toLocaleString("en-US") : "?"} ns`),
        element("td", "", checkpointPowerPhaseAtTimestamp(point.timestamp, windows)),
        element("td", "", finiteNumber(cumulative) ? `${cumulative.toLocaleString("en-US")} mJ` : "not reported"),
        element("td", "", point.effective_counter_update === true ? "YES" : "no"),
        element("td", "", finiteNumber(power) ? `${power.toLocaleString("en-US", { maximumFractionDigits: 3 })} W` : "not reported"),
        element("td", "", finiteNumber(point.gpu_utilization_percent) ? `${point.gpu_utilization_percent}%` : "not reported"),
        element("td", "", finiteNumber(point.temperature_c) ? `${point.temperature_c} °C` : "not reported"),
      );
      dom.checkpointenergyrawpoints.append(row);
    });
  }

  function renderCheckpointEnergyTrace() {
    renderCheckpointEnergyRunSelector();
    renderCheckpointEnergyLedger();
    renderCheckpointEnergyPhaseMetrics();
    renderCheckpointEnergyProvenance();
    if (checkpointEnergyRawArtifact) renderCheckpointEnergyRawTrace();
  }

  function renderCheckpointEnergyV2() {
    if (!dom.checkpointenergyv2) return;
    if (!checkpointEnergyArtifact) {
      dom.checkpointenergyv2.hidden = true;
      return;
    }
    dom.checkpointenergyv2.hidden = false;
    const freshman = checkpointEnergyArtifact.freshman;
    dom.checkpointenergyv2state.textContent = `measurement valid · 11/11 gates pass · artifact ${checkpointEnergyArtifact.artifact_sha256.slice(0, 12)}`;
    dom.checkpointenergyinsighttitle.textContent = freshman.headline;
    dom.checkpointenergyplainanswer.textContent = freshman.plain_answer;
    setPlainWords("checkpoint-energy-plain-words", checkpointEnergyArtifact.researcher.conclusion);
    dom.checkpointenergymechanism.textContent = freshman.mechanism;
    const gpu = checkpointEnergyArtifact.full_trace.runtime.hardware.gpu;
    dom.checkpointenergyevidenceboundary.textContent = `${freshman.boundary} Observed boundary: ${gpu}, cumulative GPU-board energy, and the frozen TinyStories learning setup. Facility claim allowed: no.`;
    const next = checkpointEnergyArtifact.next_experiment;
    dom.checkpointenergynextquestion.textContent = `${next.id}: ${next.question} Required scale: ${next.required_scale}. Do not claim yet: ${next.do_not_claim_yet.join(", ")}.`;
    renderCheckpointEnergyFreshman();
    renderCheckpointEnergyValidity();
    renderCheckpointEnergyEffects();
    renderCheckpointEnergyPhaseSupport();
    renderCheckpointEnergyGates();
    renderCheckpointEnergyTrace();
  }

  function semanticHumanLabel(value) {
    return String(value || "not reported")
      .replaceAll("_", " ")
      .replaceAll("-", " ")
      .replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  function semanticPolicyLabel(policyId) {
    const labels = {
      synchronous_restart: "Synchronous restart",
      exact_forward_recovery: "Exact forward recovery",
      delayed_one_step: "One-step delayed",
      periodic_local: "Periodic local",
      observable_adaptive: "Observable adaptive",
      future_trace_oracle: "Hindsight policy envelope",
    };
    return labels[policyId] || semanticHumanLabel(policyId);
  }

  function semanticFamilyResults() {
    return semanticConsistencyArtifact && semanticConsistencyArtifact.researcher && Array.isArray(semanticConsistencyArtifact.researcher.family_results)
      ? semanticConsistencyArtifact.researcher.family_results
      : [];
  }

  function semanticSelectedFamily() {
    const families = semanticFamilyResults();
    if (!families.length) return null;
    const selected = families.find((family) => family.family_id === state.semanticFamily);
    return selected || families.find((family) => family.family_id === semanticConsistencyArtifact.full_trace.narrative_family_id) || families[0];
  }

  function renderSemanticConsistencyFreshman() {
    dom.semanticconsistencyfreshmangrid.replaceChildren();
    semanticConsistencyArtifact.freshman.cards.forEach((entry) => {
      const card = element("article", "checkpoint-energy-plain-card");
      card.dataset.state = entry.state || "unresolved";
      card.append(
        element("p", "checkpoint-energy-plain-label", entry.label),
        element("strong", "checkpoint-energy-plain-value", entry.value),
        element("p", "checkpoint-energy-plain-detail", entry.detail),
        evidenceTag(entry.evidence_class || "unmeasured"),
      );
      dom.semanticconsistencyfreshmangrid.append(card);
    });
  }

  function renderSemanticConsistencyEffects() {
    dom.semanticconsistencyeffectgrid.replaceChildren();
    semanticConsistencyArtifact.researcher.paired_effects.forEach((effect) => {
      const passed = effect.passed;
      const stateLabel = passed === true ? "PASS" : passed === false ? "FAIL" : "UNRESOLVED";
      const card = element("article", "equal-work-effect-card");
      card.dataset.passed = passed === null || passed === undefined ? "unresolved" : String(passed);
      card.dataset.effectId = effect.effect_id || "";
      const header = element("header");
      header.append(element("h4", "", effect.label), element("span", "equal-work-effect-status", stateLabel));
      card.append(
        header,
        element("strong", "equal-work-effect-value", effect.display_value),
        element("p", "equal-work-effect-interval", effect.interval_display),
        element("p", "equal-work-effect-bound", effect.boundary),
        element("p", "equal-work-effect-bound", effect.meaning),
        evidenceTag(effect.evidence_class || "unmeasured"),
      );
      dom.semanticconsistencyeffectgrid.append(card);
    });
  }

  function semanticRankingStateLabel(stateValue) {
    const labels = {
      adaptive_wins: "ADAPTIVE",
      adaptive_invariant: "ADAPTIVE",
      fixed_wins: "FIXED",
      fixed_invariant: "FIXED",
      rank_reverses: "REVERSAL",
      uncertain: "REVERSAL",
      abstain: "ABSTAIN",
      unsupported: "ABSTAIN",
      unmeasured: "UNMEASURED",
    };
    return labels[stateValue] || semanticHumanLabel(stateValue).toUpperCase();
  }

  function renderSemanticConsistencyRanking() {
    if (!dom.semanticconsistencyrankingsvg) return;
    const svg = dom.semanticconsistencyrankingsvg;
    const body = dom.semanticconsistencyrankingfallback;
    svg.replaceChildren();
    body.replaceChildren();
    if (!semanticConsistencyArtifact) return;

    const map = semanticConsistencyArtifact.researcher.ranking_map;
    const families = map.families;
    const domain = map.domain || {};
    const lower = finiteNumber(domain.lower) ? domain.lower : 0;
    const upper = finiteNumber(domain.upper) && domain.upper > lower ? domain.upper : lower + 1;
    const width = 1000;
    const left = 210;
    const right = 980;
    const top = 58;
    const rowHeight = 58;
    const height = top + families.length * rowHeight + 42;
    const x = (value) => left + (value - lower) / (upper - lower) * (right - left);
    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    svg.setAttribute("height", String(height));

    const title = svgElement("title");
    title.textContent = "Policy ranking across infrastructure uncertainty";
    const description = svgElement("desc");
    description.textContent = "Directly labeled regions show where adaptive or fixed policies win, where their ranking reverses, and where the controller abstains for each held-out family.";
    svg.append(title, description);

    for (let tickIndex = 0; tickIndex <= 4; tickIndex += 1) {
      const fraction = tickIndex / 4;
      const value = lower + fraction * (upper - lower);
      const tickX = left + fraction * (right - left);
      svg.append(svgElement("line", { x1: tickX, x2: tickX, y1: top - 18, y2: height - 28, class: "semantic-ranking-gridline" }));
      const label = svgElement("text", { x: tickX, y: top - 26, "text-anchor": tickIndex === 0 ? "start" : tickIndex === 4 ? "end" : "middle", class: "semantic-ranking-tick" });
      label.textContent = finiteNumber(value) ? value.toLocaleString("en-US", { maximumFractionDigits: 3 }) : "?";
      svg.append(label);
    }
    const axisLabel = svgElement("text", { x: (left + right) / 2, y: 18, "text-anchor": "middle", class: "semantic-ranking-family" });
    axisLabel.textContent = String(domain.label || "Infrastructure realization multiplier").toUpperCase();
    svg.append(axisLabel);

    families.forEach((family, familyIndex) => {
      const y = top + familyIndex * rowHeight;
      const familyLabel = svgElement("text", { x: 10, y: y + 24, class: "semantic-ranking-family" });
      familyLabel.textContent = family.family_id;
      svg.append(familyLabel);
      const regions = Array.isArray(family.regions) ? family.regions : [];
      regions.forEach((region) => {
        const start = finiteNumber(region.lower) ? Math.max(lower, region.lower) : lower;
        const end = finiteNumber(region.upper) ? Math.min(upper, region.upper) : upper;
        const startX = x(start);
        const endX = Math.max(startX + 2, x(end));
        const stateValue = String(region.state || "unmeasured");
        const rect = svgElement("rect", { x: startX, y, width: endX - startX, height: 34, rx: 3, class: "semantic-ranking-segment", "data-state": stateValue });
        const rectTitle = svgElement("title");
        rectTitle.textContent = `${family.family_id} · ${region.region_label || `${start}–${end}`}: ${semanticRankingStateLabel(stateValue)}. ${region.reason || "No reason reported."}`;
        rect.append(rectTitle);
        const label = svgElement("text", { x: (startX + endX) / 2, y: y + 22, "text-anchor": "middle", class: "semantic-ranking-label" });
        label.textContent = semanticRankingStateLabel(stateValue);
        svg.append(rect, label);

        const row = element("tr");
        row.append(
          element("td", "", family.family_id),
          element("td", "", region.region_label || `${start.toLocaleString("en-US", { maximumFractionDigits: 3 })}–${end.toLocaleString("en-US", { maximumFractionDigits: 3 })} ${domain.unit || ""}`.trim()),
          element("td", "", semanticRankingStateLabel(stateValue)),
          element("td", "", semanticPolicyLabel(region.comparator_policy_id || semanticConsistencyArtifact.comparison.selected_fixed_policy_id)),
          element("td", "", region.reason || "No reason reported."),
        );
        body.append(row);
      });
    });
  }

  function semanticTimelineRuns(family) {
    return family && Array.isArray(family.timeline_runs) ? family.timeline_runs : [];
  }

  function renderSemanticConsistencyTimelineFallback(runs) {
    dom.semanticconsistencytimelinefallback.replaceChildren();
    runs.forEach((run) => {
      dom.semanticconsistencytimelinefallback.append(element("h4", "", `${semanticPolicyLabel(run.policy_id)} · ${semanticHumanLabel(run.policy_role)}`));
      const table = element("table", "recovery-timeline-table");
      const head = element("thead");
      const headRow = element("tr");
      ["Start", "End", "Mode", "Visible reason", "Evidence"].forEach((label) => headRow.append(element("th", "", label)));
      head.append(headRow);
      const tableBody = element("tbody");
      (run.mode_intervals || []).forEach((interval) => {
        const row = element("tr");
        row.append(
          element("td", "", String(interval.start_tick)),
          element("td", "", String(interval.end_tick)),
          element("td", "", semanticPolicyLabel(interval.mode)),
          element("td", "", interval.reason || "No visible-state reason reported."),
          element("td", "", EVIDENCE_LABELS[normalizedEvidence(interval.evidence_class)]),
        );
        tableBody.append(row);
      });
      table.append(head, tableBody);
      dom.semanticconsistencytimelinefallback.append(table);
    });
  }

  function renderSemanticConsistencyTimeline() {
    if (!dom.semanticconsistencytimelinesvg) return;
    const svg = dom.semanticconsistencytimelinesvg;
    svg.replaceChildren();
    if (!semanticConsistencyArtifact) return;
    const family = semanticSelectedFamily();
    const runs = semanticTimelineRuns(family);
    const title = svgElement("title");
    title.textContent = family ? `${family.family_id} controller timeline` : "Controller timeline unavailable";
    const description = svgElement("desc");
    svg.append(title, description);
    if (!family || !runs.length) {
      svg.setAttribute("viewBox", "0 0 1000 160");
      description.textContent = "No compact controller timeline is attached for the selected family.";
      const empty = svgElement("text", { x: 500, y: 82, "text-anchor": "middle", class: "recovery-policy-label" });
      empty.textContent = "CONTROLLER TIMELINE UNAVAILABLE";
      svg.append(empty);
      renderSemanticConsistencyTimelineFallback([]);
      return;
    }

    const allIntervals = runs.flatMap((run) => run.mode_intervals || []);
    const maxTick = Math.max(1, ...allIntervals.map((interval) => Number(interval.end_tick) || 0), ...runs.flatMap((run) => (run.events || []).map((event) => Number(event.tick) || 0)));
    const left = 220;
    const right = 975;
    const axisY = 34;
    const rowHeight = 74;
    const height = 60 + runs.length * rowHeight;
    const scaleX = (tick) => left + Math.max(0, Math.min(maxTick, Number(tick) || 0)) / maxTick * (right - left);
    svg.setAttribute("viewBox", `0 0 1000 ${height}`);
    svg.setAttribute("height", String(height));
    description.textContent = "Adaptive, fixed-comparator, and hindsight whole-policy-envelope rows share one wall-tick axis. Colored intervals are selected consistency modes; diamonds mark abstention, membership, merge, and rejoin events.";
    for (let tickIndex = 0; tickIndex <= 4; tickIndex += 1) {
      const tick = Math.round(maxTick * tickIndex / 4);
      const tickX = scaleX(tick);
      svg.append(svgElement("line", { x1: tickX, x2: tickX, y1: axisY, y2: height - 14, class: "recovery-gridline" }));
      const tickLabel = svgElement("text", { x: tickX, y: axisY - 9, "text-anchor": tickIndex === 0 ? "start" : tickIndex === 4 ? "end" : "middle", class: "recovery-tick" });
      tickLabel.textContent = `tick ${tick}`;
      svg.append(tickLabel);
    }
    runs.forEach((run, runIndex) => {
      const y = 54 + runIndex * rowHeight;
      const policy = svgElement("text", { x: 10, y: y + 15, class: "recovery-policy-label" });
      policy.textContent = semanticPolicyLabel(run.policy_id);
      const role = svgElement("text", { x: 10, y: y + 33, class: "recovery-event-id" });
      role.textContent = semanticHumanLabel(run.policy_role).toUpperCase();
      svg.append(policy, role, svgElement("line", { x1: left, x2: right, y1: y + 26, y2: y + 26, class: "recovery-track" }));
      (run.mode_intervals || []).forEach((interval) => {
        const startX = scaleX(interval.start_tick);
        const endX = Math.max(startX + 3, scaleX(interval.end_tick));
        const mode = String(interval.mode || "unmeasured");
        const rect = svgElement("rect", { x: startX, y: y + 9, width: endX - startX, height: 34, rx: 3, class: "semantic-mode-interval", "data-mode": mode });
        const rectTitle = svgElement("title");
        rectTitle.textContent = `${semanticPolicyLabel(mode)}: ticks ${interval.start_tick}–${interval.end_tick}. ${interval.reason || "No reason reported."}`;
        rect.append(rectTitle);
        svg.append(rect);
        if (endX - startX > 62) {
          const label = svgElement("text", { x: (startX + endX) / 2, y: y + 30, "text-anchor": "middle", class: "semantic-mode-label" });
          label.textContent = semanticPolicyLabel(mode).toUpperCase();
          svg.append(label);
        }
      });
      (run.events || []).forEach((event, eventIndex) => {
        const eventX = scaleX(event.tick);
        const eventY = y + 47 + eventIndex % 2 * 13;
        const mark = svgElement("rect", { x: eventX - 4, y: eventY - 4, width: 8, height: 8, transform: `rotate(45 ${eventX} ${eventY})`, class: "recovery-event", "data-role": event.event_kind || "failure" });
        const markTitle = svgElement("title");
        markTitle.textContent = `${semanticHumanLabel(event.event_kind)} at tick ${event.tick}: ${event.reason || "No reason reported."}`;
        mark.append(markTitle);
        svg.append(mark);
      });
    });
    renderSemanticConsistencyTimelineFallback(runs);
  }

  function renderSemanticConsistencyFamilySelector() {
    const families = semanticFamilyResults();
    const selected = semanticSelectedFamily();
    dom.semanticconsistencyfamilyselect.replaceChildren();
    families.forEach((family) => {
      const option = element("option", "", `${family.family_id} · ${semanticRankingStateLabel(family.ranking_state)}`);
      option.value = family.family_id;
      dom.semanticconsistencyfamilyselect.append(option);
    });
    if (selected) {
      dom.semanticconsistencyfamilyselect.value = selected.family_id;
      if (state.semanticFamily !== selected.family_id) {
        state = sanitizeState({ ...state, semanticFamily: selected.family_id });
        writeStateToURL(true);
      }
    }
  }

  function renderSemanticConsistencyFamilyTable() {
    dom.semanticconsistencyfamilybody.replaceChildren();
    semanticFamilyResults().forEach((family) => {
      const row = element("tr");
      row.dataset.familyId = family.family_id || "";
      const stateCell = element("td", "", `${semanticRankingStateLabel(family.ranking_state)}${family.abstention_reason ? ` · ${family.abstention_reason}` : ""}`);
      stateCell.dataset.state = family.ranking_state || "unmeasured";
      row.append(
        element("td", "", family.family_id),
        element("td", "", family.learning_delta_display),
        element("td", "", family.completion_ratio_display),
        element("td", "", family.wan_ratio_display),
        element("td", "", family.replayed_work_display),
        element("td", "", family.energy_display),
        stateCell,
      );
      dom.semanticconsistencyfamilybody.append(row);
    });
  }

  function renderSemanticLedger(container, values) {
    container.replaceChildren();
    if (!Array.isArray(values) || !values.length) {
      container.append(element("p", "", "No entries reported."));
      return;
    }
    const list = element("ul");
    values.forEach((value) => {
      const item = element("li");
      if (value && typeof value === "object") {
        const lead = value.label || value.assumption_id || value.evidence_id || value.id || value.statement || value.claim || "Entry";
        const detail = value.detail || value.boundary || value.reason || value.statement || value.claim || value.status || "";
        item.append(element("strong", "", lead));
        if (detail && detail !== lead) item.append(document.createTextNode(`: ${detail}`));
        if (value.evidence_class) item.append(document.createTextNode(" "), evidenceTag(value.evidence_class));
      } else {
        item.textContent = String(value);
      }
      list.append(item);
    });
    container.append(list);
  }

  function renderSemanticUncertainty() {
    dom.semanticconsistencyuncertainty.replaceChildren();
    const uncertainty = semanticConsistencyArtifact.full_trace.uncertainty;
    const list = element("dl");
    Object.entries(uncertainty || {}).forEach(([key, value]) => {
      list.append(
        element("dt", "", semanticHumanLabel(key)),
        element("dd", "", typeof value === "string" ? value : JSON.stringify(value)),
      );
    });
    if (!list.children.length) list.append(element("dt", "", "Uncertainty"), element("dd", "", "Not reported."));
    dom.semanticconsistencyuncertainty.append(list);
  }

  function semanticSelectedRunLedger() {
    if (!semanticConsistencyArtifact) return null;
    const ledger = semanticConsistencyArtifact.full_trace.run_ledger;
    const family = semanticSelectedFamily();
    const requested = ledger.find((run) => run.run_id === state.semanticRun);
    if (requested) return requested;
    if (family) {
      const adaptive = ledger.find((run) => run.family_or_stratum_id === family.family_id && run.policy_id === "observable_adaptive");
      if (adaptive) return adaptive;
    }
    return ledger[0] || null;
  }

  function renderSemanticRunSelector() {
    const ledger = semanticConsistencyArtifact.full_trace.run_ledger;
    const selected = semanticSelectedRunLedger();
    dom.semanticconsistencyrunselect.replaceChildren();
    ledger.forEach((run) => {
      const option = element("option", "", `${run.family_or_stratum_id} · ${semanticPolicyLabel(run.policy_id)} · ${run.run_id}`);
      option.value = run.run_id;
      dom.semanticconsistencyrunselect.append(option);
    });
    if (selected) {
      dom.semanticconsistencyrunselect.value = selected.run_id;
      if (state.semanticRun !== selected.run_id) {
        state = sanitizeState({ ...state, semanticRun: selected.run_id });
        writeStateToURL(true);
      }
    }
  }

  function semanticCompact(value, maxLength = 72) {
    const textValue = value && typeof value === "object" ? JSON.stringify(value) : String(value === undefined || value === null ? "not reported" : value);
    return textValue.length > maxLength ? `${textValue.slice(0, maxLength - 1)}…` : textValue;
  }

  function renderSemanticEpochLedger() {
    dom.semanticconsistencyepochbody.replaceChildren();
    const selected = semanticSelectedRunLedger();
    const rawRun = selected && semanticConsistencyRawArtifact && semanticConsistencyRawArtifact.runs.find((run) => run.run_id === selected.run_id);
    if (!rawRun) {
      const row = element("tr");
      const cell = element("td", "", semanticConsistencyRawArtifactError ? `Raw trace unavailable: ${semanticConsistencyRawArtifactError.message}` : "Exact epochs load on demand in Full trace.");
      cell.colSpan = 9;
      row.append(cell);
      dom.semanticconsistencyepochbody.append(row);
      return;
    }
    rawRun.epoch_trace.forEach((epoch) => {
      const row = element("tr");
      const abstentionState = epoch.abstention_state || epoch.abstention || {};
      const oodState = epoch.ood_state || epoch.ood || {};
      const abstention = abstentionState.abstained || epoch.abstained || oodState.is_out_of_distribution;
      row.dataset.abstained = String(Boolean(abstention));
      const wall = epoch.wall_tick ?? epoch.wall_epoch;
      const logical = epoch.logical_tick ?? epoch.logical_epoch;
      const mode = epoch.mode || epoch.action || epoch.selected_mode;
      const stress = epoch.stress || epoch.observable_state || epoch.stress_state;
      const membership = epoch.membership_events || epoch.membership || epoch.active_membership || (stress && stress.active_sites) || epoch.sites;
      const lineage = epoch.replica_lineages || epoch.lineage || epoch.state_lineage || { model: epoch.model_lineage, optimizer: epoch.optimizer_lineage };
      const disagreement = epoch.disagreement || { before: epoch.replica_disagreement_before, after: epoch.replica_disagreement_after, model: epoch.model_disagreement, optimizer: epoch.optimizer_disagreement };
      const work = epoch.exact_accounting || epoch.work || epoch.accounting || {
        useful: epoch.useful_tokens,
        attempted: epoch.attempted_tokens,
        replayed: epoch.replayed_tokens,
      };
      const wan = epoch.wan || { events: epoch.wan_events, modeled_seconds: epoch.modeled_wan_seconds, payload_bytes: epoch.wan_payload_bytes, time_seconds: epoch.wan_time_seconds };
      const nll = epoch.held_out_measurement && typeof epoch.held_out_measurement === "object"
        ? { value: epoch.held_out_measurement.held_out_nll, standard_deviation: epoch.held_out_measurement.held_out_nll_standard_deviation, last: epoch.last_measured_held_out_nll }
        : epoch.held_out_nll && typeof epoch.held_out_nll === "object" ? epoch.held_out_nll : { value: epoch.held_out_nll, last: epoch.last_measured_held_out_nll };
      const evidence = epoch.evidence_class || (nll.value !== null && nll.value !== undefined ? "observed" : "modeled");
      row.append(
        element("td", "", `${wall ?? "?"} / ${logical ?? "?"}`),
        element("td", "", `${semanticPolicyLabel(mode)}${epoch.mode_transition || epoch.transition ? ` · ${semanticCompact(epoch.mode_transition || epoch.transition)}` : ""}`),
        element("td", "", `${semanticCompact(stress)} · members ${semanticCompact(membership)}`),
        element("td", "", semanticCompact(lineage, 96)),
        element("td", "", `age ${semanticCompact(epoch.update_age_ticks ?? epoch.update_age)} · disagreement ${semanticCompact(disagreement)}`),
        element("td", "", semanticCompact(work, 96)),
        element("td", "", semanticCompact(wan, 96)),
        element("td", "", nll.value !== null && nll.value !== undefined ? semanticCompact(nll.value) : `not evaluated · last ${semanticCompact(nll.last)}`),
        element("td", "", `${EVIDENCE_LABELS[normalizedEvidence(evidence)]}${abstention ? ` · ABSTAIN ${semanticCompact(abstentionState.reasons || epoch.abstention_reason || oodState)}` : ""}`),
      );
      dom.semanticconsistencyepochbody.append(row);
    });
    dom.semanticconsistencyrawstate.textContent = `Raw optimizer-commit artifact loaded · ${semanticConsistencyRawArtifact.artifact_sha256}.`;
    dom.semanticconsistencyrawmeta.textContent = `${rawRun.run_id} · ${rawRun.epoch_trace.length.toLocaleString("en-US")} exact epoch records.`;
  }

  function renderSemanticConsistencyTrace() {
    if (!semanticConsistencyArtifact) return;
    renderSemanticRunSelector();
    renderSemanticEpochLedger();
    renderSemanticLedger(dom.semanticconsistencyassumptions, semanticConsistencyArtifact.full_trace.assumptions);
    renderSemanticUncertainty();
    renderSemanticLedger(dom.semanticconsistencymissingevidence, semanticConsistencyArtifact.full_trace.missing_evidence);
    const trace = semanticConsistencyArtifact.full_trace;
    const provenance = {
      schema: semanticConsistencyArtifact.schema,
      artifact_sha256: semanticConsistencyArtifact.artifact_sha256,
      source_result: semanticConsistencyArtifact.source_result,
      comparison: semanticConsistencyArtifact.comparison,
      work_contract: semanticConsistencyArtifact.work_contract,
      bindings: trace.bindings,
      evidence_boundary: semanticConsistencyArtifact.evidence_boundary,
      raw_trace_artifact: trace.raw_trace_artifact,
    };
    dom.semanticconsistencyprovenancejson.textContent = JSON.stringify(provenance, null, 2);
    dom.semanticconsistencydepthtrace.textContent = `${trace.run_ledger.length.toLocaleString("en-US")} run records · ${trace.raw_trace_artifact.epoch_count.toLocaleString("en-US")} exact optimizer-commit records available on demand · compact artifact ${semanticConsistencyArtifact.artifact_sha256}${trace.raw_trace_artifact.artifact_sha256 ? ` · raw artifact ${trace.raw_trace_artifact.artifact_sha256}` : ""}.`;
  }

  function renderSemanticConsistencyV1() {
    if (!dom.semanticconsistencyv1) return;
    dom.semanticconsistencyv1.hidden = state.experiment !== "E001-SC1";
    if (!semanticConsistencyArtifact) {
      dom.semanticconsistencyv1state.textContent = semanticConsistencyArtifactError instanceof ArtifactContractError
        ? `Artifact rejected · ${semanticConsistencyArtifactError.message}`
        : semanticConsistencyArtifactError
          ? "No result artifact yet · experiment not run"
          : "Reading semantic-consistency artifact…";
      return;
    }
    const status = semanticConsistencyArtifact.status;
    const freshman = semanticConsistencyArtifact.freshman;
    const familyCount = semanticConsistencyArtifact.researcher.family_results.length;
    dom.semanticconsistencyv1state.textContent = `${String(status.conclusion).replaceAll("_", " ")} · ${familyCount} held-out families · comparator ${semanticPolicyLabel(semanticConsistencyArtifact.comparison.selected_fixed_policy_id)} · artifact ${semanticConsistencyArtifact.artifact_sha256.slice(0, 12)}`;
    dom.semanticconsistencyeyebrow.textContent = `${semanticConsistencyArtifact.work_contract.canonical_tokens.toLocaleString("en-US")} canonical tokens · ${familyCount} untouched families`;
    dom.semanticconsistencyinsighttitle.textContent = freshman.headline;
    dom.semanticconsistencyplainanswer.textContent = freshman.plain_answer;
    setPlainWords("semantic-consistency-plain-words", status.conclusion);
    dom.semanticconsistencyboundaryshort.textContent = freshman.boundary;
    dom.semanticconsistencyfreshmancopy.textContent = freshman.explanation;
    dom.semanticconsistencyresearchercopy.textContent = semanticConsistencyArtifact.researcher.explanation;
    dom.semanticconsistencyeffectsnote.textContent = `${familyCount} evaluation families · ${semanticConsistencyArtifact.researcher.interval_label}`;
    dom.semanticconsistencyevidenceboundary.textContent = semanticConsistencyArtifact.evidence_boundary.plain_boundary;
    dom.semanticconsistencymissingshort.textContent = semanticConsistencyArtifact.full_trace.missing_evidence.length
      ? `Still missing: ${semanticConsistencyArtifact.full_trace.missing_evidence.map((entry) => entry.label || entry.claim || entry.id || entry).join("; ")}.`
      : "No missing-evidence entries were reported.";
    renderSemanticConsistencyFreshman();
    renderSemanticConsistencyEffects();
    renderSemanticConsistencyFamilySelector();
    renderSemanticConsistencyRanking();
    renderSemanticConsistencyTimeline();
    renderSemanticConsistencyFamilyTable();
    renderSemanticConsistencyTrace();
  }

  const RACK_POLICY_ORDER = ["synchronized", "random_jitter", "throughput_pacing", "static_cohorts", "telemetry_feedback"];
  const RACK_POLICY_LABELS = {
    synchronized: "Synchronized",
    random_jitter: "Random legal jitter",
    throughput_pacing: "Storage-only pacing",
    static_cohorts: "Static cohorts",
    telemetry_feedback: "Telemetry feedback",
  };

  function rackHumanLabel(value) {
    return String(value || "not reported")
      .replaceAll("_", " ")
      .replaceAll("-", " ")
      .replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  function rackRecord(value) {
    return value && typeof value === "object" && !Array.isArray(value) ? value : {};
  }

  function rackMetricValue(metric) {
    if (finiteNumber(metric)) return metric;
    const record = rackRecord(metric);
    for (const key of ["median", "value", "point_estimate", "estimate", "observed_value"]) {
      if (finiteNumber(record[key])) return record[key];
    }
    return null;
  }

  function rackInterval(metric) {
    const record = rackRecord(metric);
    const interval = record.confidence_interval_90 || record.interval_90 || record.confidence_interval;
    if (Array.isArray(interval) && interval.length === 2 && interval.every(finiteNumber)) return [interval[0], interval[1]];
    if (rackRecord(interval) && finiteNumber(interval.lower) && finiteNumber(interval.upper)) return [interval.lower, interval.upper];
    if (finiteNumber(record.lower_bound) && finiteNumber(record.upper_bound)) return [record.lower_bound, record.upper_bound];
    return null;
  }

  function rackEffectDisplay(metric) {
    const record = rackRecord(metric);
    const value = finiteNumber(record.median_effect) ? record.median_effect : rackMetricValue(record);
    const kind = String(record.effect_kind || "absolute_difference");
    const unit = String(record.unit || "");
    if (!finiteNumber(value)) return { value: "unresolved", interval: "No admissible paired estimate" };
    let valueText;
    if (kind === "relative_reduction") valueText = `${(100 * value).toLocaleString("en-US", { maximumFractionDigits: 1 })}% lower`;
    else if (["relative_increase", "relative_change", "relative_regression"].includes(kind)) valueText = `${(100 * value).toLocaleString("en-US", { maximumFractionDigits: 1, signDisplay: "always" })}%`;
    else valueText = `${value.toLocaleString("en-US", { maximumSignificantDigits: 5, signDisplay: "always" })}${unit ? ` ${unit}` : ""}`;
    const interval = rackInterval(record);
    if (!interval) return { value: valueText, interval: "90% paired interval unavailable" };
    const intervalText = ["relative_reduction", "relative_increase", "relative_change", "relative_regression"].includes(kind)
      ? `${(100 * interval[0]).toLocaleString("en-US", { maximumFractionDigits: 1 })}% to ${(100 * interval[1]).toLocaleString("en-US", { maximumFractionDigits: 1 })}%`
      : `${interval[0].toLocaleString("en-US", { maximumSignificantDigits: 5 })} to ${interval[1].toLocaleString("en-US", { maximumSignificantDigits: 5 })}${unit ? ` ${unit}` : ""}`;
    return { value: valueText, interval: `90% interval ${intervalText}` };
  }

  function rackComparison(comparator = state.rackComparator) {
    if (!rackDephasingArtifact) return {};
    const comparisons = rackRecord(rackDephasingArtifact.researcher.comparisons);
    return rackRecord(comparisons[`telemetry_feedback_vs_${comparator}`]);
  }

  function rackComparisonMetrics(comparator = state.rackComparator) {
    const comparison = rackComparison(comparator);
    return Object.keys(rackRecord(comparison.metrics)).length ? rackRecord(comparison.metrics) : comparison;
  }

  function rackMetric(metrics, ids) {
    for (const id of ids) {
      if (rackRecord(metrics[id]) && Object.keys(metrics[id]).length) return metrics[id];
      if (finiteNumber(metrics[id])) return { median_effect: metrics[id] };
    }
    return {};
  }

  function rackSelectedBlock() {
    if (!rackDephasingArtifact) return null;
    const blocks = rackDephasingArtifact.researcher.waveform_blocks;
    return blocks.find((block) => block.block_id === state.rackBlock) || blocks[0] || null;
  }

  function rackSelectedArms() {
    const block = rackSelectedBlock();
    if (!block) return { block: null, baseline: null, feedback: null };
    const baseline = block.arms.find((arm) => arm.policy_id === state.rackComparator) || null;
    const feedback = block.arms.find((arm) => arm.policy_id === "telemetry_feedback") || null;
    return { block, baseline, feedback };
  }

  function renderRackBlockControls() {
    const blocks = rackDephasingArtifact.researcher.waveform_blocks;
    dom.rackdephasingblockselect.replaceChildren();
    blocks.forEach((block) => {
      const option = element("option", "", `${block.block_id} · ${rackHumanLabel(block.split)}`);
      option.value = block.block_id;
      dom.rackdephasingblockselect.append(option);
    });
    const selected = blocks.some((block) => block.block_id === state.rackBlock) ? state.rackBlock : blocks[0]?.block_id;
    if (selected) dom.rackdephasingblockselect.value = selected;
    dom.rackdephasingcomparatorselect.value = state.rackComparator;
  }

  function rackTracePointArrays(displayTrace) {
    if (Array.isArray(displayTrace)) return displayTrace;
    const trace = rackRecord(displayTrace);
    for (const key of ["rack_pdu_points", "rack_pdu_power_points", "rack_power_points", "points", "samples"]) {
      if (Array.isArray(trace[key])) return trace[key];
      if (Array.isArray(rackRecord(trace[key]).points)) return trace[key].points;
    }
    if (Array.isArray(rackRecord(trace.rack_pdu).points)) return trace.rack_pdu.points;
    const channels = rackRecord(trace.channels);
    for (const key of ["rack_pdu_power", "rack_power_w", "rack-pdu.power-w"]) {
      if (Array.isArray(channels[key])) return channels[key];
      if (Array.isArray(rackRecord(channels[key]).points)) return channels[key].points;
    }
    return [];
  }

  function rackTraceSeries(arm) {
    const rawPoints = rackTracePointArrays(arm && arm.display_trace);
    const normalized = [];
    rawPoints.forEach((point) => {
      if (Array.isArray(point) && point.length >= 2 && finiteNumber(point[0]) && finiteNumber(point[1])) {
        normalized.push({ rawTime: point[0], isNs: Math.abs(point[0]) > 1e11, powerW: point[1] });
        return;
      }
      const record = rackRecord(point);
      const nsKeys = ["utc_ns", "reference_interval_end_ns", "reference_time_ns", "timestamp_ns", "time_ns", "monotonic_ns", "t_ns"];
      const secondKeys = ["relative_seconds", "time_seconds", "time_s", "seconds", "timestamp"];
      let rawTime = null;
      let isNs = false;
      for (const key of nsKeys) {
        if (finiteNumber(record[key])) { rawTime = record[key]; isNs = true; break; }
      }
      if (rawTime === null) {
        for (const key of secondKeys) {
          if (finiteNumber(record[key])) { rawTime = record[key]; break; }
        }
      }
      let powerW = null;
      for (const key of ["rack_pdu_power_w", "rack_power_w", "power_w", "value"]) {
        if (finiteNumber(record[key])) { powerW = record[key]; break; }
      }
      if (rawTime !== null && powerW !== null) normalized.push({ rawTime, isNs, powerW });
    });
    normalized.sort((left, right) => left.rawTime - right.rawTime);
    if (!normalized.length) return { points: [], originNs: null, duration: 0 };
    const origin = normalized[0].rawTime;
    const usesNs = normalized[0].isNs;
    const points = normalized.map((point) => ({
      seconds: usesNs ? (point.rawTime - origin) / 1e9 : point.rawTime - origin,
      powerW: point.powerW,
    })).filter((point) => finiteNumber(point.seconds) && finiteNumber(point.powerW));
    return {
      points,
      originNs: usesNs ? origin : null,
      duration: points.length ? points[points.length - 1].seconds : 0,
    };
  }

  function rackEventStart(event) {
    for (const key of ["actual_start_ns", "start_ns", "scheduled_release_ns", "earliest_start_ns"]) {
      if (finiteNumber(event[key])) return event[key];
    }
    return null;
  }

  function rackEventEnd(event, start) {
    for (const key of ["actual_end_ns", "end_ns", "completed_at_ns"]) {
      if (finiteNumber(event[key])) return Math.max(start, event[key]);
    }
    return start;
  }

  function rackDisplayEvents(arm) {
    return arm && arm.event_summary && Array.isArray(arm.event_summary.display_events) ? arm.event_summary.display_events : [];
  }

  function rackChartEvents(arm) {
    const intervals = rackRecord(arm && arm.display_trace).state_flow_intervals;
    return Array.isArray(intervals) ? intervals : rackDisplayEvents(arm);
  }

  function rackSeriesPath(points, xScale, yScale) {
    return points.map((point, index) => `${index ? "L" : "M"}${xScale(point.seconds).toFixed(2)},${yScale(point.powerW).toFixed(2)}`).join(" ");
  }

  function renderRackPanel(svg, arm, series, layout, shared) {
    const { left, right, top, waveformHeight, railTop, railHeight, width, label } = layout;
    const x = (seconds) => left + (Math.max(0, Math.min(shared.duration, seconds)) / Math.max(shared.duration, 1e-9)) * (width - left - right);
    const y = (power) => top + waveformHeight - ((power - shared.minPower) / Math.max(shared.maxPower - shared.minPower, 1e-9)) * waveformHeight;
    svg.append(svgElement("text", { x: left, y: top - 9, class: "rack-dephasing-direct-label" })).textContent = label;
    for (let index = 0; index <= 4; index += 1) {
      const power = shared.minPower + (shared.maxPower - shared.minPower) * index / 4;
      const yPosition = y(power);
      svg.append(
        svgElement("line", { x1: left, x2: width - right, y1: yPosition, y2: yPosition, class: "rack-dephasing-grid-line" }),
        svgElement("text", { x: left - 8, y: yPosition + 4, "text-anchor": "end", class: "rack-dephasing-axis-label" }),
      );
      svg.lastChild.textContent = formatPower(power);
    }
    if (series.points.length) {
      const path = svgElement("path", {
        d: rackSeriesPath(series.points, x, y),
        class: `rack-dephasing-wave-line rack-dephasing-wave-line--${arm.policy_id === "telemetry_feedback" ? "feedback" : "baseline"}`,
      });
      svg.append(path);
      const last = series.points[series.points.length - 1];
      const direct = svgElement("text", { x: Math.min(width - right + 7, width - 8), y: y(last.powerW) + 4, class: "rack-dephasing-direct-label" });
      direct.textContent = arm.policy_id === "telemetry_feedback" ? "feedback" : RACK_POLICY_LABELS[arm.policy_id] || arm.policy_id;
      svg.append(direct);
    }

    const events = rackChartEvents(arm).filter((event) => rackEventStart(event) !== null);
    const jobs = [...new Set(events.map((event) => String(event.job_id ?? "rack")))].sort((a, b) => a.localeCompare(b, undefined, { numeric: true })).slice(0, 8);
    const rowHeight = Math.max(8, Math.min(15, railHeight / Math.max(jobs.length, 1)));
    const eventOrigin = series.originNs !== null ? series.originNs : Math.min(...events.map(rackEventStart));
    jobs.forEach((job, jobIndex) => {
      const yPosition = railTop + jobIndex * rowHeight;
      const jobLabel = svgElement("text", { x: left - 8, y: yPosition + rowHeight * 0.72, "text-anchor": "end", class: "rack-dephasing-rail-label" });
      jobLabel.textContent = `job ${job}`;
      svg.append(jobLabel, svgElement("line", { x1: left, x2: width - right, y1: yPosition + rowHeight, y2: yPosition + rowHeight, class: "rack-dephasing-grid-line" }));
      events.filter((event) => String(event.job_id ?? "rack") === job).forEach((event) => {
        const startNs = rackEventStart(event);
        const endNs = rackEventEnd(event, startNs);
        const startSeconds = (startNs - eventOrigin) / 1e9;
        const endSeconds = (endNs - eventOrigin) / 1e9;
        if (endSeconds < 0 || startSeconds > shared.duration) return;
        const rect = svgElement("rect", {
          x: x(Math.max(0, startSeconds)),
          y: yPosition + 1,
          width: Math.max(1.5, x(Math.min(shared.duration, endSeconds)) - x(Math.max(0, startSeconds))),
          height: Math.max(5, rowHeight - 2),
          rx: 1,
          class: "rack-dephasing-event-mark",
          "data-kind": String(event.kind || "event"),
        });
        svg.append(rect);
      });
    });
  }

  function renderRackWaveformFallback(baseline, feedback, baselineSeries, feedbackSeries) {
    dom.rackdephasingwaveformfallback.replaceChildren();
    const table = element("table", "rack-dephasing-table");
    table.style.minWidth = "0";
    const caption = element("caption", "visually-hidden", "Selected block waveform values and event counts");
    const head = element("thead");
    const headRow = element("tr");
    ["Arm", "Rack samples", "Power range", "State-flow events", "Rack ramp", "Spectral energy"].forEach((label) => headRow.append(element("th", "", label)));
    head.append(headRow);
    const body = element("tbody");
    [[baseline, baselineSeries], [feedback, feedbackSeries]].forEach(([arm, series]) => {
      if (!arm) return;
      const powers = series.points.map((point) => point.powerW);
      const range = powers.length ? `${formatPower(Math.min(...powers))} to ${formatPower(Math.max(...powers))}` : "trace unavailable";
      const row = element("tr");
      row.append(
        element("td", "", RACK_POLICY_LABELS[arm.policy_id] || rackHumanLabel(arm.policy_id)),
        element("td", "", series.points.length.toLocaleString("en-US")),
        element("td", "", range),
        element("td", "", rackChartEvents(arm).length.toLocaleString("en-US")),
        element("td", "", finiteNumber(arm.p99_9_rack_ramp_w_per_s) ? `${arm.p99_9_rack_ramp_w_per_s.toLocaleString("en-US", { maximumSignificantDigits: 5 })} W/s` : "unmeasured"),
        element("td", "", finiteNumber(arm.rack_spectral_energy_0_1_10_hz) ? arm.rack_spectral_energy_0_1_10_hz.toLocaleString("en-US", { maximumSignificantDigits: 5 }) : "unmeasured"),
      );
      body.append(row);
    });
    table.append(caption, head, body);
    dom.rackdephasingwaveformfallback.append(element("p", "", "Solid violet is telemetry feedback; dashed orange is the selected comparator. Rectangles encode checkpoint, transfer, rebuild, rejoin, compute, and merge intervals; the table keeps all essential values available without color or hover."), table);
  }

  function renderRackDephasingWaveform() {
    if (!rackDephasingArtifact || !dom.rackdephasingwaveformsvg) return;
    const { block, baseline, feedback } = rackSelectedArms();
    const svg = dom.rackdephasingwaveformsvg;
    svg.replaceChildren();
    if (!block || !baseline || !feedback) {
      dom.rackdephasingwaveformfallback.textContent = "The selected block does not contain both the comparator and telemetry-feedback arms.";
      return;
    }
    const baselineSeries = rackTraceSeries(baseline);
    const feedbackSeries = rackTraceSeries(feedback);
    renderRackWaveformFallback(baseline, feedback, baselineSeries, feedbackSeries);
    const allPoints = [...baselineSeries.points, ...feedbackSeries.points];
    if (!allPoints.length) {
      dom.rackdephasingwaveformdesc.textContent = `${block.block_id} has no compact rack-PDU display trace. The metric table and raw chunk manifest remain available.`;
      return;
    }
    const width = Math.max(320, Math.round(svg.getBoundingClientRect().width || 960));
    const mobile = width < 620;
    const height = mobile ? 680 : 540;
    const left = mobile ? 58 : 84;
    const right = mobile ? 18 : 118;
    const minObserved = Math.min(...allPoints.map((point) => point.powerW));
    const maxObserved = Math.max(...allPoints.map((point) => point.powerW));
    const padding = Math.max((maxObserved - minObserved) * 0.08, Math.abs(maxObserved) * 0.015, 1);
    const shared = {
      duration: Math.max(baselineSeries.duration, feedbackSeries.duration, 1),
      minPower: minObserved - padding,
      maxPower: maxObserved + padding,
    };
    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
    const panelGap = mobile ? 34 : 28;
    const panelHeight = (height - 48 - panelGap) / 2;
    const waveformHeight = Math.max(105, panelHeight * 0.58);
    const railTopOffset = waveformHeight + 19;
    const railHeight = Math.max(46, panelHeight - railTopOffset - 5);
    const baselineTop = 30;
    const feedbackTop = baselineTop + panelHeight + panelGap;
    const baselineLabel = `${block.block_id} · ${RACK_POLICY_LABELS[baseline.policy_id] || baseline.policy_id}`;
    const feedbackLabel = `${block.block_id} · Telemetry feedback`;
    const timeLabels = [];
    for (let index = 0; index <= 4; index += 1) {
      const seconds = shared.duration * index / 4;
      const x = left + (seconds / shared.duration) * (width - left - right);
      svg.append(svgElement("line", { x1: x, x2: x, y1: 24, y2: height - 22, class: "rack-dephasing-grid-line" }));
      const label = svgElement("text", { x, y: height - 7, "text-anchor": index === 0 ? "start" : index === 4 ? "end" : "middle", class: "rack-dephasing-axis-label" });
      label.textContent = `${seconds.toLocaleString("en-US", { maximumFractionDigits: 1 })} s`;
      timeLabels.push(label);
    }
    renderRackPanel(svg, baseline, baselineSeries, { left, right, top: baselineTop, waveformHeight, railTop: baselineTop + railTopOffset, railHeight, width, label: baselineLabel }, shared);
    renderRackPanel(svg, feedback, feedbackSeries, { left, right, top: feedbackTop, waveformHeight, railTop: feedbackTop + railTopOffset, railHeight, width, label: feedbackLabel }, shared);
    timeLabels.forEach((label) => svg.append(label));
    dom.rackdephasingwaveformdesc.textContent = `${block.block_id} compares ${RACK_POLICY_LABELS[baseline.policy_id]} with telemetry feedback on a shared relative time axis. The comparator has ${baselineSeries.points.length} rack-PDU samples and ${rackChartEvents(baseline).length} displayed state-flow events; feedback has ${feedbackSeries.points.length} samples and ${rackChartEvents(feedback).length} events.`;
  }

  function renderRackFreshman() {
    dom.rackdephasingfreshmangrid.replaceChildren();
    rackDephasingArtifact.freshman.cards.forEach((entry) => {
      const card = element("article", "rack-dephasing-plain-card");
      card.append(element("span", "", entry.label), element("strong", "", entry.value), element("small", "", entry.detail));
      dom.rackdephasingfreshmangrid.append(card);
    });
  }

  function renderRackEffects() {
    dom.rackdephasingeffectgrid.replaceChildren();
    const metrics = rackComparisonMetrics();
    const definitions = [
      ["Rack ramp", ["rack_ramp", "rack_ramp_reduction", "p99_9_rack_ramp_w_per_s"], "p99.9 absolute rack-PDU ramp"],
      ["0.1–10 Hz energy", ["rack_spectral_energy", "rack_spectral_reduction", "rack_spectral_energy_0_1_10_hz"], "detrended rack-PDU spectral energy"],
      ["Useful-token rate", ["useful_token_throughput", "useful_token_throughput_regression"], "throughput constraint"],
      ["Rack J / token", ["rack_energy_per_useful_token", "rack_energy_per_useful_token_increase"], "whole-rack energy constraint"],
      ["p95 recovery", ["p95_recovery_time_s", "p95_recovery_time_regression", "recovery_time"], "failure-to-rejoin constraint"],
      ["Held-out NLL", ["final_held_out_nll", "held_out_nll", "held_out_nll_absolute_difference"], "learning-equivalence constraint"],
    ];
    definitions.forEach(([label, ids, meaning]) => {
      const metric = rackMetric(metrics, ids);
      const display = rackEffectDisplay(metric);
      const passed = rackRecord(metric).passed;
      const card = element("article", "rack-dephasing-effect-card");
      card.dataset.state = rackDephasingArtifact.researcher.measurement_valid !== true ? "invalid" : passed === false ? "fail" : passed === true ? "pass" : "unresolved";
      card.append(element("span", "", `${rackHumanLabel(state.rackComparator)} comparison`), element("strong", "", display.value), element("small", "", `${display.interval} · ${meaning}`));
      dom.rackdephasingeffectgrid.append(card);
    });
  }

  function rackPolicyMetric(policy, ids) {
    const policyMetrics = rackDephasingArtifact.researcher.policy_metrics;
    const metrics = Array.isArray(policyMetrics)
      ? rackRecord(policyMetrics.find((entry) => entry.policy_id === policy))
      : rackRecord(rackRecord(policyMetrics)[policy]);
    return rackMetric(metrics, ids);
  }

  function rackFormatMetric(metric, unit, formatter) {
    const value = rackMetricValue(metric);
    if (!finiteNumber(value)) return "unmeasured";
    if (formatter) return formatter(value);
    return `${value.toLocaleString("en-US", { maximumSignificantDigits: 5 })}${unit ? ` ${unit}` : ""}`;
  }

  function renderRackPolicyTable() {
    dom.rackdephasingpolicybody.replaceChildren();
    RACK_POLICY_ORDER.forEach((policy) => {
      const row = element("tr");
      row.append(
        element("td", "", RACK_POLICY_LABELS[policy]),
        element("td", "", rackFormatMetric(rackPolicyMetric(policy, ["rack_ramp", "p99_9_rack_ramp_w_per_s"]), "W/s")),
        element("td", "", rackFormatMetric(rackPolicyMetric(policy, ["rack_spectral_energy", "rack_spectral_energy_0_1_10_hz"]), "")),
        element("td", "", rackFormatMetric(rackPolicyMetric(policy, ["useful_token_throughput"]), "token/s")),
        element("td", "", rackFormatMetric(rackPolicyMetric(policy, ["rack_energy_per_useful_token"]), "J/token")),
        element("td", "", rackFormatMetric(rackPolicyMetric(policy, ["p95_recovery_time_s", "recovery_time"]), "", (value) => formatSeconds(value, 2))),
        element("td", "", rackFormatMetric(rackPolicyMetric(policy, ["final_held_out_nll", "held_out_nll"]), "")),
      );
      dom.rackdephasingpolicybody.append(row);
    });
  }

  function rackGateEntries(value, prefix = "") {
    const entries = [];
    Object.entries(rackRecord(value)).forEach(([key, candidate]) => {
      const id = prefix ? `${prefix}.${key}` : key;
      if (typeof candidate === "boolean") {
        entries.push({ id, state: candidate ? "pass" : "fail", detail: candidate ? "passed" : "failed" });
        return;
      }
      const record = rackRecord(candidate);
      const status = String(record.status || "").toLowerCase();
      if (typeof record.passed === "boolean" || ["pass", "passed", "fail", "failed", "unresolved", "invalid"].includes(status)) {
        const stateValue = typeof record.passed === "boolean" ? (record.passed ? "pass" : "fail") : status.startsWith("pass") ? "pass" : status.startsWith("fail") ? "fail" : "unresolved";
        const observedValue = finiteNumber(record.observed) ? record.observed : record.observed_value;
        const observed = finiteNumber(observedValue) ? ` · observed ${observedValue.toLocaleString("en-US", { maximumSignificantDigits: 5 })}` : "";
        entries.push({ id, state: stateValue, detail: `${record.description || record.reason || record.status || stateValue}${observed}` });
        return;
      }
      entries.push(...rackGateEntries(record, id));
    });
    return entries;
  }

  function renderRackGates() {
    dom.rackdephasinggatestrip.replaceChildren();
    const gates = rackGateEntries(rackDephasingArtifact.researcher.gates);
    gates.forEach((entry) => {
      const gate = element("div", "rack-dephasing-gate");
      gate.dataset.state = entry.state;
      gate.append(element("strong", "", `${entry.state.toUpperCase()} · ${rackHumanLabel(entry.id)}`), element("span", "", entry.detail));
      dom.rackdephasinggatestrip.append(gate);
    });
    if (!gates.length) {
      const gate = element("div", "rack-dephasing-gate");
      gate.dataset.state = "unresolved";
      gate.append(element("strong", "", "UNRESOLVED"), element("span", "", "No gate records were emitted."));
      dom.rackdephasinggatestrip.append(gate);
    }
    const passed = gates.filter((gate) => gate.state === "pass").length;
    const failed = gates.filter((gate) => gate.state === "fail").length;
    dom.rackdephasinggatesummary.textContent = `${passed}/${gates.length} pass · ${failed} fail`;
  }

  function rackBoundaryText(boundary) {
    if (typeof boundary === "string") return boundary;
    const record = rackRecord(boundary);
    const parts = [];
    for (const key of ["plain_boundary", "summary", "scope", "observed_boundary"]) {
      if (typeof record[key] === "string" && record[key]) parts.push(record[key]);
    }
    if (Array.isArray(record.observed) && record.observed.length) parts.push(`Observed: ${record.observed.join(", ")}.`);
    if (Array.isArray(record.can_resolve) && record.can_resolve.length) parts.push(`Can resolve: ${record.can_resolve.join(", ")}.`);
    if (Array.isArray(record.cannot_resolve) && record.cannot_resolve.length) parts.push(`Cannot resolve: ${record.cannot_resolve.join(", ")}.`);
    if (Array.isArray(record.unmeasured) && record.unmeasured.length) parts.push(`Unmeasured: ${record.unmeasured.join(", ")}.`);
    if (Array.isArray(record.not_claimed) && record.not_claimed.length) parts.push(`Not claimed: ${record.not_claimed.join(", ")}.`);
    return parts.join(" ") || JSON.stringify(record);
  }

  function renderRackEventLedger() {
    dom.rackdephasingeventbody.replaceChildren();
    const { baseline, feedback } = rackSelectedArms();
    const arms = [baseline, feedback].filter(Boolean);
    const records = arms.flatMap((arm) => rackDisplayEvents(arm).map((event) => ({ arm, event })));
    const displayLimit = 1000;
    records.slice(0, displayLimit).forEach(({ arm, event }) => {
      const ready = event.earliest_start_ns;
      const release = event.scheduled_release_ns;
      const start = rackEventStart(event);
      const end = start === null ? null : rackEventEnd(event, start);
      const row = element("tr");
      row.append(
        element("td", "", `${RACK_POLICY_LABELS[arm.policy_id] || arm.policy_id} / ${event.job_id ?? "rack"}`),
        element("td", "", String(event.kind || "not reported")),
        element("td", "", String(event.state_generation || "not reported")),
        element("td", "", finiteNumber(ready) && finiteNumber(release) ? `${ready.toLocaleString("en-US")} → ${release.toLocaleString("en-US")} ns` : "not reported"),
        element("td", "", finiteNumber(start) && finiteNumber(end) ? `${start.toLocaleString("en-US")} → ${end.toLocaleString("en-US")} ns` : "not reported"),
        element("td", "", finiteNumber(event.bytes) ? formatBytes(event.bytes) : "not reported"),
        element("td", "", String(event.outcome || "not reported")),
      );
      dom.rackdephasingeventbody.append(row);
    });
    if (!records.length) {
      const row = element("tr");
      const cell = element("td", "", "No display-event records are present for the selected pair. Exact raw chunk bindings remain below.");
      cell.colSpan = 7;
      row.append(cell);
      dom.rackdephasingeventbody.append(row);
    } else if (records.length > displayLimit) {
      const row = element("tr");
      const cell = element("td", "", `${(records.length - displayLimit).toLocaleString("en-US")} additional compact events are omitted from the DOM; the complete hash-chained event stream is in the raw manifest.`);
      cell.colSpan = 7;
      row.append(cell);
      dom.rackdephasingeventbody.append(row);
    }
  }

  function rackFact(label, value) {
    const fact = element("div", "rack-dephasing-trace-fact");
    fact.append(element("strong", "", label), element("span", "", value));
    return fact;
  }

  function rackManifestRefs(value, path = "raw", output = []) {
    if (Array.isArray(value)) {
      value.forEach((item, index) => rackManifestRefs(item, `${path}[${index}]`, output));
      return output;
    }
    const record = rackRecord(value);
    if (!Object.keys(record).length) return output;
    const uri = record.uri || record.path || record.relative_path || record.chunk_path;
    if (typeof uri === "string" && uri) {
      output.push({ path, uri, sha256: record.sha256 || record.content_sha256 || record.artifact_sha256 || record.chunk_sha256 || null, recordCount: record.record_count || record.sample_count || null });
    }
    Object.entries(record).forEach(([key, item]) => {
      if (["uri", "path", "relative_path", "chunk_path"].includes(key)) return;
      if (item && typeof item === "object") rackManifestRefs(item, `${path}.${key}`, output);
    });
    return output;
  }

  function renderRackTrace() {
    const trace = rackDephasingArtifact.full_trace;
    const researcher = rackDephasingArtifact.researcher;
    const { block, baseline, feedback } = rackSelectedArms();
    dom.rackdephasingtracesummary.replaceChildren(
      rackFact("Selected block", block ? `${block.block_id} · ${block.split}` : "unavailable"),
      rackFact("Result volume", `${trace.block_count.toLocaleString("en-US")} blocks · ${trace.arm_count.toLocaleString("en-US")} arms`),
      rackFact("Measurement", researcher.measurement_valid ? "VALID" : `INVALID · ${researcher.active_invalidators.join(", ") || "reason not reported"}`),
      rackFact("Comparator semantics", JSON.stringify(baseline ? baseline.semantics : null)),
      rackFact("Feedback semantics", JSON.stringify(feedback ? feedback.semantics : null)),
      rackFact("Clock alignment", JSON.stringify(researcher.clock_alignment)),
      rackFact("Sensor manifest", JSON.stringify(researcher.sensor_manifest)),
      rackFact("Source artifact", rackDephasingArtifact.source_result.artifact_sha256),
    );

    dom.rackdephasingrawmanifest.replaceChildren();
    const refs = rackManifestRefs(trace.raw_trace_manifest);
    refs.slice(0, 200).forEach((entry) => {
      const fact = element("div", "rack-dephasing-trace-fact");
      fact.append(element("strong", "", entry.path));
      const isLocalAbsolute = /^[A-Za-z]:[\\/]/.test(entry.uri) || entry.uri.startsWith("/") || entry.uri.startsWith("\\\\");
      if (isLocalAbsolute) {
        fact.append(element("span", "", `${entry.uri} · local execution path`));
      } else {
        const link = element("a", "", entry.uri);
        link.href = entry.uri;
        link.rel = "noreferrer";
        fact.append(link);
      }
      fact.append(element("span", "", `${entry.sha256 ? `SHA-256 ${entry.sha256}` : "hash not reported"}${finiteNumber(entry.recordCount) ? ` · ${entry.recordCount.toLocaleString("en-US")} records` : ""}`));
      dom.rackdephasingrawmanifest.append(fact);
    });
    if (!refs.length) dom.rackdephasingrawmanifest.append(rackFact("Raw trace", "No chunk URI was emitted."));
    if (refs.length > 200) dom.rackdephasingrawmanifest.append(rackFact("Additional chunks", `${(refs.length - 200).toLocaleString("en-US")} bindings remain in compact provenance below.`));
    dom.rackdephasingprovenancejson.textContent = JSON.stringify({
      schema: rackDephasingArtifact.schema,
      artifact_sha256: rackDephasingArtifact.artifact_sha256,
      artifact_state: rackDephasingArtifact.artifact_state,
      source_result: rackDephasingArtifact.source_result,
      scenario_sha256: trace.scenario_sha256,
      source_bindings: trace.source_bindings,
      engine: trace.engine,
      runtime: trace.runtime,
      sensor_manifest: researcher.sensor_manifest,
      clock_alignment: researcher.clock_alignment,
      raw_trace_manifest: trace.raw_trace_manifest,
      evidence_boundary: rackDephasingArtifact.evidence_boundary,
    }, null, 2);
    dom.rackdephasingdepthtrace.textContent = `${trace.block_count.toLocaleString("en-US")} paired blocks · ${trace.arm_count.toLocaleString("en-US")} physical arms · exact raw streams are hash-chained and bound by the manifest · compact artifact ${rackDephasingArtifact.artifact_sha256}.`;
    renderRackEventLedger();
  }

  function renderRackDephasingV3() {
    if (!dom.rackdephasingv3) return;
    if (!rackDephasingArtifact) {
      dom.rackdephasingv3.hidden = true;
      return;
    }
    dom.rackdephasingv3.hidden = false;
    const freshman = rackDephasingArtifact.freshman;
    const researcher = rackDephasingArtifact.researcher;
    const decision = typeof researcher.decision === "string" ? researcher.decision : rackRecord(researcher.decision).conclusion || rackRecord(researcher.decision).status || rackDephasingArtifact.artifact_state;
    dom.rackdephasingv3state.textContent = `${researcher.measurement_valid ? "measurement valid" : "measurement invalid"} · ${rackHumanLabel(decision)} · artifact ${rackDephasingArtifact.artifact_sha256.slice(0, 12)}`;
    dom.rackdephasingeyebrow.textContent = researcher.measurement_valid ? `${rackDephasingArtifact.full_trace.evaluation_block_count} physical evaluation blocks` : "Physical measurement invalid";
    dom.rackdephasinginsighttitle.textContent = freshman.headline;
    dom.rackdephasingplainanswer.textContent = freshman.plain_answer;
    dom.rackdephasingboundaryshort.textContent = freshman.boundary;
    dom.rackdephasingfreshmancopy.textContent = freshman.plain_answer;
    dom.rackdephasingresearchercopy.textContent = `Only legal release timing changed. ${RACK_POLICY_LABELS.telemetry_feedback} is compared with synchronized, random jitter, storage-only pacing, and static cohorts under the same useful work, failures, state generations, and held-out learning batches.`;
    dom.rackdephasingevidenceboundary.textContent = rackBoundaryText(rackDephasingArtifact.evidence_boundary);
    const next = rackDephasingArtifact.next_experiment;
    dom.rackdephasingnextquestion.textContent = `${next.id}: ${next.question} Do not claim yet: ${next.do_not_claim_yet.join(", ")}.`;
    renderRackBlockControls();
    renderRackFreshman();
    renderRackDephasingWaveform();
    renderRackEffects();
    renderRackPolicyTable();
    renderRackGates();
    renderRackTrace();
  }

  function renderStatus() {
    dom.stageboundary.replaceChildren();
    const mark = element("span", "stage-mark");
    mark.setAttribute("aria-hidden", "true");
    dom.stageboundary.append(mark);

    if (state.experiment === "E001-SC1") {
      dom.experimentkickercode.textContent = "E001-SC1";
      dom.experimentkickername.textContent = "Observable Semantic Slack";
      dom.experimentquestion.textContent = semanticConsistencyArtifact
        ? semanticConsistencyArtifact.question
        : "Can one observable controller safely spend semantic slack?";
      if (semanticConsistencyArtifact) {
        const status = semanticConsistencyArtifact.status;
        dom.stageboundary.append(
          element("strong", "", String(status.stage || "software experiment").replaceAll("_", " ")),
          document.createTextNode("·"),
          document.createTextNode(String(status.validation || "held-out family evaluation").replaceAll("_", " ")),
        );
        dom.plainanswer.textContent = String(status.plain_answer || semanticConsistencyArtifact.freshman.plain_answer || "The artifact does not report a plain answer.");
        setPlainWords("plain-words", status.conclusion);
        dom.artifactstate.textContent = `Artifact loaded · ${String(status.conclusion || "inconclusive").replaceAll("_", " ")} · ${semanticConsistencyArtifact.schema} · ${semanticConsistencyArtifact.artifact_sha256.slice(0, 12)}`;
        dom.footerevidencestate.lastChild.textContent = " Evidence state: measured learning + exact accounting + modeled infrastructure";
      } else {
        dom.stageboundary.append(element("strong", "", "Software experiment"), document.createTextNode("·"), document.createTextNode("result not loaded"));
        dom.plainanswer.textContent = "No semantic-consistency result is loaded. No controller ranking, interval, or learning conclusion is shown.";
        setPlainWords("plain-words", null);
        if (semanticConsistencyArtifactError instanceof ArtifactContractError) {
          dom.artifactstate.textContent = `Artifact rejected: ${semanticConsistencyArtifactError.message}.`;
        } else if (semanticConsistencyArtifactError) {
          dom.artifactstate.textContent = `${SEMANTIC_CONSISTENCY_ARTIFACT_URL} is absent or unreadable. The experiment has not produced a browser result yet.`;
        } else {
          dom.artifactstate.textContent = `Reading ${SEMANTIC_CONSISTENCY_ARTIFACT_URL}…`;
        }
        dom.footerevidencestate.lastChild.textContent = " Evidence state: awaiting semantic-consistency artifact";
      }
      return;
    }

    dom.experimentkickercode.textContent = "E001";
    dom.experimentkickername.textContent = "Beyond One Datacenter · Prior Evidence Chain";
    dom.experimentquestion.textContent = "Can one training run survive across three datacenters?";

    if (artifact) {
      const stage = String(artifact.status.stage || "virtual_mechanics_screen").replaceAll("_", " ");
      const stageStrong = element("strong", "", stage);
      const validation = artifact.status.held_out_learning_validation === true ? "held-out validation attached" : "held-out validation absent";
      dom.stageboundary.append(stageStrong, document.createTextNode("·"), document.createTextNode(validation));
      dom.plainanswer.textContent = String(artifact.status.plain_answer || "The artifact does not report a plain answer.");
      setPlainWords("plain-words", artifact.status.conclusion);
      const protocol = typeof artifact.protocol_hash === "string" ? artifact.protocol_hash.slice(0, 12) : "not reported";
      dom.artifactstate.textContent = `Artifact loaded · ${conclusionLabel(artifact.status.conclusion)} · ${artifact.schema} · protocol ${protocol}`;
      dom.footerevidencestate.lastChild.textContent = " Evidence state: mixed artifact evidence";
    } else {
      dom.stageboundary.append(element("strong", "", "Virtual screening"), document.createTextNode("·"), document.createTextNode("held-out validation absent"));
      dom.plainanswer.textContent = "No generated experiment artifact is loaded. The scenario can be inspected, but policy results and the learning-efficiency answer remain not run.";
      setPlainWords("plain-words", null);
      if (artifactError instanceof ArtifactContractError) {
        dom.artifactstate.textContent = `Artifact rejected: ${artifactError.message}. No result values are displayed.`;
      } else if (artifactError) {
        dom.artifactstate.textContent = `${ARTIFACT_URL} is absent or unreadable. Only approved scenario inputs are visible; results are not run.`;
      } else {
        dom.artifactstate.textContent = `Reading ${ARTIFACT_URL}…`;
      }
      dom.footerevidencestate.lastChild.textContent = " Evidence state: awaiting artifact";
    }
  }

  function scenarioData() {
    return artifact && artifact.scenario ? artifact.scenario : SAFE_SCENARIO;
  }

  function openInspectorFor(node, extraState = {}) {
    inspectorHidden = false;
    transientInspector = window.matchMedia("(max-width: 760px)").matches;
    commitState({ node, ...extraState });
  }

  function rackSVG() {
    const svg = svgElement("svg", { viewBox: "0 0 64 72", "aria-hidden": "true" });
    const frame = svgElement("rect", { x: 2, y: 4, width: 60, height: 64, rx: 2 });
    svg.append(frame);
    for (let bay = 0; bay < 5; bay += 1) {
      const x = 6 + bay * 11;
      svg.append(
        svgElement("rect", { x, y: 9, width: 8, height: 54, rx: 0.8 }),
        svgElement("path", { d: `M${x + 2} 16h4M${x + 2} 22h4M${x + 2} 53h4` }),
        svgElement("circle", { cx: x + 4, cy: 58, r: 1 }),
      );
    }
    svg.append(svgElement("path", { d: "M2 43h60M8 68v2m48-2v2" }));
    return svg;
  }

  function renderSiteRail() {
    const scenario = scenarioData();
    const sites = Array.isArray(scenario.sites) ? scenario.sites : [];
    const links = Array.isArray(scenario.links) ? scenario.links : [];
    dom.siterail.replaceChildren();
    dom.sitefieldsource.textContent = artifact ? "Artifact scenario inputs · assumed" : "Approved screening inputs · artifact not run";

    sites.forEach((site, index) => {
      const button = element("button", "site-button");
      button.type = "button";
      button.dataset.siteId = String(site.site_id);
      button.classList.toggle("is-selected", state.node === `site:${site.site_id}`);
      button.setAttribute("aria-label", `${site.site_id} site, ${site.accelerator_count} ${site.accelerator_type}, assumed scenario input`);
      const copy = element("span", "site-copy");
      copy.append(
        element("span", "site-name", String(site.site_id)),
        element("span", "site-fact", `${finiteNumber(site.accelerator_count) ? site.accelerator_count.toLocaleString("en-US") : "not reported"} × ${String(site.accelerator_type || "accelerator type not reported")}`),
        element("span", "site-power", artifact && finiteNumber(site.power_cap_w) ? `power cap ${formatPower(site.power_cap_w)}` : "allocated power not reported"),
        evidenceTag("assumed"),
      );
      button.append(rackSVG(), copy);
      button.addEventListener("click", () => openInspectorFor(`site:${site.site_id}`));
      dom.siterail.append(button);

      if (index < sites.length - 1) {
        const nextSite = sites[index + 1];
        const link = links.find((candidate) => {
          const endpoints = new Set([candidate.site_a, candidate.site_b]);
          return endpoints.has(site.site_id) && endpoints.has(nextSite.site_id);
        });
        const linkButton = element("button", "wan-link-button");
        linkButton.type = "button";
        if (link) {
          const gigabits = finiteNumber(link.bandwidth_bytes_per_second) ? link.bandwidth_bytes_per_second * 8 / 1e9 : null;
          const latencyMs = finiteNumber(link.latency_ns) ? link.latency_ns / 1e6 : null;
          linkButton.dataset.linkId = String(link.link_id);
          linkButton.classList.toggle("is-selected", state.node === `link:${link.link_id}`);
          linkButton.setAttribute("aria-label", `${link.link_id} assumed WAN link, ${gigabits === null ? "bandwidth not reported" : `${formatDecimal(gigabits, gigabits % 1 === 0 ? 0 : 1)} gigabits per second`}, ${latencyMs === null ? "latency not reported" : `${formatDecimal(latencyMs, latencyMs % 1 === 0 ? 0 : 1)} milliseconds latency`}`);
          const label = element("span", "", gigabits === null ? "not reported" : `${formatDecimal(gigabits, gigabits % 1 === 0 ? 0 : 1)} Gbit/s`);
          label.append(element("small", "", `${latencyMs === null ? "latency not reported" : `${formatDecimal(latencyMs, latencyMs % 1 === 0 ? 0 : 1)} ms`} · assumed`));
          linkButton.append(label);
          linkButton.append(element("span", "wan-packet"));
          linkButton.addEventListener("click", () => openInspectorFor(`link:${link.link_id}`));
        } else {
          linkButton.disabled = true;
          const label = element("span", "", "link not reported");
          label.append(element("small", "", "unmeasured"));
          linkButton.append(label);
        }
        dom.siterail.append(linkButton);
      }
    });

    // Mark sites carrying an assumed scenario interruption. The chip is
    // static text (meaning survives reduced motion); the periodic dim is
    // decoration on top.
    const outages = Array.isArray(scenario.outages) ? scenario.outages : [];
    outages.forEach((outage) => {
      const target = dom.siterail.querySelector(`.site-button[data-site-id="${CSS.escape(String(outage.site_id))}"]`);
      if (!target || target.classList.contains("has-assumed-outage")) return;
      target.classList.add("has-assumed-outage");
      const copy = target.querySelector(".site-copy");
      if (copy) copy.append(element("span", "site-outage-chip", "assumed interruption"));
    });

    window.requestAnimationFrame(() => {
      if (!siteRailInitialized && window.matchMedia("(max-width: 760px)").matches) {
        const requested = state.node.startsWith("site:") ? state.node.slice(5) : "central";
        const siteButtons = [...dom.siterail.querySelectorAll(".site-button")];
        const target = siteButtons.find((button) => button.dataset.siteId === requested) || siteButtons[0];
        if (target) dom.siteviewport.scrollLeft = Math.max(0, target.offsetLeft + target.offsetWidth / 2 - dom.siteviewport.clientWidth / 2);
        siteRailInitialized = true;
      }
      updateSitePosition();
    });
  }

  function updateSitePosition() {
    const siteButtons = [...dom.siterail.querySelectorAll(".site-button")];
    const dots = [...dom.siteposition.children];
    if (!siteButtons.length || !dots.length) return;
    const viewportCenter = dom.siteviewport.scrollLeft + dom.siteviewport.clientWidth / 2;
    let nearestIndex = 0;
    let nearestDistance = Infinity;
    siteButtons.forEach((button, index) => {
      const center = button.offsetLeft + button.offsetWidth / 2;
      const distance = Math.abs(center - viewportCenter);
      if (distance < nearestDistance) {
        nearestDistance = distance;
        nearestIndex = index;
      }
    });
    dots.forEach((dot, index) => dot.classList.toggle("is-active", index === nearestIndex));
  }

  function causalNodes() {
    return artifact && artifact.causal_graph && Array.isArray(artifact.causal_graph.nodes) ? artifact.causal_graph.nodes : CONCEPTUAL_NODES;
  }

  function causalEdges() {
    return artifact && artifact.causal_graph && Array.isArray(artifact.causal_graph.edges) ? artifact.causal_graph.edges : CONCEPTUAL_EDGES;
  }

  function nodeLayout(nodes, mobile) {
    if (mobile) {
      const map = new Map();
      nodes.forEach((node, index) => map.set(node.node_id, { x: 12, y: 18 + index * 96, width: 336, height: 72 }));
      return { width: 360, height: Math.max(696, 34 + nodes.length * 96), map };
    }
    const named = {
      site_availability: { x: 30, y: 38 },
      membership: { x: 310, y: 38 },
      sync_cadence: { x: 310, y: 150 },
      collective_payload: { x: 30, y: 265 },
      mechanical_elapsed_time: { x: 310, y: 265 },
      learning_progress: { x: 590, y: 150 },
      time_to_target: { x: 590, y: 342 },
    };
    const map = new Map();
    nodes.forEach((node, index) => {
      const fallbackColumn = index % 3;
      const fallbackRow = Math.floor(index / 3);
      const point = named[node.node_id] || { x: 30 + fallbackColumn * 280, y: 38 + fallbackRow * 112 };
      map.set(node.node_id, { ...point, width: 220, height: 74 });
    });
    return { width: 840, height: 440, map };
  }

  function causalEdgePath(source, target, mobile) {
    if (mobile) {
      const sx = source.x + source.width / 2;
      const sy = source.y + source.height;
      const tx = target.x + target.width / 2;
      const ty = target.y;
      const bend = (sy + ty) / 2;
      return `M${sx} ${sy}C${sx} ${bend},${tx} ${bend},${tx} ${ty}`;
    }
    const sourceCenter = { x: source.x + source.width / 2, y: source.y + source.height / 2 };
    const targetCenter = { x: target.x + target.width / 2, y: target.y + target.height / 2 };
    const horizontal = Math.abs(targetCenter.x - sourceCenter.x) >= Math.abs(targetCenter.y - sourceCenter.y);
    if (horizontal) {
      const direction = targetCenter.x >= sourceCenter.x ? 1 : -1;
      const sx = sourceCenter.x + direction * source.width / 2;
      const tx = targetCenter.x - direction * target.width / 2;
      const bend = (sx + tx) / 2;
      return `M${sx} ${sourceCenter.y}C${bend} ${sourceCenter.y},${bend} ${targetCenter.y},${tx} ${targetCenter.y}`;
    }
    const direction = targetCenter.y >= sourceCenter.y ? 1 : -1;
    const sy = sourceCenter.y + direction * source.height / 2;
    const ty = targetCenter.y - direction * target.height / 2;
    const bend = (sy + ty) / 2;
    return `M${sourceCenter.x} ${sy}C${sourceCenter.x} ${bend},${targetCenter.x} ${bend},${targetCenter.x} ${ty}`;
  }

  function addSVGEvidenceGlyph(group, kind, x, y) {
    const normalized = normalizedEvidence(kind);
    if (normalized === "prior") {
      group.append(svgElement("path", { class: "glyph-outline", d: `M${x + 4} ${y}h12l7 10-7 10H${x + 4}L${x - 3} ${y + 10}Z` }));
    } else if (normalized === "unmeasured") {
      group.append(svgElement("path", { class: "glyph-outline", d: `M${x + 10} ${y}l10 10-10 10L${x} ${y + 10}Z` }));
    } else if (normalized === "observed") {
      group.append(svgElement("rect", { class: "glyph-outline", x, y, width: 20, height: 20, fill: "url(#observed-hatch)" }));
    } else {
      group.append(svgElement("circle", { class: "glyph-outline", cx: x + 10, cy: y + 10, r: 10 }));
      if (normalized === "assumed") group.append(svgElement("circle", { cx: x + 10, cy: y + 10, r: 3, fill: "none", stroke: "currentColor" }));
    }
  }

  function renderCausalGraph() {
    if (!dom.causalsvg) return;
    const nodes = causalNodes();
    const edges = causalEdges();
    const mobile = window.matchMedia("(max-width: 760px)").matches;
    const layout = nodeLayout(nodes, mobile);
    const svg = dom.causalsvg;
    svg.replaceChildren();
    svg.setAttribute("viewBox", `0 0 ${layout.width} ${layout.height}`);
    svg.setAttribute("height", String(layout.height));

    const title = svgElement("title", { id: "causal-svg-title" });
    title.textContent = "E001 causal graph";
    const description = svgElement("desc", { id: "causal-svg-desc" });
    description.textContent = artifact ? "Artifact-derived causal nodes connect scenario availability, policy mechanics, traffic, elapsed time, an unfitted learning prior, and an unmeasured target." : "The generated artifact is not loaded. This is the schema-level causal path only; result values are not run.";
    svg.append(title, description);

    const defs = svgElement("defs");
    const marker = svgElement("marker", { id: "causal-arrow", viewBox: "0 0 8 8", refX: 7, refY: 4, markerWidth: 6, markerHeight: 6, orient: "auto-start-reverse" });
    marker.append(svgElement("path", { d: "M0 0 8 4 0 8Z", fill: "#596162" }));
    const pattern = svgElement("pattern", { id: "observed-hatch", width: 5, height: 5, patternUnits: "userSpaceOnUse", patternTransform: "rotate(45)" });
    pattern.append(svgElement("line", { x1: 0, y1: 0, x2: 0, y2: 5, stroke: "#2456c4", "stroke-width": 1.5 }));
    defs.append(marker, pattern);
    svg.append(defs);

    const selectedId = state.node.includes(":") ? "" : state.node;
    edges.forEach((edge) => {
      const source = layout.map.get(edge.source);
      const target = layout.map.get(edge.target);
      if (!source || !target) return;
      const path = svgElement("path", {
        class: `causal-edge${selectedId && (edge.source === selectedId || edge.target === selectedId) ? " is-selected" : ""}`,
        d: causalEdgePath(source, target, mobile),
        "marker-end": "url(#causal-arrow)",
        "data-source": edge.source,
        "data-target": edge.target,
      });
      svg.append(path);
      if (!mobile) {
        const sourceCenter = { x: source.x + source.width / 2, y: source.y + source.height / 2 };
        const targetCenter = { x: target.x + target.width / 2, y: target.y + target.height / 2 };
        const label = svgElement("text", { class: "edge-label depth-researcher", x: (sourceCenter.x + targetCenter.x) / 2, y: (sourceCenter.y + targetCenter.y) / 2 - 5 });
        label.textContent = String(edge.relation || "affects");
        svg.append(label);
      }
    });

    if (!artifact) {
      const note = svgElement("text", { class: "empty-label", x: layout.width / 2, y: mobile ? 12 : 18 });
      note.textContent = "ARTIFACT NOT RUN · SCHEMA PATH ONLY";
      svg.append(note);
    }

    const interactiveGroups = [];
    nodes.forEach((node) => {
      const box = layout.map.get(node.node_id);
      if (!box) return;
      const kind = normalizedEvidence(node.evidence_class);
      const group = svgElement("g", {
        class: `causal-node node--${kind}${state.node === node.node_id ? " is-selected" : ""}`,
        "data-node-id": node.node_id,
        transform: `translate(${box.x} ${box.y})`,
        role: "button",
        tabindex: 0,
        "aria-label": `${node.label}, ${EVIDENCE_LABELS[kind]}. ${node[state.depth] || "No explanation reported."}`,
      });
      group.append(svgElement("rect", { class: "node-frame", x: 0, y: 0, width: box.width, height: box.height, rx: 0 }));
      addSVGEvidenceGlyph(group, kind, 14, 15);
      // Wrap long labels onto two lines instead of letting them escape the
      // frame. 13px mono advances ~7.8px per character; 60px is glyph + pad.
      const label = String(node.label);
      const fitChars = Math.max(10, Math.floor((box.width - 60) / 7.8));
      let lines = [label];
      if (label.length > fitChars) {
        const mid = Math.floor(label.length / 2);
        let split = -1;
        for (let off = 0; off < label.length && split < 0; off++) {
          if (mid - off > 0 && label[mid - off] === " ") split = mid - off;
          else if (mid + off < label.length && label[mid + off] === " ") split = mid + off;
        }
        if (split > 0) lines = [label.slice(0, split), label.slice(split + 1)];
      }
      const wrapped = lines.length > 1;
      const titleNode = svgElement("text", { class: "node-title", x: 50, y: wrapped ? 20 : 27 });
      lines.forEach((line, lineIndex) => {
        const span = svgElement("tspan", { x: 50, dy: lineIndex === 0 ? 0 : 15 });
        span.textContent = line;
        titleNode.append(span);
      });
      const evidence = svgElement("text", { class: "node-evidence", x: 50, y: wrapped ? 52 : 47 });
      evidence.textContent = EVIDENCE_LABELS[kind];
      group.append(titleNode, evidence);
      const traceId = svgElement("text", { class: "node-detail depth-full_trace", x: 50, y: wrapped ? 66 : 63 });
      traceId.textContent = String(node.node_id);
      group.append(traceId);
      group.addEventListener("click", () => openInspectorFor(String(node.node_id)));
      interactiveGroups.push(group);
      svg.append(group);
    });

    interactiveGroups.forEach((group, index) => {
      group.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          group.dispatchEvent(new MouseEvent("click", { bubbles: true }));
        } else if (["ArrowRight", "ArrowDown", "ArrowLeft", "ArrowUp"].includes(event.key)) {
          event.preventDefault();
          const delta = event.key === "ArrowRight" || event.key === "ArrowDown" ? 1 : -1;
          interactiveGroups[(index + delta + interactiveGroups.length) % interactiveGroups.length].focus();
        }
      });
    });

    renderCausalFallback(nodes, edges);
  }

  function renderCausalFallback(nodes, edges) {
    dom.causalfallback.replaceChildren();
    if (!artifact) {
      const warning = element("li", "", "Generated artifact unavailable. The following entries are schema-level mechanisms, not result values.");
      dom.causalfallback.append(warning);
    }
    nodes.forEach((node) => {
      const item = element("li");
      const button = element("button", "causal-fallback-button", String(node.label));
      button.type = "button";
      button.addEventListener("click", () => openInspectorFor(String(node.node_id)));
      const incoming = edges.filter((edge) => edge.target === node.node_id).map((edge) => `${edge.source} ${edge.relation || "affects"}`);
      const explanation = element("p", "", String(node[state.depth] || "No explanation reported."));
      const evidence = evidenceTag(node.evidence_class);
      item.append(button, document.createTextNode(" "), evidence, explanation);
      if (incoming.length) item.append(element("small", "", `Incoming: ${incoming.join("; ")}`));
      dom.causalfallback.append(item);
    });
  }

  function artifactRuns() {
    return artifact && Array.isArray(artifact.runs) ? artifact.runs : [];
  }

  function runForPolicy(policy = state.policy) {
    return artifactRuns().find((run) => run.policy === policy) || null;
  }

  function artifactForRun(run) {
    return run && run.experiment_artifact && typeof run.experiment_artifact === "object" ? run.experiment_artifact : null;
  }

  function comparisonCell(value, evidenceClass, note) {
    const cell = element("td");
    cell.append(element("span", "cell-value", value), evidenceTag(evidenceClass));
    if (note) cell.append(element("span", "cell-note", note));
    return cell;
  }

  function emptyComparisonRow(policy) {
    const row = element("tr");
    const policyCell = element("td");
    const button = element("button", "policy-select", policyLabel(policy));
    button.type = "button";
    button.addEventListener("click", () => commitState({ policy }));
    policyCell.append(button, element("span", "cell-note", "artifact not loaded"));
    row.append(policyCell);
    for (let index = 0; index < 6; index += 1) row.append(comparisonCell("not run", "unmeasured", index === 5 ? "no falsifier was evaluated" : "generated artifact required"));
    return row;
  }

  function falsifierCellSummary(run) {
    const runArtifact = artifactForRun(run);
    if (!runArtifact || runArtifact.conclusion === "baseline") return { value: "baseline comparator", evidence: "unmeasured", note: "not a tested policy claim" };
    const falsifiers = Array.isArray(runArtifact.falsifiers) ? runArtifact.falsifiers : [];
    const falsified = falsifiers.filter((result) => result.survived === false).length;
    const survived = falsifiers.filter((result) => result.survived === true).length;
    const unresolved = falsifiers.filter((result) => result.survived !== true && result.survived !== false).length;
    const requirementIds = new Set(Array.isArray(runArtifact.mandatory_requirement_ids) ? runArtifact.mandatory_requirement_ids : []);
    const requirements = (Array.isArray(runArtifact.evidence_requirements) ? runArtifact.evidence_requirements : []).filter((result) => requirementIds.has(result.requirement_id));
    const failedRequirements = requirements.filter((result) => result.status === "failed").length;
    const unresolvedRequirements = requirements.filter((result) => result.status === "unresolved" || result.status === "not_applicable").length;
    const satisfiedRequirements = requirements.filter((result) => result.status === "satisfied").length;
    const scalarNote = `${falsified} scalar failed, ${survived} scalar survived, ${unresolved} scalar unresolved`;
    const structuredNote = `${failedRequirements} structured failed, ${satisfiedRequirements} structured satisfied, ${unresolvedRequirements} structured unresolved`;
    if (runArtifact.conclusion === "failed_virtual_screen") {
      return {
        value: "failed virtual screen",
        evidence: "modeled",
        note: `${scalarNote}; ${structuredNote}. This is not real-world falsification.`,
      };
    }
    if (runArtifact.conclusion === "inconclusive") {
      return {
        value: "inconclusive",
        evidence: "unmeasured",
        note: `${scalarNote}; ${structuredNote}. Every mandatory gate must resolve before survival.`,
      };
    }
    if (runArtifact.conclusion === "survived_virtual_screen") return { value: "survived virtual screen", evidence: "modeled", note: "virtual threshold result; not validation" };
    return { value: conclusionLabel(runArtifact.conclusion), evidence: "unmeasured", note: `${scalarNote}; ${structuredNote}` };
  }

  function renderComparison() {
    dom.comparisonbody.replaceChildren();
    if (!artifact) {
      POLICY_ORDER.forEach((policy) => dom.comparisonbody.append(emptyComparisonRow(policy)));
      dom.comparisonboundary.textContent = "Generated E001 artifact not loaded. Scenario inputs are visible, but all policy result cells remain not run.";
      return;
    }

    const orderedRuns = [...artifactRuns()].sort((a, b) => POLICY_ORDER.indexOf(a.policy) - POLICY_ORDER.indexOf(b.policy));
    orderedRuns.forEach((run) => {
      const row = element("tr");
      row.dataset.policyId = run.policy || "";
      row.classList.toggle("is-selected", run.policy === state.policy);
      const policyCell = element("td");
      const policyButton = element("button", "policy-select", policyLabel(run.policy));
      policyButton.type = "button";
      policyButton.setAttribute("aria-pressed", String(run.policy === state.policy));
      policyButton.addEventListener("click", () => commitState({ policy: run.policy }));
      policyCell.append(policyButton, element("span", "cell-note", run.policy === "adaptive_cadence" ? "operation-boundary controller" : "fixed comparator"));

      const initial = finiteNumber(run.initial_local_steps) ? String(run.initial_local_steps) : "not reported";
      const final = finiteNumber(run.final_local_steps) ? String(run.final_local_steps) : "not reported";
      const cadence = initial === final ? `${initial} local step${initial === "1" ? "" : "s"}` : `${initial} → ${final} local steps`;

      const prior = run.learning_prior && typeof run.learning_prior === "object" ? run.learning_prior : {};
      let progress = finiteNumber(prior.prior_screening_progress_ratio) ? formatRatio(prior.prior_screening_progress_ratio) : "unmeasured";
      let progressNote = "unfitted screening sensitivity; not a held-out metric";
      if (state.uncertainty === "intervals" && finiteNumber(prior.pessimistic_sensitivity_progress_ratio) && finiteNumber(prior.prior_screening_progress_ratio)) {
        progress = `${formatRatio(prior.pessimistic_sensitivity_progress_ratio)} to ${formatRatio(prior.prior_screening_progress_ratio)}`;
        progressNote = "pessimistic-to-point sensitivity span; not a confidence interval";
      }

      const metrics = run.metrics && typeof run.metrics === "object" ? run.metrics : {};
      const targetTime = finiteNumber(prior.prior_projected_time_to_equivalent_progress_ns) ? formatSecondsFromNs(prior.prior_projected_time_to_equivalent_progress_ns) : "unmeasured";
      const targetEvidence = finiteNumber(prior.prior_projected_time_to_equivalent_progress_ns) ? "prior" : "unmeasured";
      const falsifier = falsifierCellSummary(run);

      row.append(
        policyCell,
        comparisonCell(cadence, "modeled", "recorded policy state"),
        comparisonCell(progress, finiteNumber(prior.prior_screening_progress_ratio) ? "prior" : "unmeasured", progressNote),
        comparisonCell(formatBytes(metrics.inter_site_collective_bytes), finiteNumber(metrics.inter_site_collective_bytes) ? "modeled" : "unmeasured", "payload-link bytes; not complete all-reduce traffic"),
        comparisonCell(targetTime, targetEvidence, targetEvidence === "prior" ? "prior-projected equivalent-progress time; not held-out time to target" : "held-out target not measured"),
        comparisonCell(formatEnergy(metrics.modeled_base_and_compute_energy_j), finiteNumber(metrics.modeled_base_and_compute_energy_j) ? "modeled" : "unmeasured", "site base + accelerator compute only; network, checkpoint, storage, and cooling power are excluded"),
        comparisonCell(falsifier.value, falsifier.evidence, falsifier.note),
      );
      dom.comparisonbody.append(row);
    });

    dom.comparisonboundary.textContent = "Timing, payload, and base-plus-compute energy are virtual mechanics. Network, checkpoint, storage, and cooling power are excluded. Learning values are an unfitted sensitivity prior; unsupported falsifiers remain unresolved.";
  }

  function timelineEvents() {
    if (!artifact || !artifact.timeline || typeof artifact.timeline !== "object") return [];
    const events = [];
    Object.entries(artifact.timeline).forEach(([policy, records]) => {
      if (!Array.isArray(records)) return;
      records.forEach((record) => {
        if (!record || typeof record !== "object" || !finiteNumber(record.start_ns) || !finiteNumber(record.end_ns)) return;
        events.push({ ...record, policy: record.policy || policy });
      });
    });
    return events.sort((a, b) => a.start_ns - b.start_ns || a.end_ns - b.end_ns || String(a.event_id).localeCompare(String(b.event_id)) || String(a.policy).localeCompare(String(b.policy)));
  }

  function assignTimelineLanes(events) {
    const laneEnds = [];
    const assigned = events.map((event) => {
      const effectiveEnd = Math.max(event.end_ns, event.start_ns + 1);
      let lane = laneEnds.findIndex((end) => end <= event.start_ns);
      if (lane === -1) {
        lane = laneEnds.length;
        laneEnds.push(effectiveEnd);
      } else {
        laneEnds[lane] = effectiveEnd;
      }
      return { ...event, _lane: lane };
    });
    return { events: assigned, laneCount: Math.max(1, laneEnds.length) };
  }

  function timelineEventEvidence(event) {
    if (event && event.evidence_class) return normalizedEvidence(event.evidence_class);
    return event && (event.kind === "failure" || event.kind === "recovery") ? "assumed" : "modeled";
  }

  function renderTimeline() {
    const svg = dom.timelinesvg;
    svg.replaceChildren();
    timelineScale = null;
    const title = svgElement("title", { id: "timeline-svg-title" });
    title.textContent = "Aligned E001 policy event timeline";
    const description = svgElement("desc", { id: "timeline-svg-desc" });
    svg.append(title, description);

    const allEvents = timelineEvents();
    if (!artifact || !allEvents.length) {
      svg.setAttribute("viewBox", "0 0 1000 210");
      svg.setAttribute("height", "210");
      description.textContent = "No generated event timeline is loaded.";
      const message = svgElement("text", { class: "empty-label", x: 500, y: 105 });
      message.textContent = "EVENT TIMELINE NOT RUN";
      svg.append(message);
      dom.timescrubber.disabled = true;
      dom.previousevent.disabled = true;
      dom.nextevent.disabled = true;
      dom.timelinereadout.textContent = "selected time: not run";
      renderTimelineFallback([]);
      return;
    }

    description.textContent = "Each policy track contains artifact event intervals. Failure and recovery are assumed scenario events; compute, collective, checkpoint, and facility mechanics are modeled.";
    const minNs = Math.min(0, ...allEvents.map((event) => event.start_ns));
    const maxNs = Math.max(...allEvents.map((event) => event.end_ns), minNs + 1);
    const left = 150;
    const right = 980;
    const axisY = 32;
    const scaleX = (value) => left + (value - minNs) / (maxNs - minNs) * (right - left);

    const policyLayouts = [];
    let cursorY = 48;
    POLICY_ORDER.forEach((policy) => {
      const policyEvents = allEvents.filter((event) => event.policy === policy);
      const packed = assignTimelineLanes(policyEvents);
      const rowHeight = Math.max(48, packed.laneCount * 9 + 24);
      policyLayouts.push({ policy, ...packed, top: cursorY, height: rowHeight });
      cursorY += rowHeight + 8;
    });
    const height = cursorY + 18;
    svg.setAttribute("viewBox", `0 0 1000 ${height}`);
    svg.setAttribute("height", String(height));

    const hitArea = svgElement("rect", { x: left, y: axisY, width: right - left, height: height - axisY - 8, fill: "transparent", "pointer-events": "all" });
    hitArea.addEventListener("pointerdown", (event) => {
      const bounds = svg.getBoundingClientRect();
      const x = (event.clientX - bounds.left) / bounds.width * 1000;
      const clamped = Math.min(right, Math.max(left, x));
      const selectedNs = minNs + (clamped - left) / (right - left) * (maxNs - minNs);
      commitState({ time: selectedNs / 1e9 }, { timelineOnly: true });
    });
    svg.append(hitArea);

    svg.append(svgElement("line", { class: "axis-line", x1: left, y1: axisY, x2: right, y2: axisY }));
    const tickCount = 5;
    for (let index = 0; index <= tickCount; index += 1) {
      const fraction = index / tickCount;
      const valueNs = minNs + fraction * (maxNs - minNs);
      const x = left + fraction * (right - left);
      svg.append(svgElement("line", { class: "axis-tick", x1: x, y1: axisY - 5, x2: x, y2: axisY + 5 }));
      const label = svgElement("text", { class: "axis-text", x, y: axisY - 9, "text-anchor": index === 0 ? "start" : index === tickCount ? "end" : "middle" });
      label.textContent = compactTime(valueNs / 1e9);
      svg.append(label);
      if (index > 0 && index < tickCount) svg.append(svgElement("line", { class: "axis-minor", x1: x, y1: axisY + 6, x2: x, y2: height - 12 }));
    }

    const interactive = [];
    policyLayouts.forEach((layout) => {
      const baselineY = layout.top + 14;
      const label = svgElement("text", { class: "policy-label", x: 8, y: baselineY + 4 });
      label.textContent = policyLabel(layout.policy);
      svg.append(label, svgElement("line", { class: "track-line", x1: left, y1: baselineY, x2: right, y2: baselineY }));

      layout.events.forEach((record) => {
        const x = scaleX(record.start_ns);
        const width = Math.max(2, scaleX(record.end_ns) - x);
        const y = layout.top + 20 + record._lane * 9;
        const rect = svgElement("rect", {
          class: `timeline-event${state.policy === record.policy && state.event === String(record.event_id) ? " is-selected" : ""}`,
          x,
          y,
          width,
          height: 7,
          rx: 1,
          tabindex: 0,
          role: "button",
          "data-kind": String(record.kind || "unknown"),
          "aria-label": `${policyLabel(record.policy)}, ${record.event_id}, ${record.kind}, starts ${formatSecondsFromNs(record.start_ns)}, ends ${formatSecondsFromNs(record.end_ns)}, ${EVIDENCE_LABELS[timelineEventEvidence(record)]}`,
        });
        rect.addEventListener("click", (event) => {
          event.stopPropagation();
          openInspectorFor(`timeline:${record.event_id}`, { policy: record.policy, event: String(record.event_id), time: record.start_ns / 1e9 });
        });
        interactive.push({ node: rect, event: record });
        svg.append(rect);
        if ((record.kind === "failure" || record.kind === "recovery" || (state.policy === record.policy && state.event === String(record.event_id))) && width > 24) {
          const direct = svgElement("text", { class: "event-label", x: x + 3, y: y + 6 });
          direct.textContent = String(record.kind).toUpperCase();
          svg.append(direct);
        }
      });
    });

    interactive.forEach((entry, index) => {
      entry.node.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          entry.node.dispatchEvent(new MouseEvent("click", { bubbles: true }));
        } else if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
          event.preventDefault();
          const delta = event.key === "ArrowRight" ? 1 : -1;
          interactive[(index + delta + interactive.length) % interactive.length].node.focus();
        }
      });
    });

    const scrubberLine = svgElement("line", { id: "timeline-scrubber-line", class: "scrubber-line", x1: left, x2: left, y1: axisY - 3, y2: height - 12 });
    const scrubberHandle = svgElement("circle", { id: "timeline-scrubber-handle", class: "scrubber-handle", cx: left, cy: axisY - 3, r: 4.5 });
    svg.append(scrubberLine, scrubberHandle);
    timelineScale = { minSeconds: minNs / 1e9, maxSeconds: maxNs / 1e9, left, right, height };

    dom.timescrubber.disabled = false;
    dom.timescrubber.min = String(timelineScale.minSeconds);
    dom.timescrubber.max = String(timelineScale.maxSeconds);
    dom.timescrubber.step = String(Math.max(0.001, (timelineScale.maxSeconds - timelineScale.minSeconds) / 2000));
    dom.previousevent.disabled = false;
    dom.nextevent.disabled = false;
    updateTimelineScrubber();
    renderTimelineFallback(allEvents);
  }

  function updateTimelineScrubber() {
    if (!timelineScale) {
      dom.timelinereadout.textContent = "selected time: not run";
      return;
    }
    const clamped = Math.min(timelineScale.maxSeconds, Math.max(timelineScale.minSeconds, state.time));
    if (clamped !== state.time) {
      state = sanitizeState({ ...state, time: clamped });
      writeStateToURL(true);
    }
    const span = timelineScale.maxSeconds - timelineScale.minSeconds || 1;
    const x = timelineScale.left + (clamped - timelineScale.minSeconds) / span * (timelineScale.right - timelineScale.left);
    const line = byId("timeline-scrubber-line");
    const handle = byId("timeline-scrubber-handle");
    if (line) {
      line.setAttribute("x1", String(x));
      line.setAttribute("x2", String(x));
    }
    if (handle) handle.setAttribute("cx", String(x));
    dom.timescrubber.value = String(clamped);
    dom.timelinereadout.textContent = `selected time: ${formatSeconds(clamped, clamped < 10 ? 3 : 1)}`;
  }

  function selectAdjacentEvent(direction) {
    const events = timelineEvents().filter((event) => event.policy === state.policy);
    if (!events.length) return;
    let index = events.findIndex((event) => String(event.event_id) === state.event);
    if (index < 0) {
      index = events.findIndex((event) => event.start_ns / 1e9 >= state.time);
      if (index < 0) index = events.length - 1;
    } else {
      index = (index + direction + events.length) % events.length;
    }
    const selected = events[index];
    openInspectorFor(`timeline:${selected.event_id}`, { event: String(selected.event_id), time: selected.start_ns / 1e9 });
  }

  function renderTimelineFallback(events) {
    dom.timelinefallback.replaceChildren();
    if (!events.length) {
      dom.timelinefallback.append(element("p", "", "No generated event records are available."));
      return;
    }
    const selectedPolicyEvents = events.filter((event) => event.policy === state.policy);
    const table = element("table", "timeline-event-table");
    const caption = element("caption", "visually-hidden", `${policyLabel(state.policy)} event records`);
    const head = element("thead");
    const headRow = element("tr");
    ["Event ID", "Kind", "Start", "End", "Location", "Evidence"].forEach((label) => headRow.append(element("th", "", label)));
    head.append(headRow);
    const body = element("tbody");
    selectedPolicyEvents.forEach((record) => {
      const row = element("tr");
      const idCell = element("td");
      const button = element("button", "policy-select", String(record.event_id));
      button.type = "button";
      button.addEventListener("click", () => openInspectorFor(`timeline:${record.event_id}`, { event: String(record.event_id), time: record.start_ns / 1e9 }));
      idCell.append(button);
      row.append(
        idCell,
        element("td", "", String(record.kind || "unknown")),
        element("td", "", formatSecondsFromNs(record.start_ns)),
        element("td", "", formatSecondsFromNs(record.end_ns)),
        element("td", "", String(record.location || "not reported")),
        element("td", "", EVIDENCE_LABELS[timelineEventEvidence(record)]),
      );
      body.append(row);
    });
    table.append(caption, head, body);
    dom.timelinefallback.append(table);
  }

  function copyIcon() {
    const svg = svgElement("svg", { viewBox: "0 0 20 20", "aria-hidden": "true" });
    svg.append(
      svgElement("rect", { x: 6, y: 5, width: 10, height: 12, rx: 1 }),
      svgElement("path", { d: "M4 14H3a1 1 0 0 1-1-1V3a1 1 0 0 1 1-1h9a1 1 0 0 1 1 1v1" }),
    );
    return svg;
  }

  function copyButton(value, label, className = "copy-source") {
    const button = element("button", `icon-button ${className}`);
    button.type = "button";
    button.setAttribute("aria-label", label);
    button.append(copyIcon());
    button.addEventListener("click", () => copyText(value, `${label} copied.`));
    return button;
  }

  function inspectorLead(value, evidenceClass, note) {
    const lead = element("div", "inspector-lead");
    lead.append(element("p", "inspector-value", value), evidenceTag(evidenceClass));
    if (note) lead.append(element("p", "cell-note", note));
    return lead;
  }

  function inspectorSection(title, ...children) {
    const section = element("section", "inspector-section");
    const researcherTitles = new Set(["Mechanism", "Policy rule", "Uncertainty", "What it changes", "Controller boundary", "Known transfer limit", "Transfer limit", "Preregistered falsifier", "Source"]);
    const fullTraceTitles = new Set(["Exact event record", "Event metadata", "Source observations", "Residual attribution"]);
    if (researcherTitles.has(title)) section.classList.add("depth-researcher");
    if (fullTraceTitles.has(title)) section.classList.add("depth-full_trace");
    section.append(element("h3", "", title));
    children.forEach((child) => {
      if (child === null || child === undefined) return;
      section.append(typeof child === "string" ? element("p", "", child) : child);
    });
    return section;
  }

  function factList(entries) {
    const list = element("dl", "inspector-facts");
    entries.forEach(([term, value]) => {
      list.append(element("dt", "", term), element("dd", "", value));
    });
    return list;
  }

  function sourceIdList(ids) {
    const wrapper = element("div");
    if (!Array.isArray(ids) || !ids.length) {
      wrapper.append(element("p", "", "No source observation ID is attached."));
      return wrapper;
    }
    ids.forEach((id) => {
      const row = element("div", "source-id-row");
      const copy = element("div");
      copy.append(element("code", "", String(id)));
      const observation = observationById(id);
      const provenance = observation && observation.provenance && typeof observation.provenance === "object" ? observation.provenance : null;
      if (provenance && typeof provenance.uri === "string" && provenance.uri) {
        const link = element("a", "cell-note", `Open ${String(provenance.citation || "source provenance")}`);
        link.href = provenance.uri;
        link.target = "_blank";
        link.rel = "noreferrer";
        copy.append(link);
      } else {
        copy.append(element("span", "cell-note", "Observation payload unavailable from artifact"));
      }
      row.append(copy, copyButton(String(id), "Copy observation ID"));
      wrapper.append(row);
    });
    return wrapper;
  }

  function observationById(observationId) {
    if (!artifact || !Array.isArray(artifact.observations)) return null;
    return artifact.observations.find((observation) => observation && observation.observation_id === observationId) || null;
  }

  function selectedEntity() {
    const scenario = scenarioData();
    if (state.node.startsWith("site:")) {
      const id = state.node.slice(5);
      const site = Array.isArray(scenario.sites) ? scenario.sites.find((candidate) => String(candidate.site_id) === id) : null;
      if (site) return { type: "site", value: site };
    }
    if (state.node.startsWith("link:")) {
      const id = state.node.slice(5);
      const link = Array.isArray(scenario.links) ? scenario.links.find((candidate) => String(candidate.link_id) === id) : null;
      if (link) return { type: "link", value: link };
    }
    if (state.node.startsWith("timeline:")) {
      const id = state.node.slice(9);
      const record = timelineEvents().find((candidate) => candidate.policy === state.policy && String(candidate.event_id) === id);
      if (record) return { type: "timeline", value: record };
    }
    if (state.node.startsWith("event:")) {
      const id = state.node.slice(6);
      const outage = Array.isArray(scenario.outages) ? scenario.outages.find((candidate) => String(candidate.event_id) === id) : null;
      if (outage) return { type: "outage", value: outage };
    }
    const causal = causalNodes().find((candidate) => String(candidate.node_id) === state.node);
    if (causal) return { type: "causal", value: causal };
    const defaultOutage = Array.isArray(scenario.outages) ? scenario.outages.find((candidate) => candidate.event_id === "central-curtailment-1") : null;
    return defaultOutage ? { type: "outage", value: defaultOutage } : { type: "none", value: null };
  }

  function renderInspector() {
    dom.evidenceinspector.classList.toggle("is-transient", transientInspector);
    dom.evidenceinspector.classList.toggle("is-hidden", inspectorHidden);
    dom.researchBand.classList.toggle("inspector-hidden", inspectorHidden);
    dom.evidenceinspector.setAttribute("aria-hidden", String(inspectorHidden));
    if (inspectorHidden) return;

    const entity = selectedEntity();
    dom.inspectorbody.replaceChildren();
    if (entity.type === "outage") renderOutageInspector(entity.value);
    else if (entity.type === "site") renderSiteInspector(entity.value);
    else if (entity.type === "link") renderLinkInspector(entity.value);
    else if (entity.type === "timeline") renderTimelineInspector(entity.value);
    else if (entity.type === "causal") renderCausalInspector(entity.value);
    else {
      dom.inspectortitle.textContent = "No evidence selected";
      dom.inspectorbody.append(inspectorLead("unmeasured", "unmeasured", "Select a site, link, event, mechanism, or falsifier."));
    }
  }

  function renderOutageInspector(outage) {
    dom.inspectortitle.textContent = String(outage.event_id);
    const durationNs = finiteNumber(outage.duration_ns) ? outage.duration_ns : finiteNumber(outage.recovery_ns) && finiteNumber(outage.failure_start_ns) ? outage.recovery_ns - outage.failure_start_ns : null;
    dom.inspectorbody.append(
      inspectorLead(formatSecondsFromNs(durationNs, { fixed: 1 }), "assumed", "screening scenario event"),
      inspectorSection("Exact scenario interval", factList([
        ["Site", String(outage.site_id || "not reported")],
        ["Starts", formatSecondsFromNs(outage.failure_start_ns, { fixed: 1 })],
        ["Recovers", formatSecondsFromNs(outage.recovery_ns, { fixed: 1 })],
        ["Cause", String(outage.cause || "not reported")],
        ["Evidence", "ASSUMED · no measured outage trace"],
      ])),
      inspectorSection("Plain meaning", `${String(outage.site_id || "The selected site")} is unavailable for the assumed interval. The virtual mechanics engine can show how scheduled operations wait around that interval.`),
      inspectorSection("What it changes", "The scenario blocks the site's operational resources. Compute, collective, state movement, and checkpoint events that overlap the interval are mechanically postponed."),
      inspectorSection("Controller boundary", "The current controller does not observe an active outage or issue a failure-response membership decision. It adapts synchronization cadence only after a completed communication cycle."),
      inspectorSection("Known transfer limit", "Whole operations move after an overlapping interruption. Preemption, lost work, checkpoint recovery, repair-time distributions, and resumable mid-operation control are not modeled."),
      inspectorSection("Source", "Scenario input. No source observation ID or fleet failure model is attached."),
    );
  }

  function renderSiteInspector(site) {
    dom.inspectortitle.textContent = `${String(site.site_id).toUpperCase()} site`;
    const acceleratorCount = finiteNumber(site.accelerator_count) ? site.accelerator_count.toLocaleString("en-US") : "not reported";
    dom.inspectorbody.append(
      inspectorLead(`${acceleratorCount} × ${String(site.accelerator_type || "accelerator type not reported")}`, "assumed", "screening scenario configuration"),
      inspectorSection("Exact scenario input", factList([
        ["Accelerator", String(site.accelerator_type || "not reported")],
        ["Count", acceleratorCount],
        ["Sustained rate / GPU", formatRate(site.accelerator_flops_per_second)],
        ["Power cap", artifact ? formatPower(site.power_cap_w) : "not exposed before artifact load"],
        ["Allocated power", "not reported by site"],
      ])),
      inspectorSection("Plain meaning", "This site is one member of the three-site screening scenario. Its accelerator count and sustained rate are assumptions, not an observed deployment."),
      inspectorSection("Evidence boundary", "The assumed 500 TFLOP/s sustained training rate is distinct from a vendor peak specification. GPUSTACK does not attach a measured utilization trace to this site yet."),
      inspectorSection("Transfer limit", "A per-site allocated-power trace is not reported in the observatory artifact. The run-level peak is not redistributed into invented site values."),
    );
  }

  function renderLinkInspector(link) {
    dom.inspectortitle.textContent = String(link.link_id);
    const gigabits = finiteNumber(link.bandwidth_bytes_per_second) ? link.bandwidth_bytes_per_second * 8 / 1e9 : null;
    const latencyMs = finiteNumber(link.latency_ns) ? link.latency_ns / 1e6 : null;
    dom.inspectorbody.append(
      inspectorLead(gigabits === null ? "not reported" : `${formatDecimal(gigabits, gigabits % 1 === 0 ? 0 : 1)} Gbit/s`, "assumed", "dedicated payload bandwidth"),
      inspectorSection("Exact scenario input", factList([
        ["Endpoints", `${String(link.site_a || "?")} ↔ ${String(link.site_b || "?")}`],
        ["Payload bandwidth", gigabits === null ? "not reported" : `${formatDecimal(gigabits, gigabits % 1 === 0 ? 0 : 1)} Gbit/s`],
        ["One-way latency", latencyMs === null ? "not reported" : `${formatDecimal(latencyMs, latencyMs % 1 === 0 ? 0 : 1)} ms`],
        ["Scenario availability", typeof link.available === "boolean" ? String(link.available) : "not reported"],
      ])),
      inspectorSection("Plain meaning", "This WAN link limits how quickly the modeled collective payload can cross between adjacent sites."),
      inspectorSection("Mechanism", "The event engine reserves link bandwidth and includes the scenario latency. It reports payload-link bytes rather than claiming a complete algorithm-specific all-reduce byte count."),
      inspectorSection("Transfer limit", "Bandwidth is dedicated and fixed in this screen. Congestion, packet loss, routing changes, protocol overhead, and observed WAN variability are not attached."),
    );
  }

  function metricForCausalNode(node) {
    if (!artifact) return { value: "not run", evidence: "unmeasured", note: "generated experiment artifact required" };
    const run = runForPolicy();
    if (!run) return { value: "not run", evidence: "unmeasured", note: "selected policy is absent from the artifact" };
    const metrics = run.metrics && typeof run.metrics === "object" ? run.metrics : {};
    const prior = run.learning_prior && typeof run.learning_prior === "object" ? run.learning_prior : {};
    if (node.node_id === "site_availability") {
      const outage = Array.isArray(artifact.scenario.outages) ? artifact.scenario.outages[0] : null;
      return outage ? { value: formatSecondsFromNs(outage.duration_ns), evidence: "assumed", note: "scenario interruption interval" } : { value: "not reported", evidence: "unmeasured", note: "no outage interval attached" };
    }
    if (node.node_id === "membership") return { value: "unmeasured", evidence: "unmeasured", note: "reactive active-outage membership is not implemented" };
    if (node.node_id === "sync_cadence") {
      const initial = finiteNumber(run.initial_local_steps) ? String(run.initial_local_steps) : "?";
      const final = finiteNumber(run.final_local_steps) ? String(run.final_local_steps) : "?";
      return { value: initial === final ? `${initial} local step${initial === "1" ? "" : "s"}` : `${initial} → ${final} local steps`, evidence: "modeled", note: "recorded operation-boundary policy state" };
    }
    if (node.node_id === "collective_payload") return { value: formatBytes(metrics.inter_site_collective_bytes), evidence: finiteNumber(metrics.inter_site_collective_bytes) ? "modeled" : "unmeasured", note: "sum of modeled payload-link bytes" };
    if (node.node_id === "mechanical_elapsed_time") return { value: formatSecondsFromNs(run.elapsed_ns), evidence: finiteNumber(run.elapsed_ns) ? "modeled" : "unmeasured", note: "mechanical elapsed interval" };
    if (node.node_id === "learning_progress") {
      if (!finiteNumber(prior.prior_screening_progress_ratio)) return { value: "unmeasured", evidence: "unmeasured", note: "learning prior value not reported" };
      const value = state.uncertainty === "intervals" && finiteNumber(prior.pessimistic_sensitivity_progress_ratio) ? `${formatRatio(prior.pessimistic_sensitivity_progress_ratio)} to ${formatRatio(prior.prior_screening_progress_ratio)}` : formatRatio(prior.prior_screening_progress_ratio);
      return { value, evidence: "prior", note: state.uncertainty === "intervals" ? "sensitivity span, not a confidence interval" : "unfitted prior point" };
    }
    if (node.node_id === "time_to_target") return { value: "unmeasured", evidence: "unmeasured", note: "no held-out target observation exists" };
    return { value: "unmeasured", evidence: normalizedEvidence(node.evidence_class), note: "no direct metric projection is defined" };
  }

  function mechanismForNode(nodeId) {
    const mechanisms = {
      site_availability: "Failure and recovery timestamps are fixed scenario inputs. The event engine reserves the affected site's operational resources over that interval.",
      membership: "No reactive active-outage membership rule is implemented in E001's current mechanics screen.",
      sync_cadence: "After a completed synchronization cycle, the controller reads communication-phase fraction. High pressure can double local steps; low pressure can halve them within configured bounds. It does not react to an active outage.",
      collective_payload: "modeled_collective_payload_link_bytes = sum of one gradient payload per modeled WAN link and synchronization cycle.",
      mechanical_elapsed_time: "Successive epochs enforce compute before collective, share explicit resources, and postpone a whole overlapping operation around an assumed outage.",
      learning_progress: "screening progress ratio = 1 / (1 + sensitivity × (local_steps − 1)^exponent). Sensitivity is an assumed transform seeded by one-step final-loss observations, not a fitted calibration.",
      time_to_target: "No equation can resolve held-out time to target without an observed learning response. A prior-projected equivalent-progress time may be inspected as sensitivity only.",
    };
    return mechanisms[nodeId] || "No mechanism text is reported for this node.";
  }

  function uncertaintyForEvidence(evidenceClass) {
    const kind = normalizedEvidence(evidenceClass);
    if (kind === "prior") return "The displayed span varies an assumed sensitivity. It is not a confidence interval, posterior, or run-to-run variance estimate.";
    if (kind === "modeled") return "No statistical interval is attached. The value is deterministic under the current scenario and engine assumptions.";
    if (kind === "assumed") return "The exact input is fixed by the scenario. It is not an estimate of real-world incidence or variability.";
    if (kind === "observed") return "Measurement bounds and their semantics are read from the attached observation artifact. A publication-rounding interval is not run-to-run variance.";
    return "No observation exists, so no interval, residual, or coverage statement can be computed.";
  }

  function falsifierForNode(nodeId, run) {
    const mapping = { learning_progress: "e001-progress", collective_payload: "e001-wan", time_to_target: "e001-time" };
    const falsifierId = mapping[nodeId];
    const runArtifact = artifactForRun(run);
    if (!falsifierId || !runArtifact || !Array.isArray(runArtifact.falsifiers)) return null;
    return runArtifact.falsifiers.find((candidate) => candidate.falsifier_id === falsifierId) || null;
  }

  function evidenceRequirementsForMetric(metric, run) {
    const runArtifact = artifactForRun(run);
    if (!metric || !runArtifact || !artifact || !artifact.protocol) return [];
    const specs = Array.isArray(artifact.protocol.evidence_requirements) ? artifact.protocol.evidence_requirements : [];
    const results = new Map((Array.isArray(runArtifact.evidence_requirements) ? runArtifact.evidence_requirements : []).map((result) => [result.requirement_id, result]));
    return specs
      .filter((spec) => spec.mandatory === true && Array.isArray(spec.required_metrics) && spec.required_metrics.includes(metric))
      .map((spec) => ({ spec, result: results.get(spec.requirement_id) || null }));
  }

  function learningTransferBoundary() {
    if (!artifact || !Array.isArray(artifact.observations) || !artifact.observations.length) return "Source observation payloads are unavailable from the current artifact, so the transfer boundary cannot be enumerated from evidence.";
    const parameterCounts = [...new Set(artifact.observations.map((observation) => observation && observation.workload && observation.workload.parameters).filter(finiteNumber))].map(formatParameterCount);
    const optimizers = [...new Set(artifact.observations.map((observation) => observation && observation.workload && observation.workload.optimizer).filter((value) => typeof value === "string" && value))];
    const delays = [...new Set(artifact.observations.map((observation) => observation && observation.topology && observation.topology.gradient_delay_steps).filter(finiteNumber))].sort((a, b) => a - b);
    const scenarioParameters = artifact.scenario && artifact.scenario.metadata ? artifact.scenario.metadata.model_parameters : null;
    const observedScope = `${parameterCounts.length ? parameterCounts.join(", ") : "unreported-size"} ${optimizers.length ? optimizers.join(", ") : "optimizer-unreported"} at delay steps ${delays.length ? delays.join(", ") : "not reported"}`;
    const targetScope = finiteNumber(scenarioParameters) ? formatParameterCount(scenarioParameters) : "the scenario scale";
    return `Attached observations cover ${observedScope}. They do not validate longer local intervals, transfer to ${targetScope}, or multi-site interruption behavior.`;
  }

  function renderCausalInspector(node) {
    const kind = normalizedEvidence(node.evidence_class);
    const metric = metricForCausalNode(node);
    const run = runForPolicy();
    const falsifier = falsifierForNode(node.node_id, run);
    const scenario = scenarioData();
    const prior = scenario.learning_prior && typeof scenario.learning_prior === "object" ? scenario.learning_prior : {};
    dom.inspectortitle.textContent = String(node.label);
    dom.inspectorbody.append(
      inspectorLead(metric.value, metric.evidence, metric.note),
      inspectorSection("Plain meaning", String(node[state.depth] || node.freshman || "No explanation reported.")),
      inspectorSection("Evidence class", `${EVIDENCE_LABELS[kind]}. ${uncertaintyForEvidence(kind)}`),
      inspectorSection(node.node_id === "sync_cadence" ? "Policy rule" : "Mechanism", element("p", "inspector-code", mechanismForNode(node.node_id))),
    );

    if (node.node_id === "learning_progress") {
      dom.inspectorbody.append(inspectorSection("Source observations", sourceIdList(Array.isArray(prior.seed_observation_ids) ? prior.seed_observation_ids : [])));
    } else {
      dom.inspectorbody.append(inspectorSection("Source", node.node_id === "site_availability" ? "E001 scenario input; no observed fleet trace." : "E001 virtual datacenter artifact and preregistered protocol."));
    }

    const boundaryText = node.node_id === "collective_payload" ? "Payload-link bytes omit complete algorithm-specific collective traffic and protocol overhead." : node.node_id === "mechanical_elapsed_time" ? "Preemption, lost work, checkpoint recovery, and resumable mid-operation control are not modeled." : node.node_id === "learning_progress" || node.node_id === "time_to_target" ? learningTransferBoundary() : "The value does not transfer beyond the explicit scenario and supported result scope without new evidence.";
    dom.inspectorbody.append(inspectorSection("Known transfer limit", boundaryText));

    if (falsifier) {
      const status = falsifier.survived === true ? "survived virtual screen" : falsifier.survived === false ? "failed virtual screen gate" : "unresolved";
      dom.inspectorbody.append(inspectorSection("Preregistered falsifier", factList([
        ["ID", String(falsifier.falsifier_id)],
        ["Metric", String(falsifier.metric)],
        ["Reported value", finiteNumber(falsifier.observed_value) ? formatRatio(falsifier.observed_value) : "unmeasured"],
        ["Status", status],
        ["Reason", String(falsifier.reason || "not reported")],
      ])));
      const requirements = evidenceRequirementsForMetric(falsifier.metric, run);
      if (requirements.length) {
        dom.inspectorbody.append(inspectorSection("Structured evidence requirements", factList(requirements.map(({ spec, result }) => [
          String(spec.requirement_id),
          `${result && result.status ? String(result.status).replaceAll("_", " ") : "unresolved"}: ${result && result.reason ? result.reason : String(spec.evidence_boundary || "no evidence attached")}`,
        ]))));
      }
    }

    if (node.node_id === "learning_progress" || node.node_id === "time_to_target") {
      dom.inspectorbody.append(inspectorSection("Residual attribution", "No held-out multi-site learning observation exists. Residual attribution is not computable."));
    }
  }

  function renderTimelineInspector(record) {
    const evidenceClass = timelineEventEvidence(record);
    dom.inspectortitle.textContent = String(record.event_id);
    const intervalNs = record.end_ns - record.start_ns;
    const metadata = record.metadata && typeof record.metadata === "object" ? record.metadata : {};
    const metadataCode = element("pre", "inspector-code", JSON.stringify(metadata, null, 2));
    dom.inspectorbody.append(
      inspectorLead(formatSecondsFromNs(intervalNs), evidenceClass, `${String(record.kind || "unknown")} event · ${policyLabel(record.policy)}`),
      inspectorSection("Exact event record", factList([
        ["Policy", policyLabel(record.policy)],
        ["Kind", String(record.kind || "not reported")],
        ["Starts", formatSecondsFromNs(record.start_ns)],
        ["Ends", formatSecondsFromNs(record.end_ns)],
        ["Scheduled duration", formatSecondsFromNs(record.duration_ns)],
        ["Resource wait", formatSecondsFromNs(record.wait_ns)],
        ["Location", String(record.location || "not reported")],
        ["Epoch", finiteNumber(record.epoch_index) ? String(record.epoch_index) : "not reported"],
      ])),
      inspectorSection("Plain meaning", EVENT_MEANINGS[record.kind] || "The artifact records this interval without an additional human explanation."),
      inspectorSection("Uncertainty", uncertaintyForEvidence(evidenceClass)),
      inspectorSection("Event metadata", metadataCode),
    );
    if (record.kind === "failure" || record.kind === "recovery") {
      dom.inspectorbody.append(inspectorSection("Controller boundary", "The active interruption is a scenario event. The current E001 controller does not detect it or issue a failure-response membership decision; cadence changes follow completed communication cycles only."));
    }
    dom.inspectorbody.append(inspectorSection("Known transfer limit", "An event interval demonstrates virtual ordering and contention. It is not an observed production trace, and it does not validate training quality."));
  }

  function formatParameterCount(value) {
    if (!finiteNumber(value)) return "model size not reported";
    if (Math.abs(value) >= 1e9) return `${(value / 1e9).toLocaleString("en-US", { maximumFractionDigits: 2 })}B`;
    if (Math.abs(value) >= 1e6) return `${(value / 1e6).toLocaleString("en-US", { maximumFractionDigits: 1 })}M`;
    return value.toLocaleString("en-US");
  }

  function observationLabel(observation) {
    const workload = observation.workload && typeof observation.workload === "object" ? observation.workload : {};
    const topology = observation.topology && typeof observation.topology === "object" ? observation.topology : {};
    const optimizer = String(workload.optimizer || "optimizer not reported");
    const size = formatParameterCount(workload.parameters);
    const delay = finiteNumber(topology.gradient_delay_steps) ? topology.gradient_delay_steps : null;
    const delayLabel = delay === null ? "delay not reported" : delay === 0 ? "synchronous" : `${delay}-step delay`;
    const feedback = workload.error_feedback === true ? " + error feedback" : "";
    return `${optimizer} · ${size} · ${delayLabel}${feedback}`;
  }

  function humanMetricName(metric) {
    return String(metric || "measurement").replaceAll("_", " ");
  }

  function observationUncertaintyText(measurement) {
    const uncertainty = measurement && measurement.uncertainty && typeof measurement.uncertainty === "object" ? measurement.uncertainty : {};
    const metadata = measurement && measurement.metadata && typeof measurement.metadata === "object" ? measurement.metadata : {};
    const decimalPlaces = Number.isInteger(metadata.reported_precision_decimal_places) ? metadata.reported_precision_decimal_places : 3;
    if (finiteNumber(uncertainty.lower_bound) && finiteNumber(uncertainty.upper_bound)) {
      const halfWidth = Math.abs(uncertainty.upper_bound - uncertainty.lower_bound) / 2;
      const interval = `${formatDecimal(uncertainty.lower_bound, decimalPlaces + 1)} to ${formatDecimal(uncertainty.upper_bound, decimalPlaces + 1)}`;
      const rounding = typeof uncertainty.notes === "string" && uncertainty.notes.toLowerCase().includes("rounding");
      return `${interval} · ${rounding ? `±${formatDecimal(halfWidth, decimalPlaces + 1)} rounding` : "reported bounds"}`;
    }
    if (finiteNumber(uncertainty.standard_deviation)) return `σ ${formatDecimal(uncertainty.standard_deviation, decimalPlaces + 1)}`;
    return "uncertainty unavailable";
  }

  function missingObservationRow(observationId, message) {
    const row = element("tr");
    const idCell = element("td", "observation-name");
    idCell.append(element("code", "", String(observationId)), element("small", "", message));
    const value = element("td", "observation-value");
    value.append(element("strong", "", "unavailable"), element("small", "", "no value copied into the browser"));
    const evidence = element("td");
    evidence.append(evidenceTag("unmeasured"), element("span", "cell-note", "observation payload absent"));
    row.append(idCell, value, evidence, element("td"));
    return row;
  }

  function renderSourceObservations() {
    dom.sourceobservationbody.replaceChildren();
    if (!artifact) {
      renderSourceChainState(0);
      dom.sourceobservationbody.append(missingObservationRow("source observations", "source observations unavailable from the current artifact"));
      return;
    }

    const observations = Array.isArray(artifact.observations) ? artifact.observations : [];
    renderSourceChainState(observations.length);
    observations.forEach((observation) => {
      const row = element("tr");
      const measuredValues = observation.measured_values && typeof observation.measured_values === "object" ? observation.measured_values : {};
      const metricEntry = Object.entries(measuredValues)[0];
      const metric = metricEntry ? metricEntry[0] : "measurement";
      const measurement = metricEntry && metricEntry[1] && typeof metricEntry[1] === "object" ? metricEntry[1] : null;
      const provenance = observation.provenance && typeof observation.provenance === "object" ? observation.provenance : {};
      const name = element("td", "observation-name");
      const label = observationLabel(observation);
      if (typeof provenance.uri === "string" && provenance.uri) {
        const link = element("a", "", label);
        link.href = provenance.uri;
        link.target = "_blank";
        link.rel = "noreferrer";
        name.append(link);
      } else {
        name.append(element("strong", "", label));
      }
      name.append(element("small", "", String(provenance.citation || observation.observation_id || "provenance not reported")));

      const value = element("td", "observation-value");
      if (measurement && finiteNumber(measurement.value)) {
        const precision = measurement.metadata && Number.isInteger(measurement.metadata.reported_precision_decimal_places) ? measurement.metadata.reported_precision_decimal_places : 3;
        const unit = typeof measurement.unit === "string" && measurement.unit !== "1" ? ` (${measurement.unit})` : "";
        value.append(
          element("strong", "", `${formatDecimal(measurement.value, precision)} ${humanMetricName(metric)}${unit}`),
          element("small", "", observationUncertaintyText(measurement)),
        );
      } else {
        value.append(element("strong", "", "unavailable"), element("small", "", "measured value missing from artifact"));
      }
      const evidence = element("td");
      evidence.append(evidenceTag(measurement ? "observed" : "unmeasured"), element("span", "cell-note", measurement ? "artifact observation; run-to-run variance only if reported" : "observation payload incomplete"));
      const action = element("td");
      if (typeof observation.observation_id === "string" && observation.observation_id) action.append(copyButton(observation.observation_id, "Copy observation ID", "copy-observation"));
      row.append(name, value, evidence, action);
      dom.sourceobservationbody.append(row);
    });

    const missingIds = Array.isArray(artifact.missing_observation_ids) ? artifact.missing_observation_ids : [];
    missingIds.forEach((id) => dom.sourceobservationbody.append(missingObservationRow(id, "referenced ID missing from artifact observations")));
    if (!observations.length && !missingIds.length) dom.sourceobservationbody.append(missingObservationRow("no observation ID reported", "artifact contains no source observations"));
  }

  function renderSourceChainState(observationCount) {
    const observed = observationCount > 0;
    dom.sourcechainitem.classList.toggle("evidence-observed", observed);
    dom.sourcechainitem.classList.toggle("evidence-unmeasured", !observed);
    dom.sourcechainitem.querySelector(".evidence-glyph")?.replaceWith(evidenceGlyph(observed ? "observed" : "unmeasured"));
    dom.sourcechainlabel.textContent = observed ? `${observationCount} source observation${observationCount === 1 ? "" : "s"}` : "Source observations";
    dom.sourcechainevidence.textContent = observed ? "OBSERVED" : "UNMEASURED · UNAVAILABLE FROM ARTIFACT";
  }

  function renderPriorParameters() {
    dom.priorparameters.replaceChildren();
    const prior = artifact && artifact.scenario && artifact.scenario.learning_prior ? artifact.scenario.learning_prior : null;
    const entries = prior ? [
      ["Prior ID", String(prior.prior_id || "not reported")],
      ["Sensitivity", finiteNumber(prior.staleness_sensitivity) ? `${prior.staleness_sensitivity} · ASSUMED TRANSFORM` : "unmeasured"],
      ["Sensitivity scale", finiteNumber(prior.sensitivity_scale) ? `${prior.sensitivity_scale} · ASSUMED TRANSFORM` : "unmeasured"],
      ["Exponent", finiteNumber(prior.staleness_exponent) ? `${prior.staleness_exponent} · ASSUMED TRANSFORM` : "unmeasured"],
      ["Evidence status", String(prior.evidence_status || "screening_prior_not_fitted")],
    ] : [
      ["Prior ID", "artifact not run"],
      ["Sensitivity", "not run"],
      ["Sensitivity scale", "not run"],
      ["Exponent", "not run"],
      ["Evidence status", "PRIOR · NOT FITTED"],
    ];
    entries.forEach(([term, value]) => dom.priorparameters.append(element("dt", "", term), element("dd", "", value)));
  }

  function ledgerRow(values) {
    const row = element("tr");
    values.forEach((value) => row.append(element("td", "", value)));
    return row;
  }

  function renderDecisionLedger() {
    dom.decisionledgerbody.replaceChildren();
    const run = runForPolicy("adaptive_cadence");
    if (!artifact || !run) {
      const row = ledgerRow(["not run", "artifact unavailable", "not run", "not run", "UNMEASURED"]);
      dom.decisionledgerbody.append(row);
      return;
    }
    const cycles = Array.isArray(run.sync_cycles) ? run.sync_cycles : [];
    dom.decisionledgerbody.append(ledgerRow([
      "startup",
      "no completed-cycle history",
      `begin with local steps ${finiteNumber(run.initial_local_steps) ? run.initial_local_steps : "not reported"}`,
      "first compute epoch",
      "MODELED POLICY",
    ]));
    let changeCount = 0;
    for (let index = 1; index < cycles.length; index += 1) {
      const previous = cycles[index - 1];
      const current = cycles[index];
      if (previous.selected_local_steps === current.selected_local_steps) continue;
      changeCount += 1;
      dom.decisionledgerbody.append(ledgerRow([
        `completed sync cycle ${previous.cycle_index}`,
        finiteNumber(previous.collective_phase_fraction) ? `communication-phase fraction ${formatRatio(previous.collective_phase_fraction)}` : "communication-phase fraction not reported",
        `local steps ${previous.selected_local_steps} → ${current.selected_local_steps}`,
        finiteNumber(current.start_step) ? `compute epoch starting step ${current.start_step}` : "next compute epoch",
        "MODELED POLICY",
      ]));
    }
    if (!changeCount) {
      dom.decisionledgerbody.append(ledgerRow([
        "completed cycles",
        "recorded communication-phase fractions",
        "no cadence change recorded",
        "subsequent compute epochs",
        "MODELED POLICY",
      ]));
    }
  }

  function renderRawTrace() {
    if (!artifact) {
      dom.rawtracesummary.textContent = "Generated event JSON is not loaded.";
      dom.rawtracejson.textContent = "not run";
      return;
    }
    const eventCount = timelineEvents().length;
    dom.rawtracesummary.textContent = `${eventCount.toLocaleString("en-US")} artifact event records · ${artifact.schema}`;
    dom.rawtracejson.textContent = JSON.stringify(artifact, null, 2);
  }

  const observatoryBridge = Object.freeze({
    version: "1.0.0",
    whenReady() {
      return observatoryReady;
    },
    getState() {
      return { ...state };
    },
    getArtifactStatus() {
      return {
        screening: artifact ? "ready" : artifactError ? "error" : "loading",
        semanticConsistency: semanticConsistencyArtifact ? "ready" : semanticConsistencyArtifactError ? "error" : "loading",
        semanticRaw: semanticConsistencyRawArtifact ? "ready" : semanticConsistencyRawArtifactError ? "error" : "not_loaded",
      };
    },
    async selectView(patch, options = {}) {
      await observatoryReady;
      commitState(patch, { replace: Boolean(options.replace) });
      return { ...state };
    },
    async focusCausalPath(nodeIds, edges = []) {
      await observatoryReady;
      const pathNodes = Array.isArray(nodeIds) ? nodeIds.filter((value) => typeof value === "string") : [];
      const terminalNode = pathNodes[pathNodes.length - 1] || "time_to_target";
      commitState({ experiment: "E001", depth: "researcher", node: terminalNode });
      const selectedNodes = new Set(pathNodes);
      const selectedEdges = new Set(edges.map((edge) => `${edge.source}>${edge.target}`));
      document.querySelectorAll("#causal-svg [data-node-id]").forEach((node) => {
        node.classList.toggle("is-mission-path", selectedNodes.has(node.dataset.nodeId));
      });
      document.querySelectorAll("#causal-svg [data-source][data-target]").forEach((edge) => {
        edge.classList.toggle("is-mission-path", selectedEdges.has(`${edge.dataset.source}>${edge.dataset.target}`));
      });
      byId("causal-field")?.scrollIntoView({ behavior: "smooth", block: "center" });
      return { ...state };
    },
    announce(message) {
      announce(String(message || ""));
    },
  });

  Object.defineProperty(window, "GPUStackObservatory", {
    configurable: false,
    enumerable: true,
    writable: false,
    value: observatoryBridge,
  });

})();
