# Experiments

Each experiment directory contains a frozen scientific question, hypothesis,
baselines, variables, observations, metrics, falsifiers, and path to real-world
validation.

An experiment moves through these states:

1. `designed`: hypothesis and falsifiers are frozen.
2. `virtual`: executed in GPUSTACK with calibration/evaluation separation.
3. `shadow`: predictions compared with live telemetry without controlling it.
4. `controlled`: bounded real-cluster intervention.
5. `validated`, `falsified`, or `inconclusive`.

Simulation-only results never advance beyond `virtual`.
