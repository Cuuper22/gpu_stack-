"""
gpu_stack.presets.hardware
==========================

Hardware-layer presets.

The only preset defined here right now is `demo_rack`, a small,
self-consistent bundle drawn directly from `gpu_stack.demo`: 9 nodes per
rack, 8 GPUs per node, and 15 PFLOP/s per GPU at the `gpu.peak_flops`
level. The preset is deliberately conservative. It does not try to carry
a full hardware profile because the foundational numbers for that are
not yet sourced with the rigor this file wants for calibrated presets.

Add new hardware presets as separate module-level `Preset` instances
with concrete `source` strings citing a vendor datasheet or technical
report. Do not fabricate numbers.
"""

from ..core.presets import Preset


demo_rack = Preset(
    name="demo_rack",
    description=(
        "Rack-level hardware skeleton used by gpu_stack.demo. 9 nodes per "
        "rack, 8 GPUs per node, and 15 PFLOP/s per GPU. The preset is "
        "intentionally limited to the three variables exercised in the "
        "demo so it stays easy to audit."
    ),
    assignments={
        "cluster.rack.n_nodes": 9,
        "cluster.node.n_gpus": 8,
        "gpu.peak_flops": 1.5e16,
    },
    source=(
        "gpu_stack/demo.py: matches the substitution example used for "
        "cluster.rack.peak_flops that evaluates to 1.08 EFLOP/s. Not "
        "calibrated to any specific shipping platform."
    ),
    notes=(
        "Use this preset as a regression anchor for the resolver rather "
        "than as authoritative hardware numbers.",
    ),
)


__all__ = ["demo_rack"]
