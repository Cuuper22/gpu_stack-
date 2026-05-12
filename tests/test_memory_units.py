"""
tests/test_memory_units.py
==========================

Focused unit/provenance coverage for the memory-owned scope modules.
"""

from gpu_stack import Registry
from gpu_stack.core.units import BPS, JOULE, SECOND, VOLT
from gpu_stack.core.units import check_dimensional_consistency
from gpu_stack.scopes import (
    memory_cache,
    memory_dram,
    memory_hbm,
    memory_regfile,
    memory_smem,
    memory_sram,
)


BYTE = BPS * SECOND

OWNED_VARIABLE_GROUPS = (
    memory_regfile.MEMSUB_REGFILE_VARIABLES,
    memory_smem.MEMSUB_SMEM_VARIABLES,
    memory_cache.MEMSUB_CACHE_VARIABLES,
    memory_hbm.MEMSUB_HBM_VARIABLES,
    memory_sram.MEMCELL_SRAM_VARIABLES,
    memory_dram.MEMCELL_DRAM_VARIABLES,
)

OWNED_EQUATION_GROUPS = (
    memory_regfile.MEMSUB_REGFILE_EQUATIONS,
    memory_smem.MEMSUB_SMEM_EQUATIONS,
    memory_cache.MEMSUB_CACHE_EQUATIONS,
    memory_hbm.MEMSUB_HBM_EQUATIONS,
    memory_sram.MEMCELL_SRAM_EQUATIONS,
    memory_dram.MEMCELL_DRAM_EQUATIONS,
)


def _assert_units(var_name, expected_units):
    check_dimensional_consistency(
        expected_units,
        Registry.variables[var_name].sp_units,
        var_name,
    )


def test_owned_memory_variable_groups_have_sympy_units():
    missing = [
        variable.name
        for group in OWNED_VARIABLE_GROUPS
        for variable in group
        if variable.sp_units is None
    ]
    assert missing == []


def test_representative_memory_units_are_dimensionally_consistent():
    _assert_units("mem.reg.bw_peak", BPS)
    _assert_units("mem.smem.bank_width", BYTE)
    _assert_units("mem.l2.latency", SECOND)
    _assert_units("mem.hbm.capacity_effective", BYTE)
    _assert_units("mem.energy.per_byte_hbm", JOULE / BYTE)
    _assert_units("memcell.sram.snm_read", VOLT)
    _assert_units("memcell.dram.stored_charge", JOULE / VOLT)


def test_owned_memory_equations_have_provenance_refs():
    missing = [
        equation.name
        for group in OWNED_EQUATION_GROUPS
        for equation in group
        if not equation.references
    ]
    assert missing == []


def test_curated_memory_equations_have_unit_checks_enabled():
    checked = {
        equation.name
        for group in OWNED_EQUATION_GROUPS
        for equation in group
        if getattr(equation, "_check_units_flag", False)
    }

    assert {
        "mem.eq.reg_bw_peak",
        "mem.eq.smem_bw_peak",
        "mem.eq.l1_sets",
        "mem.eq.hbm_bw_total",
        "memcell.eq.sram_access_time",
        "memcell.eq.sram_read_energy",
        "memcell.eq.dram_charge",
        "memcell.eq.dram_sense_resolve",
        "memcell.eq.dram_refresh_guard_constraint",
    } <= checked
