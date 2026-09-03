# GPUSTACK Causal Mission Control

**WebMCP Challenge 2026 entry**

GPUSTACK is a virtual AI datacenter whose full Python model connects 1,517 variables across training, kernels, memory, interconnects, thermals, power delivery, economics, semiconductor devices, lithography, materials, and physical constants. The browser publishes immutable experiment artifacts and a 700-node dependency cone rather than running that model. Causal Mission Control turns the existing observatory into a shared evidence-audit surface: an agent handles the breadth of the published evidence, while the human owns the scientific conclusion.

- **Live application:** <https://cuuper22.github.io/gpu_stack-/observatory.html>
- **Public source:** <https://github.com/Cuuper22/gpu_stack->
- **Pre-WebMCP baseline:** [`3d7339a87e13c4f809ed223c2aa299fb3f631799`](https://github.com/Cuuper22/gpu_stack-/commit/3d7339a87e13c4f809ed223c2aa299fb3f631799)
- **Baseline ref:** [`pre-webmcp-baseline`](https://github.com/Cuuper22/gpu_stack-/tree/pre-webmcp-baseline) (public branch; also an annotated tag in the development checkout)

## Challenge-window disclosure

GPUSTACK is an existing project. The baseline commit above, merged August 13, 2026, is the exact state immediately before the WebMCP Challenge extension. It is preserved as a public immutable comparison ref so reviewers can separate the new work from the underlying project.

### Existing before the challenge extension

- The Python registry-backed equation graph and resolver
- The virtual datacenter, scenario runners, and preregistered research program
- Existing experiment results and evidence JSON
- The Causal Observatory, its visual design, charts, data loaders, and normal human controls
- The public GitHub Pages deployment

### Added for the WebMCP Challenge after August 25, 2026

- Top-level imperative WebMCP registration for eight domain-specific tools
- A bounded adapter between WebMCP tool calls and the observatory's published, immutable artifacts
- A generated scalar-only projection of the existing E001-SC1 raw trace, so an agent can inspect bounded epoch slices without loading the roughly 72 MB authoritative artifact
- Visible causal spotlight, agent activity, pending-review, receipt, and undo surfaces
- A local review workflow with a distinct human approval boundary
- Structured results carrying affected model IDs and current state version
- Contract tests for registration, schemas, state effects, and failure behavior
- This challenge disclosure, a root open-source license, and the WebMCP eval suite

The challenge contribution can be inspected directly with:

```bash
git diff 3d7339a87e13c4f809ed223c2aa299fb3f631799..HEAD
git log --oneline 3d7339a87e13c4f809ed223c2aa299fb3f631799..HEAD
```

Only that post-baseline work is presented as the WebMCP Challenge submission.

## Why WebMCP is load-bearing

A screenshot-based agent sees windows, labels, and charts. It does not naturally know that `training.tokens_per_sec` is a typed model variable, which published dependencies lead to it, which quantities are measured or modeled, which experiment artifact supports a claim, or whether an operation merely inspects evidence or records a review decision.

WebMCP exposes those domain objects and authority boundaries directly. The tools read the same immutable artifacts shown in the page, and each meaningful call leaves a visible selection, highlight, comparison, or review receipt. The result is not a chat layer over GPUSTACK: it is a semantic audit plane for evidence that would otherwise require laborious manual traversal.

The extension deliberately does **not** pretend the static browser is a simulator. It cannot recompute the Python model, invent an intervention, or turn one small-model experiment into a frontier-scale claim. Its job is narrower and more defensible: find the relevant published evidence, preserve its boundary, and help a person judge what conclusion it supports.

## Architecture

| Layer | Path | Responsibility |
|---|---|---|
| WebMCP adapter | `docs/webmcp-tools.js` | Feature detection, JSON Schemas, imperative `document.modelContext.registerTool(...)` calls, bounded results, and abort handling |
| Mission handlers | `docs/webmcp-mission.js` via `window.GPUStackMission.invoke(name, args, { signal })` | Indexed, bounded reads over the shipped artifacts plus local review state and receipts |
| View bridge | `docs/observatory.js` via `window.GPUStackObservatory` | Applies tool-driven selections and causal highlights to the same observatory the human sees |
| Published data | `docs/data/*.json` | Immutable registry-cone and experiment evidence loaded by the observatory |
| Run projection | `scripts/generate_webmcp_projection.py` and `docs/data/webmcp-run-projection-v1.json.gz` | Reproducible, scalar-only view of all 56 E001-SC1 runs and 12,981 epochs; source hashes and omissions are explicit |
| Shared interface | `docs/observatory.html` and `docs/styles/99-webmcp-mission.css` | Human-visible selections, paths, pending reviews, receipts, and approval controls |
| Contract tests | `tests/test_webmcp_contract.py` | Registration, schema, tool inventory, safety boundary, and integration checks |
| Agent evals | `evals/webmcp-evals.json` | Official experimental WebMCP call-selection and trajectory cases |

Registration occurs in the top-level document. If `document.modelContext` is unavailable, the observatory keeps working normally; the application does not install a fake compatibility object. Tool `execute` callbacks validate their inputs again in code and return compact, JSON-serializable objects.

## Tools and authority

| Tool | Mode | What it contributes to the shared page |
|---|---|---|
| `get_observatory_state` | Read-only | Returns the active immutable artifact, registered IDs, evidence boundary, visible selection, and current review state so the agent does not guess identifiers |
| `compare_stress_families` | Read-only | Compares all six held-out E001-SC1 families, or a named subset, across the registered learning, infrastructure, work, and abstention fields |
| `inspect_stress_family` | Read-only | Selects and explains one held-out family, its adaptive-versus-comparator deltas, uncertainty regions, abstention reason, and linked run IDs |
| `inspect_run` | Read-only | Opens an exact run, accepts a request of up to 20 epochs, and returns at most 6 scalar-projection rows per compact result while preserving the authoritative-trace binding |
| `trace_causal_path` | Read-only | Finds and highlights a bounded path through the seven-node conceptual evidence graph without collapsing its branches or evidence classes |
| `open_evidence` | Read-only | Opens a registered artifact, source result, assumption, uncertainty item, or missing-evidence boundary at a chosen semantic depth |
| `compare_policies` | Read-only | Compares up to three registered policies; by default it uses `observable_adaptive` and the calibration-frozen `periodic_local` comparator |
| `stage_conclusion` | Staging write | Places the artifact's typed `abstain_without_policy_claim` conclusion plus one to eight evidence IDs in the pending tray; free-form agent claims are rejected and it cannot approve or commit the conclusion |

The first seven tools are annotated read-only. `stage_conclusion` requires the current state version, a failed frozen gate, and an adaptive family or run with controller abstentions; it performs a final compare-and-swap and refuses to overwrite an existing pending review. It affects only local pending-review state—never the source experiment JSON. No WebMCP tool can approve, reject, edit, or undo a conclusion: those actions are page-only human controls. A human edit is recorded explicitly as an override, and the approved claim, evidence, artifact code, timestamp, and override status remain visible until undone. The agent can explore broadly and prepare a coherent evidence bundle, but it must stop at the judgment boundary.

## Testing

Run the WebMCP contract tests:

```bash
python -m pytest tests/test_webmcp_contract.py -q
```

Run the complete Python suite:

```bash
python -m pytest -q
```

Serve the static site locally:

```bash
python -m http.server 8000 --directory docs
```

Then open <http://localhost:8000/observatory.html> in a WebMCP-enabled browser. The application must remain fully usable in an ordinary browser where WebMCP is absent.

The eval file follows the official experimental [`webmcp-evals`](https://github.com/GoogleChromeLabs/webmcp-tools/tree/main/webmcp-evals) format. With the page already served, deterministic calls can be checked without an API key:

```bash
npx webmcp-evals smoke \
  -u http://localhost:8000/observatory.html \
  -e evals/webmcp-evals.json \
  -v
```

For probabilistic tool selection and multi-step journeys:

```bash
npx webmcp-evals browser \
  -u https://cuuper22.github.io/gpu_stack-/observatory.html \
  -e evals/webmcp-evals.json \
  --open
```

Final acceptance is performed against the deployed top-level page in ChatGPT desktop and a WebMCP-enabled Chrome build. Each demonstrated call must update the visible shared state before returning.

## Judging-criteria map

| Criterion | What to inspect |
|---|---|
| WebMCP leverage | Eight typed domain operations replace brittle UI-coordinate automation; calls operate on the published evidence graph and produce visible state transitions. The human/agent authority boundary depends on staged semantic actions. |
| Execution | The shipped surface contains a 700-node dependency cone and compact E001-SC1 summaries for 56 runs backed by 12,981 raw epochs. Inputs are validated, results are bounded, artifacts stay immutable, and local decisions leave receipts with undo. |
| Potential impact | Researchers can audit a result across stress families and evidence classes faster without giving an agent authority to upgrade an experiment into a stronger claim. The pattern applies to other evidence-heavy technical reviews. |
| Creativity and ambition | The browser becomes an evidence court: the agent traverses a dense causal record, but the human decides whether the claim survives its falsifier. |

## Demo prompt

> Audit whether E001-SC1's observable adaptive controller deserves a transferable win claim over `periodic_local`. Compare all six held-out stress families, inspect the failure, trace the evidence boundary, and stage the scientifically honest conclusion. Do not approve it for me.

The demo is anchored to values already serialized in `docs/data/e001-semantic-consistency-v1.json`:

| Audit fact | Published value |
|---|---|
| Experiment | `E001-SC1` |
| Candidate | `observable_adaptive` |
| Frozen comparator | `periodic_local`; selected on the calibration split before evaluation |
| Untouched evaluation families | `E1` through `E6` |
| Out-of-support abstentions | 104 total: 32 in `E2`, 48 in `E4`, and 24 in `E6` |
| Decisive E6 held-out NLL | adaptive `1.063824194483459`; comparator `0.9984574504196644` |
| Serialized conclusion | `abstain_without_policy_claim` |
| Evidence boundary | measured small-model learning, exact accounting, modeled infrastructure; frontier-scale transfer remains unresolved |

A complete demo should make one coherent loop visible:

1. Open E001-SC1 and compare the controller with `periodic_local` across its six untouched evaluation families.
2. Inspect the compact run ledger, then drill into a bounded slice of the 12,981-epoch scalar projection instead of dumping the roughly 72 MB authoritative raw artifact into context.
3. Surface the decisive failure: on `E6-repeated-membership-loss`, the adaptive policy reaches 1.0638 held-out NLL versus 0.9985 for `periodic_local`.
4. Trace one directed route from site availability to time to target through the published seven-node, eight-edge causal DAG, then open the measured/modeled/unresolved boundary. Present the returned route as one path through a branching graph, not as the entire DAG.
5. Stage `abstain_without_policy_claim`, linked to the evidence, in the pending-review surface.
6. Have the human alone approve or reject it, then show the decision receipt and undo.

The strongest moment is not a list of tool names. It is the point where the agent finds the tempting win, finds the falsifying family, and voluntarily stages the narrower conclusion already warranted by the record—then stops for human judgment.

## Known limits

- WebMCP is experimental and availability depends on the host browser or agent.
- The challenge extension reads the shipped registry-cone export and experiment artifacts; it does not execute the Python simulator, fabricate measurements, or claim live access to a physical datacenter.
- Scenario comparisons are only as strong as their declared assumptions and evidence. The interface keeps those boundaries visible rather than hiding them behind a single recommendation.
- The static public deployment has no account system or server-side persistence. Review state is local to the current browser session, while source evidence remains immutable.

## References

- [OpenAI WebMCP Challenge](https://openai.com/webmcp-challenge/)
- [Official challenge rules and judging criteria](https://webmcp.devpost.com/rules)
- [WebMCP Community Group draft](https://webmachinelearning.github.io/webmcp/)
- [Chrome imperative WebMCP API](https://developer.chrome.com/docs/ai/webmcp/imperative-api)
- [Chrome WebMCP eval guidance](https://developer.chrome.com/docs/ai/webmcp/evals)
