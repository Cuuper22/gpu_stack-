# Changelog

The old pass-by-pass work log (1,350 lines) is in git at commit 7a5838870e553cf9bef683f55b2e1d87343e6281 (`git show 7a58388:CHANGELOG.md`).

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions come from `pyproject.toml` bumps in git history. There are no git tags. Versions before 0.23.0 predate this repository's history. Conclusion names such as `candidate_falsified_*` are the strings the code recorded at the time, not endorsed verdicts.

## [Unreleased]

Work after the 0.27.0 bump. `pyproject.toml` still says 0.27.0.

### Removed
- Restructured the repository around one story and two tools. Dropped the research scaffolding: the E003 to E006 protocols, the P001, V001, R001, S001 and V002 study folders, `EVIDENCE.md`, `RESEARCH.md`, `analysis/` and `docs/research/`. All of it stays in the version history.
- Dropped the prose and large result files under `experiments/e001-*` and `experiments/e002-*`. Scenario inputs remain, with a short `experiments/README.md`.
- Removed the `next-work` command and the `gpu_stack/next_work*.py` modules, with their tests. `experiment-protocol` now lists only E001 and E002.
- `gpu_stack.docs_stats_check` now checks `README.md` only by default; `--files` selects other files. `ROADMAP.md` is now a short list of concrete next fixes.

### Added
- E002 checkpoint-power and checkpoint-energy runs (PW1, PW2) on the same single laptop GPU. PW1 recorded `measurement_invalid`; PW2 used the cumulative energy counter and recorded `checkpoint_cadence_attributed_sparse_continuation_survives`.
- E002-PW3 rack-dephasing protocol, scheduler and telemetry-ingest code.
- E001 semantic-consistency run (SC1) with its protocol, result and raw sidecar.
- Sourced Krane SEMF nuclear-binding preset; isotope roots are now proton count Z and neutron count N, with quark counts derived (U = 2Z + N, D = Z + 2N).
- WebMCP tools on the site and a "causal mission control" panel; `evals/webmcp-evals.json` for the tools.

### Changed
- Site rebuilt in the CuperOS style (pixel fonts, observatory inside the desktop chrome, plain-words depth levels).
- Docs, docstrings and site prose rewritten in a plainer voice.
- Removed agent clutter from the tree: `archive/`, `process/`, `.impeccable/`, `docs/readme_fragments/`, the duplicate top-level `observations/`, and this file's old work log. The package-data copy under `gpu_stack/data/observations/` is now the single source.

## [0.27.0] - 2026-07-12

- E001 redirected to an equal-work contrast. LC2 v1 and v2 were kept as recorded protocol failures (`protocol_failed_warm_start_not_late_stage`, `protocol_failed_calibration_validity`).
- LC3 equal-work run: 12 held-out fixed-versus-adaptive observations over six failure schedules. Recorded conclusion `candidate_falsified_equal_canonical_work`, decided by sampled device energy (median ratio 1.068, 90 percent upper bound 1.134, ceiling 1.05).
- New compact observatory artifact `docs/data/e001-equal-work-v1.json`.

## [0.26.0] - 2026-07-12

- E001-LC1 learning calibration: 40 real runs (10 calibration, 30 held-out) on one RTX 3060 Laptop GPU with a 1.87M-parameter byte-level decoder.
- Recorded conclusion `candidate_falsified_small_model_calibration`. Every policy crossed the calibration target at the first observation.
- Added the learning-calibration runner, its result file and the observatory learning view.

## [0.25.0] - 2026-07-12

- First recovery-backed E001 loop: four recovery policies (synchronous wait and restore, fixed-local restart, adaptive, future-trace oracle) compared on one matched two-failure scenario.
- Added the recovery runner and runtime, a content-addressed result, and the observatory failure-clock view.
- Recorded status `inconclusive_frontier_hypothesis`, because learning was a shared declared prior.

## [0.24.0] - 2026-07-12

- Reoriented the project around a "virtual datacenter" simulator and an experiment program. Added `gpu_stack/research/` (multi-site event simulator, protocols, evaluation, observations, temporal model) and the `experiments/` tree with protocols E001 to E006.
- Added research commands to the CLI and the E001 screening run.
- Added the observatory page (`docs/observatory.html`) and its design notes in `docs/design/`.
- Added three literature observations (SmolLM-360M, Muon; transcribed from arXiv 2606.30634, not run here).

## [0.23.0] - 2026-06-11

- Equation graph grew from 314 variables and 113 equations to 1,517 variables, 24 constants and 959 equations across 16 systems (counts from the old log). Scopes were split into small modules.
- Core: relation roles (identity, constraint, approximation, variant), `Inequality.as_sympy()` no longer collapses to `True`, unit checking on expression relations, a scenario resolver with opt-in fallback and small simultaneous-system solving, and `pyproject.toml` packaging with tests.
- Eight sourced scenario packs (DGX H100 power and full-TCO closure, Pythia-160M, commercial tariff), a `scenario-audit` command, and physical boundary-hardening constraints for lithography source, plasma, imaging medium and nuclear roots.
- Added Monte Carlo uncertainty propagation (`gpu_stack.uncertainty`), a dependency-cone browser on the site with `export-graph-json`, and a docs-stats gate that checks README and site numbers against the registry.
- Added the `gpu-stack` CLI, a CI verify job, Python 3.13 support and a tag-gated release workflow.
- Added the GitHub Pages site.
