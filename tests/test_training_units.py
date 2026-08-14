"""Metadata coverage regressions for the training scope.

Every training variable must declare concrete SymPy units and cite
references, and every training equation must carry provenance. The counts
here (at least 61 variables, 49 equations, 31 unit-checked) are floors: they
stop coverage from silently shrinking when the graph changes. Representative
spot checks pin exact units — seconds for step time, FLOP for work per step,
watts for power — so a unit swap cannot hide inside an aggregate count.
"""

import sympy as sp

from gpu_stack import Registry
from gpu_stack.core.units import FLOP, FLOPS, JOULE, SECOND, WATT, byte


DIMENSIONLESS = sp.Integer(1)


def _training_variables():
    return [v for v in Registry.variables.values() if v.scope == "training"]


def _training_equations():
    return [
        e for e in Registry.equations.values()
        if e.name.startswith("training.")
    ]


def test_training_variables_have_units_and_references():
    training_vars = _training_variables()
    assert len(training_vars) >= 61
    assert [v.name for v in training_vars if v.sp_units is None] == []
    assert [v.name for v in training_vars if not v.references] == []


def test_training_representative_units_are_dimensional():
    assert Registry.variables["training.t_step"].sp_units == SECOND
    assert Registry.variables["training.flops_per_step"].sp_units == FLOP
    assert Registry.variables["training.peak_flops"].sp_units == FLOPS
    assert Registry.variables["training.dp.beta"].sp_units == SECOND / byte
    assert Registry.variables["training.mem.hbm_bytes_step"].sp_units == byte
    assert Registry.variables["training.run_power_it"].sp_units == WATT
    assert Registry.variables["training.energy_per_step"].sp_units == JOULE
    assert Registry.variables["training.tokens_per_sec"].sp_units == 1 / SECOND
    assert Registry.variables["training.chinchilla_gap"].sp_units == DIMENSIONLESS


def test_training_equations_have_references_and_curated_unit_checks():
    training_eqs = _training_equations()
    checked = {
        e.name for e in training_eqs
        if getattr(e, "_check_units_flag", False)
    }

    assert len(training_eqs) >= 49
    assert [e.name for e in training_eqs if not e.references] == []
    assert len(checked) >= 31
    assert {
        "training.eq.flops_executed_step",
        "training.eq.t_compute",
        "training.eq.t_comm_dp",
        "training.eq.t_exposed_comm",
        "training.eq.hbm_bytes_step",
        "training.eq.t_mem_bound",
        "training.eq.t_step",
        "training.eq.tokens_per_sec",
        "training.eq.energy_per_step",
        "training.eq.wallclock",
    } <= checked
