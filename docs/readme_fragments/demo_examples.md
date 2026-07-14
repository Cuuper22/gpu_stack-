# Verified demo examples

These snippets were checked from `D:\GPUSTACK` on 2026-05-11 with Python 3.12.

## Registry stats

```powershell
python -m gpu_stack.cli stats
```

Observed summary:

```text
Registry stats:
  systems        16
  variables      1517
  constants      24
  equations      950
  root_inputs    619
  leaves         259

Coverage:
  non_constant_variables         1493
  with_sp_units                  1428
  with_references                1324
  equations                      950
  equations_with_references      878
  equations_with_unit_check      799
```

Use this as a quick health check for the symbolic registry. The exact counts can change as new scopes and equations are added.

## Root-debt ranking

```powershell
python -m gpu_stack.cli root-debt --families --limit 5
```

Observed summary:

```text
Root-debt family ranking:
  total_roots        619
  include_constraints False
  grouped_roots      619
  family_count       151
  shown              5

total_weight  root_count  family                                      boundary_category  primitive_boundary
        3014          15  physical.lithography.medium                 primitive-root     True
        2185          11  physical.lithography                        primitive-root     True
        1943           8  physical.lithography.source_plasma_drive    primitive-root     True
        1866          18  physical.mosfet                             primitive-root     True
        1293           8  physical.process                            primitive-root     True
```

This ranks unresolved root-input families by downstream impact. The full command also prints representative top roots for each family.

## Next-work compass

```powershell
python -m gpu_stack.cli next-work
```

Observed summary:

```text
Next work:
  graph evidence: variables=1517 equations=950 root_inputs=619

Top 3 highest impact:
  1. Close the sourced Pythia cost frontier
  2. Pay down the heaviest root-debt family
  3. Finish metadata coverage before widening scenarios

4 best implementations:
  1. Registry import graph is currently coherent
  2. Pythia sourced pack resolves the non-cost targets
  3. EUV tin120 assumption pack is cleanly bounded
  4. Dense cost fixture still exercises the full rollup
```

Caveat: `python -m gpu_stack.cli next-work --limit 5` does not work in the current CLI. The subcommand currently supports only `--json`.

## Dense training cost fixture

```powershell
python -m gpu_stack.cli scenario-report scenarios.dense_training_cost_fixture --json
```

Observed summary:

```json
{
  "preset": "dense_training_cost_fixture",
  "status": "ok",
  "assignment_count": 30,
  "target_count": 4,
  "ok_count": 4,
  "error_count": 0,
  "issue_count": 0,
  "ok_target_labels": [
    "tokens_per_second",
    "job_dc_power",
    "run_power_cost",
    "cost_per_token"
  ]
}
```

Representative resolved values:

```text
training.tokens_per_sec = 6666666.66666667
econ.job.dc_power       = 5200.0
econ.run.power_cost     = 0.00078
econ.cost.per_token     = 3.000078e-06
```

Caveat: the fixture source says these are synthetic, round-number assumptions for deterministic tests. They are not historical data, vendor specifications, or price recommendations.
