"""
scopes/physical_lithography_transition_step.py
==============================================

Default shell step for the source transition. The emitting transition is
taken between adjacent principal shells: the upper quantum number is the
lower plus one. This one-line closure lives in its own bridge module only
to keep the main electronic-structure file under the audit size limit
while staying next to the layer it belongs to.
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
