# E004: Fluid Inference Topology

Status: designed

Protocol date: July 12, 2026

No result is reported in this document. Every numeric threshold below is a
preregistered prediction or an evaluation requirement.

## Question

Should an inference fleet choose, per request and over the life of a request,
whether model execution is aggregated or disaggregated, where prefill runs,
where decode runs, where attention and experts live, which KV state moves, and
which precision or speculative path is used?

The stronger question is whether these choices have positive interaction
effects. If they do, a controller that reasons about them jointly should beat
both a fixed topology and a collection of independently tuned controllers that
have access to the same actions.

## Why This Is Genuinely Unanswered

Recent systems establish several important mechanisms, but each fixes most of
the surrounding topology:

- [HMA-Serve](https://arxiv.org/abs/2606.29986) separates prefill and decode
  across memory-heterogeneous, potentially cross-vendor devices and couples
  that choice to phase-wise quantization and KV transfer.
- [KernelFlume](https://arxiv.org/abs/2606.29207) makes attention capacity
  elastic independently of the weight-bearing path, with larger-model results
  partly projected by simulation.
- [Kairos](https://arxiv.org/abs/2607.02043) shows that queueing and KV transfer,
  rather than prefill execution alone, can dominate tail time-to-first-token
  and that selected requests can profitably return to an aggregated path.
- [TraceLab](https://arxiv.org/abs/2606.30560) exposes long contexts, short
  outputs, prefix reuse, and heavy-tailed tool gaps in real coding-agent
  sessions.
- [WattGPU](https://arxiv.org/abs/2607.02391) predicts mean inference power and
  latency on unseen GPUs, but not queue-coupled topology changes.

No cited system asks one policy to price weights, KV blocks, experts, draft
capacity, queue delay, network occupancy, and facility power under a shared
future-service objective. This is not a scheduler knob added to a known serving
design. It tests whether the serving design itself should repeatedly change as
request state and fleet pressure change.

## Why Datacenter Scale Is Required

The proposed effect is produced by multiplexing and shared-resource
interference. It cannot be established on one model replica or one rack.
Regime changes depend on concurrent request families, cross-rack network
oversubscription, replicated model and expert memory, heterogeneous device
pools, rack power limits, and the long-lived state of paused agent sessions.

The full claim therefore requires a live fleet with at least 1,024
accelerators across at least eight failure and network domains. Smaller systems
can calibrate mechanisms, but cannot validate the datacenter-level interaction
hypothesis.

## Preregistered Hypotheses

Define request service value as

`V = sum_r w_r * u_r * I_r`,

where `u_r` is a frozen, workload-specific utility score in `[0, 1]`, `w_r` is
a preregistered workload weight, and `I_r` is one only when the request or
session finishes inside its TTFT, TPOT, and end-to-end deadline constraints.
Rejected, expired, and silently degraded requests contribute zero. Define
facility efficiency as `U = V / E_facility`, including accelerator, host,
network, storage, and cooling energy inside the measured boundary.

The predictions are:

1. The joint controller will improve `U` by at least 20% over the best static
   topology selected on the development split.
2. It will improve `U` by at least 10% over an independent-controller ensemble
   with identical action access and compute budget.
3. Let `u(S)` be `U` normalized by the no-control baseline when control families
   in subset `S` are enabled. For topology `A`, state management `B`, and
   scheduling `C`, the three-way interaction
   `I_ABC = u(ABC) - u(AB) - u(AC) - u(BC) + u(A) + u(B) + u(C) - u(empty)`
   will be at least `0.05`, with its cluster-bootstrap 95% interval excluding
   zero.
4. In at least three of four held-out workload families, both aggregated and
   disaggregated execution will each account for at least 10% of request-time
   in at least half of evaluation traces. This is the preregistered test of the
   claimed repeated regime crossing.
5. Relative to the best static baseline, aggregate utility will fall by no more
   than 1% and SLO attainment by no more than one percentage point in every
   preregistered workload family.

These are predictions to test, not claims about an implemented controller.

## Virtual Datacenter State

The simulator state must include:

- request and session arrivals, prompt and output distributions, deadlines,
  priority, tenant, prefix lineage, tool-gap state, and frozen utility curves;
- dense and MoE model graphs, phase-specific precision choices, draft models,
  expert popularity, and quality constraints;
- device type, count, memory capacity, bandwidth, kernel curves, power state,
  and model or expert residency;
- prefill, decode, projection, attention, and expert queues;
- KV blocks with owner, location, precision, age, prefix-sharing set, transfer
  progress, and expected future reuse;
- rack and fabric topology, link contention, endpoint setup, packet loss, and
  cross-vendor transfer conversion costs;
- facility power caps, rack caps, cooling response, ambient state, and measured
  non-accelerator load;
- failures, fail-slow devices, recovery state, and migration side effects;
- uncertainty and provenance for every learned latency, power, quality, reuse,
  and arrival model.

The policy receives only observable telemetry available at decision time.
Future arrivals, latent utility, future failures, and simulator ground truth
remain hidden.

## Interventions

- run a request on an aggregated replica or a disaggregated execution graph;
- select prefill, decode, attention, and expert locations;
- add or remove weightless attention capacity;
- replicate, migrate, pin, quantize, reconstruct, or evict KV blocks;
- replicate or migrate experts and change expert-routing capacity;
- select model, phase precision, speculative draft, and speculation depth;
- route, batch, preempt, resume, defer, or reject a request, with all rejected
  and delayed work charged to the objective;
- change placement or topology at token, layer, or request boundaries when the
  implementation permits it;
- reserve rack power or network headroom when its expected future value exceeds
  immediate goodput.

Every intervention records state-movement bytes, pause time, conversion work,
energy, and the decision information set.

## Baselines

1. Best static aggregated serving topology.
2. Best static prefill/decode-disaggregated topology.
3. A mechanism-matched HMA-Serve-style memory-heterogeneous topology within the
   mechanism supported by public evidence.
4. A mechanism-matched Kairos-style prefill-deflection policy.
5. A mechanism-matched KernelFlume-style elastic-attention policy.
6. Independent controllers for topology, KV and expert state, precision and
   speculation, and request scheduling, trained separately and composed with a
   frozen conflict priority.
7. The same full action space controlled by a myopic one-step optimizer.
8. A clairvoyant offline oracle with future arrivals and failures, used only to
   bound decision regret.

All non-oracle baselines receive identical observations, hardware capacity,
profiling budget, warm state, and policy inference budget.

## Experimental Matrix

The confirmatory matrix crosses the following axes through a preregistered
fractional-factorial design, followed by full crossing of any detected
interaction cell:

- dense 8B to 70B models and MoE models with at least 100B total parameters;
- homogeneous HBM fleets, mixed HBM generations, and HBM plus lower-cost
  memory-heterogeneous fleets;
- aggregated, prefill/decode-disaggregated, and attention-disaggregated
  starting topologies;
- conversational, retrieval-heavy, long-context reasoning, and coding-agent
  workloads;
- low, medium, and saturation arrival rates with stationary, diurnal, burst,
  and correlated-tenant patterns;
- low and high prefix reuse, short and heavy-tailed tool gaps, and stable versus
  shifting expert popularity;
- nonblocking, 2:1 oversubscribed, and 4:1 oversubscribed fabrics with
  congestion bursts;
- unconstrained, rack-capped, and facility-curtailed power regimes;
- clean operation, visible device failure, fail-slow behavior, and link loss.

Each stochastic virtual cell uses 30 frozen seeds. A run covers 24 simulated
hours after a one-hour warm-up. Statistical resampling is by trace-day and
failure domain, never by individual request.

## Held-Out Splits And Leakage Controls

- Assign trace groups to 60% calibration, 20% development, and 20% evaluation
  before fitting. Split complete sessions and contiguous time blocks, not
  individual requests, so prefix-related requests cannot cross splits.
- The confirmatory evaluation contains four leave-one-group-out panels: one
  entire hardware family, one model family, one workload family, and one
  fabric-topology class absent from calibration.
- A fifth compound panel withholds a hardware, workload, congestion, and power
  combination even when each component appears separately in calibration.
- Utility labels, quality curves, and future-reuse labels from evaluation are
  inaccessible to the controller and calibration pipeline.
- Model selection stops after the development split. The evaluation split is
  computed once under a versioned protocol and immutable seeds.
- A policy must abstain or fall back to a named baseline when its
  out-of-distribution detector fires. Abstention frequency and value loss are
  reported.

## Outcomes

Primary:

- quality- and SLO-constrained service value per facility joule, `U`;
- P50 and P99 TTFT, TPOT, and session completion latency by workload family;
- SLO attainment and frozen utility by workload family;
- factorial interaction `I_ABC` and joint-versus-independent coupling gain;
- configuration-ranking correlation and intervention decision regret;
- 50%, 90%, and 95% prediction-interval coverage on held-out cells.

Secondary:

- useful requests and useful output units per second;
- KV, weight, expert, and draft-state movement bytes;
- cache hit rate, recomputation avoided, and state stranded at topology change;
- link utilization, queue occupancy, migration stalls, and batch fragmentation;
- accelerator, host, network, storage, and cooling energy;
- rack peak, ramp rate, and power-cap violations;
- policy compute overhead, action churn, and topology transition count;
- residual attribution by queue, memory, network, power, and model-quality
  mechanism.

All averages are accompanied by workload-family and tail results. Token
throughput alone cannot support the hypothesis.

## Falsifiers

The research claim is falsified if any of these survive uncertainty analysis:

- the joint controller misses either the 20% static-baseline threshold or the
  10% independent-controller threshold;
- the lower 95% bound of `I_ABC` includes zero, or the interaction point
  estimate is below `0.05`;
- a frozen static regime accounts for at least 90% of request-time in two or
  more held-out workload families;
- gains disappear when every baseline receives the same state-movement,
  policy-compute, and warm-cache accounting;
- any workload family loses more than 1% utility or one percentage point of
  SLO attainment;
- held-out ranking fails, intervention regret exceeds 10% of oracle value, or
  nominal 90% intervals cover fewer than 80% of held-out outcomes;
- simulated topology choices fail to transfer directionally to controlled real
  cluster interventions;
- the benefit is explained entirely by extra replicas, looser admission, or
  hidden quality degradation.

## Validation Ladder

1. Replay TraceLab and public serving traces; reproduce the direction, not an
   invented exact value, of published HMA-Serve, Kairos, KernelFlume, and
   WattGPU mechanism comparisons inside their disclosed regimes.
2. Measure kernels, transfers, queueing, power, and quality curves on 8 to 64
   accelerators across at least three device families.
3. Run controlled topology transitions and factorial ablations on 64 to 256
   accelerators with recorded network and rack-power perturbations.
4. Operate in shadow mode on at least two real serving clusters. Predict every
   action and outcome without controlling traffic.
5. Run a guarded live experiment on 256 to 1,024 accelerators with production-
   shaped traffic and fixed safety fallbacks.
6. Test the confirmatory protocol on at least 1,024 accelerators across eight
   failure and network domains using held-out workload weeks.

Only stages 5 and 6 can support a claim about live serving value. Only stage 6
can support the datacenter-scale interaction and regime-crossing claims.

## First Engine Slice

Implement the smallest substrate that can invalidate the virtual hypothesis:

- a request/session event schema with prefix lineage, deadlines, tool gaps,
  quality labels, and explicit calibration provenance;
- resource queues for prefill, decode, attention, experts, network, and rack
  power;
- first-class KV, weight, expert, and draft-state ownership and movement;
- aggregated and prefill/decode-disaggregated topologies with a reversible
  per-request transition;
- observable-state policy interfaces for topology and KV placement;
- facility energy and service-value accounting that charges rejected work and
  migration overhead;
- the static, independent-controller, myopic, and offline-oracle baselines;
- factorial ablation reports, held-out residuals, uncertainty coverage, and
  decision regret.

Expert disaggregation and speculative-control actions enter only after the
two-family interaction test is measurable and falsifiable.
