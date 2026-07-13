"""CLI resolve command tests."""

import contextlib
import io

import pytest

from gpu_stack.cli import main
from tests.helpers.cli import (
    captured_stderr,
    captured_stdout,
    unresolved_input_line,
)


def test_resolve_missing_exposes_source_nucleon_root_diagnostics():
    with captured_stdout() as buf:
        rc = main([
            "resolve",
            "physical.lithography.source_valence_up_quark_count",
            "--missing",
        ])

    out = buf.getvalue()
    assert rc == 0
    assert (
        "missing: ['physical.lithography.source_neutron_count', "
        "'physical.lithography.source_proton_count']"
    ) in out
    assert "unresolved inputs:" in out
    assert out.count("kind=ROOT_INPUT reason=root input assignment required") == 2
    assert "kind=DERIVED reason=symbolic boundary" not in out

    neutron = unresolved_input_line(
        out,
        "physical.lithography.source_neutron_count",
    )
    proton = unresolved_input_line(
        out,
        "physical.lithography.source_proton_count",
    )
    assert "[count] scope=physical kind=ROOT_INPUT" in neutron
    assert "[count] scope=physical kind=ROOT_INPUT" in proton
    assert (
        "hint: --assign "
        "physical.lithography.source_neutron_count=VALUE"
    ) in out
    assert (
        "direct physical.lithography.source_isotope_mass_number, "
        "physical.lithography.source_neutron_excess"
    ) in out


def test_resolve_missing_families_groups_source_nucleon_roots():
    with captured_stdout() as buf:
        rc = main([
            "resolve",
            "physical.lithography.source_valence_up_quark_count",
            "--missing-families",
        ])

    out = buf.getvalue()
    assert rc == 0
    assert "physical.lithography.source_valence_up_quark_count =" in out
    assert "unresolved inputs:" not in out
    assert "missing families:" in out
    assert (
        "family=physical.lithography.source "
        "boundary_category=primitive-root primitive_boundary=True count=2 "
        "names=physical.lithography.source_neutron_count, "
        "physical.lithography.source_proton_count"
    ) in out


def test_resolve_missing_exposes_mixed_cost_frontier_diagnostics():
    with captured_stdout() as buf:
        rc = main([
            "resolve",
            "econ.cost.per_token",
            "--preset",
            "scenarios.pythia_70m_dgx_h100_us_2024_industrial_power",
            "--missing",
        ])

    out = buf.getvalue()
    assert rc == 0
    assert "econ.cost.per_token =" in out
    assert "missing:" in out
    assert "unresolved inputs:" in out
    assert out.count("kind=DERIVED reason=symbolic boundary") == 3
    assert "missing families:" not in out

    for variable, expected in {
        "cluster.node.cpu.power_per_cpu": (
            "[W/CPU] scope=cluster kind=ROOT_INPUT "
            "reason=root input assignment required"
        ),
        "cluster.node.storage_power": (
            "[W] scope=cluster kind=DERIVED "
            "reason=symbolic boundary; assign directly or resolve its inputs"
        ),
        "econ.cluster.facility_capex": (
            "[USD] scope=economics kind=DERIVED "
            "reason=symbolic boundary; assign directly or resolve its inputs"
        ),
        "econ.node.cpu_capex": (
            "[USD] scope=economics kind=ROOT_INPUT "
            "reason=root input assignment required"
        ),
        "econ.power.capacity_charge_kw_month": (
            "[USD/(kW*month)] scope=economics kind=ROOT_INPUT "
            "reason=root input assignment required"
        ),
        "thermal.water.latent_heat": (
            "[J/kg] scope=thermal kind=ROOT_INPUT "
            "reason=root input assignment required"
        ),
    }.items():
        assert expected in unresolved_input_line(out, variable)

    assert "definitions: cluster.eq.node_storage_power" in out
    assert "definitions: econ.eq.cluster_facility_capex" in out
    assert "definitions: econ.eq.network_transit_cost_rate" in out


def test_resolve_missing_families_groups_mixed_cost_frontier():
    with captured_stdout() as buf:
        rc = main([
            "resolve",
            "econ.cost.per_token",
            "--preset",
            "scenarios.pythia_70m_dgx_h100_us_2024_industrial_power",
            "--missing-families",
        ])

    out = buf.getvalue()
    assert rc == 0
    assert "econ.cost.per_token =" in out
    assert "unresolved inputs:" not in out
    assert "missing families:" in out
    assert (
        "family=cluster.node boundary_category=primitive-root "
        "primitive_boundary=True count=6"
    ) in out
    assert (
        "family=cluster.node boundary_category=symbolic-boundary "
        "primitive_boundary=False count=1 names=cluster.node.storage_power"
    ) in out
    assert (
        "family=econ.cluster boundary_category=primitive-root "
        "primitive_boundary=True count=3"
    ) in out
    assert (
        "family=econ.cluster boundary_category=symbolic-boundary "
        "primitive_boundary=False count=1 names=econ.cluster.facility_capex"
    ) in out
    assert (
        "family=econ.network boundary_category=symbolic-boundary "
        "primitive_boundary=False count=1 names=econ.network.transit_cost_rate"
    ) in out
    assert (
        "family=thermal.water boundary_category=primitive-root "
        "primitive_boundary=True count=4"
    ) in out


def test_resolve_missing_and_missing_families_prints_both_sections():
    with captured_stdout() as buf:
        rc = main([
            "resolve",
            "physical.lithography.source_valence_up_quark_count",
            "--missing",
            "--missing-families",
        ])

    out = buf.getvalue()
    assert rc == 0
    assert "missing:" in out
    assert "unresolved inputs:" in out
    assert "missing families:" in out
    assert (
        "physical.lithography.source_neutron_count [count] "
        "scope=physical kind=ROOT_INPUT"
    ) in unresolved_input_line(
        out,
        "physical.lithography.source_neutron_count",
    )
    assert (
        "family=physical.lithography.source "
        "boundary_category=primitive-root primitive_boundary=True count=2"
    ) in out


def test_resolve_with_material_preset_hits_formula_count():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = main([
            "resolve",
            "physical.lithography.medium_formula_unit_electron_count",
            "--preset",
            "materials.medium_h2o_h1_o16_composition",
        ])
    out = buf.getvalue()
    assert rc == 0
    assert "physical.lithography.medium_formula_unit_electron_count = 10" in out


def test_resolve_with_preset_hits_demo_number():
    with captured_stdout() as buf:
        rc = main([
            "resolve",
            "cluster.rack.peak_flops",
            "--preset", "hardware.demo_rack",
        ])
    out = buf.getvalue()
    assert rc == 0
    assert "cluster.rack.peak_flops" in out
    # 1.08e18 shown in SymPy Float format.
    assert "1.08" in out


def test_resolve_with_unused_workload_selector_preset_hits_demo_number():
    with captured_stdout() as buf:
        rc = main([
            "resolve",
            "cluster.rack.peak_flops",
            "--preset", "hardware.demo_rack",
            "--preset", "workload.dense_variant_selector",
        ])
    out = buf.getvalue()
    assert rc == 0
    assert "cluster.rack.peak_flops" in out
    assert "1.08" in out


def test_resolve_with_scenario_preset_hits_cost_per_token():
    with captured_stdout() as buf:
        rc = main([
            "resolve",
            "econ.cost.per_token",
            "--preset", "scenarios.dense_training_cost_fixture",
        ])
    out = buf.getvalue()
    assert rc == 0
    assert "econ.cost.per_token" in out
    assert "0.000003000078" in out


def test_resolve_with_sourced_scenario_preset_hits_power_cost():
    with captured_stdout() as buf:
        rc = main([
            "resolve",
            "econ.run.power_cost",
            "--preset",
            "scenarios.pythia_70m_dgx_h100_us_2024_industrial_power",
            "--trace",
        ])
    out = buf.getvalue()
    assert rc == 0
    assert "econ.run.power_cost = 54.4378103942861" in out
    assert "econ.eq.run_power_cost" in out
    assert "econ.eq.price_kwh" in out
    assert "0.0813000000000000" in out


def test_resolve_cli_variant_overrides_preset_selector():
    with captured_stdout() as buf:
        rc = main([
            "resolve",
            "training.flops_per_step",
            "--preset", "workload.dense_variant_selector",
            "--assign", "arch.flops.step_dense=1e21",
            "--assign", "arch.flops.step_moe=3e20",
            "--variant", "training.flops_per_step=moe",
            "--trace",
        ])
    out = buf.getvalue()
    assert rc == 0
    assert "training.eq.flops_step_moe" in out
    assert "3.00000000000000E+20" in out


def test_resolve_with_inline_assignment():
    with captured_stdout() as buf:
        rc = main([
            "resolve",
            "cluster.node.peak_flops",
            "--assign", "cluster.node.n_gpus=4",
            "--assign", "gpu.peak_flops=2e15",
        ])
    out = buf.getvalue()
    assert rc == 0
    assert "8.00" in out.replace("E+", "e+").replace("E-", "e-")


def test_resolve_trace_prints_equation_names():
    with captured_stdout() as buf:
        rc = main([
            "resolve",
            "cluster.rack.peak_flops",
            "--preset", "hardware.demo_rack",
            "--trace",
        ])
    out = buf.getvalue()
    assert rc == 0
    assert "cluster.eq.rack_peak_flops" in out


def test_resolve_constraints_prints_constraint_status():
    with captured_stdout() as buf:
        rc = main([
            "resolve",
            "physical.gate.elmore_delay",
            "--assign", "physical.gate.r_on=1",
            "--assign", "physical.gate.fanout=1",
            "--assign", "physical.gate.c_input=1",
            "--assign", "physical.interconnect.c_total=1",
            "--assign", "physical.interconnect.r_per_length=0",
            "--assign", "physical.interconnect.c_per_length=1",
            "--assign", "physical.wire_length=1",
            "--assign", "physical.clock_frequency=0.1",
            "--constraints",
        ])
    out = buf.getvalue()
    assert rc == 0
    assert "constraints:" in out
    assert "physical.eq.clock_timing_constraint [satisfied]" in out


def test_resolve_approximation_validity_prints_status():
    with captured_stdout() as buf:
        rc = main([
            "resolve",
            "physical.lithography.medium_formula_unit_intercomponent_binding_energy",
            "--assign",
            "physical.lithography.medium_component_a_effective_intercomponent_charge_number=1",
            "--assign",
            "physical.lithography.medium_component_b_effective_intercomponent_charge_number=1",
            "--assign",
            "physical.lithography.medium_formula_unit_intercomponent_pair_count=1",
            "--assign",
            "physical.lithography.medium_component_a_effective_intercomponent_radius=4e-10",
            "--assign",
            "physical.lithography.medium_component_b_effective_intercomponent_radius=4e-10",
            "--assign",
            "physical.lithography.medium_intercomponent_gap=2e-10",
            "--assign",
            "physical.lithography.medium_intercomponent_relative_permittivity=1",
            "--approximation-validity",
        ])
    out = buf.getvalue()
    assert rc == 0
    assert "approximation validity:" in out
    assert (
        "physical.eq.lithography_medium_formula_unit_intercomponent_binding_energy"
        " [violated]"
    ) in out


def test_resolve_fail_on_violated_constraints_returns_nonzero():
    with captured_stdout() as buf:
        rc = main([
            "resolve",
            "physical.gate.elmore_delay",
            "--assign", "physical.gate.r_on=1",
            "--assign", "physical.gate.fanout=1",
            "--assign", "physical.gate.c_input=1",
            "--assign", "physical.interconnect.c_total=1",
            "--assign", "physical.interconnect.r_per_length=0",
            "--assign", "physical.interconnect.c_per_length=1",
            "--assign", "physical.wire_length=1",
            "--assign", "physical.clock_frequency=1",
            "--constraints",
            "--fail-on-violated-constraints",
        ])
    out = buf.getvalue()
    assert rc == 1
    assert "physical.eq.clock_timing_constraint [violated]" in out


def test_resolve_fail_on_violated_domain_constraint_returns_nonzero():
    with captured_stdout() as buf:
        rc = main([
            "resolve",
            "physical.lithography.source_plasma_drive_peak_intensity",
            "--assign",
            "physical.lithography.source_plasma_drive_pulse_fluence=-1",
            "--assign",
            "physical.lithography.source_plasma_drive_pulse_duration=1",
            "--assign",
            "physical.lithography.source_plasma_drive_pulse_temporal_shape_factor=1",
            "--constraints",
            "--fail-on-violated-constraints",
        ])
    out = buf.getvalue()
    assert rc == 1
    assert (
        "domain.physical.lithography.source_plasma_drive_pulse_fluence.positive"
        " [violated]"
    ) in out


def test_resolve_fail_on_violated_approximation_validity_returns_nonzero():
    with captured_stdout() as buf:
        rc = main([
            "resolve",
            "physical.lithography.medium_formula_unit_intercomponent_binding_energy",
            "--assign",
            "physical.lithography.medium_component_a_effective_intercomponent_charge_number=1",
            "--assign",
            "physical.lithography.medium_component_b_effective_intercomponent_charge_number=1",
            "--assign",
            "physical.lithography.medium_formula_unit_intercomponent_pair_count=1",
            "--assign",
            "physical.lithography.medium_component_a_effective_intercomponent_radius=4e-10",
            "--assign",
            "physical.lithography.medium_component_b_effective_intercomponent_radius=4e-10",
            "--assign",
            "physical.lithography.medium_intercomponent_gap=2e-10",
            "--assign",
            "physical.lithography.medium_intercomponent_relative_permittivity=1",
            "--approximation-validity",
            "--fail-on-violated-approximation-validity",
        ])
    out = buf.getvalue()
    assert rc == 1
    assert (
        "physical.eq.lithography_medium_formula_unit_intercomponent_binding_energy"
        " [violated]"
    ) in out


def test_resolve_fail_on_recovered_violated_approximation_validity_returns_nonzero():
    with captured_stdout() as buf:
        rc = main([
            "resolve",
            "physical.lithography.source_nuclear_radius_coefficient",
            "--assign",
            "physical.lithography.source_binding_coulomb_coefficient=-1",
            "--approximation-validity",
            "--fail-on-violated-approximation-validity",
        ])
    out = buf.getvalue()
    assert rc == 1
    assert (
        "physical.eq.lithography_source_nuclear_radius_coefficient"
        " [violated]"
    ) in out


def test_resolve_bad_variant_selector_returns_clean_error():
    with captured_stderr() as err:
        rc = main([
            "resolve",
            "cluster.rack.peak_flops",
            "--variant",
            "cluster.rack.n_nodes=dense",
        ])
    assert rc == 1
    assert "resolve error:" in err.getvalue()
    assert "no VARIANT relations" in err.getvalue()


def test_resolve_bad_assignment_returns_clean_error():
    with captured_stderr() as err:
        rc = main([
            "resolve",
            "cluster.rack.peak_flops",
            "--assign",
            "cluster.rack.n_NODES=9",
        ])
    assert rc == 1
    assert "resolve error:" in err.getvalue()
    assert "unknown variable name in assignments" in err.getvalue()


def test_resolve_unknown_target_returns_clean_error():
    with captured_stderr() as err:
        rc = main(["resolve", "cluster.rack.peak_flopz"])
    assert rc == 1
    assert "resolve error:" in err.getvalue()
    assert "unknown variable name" in err.getvalue()


def test_resolve_unknown_preset_raises_clean_error():
    with pytest.raises(SystemExit):
        main([
            "resolve",
            "cluster.rack.peak_flops",
            "--preset", "hardware.does_not_exist",
        ])
