"""
scopes/physical_lithography_medium_components_reference.py
==========================================================

The single provenance Reference shared by every imaging-medium component
declaration. Stating the modeling source once here keeps the component
variable and equation modules free of repeated citations and lets them
import it without importing each other.
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
