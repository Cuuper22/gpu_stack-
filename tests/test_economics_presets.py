"""Tests for the electricity-price presets and their provenance.

Each preset encodes one flat power tariff from EIA (the U.S. Energy
Information Administration) 2024 data — for example 0.0813 USD/kWh for U.S.
industrial customers. A price without a citation is just a guess, so the
tests check three things: every preset cites its EIA source with the exact
cents/kWh figure, every preset assigns exactly the three power-price roots
and nothing else, and the resolver turns each flat tariff into the blended
kWh price and the per-watt-second price (divide by 3,600,000).
"""

import pytest

from gpu_stack import Registry
import gpu_stack.presets.economics as economics


POWER_PRICE_ROOTS = {
    "econ.power.price_kwh_peak",
    "econ.power.price_kwh_offpeak",
    "econ.power.peak_energy_fraction",
}

EXPECTED_FLAT_PRICES = (
    (economics.us_2024_commercial_flat_power_tariff, 0.1275),
    (economics.us_2024_industrial_flat_power_tariff, 0.0813),
    (economics.california_2024_commercial_flat_power_tariff, 0.2554),
    (economics.california_2024_industrial_flat_power_tariff, 0.2153),
)


def test_eia_power_price_presets_record_public_provenance():
    us_commercial = economics.us_2024_commercial_flat_power_tariff
    us_industrial = economics.us_2024_industrial_flat_power_tariff
    ca_commercial = economics.california_2024_commercial_flat_power_tariff
    ca_industrial = economics.california_2024_industrial_flat_power_tariff

    assert "U.S. Energy Information Administration" in (us_commercial.source or "")
    assert "Electric Power Annual" in (us_commercial.source or "")
    assert "12.75 cents/kWh" in (us_commercial.source or "")
    assert "0.1275 USD/kWh" in (us_commercial.source or "")
    assert "8.13 cents/kWh" in (us_industrial.source or "")
    assert "0.0813 USD/kWh" in (us_industrial.source or "")
    assert "California" in (ca_commercial.source or "")
    assert "25.54 cents/kWh" in (ca_commercial.source or "")
    assert "0.2554 USD/kWh" in (ca_commercial.source or "")
    assert "21.53 cents/kWh" in (ca_industrial.source or "")
    assert "0.2153 USD/kWh" in (ca_industrial.source or "")
    assert all("eia.gov" in (preset.source or "") for preset, _ in EXPECTED_FLAT_PRICES)
    assert any("not utility rates" in note for note in us_commercial.notes)
    assert any("Not a live 2026 value" in note for note in us_commercial.notes)


def test_eia_power_price_presets_assign_only_existing_power_roots():
    for preset, usd_per_kwh in EXPECTED_FLAT_PRICES:
        assert set(preset.assignments) == POWER_PRICE_ROOTS
        assert preset.assignments["econ.power.price_kwh_peak"] == usd_per_kwh
        assert preset.assignments["econ.power.price_kwh_offpeak"] == usd_per_kwh
        assert preset.assignments["econ.power.peak_energy_fraction"] == 0.0

        for name in preset.assignments:
            assert name in Registry.variables
            assert Registry.variables[name].is_root_input, name
            assert name.startswith("econ.power.")

        assert "econ.power.price_kwh" not in preset.assignments
        assert "econ.power.price_ws" not in preset.assignments
        assert "econ.power.capacity_charge_kw_month" not in preset.assignments


@pytest.mark.parametrize(
    ("preset", "usd_per_kwh"),
    list(EXPECTED_FLAT_PRICES),
)
def test_flat_power_price_presets_resolve_blended_price_and_watt_second_price(
    preset,
    usd_per_kwh,
):
    blended = preset.resolve("econ.power.price_kwh")
    watt_second = preset.resolve("econ.power.price_ws")

    assert float(blended.value) == pytest.approx(usd_per_kwh)
    assert float(watt_second.value) == pytest.approx(usd_per_kwh / 3_600_000)
    assert blended.trace
    assert watt_second.trace
