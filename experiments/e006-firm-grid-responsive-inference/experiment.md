# E006: Firm Grid-responsive Inference

Status: designed

Protocol date: July 12, 2026

No result is reported in this document. Every numeric threshold below is a
preregistered prediction or an evaluation requirement.

## Question

Can an inference datacenter offer a firm, auditable power-reduction commitment
to the grid while preserving per-request utility and tail latency, including
under bursty arrivals, equipment faults, hot weather, and repeated dispatch?

The question is about contracted flexibility, not whether average power can be
lowered once. A successful controller must predict how much reduction it can
guarantee before the event, deliver it at the grid meter, and avoid a hidden
latency, quality, rejection, or rebound cost.

## Why This Is Genuinely Unanswered

[Quantization-enabled demand response](https://arxiv.org/abs/2606.18851)
connects model switching, request routing, and precision selection to a
multi-campus dispatch problem, but its reported fleet result is a case study
rather than hyperscale live validation of per-request service tails.
[Power-Flexible AI Data Centers](https://arxiv.org/abs/2606.25098) demonstrates
rapid reduction, sustained curtailment, and geographic shifting on a real 130
kW GPU cluster, but does not establish a statistically firm product at
hyperscale. [OpenG2G](https://arxiv.org/abs/2605.05519) supplies a measured
datacenter-to-grid simulation interface, while
[WattGPU](https://arxiv.org/abs/2607.02391) predicts mean device behavior rather
than event-level delivery under queue and facility dynamics.

The untested step is joint, request-conditioned control with an ex ante reserve
bid, calibrated delivery probability, end-to-end service accounting, and
rebound constraints. This is materially different from adding quantization or
DVFS to an energy scheduler.

## Why Datacenter Scale Is Required

Firm flexibility is a property of an aggregate distribution, not one rack.
Correlated request bursts, model residency, rack caps, network congestion,
cooling lag, ambient temperature, device failures, and geographic routing can
all invalidate a reserve bid. Rare delivery failures and service cliffs are
also invisible in a short laboratory trace.

The full firmness claim requires at least 10 MW of controllable inference load
across at least two power and failure domains, plus enough independent dispatch
windows to estimate a 99% delivery target. Smaller deployments calibrate
mechanisms but do not validate the product.

## Firmness Estimand And Accounting Boundary

For each event, freeze a counterfactual no-dispatch facility-load baseline
before the dispatch signal. Where operationally possible, estimate it through
randomized dispatch windows and matched non-dispatch windows. Delivered
reduction at the revenue meter is

`R(t) = P_baseline(t) - P_meter(t)`.

Battery discharge, generator output, exported on-site generation, and cooling
preconditioning are reported separately. They cannot be counted as
compute-native reduction. Deferred work remains charged until it completes or
expires.

Define `R_firm` as the largest preregistered reserve bid for which the lower 95%
confidence bound on held-out event delivery probability is at least 99%, at
least 90% of the bid arrives within 10 seconds, the full bid is sustained for a
15-minute event, and all service and rebound constraints below hold.

## Preregistered Hypotheses

The predictions are:

1. A joint controller will provide `R_firm` equal to at least 20% of the
   matched non-dispatch facility load.
2. Its `R_firm` will be at least 50% greater than that of the best isolated
   mechanism under identical service constraints.
3. Relative to matched no-dispatch operation, TTFT and TPOT SLO attainment will
   each decline by no more than one percentage point in any workload family,
   P99 TTFT and P99 TPOT will remain within their frozen workload-specific
   limits, and frozen per-request utility will decline by no more than 1%.
4. Metered power during the 30 minutes after an event will not exceed the
   matched baseline peak by more than 5%. Deferred energy and work must not be
   hidden beyond the reporting window.
5. On held-out events, the controller's nominal 99% delivery probability will
   have a lower 95% confidence bound of at least 99%, using event-level rather
   than request-level replication.

These thresholds define a research hypothesis. They are not claims about the
current GPUSTACK engine or an existing datacenter.

## Virtual Datacenter State

The simulator must include:

- request arrivals, workload family, tenant, priority, prompt and output
  distributions, deadline, SLO, model eligibility, and frozen utility curves;
- queues, batches, model replicas, KV and prefix state, speculative state,
  paused work, and rejected or expired requests;
- model, precision, quantization, and device-specific latency, quality, memory,
  and power distributions;
- accelerator, host, fabric, storage, and rack power with DVFS and transition
  delay;
- rack and facility caps, power-distribution losses, cooling load, thermal
  inertia, ambient weather, and metered non-compute load;
- campus links, model and state movement, geographic routing latency, and
  regional capacity;
- grid dispatch signal, reserve bid, measurement baseline, telemetry delay,
  meter noise, event duration, and settlement interval;
- visible failures, fail-slow devices, network loss, cooling faults, and
  recovery state;
- prediction intervals, provenance, calibration scope, and out-of-distribution
  state for every workload, quality, latency, and power model.

The policy can observe operational telemetry available before or during the
event. It cannot observe future arrivals, future faults, counterfactual meter
truth, or latent request quality.

## Interventions

- select model, precision, quantization, speculative draft, and speculation
  depth per request within its utility floor;
- change batching, chunking, admission, priority, and deadline-aware deferral;
- route requests among replicas, racks, and campuses;
- change replica count, model placement, KV placement, and paused-session
  retention;
- set accelerator frequency, power cap, and idle-state transitions;
- reserve capacity before dispatch and release it after uncertainty clears;
- precondition or adjust cooling within thermal and post-event accounting
  constraints;
- decline or derate a reserve bid before commitment when predicted uncertainty
  is too high.

Every action records its effect on served work, utility, latency, state
movement, facility power, and post-event debt.

## Baselines

1. No demand-response action.
2. Accelerator power-cap or DVFS-only control.
3. Quantization and model-switching-only control, matched to the public
   quantization-enabled mechanism where evidence permits.
4. Batching, admission, and deadline-aware deferral only.
5. Geographic request routing and load shifting only.
6. Aggregate-load scheduling without request-conditioned utility.
7. An independent-controller ensemble with all isolated levers and a frozen
   conflict priority.
8. The joint controller without a calibrated reserve derating rule.
9. A clairvoyant oracle with future arrivals, faults, and weather, used only to
   bound reserve and decision regret.

Storage and generation baselines are reported in a separate panel. They never
substitute for the compute-native comparison.

## Experimental Matrix

Primary confirmatory events are 15 minutes long with a 10-second response
requirement. Transfer panels vary:

- 5-minute, 15-minute, and 60-minute event durations;
- reserve bids of 5%, 10%, 20%, and 30% of matched baseline load;
- conversational, retrieval-heavy, coding-agent, and latency-tolerant batch
  workloads, both separately and in changing mixtures;
- steady, diurnal, flash-crowd, heavy-tailed tool-gap, and correlated-campus
  arrivals;
- dense and MoE models across at least three model-size classes and four
  precision or quantization choices;
- homogeneous and mixed accelerator fleets across at least three hardware
  families;
- one campus and multi-campus routing with uncongested and congested links;
- cool, nominal, and hot ambient conditions with normal and degraded cooling;
- clean operation, device loss, fail-slow behavior, link loss, and telemetry
  delay;
- isolated events and repeated events with 5-, 15-, and 60-minute recovery
  intervals.

Each stochastic virtual cell uses 30 frozen seeds. Meter and service metrics
are aggregated by complete event and campus-day, never by request.

## Held-Out Splits And Leakage Controls

- Allocate complete campus-days and contiguous workload blocks to 60%
  calibration, 20% development, and 20% evaluation before fitting. Requests
  from one session or prefix lineage stay in one split.
- Withhold one complete workload family, model family, hardware family, campus,
  weather regime, and dispatch-shape family in separate transfer panels.
- Include one compound evaluation panel combining a held-out workload mix,
  heat condition, network stress, and device-failure rate.
- Baseline estimation, utility calibration, and reserve derating are frozen on
  the development split. Evaluation meter data are opened once.
- The live confirmatory dataset must contain at least 300 non-overlapping
  dispatch windows and use campus-day clustered confidence intervals. If the
  required statistical lower bound cannot be estimated, the firmness claim is
  unproven rather than extrapolated.
- Report abstention and bid derating. Events declined before commitment do not
  count as delivery successes and reduce offered reserve availability.

## Outcomes

Primary:

- `R_firm` in MW and as a fraction of matched facility load;
- event delivery probability and its event-clustered confidence bound;
- time to 90% delivery, sustained-delivery error, and settlement-interval
  tracking error;
- P50 and P99 TTFT and TPOT, SLO attainment, rejection, expiration, and frozen
  request utility by workload family;
- 30-minute rebound peak, deferred work, and deferred facility energy;
- reserve decision regret and uncertainty calibration on held-out events.

Secondary:

- accelerator, host, fabric, storage, cooling, and total meter power;
- rack peaks, ramp rate, thermal headroom, and cooling-cap violations;
- useful requests and task units completed during and after dispatch;
- model, precision, routing, batching, and DVFS action counts and churn;
- model and KV movement bytes, replica warm-up energy, and post-event queue
  debt;
- geographic shift, network congestion, carbon, and cost under identical
  accounting boundaries;
- separate contribution from compute control, cooling, storage, and generation;
- residual attribution for baseline error, workload error, device power,
  cooling, telemetry, and controller action.

Average token volume cannot substitute for the request-level service and
utility outcomes.

## Falsifiers

The firm-flexibility claim is falsified if any of these survive uncertainty
analysis:

- `R_firm` is below 20% of matched facility load;
- joint `R_firm` is less than 1.5 times the best isolated mechanism;
- the lower 95% confidence bound on delivery probability is below 99%, 90%
  response takes longer than 10 seconds, or full delivery is not sustained for
  15 minutes;
- any workload family loses more than one percentage point of TTFT or TPOT SLO
  attainment, exceeds its P99 latency limit, or loses more than 1% frozen
  utility;
- post-event power exceeds the matched peak by more than 5%, or deferred work
  and energy erase the dispatch benefit;
- the result depends on excluding rejected requests, cooling load, network and
  host power, failed events, or pre-event energy;
- reserve rankings or confidence bounds fail on a held-out campus, workload,
  hardware, weather, or compound-stress panel;
- a non-request-conditioned or isolated controller matches the joint policy
  within uncertainty;
- the virtual delivery result fails directionally in controlled live dispatch.

## Validation Ladder

1. Replay public inference power traces and OpenG2G scenarios with explicit
   baseline uncertainty and meter accounting.
2. Measure per-model, precision, batching, DVFS, transition, and utility curves
   on 8 to 64 accelerators.
3. Validate meter response, cooling lag, and request-service accounting on a
   100 to 500 kW controlled cluster.
4. Run shadow bids on at least two live inference sites without dispatching
   them; score predicted reserve against naturally observed counterfactuals and
   guarded test windows.
5. Execute repeated controlled events on at least 1 MW of live inference load,
   including heat, burst, and equipment-loss panels.
6. Run the frozen confirmatory protocol on at least 10 MW across two power and
   failure domains, with at least 300 non-overlapping dispatch windows and
   held-out campus-days.

Stages 1 through 3 validate mechanisms and accounting. Stage 5 can support a
large-cluster flexibility result. Only stage 6 can support the 99% firm reserve
claim.

## First Engine Slice

Implement the smallest substrate that can prove a reserve bid was wrong:

- request-level arrival, deadline, SLO, model eligibility, and frozen utility
  observations;
- model and precision latency, quality, power, and transition distributions;
- queue, batch, replica, KV-residency, DVFS, rack-power, cooling, and revenue-
  meter temporal state;
- a frozen no-dispatch baseline estimator with uncertainty and causal event
  identifiers;
- quantization-only, DVFS-only, deferral-only, independent-ensemble, joint,
  and clairvoyant-oracle policies;
- precommitment reserve bidding, derating, abstention, and event settlement;
- post-event queue and energy debt carried until completion or expiry;
- event-level delivery intervals, service tails, utility, rebound, decision
  regret, and residual attribution.

Geographic routing and cooling control enter only after a single-site,
compute-native reserve bid can be evaluated without hidden work or energy.
