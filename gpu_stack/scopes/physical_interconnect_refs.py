"""
scopes/physical_interconnect_refs.py
====================================

Shared references for physical interconnect declarations.
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
