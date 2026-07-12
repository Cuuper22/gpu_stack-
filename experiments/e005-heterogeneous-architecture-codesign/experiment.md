# E005: Heterogeneous Architecture Co-design

Status: designed

Protocol date: July 12, 2026

No result is reported in this document. Every numeric threshold below is a
preregistered prediction or an evaluation requirement.

## Question

Under a fixed facility power envelope and wall-clock training budget, can a
mixed accelerator fleet make a different model architecture optimal, rather
than merely execute the homogeneous-fleet winner more cheaply?

The experiment jointly chooses model sections, conditional routing, precision,
device types, parallelism, and placement. Its central causal test separates an
architecture effect from a placement-only effect.

## Why This Is Genuinely Unanswered

[Maestro](https://arxiv.org/abs/2605.10501) demonstrates independent
parallelism and dynamic scheduling for sections of a fixed compound training
graph. [HMA-Serve](https://arxiv.org/abs/2606.29986) demonstrates strong phase
affinity between different memory systems during inference.
[WattGPU](https://arxiv.org/abs/2607.02391) predicts power and latency rankings
for unseen LLM and GPU combinations, while
[Charon](https://arxiv.org/abs/2605.17164) sets a strong performance-simulation
baseline.

These results make heterogeneous execution plausible, but they do not test
whether hardware diversity should change the graph worth training. A
placement study keeps the hypothesis class fixed. This experiment changes the
allocation of parameters and training FLOPs among attention, experts, dense
blocks, modality sections, and conditional paths, then tests held-out
capability after an equal facility budget. That is an architecture and learning
question, not a minor runtime optimization.

## Why Datacenter Scale Is Required

Architecture choices couple to collective topology, memory capacity, expert
traffic, pipeline bubbles, cooling, rack power, and failure domains. Small
proxy runs can estimate kernels but cannot reveal whether a heterogeneous
architecture remains trainable and efficient when thousands of devices share
the facility envelope.

The full claim requires target-scale training of at least a 70B dense model or
a 100B-total-parameter MoE model on at least 1,024 accelerators. At least two
hardware classes must each supply 20% or more of delivered training FLOPs so a
nominally heterogeneous fleet cannot pass while behaving as a homogeneous one.

## Preregistered Hypotheses

Freeze a capability vector before search. It contains one metric from each
preregistered task family. Normalize each metric to `[0, 1]` with a semantic
floor and ceiling frozen before search, then define `C` as their geometric
mean. Every component and normalization anchor is also reported separately.
Define `E_facility` as measured IT plus cooling energy from training start
through final evaluation, excluding no failed or repeated work. The primary
efficiency is `CE = C / E_facility`.

The predictions are:

1. Under identical peak facility power and maximum wall-clock budgets, joint
   architecture and hardware co-design will improve `CE` by at least 25% over
   the best architecture co-designed for any single homogeneous accelerator
   family.
2. No preregistered task-family metric will be more than 2% worse than the best
   homogeneous design. This prevents a geometric-mean gain from hiding a
   capability collapse.
3. Let `J` be the joint design, `H` the best homogeneous design, and `P` the
   heterogeneous placement of `H` with its architecture frozen. At least half
   of the joint gain must remain after subtracting the placement-only gain:
   `CE(J) - CE(P) >= 0.5 * (CE(J) - CE(H))`.
4. On held-out candidate designs, the world model will achieve Kendall ranking
   correlation of at least `0.70`, select a design within 10% of the best
   observed `CE`, and attain 85% to 95% empirical coverage for nominal 90%
   intervals.
5. Multi-fidelity search, including failed candidates, will consume no more
   than 25% of the facility energy of one target-scale training run. Search
   energy is a prediction and is reported both separately and amortized over
   one, four, and sixteen deployments.

These thresholds are predictions to test, not evidence that heterogeneous
co-design already works.

## Virtual Datacenter State

The virtual datacenter must represent:

- a section graph for attention, feed-forward, expert, embedding, output,
  modality, teacher, retrieval, and auxiliary-loss computation;
- candidate depth, width, active and total parameter count, expert count and
  capacity, conditional-routing rules, precision, sparsity, and activation
  memory;
- optimizer, training data position, sample type, learning state, gradient age,
  checkpoints, and held-out capability surrogate uncertainty;
- device-class compute, memory, interconnect, kernel, collective, numerical,
  reliability, and component-power behavior;
- placement, parallelism, microbatch, pipeline, activation-transfer, expert-
  traffic, and sample-order state per section;
- rack topology, fabric contention, storage, checkpoint bandwidth, and repair
  domains;
- facility IT power, cooling response, ambient conditions, ramp limits, and
  grid-import envelope;
- observation provenance and out-of-distribution scope for every performance,
  power, numerical, and learning surrogate.

The architecture search receives calibration and development observations
only. Evaluation tasks, evaluation hardware measurements, and future failures
remain hidden.

## Interventions

Design-time interventions:

- change depth, width, expert count, expert capacity, active-parameter budget,
  attention allocation, and conditional module structure;
- add, remove, resize, or share modality, teacher, retrieval, and auxiliary
  sections;
- choose precision and sparsity by section;
- choose the device class and replication budget available to each section;
- choose data, tensor, pipeline, expert, context, and sequence parallelism;
- choose placement, microbatch, checkpointing, and sample-order policy.

Runtime interventions:

- rebalance section placement or parallelism within the frozen architecture;
- change expert replication, routing capacity, precision, or microbatch inside
  preregistered numerical limits;
- move checkpoints and optimizer state after failure or power constraint;
- reorder eligible samples while preserving data and dependency semantics.

No architecture or metric weight can change after evaluation begins.

## Baselines

1. Best architecture co-designed separately for each homogeneous accelerator
   family, with the strongest family chosen on the development split.
2. Best homogeneous architecture placed and scheduled on the heterogeneous
   fleet without changing its graph.
3. Jointly selected architecture executed on the best homogeneous fleet.
4. Sequential search: choose architecture under an abstract FLOP and parameter
   budget, then optimize hardware and placement.
5. Fixed compound architecture with a mechanism-matched Maestro-style
   section scheduler and independent parallelism.
6. Heterogeneous placement optimized only for throughput.
7. Heterogeneous placement optimized only for accelerator energy.
8. Exhaustive enumeration on a bounded proxy search space, used only as a
   selection-regret oracle.

Every search baseline receives the same candidate-evaluation count, simulator
query budget, proxy-training energy, wall-clock limit, and calibration records.

## Experimental Matrix

The matrix includes:

- dense decoder, MoE, multimodal compound, and teacher-student compound model
  families;
- 1B to 7B proxy scale, 13B to 30B transfer scale, and at least one 70B dense
  or 100B-total-parameter MoE confirmatory scale;
- two-, three-, and four-class accelerator portfolios spanning compute-heavy,
  memory-bandwidth-heavy, memory-capacity-heavy, and lower-power devices;
- nonblocking, rack-oversubscribed, and cross-vendor or bridged fabrics;
- fixed 1 MW, 5 MW, and 20 MW virtual IT envelopes, with cooling and network
  power added rather than hidden inside accelerator energy;
- text-only, code-heavy, multimodal, and distillation data mixtures;
- stable operation, device loss, fail-slow behavior, and rack power
  curtailment;
- energy-flat, peak-power-constrained, and wall-clock-constrained objectives.

Each proxy candidate uses five frozen training seeds. Confirmatory 7B to 30B
comparisons use at least three seeds. A single target-scale run may test scaling
but cannot establish a stochastic improvement; the final claim requires at
least two independent target-scale runs per selected design and baseline.

## Held-Out Splits And Leakage Controls

- Partition observations into 60% calibration, 20% architecture selection, and
  20% final evaluation by complete run, task family, and contiguous data block.
- Freeze a capability-development set for search and a disjoint capability-
  evaluation set that is scored only after design selection.
- Evaluate leave-one-hardware-family-out, leave-one-architecture-family-out,
  leave-one-data-mixture-out, and leave-one-fabric-class-out transfer.
- Hold out at least one compound combination of hardware portfolio, model
  family, data mixture, power envelope, and failure regime.
- When a hardware family is held out, no measured kernel, collective, power, or
  reliability record from that family enters calibration. Public
  specifications may enter through a separately identified prior.
- Candidate selection uses a frozen search budget. Failed and numerically
  unstable candidates remain in the energy, reliability, and uncertainty
  accounting.
- The final task weights, metric transforms, architecture constraints, and
  random seeds are content-addressed before evaluation.

## Outcomes

Primary:

- preregistered capability vector and composite `C`;
- capability per facility joule, `CE`, at equal peak-power and wall-clock
  limits;
- architecture-attributable gain relative to the placement-only counterfactual;
- time and facility energy to each frozen capability target;
- held-out design-ranking correlation, selection regret, and interval coverage.

Secondary:

- training FLOPs, tokens, active parameters, total parameters, and data mix;
- accelerator, host, fabric, storage, and cooling energy;
- peak facility power, rack-cap violations, ramp rate, and cooling headroom;
- device-hours by class, delivered FLOPs by class, and stranded capacity;
- collective and activation-transfer bytes, expert imbalance, pipeline idle
  time, and checkpoint traffic;
- numerical failures, repeated work, recovery time, and lost learning work;
- total search energy, wall time, candidate count, and amortization break-even;
- residual attribution by architecture, kernel, network, power, numerical, and
  learning-surrogate mechanism.

Raw task metrics are always shown beside `C`. Accelerator energy is always
shown beside total facility energy.

## Falsifiers

The architecture co-design claim is falsified if any of these survive
uncertainty analysis:

- `CE` improves by less than 25% over the best fair homogeneous co-design;
- any task-family metric regresses by more than 2%;
- freezing the homogeneous winner and changing only heterogeneous placement
  accounts for more than half of the observed joint gain;
- fewer than two hardware classes each deliver 20% of training FLOPs in the
  selected design;
- equalizing search budget, failed-run energy, network energy, or cooling
  energy erases the gain;
- the selected architecture loses its ranking on a held-out hardware, model,
  task, fabric, or compound-stress panel;
- selected-design regret exceeds 10%, nominal 90% intervals fall outside the
  preregistered 85% to 95% coverage band, or the model fails to abstain outside
  scope;
- proxy-scale architecture rankings do not transfer directionally to repeated
  target-scale training;
- search consumes more than 25% of one target-scale run.

## Validation Ladder

1. Calibrate section-level kernel, memory, transfer, collective, and power
   models from public records and controlled microbenchmarks.
2. Exhaustively enumerate a bounded subspace at sub-1B scale to validate
   ranking, uncertainty, and selection-regret calculations.
3. Run equal-budget 1B to 7B co-design studies across at least three device
   classes with five seeds.
4. Shadow-predict section placement, facility power, and learning outcomes on
   two real heterogeneous clusters without changing live training.
5. Run repeated 13B to 30B controlled comparisons on 64 to 512 accelerators,
   including architecture-frozen counterfactuals.
6. Execute at least two independent runs per design at 70B dense or
   100B-total-parameter MoE scale on at least 1,024 accelerators, under the same
   measured facility envelope and final evaluation set.

Stages 1 through 3 can validate the search machinery. Stage 5 can support a
medium-scale architecture-effect claim. Only stage 6 can support the stated
datacenter-scale capability and facility-efficiency hypothesis.

## First Engine Slice

Implement the smallest substrate that can reject a placement-only story:

- a section-graph model with section-specific FLOPs, parameters, activation
  state, precision, and conditional activation;
- two architecture families whose section allocation can change, initially a
  dense decoder and an MoE decoder;
- two device classes with measured compute, memory, collective, power, and
  uncertainty records;
- section-to-device placement and data, tensor, pipeline, and expert
  parallelism decisions;
- facility power and cooling accounting, including failed and repeated work;
- a frozen learning-progress and capability surrogate with explicit
  calibration and abstention limits;
- equal-budget homogeneous, placement-only, sequential-search, and joint-search
  baselines;
- held-out ranking, selection regret, interval coverage, and the architecture-
  attributable-gain calculation.

Multimodal sections and four-class portfolios enter only after the dense-versus-
MoE, two-device causal contrast is measurable.
