"""
scopes/memory_hbm.py
====================

HBM organization, usable bandwidth, and capacity after stacked-die
organization, channel geometry, refresh, ECC overhead, and memory compression.
"""

import sympy as sp

from ..core import Reference, eq, var
from ..core.units import BPS, JOULE, SECOND


# ---------------------------------------------------------------------------
# HBM and its usable bandwidth or capacity
# ---------------------------------------------------------------------------

DIMENSIONLESS = sp.Integer(1)
BYTE = BPS * SECOND

HBM_ORGANIZATION_REF = Reference(
    "JEDEC HBM DRAM standards and vendor HBM3/HBM3E stack datasheets describe "
    "stacked-die organization, channelized interfaces, and per-pin signaling.",
    kind="standard",
)
HBM_SERVICE_REF = Reference(
    "HBM timing, refresh, ECC, thermal throttling, controller scheduling, and "
    "interface power are specified or characterized in JEDEC HBM standards and "
    "vendor HBM stack/controller datasheets.",
    kind="standard",
)

hbm_stack_count = var(
    "mem.hbm.stacks", "N_HBM_stacks", "units",
    "Number of HBM stacks on the package.",
    scope="memory_subsystem",
    positive=True,
    integer=True,
    sp_units=DIMENSIONLESS,
    references=[HBM_ORGANIZATION_REF],
)
hbm_dies_per_stack = var(
    "mem.hbm.dies_per_stack", "N_die_HBM_stack", "dies",
    "Number of memory dies bonded into one HBM stack.",
    scope="memory_subsystem",
    positive=True,
    integer=True,
    sp_units=DIMENSIONLESS,
    references=[HBM_ORGANIZATION_REF],
)
hbm_die_capacity = var(
    "mem.hbm.die_capacity", "B_HBM_die", "byte",
    "Raw capacity of one HBM memory die.",
    scope="memory_subsystem",
    positive=True,
    sp_units=BYTE,
    references=[HBM_ORGANIZATION_REF],
)
hbm_spare_die_fraction = var(
    "mem.hbm.spare_die_fraction", "phi_spare_HBM", "dimensionless",
    "Fractional capacity withheld for spare rows, repair, binning, or stack-level redundancy.",
    scope="memory_subsystem",
    nonnegative=True,
    value_range=(0.0, 1.0),
    sp_units=DIMENSIONLESS,
    references=[HBM_ORGANIZATION_REF],
)
hbm_stack_capacity = var(
    "mem.hbm.stack_capacity", "B_HBM_stack", "byte",
    "Raw usable-addressable capacity per HBM stack before package-level ECC overhead.",
    scope="memory_subsystem",
    positive=True,
    sp_units=BYTE,
    references=[HBM_ORGANIZATION_REF],
)
hbm_capacity = var(
    "mem.hbm.capacity", "B_HBM", "byte",
    "Total raw HBM capacity per GPU package.",
    scope="memory_subsystem",
    positive=True,
    sp_units=BYTE,
    references=[HBM_ORGANIZATION_REF],
)
hbm_channels_per_stack = var(
    "mem.hbm.channels_per_stack", "N_chan_HBM_stack", "channels",
    "Number of independent HBM data channels exposed by one stack.",
    scope="memory_subsystem",
    positive=True,
    integer=True,
    sp_units=DIMENSIONLESS,
    references=[HBM_ORGANIZATION_REF],
)
hbm_pins_per_channel = var(
    "mem.hbm.pins_per_channel", "N_pins_HBM_chan", "pins/channel",
    "Data pins per HBM channel.",
    scope="memory_subsystem",
    positive=True,
    integer=True,
    sp_units=DIMENSIONLESS,
    references=[HBM_ORGANIZATION_REF],
)
hbm_pins_per_stack = var(
    "mem.hbm.pins_per_stack", "N_pins_HBM", "pins",
    "Data pins per HBM stack.",
    scope="memory_subsystem",
    positive=True,
    integer=True,
    sp_units=DIMENSIONLESS,
    references=[HBM_ORGANIZATION_REF],
)
hbm_pin_rate = var(
    "mem.hbm.pin_rate", "r_pin_HBM", "bit/s/pin",
    "Per-pin signaling rate.",
    scope="memory_subsystem",
    positive=True,
    sp_units=BPS,
    references=[HBM_ORGANIZATION_REF],
)
hbm_protocol_efficiency = var(
    "mem.hbm.protocol_efficiency", "eta_HBM_proto", "dimensionless",
    "Payload efficiency of the HBM interface after command, framing, turnaround, and protocol overhead.",
    scope="memory_subsystem",
    nonnegative=True,
    value_range=(0.0, 1.0),
    sp_units=DIMENSIONLESS,
    references=[HBM_ORGANIZATION_REF],
)
hbm_bw_per_channel = var(
    "mem.hbm.bw_per_channel", "BW_HBM_chan", "byte/s",
    "Payload bandwidth of one HBM channel before refresh and controller-level losses.",
    scope="memory_subsystem",
    positive=True,
    sp_units=BPS,
    references=[HBM_ORGANIZATION_REF],
)
hbm_bw_per_stack = var(
    "mem.hbm.bw_per_stack", "BW_HBM_stack", "byte/s",
    "Payload bandwidth of one HBM stack before refresh and controller-level losses.",
    scope="memory_subsystem",
    positive=True,
    sp_units=BPS,
    references=[HBM_ORGANIZATION_REF],
)
hbm_bw = var(
    "mem.hbm.bw", "BW_HBM", "byte/s",
    "Total raw HBM bandwidth per GPU package.",
    scope="memory_subsystem",
    positive=True,
    sp_units=BPS,
    references=[HBM_ORGANIZATION_REF],
)
hbm_latency = var(
    "mem.hbm.latency", "t_HBM", "s",
    "Average HBM read latency.",
    scope="memory_subsystem",
    positive=True,
    sp_units=SECOND,
    references=[HBM_SERVICE_REF],
)
hbm_refresh_overhead = var(
    "mem.hbm.refresh_overhead", "phi_refresh_HBM", "dimensionless",
    "Fraction of raw HBM bandwidth lost to refresh activity.",
    scope="memory_subsystem",
    nonnegative=True,
    value_range=(0.0, 1.0),
    sp_units=DIMENSIONLESS,
    references=[HBM_SERVICE_REF],
)
hbm_bank_conflict_overhead = var(
    "mem.hbm.bank_conflict_overhead", "phi_bank_HBM", "dimensionless",
    "Supply-side fraction of HBM service time lost to bank, row, or pseudo-channel conflicts.",
    scope="memory_subsystem",
    nonnegative=True,
    value_range=(0.0, 1.0),
    sp_units=DIMENSIONLESS,
    references=[HBM_SERVICE_REF],
)
hbm_controller_efficiency = var(
    "mem.hbm.controller_efficiency", "eta_HBM_ctrl", "dimensionless",
    "Memory-controller scheduling efficiency after arbitration and queueing overhead.",
    scope="memory_subsystem",
    nonnegative=True,
    value_range=(0.0, 1.0),
    sp_units=DIMENSIONLESS,
    references=[HBM_SERVICE_REF],
)
hbm_thermal_derate = var(
    "mem.hbm.thermal_derate", "eta_HBM_thermal", "dimensionless",
    "Thermal throttling multiplier applied to the HBM service rate.",
    scope="memory_subsystem",
    nonnegative=True,
    value_range=(0.0, 1.0),
    sp_units=DIMENSIONLESS,
    references=[HBM_SERVICE_REF],
)
hbm_bw_effective = var(
    "mem.hbm.bw_effective", "BW_HBM_eff", "byte/s",
    "Usable supply-side HBM bandwidth after refresh, bank, controller, and thermal losses.",
    scope="memory_subsystem",
    positive=True,
    sp_units=BPS,
    references=[HBM_SERVICE_REF],
)
hbm_ecc_overhead = var(
    "mem.hbm.ecc_overhead", "phi_ecc_HBM", "dimensionless",
    "Fraction of raw HBM capacity consumed by ECC or metadata overhead.",
    scope="memory_subsystem",
    nonnegative=True,
    value_range=(0.0, 1.0),
    sp_units=DIMENSIONLESS,
    references=[HBM_SERVICE_REF],
)
hbm_capacity_usable = var(
    "mem.hbm.capacity_usable", "B_HBM_use", "byte",
    "Usable HBM capacity after ECC or metadata overhead.",
    scope="memory_subsystem",
    positive=True,
    sp_units=BYTE,
    references=[HBM_SERVICE_REF],
)
mem_compression_ratio = var(
    "mem.hbm.compression_ratio", "rho_comp_mem", "dimensionless",
    "Effective compression ratio seen by memory traffic or footprint.",
    scope="memory_subsystem",
    positive=True,
    sp_units=DIMENSIONLESS,
    references=[HBM_SERVICE_REF],
)
hbm_effective_capacity = var(
    "mem.hbm.capacity_effective", "B_HBM_eff_cap", "byte",
    "Effective HBM capacity after usable-capacity adjustment and compression.",
    scope="memory_subsystem",
    positive=True,
    sp_units=BYTE,
    references=[HBM_SERVICE_REF],
)
e_per_byte_hbm = var(
    "mem.energy.per_byte_hbm", "E_B_hbm", "J/byte",
    "Energy per byte read from HBM.",
    scope="memory_subsystem",
    sp_units=JOULE / BYTE,
    references=[HBM_SERVICE_REF],
)

eq_hbm_stack_capacity = eq(
    "mem.eq.hbm_stack_capacity",
    hbm_stack_capacity.symbol,
    hbm_dies_per_stack.symbol
    * hbm_die_capacity.symbol
    * (1 - hbm_spare_die_fraction.symbol),
    "Per-stack HBM capacity comes from die count, per-die capacity, and stack-level redundancy.",
    references=[HBM_ORGANIZATION_REF],
    check_units=True,
)

eq_hbm_capacity = eq(
    "mem.eq.hbm_capacity",
    hbm_capacity.symbol,
    hbm_stack_count.symbol * hbm_stack_capacity.symbol,
    "HBM capacity equals stack count times per-stack capacity.",
    references=[HBM_ORGANIZATION_REF],
    check_units=True,
)

eq_hbm_pins_per_stack = eq(
    "mem.eq.hbm_pins_per_stack",
    hbm_pins_per_stack.symbol,
    hbm_channels_per_stack.symbol * hbm_pins_per_channel.symbol,
    "HBM data pins per stack equal channel count times data pins per channel.",
    references=[HBM_ORGANIZATION_REF],
    check_units=True,
)

eq_hbm_bw_per_channel = eq(
    "mem.eq.hbm_bw_per_channel",
    hbm_bw_per_channel.symbol,
    hbm_pins_per_channel.symbol
    * hbm_pin_rate.symbol
    * hbm_protocol_efficiency.symbol
    / 8,
    "Per-channel HBM payload bandwidth converts per-pin bit rate into bytes per second after protocol overhead.",
    references=[HBM_ORGANIZATION_REF],
    check_units=True,
)

eq_hbm_bw_per_stack = eq(
    "mem.eq.hbm_bw_per_stack",
    hbm_bw_per_stack.symbol,
    hbm_channels_per_stack.symbol * hbm_bw_per_channel.symbol,
    "Per-stack HBM payload bandwidth aggregates channel bandwidth.",
    references=[HBM_ORGANIZATION_REF],
    check_units=True,
)

eq_hbm_bw_total = eq(
    "mem.eq.hbm_bw_total",
    hbm_bw.symbol,
    hbm_stack_count.symbol * hbm_bw_per_stack.symbol,
    "Total HBM bandwidth across all stacks.",
    references=[HBM_ORGANIZATION_REF],
    check_units=True,
)

eq_hbm_bw_effective = eq(
    "mem.eq.hbm_bw_effective",
    hbm_bw_effective.symbol,
    hbm_bw.symbol
    * (1 - hbm_refresh_overhead.symbol)
    * (1 - hbm_bank_conflict_overhead.symbol)
    * hbm_controller_efficiency.symbol
    * hbm_thermal_derate.symbol,
    "Effective HBM bandwidth after refresh, conflict, controller, and thermal service-rate losses.",
    references=[HBM_SERVICE_REF],
    check_units=True,
)

eq_hbm_capacity_usable = eq(
    "mem.eq.hbm_capacity_usable",
    hbm_capacity_usable.symbol,
    hbm_capacity.symbol * (1 - hbm_ecc_overhead.symbol),
    "Usable HBM capacity after ECC or metadata overhead.",
    references=[HBM_SERVICE_REF],
    check_units=True,
)

eq_hbm_capacity_effective = eq(
    "mem.eq.hbm_capacity_effective",
    hbm_effective_capacity.symbol,
    hbm_capacity_usable.symbol * mem_compression_ratio.symbol,
    "Effective HBM capacity after compression.",
    references=[HBM_SERVICE_REF],
    check_units=True,
)


MEMSUB_HBM_VARIABLES = (
    hbm_stack_count,
    hbm_dies_per_stack,
    hbm_die_capacity,
    hbm_spare_die_fraction,
    hbm_stack_capacity,
    hbm_capacity,
    hbm_channels_per_stack,
    hbm_pins_per_channel,
    hbm_pins_per_stack,
    hbm_pin_rate,
    hbm_protocol_efficiency,
    hbm_bw_per_channel,
    hbm_bw_per_stack,
    hbm_bw,
    hbm_latency,
    hbm_refresh_overhead,
    hbm_bank_conflict_overhead,
    hbm_controller_efficiency,
    hbm_thermal_derate,
    hbm_bw_effective,
    hbm_ecc_overhead,
    hbm_capacity_usable,
    mem_compression_ratio,
    hbm_effective_capacity,
    e_per_byte_hbm,
)

MEMSUB_HBM_EQUATIONS = (
    eq_hbm_stack_capacity,
    eq_hbm_capacity,
    eq_hbm_pins_per_stack,
    eq_hbm_bw_per_channel,
    eq_hbm_bw_per_stack,
    eq_hbm_bw_total,
    eq_hbm_bw_effective,
    eq_hbm_capacity_usable,
    eq_hbm_capacity_effective,
)


__all__ = [
    "hbm_stack_count",
    "hbm_dies_per_stack",
    "hbm_die_capacity",
    "hbm_spare_die_fraction",
    "hbm_stack_capacity",
    "hbm_capacity",
    "hbm_channels_per_stack",
    "hbm_pins_per_channel",
    "hbm_pins_per_stack",
    "hbm_pin_rate",
    "hbm_protocol_efficiency",
    "hbm_bw_per_channel",
    "hbm_bw_per_stack",
    "hbm_bw",
    "hbm_latency",
    "hbm_refresh_overhead",
    "hbm_bank_conflict_overhead",
    "hbm_controller_efficiency",
    "hbm_thermal_derate",
    "hbm_bw_effective",
    "hbm_ecc_overhead",
    "hbm_capacity_usable",
    "mem_compression_ratio",
    "hbm_effective_capacity",
    "e_per_byte_hbm",
    "eq_hbm_stack_capacity",
    "eq_hbm_capacity",
    "eq_hbm_pins_per_stack",
    "eq_hbm_bw_per_channel",
    "eq_hbm_bw_per_stack",
    "eq_hbm_bw_total",
    "eq_hbm_bw_effective",
    "eq_hbm_capacity_usable",
    "eq_hbm_capacity_effective",
    "MEMSUB_HBM_VARIABLES",
    "MEMSUB_HBM_EQUATIONS",
]
