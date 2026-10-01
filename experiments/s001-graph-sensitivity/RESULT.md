# S001 result: which root inputs move the headline outputs?

Protocol frozen at 99c2e95ad118cd73454cc31e3594d2d525ea0af0 (`protocol.md`, unchanged).
Raw output: `results/` (`sobol__<preset>__<target>__<rule>.json`, `structure.json`,
`summary.json`, `provenance.json`). Numbers below come from `python report.py`
(read-only on `results/`). Run time 853 s, one core.

## What happened

Twelve (preset, target) pairs were run under rule R1 (log-uniform, half to double the
nominal) at N = 2^15, plus variants R1_f1.25, R1_f4 and R4 at N = 2^14. No sample row was
invalid (0 of every run). Sobol first-order sums were 0.98 to 1.00 and total-order sums 1.00
to 1.02, so the log-target is almost additive in these inputs: ST is close to S1, and
ranking mostly follows each input's exponent in the cost formula.

Structure (roots of 619; P1 = Pythia-70M full TCO; `structure.json`):

| target (P1) | roots reachable, any equation | in resolved formula | pinned cut points in formula |
|---|---|---|---|
| cost per token | 277 | 62 | 9 |
| tokens per second | 206 | 10 | 7 |
| datacenter power | 167 | 3 | 2 |

All 43 lithography roots (11 of them nuclear/quark by the frozen name rule) are reachable
for every target, but 0 are in any resolved formula, in all 3 presets and 4 targets.
They sit under pinned values: `gpu.peak_flops_power_limited` (133 roots beneath, 43
lithography), `gpu.power.total` (127, 43), `thermal.dc.total_power` (162, 43).
Joint total influence of lithography and of nuclear/quark roots: exactly 0 on every target.

## Top 10 inputs by total-order index (P1, R1, log target; 95% interval < 0.005 wide)

Cost per token: `arch.d_model` 0.232, `gpu.peak_flops_power_limited` 0.198 (a pinned
value, not a root), `arch.vocab` 0.096, `econ.asset.useful_life` 0.094,
`econ.cluster.utilization` 0.058, `cluster.node.n_gpus` 0.055, `econ.gpu.capex` 0.052,
`training.cluster_availability` 0.049, `training.recompute_overhead` 0.049 (pinned),
`training.optimizer_flop_multiplier` 0.049. Tiers: 2 major, 12 minor, 48 negligible of 62.

Tokens per second (15 factors): `arch.d_model` 0.219, `cluster.node.n_gpus` 0.193,
`gpu.peak_flops_power_limited` 0.187, `cluster.rack.n_nodes` 0.092, `cluster.site.n_racks`
0.092, `arch.vocab` 0.091, `training.optimizer_flop_multiplier` 0.047,
`training.recompute_overhead` 0.047, `arch.n_layers` 0.021, `arch.d_ffn` 0.011. The three
node counts act only through the tied `par.n_gpus`.

Datacenter power: 4 factors. `thermal.dc.total_power` (pinned) 1.000; the three
node/rack/site counts 0.000. In this preset the power answer is the pinned 10.2 kW.

Raw-target Sobol (secondary) gives the same top 6 inputs for cost per token (two swap places) and agrees on 47 of 48
negligible inputs. Morris mu* vs ST tau-b: 0.96 (primary), 0.56 to 0.95 elsewhere; none
below the 0.5 flag.

## Convergence gates

- C1 (largest change in ST over the last doubling, ST >= 0.01): passes in all 12 R1 pairs;
  worst 0.0005 (limit 0.02).
- C2 (largest CI half-width): passes in all 12; worst 0.0107 (`dc_power`), primary 0.0036
  (limit 0.02).
- C3 (primary pair, two replicate seeds at 2^14): tau-b 0.989 and 0.994, top-10 overlap
  10 and 10 (limits 0.8 and 8). Pass.

## Verdicts against the frozen criteria

**H1** "supported if the upper limit < 0.30; refuted if the lower limit >= 0.30; else
inconclusive." Primary (P1 x cost per token x R1, tau-b over n = 57 factor roots): tau-b
0.038, one-sided 95% limits [-0.159, 0.215]. Upper limit 0.215 < 0.30, so SUPPORTED.
Robustness: also supported under R1_f1.25 (tau -0.091, upper 0.080) and R1_f4 (0.019,
upper 0.197), so no rule dependence. Breadth rule: pairs with at least 10 factor roots are
P1 cost, P1 tokens/s, P1 run power cost, P3 cost, P3 tokens/s, P3 run power cost (the P2
pairs and every `dc_power` pair have 9 or fewer). Only 1 of these 6 is supported; the other
5 are inconclusive (point estimates 0.13 to 0.34, upper limits 0.47 to 0.64, with 12 to
16 roots). The criterion therefore gives "supported for the headline only", not "supported
in general". Not refuted anywhere. Context: tau-b over all 619 roots is 0.118 (557 roots
have ST = 0), and the family-level tau-b is 0.30 on only 21 families.

**H2a** "Falsified if any `physical.lithography.*` root is a free symbol of any target's
resolved formula in P1, P2 or P3." None is (0 of 12 formulas, checked also across all
variant runs). NOT FALSIFIED. As the protocol said, this was structural and expected.

**H2b** "Falsified if, in P1 x cost_per_token under R1_f1.25, at least one cut point with
lithography roots beneath it has ST lower bound >= 0.01." `gpu.peak_flops_power_limited`
has ST 0.194, interval [0.190, 0.198], local elasticity -1.00. FALSIFIED. Qualifiers: the
other two cut points with lithography beneath them are negligible (`gpu.power.total`
ST 0.0000, `thermal.dc.total_power` 0.0006), so the whole conduit is one number, the
effective per-GPU FLOP rate, which the preset pins to the H100 datasheet 67 TFLOPS. The
criterion tests the interface, not whether lithography can move it; no preset sources the
physical roots, so how much lithography could change that FLOP rate is not answered here.

**H3** (descriptive). The 20 highest root-debt roots are all `physical.lithography.*`;
0 of 20 are factors of cost per token, so 0 are non-negligible. The 10 roots with the
highest ST on cost per token have debt ranks (of 619) 131, 162, 286, 280, 129, 227, 256,
215, 158, 116: none is in the top 100.

## Reading

In these three presets the lithography/nuclear layers have no influence, because the
presets pin the chip's FLOP rate and power. Influence comes from workload size (width,
vocabulary), the pinned FLOP rate, GPU count, and a few economics inputs (asset life,
utilization, GPU price). The root-debt count does not order those. It is a poor guide for
cost per token at this nominal point, but the other pairs had too few roots to say so.

## Deviations and caveats

- `report.py` was added after the freeze; it only prints from `results/`. `run.py` and
  `sens_lib.py` are byte-identical to the frozen commit.
- `provenance.json` git HEAD is 2cb4e61, newer than the freeze commit; `gpu_stack/` had
  no uncommitted changes. Protocol SHA-256 matches the frozen file.
- "Seed replicates" were run only for the primary pair, as the protocol states.
- Ranges are equal-relative by design, so ST mostly reflects formula structure. Sampling
  ignored constraints; redundant pins other than `par.n_gpus` were sampled independently.
  The 62 to 15 to 4 factor counts depend on those rules and on holding zero-nominal
  inputs (R4 shows the same primary verdict: tau -0.025, supported).
- `training.recompute_overhead` appears as a "pin" (it has a defining equation in the graph
  but is assigned in the preset), so it is not in the root-only tau.
- No measured data. This is model sensitivity, not validation.
