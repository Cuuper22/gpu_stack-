"""Core process-geometry model relationships."""

import pytest

from gpu_stack import Registry, resolve
from gpu_stack.core import RelationRole
from tests.helpers.lithography import source_quark_assignments


def test_source_plasma_radial_expansion_uses_species_mass_chain():
    proton_mass = Registry.variables["physics.proton_mass"].value
    neutron_mass = Registry.variables["physics.neutron_mass"].value
    boltzmann = Registry.variables["physics.boltzmann"].value
    gas_temperature = 1000.0
    expansion_factor = (5.0 / 3.0) ** 0.5
    species_mass = proton_mass + neutron_mass

    result = resolve(
        "physical.lithography.source_plasma_column_radial_expansion_speed",
        assignments={
            **source_quark_assignments(1, 1),
            "physical.lithography.source_plasma_species_gas_temperature": gas_temperature,
        },
    )

    assert float(result.value) == pytest.approx(
        expansion_factor * (boltzmann * gas_temperature / species_mass) ** 0.5
    )
    assert [step.equation for step in result.trace] == [
        "physical.eq.lithography_source_proton_count_from_valence_quarks",
        "physical.eq.lithography_source_neutron_count_from_valence_quarks",
        "physical.eq.lithography_source_plasma_species_particle_mass_from_nuclear_counts",
        "physical.eq.lithography_source_plasma_species_thermal_speed_from_gas_temperature",
        "physical.eq.lithography_source_plasma_column_expansion_speed_factor_from_monatomic_sound_speed",
        "physical.eq.lithography_source_plasma_column_radial_expansion_speed_from_species_thermal_speed",
    ]


def test_channel_length_has_process_geometry_model():
    channel = Registry.variables["physical.channel_length"]
    assert not channel.is_root_input
    approximations = channel.approximations()
    assert len(approximations) == 1
    eq = approximations[0]
    assert eq.name == "physical.eq.channel_length_process"
    assert eq.role is RelationRole.APPROXIMATION


def test_channel_length_dependencies_are_process_geometry_inputs():
    deps = {v.name for v in Registry.variables["physical.channel_length"].direct_dependencies()}
    assert deps == {
        "physical.process.node_length",
        "physical.process.gate_length_scale",
        "physical.process.gate_length_bias",
    }


def test_process_node_length_depends_on_frontend_and_backend_pitch():
    node = Registry.variables["physical.process.node_length"]
    assert not node.is_root_input
    deps = {v.name for v in node.direct_dependencies()}
    assert deps == {
        "physical.process.contacted_gate_pitch",
        "physical.process.minimum_metal_pitch",
        "physical.process.node_geometry_factor",
    }

    result = resolve(
        "physical.process.node_length",
        assignments={
            "physical.process.contacted_gate_pitch": 4.0,
            "physical.process.minimum_metal_pitch": 9.0,
            "physical.process.node_geometry_factor": 2.0,
        },
    )
    assert float(result.value) == pytest.approx(12.0)


def test_contacted_gate_pitch_depends_on_layout_components():
    cpp = Registry.variables["physical.process.contacted_gate_pitch"]
    assert not cpp.is_root_input
    deps = {v.name for v in cpp.direct_dependencies()}
    assert deps == {
        "physical.process.drawn_gate_length",
        "physical.process.source_drain_contact_width",
        "physical.process.gate_contact_spacing",
    }

    result = resolve(
        "physical.process.contacted_gate_pitch",
        assignments={
            "physical.process.drawn_gate_length": 4.0,
            "physical.process.source_drain_contact_width": 6.0,
            "physical.process.gate_contact_spacing": 1.5,
        },
    )
    assert float(result.value) == pytest.approx(13.0)


def test_drawn_gate_length_depends_on_lithography_resolution_and_bias():
    gate = Registry.variables["physical.process.drawn_gate_length"]
    assert not gate.is_root_input
    deps = {v.name for v in gate.direct_dependencies()}
    assert deps == {
        "physical.lithography.gate_resolution",
        "physical.process.gate_length_lithography_bias",
    }

    result = resolve(
        "physical.process.drawn_gate_length",
        assignments={
            "physical.lithography.wavelength": 10.0,
            "physical.lithography.numerical_aperture": 2.0,
            "physical.lithography.gate_k1": 0.8,
            "physical.process.gate_length_lithography_bias": 1.0,
        },
    )
    assert float(result.value) == pytest.approx(5.0)


def test_contact_width_and_gate_spacing_have_lower_process_models():
    contact = Registry.variables["physical.process.source_drain_contact_width"]
    assert not contact.is_root_input
    assert {v.name for v in contact.direct_dependencies()} == {
        "physical.lithography.contact_resolution",
        "physical.process.source_drain_contact_bias",
    }

    spacing = Registry.variables["physical.process.gate_contact_spacing"]
    assert not spacing.is_root_input
    assert {v.name for v in spacing.direct_dependencies()} == {
        "physical.process.gate_contact_overlay_budget",
        "physical.process.gate_contact_enclosure_margin",
    }

    contact_result = resolve(
        "physical.process.source_drain_contact_width",
        assignments={
            "physical.lithography.wavelength": 10.0,
            "physical.lithography.numerical_aperture": 2.0,
            "physical.lithography.contact_k1": 1.0,
            "physical.process.source_drain_contact_bias": 1.0,
        },
    )
    assert float(contact_result.value) == pytest.approx(6.0)

    spacing_result = resolve(
        "physical.process.gate_contact_spacing",
        assignments={
            "physical.process.gate_contact_overlay_budget": 0.5,
            "physical.process.gate_contact_enclosure_margin": 1.0,
        },
    )
    assert float(spacing_result.value) == pytest.approx(1.5)


def test_metal_width_and_spacing_depend_on_lithography_resolution_and_bias():
    width = Registry.variables["physical.process.minimum_metal_width"]
    spacing = Registry.variables["physical.process.minimum_metal_spacing"]
    assert not width.is_root_input
    assert not spacing.is_root_input
    assert {v.name for v in width.direct_dependencies()} == {
        "physical.lithography.metal_width_resolution",
        "physical.process.minimum_metal_width_bias",
    }
    assert {v.name for v in spacing.direct_dependencies()} == {
        "physical.lithography.metal_spacing_resolution",
        "physical.process.minimum_metal_spacing_bias",
    }

    width_result = resolve(
        "physical.process.minimum_metal_width",
        assignments={
            "physical.lithography.wavelength": 10.0,
            "physical.lithography.numerical_aperture": 2.0,
            "physical.lithography.metal_width_k1": 0.8,
            "physical.process.minimum_metal_width_bias": 0.25,
        },
    )
    assert float(width_result.value) == pytest.approx(4.25)

    spacing_result = resolve(
        "physical.process.minimum_metal_spacing",
        assignments={
            "physical.lithography.wavelength": 10.0,
            "physical.lithography.numerical_aperture": 2.0,
            "physical.lithography.metal_spacing_k1": 1.0,
            "physical.process.minimum_metal_spacing_bias": -0.5,
        },
    )
    assert float(spacing_result.value) == pytest.approx(4.5)


def test_minimum_metal_pitch_depends_on_width_and_spacing():
    pitch = Registry.variables["physical.process.minimum_metal_pitch"]
    assert not pitch.is_root_input
    deps = {v.name for v in pitch.direct_dependencies()}
    assert deps == {
        "physical.process.minimum_metal_width",
        "physical.process.minimum_metal_spacing",
    }

    result = resolve(
        "physical.process.minimum_metal_pitch",
        assignments={
            "physical.process.minimum_metal_width": 4.0,
            "physical.process.minimum_metal_spacing": 5.0,
        },
    )
    assert float(result.value) == pytest.approx(9.0)
