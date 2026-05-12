"""
tests/test_hardware_presets.py
==============================

Focused provenance and strict-assignment coverage for hardware presets.
"""

import pytest

from gpu_stack import Registry
from gpu_stack.presets import hardware


H100_SXM_80GB_ASSIGNMENTS = {
    "gpu.peak_flops": 67e12,
    "gpu.peak_flops_sparse": 1_979e12,
    "gpu.tdp": 700.0,
    "gpu.nvlink.bw": 900e9,
    "mem.hbm.capacity": 80e9,
    "mem.hbm.bw": 3.35e12,
}

DGX_H100_8GPU_NODE_ASSIGNMENTS = {
    **H100_SXM_80GB_ASSIGNMENTS,
    "cluster.node.n_gpus": 8,
    "cluster.node.hbm_capacity": 640e9,
    "cluster.node.n_cpus": 2,
    "cluster.node.ram": 2e12,
    "cluster.node.nic.count": 8,
    "cluster.node.nic.ports_per_nic": 1,
    "cluster.node.nic.port_rate": 50e9,
}


@pytest.mark.parametrize(
    ("preset", "tokens"),
    [
        (
            hardware.h100_sxm_80gb_gpu,
            (
                "NVIDIA H100 GPU product specifications",
                "https://www.nvidia.com/en-us/data-center/h100/",
                "H100 SXM",
                "FP32=67 teraFLOPS",
                "FP16 Tensor Core*=1,979 teraFLOPS",
                "GPU Memory=80GB",
                "GPU Memory Bandwidth=3.35TB/s",
                "Up to 700W",
                "NVIDIA NVLink 900GB/s",
                "Footnote: * With sparsity",
            ),
        ),
        (
            hardware.dgx_h100_8gpu_node,
            (
                "NVIDIA DGX H100/H200 User Guide",
                "https://docs.nvidia.com/dgx/dgxh100-user-guide/",
                "8 x NVIDIA H100 GPUs",
                "640 GB total GPU memory",
                "2 x Intel Xeon 8480C",
                "8 x NVIDIA ConnectX-7 Single Port InfiniBand Cards",
                "up to 400Gbps",
                "2 TB using 32 x DIMMs",
            ),
        ),
    ],
)
def test_hardware_presets_record_official_nvidia_source_strings(preset, tokens):
    source = preset.source or ""

    assert source
    for token in tokens:
        assert token in source
    assert any("decimal SI prefixes" in note for note in preset.notes)


def test_h100_sxm_80gb_assigns_exact_sourced_values():
    assert dict(hardware.h100_sxm_80gb_gpu.assignments) == H100_SXM_80GB_ASSIGNMENTS


def test_dgx_h100_node_assigns_exact_sourced_values():
    assert dict(hardware.dgx_h100_8gpu_node.assignments) == DGX_H100_8GPU_NODE_ASSIGNMENTS


@pytest.mark.parametrize(
    "preset",
    [
        hardware.h100_sxm_80gb_gpu,
        hardware.dgx_h100_8gpu_node,
    ],
)
def test_hardware_preset_assignments_are_registered_numeric_and_frozen(preset):
    for name, value in preset.assignments.items():
        assert name in Registry.variables
        assert isinstance(value, (int, float))

    first_key = next(iter(preset.assignments))
    with pytest.raises(TypeError):
        preset.assignments[first_key] = 0


def test_dgx_h100_node_resolves_peak_flops_from_h100_fp32_fact():
    result = hardware.dgx_h100_8gpu_node.resolve("cluster.node.peak_flops")

    assert float(result.value) == pytest.approx(8 * 67e12)
    assert any(step.equation == "cluster.eq.node_peak_flops" for step in result.trace)


def test_dgx_h100_node_resolves_cluster_nic_raw_bandwidth():
    result = hardware.dgx_h100_8gpu_node.resolve("cluster.node.nic_bw_raw")

    assert float(result.value) == pytest.approx(8 * 1 * 50e9)
    assert any(step.equation == "cluster.eq.node_nic_bw_raw" for step in result.trace)
