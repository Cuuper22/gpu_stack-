(() => {
  "use strict";

  /**
   * WebMCP adapter for GPUSTACK's immutable E001-SC1 evidence observatory.
   *
   * The page owns the artifacts, visible selection, staged conclusion, and
   * human approval/rejection controls. It exposes one bridge to this adapter:
   *
   *   window.GPUStackMission.invoke(toolName, validatedArgs, { signal })
   *
   * The bridge may be installed after this file is evaluated. Every invocation
   * resolves it from `window` at call time. It must update the human-visible UI
   * before resolving and return a compact JSON-serializable object. WebMCP can
   * stage a conclusion, but approval remains an explicit page-only human act.
   */

  const MAX_ID_LENGTH = 180;
  const MAX_RESULT_CHARS = 1500;
  const ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,179}$/;
  const SEMANTIC_DEPTHS = ["freshman", "researcher", "full_trace"];
  const CONFIDENCE_LEVELS = ["supported", "qualified", "abstain"];

  class ArgumentError extends Error {
    constructor(field, message, expected) {
      super(message);
      this.name = "ArgumentError";
      this.field = field;
      this.expected = expected;
    }
  }

  const objectSchema = (properties, required = []) => ({
    type: "object",
    properties,
    required,
    additionalProperties: false,
  });

  const idSchema = (description) => ({
    type: "string",
    description,
    minLength: 1,
    maxLength: MAX_ID_LENGTH,
    pattern: "^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,179}$",
  });

  const idArraySchema = (description, maxItems, minItems = 1) => ({
    type: "array",
    description,
    minItems,
    maxItems,
    uniqueItems: true,
    items: idSchema("Exact identifier from the active observatory artifact."),
  });

  const SCHEMAS = Object.freeze({
    get_observatory_state: objectSchema({}),

    compare_stress_families: objectSchema({
      family_ids: idArraySchema(
        "Optional held-out evaluation family IDs. Omit to compare all six E001-SC1 families.",
        6,
      ),
    }),

    inspect_stress_family: objectSchema(
      {
        family_id: idSchema("Held-out family ID, for example E4-failure-inside-wan-collapse."),
        include_regions: {
          type: "boolean",
          default: true,
          description: "Include compact uncertainty ranking regions. Defaults to true.",
        },
      },
      ["family_id"],
    ),

    inspect_run: objectSchema(
      {
        run_id: idSchema("Exact run ID from the E001-SC1 compact or raw artifact."),
        epoch_offset: {
          type: "integer",
          minimum: 0,
          default: 0,
          description: "Zero-based first epoch to return. Defaults to 0.",
        },
        epoch_limit: {
          type: "integer",
          minimum: 1,
          maximum: 20,
          default: 8,
          description: "Requested projected epochs. Defaults to 8; replies cap rows to fit the result budget.",
        },
      },
      ["run_id"],
    ),

    trace_causal_path: objectSchema(
      {
        from_node: idSchema("Conceptual evidence-graph node where the trace begins."),
        to_node: idSchema("Conceptual evidence-graph node where the trace ends."),
        max_nodes: {
          type: "integer",
          minimum: 2,
          maximum: 12,
          default: 7,
          description: "Maximum nodes in the returned path. Defaults to 7.",
        },
      },
      ["from_node", "to_node"],
    ),

    open_evidence: objectSchema(
      {
        evidence_id: idSchema("Evidence record, artifact, source, or boundary identifier."),
        semantic_depth: {
          type: "string",
          enum: SEMANTIC_DEPTHS,
          default: "researcher",
          description: "Explanation depth. Defaults to researcher.",
        },
      },
      ["evidence_id"],
    ),

    compare_policies: objectSchema({
      policy_ids: idArraySchema(
        "Optional policy IDs. Omit to compare observable_adaptive with the frozen periodic_local comparator.",
        3,
      ),
      metric_ids: idArraySchema(
        "Optional metric IDs to prioritize. Omit for the artifact's registered comparison metrics.",
        6,
      ),
    }),

    stage_conclusion: objectSchema(
      {
        claim: {
          type: "string",
          minLength: 1,
          maxLength: 600,
          description: "Concise proposed conclusion grounded only in the cited evidence IDs.",
        },
        evidence_ids: idArraySchema(
          "One to eight evidence IDs that directly support or qualify the proposed claim.",
          8,
        ),
        confidence: {
          type: "string",
          enum: CONFIDENCE_LEVELS,
          description: "Supported, qualified, or abstain. This is evidence confidence, not approval.",
        },
        expected_state_version: {
          type: "integer",
          minimum: 0,
          description: "Optional optimistic-concurrency version returned by a prior tool call.",
        },
      },
      ["claim", "evidence_ids", "confidence"],
    ),
  });

  function isRecord(value) {
    if (value === null || typeof value !== "object" || Array.isArray(value)) return false;
    const prototype = Object.getPrototypeOf(value);
    return prototype === Object.prototype || prototype === null;
  }

  function checkObject(value, allowedKeys) {
    if (!isRecord(value)) {
      throw new ArgumentError("$", "Arguments must be a JSON object.", "object");
    }
    const unknown = Object.keys(value).find((key) => !allowedKeys.includes(key));
    if (unknown) {
      throw new ArgumentError(
        unknown,
        `Unknown argument: ${unknown}.`,
        allowedKeys.length ? `one of: ${allowedKeys.join(", ")}` : "no arguments",
      );
    }
  }

  function cleanString(value, field, options = {}) {
    const { required = false, min = 0, max = 600, pattern = null } = options;
    if (value === undefined) {
      if (required) throw new ArgumentError(field, `${field} is required.`, "string");
      return undefined;
    }
    if (typeof value !== "string") {
      throw new ArgumentError(field, `${field} must be a string.`, "string");
    }
    const cleaned = value.trim();
    if (cleaned.length < min || cleaned.length > max) {
      throw new ArgumentError(field, `${field} must be ${min}-${max} characters.`, `${min}-${max} characters`);
    }
    if (pattern && !pattern.test(cleaned)) {
      throw new ArgumentError(field, `${field} has an invalid identifier format.`, "GPUSTACK identifier");
    }
    return cleaned;
  }

  function cleanId(value, field) {
    return cleanString(value, field, {
      required: true,
      min: 1,
      max: MAX_ID_LENGTH,
      pattern: ID_PATTERN,
    });
  }

  function cleanIdArray(value, field, maxItems) {
    if (!Array.isArray(value) || value.length < 1 || value.length > maxItems) {
      throw new ArgumentError(field, `${field} must contain 1-${maxItems} identifiers.`, `array with 1-${maxItems} identifiers`);
    }
    const cleaned = value.map((item, index) => cleanId(item, `${field}[${index}]`));
    if (new Set(cleaned).size !== cleaned.length) {
      throw new ArgumentError(field, `${field} must not contain duplicates.`, "unique identifiers");
    }
    return cleaned;
  }

  function cleanOptionalIdArray(value, field, maxItems) {
    return value === undefined ? undefined : cleanIdArray(value, field, maxItems);
  }

  function cleanEnum(value, field, allowed, fallback) {
    if (value === undefined && fallback !== undefined) return fallback;
    if (typeof value !== "string" || !allowed.includes(value)) {
      throw new ArgumentError(field, `${field} must be one of ${allowed.join(", ")}.`, allowed.join(" | "));
    }
    return value;
  }

  function cleanInteger(value, field, minimum, maximum, fallback) {
    if (value === undefined) {
      if (fallback !== undefined) return fallback;
      throw new ArgumentError(field, `${field} is required.`, `integer >= ${minimum}`);
    }
    const aboveMax = maximum !== undefined && value > maximum;
    if (!Number.isInteger(value) || value < minimum || aboveMax) {
      const range = maximum === undefined ? `>= ${minimum}` : `${minimum}-${maximum}`;
      throw new ArgumentError(field, `${field} must be an integer in ${range}.`, `integer ${range}`);
    }
    return value;
  }

  const VALIDATORS = Object.freeze({
    get_observatory_state(args) {
      checkObject(args, []);
      return {};
    },

    compare_stress_families(args) {
      checkObject(args, ["family_ids"]);
      const result = {};
      const familyIds = cleanOptionalIdArray(args.family_ids, "family_ids", 6);
      if (familyIds !== undefined) result.family_ids = familyIds;
      return result;
    },

    inspect_stress_family(args) {
      checkObject(args, ["family_id", "include_regions"]);
      if (args.include_regions !== undefined && typeof args.include_regions !== "boolean") {
        throw new ArgumentError("include_regions", "include_regions must be a boolean.", "boolean");
      }
      return {
        family_id: cleanId(args.family_id, "family_id"),
        include_regions: args.include_regions === undefined ? true : args.include_regions,
      };
    },

    inspect_run(args) {
      checkObject(args, ["run_id", "epoch_offset", "epoch_limit"]);
      return {
        run_id: cleanId(args.run_id, "run_id"),
        epoch_offset: cleanInteger(args.epoch_offset, "epoch_offset", 0, undefined, 0),
        epoch_limit: cleanInteger(args.epoch_limit, "epoch_limit", 1, 20, 8),
      };
    },

    trace_causal_path(args) {
      checkObject(args, ["from_node", "to_node", "max_nodes"]);
      const fromNode = cleanId(args.from_node, "from_node");
      const toNode = cleanId(args.to_node, "to_node");
      if (fromNode === toNode) {
        throw new ArgumentError("to_node", "to_node must differ from from_node.", "different node identifier");
      }
      return {
        from_node: fromNode,
        to_node: toNode,
        max_nodes: cleanInteger(args.max_nodes, "max_nodes", 2, 12, 7),
      };
    },

    open_evidence(args) {
      checkObject(args, ["evidence_id", "semantic_depth"]);
      return {
        evidence_id: cleanId(args.evidence_id, "evidence_id"),
        semantic_depth: cleanEnum(args.semantic_depth, "semantic_depth", SEMANTIC_DEPTHS, "researcher"),
      };
    },

    compare_policies(args) {
      checkObject(args, ["policy_ids", "metric_ids"]);
      const result = {};
      const policyIds = cleanOptionalIdArray(args.policy_ids, "policy_ids", 3);
      const metricIds = cleanOptionalIdArray(args.metric_ids, "metric_ids", 6);
      if (policyIds !== undefined) result.policy_ids = policyIds;
      if (metricIds !== undefined) result.metric_ids = metricIds;
      return result;
    },

    stage_conclusion(args) {
      checkObject(args, ["claim", "evidence_ids", "confidence", "expected_state_version"]);
      const result = {
        claim: cleanString(args.claim, "claim", { required: true, min: 1, max: 600 }),
        evidence_ids: cleanIdArray(args.evidence_ids, "evidence_ids", 8),
        confidence: cleanEnum(args.confidence, "confidence", CONFIDENCE_LEVELS),
      };
      if (args.expected_state_version !== undefined) {
        result.expected_state_version = cleanInteger(args.expected_state_version, "expected_state_version", 0);
      }
      return result;
    },
  });

  const READ_ONLY = Object.freeze({ readOnlyHint: true, untrustedContentHint: false });
  const STAGING_WRITE = Object.freeze({ readOnlyHint: false, untrustedContentHint: true });

  const TOOL_DEFINITIONS = Object.freeze([
    {
      name: "get_observatory_state",
      title: "Read observatory state",
      description: "Read the active immutable artifact, semantic depth, selected family and run, registered IDs, evidence boundary, state version, and any staged conclusion. Use this first instead of guessing identifiers.",
      inputSchema: SCHEMAS.get_observatory_state,
      annotations: READ_ONLY,
    },
    {
      name: "compare_stress_families",
      title: "Compare held-out stress families",
      description: "Compare up to six E001-SC1 held-out evaluation families on learning, completion time, WAN payload, replayed work, energy, ranking regions, and abstentions. Omit IDs to compare all six.",
      inputSchema: SCHEMAS.compare_stress_families,
      annotations: READ_ONLY,
    },
    {
      name: "inspect_stress_family",
      title: "Inspect one stress family",
      description: "Inspect one held-out E001-SC1 stress family, including adaptive-versus-frozen-comparator deltas, uncertainty regions, abstention reason, and linked run IDs. Also selects it visibly.",
      inputSchema: SCHEMAS.inspect_stress_family,
      annotations: READ_ONLY,
    },
    {
      name: "inspect_run",
      title: "Inspect experiment run",
      description: "Inspect one exact E001-SC1 run and a bounded page of scalar-projected optimizer-commit epochs. Returns mode choice, OOD and abstention state, completion, and event markers while preserving the authoritative raw-trace hash.",
      inputSchema: SCHEMAS.inspect_run,
      annotations: READ_ONLY,
    },
    {
      name: "trace_causal_path",
      title: "Trace evidence path",
      description: "Trace a bounded path through the seven-node conceptual evidence graph, preserving relation labels and observed, modeled, assumed, prior, or unmeasured boundaries. Highlights the same path.",
      inputSchema: SCHEMAS.trace_causal_path,
      annotations: READ_ONLY,
    },
    {
      name: "open_evidence",
      title: "Open supporting evidence",
      description: "Open a registered artifact hash, frozen gate, held-out family, run, source observation, or causal node at the requested semantic depth. Returns provenance and caveats, not a fabricated claim.",
      inputSchema: SCHEMAS.open_evidence,
      annotations: READ_ONLY,
    },
    {
      name: "compare_policies",
      title: "Compare registered policies",
      description: "Compare up to three policies from the immutable experiment artifact. Omit IDs for observable_adaptive versus the calibration-frozen periodic_local comparator across registered metrics.",
      inputSchema: SCHEMAS.compare_policies,
      annotations: READ_ONLY,
    },
    {
      name: "stage_conclusion",
      title: "Stage evidence conclusion",
      description: "Stage a supported, qualified, or abstain conclusion with explicit evidence IDs in the visible pending tray. This never approves or commits it; only the human can approve or reject it in the page.",
      inputSchema: SCHEMAS.stage_conclusion,
      annotations: STAGING_WRITE,
    },
  ]);

  function failure(toolName, code, message, extra = {}) {
    return {
      ok: false,
      tool: toolName,
      code,
      message: String(message).slice(0, 320),
      ...extra,
    };
  }

  function compactValue(value, depth = 0) {
    if (value === null || typeof value === "boolean") return value;
    if (typeof value === "number") return Number.isFinite(value) ? value : null;
    if (typeof value === "string") return value.length > 300 ? `${value.slice(0, 297)}...` : value;
    if (depth >= 5) return "[detail omitted]";
    if (Array.isArray(value)) {
      const result = value.slice(0, 10).map((item) => compactValue(item, depth + 1));
      if (value.length > 10) result.push(`[${value.length - 10} more]`);
      return result;
    }
    if (isRecord(value)) {
      const result = {};
      const keys = Object.keys(value).sort().slice(0, 24);
      keys.forEach((key) => {
        const item = compactValue(value[key], depth + 1);
        if (item !== undefined) result[key] = item;
      });
      if (Object.keys(value).length > 24) result.detail_omitted = true;
      return result;
    }
    return undefined;
  }

  function compactResult(toolName, rawResult) {
    if (rawResult === undefined) {
      return failure(toolName, "EMPTY_RESULT", "The mission bridge returned no result.");
    }
    const normalized = isRecord(rawResult)
      ? { ok: rawResult.ok !== false, ...rawResult, tool: toolName }
      : { ok: true, tool: toolName, result: rawResult };

    try {
      if (JSON.stringify(normalized).length <= MAX_RESULT_CHARS) return normalized;
    } catch (_error) {
      return failure(toolName, "NON_SERIALIZABLE_RESULT", "The mission bridge returned data that is not JSON-serializable.");
    }

    const compacted = compactValue(normalized);
    try {
      compacted.truncated = true;
      if (JSON.stringify(compacted).length <= MAX_RESULT_CHARS) return compacted;
    } catch (_error) {
      // Fall through to a small receipt. Full detail remains in the page.
    }

    const fallback = {
      ok: normalized.ok !== false,
      tool: toolName,
      truncated: true,
      message: "Full detail is visible in GPUSTACK; this response was reduced to the WebMCP result budget.",
    };
    ["code", "stateVersion", "state_version", "proposal_id", "summary"].forEach((key) => {
      if (normalized[key] !== undefined) fallback[key] = compactValue(normalized[key]);
    });
    return fallback;
  }

  function abortIfNeeded(signal) {
    if (signal && signal.aborted) {
      throw signal.reason || new Error("Tool execution was cancelled.");
    }
  }

  async function executeTool(toolName, args, options = {}) {
    const signal = options && options.signal;
    abortIfNeeded(signal);

    let validated;
    try {
      validated = VALIDATORS[toolName](args);
    } catch (error) {
      if (error instanceof ArgumentError) {
        return failure(toolName, "INVALID_ARGUMENT", error.message, {
          field: error.field,
          expected: error.expected,
        });
      }
      return failure(toolName, "INVALID_ARGUMENT", "The tool arguments could not be validated.");
    }

    const bridge = window.GPUStackMission;
    if (!bridge || typeof bridge.invoke !== "function") {
      return failure(toolName, "BRIDGE_UNAVAILABLE", "GPUSTACK Mission Control is still loading. Retry after the observatory is ready.");
    }

    try {
      const result = await bridge.invoke(toolName, validated, { signal });
      abortIfNeeded(signal);
      return compactResult(toolName, result);
    } catch (error) {
      abortIfNeeded(signal);
      const message = error && typeof error.message === "string" ? error.message : "Mission execution failed.";
      return failure(toolName, "MISSION_ERROR", message);
    }
  }

  function emit(name, detail) {
    if (typeof window.dispatchEvent !== "function" || typeof CustomEvent !== "function") return;
    window.dispatchEvent(new CustomEvent(name, { detail }));
  }

  const toolNames = Object.freeze(TOOL_DEFINITIONS.map((tool) => tool.name));
  if (window.GPUStackWebMCP) return;

  const modelContext = document.modelContext;
  if (!modelContext || typeof modelContext.registerTool !== "function") {
    window.GPUStackWebMCP = Object.freeze({
      supported: false,
      toolNames,
      ready: Promise.resolve({ supported: false, registered: [], failed: [] }),
      dispose() {},
    });
    emit("gpustack:webmcp-unavailable", {
      reason: "document.modelContext.registerTool is unavailable",
      toolNames,
    });
    return;
  }

  const lifecycle = typeof AbortController === "function" ? new AbortController() : null;
  const registered = [];
  const failed = [];
  const ready = (async () => {
    for (const definition of TOOL_DEFINITIONS) {
      const executable = {
        ...definition,
        execute: (args, options) => executeTool(definition.name, args, options),
      };
      try {
        if (lifecycle) {
          await modelContext.registerTool(executable, { signal: lifecycle.signal });
        } else {
          await modelContext.registerTool(executable);
        }
        registered.push(definition.name);
      } catch (error) {
        failed.push({
          name: definition.name,
          message: error && typeof error.message === "string" ? error.message.slice(0, 240) : "Registration failed.",
        });
      }
    }
    const status = { supported: true, registered: [...registered], failed: [...failed] };
    emit("gpustack:webmcp-ready", status);
    return status;
  })();

  window.GPUStackWebMCP = Object.freeze({
    supported: true,
    toolNames,
    ready,
    dispose() {
      if (lifecycle && !lifecycle.signal.aborted) lifecycle.abort();
    },
  });
})();
