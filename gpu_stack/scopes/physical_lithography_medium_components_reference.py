"""
scopes/physical_lithography_medium_components_reference.py
==========================================================

Shared provenance reference for lithography imaging-medium components.
"""

from ..core import Reference


LITHOGRAPHY_MEDIUM_COMPOSITION_REF = Reference(
    citation=(
        "Lithography imaging-medium composition: representative binary "
        "formula unit from stoichiometric component counts and isotope content"
    ),
    kind="memo",
)


__all__ = ["LITHOGRAPHY_MEDIUM_COMPOSITION_REF"]
