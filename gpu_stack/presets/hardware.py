"""
gpu_stack.presets.hardware
==========================

Hardware-layer presets.

`demo_rack` is a tiny self-consistent bundle taken straight from
`gpu_stack.demo`: 9 nodes per rack, 8 GPUs per node, 15 PFLOP/s per GPU at
`gpu.peak_flops`. It exists as a regression anchor, not as real hardware
data. The H100 and DGX H100 presets are the opposite: narrow vendor-spec
bundles that assign only values mapping cleanly onto registered variables,
with the official NVIDIA source text cited in `source` and `notes`.

To add a hardware preset, create a new module-level `Preset` with a
concrete `source` string citing a vendor datasheet or technical report.
Never invent numbers.
"""

from ..core.presets import Preset
from ..core.registry import Registry


def _registered_assignments(assignments: dict[str, float]) -> dict[str, float]:
    unknown = [name for name in assignments if name not in Registry.variables]
    if unknown:
        raise ValueError(
            "hardware preset assignments reference unknown variables: "
            f"{sorted(unknown)}"
        )
    return assignments


_H100_SXM_80GB_SOURCE = (
    "NVIDIA H100 GPU product specifications, "
    "https://www.nvidia.com/en-us/data-center/h100/ "
    "(accessed 2026-05-06): H100 SXM lists FP32=67 teraFLOPS, "
    "FP16 Tensor Core*=1,979 teraFLOPS, GPU Memory=80GB, "
    "GPU Memory Bandwidth=3.35TB/s, Max Thermal Design Power (TDP)="
    "Up to 700W (configurable), and Interconnect=NVIDIA NVLink 900GB/s. "
    "Footnote: * With sparsity."
)

_H100_UNIT_NOTE = (
    "Vendor GB/TB/GB/s/TB/s strings are converted with decimal SI prefixes: "
    "80GB -> 80e9 byte, 3.35TB/s -> 3.35e12 byte/s, and "
    "900GB/s -> 900e9 byte/s."
)

_H100_PRECISION_NOTE = (
    "FP32 67 teraFLOPS is assigned to gpu.peak_flops. The FP16 Tensor Core "
    "1,979 teraFLOPS entry carries NVIDIA's sparsity footnote, so it is "
    "assigned only to gpu.peak_flops_sparse rather than to the generic dense "
    "peak variable."
)

_H100_SXM_80GB_ASSIGNMENTS = _registered_assignments(
    {
        "gpu.peak_flops": 67e12,
        "gpu.peak_flops_sparse": 1_979e12,
        "gpu.tdp": 700.0,
        "gpu.nvlink.bw": 900e9,
        "mem.hbm.capacity": 80e9,
        "mem.hbm.bw": 3.35e12,
    }
)

_DGX_H100_NODE_SOURCE = (
    "NVIDIA DGX H100/H200 User Guide, Introduction to NVIDIA DGX H100/H200 "
    "Systems, Table 1, "
    "https://docs.nvidia.com/dgx/dgxh100-user-guide/"
    "introduction-to-dgxh100.html (accessed 2026-05-06): For H100, "
    "8 x NVIDIA H100 GPUs provide 640 GB total GPU memory; CPU is "
    "2 x Intel Xeon 8480C PCIe Gen5 CPUs with 56 cores each; "
    "Network (Cluster) card is 8 x NVIDIA ConnectX-7 Single Port "
    "InfiniBand Cards, each up to 400Gbps; system memory is 2 TB using "
    "32 x DIMMs."
)

_DGX_H100_NODE_ASSIGNMENTS = _registered_assignments(
    {
        **_H100_SXM_80GB_ASSIGNMENTS,
        "cluster.node.n_gpus": 8,
        "cluster.node.hbm_capacity": 640e9,
        "cluster.node.n_cpus": 2,
        "cluster.node.ram": 2e12,
        "cluster.node.nic.count": 8,
        "cluster.node.nic.ports_per_nic": 1,
        "cluster.node.nic.port_rate": 50e9,
    }
)


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


h100_sxm_80gb_gpu = Preset(
    name="h100_sxm_80gb_gpu",
    description=(
        "Official NVIDIA H100 SXM per-GPU specification bundle for the "
        "80GB part: FP32 peak, sparsity-footnoted FP16 Tensor Core peak, "
        "TDP, NVLink bandwidth, and HBM capacity/bandwidth."
    ),
    assignments=_H100_SXM_80GB_ASSIGNMENTS,
    source=_H100_SXM_80GB_SOURCE,
    notes=(
        _H100_UNIT_NOTE,
        _H100_PRECISION_NOTE,
        "This preset does not assign lower-level HBM stack/channel/pin "
        "parameters or protocol efficiencies because those are not present "
        "in the cited NVIDIA product-specification string.",
    ),
)


dgx_h100_8gpu_node = Preset(
    name="dgx_h100_8gpu_node",
    description=(
        "Official NVIDIA DGX H100 node-style preset with eight H100 GPUs, "
        "total GPU memory, CPU count, host memory, and cluster NIC line-rate "
        "topology, plus the H100 SXM per-GPU facts."
    ),
    assignments=_DGX_H100_NODE_ASSIGNMENTS,
    source=f"{_H100_SXM_80GB_SOURCE} {_DGX_H100_NODE_SOURCE}",
    notes=(
        _H100_UNIT_NOTE,
        _H100_PRECISION_NOTE,
        "DGX cluster networking is assigned as 8 single-port ConnectX-7 "
        "cards at 400Gbps each, converted to 50e9 byte/s per port; no "
        "protocol efficiency or bidirectional aggregate is inferred.",
        "The DGX total GPU memory value is assigned directly to "
        "cluster.node.hbm_capacity because the cited NVIDIA string reports "
        "the node total. Per-GPU HBM stack, ECC, compression, and controller "
        "efficiency parameters remain unassigned.",
    ),
)


__all__ = ["demo_rack", "h100_sxm_80gb_gpu", "dgx_h100_8gpu_node"]
