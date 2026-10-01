# S001: which root inputs actually move the headline outputs?

Status: STAGE 1 (protocol and code only). No graph sensitivity index has been computed.
Code: `run.py`, `sens_lib.py`. Results will go to `results/`.

## Question

`python -m gpu_stack.cli root-debt --families` ranks root inputs by how many graph
variables depend on them (count of dependents). That ranks lithography and nuclear
families first. A count of dependents is not influence. In plain terms: if each input is
moved within a stated range, how much of the spread in cost per token, tokens per second
and datacenter power does each cause, and does the root-debt order predict it?

## Targets and nominal points

Targets: `econ.cost.per_token`, `training.tokens_per_sec`, `econ.job.dc_power`,
`econ.run.power_cost` (electricity only). Nominal points (shipped presets, unmodified):
- P1 `pythia_70m_dgx_h100_us_2024_industrial_full_tco_assumption` (80 inputs; cited
  hardware, workload and tariff plus labeled assumption closures). Primary.
- P2 `dense_training_cost_fixture` (30 inputs; synthetic round numbers).
- P3 `pythia_160m_dgx_h100_us_2024_industrial_energy_floor_cost` (2026-era pack;
  capex set to 0, so cost per token is electricity only).

## What is computed

1. Closed form. Every preset input is replaced by its own symbol and the resolver
   (`gpu_stack.core.resolver.resolve`) returns the target as an expression in those
   symbols; it is lambdified with numpy. The closed form must equal the numeric
   resolver at nominal to 1e-9 relative, else the run aborts. This is needed because
   `uncertainty.py`'s fast path cannot expand pinned graph cut points.
2. Structure counts, per target: roots (of 619) that are ancestors via any
   defining equation; via the resolver's selected equations; assigned in the preset;
   present as a free symbol in the resolved formula. Split into lithography
   (`physical.lithography.*`) and nuclear/quark (name matches
   `nuclear|proton|neutron|quark|binding|isotope`; no root name contains "quark", quark
   counts are derived). A root absent from the formula has exactly zero influence. For each
   pinned derived input in the formula (a "cut point", e.g. `gpu.peak_flops_power_limited`):
   how many roots lie beneath it.
3. Sampling rule R1 (primary). Each input in the formula, nominal x0 > 0, is
   log-uniform on [x0/2, 2x0]. Exceptions, fixed now: dimensionless x0 <= 1 gets
   [x0/2, min(2x0, 1)]; `training.recompute_overhead`, `training.optimizer_flop_multiplier`
   get [x0, 2x0] (multipliers cannot be below 1); `arch.n_kv_heads`,
   `arch.norm.param_multiplier` get [x0/2, x0]; `arch.ffn.weight_matrices` is 2 or 3;
   `arch.output.untied_factor` (0/1 switch) is held; inputs with x0 = 0 are held and
   listed; integer-typed inputs and layer/head counts are rounded. `par.n_gpus` is
   not sampled alone; it is set to node GPUs x nodes per rack x racks, which also
   enter as factors. Width variants: R1_f1.25 and R1_f4 (same rules, factor 1.25 or 4).
   R4 = R1 plus zero-nominal inputs sampled uniformly: dimensionless U(0,0.3),
   seconds U(0, 0.3 x nominal step time), USD/t U(0,100); other zeros stay held.
   Why a factor of 2: no input has a measured uncertainty, so one common relative range is
   the neutral choice; it asks which inputs the model is structurally sensitive to. It is
   not a claim that each input is uncertain by 2x. The width variants test that choice.
4. Morris elementary effects: 100 trajectories, 4 levels, on log(target); a cross-check,
   not a filter (full Sobol is cheap here).
5. Sobol indices on log(target) (primary; makes the multiplicative cost model additive
   and scale-free) and on raw target (secondary). Scrambled Sobol sequence, dimension
   2k, base N = 2^15 (R1) or 2^14 (variants). First order: Saltelli 2010 estimator.
   Total order: Jansen estimator. Group total indices (swap a whole group of columns):
   by domain, all roots, all pinned inputs, lithography, nuclear/quark, each boundary
   family. Percentile bootstrap over rows (1000 for R1, 500 otherwise), 95% two-sided.
   Convergence ladder N = 2^10 ... max. Two extra scramble seeds at 2^14 for the primary pair.
6. Rank comparison, Kendall tau-b between total-order index ST and root debt:
   (a) roots that are factors of the target (PRIMARY); (b) all 619 roots, absent roots
   at ST = 0; (c) all factors including pinned inputs, using the dependents count;
   (d) boundary families (joint ST vs the family total weight the CLI prints);
   plus top-20 root-debt roots and where the top-10 ST roots sit in the debt order.
   tau CI: bootstrap that resamples roots and uses one Sobol bootstrap draw per replicate.

## Inputs

Preset values: `gpu_stack/presets/scenarios.py`, `scenarios_cited_2026.py`. Resolver:
`gpu_stack/core/resolver*.py`. Root debt: `gpu_stack/cli_root_debt.py`, re-implemented in
`sens_lib.root_debt` and matched to the CLI JSON (619 rows, 0 mismatches in smoke). The
runner records git HEAD, SHA-256 of `gpu_stack/**/*.py`, of each preset's assignments, of
the scripts and this protocol, seeds (main 20261001, replicates +1 and +2), versions, runtime.

## Decision criteria (frozen before any real index is computed)

Tiers, from the 95% bootstrap interval of ST on log target:
- negligible: upper bound < 0.01. major: lower bound >= 0.10. minor: lower >= 0.01.
  Otherwise ambiguous.
- Why 0.01: about the smallest value the design should resolve (CI half-width at
  N = 2^15 is assumed near 0.01 or less; C2 checks it) and below an equal share
  (1/k = 0.016 for k = 62). 0.10 is six equal shares.

Convergence gates: C1: for inputs with ST >= 0.01, |ST(N) - ST(N/2)| <= 0.02.
C2: every input's CI half-width <= 0.02 (failure only marks tiers ambiguous).
C3: against the replicate seeds, tau-b of ST >= 0.8 and top-10 overlap >= 8.
If C1 or C3 fail for a pair, every verdict on that pair is "inconclusive".

H1, root debt is a poor proxy for influence (the hypothesis under test). Test: tau-b in
comparison (a), pair P1 x cost_per_token x R1. One-sided 95% limits (5th and 95th
percentiles of the tau bootstrap).
- supported if the upper limit < 0.30; refuted if the lower limit >= 0.30; else inconclusive.
- Why 0.30: tau 0.30 corresponds to a Pearson-type correlation of sin(pi x 0.30 / 2) = 0.45
  (about 20% of rank variance explained). For n near 60 independent roots the null sd of
  tau is about 0.09, so 0.30 is roughly 3.4 sd above no relation: a tau at or above
  it is a real, if modest, association; below it the proxy is weak. The CI rule means a
  noisy point estimate cannot support the claim; the point estimate must be about 0.15
  or lower for "supported".
- Robustness: if the primary verdict differs under R1_f1.25 or R1_f4 it is reported as
  "inconclusive (rule-dependent)".
- Breadth: pairs with fewer than 10 factor roots are "not evaluable". H1 is "supported in
  general" only if the primary is supported and at least half of the evaluable R1 pairs
  are; otherwise "supported for the headline only".

H2a, lithography and nuclear/quark roots are inert at the shipped presets. Falsified if
any `physical.lithography.*` root is a free symbol of any target's resolved formula in
P1, P2 or P3. This is structural and I expect it to hold (no preset assigns a
lithography root; see Disclosures). It is stated so it is not read as a surprise.

H2b, lithography layers are decorative for cost per token in principle, i.e. through the
pinned cut points. Falsified if, in P1 x cost_per_token under R1_f1.25 (+-25%, a modest
swing in chip FLOPs or power), at least one cut point with lithography roots beneath it
(selected equations) has ST lower bound >= 0.01; supported only if none does. That is
a lenient falsifier (several cut points qualify), chosen because it tests the interface
quantity, not whether lithography can move it. No preset gives sourced values for the
physical roots, so that second question cannot be answered here and the report must say so.

H3 (descriptive, no threshold): the tier of each of the top-20 root-debt roots, and
the root-debt rank of the ten roots with the highest ST.

Morris tau vs Sobol ST below 0.5 is flagged for inspection; it changes no verdict.

## What each outcome means

- H1 supported: do not use the CLI ranking to decide which inputs to measure; use an
  influence ranking with a stated range. Refuted: the count is an acceptable first filter
  at these presets. Inconclusive: say so.
- H2a falsified: physics roots leak into headline numbers; inspect the preset.
- H2b falsified: lithography is not decorative, conditional on it moving the cut point;
  the next item is sourced physical values. Supported: it cannot matter even if it moved them.

## Compute budget

One process, one core. Smoke scaling (2^12 rows, k = 62, 20 bootstraps) took about 1 s.
Full run: 12 (preset, target) pairs, R1 at 2^15 plus three variants at 2^14, plus two
replicate seeds. Expected 30 to 60 minutes, under 2 GB RAM.

## Known limitations

- Sampling is independent except `par.n_gpus`. Other redundant pins (`thermal.dc.total_power`
  vs node power inputs, `gpu.peak_flops_power_limited` vs `gpu.tdp`) can be set
  inconsistently. Constraints are not checked per sample, so some samples may be invalid.
- Equal relative ranges make ST mostly reflect formula structure, not real uncertainty.
- Zero-nominal closures (overhead, exposed communication, carbon price) are held under R1;
  R4 ranges are my assumptions.
- Pinned cut points hide the physics below them, so this measures the presets, not the
  whole graph. Three presets, all small DGX H100 style runs; no measured data, so this is
  model sensitivity, not validation.
- `dc_power` has few factors, so tau there is not evaluable.

## Disclosures about Stage 1

- Structural facts seen while designing (not sensitivity results): the P1 cost-per-token
  formula has 71 free symbols, tokens/s 17, dc_power 5; 43 lithography roots lie under each
  of `gpu.peak_flops`, `gpu.power.total`, `thermal.dc.total_power`; root ancestors via any
  equation: 277, 206, 167 for the three headline targets. Smoke printed factor counts.
- Smoke: 2^5 rows, 4 bootstraps, written to the scratchpad and not read. An Ishigami check
  (analytic function, 2^13 rows) passed: max error 0.001 (S1), 0.0002 (ST).
