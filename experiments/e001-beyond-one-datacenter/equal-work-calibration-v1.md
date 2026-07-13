# E001-LC3: Equal-Canonical-Work Survivor Continuation

Status: executed July 12, 2026; candidate falsified on held-out device energy

## Research Question

From one demonstrably late-stage checkpoint, can survivor continuation reach
the same canonical useful-work frontier with non-inferior held-out quality while
using less attempted compute, fewer scheduled opportunity ticks, and no more
sampled training-only GPU energy than fixed-local restart?

This is a research redirect selected by two preserved LC2 protocol results.
LC2 v1 showed that 2,048 ticks was not late-stage. LC2 v2 established a valid
8,192-tick late-stage state and exact fixed/adaptive no-failure equivalence, but
also showed that raw NLL first crossing is not a stable late-stage objective:
the target chosen from ticks 240–256 had already been crossed at ticks 40 and
96 because validation NLL fluctuates non-monotonically around the threshold.

LC3 does not smooth or retune that target. It removes first crossing from the
question.

## Frozen Design

- Same TinyStories shard, approximately 2M-parameter byte decoder, AdamW,
  validation suite, warm seed, healthy cadence, checkpoint cadence, and
  recovery semantics as LC2 v2.
- Rebuild the shared 8,192-tick checkpoint. Its final-256-tick NLL improvement
  must again be at most `0.03`.
- Two calibration strata run fixed and adaptive no-failure controls to the
  same canonical tick 256. Their attempted tokens and NLL curves must match
  exactly.
- Six held-out schedules are reused unchanged from LC1. Each runs fixed
  interrupted and adaptive interrupted until canonical logical tick 256, with
  a hard censoring limit of 384 opportunity ticks.
- Pair order alternates by stratum. Validation and cooldown are outside the
  training energy/time meter.

The work frontier is exact: 256 logical ticks, two 4x256-token site quotas per
tick, or 524,288 canonical tokens in every completed arm. A policy that fails
to reach it is a censored failure, never a low-work winner.

## Primary Learning Estimand

For stratum `s`:

`delta_nll_s = final_NLL[adaptive,s] - final_NLL[fixed,s]`.

Report all six paired effects, the median, and a paired 90% percentile-
bootstrap interval. Adaptive is learning-noninferior only if the interval's
upper bound is at most `0.01` NLL.

The `0.01` margin was frozen before LC3 evaluation. LC2's untouched C1/C2
fixed-control final-NLL span was `0.00451699830591679`; the margin is greater
than twice that observed seed span and rounded upward. It is not selected from
LC3 held-out outcomes.

## Recovery-Cost Estimands

At the same canonical work frontier, report paired:

- attempted-FLOP saving `(fixed - adaptive) / fixed`;
- opportunity-tick saving `fixed - adaptive`;
- adaptive/fixed sampled training-only device-energy ratio;
- replayed, discarded, and survivor-redistributed tokens;
- checkpoint bytes and local active seconds.

## Frozen Falsifiers

The candidate survives LC3 only if all are true:

1. all six fixed/adaptive pairs reach canonical tick 256 by opportunity tick
   384;
2. the upper bound of the paired 90% adaptive-minus-fixed NLL interval is at
   most `0.01`;
3. the lower bound of the paired attempted-FLOP-saving interval is above zero
   and its median is at least 3%;
4. median opportunity-tick saving is at least 24 ticks and adaptive is earlier
   in all six schedules;
5. the upper bound of the paired adaptive/fixed training-device-energy ratio is
   at most 1.05;
6. calibration controls remain exactly learning-equivalent;
7. no adaptive held-out run diverges.

## Evidence Boundary

Observed: paired held-out byte NLL at the exact same canonical work, attempted
and canonical tokens, local serial active time, training-only NVML board
energy, temperatures, and checkpoint/replay/discard accounting.

Simulated: opportunity ticks and visible failure/rejoin schedule.

Modeled sensitivity only: the recovery-v2 bridge for datacenter time, WAN,
lost FLOP, and partial energy. It is never added to the measured RTX energy.

Unmeasured: simultaneous multi-site throughput, actual WAN or storage service,
host/cooling/facility energy, failure detection, hybrid parallelism,
frontier-scale convergence, and transfer beyond the frozen workload.

## Executed Result

All six held-out pairs reached the exact 524,288-canonical-token frontier. The
adaptive candidate passed every frozen gate except device energy:

| Held-out result | Fixed-local restart | Adaptive continuation |
|---|---:|---:|
| Median final held-out NLL | 1.0195826 | 1.0248523 |
| Median opportunity ticks | 296 | 256 |
| Median attempted tokens | 540,672 | 524,288 |
| Median canonical tokens | 524,288 | 524,288 |
| Median replayed / discarded tokens | 16,384 / 16,384 | 0 / 0 |
| Median survivor-redistributed tokens | 0 | 32,768 |
| Median sampled device energy | 75.295 J | 81.556 J |
| Median local active time | 7.443 s | 8.384 s |
| Median checkpoint bytes | 385,076,112 | 1,064,622,192 |
| Median checkpoint count | 17 | 47 |

Adaptive-minus-fixed NLL had median `0.003338515292853117` and a paired 90%
interval `[0.0023927902802824974, 0.008503663819283247]`. Its upper bound was
below the frozen `0.01` noninferiority margin. Attempted-work saving had median
`0.030303030303030304` and interval
`[0.030303030303030304, 0.058823529411764705]`. Opportunity-tick saving had
median `40`, interval `[36, 44]`, and adaptive was earlier in all six strata.
Calibration controls remained exactly equivalent and no adaptive run diverged.

The sole failed gate was sampled training-device energy. The adaptive/fixed
ratio had median `1.0683917796356628` and a paired 90% interval
`[1.0017954332700434, 1.134269402803286]`; the upper bound exceeded the frozen
`1.05` ceiling. The conclusion is therefore
`candidate_falsified_equal_canonical_work`. Adaptive preserved late-stage
learning and saved attempted work and scheduled time, but its shortened
checkpoint cadence and longer active execution carried an unresolved energy
penalty in this harness.

Artifacts:

- result: `results/equal-work-v1.json`
  (`f7548b68d4791978260f0bd557bf92041d0f769b796b1e684bbcab99e88f639f`);
- engine source:
  `893b2d25eed53122c59ee26ac95a10c2e9f2e360c0c9b6c39c14bf1d32d25fbd`;
- engine bundle:
  `b574609b19eeca593dc932ec09943a779b50a28b4d9e336afa07b5a18fa52249`;
- scenario:
  `f5212c19e701f183c7ab9aaf7620bf43c03a234eee92dd7e9d98c73c5c22a9ed`;
- observatory projection: `../../docs/data/e001-equal-work-v1.json`
  (`5ff07c4cf5b59be04d14f1b66961e679c2cec127b521c386d54ff9ebaadc1ae1`).

## Next Frontier Question

E001 should not scale this candidate yet. E002 should attribute the observed
energy penalty to checkpoint and recovery phases with operation-to-facility
power waveforms, using a frozen 2x2 experiment: checkpoint cadence by survivor
continuation. The next question is whether dependency-safe phase scheduling
can remove the energy penalty without losing LC3's learning, attempted-work,
or opportunity-tick gains.
