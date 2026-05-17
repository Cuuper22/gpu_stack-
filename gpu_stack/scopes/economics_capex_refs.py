"""
Shared units and references for economics capex helpers.
"""

import sympy as sp

from ..core import Reference


DIMENSIONLESS = sp.Integer(1)
USD = sp.Symbol("USD_unit", positive=True)

CAPEX_BOM_REF = Reference(
    "Cluster capex is decomposed as node, rack, cluster-network, storage, "
    "facility, residual-value, and straight-line depreciation terms.",
    kind="model",
)

FACILITY_CAPEX_REF = Reference(
    "Facility capex is modeled from capex-facing sizing drivers: floor area, "
    "electrical design capacity, and thermal design capacity multiplied by "
    "their unit costs.",
    kind="model",
)


__all__ = [
    "CAPEX_BOM_REF",
    "DIMENSIONLESS",
    "FACILITY_CAPEX_REF",
    "USD",
]
