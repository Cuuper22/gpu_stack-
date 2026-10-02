"""
gpu_stack.presets
=================

Concrete, named scenario presets with provenance.

A preset is a bundle of variable assignments: it fills in every input a
resolver call needs to evaluate a target, so callers do not have to
rediscover each number by hand. The machinery for building presets lives in
`gpu_stack.core.presets`; this package holds the actual instances, grouped
by domain: hardware, workload, economics, lithography exposure optics, and
combined scenarios.

Current inventory:

* `hardware.demo_rack`: minimal rack-level hardware scenario matching the
  GB300-class numbers already shipped in `gpu_stack.demo`. Intended as the
  canonical regression-test preset rather than a calibrated vendor spec.
* `hardware.h100_sxm_80gb_gpu` and `hardware.dgx_h100_8gpu_node`: sourced
  NVIDIA H100 SXM and DGX H100 bundles that assign only vendor facts with a
  registered variable mapping.
* `workload.pythia_70m_dense_training`: sourced EleutherAI Pythia-70M dense
  GPT-NeoX workload and model-shape facts.
* `workload.dense_variant_selector`: a workload preset that pins the
  dense / MoE variant selectors to "dense" for every variable tagged as a
  dense-vs-MoE VARIANT family.
* `workload.moe_variant_selector`: the MoE counterpart.
* `economics.POWER_PRICE_PRESETS`: EIA 2024 historical average flat power
  tariffs for U.S. and California commercial/industrial electricity prices.
* `lithography.euv_exposure` and `lithography.arf_immersion_exposure`:
  exposure optics (wavelength, numerical aperture, medium index) for EUV at
  13.5 nm and ArF immersion at 193 nm, from ASML product specifications.
* `scenarios.dense_training_cost_fixture`: synthetic end-to-end fixture that
  resolves training step time, allocated site power, run cost, and cost per
  token through the existing resolver. Values are round-number assumptions,
  not historical or vendor data.
* `scenarios.pythia_70m_dgx_h100_us_2024_industrial_power`: sourced scenario
  pack combining DGX H100 hardware, Pythia-70M workload facts, EIA 2024 U.S.
  industrial power pricing, and explicit single-node run closures.
* `scenarios.pythia_70m_dgx_h100_us_2024_industrial_energy_floor_cost`:
  assumption-labeled cost-floor pack that composes the sourced Pythia/DGX
  industrial-power scenario with zero non-energy-cost boundary assumptions so
  `econ.cost.per_token` resolves as electricity-only run cost, not fully
  allocated datacenter TCO.

Every instance carries a `source` string, so an audit can trace each number
back to where it came from. A preset without a cited source is labeled an
assumption and should not be treated as authoritative.
"""

from . import dgx_h100_tco, economics, hardware, lithography, scenarios, workload

__all__ = [
    "dgx_h100_tco",
    "economics",
    "hardware",
    "lithography",
    "scenarios",
    "workload",
]
