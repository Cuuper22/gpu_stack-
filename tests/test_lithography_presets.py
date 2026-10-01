"""
tests/test_lithography_presets.py
=================================

The exposure presets assign only the three optics roots (wavelength,
numerical aperture, medium index), cite a source, and, combined with a k1
value, give the printed critical dimension from CD = k1 * wavelength / NA.
"""

import pytest

from gpu_stack import Registry
from gpu_stack.presets import lithography


OPTICS_ROOTS = {
    "physical.lithography.wavelength",
    "physical.lithography.numerical_aperture",
    "physical.lithography.medium_refractive_index",
}


@pytest.mark.parametrize("preset", lithography.EXPOSURE_PRESETS)
def test_exposure_presets_assign_only_optics_roots(preset):
    assert set(preset.assignments) == OPTICS_ROOTS
    for name in preset.assignments:
        assert Registry.variables[name].is_root_input, name
    assert preset.has_source()
    assert "ASML" in (preset.source or "")


def test_euv_wavelength_is_13_5_nm_and_arf_is_193_nm():
    assert lithography.euv_exposure.assignments[
        "physical.lithography.wavelength"
    ] == pytest.approx(13.5e-9)
    assert lithography.arf_immersion_exposure.assignments[
        "physical.lithography.wavelength"
    ] == pytest.approx(193e-9)


@pytest.mark.parametrize("preset", lithography.EXPOSURE_PRESETS)
def test_numerical_aperture_does_not_exceed_medium_index(preset):
    na = preset.assignments["physical.lithography.numerical_aperture"]
    index = preset.assignments["physical.lithography.medium_refractive_index"]
    assert 0 < na <= index


@pytest.mark.parametrize(
    ("preset", "k1", "expected_cd"),
    [
        (lithography.euv_exposure, 0.4, 0.4 * 13.5e-9 / 0.33),
        (lithography.arf_immersion_exposure, 0.3, 0.3 * 193e-9 / 1.35),
    ],
)
def test_gate_critical_dimension_follows_rayleigh(preset, k1, expected_cd):
    result = preset.with_overrides(
        name=f"{preset.name}_with_k1",
        assignments={"physical.lithography.gate_k1": k1},
    ).resolve("physical.lithography.gate_resolution")

    assert float(result.value) == pytest.approx(expected_cd)
    assert result.missing == set()
