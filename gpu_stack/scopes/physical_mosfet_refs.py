"""
scopes/physical_mosfet_refs.py
==============================

Shared Reference objects for the MOSFET modules. Each provenance record is
declared once here and cited by the variable and equation declarations, so
the modeling sources stay in one place and the sibling modules can import
them without importing each other.
"""

from ..core import Reference


_MOS_TEXT = Reference(
    citation="Sze and Ng, Physics of Semiconductor Devices, MOS electrostatics and current models",
    kind="textbook",
)
_DEVICE_GEOMETRY_REF = Reference(
    citation="Device-geometry abstraction: effective MOSFET width and oxide thickness from replicated channels and EOT",
    kind="memo",
)


__all__ = [
    "_MOS_TEXT",
    "_DEVICE_GEOMETRY_REF",
]
