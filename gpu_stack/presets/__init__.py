"""
gpu_stack.presets
=================

Named, provenanced scenario presets.

Presets bundle scenario assignments so a resolver call can evaluate a target
variable without the caller rediscovering every input by hand. The framework
lives in `gpu_stack.core.presets`; this package holds concrete instances
organized by domain (hardware, workload, run-economics).

Current inventory:

* `hardware.demo_rack`: minimal rack-level hardware scenario matching the
  GB300-class numbers already shipped in `gpu_stack.demo`. Intended as the
  canonical regression-test preset rather than a calibrated vendor spec.
* `workload.dense_variant_selector`: a workload preset that pins the
  dense / MoE variant selectors to "dense" for every variable tagged as a
  dense-vs-MoE VARIANT family.
* `workload.moe_variant_selector`: the MoE counterpart.

Each instance carries a `source` string so downstream auditing knows where
the numbers came from. Presets without a cited source are marked as
assumptions and should not be treated as authoritative.
"""

from . import hardware, workload

__all__ = ["hardware", "workload"]
