# GPUSTACK Research Program

Status: July 12, 2026

## Telos

GPUSTACK is one system with three expressions:

- **Engine:** a causal and uncertainty-aware virtual AI datacenter that predicts
  training, inference, power, reliability, thermal, and economic behavior.
- **Medium:** an interactive causal observatory that can explain the same result
  to a freshman or expose PhD-level mechanisms, equations, provenance, and raw
  evidence without changing the underlying truth.
- **Research lab:** an experimental environment for screening datacenter-scale
  ML systems hypotheses before asking for expensive real-world validation.

These are a feedback loop, not three product tracks. Measurements calibrate the
engine. The engine powers the visual explanation. The visual explanation makes
the hypothesis and its assumptions inspectable. Experiments produce new
measurements.

## Scientific Position

Recent systems can already simulate operator timelines accurately, optimize
individual serving mechanisms, switch parallelism online, or control facility
power. The open problem is their interaction.

GPUSTACK should answer questions of this form:

> Under uncertain workload, hardware, network, failure, thermal, and grid
> conditions, which intervention most improves time-to-capability or useful
> service, why, and how likely is that conclusion to survive transfer to a real
> datacenter?

The primary score is not equation count, root count, test count, or in-sample
fit. The primary scores are:

- held-out predictive error and uncertainty coverage;
- configuration-ranking and intervention decision regret;
- time-to-loss or capability target for training;
- useful, quality-constrained service for inference;
- facility energy, power waveform, cost, and reliability;
- correct causal residual attribution;
- successful falsification or survival of preregistered hypotheses.

## Engine Contract

The next engine must add the following concepts without discarding the current
symbolic registry:

1. **Observation** records measured values, timestamps, topology, workload,
   software, instrumentation, uncertainty, and provenance.
2. **Calibration split** and **evaluation split** prevent a scenario used for
   fitting from becoming its own proof.
3. **Temporal state** represents operations, queues, data movement, state
   ownership, failures, recovery, power, and thermal response.
4. **Intervention** represents an action such as changing parallelism,
   consistency, placement, precision, frequency, batching, checkpoint cadence,
   routing, or cooling control.
5. **Policy** chooses interventions from observable state without access to
   hidden simulator truth.
6. **Learned residual** may correct a physical model, but it must carry a named
   scope, training data, uncertainty, and out-of-distribution behavior.
7. **Experiment** freezes a hypothesis, baselines, variables, metrics,
   falsifiers, seeds, and validation path.

## Visual Medium Contract

The primary artifact is a causal observatory, not an equal-weight dashboard.
Each result uses semantic zoom:

1. **Question:** a plain-language claim and the immediate answer.
2. **Mechanism:** the few causal paths responsible for the result.
3. **Regime:** bottlenecks, counterfactuals, tradeoffs, and uncertainty.
4. **Model:** equations, constraints, distributions, and policy decisions.
5. **Evidence:** observations, provenance, residuals, raw traces, and known
   missing mechanisms.

Core views:

- a causal dependency and intervention map;
- an event timeline aligned with network, rack power, thermal, and grid traces;
- counterfactual small multiples with uncertainty intervals;
- residual attribution showing where prediction and observation diverge;
- an experiment notebook that presents hypothesis, controls, results, and
  falsification status as one shareable state.

Essential values remain visible without hover. URL state captures experiment,
scenario, target, selected intervention, time range, uncertainty mode, and zoom
depth. Mobile uses the same reading order with tap and focus interactions.

## Ranked Frontier Programs

### 1. Beyond One Datacenter

Can a frontier model train efficiently across heterogeneous, intermittently
powered datacenters rather than one tightly synchronized site?

Hypothesis: a controller that jointly changes local-step count, communication
topology, pipeline delay, optimizer correction, parallelism, and site
membership can retain at least 95% of centralized loss progress per training
FLOP while using at least 10 times fewer inter-site bytes under realistic power
interruptions.

The virtual experiment is specified in
`experiments/e001-beyond-one-datacenter/experiment.md`.

### 2. Shape The Power Waveform

Can phase offsets across compute, collectives, checkpoints, and colocated jobs
remove dangerous facility and grid oscillations without slowing learning?

Hypothesis: optimizer-preserving phase shaping can reduce grid-danger-band
spectral energy by at least 50% with no more than 2% time-to-target regression,
and can admit 10% more active accelerators under the same power envelope.

### 3. Semantic Fault Tolerance

Can hard failures, fail-slow devices, and silent corruption be treated as
bounded learning perturbations instead of job-ending events?

Hypothesis: trajectory-sensitivity-guided canaries and selective redundancy can
keep final behavior statistically indistinguishable from a clean run with less
than 2% overhead under empirically structured fault processes.

### 4. Fluid Inference Topology

Should prefill/decode placement, KV movement, precision, expert replication,
speculative drafting, and aggregation be selected per request and changed
continuously?

Hypothesis: joint control produces superadditive gains because independent
policies move queue, memory, network, and power pressure into one another. The
optimal system repeatedly crosses between aggregated and disaggregated regimes.

### 5. Architecture As A Datacenter Variable

Can heterogeneous accelerators support a better model architecture under a
fixed facility envelope, rather than merely running a fixed architecture more
cheaply?

Hypothesis: jointly choosing modules, routing, precision, device type,
parallelism, and placement improves capability per facility joule by at least
25% over the best homogeneous design at equal power and wall-clock budgets.

### 6. Firm Grid-Responsive Inference

Can an inference datacenter offer predictable demand response without a hidden
quality or tail-latency cliff?

Hypothesis: request-conditioned control across model choice, precision,
batching, routing, DVFS, and placement provides more firm power flexibility
than any isolated mechanism while preserving per-request utility.

## Research Rules

- The virtual datacenter screens hypotheses. It never serves as the sole
  evidence for a claim about a real datacenter.
- Every experiment has a falsifier and reports negative results.
- Every claimed improvement includes the metric most likely to reverse it,
  such as time-to-capability beside throughput or facility power beside GPU
  energy.
- Every model comparison uses identical observations, splits, and accounting
  boundaries.
- Root-debt work enters the research queue only through an observed residual,
  decision-relevant uncertainty, or experiment requirement.
- Draft PR #14 remains parked until its nuclear and quark decomposition affects
  one of those criteria.

## Build Order

1. Observation schema, calibration/evaluation splits, benchmark runner, and
   baseline models.
2. Event and state graph with shared-resource contention and facility traces.
3. Intervention and policy interface with decision-regret evaluation.
4. Experiment 001 virtual environment and preregistered evaluation.
5. Causal observatory views over live experiment artifacts.
6. Shadow-mode comparison against real cluster telemetry before any controller
   is trusted with live actions.
