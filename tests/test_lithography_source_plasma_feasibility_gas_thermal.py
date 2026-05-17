"""
Gas and thermal feasibility coverage for lithography source plasmas.
"""

import pytest
import sympy as sp

from gpu_stack import Registry, resolve
from gpu_stack.constants import BOLTZMANN
from gpu_stack.core import Inequality, RelationRole, VariableKind
from tests.test_lithography_source_plasma_feasibility import (
    SOURCE_PLASMA_GAS_THERMAL_CONSTRAINTS,
    _failed_constraint,
    _failed_validity,
    _satisfied_constraint,
)


def test_source_plasma_gas_thermal_constraints_are_named_boundaries():
    for equation_name, variable_name, op, rhs, _bad_value in (
        SOURCE_PLASMA_GAS_THERMAL_CONSTRAINTS
    ):
        eq = Registry.equations[equation_name]
        variable = Registry.variables[variable_name]
        assert isinstance(eq, Inequality)
        assert eq.role is RelationRole.CONSTRAINT
        assert eq in variable.constraints()
        assert eq.op == op
        assert eq.rhs == rhs
        assert eq.references
        assert isinstance(eq.as_sympy(), sp.Rel)


def test_source_plasma_gas_thermal_variables_keep_boundary_semantics():
    root_inputs = {
        "physical.lithography.source_plasma_species_partial_pressure",
        "physical.lithography.source_plasma_species_gas_temperature",
    }
    derived_by_real_equations = {
        "physical.lithography.source_plasma_species_number_density": (
            "physical.eq.lithography_source_plasma_species_number_density_from_ideal_gas"
        ),
        "physical.lithography.source_plasma_species_thermal_speed": (
            "physical.eq.lithography_source_plasma_species_thermal_speed_from_gas_temperature"
        ),
    }

    for variable_name in root_inputs:
        variable = Registry.variables[variable_name]
        assert variable.kind is VariableKind.ROOT_INPUT
        assert variable.is_root_input
        assert variable.direct_dependencies() == set()
        assert variable.constraints()

    for variable_name, equation_name in derived_by_real_equations.items():
        variable = Registry.variables[variable_name]
        assert variable.kind is VariableKind.DERIVED
        assert not variable.is_root_input
        assert Registry.equations[equation_name] in variable.defining_equations
        assert variable.constraints()


def test_source_plasma_gas_thermal_constraints_report_invalid_assignments():
    for equation_name, variable_name, _op, _rhs, bad_value in (
        SOURCE_PLASMA_GAS_THERMAL_CONSTRAINTS
    ):
        result = resolve(variable_name, assignments={variable_name: bad_value})
        assert float(result.value) == pytest.approx(bad_value)
        _failed_constraint(result, equation_name)


def test_source_plasma_ideal_gas_validity_reports_invalid_pressure_boundary():
    result = resolve(
        "physical.lithography.source_plasma_species_number_density",
        assignments={
            "physical.lithography.source_plasma_species_partial_pressure": -1.0,
            "physical.lithography.source_plasma_species_gas_temperature": 300.0,
        },
    )

    assert float(result.value) < 0.0
    assert [step.equation for step in result.trace] == [
        "physical.eq.lithography_source_plasma_species_number_density_from_ideal_gas",
    ]
    _failed_validity(
        result,
        "physical.eq.lithography_source_plasma_species_number_density_from_ideal_gas",
    )
    _failed_constraint(
        result,
        "physical.ineq.lithography_source_plasma_species_partial_pressure_positive",
    )
    _failed_constraint(
        result,
        "physical.ineq.lithography_source_plasma_species_number_density_positive",
    )


def test_source_plasma_ideal_gas_validity_reports_invalid_temperature_boundary():
    result = resolve(
        "physical.lithography.source_plasma_species_number_density",
        assignments={
            "physical.lithography.source_plasma_species_partial_pressure": 1.0,
            "physical.lithography.source_plasma_species_gas_temperature": -300.0,
        },
    )

    assert float(result.value) < 0.0
    assert [step.equation for step in result.trace] == [
        "physical.eq.lithography_source_plasma_species_number_density_from_ideal_gas",
    ]
    _failed_validity(
        result,
        "physical.eq.lithography_source_plasma_species_number_density_from_ideal_gas",
    )
    _failed_constraint(
        result,
        "physical.ineq.lithography_source_plasma_species_gas_temperature_positive",
    )
    _failed_constraint(
        result,
        "physical.ineq.lithography_source_plasma_species_number_density_positive",
    )
    _failed_constraint(
        result,
        "domain.physical.lithography.source_plasma_species_gas_temperature.positive",
    )
    _failed_constraint(
        result,
        "domain.physical.lithography.source_plasma_species_number_density.positive",
    )


def test_source_plasma_ideal_gas_valid_assignments_resolve_cleanly():
    partial_pressure = 2.0
    gas_temperature = 400.0

    result = resolve(
        "physical.lithography.source_plasma_species_number_density",
        assignments={
            "physical.lithography.source_plasma_species_partial_pressure": (
                partial_pressure
            ),
            "physical.lithography.source_plasma_species_gas_temperature": (
                gas_temperature
            ),
        },
    )

    assert float(result.value) == pytest.approx(
        partial_pressure / (BOLTZMANN.value * gas_temperature)
    )
    assert [step.equation for step in result.trace] == [
        "physical.eq.lithography_source_plasma_species_number_density_from_ideal_gas",
    ]
    assert all(
        check.satisfied is True for check in result.approximation_validity
    )
    for equation_name in [
        "physical.ineq.lithography_source_plasma_species_partial_pressure_positive",
        "physical.ineq.lithography_source_plasma_species_gas_temperature_positive",
        "physical.ineq.lithography_source_plasma_species_number_density_positive",
        "domain.physical.lithography.source_plasma_species_partial_pressure.positive",
        "domain.physical.lithography.source_plasma_species_gas_temperature.positive",
        "domain.physical.lithography.source_plasma_species_number_density.positive",
    ]:
        _satisfied_constraint(result, equation_name)
