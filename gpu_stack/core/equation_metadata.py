"""
Reference normalization for equation constructors.

Equation authors may pass citations as plain strings or as structured
Reference objects; this module turns both into a uniform Reference list.
"""

from __future__ import annotations

from typing import List, Optional, Union

from .variable import Reference


def normalize_references(
    refs: Optional[List[Union[str, Reference]]]
) -> List[Reference]:
    """Wrap bare strings as Reference objects, preserving input order."""
    if not refs:
        return []
    out: List[Reference] = []
    for ref in refs:
        if isinstance(ref, Reference):
            out.append(ref)
        else:
            out.append(Reference(citation=str(ref)))
    return out


__all__ = ["normalize_references"]
