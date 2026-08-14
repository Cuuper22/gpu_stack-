# README QA Checklist

Prepared 2026-05-11 18:11 America/Los_Angeles for a README rewrite into a Medium-style Cuper article. The scope is simple to state: keep every technical claim correct while the prose becomes sharper, more narrative, and less of a registry dump.

## 1. Factual Claims To Preserve Or Reverify

- Preserve the package identity: GPUSTACK is a causal, uncertainty-aware virtual AI datacenter, visual observatory, and ML systems research lab. The SymPy registry is its symbolic causal backbone, not its sole product or progress metric.
- Preserve the declared project metadata from `pyproject.toml`: package name `gpu_stack`, version `0.27.0`, Python `>=3.10`, MIT license, dependency `sympy>=1.12`, optional dev dependencies `pytest>=7` and `pytest-asyncio>=0.24`, console script `gpu-stack = gpu_stack.cli:main`, homepage `https://github.com/cuuper22/gpu_stack-`.
- Preserve the current live registry/audit counts unless a fresh command disagrees:
  - 16 systems
  - 1517 variables
  - 24 constants
  - 950 equations
  - 619 root inputs
  - 259 leaves
  - 0 cycles
  - topological order length 1517
  - 0 collapsed equations
  - 0 collapsed approximation-validity relations
  - 0 unresolved raw symbols
  - 0 orphan value equations
  - 53 multi-definition variables
  - 0 large scope files
  - 7 large project files
  - 0 hard audit failures
  - 1428 non-constant variables with `sp_units`
  - 1324 non-constant variables with references
  - 878 equations with references
  - 799 equations with unit checks
- Reverify the collected test count before publishing. The current README says 639 collected tests, but `python -m pytest --collect-only -q` collected 648 tests in this workspace on 2026-05-11.
- Preserve the current fast verifier status only if freshly rerun: `python -m gpu_stack.cli verify --profile fast` passed with 2 of 2 gates in 43.23s on this machine.
- Do not overclaim the latest verified wave. The README currently states full pytest, full verifier, read-only verifier, and source-clean results from earlier work. Those are historical claims unless rerun in the same final state.
- Preserve the design rules:
  - only universal physics constants are `Constant`s
  - scopes self-register on import
  - `gpu_stack.scopes.SCOPE_MODULES` is authoritative import order
  - the project is symbolic first
  - root inputs are visible modeling debt, not hidden defaults
- Preserve the limitation framing: broad modeling substrate, conservative resolver, skeletal calibration presets, many remaining root inputs.
- Preserve resolver behavior precisely: one selected defining relation per variable, unassigned symbolic boundaries reported as `missing`, constraint and approximation-validity feedback, no simultaneous solving, no optimization, no automatic relation switching.
- Preserve current CLI surfaces if mentioned: `verify`, `root-debt`, `scenario-report`, `scenario-audit`, `resolve`, `next-work`, JSON output modes, missing-family reporting, preset target evaluation.
- Preserve the existence and role of `Preset.evaluate_targets(...)`, `ScenarioReport`, `ScenarioTargetReport`, `MissingFamilySummary`, and `scenario-report --json`.
- Preserve the sourced vs synthetic distinction for presets. Do not call synthetic fixtures authoritative hardware calibration.
- Preserve physical-slice specifics only if they remain readable and correct. If the article trims the huge lithography paragraph, keep the meaning: lithography/source/medium layers have been recursively decomposed down to more primitive symbolic roots with feasibility constraints, not filled with magic constants.
- Preserve the current scope inventory counts only after rerunning or deriving them. If not reverified, call them a snapshot instead of current truth.

## 2. Markdown And GitHub Rendering Pitfalls

- Keep the README valid as the `pyproject.toml` long description. Avoid HTML that PyPI may reject or render poorly.
- Avoid giant unwrapped paragraphs like the current physical-slice paragraph. GitHub renders them as a wall; Medium-style prose needs shorter sections without losing the exact claims.
- Keep code fences language-tagged where possible: `bash`, `python`, or `text`.
- Do not put command prompts like `$` inside copyable command blocks unless the whole README consistently uses them.
- Keep tables narrow enough for GitHub mobile rendering. The full scope inventory table is wide and may need splitting, collapsing into bullets, or moving to a fragment.
- Escape or fence symbols that Markdown can mangle: `*`, `_`, `<`, `>`, `|`, `<=`, `>=`, `D <= 2U`, `(U + D) mod 3 = 0`, `x_LL > -1/2`, `gpu-stack root-debt --families`.
- Use inline code for variable names, equation names, CLI flags, package names, and file paths.
- Keep relative links stable from the repository root: `./IMPROVEMENT_MAP.md`, `./ROADMAP.md`, `./HANDOFF.md`, `./CHANGELOG.md`, `./archive/AGENT_DIARY.md`, `./archive/rest_breaks/README.md`.
- If badges or images are added later, verify they do not depend on private state or dead external URLs.
- Avoid raw Unicode math if the repo stays ASCII. Prefer fenced or inline code for equations unless the README already accepts richer typography.
- Ensure headings descend cleanly. Do not jump from `##` to `####` for visual styling.
- Keep generated article sections linkable with stable headings. Avoid repeated heading text such as multiple `Previous Verified Wave` sections without unique labels.
- Check that underscores in `gpu_stack`, `ScenarioReport`, and variable names are either fenced or rendered correctly.
- Keep line endings and trailing spaces clean. Markdown line breaks by two trailing spaces are easy to create by accident and hard to see.

## 3. Voice And Design Anti-Patterns To Reject

- Reject startup brochure language: "revolutionary", "cutting-edge", "seamless", "unlock", "empower", "next generation", "production ready" unless directly proven.
- Reject empty README tropes: badges as authority, star-count bait, generic "features" lists, "built with passion", skill-section filler, and mic-drop closers.
- Reject AI-slop transitions: "In today's rapidly evolving landscape", "At its core", "What sets this apart", "This isn't just X, it's Y".
- Reject fake confidence. If a count is not rerun after code changes, say "snapshot" or "historical verified run".
- Reject smoothing over modeling debt. The root inputs are the point; do not hide them behind "fully modeled" language.
- Reject turning the project into a simulator claim. The honest line is symbolic dependency substrate with selected scenario resolution.
- Reject over-humanized mysticism in the technical README. Cuper-style can be vivid, sharp, and weird, but the repo still needs to teach a serious reader what the package does.
- Reject excessive lore before utility. A Medium-style article can open with a hook, but the first screen should still answer what `gpu_stack` is and why it exists.
- Reject dense equation-name confetti in narrative paragraphs. Put unavoidable registries, counts, and scope lists into tables or appendices.
- Reject cute analogies that distort the physics, training stack, or resolver behavior.
- Reject false completeness: "models the entire GPU stack" should be softened to "maps a broad symbolic slice of the GPU training stack" unless every boundary is qualified.
- Reject "just run" examples that omit install context, Python version, or editable install.
- Reject hiding limitations at the bottom as a legal disclaimer. Put the limitation frame near the promise so the article earns trust early.
- Reject negative parallelism and over-polished contrast pairs if they start sounding like a generated manifesto.
- Reject em dashes in the final README if Cuper's anti-slop constraints apply. Use commas, parentheses, colons, or periods.

## 4. Final Verification Commands For A README-Only Change

Run from `D:\GPUSTACK` after the README rewrite lands:

```powershell
Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz"
python -m gpu_stack.cli stats
python -m gpu_stack.cli audit
python -m pytest --collect-only -q
python -m gpu_stack.cli verify --profile fast
python -B -m gpu_stack.cli verify --profile fast --read-only
python -m pip install -e ".[dev]"
python -m build --sdist --wheel
```

Optional but useful if the article changes command examples:

```powershell
python -m gpu_stack.cli root-debt --families --limit 20
python -m gpu_stack.cli scenario-report scenarios.dense_training_cost_fixture --json
python -m gpu_stack.cli scenario-audit --json
```

Final README-specific checks:

```powershell
rg -n "\x{2014}|revolutionary|cutting-edge|seamless|unlock|empower|passionate about|In today's rapidly evolving landscape|At its core|What sets this apart|This isn't just" README.md
rg -n "639|648|1517|959|619|799|878|1324|1428|0 cycles|hard failures|large project files" README.md
git diff -- README.md docs/readme_fragments/readme_qa_checklist.md
```

If the workspace has no `.git` directory, replace the final diff command with a direct file read and a manual path check:

```powershell
Get-Content README.md -Raw
Get-Content docs\readme_fragments\readme_qa_checklist.md -Raw
```

Expected review posture: every numeric claim in `README.md` either matches fresh command output, is explicitly labeled historical, or is removed.
