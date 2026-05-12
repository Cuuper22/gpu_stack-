"""
tests/test_thermal_units.py
===========================

Thermal scope metadata coverage for water/environment and facility power.
"""

from gpu_stack import Registry


THERMAL_ENV_VARIABLES = {
    "thermal.water.latent_heat",
    "thermal.water.density",
    "thermal.water.cycles_of_concentration",
    "thermal.water.drift_fraction",
    "thermal.water.evap_rate",
    "thermal.water.blowdown_rate",
    "thermal.water.drift_rate",
    "thermal.water.usage_rate",
    "thermal.water.wue",
    "thermal.env.ashrae_a1_inlet_min",
    "thermal.env.ashrae_a1_inlet_max",
    "thermal.env.relative_humidity",
    "thermal.env.relative_humidity_min",
    "thermal.env.relative_humidity_max",
    "thermal.env.dew_point",
    "thermal.env.condensation_margin",
    "thermal.env.dew_point_headroom",
}

THERMAL_ENV_RELATIONS = {
    "thermal.eq.water_evap_rate",
    "thermal.eq.water_blowdown_rate",
    "thermal.eq.water_drift_rate",
    "thermal.eq.water_usage_rate",
    "thermal.eq.wue",
    "thermal.eq.dew_point_headroom",
    "thermal.ineq.ashrae_a1_low",
    "thermal.ineq.ashrae_a1_high",
    "thermal.ineq.relative_humidity_low",
    "thermal.ineq.relative_humidity_high",
    "thermal.ineq.condensation_margin",
}

THERMAL_ENV_CHECKED_RELATIONS = THERMAL_ENV_RELATIONS - {"thermal.eq.wue"}

FACILITY_POWER_VARIABLES = {
    "thermal.facility.cooling_power",
    "thermal.facility.ups_loss_fraction",
    "thermal.facility.transformer_loss_fraction",
    "thermal.facility.ups_loss",
    "thermal.facility.transformer_loss",
    "thermal.facility.lighting",
    "thermal.facility.misc",
    "thermal.dc.total_power",
    "thermal.dc.pue",
}

FACILITY_POWER_RELATIONS = {
    "thermal.eq.ups_loss",
    "thermal.eq.transformer_loss",
    "thermal.eq.lighting",
    "thermal.eq.facility_misc",
    "thermal.eq.dc_total_power",
    "thermal.eq.pue_definition",
}

FACILITY_CHECKED_RELATIONS = {
    "thermal.eq.fan_power",
    "thermal.eq.recovered_heat_power",
    "thermal.eq.heat_to_reject",
    "thermal.eq.chiller_heat_load",
    "thermal.eq.chiller_power",
    "thermal.eq.cooling_tower_power",
    "thermal.eq.cooling_power_total",
    "thermal.eq.lighting",
}


def test_thermal_environment_variables_have_units_and_references():
    for name in THERMAL_ENV_VARIABLES:
        variable = Registry.variables[name]
        assert variable.sp_units is not None, name
        assert variable.references, name


def test_thermal_environment_relations_have_provenance_and_unit_checks():
    for name in THERMAL_ENV_RELATIONS:
        assert Registry.equations[name].references, name

    for name in THERMAL_ENV_CHECKED_RELATIONS:
        assert getattr(Registry.equations[name], "_check_units_flag", False), name


def test_facility_power_metadata_covers_total_power_and_losses():
    for name in FACILITY_POWER_VARIABLES:
        variable = Registry.variables[name]
        assert variable.sp_units is not None, name
        assert variable.references, name

    for name in FACILITY_POWER_RELATIONS:
        assert Registry.equations[name].references, name


def test_facility_verifiable_cooling_power_relations_are_unit_checked():
    for name in FACILITY_CHECKED_RELATIONS:
        assert getattr(Registry.equations[name], "_check_units_flag", False), name
