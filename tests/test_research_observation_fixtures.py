"""Tests for the E001 literature observation fixtures.

The E001 experiment seeds its learning prior with three validation-loss
numbers transcribed from a published paper (arXiv:2606.30634, SmolLM-360M
with Muon under sync, async-one-step, and async-with-error-feedback). The
paper reports values to three decimals, so the honest uncertainty is the
rounding half-width: each fixture must carry bounds of +/-0.0005 around the
printed value, with no invented standard deviation or confidence level.

The observations live in two places — the research tree and the installed
package data — because tools read whichever is available. The second test
requires the two copies to match byte for byte, so they can never drift.
"""

from importlib import resources
from pathlib import Path

import pytest

from gpu_stack.research.observations import Observation


OBSERVATION_DIR = (
    Path(__file__).resolve().parents[1]
    / "observations"
    / "literature"
    / "e001-one-step-delay"
)
BUNDLED_OBSERVATION_DIR = resources.files("gpu_stack").joinpath(
    "data",
    "observations",
    "literature",
    "e001-one-step-delay",
)


def test_e001_paper_observations_are_parseable_and_keep_rounding_uncertainty():
    observations = tuple(
        Observation.from_json(path.read_text(encoding="utf-8"))
        for path in sorted(OBSERVATION_DIR.glob("*.json"))
    )

    assert len(observations) == 3
    assert len({observation.observation_id for observation in observations}) == 3
    by_id = {observation.observation_id: observation for observation in observations}
    expected = {
        "arxiv:2606.30634:smollm-360m:muon:sync": 2.578,
        "arxiv:2606.30634:smollm-360m:muon:async-one-step": 2.590,
        "arxiv:2606.30634:smollm-360m:muon:async-one-step-error-feedback": 2.583,
    }
    for observation_id, value in expected.items():
        measurement = by_id[observation_id].measured_values["validation_loss"]
        assert measurement.value == value
        assert measurement.uncertainty.standard_deviation is None
        assert measurement.uncertainty.confidence_level is None
        assert measurement.uncertainty.lower_bound == pytest.approx(value - 0.0005)
        assert measurement.uncertainty.upper_bound == pytest.approx(value + 0.0005)


def test_bundled_e001_observations_match_research_copies_byte_for_byte():
    research_copies = {
        path.name: path.read_bytes()
        for path in sorted(OBSERVATION_DIR.glob("*.json"))
    }
    bundled_copies = {
        resource.name: resource.read_bytes()
        for resource in sorted(
            (
                entry
                for entry in BUNDLED_OBSERVATION_DIR.iterdir()
                if entry.is_file() and entry.name.endswith(".json")
            ),
            key=lambda entry: entry.name,
        )
    }

    assert bundled_copies == research_copies
    assert {
        name: Observation.from_json(payload.decode("utf-8"))
        for name, payload in bundled_copies.items()
    } == {
        name: Observation.from_json(payload.decode("utf-8"))
        for name, payload in research_copies.items()
    }
