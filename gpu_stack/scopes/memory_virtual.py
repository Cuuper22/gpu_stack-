"""
scopes/memory_virtual.py
========================

The costs of pretending memory is flat: translation, host links, NUMA.

Programs use virtual addresses, and every access must be translated. The
TLB caches translations, and its reach — entries times effective page
size — is the footprint it can cover without missing; mixing huge pages
into the ordinary ones stretches the effective page size and therefore
the reach. Average translation latency then weights the hit and
miss-penalty paths by the hit rate, and the cache helper adds it to every
global load.

Beyond the package, this module prices the host side: PCIe bandwidth from
lanes, lane rate, and efficiency; CXL bandwidth and latency for pooled
memory; unified-memory page faults, whose service plus migration cost
makes transparent oversubscription expensive; and NUMA, where remote
socket access pays measurable bandwidth and latency penalty ratios over
local. The offload models in the parallelism scope lean on these numbers.
"""

import sympy as sp

from ..core import Reference, eq, var
from ..core.units import BPS, SECOND


BYTE = BPS * SECOND
DIMENSIONLESS = sp.Integer(1)

TLB_REF = Reference(
    "GPU TLB organization and huge-page mixing are described in NVIDIA GPU "
    "architecture whitepapers and CUDA programming documentation.",
    kind="datasheet",
)
PCIE_REF = Reference(
    "PCIe lane rate and efficiency are specified in the PCI Express Base "
    "Specification; current generation is PCIe 5.0 or 6.0 from PCI-SIG.",
    kind="standard",
)
CXL_REF = Reference(
    "CXL memory link bandwidth and latency are specified in the CXL "
    "Specification from CXL Consortium (CXL 3.0 and later).",
    kind="standard",
)
NUMA_REF = Reference(
    "NUMA bandwidth and latency hierarchy in multi-socket servers is "
    "characterized in platform datasheets and Linux numactl/numastat tooling.",
    kind="datasheet",
)
UM_REF = Reference(
    "Unified memory page-fault service overhead and migration latency over "
    "PCIe or NVLink are characterized in NVIDIA CUDA documentation.",
    kind="datasheet",
)


# ---------------------------------------------------------------------------
# Translation, TLBs, huge pages, and unified memory
# ---------------------------------------------------------------------------

tlb_entries = var(
    "mem.tlb.entries", "N_TLB", "entries",
    "Effective GPU TLB entry count for the path under study.",
    scope="memory_subsystem",
    sp_units=DIMENSIONLESS,
    references=[TLB_REF],
)
page_bytes = var(
    "mem.tlb.page_bytes", "B_page", "byte",
    "Base page size.",
    scope="memory_subsystem",
    sp_units=BYTE,
    references=[TLB_REF],
)
huge_page_bytes = var(
    "mem.tlb.huge_page_bytes", "B_page_huge", "byte",
    "Huge page size.",
    scope="memory_subsystem",
    sp_units=BYTE,
    references=[TLB_REF],
)
huge_page_fraction = var(
    "mem.tlb.huge_page_fraction", "phi_huge", "dimensionless",
    "Fraction of translations backed by huge pages.",
    scope="memory_subsystem",
    sp_units=DIMENSIONLESS,
    references=[TLB_REF],
)
effective_page_bytes = var(
    "mem.tlb.page_bytes_effective", "B_page_eff", "byte",
    "Average page size seen by the TLB after mixing base and huge pages.",
    scope="memory_subsystem",
    sp_units=BYTE,
    references=[TLB_REF],
)
tlb_reach = var(
    "mem.tlb.reach", "B_TLB_reach", "byte",
    "Address footprint covered by the active TLB.",
    scope="memory_subsystem",
    sp_units=BYTE,
    references=[TLB_REF],
)
tlb_hit_rate = var(
    "mem.tlb.hit_rate", "p_hit_TLB", "dimensionless",
    "TLB hit probability.",
    scope="memory_subsystem",
    sp_units=DIMENSIONLESS,
    references=[TLB_REF],
)
tlb_miss_penalty = var(
    "mem.tlb.miss_penalty", "t_miss_TLB", "s",
    "Translation miss penalty.",
    scope="memory_subsystem",
    sp_units=SECOND,
    references=[TLB_REF],
)
avg_translation_latency = var(
    "mem.tlb.latency_avg", "t_TLB_avg", "s",
    "Average translation latency.",
    scope="memory_subsystem",
    sp_units=SECOND,
    references=[TLB_REF],
)
pcie_lanes_per_gpu = var(
    "mem.pcie.lanes_per_gpu", "N_lane_PCIe", "lanes",
    "PCIe lane count exposed to one GPU.",
    scope="memory_subsystem",
    sp_units=DIMENSIONLESS,
    references=[PCIE_REF],
)
pcie_lane_rate_raw = var(
    "mem.pcie.lane_rate_raw", "r_lane_PCIe", "byte/s/lane",
    "Raw payload-capable lane throughput after encoding is accounted for separately.",
    scope="memory_subsystem",
    sp_units=BPS,
    references=[PCIE_REF],
)
pcie_efficiency = var(
    "mem.pcie.efficiency", "eta_PCIe", "dimensionless",
    "Protocol and payload efficiency of PCIe transfers.",
    scope="memory_subsystem",
    sp_units=DIMENSIONLESS,
    references=[PCIE_REF],
)
pcie_bw = var(
    "mem.pcie.bw", "BW_PCIe", "byte/s",
    "Effective PCIe bandwidth to the GPU.",
    scope="memory_subsystem",
    sp_units=BPS,
    references=[PCIE_REF],
)
cxl_bw = var(
    "mem.cxl.bw", "BW_CXL", "byte/s",
    "CXL memory-link bandwidth.",
    scope="memory_subsystem",
    sp_units=BPS,
    references=[CXL_REF],
)
cxl_latency = var(
    "mem.cxl.latency", "t_CXL", "s",
    "CXL memory access latency.",
    scope="memory_subsystem",
    sp_units=SECOND,
    references=[CXL_REF],
)
um_page_bytes = var(
    "mem.um.page_bytes", "B_page_UM", "byte",
    "Unified-memory migration granularity.",
    scope="memory_subsystem",
    sp_units=BYTE,
    references=[UM_REF],
)
um_page_fault_service = var(
    "mem.um.page_fault_service", "t_fault_UM", "s",
    "Page-fault servicing overhead excluding pure data transfer time.",
    scope="memory_subsystem",
    sp_units=SECOND,
    references=[UM_REF],
)
um_page_migration_latency = var(
    "mem.um.page_migration_latency", "t_mig_UM", "s",
    "Unified-memory page migration latency over the host link.",
    scope="memory_subsystem",
    sp_units=SECOND,
    references=[UM_REF],
)


# ---------------------------------------------------------------------------
# Host-side NUMA effects
# ---------------------------------------------------------------------------

host_numa_local_bw = var(
    "mem.numa.local_bw", "BW_NUMA_local", "byte/s",
    "Host memory bandwidth from the local NUMA domain.",
    scope="memory_subsystem",
    sp_units=BPS,
    references=[NUMA_REF],
)
host_numa_remote_bw = var(
    "mem.numa.remote_bw", "BW_NUMA_remote", "byte/s",
    "Host memory bandwidth from a remote NUMA domain.",
    scope="memory_subsystem",
    sp_units=BPS,
    references=[NUMA_REF],
)
host_numa_local_latency = var(
    "mem.numa.local_latency", "t_NUMA_local", "s",
    "Host memory latency from the local NUMA domain.",
    scope="memory_subsystem",
    sp_units=SECOND,
    references=[NUMA_REF],
)
host_numa_remote_latency = var(
    "mem.numa.remote_latency", "t_NUMA_remote", "s",
    "Host memory latency from a remote NUMA domain.",
    scope="memory_subsystem",
    sp_units=SECOND,
    references=[NUMA_REF],
)
host_numa_bw_penalty = var(
    "mem.numa.bw_penalty", "k_NUMA_bw", "dimensionless",
    "Bandwidth penalty factor for remote NUMA access.",
    scope="memory_subsystem",
    sp_units=DIMENSIONLESS,
    references=[NUMA_REF],
)
host_numa_latency_penalty = var(
    "mem.numa.latency_penalty", "k_NUMA_lat", "dimensionless",
    "Latency inflation factor for remote NUMA access.",
    scope="memory_subsystem",
    sp_units=DIMENSIONLESS,
    references=[NUMA_REF],
)


eq_effective_page_bytes = eq(
    "mem.eq.tlb_effective_page_bytes",
    effective_page_bytes.symbol,
    (1 - huge_page_fraction.symbol) * page_bytes.symbol + huge_page_fraction.symbol * huge_page_bytes.symbol,
    "Average page size after mixing base and huge pages.",
    references=[TLB_REF],
    check_units=True,
)

eq_tlb_reach = eq(
    "mem.eq.tlb_reach",
    tlb_reach.symbol,
    tlb_entries.symbol * effective_page_bytes.symbol,
    "TLB reach equals entry count times effective page size.",
    references=[TLB_REF],
    check_units=True,
)

eq_tlb_latency_avg = eq(
    "mem.eq.tlb_latency_avg",
    avg_translation_latency.symbol,
    (1 - tlb_hit_rate.symbol) * tlb_miss_penalty.symbol,
    "Average translation latency from TLB misses only, with hits treated as the baseline path.",
    references=[TLB_REF],
    check_units=True,
)

eq_pcie_bw = eq(
    "mem.eq.pcie_bw",
    pcie_bw.symbol,
    pcie_lanes_per_gpu.symbol * pcie_lane_rate_raw.symbol * pcie_efficiency.symbol,
    "Effective PCIe bandwidth from lane count, lane rate, and protocol efficiency.",
    references=[PCIE_REF],
    check_units=True,
)

eq_um_page_migration = eq(
    "mem.eq.um_page_migration_latency",
    um_page_migration_latency.symbol,
    um_page_bytes.symbol / pcie_bw.symbol + um_page_fault_service.symbol,
    "Unified-memory migration latency from data transfer time plus page-fault service overhead.",
    references=[UM_REF],
    check_units=True,
)

eq_numa_bw_penalty = eq(
    "mem.eq.numa_bw_penalty",
    host_numa_bw_penalty.symbol,
    host_numa_local_bw.symbol / host_numa_remote_bw.symbol,
    "Remote-NUMA bandwidth penalty relative to local bandwidth.",
    references=[NUMA_REF],
    check_units=True,
)

eq_numa_latency_penalty = eq(
    "mem.eq.numa_latency_penalty",
    host_numa_latency_penalty.symbol,
    host_numa_remote_latency.symbol / host_numa_local_latency.symbol,
    "Remote-NUMA latency penalty relative to local latency.",
    references=[NUMA_REF],
    check_units=True,
)


MEMSUB_VIRTUAL_VARIABLES = (
    tlb_entries,
    page_bytes,
    huge_page_bytes,
    huge_page_fraction,
    effective_page_bytes,
    tlb_reach,
    tlb_hit_rate,
    tlb_miss_penalty,
    avg_translation_latency,
    pcie_lanes_per_gpu,
    pcie_lane_rate_raw,
    pcie_efficiency,
    pcie_bw,
    cxl_bw,
    cxl_latency,
    um_page_bytes,
    um_page_fault_service,
    um_page_migration_latency,
    host_numa_local_bw,
    host_numa_remote_bw,
    host_numa_local_latency,
    host_numa_remote_latency,
    host_numa_bw_penalty,
    host_numa_latency_penalty,
)

MEMSUB_VIRTUAL_EQUATIONS = (
    eq_effective_page_bytes,
    eq_tlb_reach,
    eq_tlb_latency_avg,
    eq_pcie_bw,
    eq_um_page_migration,
    eq_numa_bw_penalty,
    eq_numa_latency_penalty,
)


__all__ = [
    "tlb_entries",
    "page_bytes",
    "huge_page_bytes",
    "huge_page_fraction",
    "effective_page_bytes",
    "tlb_reach",
    "tlb_hit_rate",
    "tlb_miss_penalty",
    "avg_translation_latency",
    "pcie_lanes_per_gpu",
    "pcie_lane_rate_raw",
    "pcie_efficiency",
    "pcie_bw",
    "cxl_bw",
    "cxl_latency",
    "um_page_bytes",
    "um_page_fault_service",
    "um_page_migration_latency",
    "host_numa_local_bw",
    "host_numa_remote_bw",
    "host_numa_local_latency",
    "host_numa_remote_latency",
    "host_numa_bw_penalty",
    "host_numa_latency_penalty",
    "eq_effective_page_bytes",
    "eq_tlb_reach",
    "eq_tlb_latency_avg",
    "eq_pcie_bw",
    "eq_um_page_migration",
    "eq_numa_bw_penalty",
    "eq_numa_latency_penalty",
    "MEMSUB_VIRTUAL_VARIABLES",
    "MEMSUB_VIRTUAL_EQUATIONS",
]
