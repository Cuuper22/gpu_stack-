"""Tests for the E001 literature observation fixtures.

The E001 experiment seeds its learning prior with three validation-loss
numbers transcribed from a published paper (arXiv:2606.30634, SmolLM-360M
with Muon under sync, async-one-step, and async-with-error-feedback). The
paper reports values to three decimals, so the honest uncertainty is the
rounding half-width: each fixture must carry bounds of +/-0.0005 around the
printed value, with no invented standard deviation or confidence level.

The single copy of the data lives in the package data directory
(gpu_stack/data/observations), so it is also available from an installed wheel.
"""

from importlib import resources

import pytest

from gpu_stack.research.observations import Observation


OBSERVATION_DIR = resources.files("gpu_stack").joinpath(
    "data",
    "observations",
    "literature",
    "e001-one-step-delay",
)


def _observation_files():
    return sorted(
        (
            entry
            for entry in OBSERVATION_DIR.iterdir()
            if entry.is_file() and entry.name.endswith(".json")
        ),
        key=lambda entry: entry.name,
    )


def test_e001_paper_observations_are_parseable_and_keep_rounding_uncertainty():
    observations = tuple(
        Observation.from_json(entry.read_text(encoding="utf-8"))
        for entry in _observation_files()
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


def test_observation_json_is_declared_as_package_data():
    # setuptools only ships files matched by [tool.setuptools.package-data].
    # Keep the declared glob in step with the directory the tests read.
    from pathlib import Path

    tomllib = pytest.importorskip("tomllib")  # stdlib from Python 3.11
    pyproject = tomllib.loads(
        (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(
            encoding="utf-8"
        )
    )
    patterns = pyproject["tool"]["setuptools"]["package-data"]["gpu_stack"]
    assert "data/observations/literature/e001-one-step-delay/*.json" in patterns
