"""
scopes/physical_lithography_transition_step.py
==============================================

Adjacent-shell closure for lithography source transition steps.

This bridge keeps the principal-shell step default close to the electronic
structure layer without making the main scope file grow past the audit limit.
"""

import sympy as sp

from ..core import Approximation, Registry


_vars = Registry.variables

lithography_source_transition_principal_quantum_step = _vars[
    "physical.lithography.source_transition_principal_quantum_step"
]

LITHOGRAPHY_SOURCE_TRANSITION_STEP_REF = (
    lithography_source_transition_principal_quantum_step.references[0]
)


eq_lithography_source_transition_principal_quantum_step_from_adjacent_shells = Approximation(
    "physical.eq.lithography_source_transition_principal_quantum_step_from_adjacent_shells",
    lithography_source_transition_principal_quantum_step.symbol,
    sp.Integer(1),
    sp.S.true,
    "Adjacent-shell closure for the hydrogenic source-transition principal-shell step.",
    references=[LITHOGRAPHY_SOURCE_TRANSITION_STEP_REF],
    check_units=True,
)


LITHOGRAPHY_SOURCE_TRANSITION_STEP_EQUATIONS = [
    eq_lithography_source_transition_principal_quantum_step_from_adjacent_shells,
]


__all__ = [
    "eq_lithography_source_transition_principal_quantum_step_from_adjacent_shells",
    "LITHOGRAPHY_SOURCE_TRANSITION_STEP_EQUATIONS",
]
