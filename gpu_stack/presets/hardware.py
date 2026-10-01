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

# Dense BF16 tensor-core peak, the number a training run is actually bound by.
# NVIDIA lists FP16/BF16 Tensor Core 1,979 teraFLOPS "with sparsity" for H100
# SXM (footnote in the source string above). Dense is half of the sparse figure:
# 989.4 teraFLOPS (1,978.9 / 2 in NVIDIA's H100 architecture whitepaper table).
H100_SXM_BF16_DENSE_FLOPS = 989.4e12

# Assumption, not a vendor fact: sustained model-FLOPs utilization (MFU) of the
# dense BF16 peak that scenario closures apply when they need an effective
# training throughput. Published large-run MFU is roughly 38-43% for BF16 Llama 3
# on H100 (Dubey et al., The Llama 3 Herd of Models, 2024, Table 4) and 46% for
# PaLM on TPU v4 (Chowdhery et al., 2022). Small models on one node can be
# lower. Change it per scenario; it is not measured for any preset here.
ASSUMED_TRAINING_MFU = 0.40

# Effective per-GPU training throughput used by the one-node DGX H100 scenario
# closures: dense BF16 peak times the assumed MFU above (395.76 teraFLOPS).
H100_SXM_ASSUMED_SUSTAINED_BF16_FLOPS = H100_SXM_BF16_DENSE_FLOPS * ASSUMED_TRAINING_MFU

_GIB = 2**30

_H100_UNIT_NOTE = (
    "Bandwidth and rate strings are converted with decimal SI prefixes: "
    "3.35TB/s -> 3.35e12 byte/s. Memory is the exception: NVIDIA's 80GB "
    "(and 640 GB for eight GPUs) is read as 80 GiB = 85,899,345,920 byte "
    "(and 640 GiB), inferred because HBM dies are sized in binary Gib; the "
    "datasheet does not state the base. A decimal reading would be 7% lower."
)

_H100_NVLINK_NOTE = (
    "NVLink 900GB/s is NVIDIA's bidirectional total (inferred from NVIDIA's "
    "NVLink convention of counting both directions: 18 links x 50 GB/s). "
    "gpu.nvlink.bw is assigned per direction, 450e9 byte/s, because the "
    "collective beta term (1 / effective bandwidth) charges bytes moved in "
    "one direction."
)

_H100_PRECISION_NOTE = (
    "gpu.peak_flops is the dense BF16 Tensor Core peak, 989.4 teraFLOPS, "
    "which is the sparsity-footnoted 1,979 teraFLOPS figure halved. The "
    "listed FP32 67 teraFLOPS is not assigned: it is the CUDA-core rate and "
    "is not what a BF16 training run uses. The 1,979 teraFLOPS sparse value "
    "stays on gpu.peak_flops_sparse."
)

_H100_SXM_80GB_ASSIGNMENTS = _registered_assignments(
    {
        "gpu.peak_flops": H100_SXM_BF16_DENSE_FLOPS,
        "gpu.peak_flops_sparse": 1_979e12,
        "gpu.tdp": 700.0,
        "gpu.nvlink.bw": 450e9,
        "mem.hbm.capacity": 80 * _GIB,
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
        "cluster.node.hbm_capacity": 640 * _GIB,
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
        "80GB part: dense BF16 Tensor Core peak, sparsity-footnoted FP16 "
        "Tensor Core peak, TDP, per-direction NVLink bandwidth, and HBM "
        "capacity/bandwidth."
    ),
    assignments=_H100_SXM_80GB_ASSIGNMENTS,
    source=_H100_SXM_80GB_SOURCE,
    notes=(
        _H100_UNIT_NOTE,
        _H100_NVLINK_NOTE,
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
        _H100_NVLINK_NOTE,
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


__all__ = [
    "ASSUMED_TRAINING_MFU",
    "H100_SXM_ASSUMED_SUSTAINED_BF16_FLOPS",
    "H100_SXM_BF16_DENSE_FLOPS",
    "demo_rack",
    "dgx_h100_8gpu_node",
    "h100_sxm_80gb_gpu",
]
