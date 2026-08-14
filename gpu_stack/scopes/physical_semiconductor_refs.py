"""
scopes/physical_semiconductor_refs.py
=====================================

Shared Reference objects for the semiconductor transport modules,
declared once here and cited by the variable and equation declarations so
provenance stays in one place and the sibling modules need not import each
other.
"""

from ..core import Reference


_SZE_TRANSPORT = Reference(
    citation="Sze and Ng, Physics of Semiconductor Devices, carrier transport fundamentals",
    kind="textbook",
)
_SI_BASE_UNITS = Reference(
    citation="International System of Units, 9th edition, base and derived electrical units",
    kind="standard",
    year=2019,
)


__all__ = [
    "_SZE_TRANSPORT",
    "_SI_BASE_UNITS",
]
