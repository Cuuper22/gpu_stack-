"""
gpu_stack.presets.economics
===========================

Historical economics presets for power-price roots.

These presets intentionally use annual-average EIA retail electricity prices
as flat tariffs. They are not live procurement quotes, utility rate schedules,
or time-of-use tariffs. Demand-charge roots are left unassigned so callers do
not accidentally double count charges already blended into average retail
prices.
"""

from __future__ import annotations

from ..core.presets import Preset
from ..core.registry import Registry


_EIA_US_2024_AVERAGE_PRICE_SOURCE = (
    "U.S. Energy Information Administration (EIA), Electric Power Annual, "
    "Table 2.4, 'Average Price of Electricity to Ultimate Customers by "
    "End-Use Sectors 2014 through 2024 (Cents per kilowatthour)', "
    "Total Electric Industry 2024 row: Commercial 12.75 cents/kWh and "
    "Industrial 8.13 cents/kWh. URL: "
    "https://www.eia.gov/electricity/annual/table.php?t=epa_02_04"
)

_EIA_CA_2024_AVERAGE_PRICE_SOURCE = (
    "U.S. Energy Information Administration (EIA), Electric Power Annual "
    "state electricity profile map, with data for 2024, California row: "
    "Commercial 25.54 cents/kWh and Industrial 21.53 cents/kWh. URL: "
    "https://www.eia.gov/electricity/annual/secrev-map.php"
)

_EIA_PRICE_LIMITATION = (
    "EIA FAQ: published average retail electricity prices are derived as "
    "utility revenue divided by retail sales and are not utility rates or "
    "itemized tariff schedules."
)

_FLAT_TARIFF_NOTES = (
    "Historical annual-average flat-tariff closure: the same sourced EIA "
    "average price is assigned to peak and off-peak price roots.",
    "The peak-energy fraction is set to 0.0 only as a resolver-neutral "
    "closure under equal peak/off-peak prices; it is not a measured "
    "time-of-use load split.",
    "Demand-charge roots are not assigned. EIA average retail prices are "
    "delivered average prices, not utility rates or itemized tariff "
    "schedules.",
    "Not a live 2026 value; the cited Electric Power Annual data are final "
    "2024 historical annual averages.",
)


def _root_assignments(assignments: dict[str, float]) -> dict[str, float]:
    unknown = [name for name in assignments if name not in Registry.variables]
    if unknown:
        raise ValueError(
            "economics preset assignments reference unknown variables: "
            f"{sorted(unknown)}"
        )
    non_roots = [
        name
        for name in assignments
        if not Registry.variables[name].is_root_input
    ]
    if non_roots:
        raise ValueError(
            "economics preset assignments must be root inputs only: "
            f"{sorted(non_roots)}"
        )
    return assignments


def _flat_power_tariff(
    *,
    name: str,
    description: str,
    usd_per_kwh: float,
    source: str,
) -> Preset:
    return Preset(
        name=name,
        description=description,
        assignments=_root_assignments(
            {
                "econ.power.price_kwh_peak": usd_per_kwh,
                "econ.power.price_kwh_offpeak": usd_per_kwh,
                "econ.power.peak_energy_fraction": 0.0,
            }
        ),
        source=source,
        notes=_FLAT_TARIFF_NOTES,
    )


us_2024_commercial_flat_power_tariff = _flat_power_tariff(
    name="us_2024_commercial_flat_power_tariff",
    description=(
        "Historical U.S. 2024 Total Electric Industry commercial average "
        "retail electricity price, represented as a flat tariff."
    ),
    usd_per_kwh=0.1275,
    source=(
        f"{_EIA_US_2024_AVERAGE_PRICE_SOURCE} Converts 12.75 cents/kWh to "
        f"0.1275 USD/kWh. {_EIA_PRICE_LIMITATION}"
    ),
)


us_2024_industrial_flat_power_tariff = _flat_power_tariff(
    name="us_2024_industrial_flat_power_tariff",
    description=(
        "Historical U.S. 2024 Total Electric Industry industrial average "
        "retail electricity price, represented as a flat tariff."
    ),
    usd_per_kwh=0.0813,
    source=(
        f"{_EIA_US_2024_AVERAGE_PRICE_SOURCE} Converts 8.13 cents/kWh to "
        f"0.0813 USD/kWh. {_EIA_PRICE_LIMITATION}"
    ),
)


california_2024_commercial_flat_power_tariff = _flat_power_tariff(
    name="california_2024_commercial_flat_power_tariff",
    description=(
        "Historical California 2024 commercial average retail electricity "
        "price, represented as a flat tariff."
    ),
    usd_per_kwh=0.2554,
    source=(
        f"{_EIA_CA_2024_AVERAGE_PRICE_SOURCE} Converts 25.54 cents/kWh to "
        f"0.2554 USD/kWh. {_EIA_PRICE_LIMITATION}"
    ),
)


california_2024_industrial_flat_power_tariff = _flat_power_tariff(
    name="california_2024_industrial_flat_power_tariff",
    description=(
        "Historical California 2024 industrial average retail electricity "
        "price, represented as a flat tariff."
    ),
    usd_per_kwh=0.2153,
    source=(
        f"{_EIA_CA_2024_AVERAGE_PRICE_SOURCE} Converts 21.53 cents/kWh to "
        f"0.2153 USD/kWh. {_EIA_PRICE_LIMITATION}"
    ),
)


POWER_PRICE_PRESETS = (
    us_2024_commercial_flat_power_tariff,
    us_2024_industrial_flat_power_tariff,
    california_2024_commercial_flat_power_tariff,
    california_2024_industrial_flat_power_tariff,
)


__all__ = [
    "POWER_PRICE_PRESETS",
    "us_2024_commercial_flat_power_tariff",
    "us_2024_industrial_flat_power_tariff",
    "california_2024_commercial_flat_power_tariff",
    "california_2024_industrial_flat_power_tariff",
]
