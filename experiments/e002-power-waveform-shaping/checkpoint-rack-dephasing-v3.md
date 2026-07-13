# E002-PW3: Recovery-Graph Rack Dephasing

Status: frozen for physical execution. No PW3 result exists yet.

Machine contract:
[checkpoint-rack-dephasing-scenario-v3.json](checkpoint-rack-dephasing-scenario-v3.json)

Telemetry deployment contract:
[checkpoint-rack-telemetry-v3.example.json](checkpoint-rack-telemetry-v3.example.json).
The checked-in file fixes channel identities, rates, boundaries, and
environment-variable names. A rack deployment replaces the `.invalid`
Prometheus endpoint and example label bindings with the named physical meters,
then removes every `metadata.example_not_a_measurement_binding` flag. The
runtime rejects a config while any required channel still carries that flag;
binding the instruments does not change the scientific scenario.

PW2 established a local GPU-board checkpoint-cadence mechanism under its
preregistered raw cumulative-energy estimand. It did not establish that the
effect survives idle-baseline treatment, simultaneous GPUs, shared storage,
rack power, or cooling. PW3 crosses that boundary directly.

## Research Question

Does a distributed training recovery graph contain controllable electrical
phase slack? Specifically, can an online controller phase-decorrelate
checkpoint capture and durable offload, survivor updates, state transfer,
communicator rebuild, and rejoin across independent two-site training jobs
while preserving one globally recoverable cut and the exact learning
commitments of the unshaped schedule?

This is not generic checkpoint staggering. The intervention is constrained by
the state-generation DAG, durability deadline, rollback bound, live storage
queue, and observed rack waveform. A move is legal only while all predecessor,
consistency, and recovery obligations remain satisfied.

## Why This Is Still Open

Recent systems results expose the separate pieces but not their joint causal
frontier:

- [EasyRider](https://arxiv.org/abs/2604.15522) targets 100 ms to 10 s
  synchronized power transients with rack hardware. Its physical prototype is
  about 10 kW and it does not use optimizer or recovery-graph semantics.
- [Power-Flexible AI Data Centers](https://arxiv.org/abs/2606.25098) controls a
  real 96-Blackwell, 130 kW cluster, but its one-second GPU and slower rack
  telemetry target tens-of-seconds flexibility rather than checkpoint/rejoin
  transients.
- [TierCheck](https://arxiv.org/abs/2605.17821) paces checkpoint microchunks on
  16 A800 GPUs to reduce training/I/O interference without measuring an
  electrical or thermal outcome.
- [PHOENIX](https://arxiv.org/abs/2607.01646) demonstrates hot recovery through
  512 A100 GPUs in under 40 seconds without power or energy telemetry.
- The [504-B200 operational
  study](https://arxiv.org/abs/2605.09370) observes highly concurrent save
  bursts and storage queueing, while its 30-second telemetry cannot resolve the
  burst peak.
- [Cross-layer Grace Hopper energy
  characterization](https://arxiv.org/abs/2605.01938) measures up to 128 GPUs
  at 100 ms and shows asynchronous overlap can smooth a node trace, but it does
  not test failure, rejoin, shared rack PDU, or globally recoverable cuts.
- [ResiHP](https://arxiv.org/abs/2605.06374) shows on 256 A100 GPUs that one
  degraded device propagates through tensor, pipeline, and data parallelism.
  It adapts parallelism and microbatches for throughput, not the joint
  recovery-consistency-electrical objective.

The unanswered question is whether consistency-safe recovery slack is a real
rack control resource, or whether the apparent slack disappears once learning,
durability, storage, and electrical measurements share one boundary.

## Physical Hypothesis

On a physical rack with at least eight simultaneously active GPUs arranged as
at least four independent two-rank jobs, telemetry-feedback dephasing will,
relative to synchronized earliest-ready recovery execution over equal useful
work:

1. reduce the paired `p99.9 |dP/dt|` at the rack-PDU boundary by at least 30%;
2. reduce paired rack-PDU spectral energy integrated over 0.1 to 10 Hz by at
   least 30%;
3. reduce both quantities by at least 15% relative to seeded random jitter;
4. regress useful-token throughput by no more than 1%;
5. increase total rack joules per useful token by no more than 2%;
6. regress p95 recovery time by no more than 5%;
7. preserve every state-generation, durable-cut, rollback, sample-order,
   optimizer-step, and held-out learning-equivalence obligation.

The percentages are GPUSTACK preregistration choices, not values reported by
the sources. The rack mechanism passes only if every primary and constraint
gate survives its paired interval. It does not resolve E002's later
point-of-common-coupling or admission-capacity claims.

## Policies

Each physical block executes the same job states under five policies in a
frozen balanced order:

1. `synchronized`: every ready state-flow operation releases immediately;
2. `random_jitter`: seeded legal jitter without telemetry feedback;
3. `throughput_pacing`: legal chunk timing minimizing storage queueing only;
4. `static_cohorts`: rotating dependency-safe cohorts fixed before the block;
5. `telemetry_feedback`: online slot selection minimizing predicted rack ramp
   and storage pressure from currently visible measurements.

No policy receives a future sensor trace, future operation duration, hidden
failure information, or evaluation outcome. The shaped policy may abstain when
clock or sensor uncertainty makes a legal decision unidentifiable.

## Exact Learning And Recovery Invariant

Within every block and workload, all policies receive the same:

- initial model, optimizer, random-number, and sample-order commitments;
- useful token count, quota identities, failure clock, and rank membership;
- sparse-continuation semantics inherited from PW2;
- checkpoint state generation, payload content, durability requirement, and
  rollback deadline;
- held-out evaluation batches and learning-equivalence margin.

Every moved operation records its predecessor IDs, state generation, earliest
release, scheduled release, actual interval, deadline, bytes, and outcome. A
checkpoint is globally recoverable only after the complete state generation is
flushed and fsynced. A rejoining rank cannot contribute until state transfer,
communicator rebuild, and the rejoin commitment complete.

The intervention may change wall-clock timing only. A different sample order,
missing quota, stale gradient contribution, changed optimizer update, mixed
checkpoint generation, incomplete durable cut, rollback-bound violation, or
learning result outside the frozen equivalence band is a failed arm.

## Direct Measurement Boundary

The primary rack claim requires all of the following on one reference clock:

- per-GPU cumulative energy and ancillary power at an effective interval below
  100 ms;
- rack-PDU power with an effective integration interval at or below 50 ms;
- shared-storage request/byte activity and a separate measured storage-power
  channel at or below 100 ms;
- cooling power and inlet/outlet temperature at or below one second;
- operation events with clock uncertainty below 25 ms.

Storage bytes never stand in for storage power. Summed GPU power never stands
in for rack-PDU power. A static PUE never stands in for cooling response.
Missing primary PDU samples, excessive clock uncertainty, nonmonotone energy
counters, incomplete event windows, or absent required storage/cooling channels
invalidate the affected claim rather than invoking a modeled substitute.

## Workload And Failure Slice

The first physical slice uses at least eight GPUs, one process per GPU, and
two-rank jobs preserving the two-site quota semantics that produced PW2.
Healthy sites train concurrently and merge their model and Adam state exactly
as the local two-site runner did. During a frozen availability interval, the
affected rank stays alive but contributes no quota; its partner performs both
deterministic quota identities. Rejoin transfers the survivor state, rebuilds
the job communicator, and resumes only after the explicit rejoin commitment.

The rack-relevant byte-level transformer uses TinyStories with the PW2 dataset
identity, 256-token context, 12 layers, width 768, 12 heads, and MLP width 3072.
Every arm completes 256 logical ticks and 524,288 useful tokens per job. Sparse
checkpoints occur every 16 healthy ticks and every four reduced-membership
ticks. Two frozen interruption windows create checkpoint, survivor, transfer,
and rejoin flows without killing the measurement processes.

This larger model is a new PW3 workload, not evidence that PW2 transferred
across model scale. The paired exact-state and held-out learning gates apply
inside PW3 itself.

## Analysis

Calibration blocks are excluded from claims. Evaluation blocks use complete
arm-level pairing and frozen arm order. The report includes every paired block,
the median effect, and the preregistered 90% paired-bootstrap interval.

Rack PDU samples are analyzed on their native integration windows. Primary
ramp uses the p99.9 absolute first difference divided by the reference interval.
Spectral energy integrates a detrended, windowed rack trace over 0.1 to 10 Hz
and reports its distribution across complete checkpoint/rejoin episodes.
Event-window coincidence reports the maximum simultaneously active state-flow
fraction and overlap-weighted bytes.

GPU energy, rack energy, storage energy/activity, cooling energy, peak power,
temperature, checkpoint latency, rejoin latency, useful tokens, attempted
tokens, final held-out NLL, and exact state commitments remain adjacent. An
apparent rack improvement that moves load into another measured boundary or
does less useful work is a failure.

## Decision

- If telemetry feedback clears every primary and constraint gate, advance to
  multi-PDU correlated-failure PW4 while retaining the rack-only boundary.
- If static cohorts or throughput pacing match it within uncertainty, reject
  the closed-loop novelty and keep the simpler policy.
- If rack ramp falls but energy, recovery, or learning reverses, publish the
  tradeoff and redirect the controller objective.
- If exact dephasing has no electrical effect, reject semantic slack as a useful
  rack control resource.
- If the required meters or clocks are absent, publish `measurement_invalid`;
  do not substitute the virtual datacenter for the physical result.

## Current Execution Blocker

The development machine exposes one RTX 3060 Laptop GPU. Locally stored cloud
credentials do not expose tenant-visible rack PDU, storage-power, or cooling
telemetry. A valid PW3 result therefore requires a named physical rack target
with at least eight GPUs and the bound measurement channels above. Engine and
instrumentation work can proceed locally; the research conclusion cannot.

## Physical Execution Path

On a single instrumented eight-GPU node, the complete run is launched once as:

```powershell
torchrun --standalone --nnodes 1 --nproc-per-node 8 -m gpu_stack.cli experiment-run E002-PW3 `
  --scenario experiments/e002-power-waveform-shaping/checkpoint-rack-dephasing-scenario-v3.json `
  --dataset E:\data\TinyStories\0000.parquet `
  --telemetry-config E:\gpustack-rack\checkpoint-rack-telemetry-v3.json `
  --output E:\gpustack-rack\results\checkpoint-rack-dephasing-v3.json `
  --raw-output-dir E:\gpustack-rack\raw\checkpoint-rack-dephasing-v3 `
  --observatory-output docs\data\e002-rack-dephasing-v3.json
```

For a multi-node rack, the same command uses the site's `torchrun` rendezvous
arguments and one process per visible GPU. Rank zero owns the compact result
and observatory projection; every rank writes UUID-bound raw telemetry into the
shared raw directory. This command executes the calibration and frozen
evaluation blocks. There is no synthetic, dry-run, or summed-GPU-power mode.
