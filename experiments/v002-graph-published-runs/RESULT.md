# V002 result: graph vs published training runs

Run on the frozen protocol (git HEAD c8801eae310b93dbba8bab63c1af628c51b2a214). Dataset and
predict.py hashes matched. Raw output: `results/results.json` (every record, every arm).
Runtime 9 s on 2 cores. Metrics: MdAPE = median |pred/true - 1|; 95% CI = cluster bootstrap
over model families (10,000 reps).

## What happened

Time is accelerator-seconds per token. 27 tier-A records, 12 families. Tier A+B (31 records) gives the same story.

| Arm | MdAPE | 95% CI | median log error | Spearman | pair order acc |
|---|---|---|---|---|---|
| A: 6ND at 40% MFU | 0.219 | 0.125-0.287 | -0.229 | 0.994 | 0.918 |
| G0: graph as shipped (MFU 100%) | 0.682 | 0.591-0.715 | -1.145 | 0.994 | 0.918 |
| G1: graph + frozen MFU prior | 0.218 | 0.124-0.286 | -0.227 | 0.994 | 0.902 |

- G1 minus A in MdAPE: -0.0011, CI [-0.0012, +0.0016]. They are the same predictor.
- Leave-one-family-out MdAPE for G1: 0.203-0.244, so Pythia (8 of 27) does not drive it.
- G1 under-predicts 22 of 27 runs. Implied MFU (0.4 x A / truth) is below 0.40 for most
  runs: Pythia, MT-NLG, PaLM, Gopher, BLOOM, StarCoder, SmolLM3, BloombergGPT 0.22-0.32;
  Llama 1 and Llama 2 0.35-0.51.
- Interval [p5, p95] from `uncertainty.py`: covers 27 of 27, median p95/p5 = 2.92. The closed-form
  interval of the same prior gives 27 of 27 and 2.93. The graph adds nothing in propagation.
  100% against a 90% target means the interval is wider than needed; the criterion only tests under-coverage.
- Oracle MFU (G2, n=4): MdAPE 0.113 (A with reported MFU is identical). Per record G2/true:
  Llama 3.1 405B 0.84, PaLM 0.67, Gopher 0.93, MT-NLG 1.00. Fixed 40% on the same 4: 0.243.
- Energy (descriptive; each set has 1 tier-A cluster):
  - E1, hours given (3 TPU v3 records): MdAPE TDP x hours 0.42, x PUE 1.2 0.71, x reported PUE 0.55, graph 0.87.
    All over-predict (measured power is 0.64-0.69 of TDP). Graph interval covers 0 of 3.
  - E2, end-to-end (2 OLMo 2 records, GPU-only measured): TDP arm 0.23, PUE arm 0.20, graph 0.42; graph interval covers 1 of 2.
- S2, parameters from architecture (11 records): graph MdAPE 0.0003 (max error 0.09%); naive 12Ld^2 formula 0.0005 (worst 33% on SmolLM3, a gated-FFN GQA model).

## Verdicts against the frozen criteria (verbatim rules)

- Q1_graph_as_shipped_time: rule "MdAPE(G0) <= 0.33". G0 = 0.682. **FAIL.**
- Q2a_graph_plus_prior_accuracy: rule "MdAPE(G1) <= 0.33". G1 = 0.218. **PASS.**
- Q2b_interval_calibration_and_sharpness: rule "covered >= binom 5th percentile of Bin(n,0.9) AND median p95/p5 <= 4". 27 >= 22, ratio 2.92. **PASS.**
- Q2c_value_over_baseline_A: rule "cluster-bootstrap 95% CI of MdAPE(G1)-MdAPE(A) vs +/-0.02". CI [-0.0012, 0.0016]. **equivalent_to_baseline.**
- Q3_oracle_mfu_accounting: rule "MdAPE(G2) <= 0.15 (n small, descriptive)". 0.113, n=4. **PASS (descriptive).**
- Q4_E1_tierA and Q4_E2_tierA: rule "fewer than 6 independent clusters => no verdict". 1 and 1. **not_tested_too_few_clusters.**
- Q5_param_count_from_architecture: rule "MdAPE(graph params) <= 0.02". 0.0003. **PASS.**
- Money: not testable (every published dollar cost is hours x a stated rate).

## Plain reading

The README sentence is not supported as written: with the shipped neutral overheads the graph is about 3x
too fast on every run. With a prior for MFU it forecasts GPU-hours within about 22% (median) of published
values, but that is the 6ND baseline, not extra graph skill. Intervals are conservative. Parameter
counting from architecture works. Power and money claims remain untested here.

## Largest misses (G1 time, all records)

1. Llama 3.1 8B (tier B): predicted 0.35x truth, implied MFU 0.14. Likely cause: a small model at 15T+ tokens
   whose reported hours cover the long-context continuation and non-compute time, plus tokens given only as a lower bound.
2. Pythia 70M (tier A): 0.55x, implied MFU 0.22. Likely cause: tiny model, kernel-launch and data-loading bound; the prior assumes large-model MFU.
3. BloombergGPT 50B (tier A): 0.59x, implied MFU 0.24. Likely cause: activation checkpointing recompute and 50 Gbps cloud networking cost time that the 40% prior ignores.
Next: GLM-130B 0.63 (tier B), Pythia 160M 0.63. The only large over-prediction is Llama 1 13B (1.29x).
Largest energy miss: T5-11B E1 graph 1.7x true; cause: TPU v3 measured system power is about 0.69 of its 450 W TDP while the prior centers at about 1.1 x TDP (GPU load plus host share) times PUE.

## Deviations from protocol

None in code, data or criteria. Operational: run pinned to 2 cores (`taskset`); no smoke-test files remain; no `__pycache__` created.
The "implied MFU" values above are post-hoc arithmetic (0.4 x A / truth), not frozen outputs.

## Limits

12 families for time, 1 per energy set. Reported hours include restarts and idle time. Priors are judgments;
the 40% median is above what 22 of 27 runs achieved, so a lower median would score better, but that is not
a graph property and was not tried. Not covered: MoE/FP8, MLPerf, dollar cost.
