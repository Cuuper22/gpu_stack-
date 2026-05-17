"""
scopes/physical_semiconductor_refs.py
=====================================

Shared references for semiconductor transport helper modules.
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
