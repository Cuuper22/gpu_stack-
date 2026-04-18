# gpu_stack roadmap

## Status as of pass 33

Phases 0, 1, 4, and 5 of the original plan are landed. Phase 2 has the query scaffolding in place but no scope-level metadata populated. Phase 3 is six of twelve large files split; seven remain. Full pass-by-pass history lives in `CHANGELOG.md`; the rolling coverage snapshot lives in `IMPROVEMENT_MAP.md`.

| Phase | Area | Status |
|---|---|---|
| 0 | Semantic hardening: relation roles, inequality preservation, multi-def tagging | DONE (pass 23) |
| 1 | Verification and packaging spine: pytest suite, pyproject.toml | DONE (pass 23); CLI entry point added in pass 32 |
| 2 | Metadata and provenance coverage | helpers landed (pass 30); actual population of `sp_units` and references is open |
| 3 | Modularize large scope files | 5 of 12 done (passes 24, 25, 28, 29, 31, 33); 7 remain |
| 4 | Scenario resolver | DONE (pass 26) |
| 5 | Calibrated preset framework | framework DONE (pass 27); inventory expansion is open |
| 6 | Deepen model where it matters most | not started |

## Objective

Turn the current symbolic graph into a verifiable, scenario-driven modeling toolkit that can answer end-to-end questions about performance, power, cooling, and cost without relying on ad hoc manual substitution.

## What "done" should mean for the next major milestone

A credible next milestone should satisfy five conditions:

1. A requested target variable can be evaluated from a scenario assignment through a supported resolver, not only by hand-walking equations.
2. Constraints stay visible as constraints and do not simplify away accidentally.
3. Alternative model variants are explicit and selectable.
4. High-value equations carry provenance and dimensional metadata.
5. The package ships with tests, packaging metadata, and clean source artifacts.

## Priority order

### Phase 0: Semantic hardening

**Why first:** The graph is now broad enough that semantic ambiguity will become the main source of bugs.

**Tasks**

- Introduce a first-class relation-role concept such as `identity`, `constraint`, `approximation`, and `variant`.
- Separate "defines the variable" from "constrains the variable" inside variable back-references.
- Prevent inequalities from collapsing to plain `True` or `False` when symbolic assumptions make them trivially decidable.
- Add explicit selectors for model families that currently share a target variable, such as dense vs MoE formulas and optimizer-specific update rules.

**Exit criteria**

- No constraint equations disappear under symbolic simplification unless that behavior is intentionally requested.
- Each currently multi-defined variable has an explicit interpretation.
- `Registry` exposes enough metadata to ask for identities, constraints, and variants separately.

### Phase 1: Verification and packaging spine

**Why second:** Once semantics are stable, every new scope improvement needs a safety rail.

**Tasks**

- Add `pytest` coverage for `Registry`, graph utilities, equation subclasses, and representative scope equations.
- Add smoke tests for `import gpu_stack`, `python -m gpu_stack.demo`, cycle detection, and topological sort.
- Add regression tests for the currently known failure mode where inequalities simplify to `True`.
- Add package metadata and a clean source build path. A `pyproject.toml` is the natural place to start.
- Add CI so basic graph health and test coverage run automatically.

**Exit criteria**

- The repo has one command that runs all automated checks.
- The artifact path excludes generated `__pycache__` output.
- New scope additions can land with regression protection.

### Phase 2: Metadata and provenance coverage

**Why third:** The core already supports rigorous metadata. The model should start using it.

**Tasks**

- Populate `VariableKind` across the graph so roots, measured quantities, derived quantities, and definitional labels are distinguishable.
- Populate `Extensivity` for quantities where aggregation matters.
- Add `sp_units` to the high-value physical, thermal, and economic variables.
- Turn on `check_units=True` for a curated subset of foundational equations.
- Attach references to the equations and variables that represent canonical formulas, vendor-style specifications, or benchmark-calibrated terms.

**Exit criteria**

- The physical, memory, thermal, and economics scopes have meaningful unit coverage.
- The most user-facing equations have provenance, not only descriptions.
- Aggregation-sensitive quantities can be queried by extensivity class.

### Phase 3: Modularize the largest scopes

**Why now:** The current model is workable, but several scope files are already too wide for easy review.

**Tasks**

- Split `cluster.py`, `architecture.py`, `optimizer.py`, `economics.py`, `training.py`, `precision.py`, `gpu.py`, `thermal.py`, `kernel.py`, `memory_subsystem.py`, `parallelism.py`, and `memory_cell.py` according to the split map in `IMPROVEMENT_MAP.md`.
- Keep each public scope import stable through a thin aggregator module, the same way `physical.py` already works.
- Add one smoke test per new helper module so imports fail fast if a split regresses wiring.

**Exit criteria**

- No single scope file needs to carry unrelated subdomains.
- Public imports stay backward compatible.
- Review and debugging effort drops because changes are localized.

### Phase 4: Add a scenario resolver

**Why next:** This is the feature that turns the graph from a registry into a modeling tool.

**Tasks**

- Build a resolver that accepts a target variable plus a dict of scenario assignments.
- Support relation-role filtering, variant selection, and topological evaluation where possible.
- Expose failure modes cleanly when the scenario is underdetermined, overdetermined, or inconsistent.
- Add explanation output that shows which equations were used for a result.

**Exit criteria**

- A user can request something like `econ.cost.per_token` or `training.tokens_per_sec` and get a traceable value from a single scenario object.
- The resolver can explain missing inputs rather than failing silently.
- The demo can show at least two end-to-end solved examples without manual per-equation stitching.

### Phase 5: Calibrated presets and scenario packs

**Why after the resolver:** Presets are much more useful once there is a standard evaluation path.

**Tasks**

- Add hardware presets for representative GPU, interconnect, and cluster configurations.
- Add workload presets for dense training, active-MoE training, offload-heavy runs, and inference-oriented scenarios.
- Capture measured or cited efficiency factors where the model currently leaves them as roots.
- Store provenance for every preset so numbers are auditable.

**Exit criteria**

- The repo ships with a small library of named scenarios.
- The same scenario can drive performance, thermal, and economics outputs consistently.
- Presets are documented and reproducible.

### Phase 6: Deepen the model where it matters most

Once the semantic and tooling foundation is stable, expansion becomes lower risk. The best next areas are:

- process corners, variability, and aging in physical and memory scopes,
- topology- and congestion-aware communication in interconnect and collective scopes,
- fused and decode kernels in kernel scope,
- transient thermals and controller behavior in thermal scope,
- and richer tariff, financing, and deployment cases in economics.

## Concrete next 12 tickets

| Priority | Ticket | Done when |
|---|---|---|
| P0 | Add relation-role metadata to equations and variable back-references. | Multi-definition variables can be classified cleanly. |
| P0 | Fix inequality preservation so symbolic positivity assumptions do not erase constraints. | No audited constraints simplify to bare `True`. |
| P0 | Add `pytest` with graph-health, import, and demo smoke tests. | CI can fail on regression before merge. |
| P0 | Add `pyproject.toml` and clean source packaging rules. | The repo builds and installs reproducibly. |
| P0 | Add regression tests for the 15 current multi-definition variables. | Each case has an expected semantic role. |
| P1 | Implement a scenario resolver with target evaluation and trace output. | One-call end-to-end evaluation works for selected targets. |
| P1 | Populate `VariableKind` and `Extensivity` across the graph. | Metadata queries return meaningful results. |
| P1 | Add `sp_units` plus dimensional checks for the high-value foundational equations. | Unit mistakes fail fast during import or tests. |
| P1 | Split `cluster.py` into node, rack, site, storage, and reliability helpers. | The scope stays import-compatible and easier to review. |
| P1 | Split `architecture.py` into embeddings, attention, FFN, positions, and MoE helpers. | Model structure changes become localized. |
| P1 | Add named scenario presets with provenance. | Demo and tests can run reproducible end-to-end cases. |
| P2 | Add notebooks or a CLI for dependency tracing and scenario evaluation. | Users can inspect results without writing custom scripts. |

## Sequencing note

Do not start by adding another hundred variables. The next highest-return work is semantic cleanup, tests, packaging, and evaluation. Once those exist, additional scope depth will compound instead of fragment.
