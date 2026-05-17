"""
Small provenance helpers for Preset objects.

The public API stays on ``Preset``; these functions keep source-text handling
consistent across summaries, scenario reports, and combined presets.
"""

from __future__ import annotations

from typing import Iterable, Mapping, Optional, Tuple


def has_source_text(source: Optional[str]) -> bool:
    """True when a source string carries non-blank provenance text."""
    return bool(source and source.strip())


def normalized_source(source: Optional[str]) -> Optional[str]:
    """Return stripped source text, or ``None`` for blank/missing provenance."""
    return source.strip() if has_source_text(source) else None


def preset_source_summary(
    *,
    name: str,
    source: Optional[str],
    assignments: Mapping[str, float],
    variants: Mapping[str, str],
    notes: Tuple[str, ...],
) -> dict[str, object]:
    """Return the compact provenance snapshot exposed by ``Preset``."""
    return {
        "name": name,
        "has_source": has_source_text(source),
        "source": normalized_source(source),
        "assignment_count": len(assignments),
        "variant_count": len(variants),
        "note_count": len(notes),
    }


def combined_source_for(presets: Iterable[object]) -> Optional[str]:
    """Render the later-audited source string for a combined preset."""
    sources: list[str] = []
    for preset in presets:
        source = getattr(preset, "source", None)
        if source:
            sources.append(f"{getattr(preset, 'name')}: {source}")
    return " | ".join(sources) if sources else None


__all__ = [
    "combined_source_for",
    "has_source_text",
    "normalized_source",
    "preset_source_summary",
]
