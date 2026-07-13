# E001-LC2 v2: Late-Stage Quality-To-Target Recovery

Status: executed July 12, 2026; protocol failed before held-out evaluation

This protocol preserves the v1 warm-stage failure instead of overwriting it.
V1 trained the shared checkpoint for 2,048 ticks and observed held-out NLL
`1.52376570366323 -> 1.43749829754233` over its final 256 ticks, an improvement
of `0.0862674061208963`. That failed the frozen maximum `0.03`, so v1 persisted
`protocol_failed_warm_start_not_late_stage` before any held-out schedule ran.

V2 makes one precommitted fourfold jump to an 8,192-tick shared checkpoint. It
keeps the same seed, model, optimizer, data, healthy/recovery policies,
validation suite, target-selection rule, six LC1-held-out failure schedules,
and all candidate falsifiers. The checkpoint earns the late-stage label only
if NLL improvement from tick 7,936 to 8,192 is at most `0.03`.

If the warm gate passes, the experiment follows the complete frozen design in
`quality-target-calibration-v1.md`:

1. fixed and adaptive no-failure calibration controls run for 256 ticks;
2. fixed C1/C2 values at ticks 240, 248, and 256 freeze one target;
3. exact no-failure learning equivalence and the target-window gate must pass;
4. 12 held-out fixed/adaptive interrupted runs stop at the first 8-tick
   observation at or below the target;
5. paired attempted-FLOP savings, opportunity ticks, canonical work, sampled
   training-only device energy, and all preregistered falsifiers are reported;
6. observed learning remains separate from the labeled recovery-v2 modeled
   bridge sensitivity.

No v1 held-out result exists, so v2 does not tune against evaluation. If the
8,192-tick checkpoint also fails the late-stage gate, this TinyStories workload
does not support the intended LC2 regime under the frozen criterion and the
result redirects E001 rather than adding another warm-start search.

## Executed Result

The 8,192-tick warm run passed the late-stage gate: held-out NLL moved from
`1.0317214401438832` at tick 7,936 to `1.02718645054847` at tick 8,192, an
improvement of `0.004534989595413208`, below the frozen `0.03` maximum. The
fixed and adaptive no-failure calibration controls were exactly equivalent.

The calibration-only target was `1.01961656101048`, but C1 and C2 first crossed
it at ticks 40 and 96. Those crossings were outside the frozen tick 192 to 288
validity window even though the target was constructed from ticks 240, 248,
and 256. Late-stage validation NLL was non-monotonic around the threshold, so
the first-crossing objective did not mean what the protocol required it to
mean.

The result persisted `protocol_failed_calibration_validity` and stopped before
all six held-out schedules. This is not a candidate failure and contains no
held-out policy comparison. It motivated LC3's equal-canonical-work endpoint,
which removes first crossing without smoothing or retuning the target.

Result artifact:
`results/quality-target-v2.json`
(`a3bb91b74a99708a08b5196ffc8d16bb27bca697f7f54fb63e60564851f97517`).
