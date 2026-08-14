"""Tests for the Krane SEMF calibration preset factory.

The SEMF (semi-empirical mass formula) treats a nucleus like a charged
liquid drop and predicts its binding energy from five fitted coefficients.
This factory encodes the coefficients from Krane, *Introductory Nuclear
Physics* (1988), Table 3.2 — quoted in MeV, stored in SI joules. The tests
check, in order:

1. Each of the five coefficients converts to joules exactly.
2. Sn-120 (the EUV tin source nucleus) resolves within 5 MeV of the
   AME2020 experimental binding energy of 1020.588 MeV — a tight bound,
   since the liquid drop works well for medium-heavy nuclei.
3. Fe-56 resolves within 15 MeV of the experimental 492.274 MeV — looser
   on purpose, because the SEMF has no magic-number shell corrections and
   over-binds near closed shells by about 5.5 MeV here.
4. The pairing term converts as Delta_pair_ref = aP / sqrt(A_ref), so it
   scales with the chosen reference mass number.
5. The preset cites Krane 1988 and assigns exactly the SEMF roots.
6. The factory rejects invalid reference mass numbers (zero, negative,
   NaN, infinity, strings, booleans).
"""

import math

import pytest

from gpu_stack import Registry, resolve
from gpu_stack.presets import nuclear


# ---------------------------------------------------------------------------
# Reference values
# ---------------------------------------------------------------------------

# Krane (1988) Table 3.2 SEMF coefficients in MeV
KRANE_A_VOL_MEV = 15.5
KRANE_A_SURF_MEV = 16.8
KRANE_A_COUL_MEV = 0.72
KRANE_A_ASYM_MEV = 23.0
KRANE_A_PAIR_MEV = 34.0

# Experimental total binding energies from AME (per-nucleon values)
# Sn-120: B/A = 8.5049 MeV/nucleon, source: AME2020 nuclear mass evaluation
SN120_EXP_BINDING_MEV = 8.5049 * 120   # = 1020.588 MeV
# Fe-56: B/A = 8.7906 MeV/nucleon, source: AME2020 nuclear mass evaluation
FE56_EXP_BINDING_MEV = 8.7906 * 56     # = 492.274 MeV

# Tolerances:
# Sn-120: Krane SEMF predicts 1020.080 MeV; the ~0.5 MeV error (<0.1%) is
#         within the SEMF liquid-drop accuracy for medium-heavy nuclei.
# Fe-56: Krane SEMF predicts 497.741 MeV; the ~5.5 MeV error (~1.1%) reflects
#        that the liquid-drop formula does not encode magic-number shell corrections.
#        A 2% tolerance accommodates the known SEMF systematic floor.
SN120_TOLERANCE_MEV = 5.0    # <0.5% for a medium-heavy nucleus
FE56_TOLERANCE_MEV = 15.0    # <3% to cover liquid-drop SEMF accuracy floor


def _krane_assignments(a_ref: int) -> dict[str, float]:
    """Build full SEMF + isotope assignments for use in resolver calls."""
    preset = nuclear.krane_semf_calibration_preset(reference_mass_number=a_ref)
    return dict(preset.assignments)


# ---------------------------------------------------------------------------
# Coefficient encoding tests
# ---------------------------------------------------------------------------

class TestKraneSemfCoefficientEncoding:
    """Verify that Krane's MeV table values are correctly encoded in SI joules."""

    def test_volume_coefficient_matches_krane(self):
        p = nuclear.krane_semf_calibration_preset(reference_mass_number=120)
        assert p.assignments[
            "physical.lithography.nuclear_binding_volume_coefficient"
        ] == pytest.approx(KRANE_A_VOL_MEV * nuclear.MEV_TO_JOULE, rel=1e-9)

    def test_surface_coefficient_matches_krane(self):
        p = nuclear.krane_semf_calibration_preset(reference_mass_number=120)
        assert p.assignments[
            "physical.lithography.nuclear_binding_surface_coefficient"
        ] == pytest.approx(KRANE_A_SURF_MEV * nuclear.MEV_TO_JOULE, rel=1e-9)

    def test_coulomb_coefficient_matches_krane(self):
        p = nuclear.krane_semf_calibration_preset(reference_mass_number=120)
        assert p.assignments[
            "physical.lithography.nuclear_binding_coulomb_coefficient"
        ] == pytest.approx(KRANE_A_COUL_MEV * nuclear.MEV_TO_JOULE, rel=1e-9)

    def test_asymmetry_coefficient_matches_krane(self):
        p = nuclear.krane_semf_calibration_preset(reference_mass_number=120)
        assert p.assignments[
            "physical.lithography.nuclear_binding_asymmetry_coefficient"
        ] == pytest.approx(KRANE_A_ASYM_MEV * nuclear.MEV_TO_JOULE, rel=1e-9)

    def test_pairing_reference_energy_for_sn120(self):
        # Delta_pair_ref = aP / sqrt(A_ref) for the self-calibrated model
        p = nuclear.krane_semf_calibration_preset(reference_mass_number=120)
        expected_j = (KRANE_A_PAIR_MEV / math.sqrt(120)) * nuclear.MEV_TO_JOULE
        assert p.assignments[
            "physical.lithography.nuclear_pairing_gap_reference_energy"
        ] == pytest.approx(expected_j, rel=1e-9)

    def test_pairing_reference_energy_scales_with_reference_mass_number(self):
        p56 = nuclear.krane_semf_calibration_preset(reference_mass_number=56)
        p120 = nuclear.krane_semf_calibration_preset(reference_mass_number=120)
        key = "physical.lithography.nuclear_pairing_gap_reference_energy"
        ratio = p56.assignments[key] / p120.assignments[key]
        assert ratio == pytest.approx(math.sqrt(120) / math.sqrt(56), rel=1e-9)


# ---------------------------------------------------------------------------
# Binding energy resolution tests
# ---------------------------------------------------------------------------

class TestKraneSemfBindingEnergyResolution:
    """
    Verify resolver computes physically reasonable binding energies with Krane
    SEMF coefficients.

    Tolerance justification:
    - SEMF is a liquid-drop formula: known RMS error ~3 MeV across stable nuclei.
    - For Sn-120 (semi-magic Z=50): deviation is small (~0.5 MeV).
    - For Fe-56 (doubly-magic-adjacent): liquid-drop gives ~5.5 MeV over-binding
      because magic-number shell corrections are not included in SEMF.
    """

    def _source_assignments(self, protons: int, neutrons: int) -> dict[str, object]:
        preset = nuclear.krane_semf_calibration_preset(
            reference_mass_number=protons + neutrons
        )
        return {
            **preset.assignments,
            "physical.lithography.source_proton_count": protons,
            "physical.lithography.source_neutron_count": neutrons,
        }

    def test_sn120_binding_energy_resolves_without_missing(self):
        assignments = self._source_assignments(protons=50, neutrons=70)
        result = resolve(
            "physical.lithography.source_nuclear_binding_energy",
            assignments=assignments,
        )
        assert result.missing == set()
        assert not result.violated_constraints

    def test_sn120_binding_energy_within_semf_tolerance(self):
        assignments = self._source_assignments(protons=50, neutrons=70)
        result = resolve(
            "physical.lithography.source_nuclear_binding_energy",
            assignments=assignments,
        )
        pred_mev = float(result.value) / nuclear.MEV_TO_JOULE
        assert abs(pred_mev - SN120_EXP_BINDING_MEV) < SN120_TOLERANCE_MEV, (
            f"Sn-120 SEMF prediction {pred_mev:.3f} MeV deviates more than "
            f"{SN120_TOLERANCE_MEV} MeV from experimental {SN120_EXP_BINDING_MEV:.3f} MeV"
        )

    def test_sn120_binding_energy_magnitude_is_physical(self):
        assignments = self._source_assignments(protons=50, neutrons=70)
        result = resolve(
            "physical.lithography.source_nuclear_binding_energy",
            assignments=assignments,
        )
        pred_mev = float(result.value) / nuclear.MEV_TO_JOULE
        # Sn-120 should be around 1020 MeV total binding energy
        assert 1000 < pred_mev < 1050, f"Sn-120 binding energy {pred_mev:.1f} MeV outside [1000, 1050] MeV"

    def test_fe56_binding_energy_resolves_without_missing(self):
        assignments = self._source_assignments(protons=26, neutrons=30)
        result = resolve(
            "physical.lithography.source_nuclear_binding_energy",
            assignments=assignments,
        )
        assert result.missing == set()
        assert not result.violated_constraints

    def test_fe56_binding_energy_within_semf_tolerance(self):
        assignments = self._source_assignments(protons=26, neutrons=30)
        result = resolve(
            "physical.lithography.source_nuclear_binding_energy",
            assignments=assignments,
        )
        pred_mev = float(result.value) / nuclear.MEV_TO_JOULE
        assert abs(pred_mev - FE56_EXP_BINDING_MEV) < FE56_TOLERANCE_MEV, (
            f"Fe-56 SEMF prediction {pred_mev:.3f} MeV deviates more than "
            f"{FE56_TOLERANCE_MEV} MeV from experimental {FE56_EXP_BINDING_MEV:.3f} MeV"
        )

    def test_fe56_binding_energy_magnitude_is_physical(self):
        assignments = self._source_assignments(protons=26, neutrons=30)
        result = resolve(
            "physical.lithography.source_nuclear_binding_energy",
            assignments=assignments,
        )
        pred_mev = float(result.value) / nuclear.MEV_TO_JOULE
        # Fe-56 should be around 490-510 MeV
        assert 480 < pred_mev < 510, f"Fe-56 binding energy {pred_mev:.1f} MeV outside [480, 510] MeV"


# ---------------------------------------------------------------------------
# Preset provenance tests
# ---------------------------------------------------------------------------

class TestKraneSemfPresetProvenance:
    """Verify preset carries required source citations."""

    def test_preset_has_source(self):
        p = nuclear.krane_semf_calibration_preset(reference_mass_number=120)
        assert p.require_source() is p

    def test_preset_source_cites_krane(self):
        p = nuclear.krane_semf_calibration_preset(reference_mass_number=120)
        assert "Krane" in p.source

    def test_preset_source_cites_1988(self):
        p = nuclear.krane_semf_calibration_preset(reference_mass_number=120)
        assert "1988" in p.source

    def test_preset_notes_document_pairing_semantics(self):
        p = nuclear.krane_semf_calibration_preset(reference_mass_number=120)
        notes_text = " ".join(p.notes)
        assert "A^(-1/2)" in notes_text or "A_ref" in notes_text

    def test_preset_assigns_all_semf_roots(self):
        p = nuclear.krane_semf_calibration_preset(reference_mass_number=120)
        assert set(p.assignments) == set(nuclear.SEMF_CALIBRATION_ROOTS)

    def test_all_assignments_are_positive_joule_values(self):
        p = nuclear.krane_semf_calibration_preset(reference_mass_number=120)
        for name, value in p.assignments.items():
            assert value > 0, f"{name} assignment is not positive"
            assert math.isfinite(value), f"{name} assignment is not finite"


# ---------------------------------------------------------------------------
# Factory error handling
# ---------------------------------------------------------------------------

class TestKraneSemfPresetFactoryErrors:
    """Verify the factory rejects invalid inputs."""

    @pytest.mark.parametrize("bad_a", [0, -1, float("nan"), float("inf"), "120", True])
    def test_factory_rejects_invalid_reference_mass_number(self, bad_a):
        with pytest.raises((ValueError, TypeError)):
            nuclear.krane_semf_calibration_preset(reference_mass_number=bad_a)


# ---------------------------------------------------------------------------
# Module-level export contract
# ---------------------------------------------------------------------------

def test_krane_semf_coefficients_table_is_exported():
    assert hasattr(nuclear, "KRANE_SEMF_COEFFICIENTS_MEV")
    coeffs = nuclear.KRANE_SEMF_COEFFICIENTS_MEV
    assert coeffs["a_vol_mev"] == pytest.approx(KRANE_A_VOL_MEV)
    assert coeffs["a_surf_mev"] == pytest.approx(KRANE_A_SURF_MEV)
    assert coeffs["a_coul_mev"] == pytest.approx(KRANE_A_COUL_MEV)
    assert coeffs["a_asym_mev"] == pytest.approx(KRANE_A_ASYM_MEV)
    assert coeffs["a_pairing_mev"] == pytest.approx(KRANE_A_PAIR_MEV)


def test_krane_factory_is_exported_in_nuclear_all():
    assert "krane_semf_calibration_preset" in nuclear.__all__


def test_nuclear_module_still_does_not_publish_preset_defaults():
    from gpu_stack.core import Preset as PresetClass
    exported_presets = [v for v in vars(nuclear).values() if isinstance(v, PresetClass)]
    assert exported_presets == []
