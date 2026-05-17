"""
scopes/physical_mosfet_refs.py
================================

Shared references for MOSFET electrostatics and current models.
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
