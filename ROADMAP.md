# Roadmap

Ranked by what the evidence says is most worth doing. Written after the 2026-10 audit.
Sources: [EVIDENCE.md](EVIDENCE.md), [graph audit](analysis/graph-audit/REPORT.md),
[S001](experiments/s001-graph-sensitivity/RESULT.md), [V002](experiments/v002-graph-published-runs/RESULT.md),
[P001](experiments/p001-protocol-power-audit/RESULT.md). Nothing here is scheduled.

## 1. Fix the E003-E006 gates before running anything

P001 found all four protocols inadequate as written. Do the cheap fixes first:

- State the interval and n for interception and delivery gates (E003-G3, E006-G3). At a
  99% lower bound this needs 299 events with zero misses (473 with one). Or set the bound
  at 95%, which needs 59.
- Make the E003-G10 and E006 match rules directional. As written the hypothesis survives
  22.6% to 48.7% of the time when the best baseline is identical to it.
- Freeze n, K and the point-or-interval reading for E003-G1/G4/G5, E004 (at least 30
  clusters, m of 100 or more for coverage) and E005-G2/G5/G6/G7.
- Give each E006 bid level its own 299 windows, or test only the 20% bid.

Done when P001 is re-run on the revised gates and no gate is labeled impossible.

## 2. Close the two running studies

- **R001** (CPU replication, protocol frozen at `0540632`): does LC3's small NLL cost
  replicate on fresh seeds, and is the SC1 averaging effect plain weight averaging? Its
  answer decides whether `periodic_local` is a finding or an artifact. Q2 is the open
  mechanism question for item 6 below.
- **V001** (simulator vs known results): done. Event mechanics match theory where runs
  complete; see item 3 for the defect it found. Multi-site, WAN policy, power and cooling
  paths are still untested.

## 3. Fix the recovery-runtime defect V001 found

While building V001 its author found that `RecoveryRuntime.begin_recovery` raises
`ValueError` when a failure arrives after a recovery's replay finished and before the next
checkpoint commits (minimal repro in the
[V001 result](experiments/v001-simulator-known-results/RESULT.md); repro: `experiments/v001-simulator-known-results/repro_defect.py`).
The shipped E001 runs have one failure each, so they never hit it. Any multi-failure
trace can. V001 has reported (1,540 of 4,500 multi-failure test traces raise), so it can be fixed now; the root cause is `WorkLedger.invalidate_outcomes` (`gpu_stack/research/recovery.py:1979`) invalidating a committed replay outcome that superseded attempts still point to.
Note that `gpu_stack/research/*.py` files hash their own source into artifact identities,
so the edit is a provenance event and must be recorded as one.

## 4. Decide what the decorative equations are

538 of 950 equations reach no headline number (audit). Pick one per family:

- **Collective, kernel, optimizer, precision (150 equations):** either wire the collective
  family into training step time (it currently has its own copy, `training.eq.t_comm_dp`)
  and test it, or label the whole set a reference library, not part of the model.
- **Nuclear and quark (88 variables, 83 equations):** remove. They have no numeric effect.
- **Plasma and atomic layers:** move out of the core graph. Keep the Rayleigh resolution
  relation with wavelength and numerical aperture as plain inputs.
- **Root debt:** stop using it to choose work. S001 found it does not track influence.

## 5. Small fixes

- PW2 field label: `idle_subtracted_gpu_board_energy_j` holds raw energy (max difference
  0.0). Its 1.023 and LC3's 1.068 are different quantities sharing one bar. Rename the
  field in the writer, and add a note to the old artifact rather than editing it.
- Remaining audit items: the 17 suspect equations and the suspect preset values (PUE
  never enters site power, demand charge double counted, a 4-year life applied to the
  facility). H100 BF16 peak, NVLink and memory units are already fixed.
- Label the MFU as a prior wherever the graph shows a time prediction (V002).

## 6. SC1 averaging mechanism

`periodic_local` beat synchronous training in 10 of 10 families, and nobody knows why.
R001 Q2 adds controls (iterate averaging, period 1, shared vs separate Adam state, EMA).
If it survives them, it is the most interesting result in the project and worth a
write-up of its own. If it does not, say so in the ledger.

## 7. Energy questions that need the owner's GPU

LC3's energy verdict is undetermined and PW2's mechanism is undetermined. A real answer
needs: the cumulative energy counter, idle measured before and after each run, randomized
arm order, nothing else on the GPU, locked clocks, 12 or more pairs, and a model big enough
that board power sits far above idle (today it is 3 to 4 W above). Report time and energy
together. The same applies to any WAN, multi-site or rack (PW3) claim.

## Not planned

More equations, SC2 (a learned risk predictor) before R001 reports, and live controllers.
