# Causal Observatory README Fragments

Use these fragments when the README needs a compact visual explanation of the
research loop. The observatory is the primary visual artifact. The dependency
cone remains useful as the symbolic ancestry view inside that larger system.

## Opening Visual

Suggested placement: below the repository and observatory links.

```markdown
![Dependency cone from datacenter economics through GPU systems, lithography, and primitive assumptions.](docs/assets/readme-equation-cone.svg)

GPUSTACK connects measurements, a causal virtual datacenter, and falsifiable
experiments. Pick a research question, compare interventions over one frozen
scenario, and keep every modeled value attached to its provenance, uncertainty,
and missing mechanisms.
```

## Explain The Observatory In One Screen

```markdown
The causal observatory has three synchronized readings of the same artifact:

1. **Freshman:** what happened and why it matters in ordinary language.
2. **Researcher:** the mechanism, intervention, uncertainty, and falsifier.
3. **Full trace:** event records, equations, assumptions, observation IDs, and
   unsupported claims.

Changing depth changes explanation density. It never changes a metric,
evidence class, or conclusion.
```

## Evidence Legend

```markdown
| Evidence class | Meaning |
|---|---|
| Measured | Recorded by named instrumentation with uncertainty and provenance. |
| Modeled | Produced by an explicit engine mechanism. |
| Assumed | Fixed by the scenario rather than inferred from data. |
| Prior | A sensitivity belief that is not fitted evidence. |
| Unmeasured | Required for the claim, but absent from the artifact. |
```

The legend is a scientific boundary, not a color theme. A favorable modeled
mechanics result cannot turn an unmeasured learning outcome into evidence.

## E001 Demo

````markdown
### Beyond One Datacenter

The first observatory artifact compares synchronous, fixed-local, and
adaptive-cadence execution over the same three-site scenario. It can support
claims about modeled event order, contention, collective payload-link bytes,
elapsed time, and site base plus accelerator compute energy.

It cannot yet support claims about held-out learning efficiency, time to a loss
target, reactive membership during an active outage, lost work, or checkpoint
recovery. Those gaps remain visible beside the result.

```bash
python -m gpu_stack.cli experiment-protocol E001 --json
python -m gpu_stack.cli experiment-run E001 \
  --scenario experiments/e001-beyond-one-datacenter/screening-scenario-v1.json \
  --output experiments/e001-beyond-one-datacenter/results/screening-mechanics-v1.json \
  --observatory-output docs/data/e001-screening-v1.json
```
````

## Dependency Cone As Supporting View

```markdown
The symbolic cone answers a narrower question: what is this number made of?
Every upstream hop is an equation, sourced scenario value, universal constant,
or exposed root input. That ancestry becomes useful research infrastructure
when a held-out residual can be traced back to the mechanism that caused it.
```

## Next Visual Research Views

```markdown
## Next visual research views

- Residual attribution that aligns a measured trace with the modeled causal
  path and names which mechanism owns the error.
- Counterfactual small multiples that hold workload and exogenous events fixed
  while one intervention changes.
- A power-waveform view for E002 that aligns operation phases, facility power,
  cooling response, and grid danger bands on one clock.
- A learning-transfer view that refuses to render an E001 convergence claim
  until held-out multi-site observations are attached.
```

## Tone Notes

- Prefer "what produced this result?" over "end-to-end platform."
- Define MFU, PUE, HBM, TTFT, and TPOT on first use.
- Keep evidence gaps adjacent to the result they constrain.
- Do not turn registry size or test count into the research score.
