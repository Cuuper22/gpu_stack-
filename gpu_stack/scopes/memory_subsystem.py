"""
scopes/memory_subsystem.py
==========================

The memory hierarchy on a GPU, from per-thread registers out to HBM and host
attached memory.

The original file had the right nouns and almost none of the machinery that
makes those nouns expensive. This version adds banked bandwidth, cache
organization, translation overhead, host links, unified-memory migration, and
refresh or compression effects that materially change usable bandwidth or
capacity.
"""

import sympy as sp

from ..core import System, var, eq


sys_mem = System(
    name="memory_subsystem",
    scope="memory_subsystem",
    description="Register file, SMEM, TMEM, L1, L2, HBM, translation, and host-memory interfaces.",
)


# ---------------------------------------------------------------------------
# Common memory-array clocking
# ---------------------------------------------------------------------------

mem_array_clock = var(
    "mem.array.clock", "f_mem", "Hz",
    "Representative cycle rate for on-chip memory arrays and bank service.",
    scope="memory_subsystem",
)
warp_size = var(
    "mem.warp.size", "N_warp", "threads",
    "Threads per warp.",
    scope="memory_subsystem",
)
threads_per_sm_max = var(
    "mem.sm.threads_max", "N_thr_SM_max", "threads",
    "Maximum resident threads per SM.",
    scope="memory_subsystem",
)


# ---------------------------------------------------------------------------
# Per-thread register file
# ---------------------------------------------------------------------------

regs_per_thread = var(
    "mem.reg.per_thread", "N_reg_thr", "regs",
    "Registers allocated per GPU thread.",
    scope="memory_subsystem",
)
reg_width_bits = var(
    "mem.reg.width", "W_reg", "bit",
    "Width of a single architectural register.",
    scope="memory_subsystem",
)
reg_file_bytes_per_sm = var(
    "mem.reg.file_bytes_per_sm", "B_reg_sm", "byte",
    "Total register file size per SM.",
    scope="memory_subsystem",
)
reg_file_regs_per_sm = var(
    "mem.reg.file_regs_per_sm", "N_reg_sm", "regs",
    "Total physical registers per SM.",
    scope="memory_subsystem",
)
warps_per_sm_reg_limit = var(
    "mem.reg.warps_limit", "N_warp_reg_lim", "warps",
    "Register-file occupancy ceiling in resident warps per SM.",
    scope="memory_subsystem",
)
reg_bank_count = var(
    "mem.reg.bank_count", "N_bank_reg", "banks",
    "Number of physical register banks.",
    scope="memory_subsystem",
)
reg_bank_width_bits = var(
    "mem.reg.bank_width", "W_bank_reg", "bit",
    "Bytes or bits serviced per bank access.",
    scope="memory_subsystem",
)
reg_ports_per_bank = var(
    "mem.reg.ports_per_bank", "N_port_reg", "ports",
    "Effective read or write service ports per bank.",
    scope="memory_subsystem",
)
reg_bw_peak = var(
    "mem.reg.bw_peak", "BW_reg_peak", "byte/s",
    "Peak register-file bandwidth per SM before bank conflicts.",
    scope="memory_subsystem",
)
reg_bank_conflict_factor = var(
    "mem.reg.bank_conflict_factor", "k_reg_conf", "dimensionless",
    "Bandwidth loss factor from register-bank conflicts.",
    scope="memory_subsystem",
)
reg_bw_effective = var(
    "mem.reg.bw_effective", "BW_reg_eff", "byte/s",
    "Effective register-file bandwidth after bank conflicts.",
    scope="memory_subsystem",
)

eq_reg_file_regs = eq(
    "mem.eq.reg_file_regs_per_sm",
    reg_file_regs_per_sm.symbol,
    reg_file_bytes_per_sm.symbol * 8 / reg_width_bits.symbol,
    "Physical register count from bytes times 8 divided by bits per register.",
)

eq_reg_warp_limit = eq(
    "mem.eq.reg_warps_limit",
    warps_per_sm_reg_limit.symbol,
    reg_file_regs_per_sm.symbol / (regs_per_thread.symbol * warp_size.symbol),
    "Register-limited warp occupancy.",
)

eq_reg_bw_peak = eq(
    "mem.eq.reg_bw_peak",
    reg_bw_peak.symbol,
    reg_bank_count.symbol * reg_ports_per_bank.symbol * reg_bank_width_bits.symbol * mem_array_clock.symbol / 8,
    "Peak register bandwidth from banks, service width, ports, and cycle rate.",
)

eq_reg_bw_effective = eq(
    "mem.eq.reg_bw_effective",
    reg_bw_effective.symbol,
    reg_bw_peak.symbol / reg_bank_conflict_factor.symbol,
    "Effective register bandwidth after bank-conflict inflation.",
)


# ---------------------------------------------------------------------------
# Shared memory and L1
# ---------------------------------------------------------------------------

l1_smem_pool_bytes_per_sm = var(
    "mem.l1_smem.pool_bytes_per_sm", "B_L1SMEM_pool", "byte",
    "Unified on-SM SRAM pool partitioned between shared memory and L1.",
    scope="memory_subsystem",
)
smem_bytes_per_sm = var(
    "mem.smem.bytes_per_sm", "B_SMEM", "byte",
    "Shared-memory allocation carved out per SM.",
    scope="memory_subsystem",
)
smem_bw_per_sm = var(
    "mem.smem.bw_per_sm", "BW_SMEM_sm", "byte/s",
    "Effective shared-memory bandwidth per SM.",
    scope="memory_subsystem",
)
smem_latency = var(
    "mem.smem.latency", "t_SMEM", "s",
    "Shared-memory load latency.",
    scope="memory_subsystem",
)
l1_bytes_per_sm = var(
    "mem.l1.bytes_per_sm", "B_L1", "byte",
    "Effective L1 capacity after the SMEM carveout.",
    scope="memory_subsystem",
)
l1_line_bytes = var(
    "mem.l1.line_bytes", "B_line_L1", "byte",
    "L1 cache line size.",
    scope="memory_subsystem",
)
l1_assoc = var(
    "mem.l1.assoc", "A_L1", "ways",
    "L1 associativity.",
    scope="memory_subsystem",
)
l1_sets = var(
    "mem.l1.sets", "N_set_L1", "sets",
    "Number of L1 sets.",
    scope="memory_subsystem",
)
l1_hit_rate = var(
    "mem.l1.hit_rate", "p_hit_L1", "dimensionless",
    "L1 hit probability for the workload of interest.",
    scope="memory_subsystem",
)
l1_latency = var(
    "mem.l1.latency", "t_L1", "s",
    "L1-hit latency.",
    scope="memory_subsystem",
)
smem_bank_count = var(
    "mem.smem.bank_count", "N_bank_SMEM", "banks",
    "Shared-memory bank count.",
    scope="memory_subsystem",
)
smem_bank_width_bytes = var(
    "mem.smem.bank_width", "B_bank_SMEM", "byte",
    "Bytes served per bank access.",
    scope="memory_subsystem",
)
smem_ports_per_bank = var(
    "mem.smem.ports_per_bank", "N_port_SMEM", "ports",
    "Effective service ports per SMEM bank.",
    scope="memory_subsystem",
)
smem_bw_peak = var(
    "mem.smem.bw_peak", "BW_SMEM_peak", "byte/s",
    "Peak shared-memory bandwidth before conflicts.",
    scope="memory_subsystem",
)
smem_conflict_factor = var(
    "mem.smem.conflict_factor", "k_SMEM_conf", "dimensionless",
    "Bandwidth loss factor from shared-memory bank conflicts.",
    scope="memory_subsystem",
)

eq_l1_capacity = eq(
    "mem.eq.l1_capacity",
    l1_bytes_per_sm.symbol,
    l1_smem_pool_bytes_per_sm.symbol - smem_bytes_per_sm.symbol,
    "L1 capacity is whatever remains after carving out shared memory from the unified SRAM pool.",
)

eq_l1_sets = eq(
    "mem.eq.l1_sets",
    l1_sets.symbol,
    l1_bytes_per_sm.symbol / (l1_line_bytes.symbol * l1_assoc.symbol),
    "Set count from total bytes divided by line size times associativity.",
)

eq_smem_bw_peak = eq(
    "mem.eq.smem_bw_peak",
    smem_bw_peak.symbol,
    smem_bank_count.symbol * smem_bank_width_bytes.symbol * smem_ports_per_bank.symbol * mem_array_clock.symbol,
    "Peak SMEM bandwidth from bank count, width, ports, and cycle rate.",
)

eq_smem_bw_effective = eq(
    "mem.eq.smem_bw_effective",
    smem_bw_per_sm.symbol,
    smem_bw_peak.symbol / smem_conflict_factor.symbol,
    "Effective SMEM bandwidth after bank conflicts.",
)


# ---------------------------------------------------------------------------
# Tensor Memory (TMEM)
# ---------------------------------------------------------------------------

tmem_bytes_per_sm = var(
    "mem.tmem.bytes_per_sm", "B_TMEM", "byte",
    "Tensor Memory per SM.",
    scope="memory_subsystem",
)
tmem_bw_per_sm = var(
    "mem.tmem.bw_per_sm", "BW_TMEM_sm", "byte/s",
    "Tensor Memory bandwidth per SM.",
    scope="memory_subsystem",
)
tmem_mma_write_latency = var(
    "mem.tmem.mma_write_latency", "t_TMEM_w", "s",
    "Latency from MMA issue to TMEM accumulator update.",
    scope="memory_subsystem",
)
tmem_bank_count = var(
    "mem.tmem.bank_count", "N_bank_TMEM", "banks",
    "Tensor Memory bank count.",
    scope="memory_subsystem",
)
tmem_bank_width_bytes = var(
    "mem.tmem.bank_width", "B_bank_TMEM", "byte",
    "Bytes served per TMEM bank access.",
    scope="memory_subsystem",
)
tmem_ports_per_bank = var(
    "mem.tmem.ports_per_bank", "N_port_TMEM", "ports",
    "Effective service ports per TMEM bank.",
    scope="memory_subsystem",
)
tmem_bw_peak = var(
    "mem.tmem.bw_peak", "BW_TMEM_peak", "byte/s",
    "Peak TMEM bandwidth per SM.",
    scope="memory_subsystem",
)

eq_tmem_bw_peak = eq(
    "mem.eq.tmem_bw_peak",
    tmem_bw_peak.symbol,
    tmem_bank_count.symbol * tmem_bank_width_bytes.symbol * tmem_ports_per_bank.symbol * mem_array_clock.symbol,
    "Peak TMEM bandwidth from banks, width, ports, and cycle rate.",
)

eq_tmem_bw = eq(
    "mem.eq.tmem_bw",
    tmem_bw_per_sm.symbol,
    tmem_bw_peak.symbol,
    "TMEM bandwidth currently treated as peak service bandwidth because the access pattern is warp-synchronous and heavily structured.",
)


# ---------------------------------------------------------------------------
# L2 organization and miss penalties
# ---------------------------------------------------------------------------

l2_bytes = var(
    "mem.l2.bytes", "B_L2", "byte",
    "L2 cache capacity, chip-wide.",
    scope="memory_subsystem",
)
l2_bw = var(
    "mem.l2.bw", "BW_L2", "byte/s",
    "Aggregate L2 bandwidth.",
    scope="memory_subsystem",
)
l2_line_bytes = var(
    "mem.l2.line_bytes", "B_line_L2", "byte",
    "L2 cache line size.",
    scope="memory_subsystem",
)
l2_assoc = var(
    "mem.l2.assoc", "A_L2", "ways",
    "L2 associativity.",
    scope="memory_subsystem",
)
l2_partitions = var(
    "mem.l2.partitions", "N_part_L2", "partitions",
    "Independent L2 partitions or slices.",
    scope="memory_subsystem",
)
l2_sets_per_partition = var(
    "mem.l2.sets_per_partition", "N_set_L2", "sets",
    "Sets per L2 partition.",
    scope="memory_subsystem",
)
l2_hit_rate = var(
    "mem.l2.hit_rate", "p_hit_L2", "dimensionless",
    "Conditional L2 hit probability given an L1 miss.",
    scope="memory_subsystem",
)
l2_latency = var(
    "mem.l2.latency", "t_L2", "s",
    "L2-hit latency.",
    scope="memory_subsystem",
)
l2_miss_penalty = var(
    "mem.l2.miss_penalty", "t_miss_L2", "s",
    "Additional latency of an L2 miss that falls through to HBM.",
    scope="memory_subsystem",
)
avg_global_load_latency = var(
    "mem.global_load.latency_avg", "t_glob_avg", "s",
    "Average latency of a global-memory access after cache and translation effects.",
    scope="memory_subsystem",
)

eq_l2_sets = eq(
    "mem.eq.l2_sets_per_partition",
    l2_sets_per_partition.symbol,
    l2_bytes.symbol / (l2_partitions.symbol * l2_line_bytes.symbol * l2_assoc.symbol),
    "L2 sets per partition from total capacity, partition count, line size, and associativity.",
)


# ---------------------------------------------------------------------------
# HBM and its usable bandwidth or capacity
# ---------------------------------------------------------------------------

hbm_stack_count = var(
    "mem.hbm.stacks", "N_HBM_stacks", "units",
    "Number of HBM stacks on the package.",
    scope="memory_subsystem",
)
hbm_stack_capacity = var(
    "mem.hbm.stack_capacity", "B_HBM_stack", "byte",
    "Capacity per HBM stack.",
    scope="memory_subsystem",
)
hbm_capacity = var(
    "mem.hbm.capacity", "B_HBM", "byte",
    "Total raw HBM capacity per GPU package.",
    scope="memory_subsystem",
)
hbm_pins_per_stack = var(
    "mem.hbm.pins_per_stack", "N_pins_HBM", "pins",
    "Data pins per HBM stack.",
    scope="memory_subsystem",
)
hbm_pin_rate = var(
    "mem.hbm.pin_rate", "r_pin_HBM", "bit/s/pin",
    "Per-pin signaling rate.",
    scope="memory_subsystem",
)
hbm_bw_per_stack = var(
    "mem.hbm.bw_per_stack", "BW_HBM_stack", "byte/s",
    "Per-stack HBM bandwidth.",
    scope="memory_subsystem",
)
hbm_bw = var(
    "mem.hbm.bw", "BW_HBM", "byte/s",
    "Total raw HBM bandwidth per GPU package.",
    scope="memory_subsystem",
)
hbm_latency = var(
    "mem.hbm.latency", "t_HBM", "s",
    "Average HBM read latency.",
    scope="memory_subsystem",
)
hbm_refresh_overhead = var(
    "mem.hbm.refresh_overhead", "phi_refresh_HBM", "dimensionless",
    "Fraction of raw HBM bandwidth lost to refresh activity.",
    scope="memory_subsystem",
)
hbm_bw_effective = var(
    "mem.hbm.bw_effective", "BW_HBM_eff", "byte/s",
    "Usable HBM bandwidth after refresh overhead.",
    scope="memory_subsystem",
)
hbm_ecc_overhead = var(
    "mem.hbm.ecc_overhead", "phi_ecc_HBM", "dimensionless",
    "Fraction of raw HBM capacity consumed by ECC or metadata overhead.",
    scope="memory_subsystem",
)
hbm_capacity_usable = var(
    "mem.hbm.capacity_usable", "B_HBM_use", "byte",
    "Usable HBM capacity after ECC or metadata overhead.",
    scope="memory_subsystem",
)
mem_compression_ratio = var(
    "mem.hbm.compression_ratio", "rho_comp_mem", "dimensionless",
    "Effective compression ratio seen by memory traffic or footprint.",
    scope="memory_subsystem",
)
hbm_effective_capacity = var(
    "mem.hbm.capacity_effective", "B_HBM_eff_cap", "byte",
    "Effective HBM capacity after usable-capacity adjustment and compression.",
    scope="memory_subsystem",
)

eq_hbm_capacity = eq(
    "mem.eq.hbm_capacity",
    hbm_capacity.symbol,
    hbm_stack_count.symbol * hbm_stack_capacity.symbol,
    "HBM capacity equals stack count times per-stack capacity.",
)

eq_hbm_bw_per_stack = eq(
    "mem.eq.hbm_bw_per_stack",
    hbm_bw_per_stack.symbol,
    hbm_pins_per_stack.symbol * hbm_pin_rate.symbol / 8,
    "Per-stack HBM bandwidth in bytes per second.",
)

eq_hbm_bw_total = eq(
    "mem.eq.hbm_bw_total",
    hbm_bw.symbol,
    hbm_stack_count.symbol * hbm_bw_per_stack.symbol,
    "Total HBM bandwidth across all stacks.",
)

eq_hbm_bw_effective = eq(
    "mem.eq.hbm_bw_effective",
    hbm_bw_effective.symbol,
    hbm_bw.symbol * (1 - hbm_refresh_overhead.symbol),
    "Effective HBM bandwidth after refresh steals a fraction of service cycles.",
)

eq_hbm_capacity_usable = eq(
    "mem.eq.hbm_capacity_usable",
    hbm_capacity_usable.symbol,
    hbm_capacity.symbol * (1 - hbm_ecc_overhead.symbol),
    "Usable HBM capacity after ECC or metadata overhead.",
)

eq_hbm_capacity_effective = eq(
    "mem.eq.hbm_capacity_effective",
    hbm_effective_capacity.symbol,
    hbm_capacity_usable.symbol * mem_compression_ratio.symbol,
    "Effective HBM capacity after compression.",
)

eq_l2_miss_penalty = eq(
    "mem.eq.l2_miss_penalty",
    l2_miss_penalty.symbol,
    hbm_latency.symbol - l2_latency.symbol,
    "Additional latency of falling through from L2 to HBM.",
)


# ---------------------------------------------------------------------------
# Translation, TLBs, huge pages, and unified memory
# ---------------------------------------------------------------------------

tlb_entries = var(
    "mem.tlb.entries", "N_TLB", "entries",
    "Effective GPU TLB entry count for the path under study.",
    scope="memory_subsystem",
)
page_bytes = var(
    "mem.tlb.page_bytes", "B_page", "byte",
    "Base page size.",
    scope="memory_subsystem",
)
huge_page_bytes = var(
    "mem.tlb.huge_page_bytes", "B_page_huge", "byte",
    "Huge page size.",
    scope="memory_subsystem",
)
huge_page_fraction = var(
    "mem.tlb.huge_page_fraction", "phi_huge", "dimensionless",
    "Fraction of translations backed by huge pages.",
    scope="memory_subsystem",
)
effective_page_bytes = var(
    "mem.tlb.page_bytes_effective", "B_page_eff", "byte",
    "Average page size seen by the TLB after mixing base and huge pages.",
    scope="memory_subsystem",
)
tlb_reach = var(
    "mem.tlb.reach", "B_TLB_reach", "byte",
    "Address footprint covered by the active TLB.",
    scope="memory_subsystem",
)
tlb_hit_rate = var(
    "mem.tlb.hit_rate", "p_hit_TLB", "dimensionless",
    "TLB hit probability.",
    scope="memory_subsystem",
)
tlb_miss_penalty = var(
    "mem.tlb.miss_penalty", "t_miss_TLB", "s",
    "Translation miss penalty.",
    scope="memory_subsystem",
)
avg_translation_latency = var(
    "mem.tlb.latency_avg", "t_TLB_avg", "s",
    "Average translation latency.",
    scope="memory_subsystem",
)
pcie_lanes_per_gpu = var(
    "mem.pcie.lanes_per_gpu", "N_lane_PCIe", "lanes",
    "PCIe lane count exposed to one GPU.",
    scope="memory_subsystem",
)
pcie_lane_rate_raw = var(
    "mem.pcie.lane_rate_raw", "r_lane_PCIe", "byte/s/lane",
    "Raw payload-capable lane throughput after encoding is accounted for separately.",
    scope="memory_subsystem",
)
pcie_efficiency = var(
    "mem.pcie.efficiency", "eta_PCIe", "dimensionless",
    "Protocol and payload efficiency of PCIe transfers.",
    scope="memory_subsystem",
)
pcie_bw = var(
    "mem.pcie.bw", "BW_PCIe", "byte/s",
    "Effective PCIe bandwidth to the GPU.",
    scope="memory_subsystem",
)
cxl_bw = var(
    "mem.cxl.bw", "BW_CXL", "byte/s",
    "CXL memory-link bandwidth.",
    scope="memory_subsystem",
)
cxl_latency = var(
    "mem.cxl.latency", "t_CXL", "s",
    "CXL memory access latency.",
    scope="memory_subsystem",
)
um_page_bytes = var(
    "mem.um.page_bytes", "B_page_UM", "byte",
    "Unified-memory migration granularity.",
    scope="memory_subsystem",
)
um_page_fault_service = var(
    "mem.um.page_fault_service", "t_fault_UM", "s",
    "Page-fault servicing overhead excluding pure data transfer time.",
    scope="memory_subsystem",
)
um_page_migration_latency = var(
    "mem.um.page_migration_latency", "t_mig_UM", "s",
    "Unified-memory page migration latency over the host link.",
    scope="memory_subsystem",
)

eq_effective_page_bytes = eq(
    "mem.eq.tlb_effective_page_bytes",
    effective_page_bytes.symbol,
    (1 - huge_page_fraction.symbol) * page_bytes.symbol + huge_page_fraction.symbol * huge_page_bytes.symbol,
    "Average page size after mixing base and huge pages.",
)

eq_tlb_reach = eq(
    "mem.eq.tlb_reach",
    tlb_reach.symbol,
    tlb_entries.symbol * effective_page_bytes.symbol,
    "TLB reach equals entry count times effective page size.",
)

eq_tlb_latency_avg = eq(
    "mem.eq.tlb_latency_avg",
    avg_translation_latency.symbol,
    (1 - tlb_hit_rate.symbol) * tlb_miss_penalty.symbol,
    "Average translation latency from TLB misses only, with hits treated as the baseline path.",
)

eq_pcie_bw = eq(
    "mem.eq.pcie_bw",
    pcie_bw.symbol,
    pcie_lanes_per_gpu.symbol * pcie_lane_rate_raw.symbol * pcie_efficiency.symbol,
    "Effective PCIe bandwidth from lane count, lane rate, and protocol efficiency.",
)

eq_um_page_migration = eq(
    "mem.eq.um_page_migration_latency",
    um_page_migration_latency.symbol,
    um_page_bytes.symbol / pcie_bw.symbol + um_page_fault_service.symbol,
    "Unified-memory migration latency from data transfer time plus page-fault service overhead.",
)

eq_avg_global_load_latency = eq(
    "mem.eq.avg_global_load_latency",
    avg_global_load_latency.symbol,
    l1_hit_rate.symbol * l1_latency.symbol
    + (1 - l1_hit_rate.symbol)
      * (l2_hit_rate.symbol * l2_latency.symbol + (1 - l2_hit_rate.symbol) * hbm_latency.symbol)
    + avg_translation_latency.symbol,
    "Average global-memory latency from cache hit rates plus translation overhead.",
)


# ---------------------------------------------------------------------------
# Host-side NUMA effects
# ---------------------------------------------------------------------------

host_numa_local_bw = var(
    "mem.numa.local_bw", "BW_NUMA_local", "byte/s",
    "Host memory bandwidth from the local NUMA domain.",
    scope="memory_subsystem",
)
host_numa_remote_bw = var(
    "mem.numa.remote_bw", "BW_NUMA_remote", "byte/s",
    "Host memory bandwidth from a remote NUMA domain.",
    scope="memory_subsystem",
)
host_numa_local_latency = var(
    "mem.numa.local_latency", "t_NUMA_local", "s",
    "Host memory latency from the local NUMA domain.",
    scope="memory_subsystem",
)
host_numa_remote_latency = var(
    "mem.numa.remote_latency", "t_NUMA_remote", "s",
    "Host memory latency from a remote NUMA domain.",
    scope="memory_subsystem",
)
host_numa_bw_penalty = var(
    "mem.numa.bw_penalty", "k_NUMA_bw", "dimensionless",
    "Bandwidth penalty factor for remote NUMA access.",
    scope="memory_subsystem",
)
host_numa_latency_penalty = var(
    "mem.numa.latency_penalty", "k_NUMA_lat", "dimensionless",
    "Latency inflation factor for remote NUMA access.",
    scope="memory_subsystem",
)

eq_numa_bw_penalty = eq(
    "mem.eq.numa_bw_penalty",
    host_numa_bw_penalty.symbol,
    host_numa_local_bw.symbol / host_numa_remote_bw.symbol,
    "Remote-NUMA bandwidth penalty relative to local bandwidth.",
)

eq_numa_latency_penalty = eq(
    "mem.eq.numa_latency_penalty",
    host_numa_latency_penalty.symbol,
    host_numa_remote_latency.symbol / host_numa_local_latency.symbol,
    "Remote-NUMA latency penalty relative to local latency.",
)


# ---------------------------------------------------------------------------
# Energy per access
# ---------------------------------------------------------------------------

e_per_byte_reg = var(
    "mem.energy.per_byte_reg", "E_B_reg", "J/byte",
    "Energy per byte read from the register file.",
    scope="memory_subsystem",
)
e_per_byte_smem = var(
    "mem.energy.per_byte_smem", "E_B_smem", "J/byte",
    "Energy per byte read from SMEM.",
    scope="memory_subsystem",
)
e_per_byte_l2 = var(
    "mem.energy.per_byte_l2", "E_B_l2", "J/byte",
    "Energy per byte read from L2.",
    scope="memory_subsystem",
)
e_per_byte_hbm = var(
    "mem.energy.per_byte_hbm", "E_B_hbm", "J/byte",
    "Energy per byte read from HBM.",
    scope="memory_subsystem",
)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

for v in [
    mem_array_clock, warp_size, threads_per_sm_max,
    regs_per_thread, reg_width_bits, reg_file_bytes_per_sm, reg_file_regs_per_sm,
    warps_per_sm_reg_limit, reg_bank_count, reg_bank_width_bits, reg_ports_per_bank,
    reg_bw_peak, reg_bank_conflict_factor, reg_bw_effective,
    l1_smem_pool_bytes_per_sm, smem_bytes_per_sm, smem_bw_per_sm, smem_latency,
    l1_bytes_per_sm, l1_line_bytes, l1_assoc, l1_sets, l1_hit_rate, l1_latency,
    smem_bank_count, smem_bank_width_bytes, smem_ports_per_bank, smem_bw_peak,
    smem_conflict_factor,
    tmem_bytes_per_sm, tmem_bw_per_sm, tmem_mma_write_latency,
    tmem_bank_count, tmem_bank_width_bytes, tmem_ports_per_bank, tmem_bw_peak,
    l2_bytes, l2_bw, l2_line_bytes, l2_assoc, l2_partitions, l2_sets_per_partition,
    l2_hit_rate, l2_latency, l2_miss_penalty, avg_global_load_latency,
    hbm_stack_count, hbm_stack_capacity, hbm_capacity,
    hbm_pins_per_stack, hbm_pin_rate, hbm_bw_per_stack, hbm_bw, hbm_latency,
    hbm_refresh_overhead, hbm_bw_effective, hbm_ecc_overhead, hbm_capacity_usable,
    mem_compression_ratio, hbm_effective_capacity,
    tlb_entries, page_bytes, huge_page_bytes, huge_page_fraction,
    effective_page_bytes, tlb_reach, tlb_hit_rate, tlb_miss_penalty,
    avg_translation_latency,
    pcie_lanes_per_gpu, pcie_lane_rate_raw, pcie_efficiency, pcie_bw,
    cxl_bw, cxl_latency, um_page_bytes, um_page_fault_service,
    um_page_migration_latency,
    host_numa_local_bw, host_numa_remote_bw,
    host_numa_local_latency, host_numa_remote_latency,
    host_numa_bw_penalty, host_numa_latency_penalty,
    e_per_byte_reg, e_per_byte_smem, e_per_byte_l2, e_per_byte_hbm,
]:
    sys_mem.add(v)

for e in [
    eq_reg_file_regs, eq_reg_warp_limit, eq_reg_bw_peak, eq_reg_bw_effective,
    eq_l1_capacity, eq_l1_sets, eq_smem_bw_peak, eq_smem_bw_effective,
    eq_tmem_bw_peak, eq_tmem_bw,
    eq_l2_sets,
    eq_hbm_capacity, eq_hbm_bw_per_stack, eq_hbm_bw_total,
    eq_hbm_bw_effective, eq_hbm_capacity_usable, eq_hbm_capacity_effective,
    eq_l2_miss_penalty,
    eq_effective_page_bytes, eq_tlb_reach, eq_tlb_latency_avg,
    eq_pcie_bw, eq_um_page_migration, eq_avg_global_load_latency,
    eq_numa_bw_penalty, eq_numa_latency_penalty,
]:
    sys_mem.add(e)
