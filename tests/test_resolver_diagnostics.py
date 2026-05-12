"""
tests/test_resolver_diagnostics.py
==================================

Focused coverage for scenario diagnostics layered on top of the resolver.
The core resolver still owns resolution; these tests make sure missing
scenario inputs and violated feasibility checks carry enough metadata for the
CLI to tell a user what to fix next.
"""

import contextlib
import io

import sympy as sp

from gpu_stack import resolve
from gpu_stack.cli import main


def _diagnostics_by_variable(target):
    return {item.variable: item for item in resolve(target).unresolved_inputs}


def _assert_primitive_boundary(diagnostic, family):
    assert diagnostic.family == family
    assert diagnostic.boundary_category == "primitive-root"
    assert diagnostic.primitive_boundary is True
    assert diagnostic.kind == "ROOT_INPUT"


def _assert_symbolic_boundary(diagnostic, family):
    assert diagnostic.family == family
    assert diagnostic.boundary_category == "symbolic-boundary"
    assert diagnostic.primitive_boundary is False
    assert diagnostic.kind == "DERIVED"


def test_unresolved_diagnostics_distinguish_roots_from_symbolic_boundaries():
    result = resolve("cluster.node.peak_flops")

    assert result.missing == {"cluster.node.n_gpus", "gpu.peak_flops"}
    diagnostics = {item.variable: item for item in result.unresolved_inputs}

    root = diagnostics["cluster.node.n_gpus"]
    assert root.reason == "root input assignment required"
    assert root.kind == "ROOT_INPUT"
    assert root.family == "cluster.node"
    assert root.boundary_category == "primitive-root"
    assert root.primitive_boundary is True
    assert root.units
    assert "cluster.node.peak_flops" in root.direct_dependents

    boundary = diagnostics["gpu.peak_flops"]
    assert boundary.reason == "symbolic boundary; assign directly or resolve its inputs"
    assert boundary.scope == "gpu"
    assert boundary.kind == "DERIVED"
    assert boundary.family == "gpu"
    assert boundary.boundary_category == "symbolic-boundary"
    assert boundary.primitive_boundary is False
    assert "cluster.node.peak_flops" in boundary.direct_dependents
    assert boundary.dependents_count >= len(boundary.direct_dependents)


def test_unselected_variant_diagnostic_lists_variant_keys():
    result = resolve("training.flops_executed_per_step")

    diagnostic = next(
        item for item in result.unresolved_inputs
        if item.variable == "training.flops_per_step"
    )
    assert diagnostic.reason == "variant selector required"
    assert diagnostic.boundary_category == "variant-family"
    assert diagnostic.primitive_boundary is False
    assert diagnostic.variant_keys == ("dense", "moe")
    assert "training.eq.flops_step_dense" in diagnostic.defining_equations
    assert "training.eq.flops_step_moe" in diagnostic.defining_equations


def test_physical_lithography_unresolved_inputs_expose_boundary_family():
    result = resolve("physical.lithography.source_plasma_drive_beam_wavelength")

    diagnostics = {item.variable: item for item in result.unresolved_inputs}
    detuning = diagnostics["physical.lithography.source_plasma_drive_edge_detuning_ratio"]
    assert detuning.family == "physical.lithography.source_plasma_drive"
    assert detuning.boundary_category == "primitive-root"
    assert detuning.primitive_boundary is True

    ionization = diagnostics["physical.lithography.source_ionization_energy"]
    assert ionization.family == "physical.lithography.source"
    assert ionization.boundary_category == "symbolic-boundary"
    assert ionization.primitive_boundary is False


def test_valence_quark_roots_share_compact_primitive_boundary_family():
    result = resolve("physical.lithography.source_proton_count")

    diagnostics = {item.variable: item for item in result.unresolved_inputs}
    for variable in (
        "physical.lithography.source_valence_down_quark_count",
        "physical.lithography.source_valence_up_quark_count",
    ):
        diagnostic = diagnostics[variable]
        assert diagnostic.family == "physical.lithography.source_valence"
        assert diagnostic.boundary_category == "primitive-root"
        assert diagnostic.primitive_boundary is True


def test_source_plasma_gas_roots_keep_species_family_metadata():
    diagnostics = _diagnostics_by_variable(
        "physical.lithography.source_plasma_species_number_density"
    )

    assert set(diagnostics) == {
        "physical.lithography.source_plasma_species_gas_temperature",
        "physical.lithography.source_plasma_species_partial_pressure",
    }
    for variable in diagnostics:
        _assert_primitive_boundary(
            diagnostics[variable],
            "physical.lithography.source_plasma_species",
        )


def test_source_plasma_focus_roots_keep_drive_family_metadata():
    waist = _diagnostics_by_variable(
        "physical.lithography.source_plasma_drive_beam_parameter_waist_radius"
    )
    acceptance = _diagnostics_by_variable(
        "physical.lithography.source_plasma_drive_acceptance_half_angle"
    )
    bpp = _diagnostics_by_variable(
        "physical.lithography.source_plasma_drive_beam_parameter_product"
    )

    for diagnostics, expected_variables in (
        (
            waist,
            {
                "physical.lithography.source_plasma_drive_objective_pupil_radius",
                "physical.lithography.source_plasma_drive_pupil_beam_fill_factor",
            },
        ),
        (
            acceptance,
            {
                "physical.lithography.source_plasma_drive_objective_focal_length",
                "physical.lithography.source_plasma_drive_objective_pupil_radius",
            },
        ),
    ):
        assert set(diagnostics) == expected_variables
        for variable in expected_variables:
            _assert_primitive_boundary(
                diagnostics[variable],
                "physical.lithography.source_plasma_drive",
            )

    divergence = bpp[
        "physical.lithography.source_plasma_drive_far_field_divergence_half_angle"
    ]
    _assert_primitive_boundary(divergence, "physical.lithography.source_plasma_drive")
    waist_boundary = bpp[
        "physical.lithography.source_plasma_drive_beam_parameter_waist_radius"
    ]
    _assert_symbolic_boundary(waist_boundary, "physical.lithography.source_plasma_drive")


def test_medium_response_roots_keep_medium_family_metadata():
    polarizable = _diagnostics_by_variable(
        "physical.lithography.medium_polarizable_electron_fraction"
    )
    oscillator = _diagnostics_by_variable(
        "physical.lithography.medium_oscillator_sum_rule_fraction"
    )
    resonance = _diagnostics_by_variable(
        "physical.lithography.medium_resonance_to_source_frequency_ratio"
    )

    _assert_primitive_boundary(
        polarizable["physical.lithography.medium_polarizable_electron_count"],
        "physical.lithography.medium",
    )
    _assert_symbolic_boundary(
        polarizable["physical.lithography.medium_formula_unit_electron_count"],
        "physical.lithography.medium",
    )

    for variable in (
        "physical.lithography.medium_dominant_oscillator_electron_count",
        "physical.lithography.medium_polarizable_electron_count",
    ):
        _assert_primitive_boundary(oscillator[variable], "physical.lithography.medium")

    _assert_primitive_boundary(
        resonance["physical.lithography.medium_resonance_energy"],
        "physical.lithography.medium",
    )
    _assert_symbolic_boundary(
        resonance["physical.lithography.photon_energy"],
        "physical.lithography",
    )


def test_sourced_pythia_cost_per_token_unresolved_inputs_use_public_families():
    from gpu_stack.presets import scenarios

    result = scenarios.pythia_70m_dgx_h100_us_2024_industrial_power.resolve(
        "econ.cost.per_token"
    )

    assert tuple(item.variable for item in result.unresolved_inputs) == tuple(
        sorted(result.missing)
    )
    diagnostics = {item.variable: item for item in result.unresolved_inputs}

    expected_primitive_families = {
        "cluster.node.cpu.power_per_cpu": "cluster.node",
        "cluster.node.misc.fixed_power": "cluster.node",
        "econ.asset.useful_life": "econ.asset",
        "econ.carbon.price_per_tonne": "econ.carbon",
        "econ.cluster.storage_capex": "econ.cluster",
        "econ.gpu.capex": "econ.gpu",
        "econ.node.cpu_capex": "econ.node",
        "econ.power.capacity_charge_kw_month": "econ.power",
        "thermal.water.latent_heat": "thermal.water",
    }
    for variable, family in expected_primitive_families.items():
        diagnostic = diagnostics[variable]
        assert diagnostic.family == family
        assert diagnostic.boundary_category == "primitive-root"
        assert diagnostic.primitive_boundary is True

    expected_symbolic_families = {
        "cluster.node.storage_power": "cluster.node",
        "econ.cluster.facility_capex": "econ.cluster",
        "econ.network.transit_cost_rate": "econ.network",
    }
    for variable, family in expected_symbolic_families.items():
        diagnostic = diagnostics[variable]
        assert diagnostic.family == family
        assert diagnostic.boundary_category == "symbolic-boundary"
        assert diagnostic.primitive_boundary is False


def test_constraint_violation_diagnostic_captures_evaluated_inputs():
    result = resolve(
        "physical.gate.elmore_delay",
        assignments={
            "physical.gate.r_on": 1.0,
            "physical.gate.fanout": 1,
            "physical.gate.c_input": 1.0,
            "physical.interconnect.c_total": 1.0,
            "physical.interconnect.r_per_length": 0.0,
            "physical.interconnect.c_per_length": 1.0,
            "physical.wire_length": 1.0,
            "physical.clock_frequency": 1.0,
        },
    )

    diagnostic = next(
        item for item in result.violated_constraints
        if item.equation == "physical.eq.clock_timing_constraint"
    )
    assert diagnostic.variable == "physical.gate.elmore_delay"
    assert diagnostic.evaluated is sp.S.false
    assert diagnostic.inputs["physical.clock_period"] == 1.0
    assert diagnostic.inputs["physical.gate.elmore_delay"] == 2.0
    assert "timing closure" in diagnostic.description


def test_cli_missing_prints_unresolved_input_diagnostics():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = main([
            "resolve",
            "cluster.node.peak_flops",
            "--assign",
            "cluster.node.n_gpus=8",
            "--missing",
        ])

    out = buf.getvalue()
    assert rc == 0
    assert "missing: ['gpu.peak_flops']" in out
    assert "unresolved inputs:" in out
    assert "gpu.peak_flops" in out
    assert "--assign gpu.peak_flops=VALUE" in out


def test_cli_diagnostics_prints_violated_constraints():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = main([
            "resolve",
            "physical.gate.elmore_delay",
            "--assign",
            "physical.gate.r_on=1",
            "--assign",
            "physical.gate.fanout=1",
            "--assign",
            "physical.gate.c_input=1",
            "--assign",
            "physical.interconnect.c_total=1",
            "--assign",
            "physical.interconnect.r_per_length=0",
            "--assign",
            "physical.interconnect.c_per_length=1",
            "--assign",
            "physical.wire_length=1",
            "--assign",
            "physical.clock_frequency=1",
            "--diagnostics",
        ])

    out = buf.getvalue()
    assert rc == 0
    assert "violated constraints:" in out
    assert "physical.eq.clock_timing_constraint" in out
    assert "physical.clock_period=1" in out
    assert "physical.gate.elmore_delay=2" in out
