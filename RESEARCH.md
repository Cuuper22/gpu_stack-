# GPUSTACK Research Program

## Status after the 2026-10 audit

The program below was written in July 2026, before any result was re-judged. In October
2026 every run and the graph itself were audited. The audit changed what the program can
claim. Read [EVIDENCE.md](EVIDENCE.md) first. It is the authoritative ledger.

What changed:

- **Nothing is fitted.** An earlier version said measurements calibrate the engine. They
  do not. No parameter in the graph or the simulator is fitted to a measurement. The
  simulator takes every duration from the caller.
- **The graph is not a validated predictor.** [V002](experiments/v002-graph-published-runs/RESULT.md)
  tested it against 27 published training runs. As shipped it was about 3x too fast
  (median error 0.682). With a labeled 40% MFU prior it reached 0.218, the same as plain
  6ND at 40% MFU (0.219). Parameter counting from architecture works (0.0003).
- **Most of the graph feeds nothing.** [The graph audit](analysis/graph-audit/REPORT.md)
  found 538 of 950 equations reach no headline number, 4 wrong equations (now fixed), and
  no numeric effect from the nuclear and quark layer. [S001](experiments/s001-graph-sensitivity/RESULT.md)
  found root debt does not rank influence.
- **"Preregistered" holds only for newer studies.** E001 and E002 protocols and results
  share commits. P001, S001, V002, V001 and R001 froze their protocols first (see
  [README](README.md#how-the-project-checks-itself)).
- **E001 and E002 verdicts were re-judged.** Short form: the adaptive controller lost to
  `periodic_local`; `periodic_local` beat synchronous training in 10 of 10 families, cause
  unknown; LC1 never tested its hypothesis; the LC3 energy question is undetermined; PW2's
  sparse continuation is a small real saving. The original verdict strings are kept as history.
- **E003-E006 cannot run yet.** [P001](experiments/p001-protocol-power-audit/RESULT.md)
  found every gate set inadequate as written.
- **Running now:** [R001](experiments/r001-cpu-replication/protocol.md) (CPU replication of
  the learning results and an averaging control) and
  [V001](experiments/v001-simulator-known-results/protocol.md) (simulator against textbook
  results). Both are frozen and have no results yet.

Next steps are in [ROADMAP.md](ROADMAP.md).

## Telos

GPUSTACK is meant to be three things at once:

- **Engine:** a virtual AI datacenter model of training, power, reliability, thermal and
  economic behavior. Today it is an equation graph plus an event simulator, not a
  calibrated twin.
- **Medium:** an observatory page that explains one result at several depths, from a
  plain question down to raw traces, without changing the numbers.
- **Lab:** a place to screen datacenter-scale ML hypotheses cheaply before asking for
  real hardware.

The loop is: hypothesis, frozen test, measurement, re-judgment, better hypothesis. The
engine does not yet close that loop, because nothing measured feeds back into it.

## Scientific position

Charon-style simulators already time training operators accurately, serving mechanisms are
optimized one at a time, and facility power is controlled separately. The open question
is how these interact. GPUSTACK asks questions of this form:

> Under uncertain workload, hardware, network, failure and grid conditions, which
> intervention most improves time-to-capability, and how likely is that conclusion to
> survive transfer to a real datacenter?

The score is not equation count, root count or test count. It is held-out error,
interval coverage, ranking, decision regret, and whether a frozen hypothesis survives.

## Engine contract

The research layer adds, without replacing the symbolic registry: observations with
provenance; calibration and evaluation splits that cannot overlap; temporal state
(queues, failures, recovery, power); interventions; policies that see only observable
state; learned residuals with a stated scope; frozen experiments; and evidence
requirements that stay mandatory when no scalar threshold fits.

## The six frontier programs

Each has a protocol under `experiments/`. Gates are predictions, not results.

1. **Beyond One Datacenter (E001).** Can a model train across heterogeneous, flaky
   datacenters at 95% of centralized progress per FLOP with 10x fewer inter-site bytes?
   Ran. The 10x byte hypothesis was out of reach even for the best simple policy, and the
   adaptive controller lost to `periodic_local`.
2. **Shape the Power Waveform (E002).** Can phase offsets across compute, collectives and
   checkpoints remove grid-danger oscillations without slowing learning? PW2 gave a small
   local result. The rack test (PW3) has never run.
3. **Semantic Fault Tolerance (E003).** Can failures be treated as bounded learning
   perturbations? Protocol only; fix gates first.
4. **Fluid Inference Topology (E004).** Should serving topology change per request?
   Protocol only.
5. **Architecture as a Datacenter Variable (E005).** Does co-designing architecture and
   mixed hardware beat the best uniform cluster per joule? Protocol only.
6. **Firm Grid-Responsive Inference (E006).** Can an inference fleet offer firm demand
   response without a hidden quality cliff? Protocol only.

## Research rules

- A virtual screen can reject a mechanism. It is never the sole evidence about a real datacenter.
- Every experiment has a falsifier and reports negative results.
- Every claimed gain names the metric most likely to reverse it (time beside throughput,
  facility power beside GPU energy).
- Every comparison uses the same observations, splits and accounting boundary.
- Gates are checked for reachability and power before they are frozen
  ([P001](experiments/p001-protocol-power-audit/RESULT.md) shows what happens otherwise).
- Root-debt work enters the queue only through a measured residual, a decision-relevant
  uncertainty or an experiment need. S001 found the debt count alone does not point there.
- Do not call a run preregistered unless the protocol commit precedes the result commit.
- No controller gets live actions before shadow comparison and a separate controlled protocol.

## Hardware boundary

All real measurements so far come from one RTX 3060 Laptop GPU (shared with other apps),
a 1,871,232-parameter byte-level transformer, six hand-written failure schedules, one
seed each. Two "sites" ran one after the other on that GPU. WAN time, completion time,
multi-site concurrency and facility energy are modeled. Energy claims need the owner's
GPU, the cumulative energy counter, and 12 or more pairs.
