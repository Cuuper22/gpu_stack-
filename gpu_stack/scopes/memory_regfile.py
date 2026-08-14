"""
scopes/memory_regfile.py
========================

The register file: the fastest memory on the chip, and its two limits.

Registers are where operands live in the instant they are computed on, and
each SM holds a large shared register file that all resident threads carve
up. That creates the first limit: registers per thread times threads must
fit in the file, so register-hungry kernels cap how many warps can be
resident — a direct input to the occupancy model.

The second limit is bandwidth. The file is built from banks, each with a
width and port count, and peak bandwidth is banks times width times ports
times the array clock. When two operands in one cycle map to the same
bank, access serializes; a bank-conflict factor derates peak to effective
bandwidth. This module also defines the common memory-array clock and the
warp-size and thread-limit constants that the other on-SM storage helpers
share, which is why it is the foundation helper.
"""

import sympy as sp

from ..core import Reference, eq, var
from ..core.units import BPS, JOULE, SECOND, bit


# ---------------------------------------------------------------------------
# Common memory-array clocking
# ---------------------------------------------------------------------------

DIMENSIONLESS = sp.Integer(1)
BYTE = BPS * SECOND

REGISTER_FILE_REF = Reference(
    "GPU ISA and architecture documentation describes SIMT warp width, "
    "per-SM register files, banked register access, and register-file "
    "occupancy limits.",
    kind="datasheet",
)

mem_array_clock = var(
    "mem.array.clock", "f_mem", "Hz",
    "Representative cycle rate for on-chip memory arrays and bank service.",
    scope="memory_subsystem",
    sp_units=1 / SECOND,
    references=[REGISTER_FILE_REF],
)
warp_size = var(
    "mem.warp.size", "N_warp", "threads",
    "Threads per warp.",
    scope="memory_subsystem",
    sp_units=DIMENSIONLESS,
    references=[REGISTER_FILE_REF],
)
threads_per_sm_max = var(
    "mem.sm.threads_max", "N_thr_SM_max", "threads",
    "Maximum resident threads per SM.",
    scope="memory_subsystem",
    sp_units=DIMENSIONLESS,
    references=[REGISTER_FILE_REF],
)


# ---------------------------------------------------------------------------
# Per-thread register file
# ---------------------------------------------------------------------------

regs_per_thread = var(
    "mem.reg.per_thread", "N_reg_thr", "regs",
    "Registers allocated per GPU thread.",
    scope="memory_subsystem",
    sp_units=DIMENSIONLESS,
    references=[REGISTER_FILE_REF],
)
reg_width_bits = var(
    "mem.reg.width", "W_reg", "bit",
    "Width of a single architectural register.",
    scope="memory_subsystem",
    sp_units=bit,
    references=[REGISTER_FILE_REF],
)
reg_file_bytes_per_sm = var(
    "mem.reg.file_bytes_per_sm", "B_reg_sm", "byte",
    "Total register file size per SM.",
    scope="memory_subsystem",
    sp_units=BYTE,
    references=[REGISTER_FILE_REF],
)
reg_file_regs_per_sm = var(
    "mem.reg.file_regs_per_sm", "N_reg_sm", "regs",
    "Total physical registers per SM.",
    scope="memory_subsystem",
    sp_units=DIMENSIONLESS,
    references=[REGISTER_FILE_REF],
)
warps_per_sm_reg_limit = var(
    "mem.reg.warps_limit", "N_warp_reg_lim", "warps",
    "Register-file occupancy ceiling in resident warps per SM.",
    scope="memory_subsystem",
    sp_units=DIMENSIONLESS,
    references=[REGISTER_FILE_REF],
)
reg_bank_count = var(
    "mem.reg.bank_count", "N_bank_reg", "banks",
    "Number of physical register banks.",
    scope="memory_subsystem",
    sp_units=DIMENSIONLESS,
    references=[REGISTER_FILE_REF],
)
reg_bank_width_bits = var(
    "mem.reg.bank_width", "W_bank_reg", "bit",
    "Bytes or bits serviced per bank access.",
    scope="memory_subsystem",
    sp_units=bit,
    references=[REGISTER_FILE_REF],
)
reg_ports_per_bank = var(
    "mem.reg.ports_per_bank", "N_port_reg", "ports",
    "Effective read or write service ports per bank.",
    scope="memory_subsystem",
    sp_units=DIMENSIONLESS,
    references=[REGISTER_FILE_REF],
)
reg_bw_peak = var(
    "mem.reg.bw_peak", "BW_reg_peak", "byte/s",
    "Peak register-file bandwidth per SM before bank conflicts.",
    scope="memory_subsystem",
    sp_units=BPS,
    references=[REGISTER_FILE_REF],
)
reg_bank_conflict_factor = var(
    "mem.reg.bank_conflict_factor", "k_reg_conf", "dimensionless",
    "Bandwidth loss factor from register-bank conflicts.",
    scope="memory_subsystem",
    sp_units=DIMENSIONLESS,
    references=[REGISTER_FILE_REF],
)
reg_bw_effective = var(
    "mem.reg.bw_effective", "BW_reg_eff", "byte/s",
    "Effective register-file bandwidth after bank conflicts.",
    scope="memory_subsystem",
    sp_units=BPS,
    references=[REGISTER_FILE_REF],
)
e_per_byte_reg = var(
    "mem.energy.per_byte_reg", "E_B_reg", "J/byte",
    "Energy per byte read from the register file.",
    scope="memory_subsystem",
    sp_units=JOULE / BYTE,
    references=[REGISTER_FILE_REF],
)

eq_reg_file_regs = eq(
    "mem.eq.reg_file_regs_per_sm",
    reg_file_regs_per_sm.symbol,
    reg_file_bytes_per_sm.symbol * 8 / reg_width_bits.symbol,
    "Physical register count from bytes times 8 divided by bits per register.",
    references=[REGISTER_FILE_REF],
    check_units=True,
)

eq_reg_warp_limit = eq(
    "mem.eq.reg_warps_limit",
    warps_per_sm_reg_limit.symbol,
    reg_file_regs_per_sm.symbol / (regs_per_thread.symbol * warp_size.symbol),
    "Register-limited warp occupancy.",
    references=[REGISTER_FILE_REF],
    check_units=True,
)

eq_reg_bw_peak = eq(
    "mem.eq.reg_bw_peak",
    reg_bw_peak.symbol,
    reg_bank_count.symbol * reg_ports_per_bank.symbol * reg_bank_width_bits.symbol * mem_array_clock.symbol / 8,
    "Peak register bandwidth from banks, service width, ports, and cycle rate.",
    references=[REGISTER_FILE_REF],
    check_units=True,
)

eq_reg_bw_effective = eq(
    "mem.eq.reg_bw_effective",
    reg_bw_effective.symbol,
    reg_bw_peak.symbol / reg_bank_conflict_factor.symbol,
    "Effective register bandwidth after bank-conflict inflation.",
    references=[REGISTER_FILE_REF],
    check_units=True,
)


MEMSUB_REGFILE_VARIABLES = (
    mem_array_clock,
    warp_size,
    threads_per_sm_max,
    regs_per_thread,
    reg_width_bits,
    reg_file_bytes_per_sm,
    reg_file_regs_per_sm,
    warps_per_sm_reg_limit,
    reg_bank_count,
    reg_bank_width_bits,
    reg_ports_per_bank,
    reg_bw_peak,
    reg_bank_conflict_factor,
    reg_bw_effective,
    e_per_byte_reg,
)

MEMSUB_REGFILE_EQUATIONS = (
    eq_reg_file_regs,
    eq_reg_warp_limit,
    eq_reg_bw_peak,
    eq_reg_bw_effective,
)


__all__ = [
    "mem_array_clock",
    "warp_size",
    "threads_per_sm_max",
    "regs_per_thread",
    "reg_width_bits",
    "reg_file_bytes_per_sm",
    "reg_file_regs_per_sm",
    "warps_per_sm_reg_limit",
    "reg_bank_count",
    "reg_bank_width_bits",
    "reg_ports_per_bank",
    "reg_bw_peak",
    "reg_bank_conflict_factor",
    "reg_bw_effective",
    "e_per_byte_reg",
    "eq_reg_file_regs",
    "eq_reg_warp_limit",
    "eq_reg_bw_peak",
    "eq_reg_bw_effective",
    "MEMSUB_REGFILE_VARIABLES",
    "MEMSUB_REGFILE_EQUATIONS",
]
