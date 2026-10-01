# V002: Can the graph predict published training runs?

Status: STAGE 1 (protocol and code only). No held-out prediction has been run.

## Question

The README says gpu_stack "predicts what a training run does to time, power, and money, says how
sure it is". It has never been compared with real runs it was not tuned on. This study compares
it with published runs and with two simple rules.

## What the graph can and cannot do (read from the code, not run on the data)

- Dense training FLOPs are `6 * params * tokens` (`arch.eq.flops_step_dense`, scopes/architecture_ffn.py).
  So the graph's time is `6ND / (peak * MFU)`, the same formula as baseline (a). Its only extra freedom is MFU.
- MFU enters through `training.t_exposed_comm`, `training.t_mem_bound`, `training.overhead_fraction`
  and `training.cluster_availability`. Every shipped preset sets them to 0 or 1 (MFU = 100%).
  Deriving them from first principles needs about 14 more roots (alpha/beta, bucket counts, bandwidth
  efficiencies, parallelism degrees) that no preset and no published run supplies in full.
- `gpu_stack/uncertainty.py` has no default distributions. Intervals come only from priors I supply.
- Electricity cost is `tariff * dc_power * wallclock` (`econ.eq.run_power_cost`). With tariff = 1 USD/kWh
  the "cost" is energy in kWh. `dc_power` needs node and facility roots that no source gives per run.
- Therefore the testable claim is: "graph plus honest priors". The graph as shipped (G0) is also scored,
  because that is the README claim as written.

## Inputs

`heldout-runs.json` (frozen, SHA-256 below): 39 records from primary sources, each number with source,
page/table and a short quote; derived numbers show their arithmetic; 14 candidates are listed as
excluded with reasons (OPT, MLPerf, DeepSeek-V3, GPT-3 time, all TDP-derived energy, all dollar costs).
Source files are pinned by SHA-256. Tier A = every needed number explicit, rounding <= ~5%, no author-flagged
assumption. Tier B = bounded, coarsely rounded or partly assumed; sensitivity only.

| Set | Records (tier A) | Independent clusters | Tier B extra |
|---|---|---|---|
| T1 time (GPU-seconds per token) | 27 | 12 | 4 |
| T2 oracle-MFU time | 4 | 4 | 0 |
| E1 energy given reported hours | 3 | 1 | 2 |
| E2 end-to-end energy | 2 | 1 | 1 |
| S2 parameter count from architecture | 11 | 4 | 0 |

Cluster = model family (same paper, hardware, team). Pythia is 8 of 27 T1 records, so every statistic
is also reported with Pythia removed (leave-one-cluster-out).

## Prediction procedure (frozen in predict.py, FROZEN and CRITERIA dicts)

Inputs taken from the record: params, tokens, accelerator type (peak dense 16-bit FLOP/s and TDP from
`hardware_specs`), accelerator count (cancels in time; 1024 if unreported). For MT-NLG throughput
records the "tokens" are one step (1920 x 2048). Target is accelerator-seconds per token, which is
total GPU-hours x 3600 / tokens, so token errors cancel.

Never given to a prediction arm: reported GPU-hours, wall time, MFU (except arm G2), power, PUE
(except arm c_oracle), energy. Reported hours are the target in T1 and an input only in E1, by design.

Time arms (T1):
- A: `6 * params / (peak * 0.40)`.
- G0: graph as shipped. `resolve("training.wallclock")` with overhead_fraction 0, availability 1, recompute 1.
- G1: graph plus prior. Step time = compute time x (1 + f), MFU = 1/(1+f). f ~ lognormal(median 1.5,
  sigma_log 0.55): MFU median 0.40, 5-95% range 0.21-0.62. Point = median, interval = 5th/95th percentile
  from `propagate_uncertainty` (20,000 samples, seed 20261001). The closed-form interval of the same
  prior is also scored, as a check that the graph adds nothing in propagation.
- G2: oracle MFU. f = 1/MFU_reported - 1 (T2 records only; PaLM-convention MFU without attention FLOPs
  where both are given). Tests accounting (units, peak, FLOP convention), not prediction.

Energy arms (kWh from `econ.run.power_cost` at 1 USD/kWh; MWh below):
- b: TDP x accelerator-hours. c: b x 1.20. c_oracle: b x the record's reported PUE.
- Graph: GPU power = TDP x u, u ~ U(0.5, 1.0); non-GPU node power = kappa x node GPU TDP, kappa ~ U(0.10, 0.60);
  facility overhead (PUE-1) ~ U(0.05, 0.35). Scope follows the record: system scope uses all three;
  GPU-only scope (OLMo 2) uses u only and no PUE. E1 fixes wall clock from the record; E2 takes it from G1.
- No sourced facility or node roots exist for these runs, so the graph energy arm is baseline c plus
  priors. A win would be credited to the priors, not to graph structure.

S2 arm: graph `arch.params_total_dense` from architecture vs published count; baseline = `12 L d^2 + V d`.

## Prior choices (a priori, not tuned)

- MFU 0.40 median: the task-specified baseline. Anchor outside the held-out set: Megatron-LM Table 1
  (arXiv 2104.04473 PDF p16) reports 43-52% for tuned A100 benchmarks; real runs are usually lower, so
  the median sits a little below and the width is wide (sigma 0.55 gives a time ratio p95/p5 of 2.93).
- u, kappa, PUE ranges: TDP is an upper bound on draw (Luccioni PDF p4; Llama 2 PDF p6); DGX A100 is
  6.5 kW max for 8 x 400 W (NVIDIA datasheet), so non-GPU load can reach ~1.0x GPU TDP at maximum.
  Ranges were set before looking at any prediction. They are judgments, not measurements.
- Disclosure: while assembling the data I saw reported values. I did mental arithmetic on two records
  (BLOOM implied MFU about 0.32; Llama 3.1 405B implied about 0.34 vs reported 0.38-0.43), saw
  Patterson's measured power vs TDP, and saw one graph output (Pythia-70M parameters from architecture:
  70,397,952 vs 70,426,624 derived from the paper). No threshold was set from these. Thresholds below
  come from arithmetic and cited ranges.

## Metrics

Per arm: median absolute percent error MdAPE = median |pred/true - 1|; median log error (bias);
90th-percentile APE; interval coverage and median p95/p5; Spearman rank correlation; pairwise order
accuracy on pairs whose true ratio is 1.2-3 (rank correlation across model sizes is near 1 for any
6ND method, so pairs are the informative version). Cluster bootstrap (10,000 reps, seed 7) for CIs.

## Decision criteria (applied mechanically by run.py `verdicts`)

Each can pass or fail; a failure is a result, not a bug.

1. Q1 graph as shipped (G0): pass if MdAPE <= 0.33. Reason: 0.33 = 0.40/0.30 - 1, so any run whose true
   MFU is between 0.30 and 0.50 counts as "right". I expect G0 to fail (it assumes MFU = 100%); it is scored
   because the README claim was made without a prior.
2. Q2a graph plus prior (G1): pass if MdAPE <= 0.33. Same reason.
3. Q2b intervals: pass if covered >= 5th percentile of Binomial(n, 0.90) (22 of 27 for T1) AND
   median p95/p5 <= 4. Sharpness cap 4 = an interval from MFU 0.2 to 0.8, beyond which it is not a forecast.
4. Q2c value over baseline A: delta = MdAPE(G1) - MdAPE(A), cluster-bootstrap 95% CI. Graph better if
   upper bound < -0.02; equivalent if CI inside +/-0.02; worse if lower bound > +0.02; else inconclusive.
   Margin 0.02 = Monte Carlo and rounding noise level. Since G1 and A share formula and median, the
   expected outcome is "equivalent"; a graph win would need structure the code does not have.
5. Q3 oracle MFU (G2, T2, n=4): descriptive. Pass if MdAPE <= 0.15 = about 10% non-productive time
   (Llama 3 paper PDF p13: ">90% effective training time") plus about 5% rounding in tokens and hours.
6. Q4 energy: if a set has fewer than 6 independent clusters the verdict is "not tested", whatever the
   errors. E1 has 1 tier-A cluster and E2 has 1, so this is expected. Numbers are still reported.
7. Q5 parameter count from architecture (S2): pass if MdAPE <= 0.02. The equations omit biases and some
   norms, which are each below 1-2% of parameters in large models.
8. Money: not testable. Every published dollar cost found is GPU-hours x a stated rental rate. The
   only graph money output testable here is electricity, folded into the energy arms.

## What each outcome would mean

- G0 fails, G1 passes Q2a and Q2c says equivalent: the graph is a 6ND calculator until someone supplies
  MFU roots; the README sentence is true only with a prior from outside the graph.
- G1 fails Q2a: even a competent MFU prior does not reach the 0.30-0.50 band on real runs; budgeting
  claims should be withdrawn or restricted to the regimes where it works (see by-cluster tables).
- G2 fails Q3: there is an accounting gap (FLOP convention, peak, hours definition) separate from MFU.
- Q2b fails with good Q2a: point forecasts are fine, the "says how sure it is" claim is not.

## Compute and files

Resolver and Monte Carlo runs are lambdified: about 0.5 s per record per arm, under 5 minutes total on
4 CPU cores, no GPU. `build_dataset.py` made `heldout-runs.json` (no network). `predict.py` arms.
`run.py` writes `results/results.json`, and refuses to run unless the hashes below match.
`synthetic-smoke.json` is one made-up run, used only to test the code (`run.py --smoke`).

## Known limitations

- Small independent n: 12 clusters for time, 1 for each energy set. Energy and money cannot be settled here.
- Reported GPU-hours include restarts, evaluation and queue time that a physics model would not predict.
- Three records use "nominal" parameter counts; Falcon, GLM, Llama 3.1 8B/70B are tier B.
- MT-NLG records are throughput benchmarks, not runs. Gopher and PaLM hours are products of reported chip counts and hours.
- Published MFU conventions differ (model vs hardware FLOPs, attention included or not); G2 uses the 6ND-matching value where given.
- Peak FLOP/s assumes dense BF16/FP16; H100 989 TFLOP/s is derived as half of NVIDIA's with-sparsity figure.
- The graph arms cannot fail "for the graph's sake" when priors dominate: coverage tests my priors.
- Not covered: MoE and FP8 runs (DeepSeek-V3 excluded), inference, MLPerf, networks of failures.

## Freeze record

- heldout-runs.json SHA-256: 92f46f557fce538a5e012446a11cd746a4dcddbcae4f53ec9617ce58cfeeb6d1
- predict.py SHA-256: bd0818d60c7eabc42abbecffb7d5bc0e73d37a41acd6bb029f5692d1b4e4a37f
- run.py carries both hashes in FROZEN_DATASET_SHA256 and FROZEN_PREDICT_SHA256.
- Stage 2 starts only when the coordinator says "protocol frozen at <sha>". Deviations go in RESULT.md.
