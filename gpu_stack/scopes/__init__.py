"""
scopes
======

Each module in this package represents one physical or logical scope of the
training stack. Importing a scope module registers its Variables and
Equations with the global Registry.

Load order (smallest to largest scale). Scopes later in the list can depend
on earlier ones; never the reverse.
"""

# Authoritative load order; the top-level gpu_stack/__init__.py iterates this.
SCOPE_MODULES = [
    # Depth 0: no internal deps besides core/constants
    "physical",
    "memory_cell",
    "memory_subsystem",
    "precision",
    "parallelism",
    "architecture",

    # Depth 1: depends on exactly one earlier scope
    "arithmetic",        # -> physical
    "optimizer",         # -> parallelism

    # Depth 2-3: multi-scope consumers
    "gpu",               # -> arithmetic, memory_subsystem, physical
    "interconnect",      # -> gpu
    "kernel",            # -> gpu, memory_subsystem
    "collective",        # -> interconnect

    # Training-level aggregation
    "training",          # -> gpu, parallelism, architecture

    # System-scale (cluster and above)
    "cluster",           # -> gpu, memory_subsystem, interconnect
    "thermal",           # -> gpu, cluster
    "economics",         # -> gpu, thermal, cluster, training, parallelism
]


SCOPE_DESCRIPTIONS = {
    "physical":         "electrons, current, transistor, gate, RC delay, CMOS power, time-of-flight",
    "memory_cell":      "SRAM 6T, DRAM 1T1C, flip-flop",
    "memory_subsystem": "register file, SMEM, TMEM, L1, L2, HBM bandwidth and latency",
    "precision":        "FP formats, microscaling (MXFP4/NVFP4), stochastic rounding",
    "parallelism":      "DP, TP, PP, EP, CP, FSDP memory, pipeline bubbles",
    "architecture":     "transformer block, attention variants, MoE, KV cache, 6*P*T",
    "arithmetic":       "ALU, FMA, Tensor Core MMA, peak SM FLOPs",
    "optimizer":        "AdamW, Muon, MuonClip, optimizer state memory",
    "gpu":              "SM count, die peak, package power, NVLink per GPU",
    "interconnect":     "NVLink, IB, Spectrum-X, alpha-beta cost model",
    "kernel":           "arithmetic intensity, roofline, matmul + attention kernels",
    "collective":       "AllReduce, AllGather, ReduceScatter, All-to-all, async-TP",
    "training":         "T_step = T_compute + T_ec + T_mb + T_bub, MFU, tokens/s",
    "cluster":          "node -> rack -> cluster -> hyperscaler aggregation",
    "thermal":          "junction-to-ambient resistance, coolant flow, PUE",
    "economics":        "GPU amortization, $/kWh, $/token, run cost",
}


def loaded_scopes():
    """Return the list of scope module names that are currently importable."""
    import importlib
    out = []
    for name in SCOPE_MODULES:
        try:
            importlib.import_module(f".{name}", package=__name__)
            out.append(name)
        except ImportError:
            pass
    return out
