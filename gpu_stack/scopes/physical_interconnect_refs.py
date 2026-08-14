"""
scopes/physical_interconnect_refs.py
====================================

Shared Reference objects for the interconnect modules. Every interconnect
variable and equation cites one of these provenance records, so the source
of a modeling choice is stated once here rather than repeated at each
declaration. A separate module lets the variable and equation files import
the references without importing each other.
"""

from ..core import Reference


_INTERCONNECT_TEXT = Reference(
    citation="Bakoglu, Circuits, Interconnections, and Packaging for VLSI",
    kind="textbook",
)
_INTERCONNECT_GEOMETRY_REF = Reference(
    citation="Interconnect-geometry abstraction: routing pitch and length from process geometry and placement span",
    kind="memo",
)


__all__ = [
    "_INTERCONNECT_TEXT",
    "_INTERCONNECT_GEOMETRY_REF",
]
