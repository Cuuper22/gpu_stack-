"""
tests/test_lithography_source_species_boundaries.py
===================================================

Focused boundary checks for source isotope and source-plasma species roots.
"""

import pytest
import sympy as sp

from gpu_stack import Registry, resolve
from gpu_stack.constants import BOLTZMANN
from gpu_stack.core import Approximation, Inequality, RelationRole, VariableKind, gt
from gpu_stack.core.units import KELVIN, METER, PASCAL


SOURCE_VALENCE_UP = "physical.lithography.source_valence_up_quark_count"
SOURCE_VALENCE_DOWN = "physical.lithography.source_valence_down_quark_count"
SOURCE_ATOMIC_NUMBER = "physical.lithography.source_atomic_number"
SOURCE_ISOTOPE_MASS_NUMBER = "physical.lithography.source_isotope_mass_number"
SOURCE_PROTON_COUNT = "physical.lithography.source_proton_count"
SOURCE_NEUTRON_COUNT = "physical.lithography.source_neutron_count"
SOURCE_MASS_NUMBER = "physical.lithography.source_mass_number"
SOURCE_BOUND_ELECTRON_COUNT = "physical.lithography.source_bound_electron_count"
SOURCE_INNER_CLOSED_SHELL_ELECTRON_COUNT = (
    "physical.lithography.source_inner_closed_shell_electron_count"
)
SOURCE_TRANSITION_SHELL_OCCUPANCY = (
    "physical.lithography.source_transition_shell_occupancy"
)
SOURCE_PLASMA_PARTIAL_PRESSURE = (
    "physical.lithography.source_plasma_species_partial_pressure"
)
SOURCE_PLASMA_GAS_TEMPERATURE = (
    "physical.lithography.source_plasma_species_gas_temperature"
)
SOURCE_PLASMA_NUMBER_DENSITY = (
    "physical.lithography.source_plasma_species_number_density"
)
SOURCE_PLASMA_PARTIAL_PRESSURE_POSITIVE = (
    "physical.ineq.lithography_source_plasma_species_partial_pressure_positive"
)
SOURCE_PLASMA_GAS_TEMPERATURE_POSITIVE = (
    "physical.ineq.lithography_source_plasma_species_gas_temperature_positive"
)
SOURCE_PLASMA_NUMBER_DENSITY_POSITIVE = (
    "physical.ineq.lithography_source_plasma_species_number_density_positive"
)
SOURCE_PLASMA_IDEAL_GAS_CLOSURE = (
    "physical.eq.lithography_source_plasma_species_number_density_from_ideal_gas"
)


def _failed_constraint(result, equation):
    check = next(c for c in result.constraints if c.equation == equation)
    assert check.satisfied is False
    assert check.missing == set()
    return check


def _satisfied_constraint(result, equation):
    check = next(c for c in result.constraints if c.equation == equation)
    assert check.satisfied is True
    assert check.missing == set()
    return check


def _violated_constraint(result, equation):
    for violation in result.violated_constraints:
        if violation.equation == equation:
            return violation
    observed = [violation.equation for violation in result.violated_constraints]
    pytest.fail(f"missing violated constraint {equation!r}; saw {observed!r}")


def test_source_plasma_species_thermodynamic_roots_are_strict_positive_boundaries():
    cases = [
        (
            SOURCE_PLASMA_PARTIAL_PRESSURE,
            SOURCE_PLASMA_PARTIAL_PRESSURE_POSITIVE,
            PASCAL,
        ),
        (
            SOURCE_PLASMA_GAS_TEMPERATURE,
            SOURCE_PLASMA_GAS_TEMPERATURE_POSITIVE,
            KELVIN,
        ),
    ]

    for variable_name, equation_name, units in cases:
        variable = Registry.variables[variable_name]
        equation = Registry.equations[equation_name]

        assert variable.kind is VariableKind.ROOT_INPUT
        assert variable.is_root_input
        assert variable.assumptions["positive"] is True
        assert "nonnegative" not in variable.assumptions
        assert not hasattr(variable, "value")
        assert variable.value_range is None
        assert variable.sp_units == units
        assert isinstance(equation, Inequality)
        assert equation.role is RelationRole.CONSTRAINT
        assert equation in variable.constraints()
        assert equation.op == ">"
        assert equation.lhs == variable.symbol
        assert equation.rhs == sp.Integer(0)
        assert equation.references


def test_source_plasma_species_number_density_is_symbolic_ideal_gas_closure():
    partial_pressure = Registry.variables[SOURCE_PLASMA_PARTIAL_PRESSURE]
    gas_temperature = Registry.variables[SOURCE_PLASMA_GAS_TEMPERATURE]
    number_density = Registry.variables[SOURCE_PLASMA_NUMBER_DENSITY]
    closure = Registry.equations[SOURCE_PLASMA_IDEAL_GAS_CLOSURE]
    density_positive = Registry.equations[SOURCE_PLASMA_NUMBER_DENSITY_POSITIVE]

    assert number_density.kind is VariableKind.DERIVED
    assert not number_density.is_root_input
    assert number_density.sp_units == sp.Integer(1) / METER**3
    assert isinstance(closure, Approximation)
    assert closure.role is RelationRole.APPROXIMATION
    assert closure in number_density.defining_equations
    assert density_positive in number_density.constraints()
    assert getattr(closure, "_check_units_flag") is True
    assert number_density.direct_dependencies() == {
        partial_pressure,
        gas_temperature,
        BOLTZMANN,
    }
    assert closure.rhs == (
        partial_pressure.symbol / (BOLTZMANN.symbol * gas_temperature.symbol)
    )
    assert gt(partial_pressure.symbol, 0) in closure.validity.args
    assert gt(gas_temperature.symbol, 0) in closure.validity.args
    assert gt(BOLTZMANN.symbol, 0) in closure.validity.args


@pytest.mark.parametrize(
    "variable_name, equation_name",
    [
        (SOURCE_PLASMA_PARTIAL_PRESSURE, SOURCE_PLASMA_PARTIAL_PRESSURE_POSITIVE),
        (SOURCE_PLASMA_GAS_TEMPERATURE, SOURCE_PLASMA_GAS_TEMPERATURE_POSITIVE),
    ],
)
def test_source_plasma_species_zero_root_assignment_reports_strict_boundary(
    variable_name,
    equation_name,
):
    result = resolve(variable_name, assignments={variable_name: 0.0})

    assert float(result.value) == pytest.approx(0.0)
    _failed_constraint(result, equation_name)
    _failed_constraint(result, f"domain.{variable_name}.positive")


def test_source_plasma_species_ideal_gas_closure_resolves_without_defaults():
    partial_pressure = 2.0
    gas_temperature = 400.0

    result = resolve(
        SOURCE_PLASMA_NUMBER_DENSITY,
        assignments={
            SOURCE_PLASMA_PARTIAL_PRESSURE: partial_pressure,
            SOURCE_PLASMA_GAS_TEMPERATURE: gas_temperature,
        },
    )

    assert float(result.value) == pytest.approx(
        partial_pressure / (BOLTZMANN.value * gas_temperature)
    )
    assert [step.equation for step in result.trace] == [
        SOURCE_PLASMA_IDEAL_GAS_CLOSURE
    ]
    assert all(check.satisfied is True for check in result.approximation_validity)
    _satisfied_constraint(result, SOURCE_PLASMA_PARTIAL_PRESSURE_POSITIVE)
    _satisfied_constraint(result, SOURCE_PLASMA_GAS_TEMPERATURE_POSITIVE)
    _satisfied_constraint(result, SOURCE_PLASMA_NUMBER_DENSITY_POSITIVE)


def test_source_nucleon_roots_are_nonnegative_integer_boundaries():
    for variable_name in (SOURCE_PROTON_COUNT, SOURCE_NEUTRON_COUNT):
        variable = Registry.variables[variable_name]
        assert variable.is_root_input
        assert variable.assumptions["integer"] is True
        assert variable.assumptions["nonnegative"] is True
        assert "positive" not in variable.assumptions
        assert not hasattr(variable, "value")
        assert variable.value_range is None


def test_source_species_inventory_counts_are_domain_constrained_without_defaults():
    domain_cases = [
        (SOURCE_ATOMIC_NUMBER, "nonnegative"),
        (SOURCE_VALENCE_UP, "positive"),
        (SOURCE_VALENCE_DOWN, "positive"),
        (SOURCE_ISOTOPE_MASS_NUMBER, "positive"),
        (SOURCE_MASS_NUMBER, "positive"),
        (SOURCE_BOUND_ELECTRON_COUNT, "nonnegative"),
        (SOURCE_INNER_CLOSED_SHELL_ELECTRON_COUNT, "nonnegative"),
        (SOURCE_TRANSITION_SHELL_OCCUPANCY, "nonnegative"),
    ]

    for variable_name, sign_domain in domain_cases:
        variable = Registry.variables[variable_name]
        assert not variable.is_root_input
        assert variable.assumptions["integer"] is True
        assert variable.assumptions[sign_domain] is True
        assert not hasattr(variable, "value")
        assert variable.value_range is None

    assert Registry.variables[SOURCE_MASS_NUMBER].direct_dependencies() == {
        Registry.variables[SOURCE_ISOTOPE_MASS_NUMBER]
    }


@pytest.mark.parametrize(
    "variable_name, assignments",
    [
        (
            SOURCE_VALENCE_UP,
            {
                SOURCE_VALENCE_UP: 0,
                SOURCE_VALENCE_DOWN: 1,
            },
        ),
        (
            SOURCE_VALENCE_DOWN,
            {
                SOURCE_VALENCE_UP: 2,
                SOURCE_VALENCE_DOWN: 0,
            },
        ),
    ],
)
def test_source_valence_quark_zero_assignment_reports_named_domain(
    variable_name,
    assignments,
):
    result = resolve(variable_name, assignments=assignments)

    assert float(result.value) == pytest.approx(0.0)
    _failed_constraint(result, f"domain.{variable_name}.positive")
    _violated_constraint(result, f"domain.{variable_name}.positive")


def test_source_nucleon_fractional_assignment_reports_integer_diagnostic():
    result = resolve(
        SOURCE_VALENCE_UP,
        assignments={
            SOURCE_PROTON_COUNT: 2.5,
            SOURCE_NEUTRON_COUNT: 2,
        },
    )

    assert float(result.value) == pytest.approx(7.0)
    integer_violation = _violated_constraint(
        result,
        f"domain.{SOURCE_PROTON_COUNT}.integer",
    )
    assert integer_violation.variable == SOURCE_PROTON_COUNT
    assert float(integer_violation.inputs[SOURCE_PROTON_COUNT]) == pytest.approx(2.5)


def test_source_nucleon_invalid_compositions_report_count_diagnostics():
    negative_proton = resolve(
        SOURCE_PROTON_COUNT,
        assignments={
            SOURCE_PROTON_COUNT: -1,
            SOURCE_NEUTRON_COUNT: 1,
        },
    )
    assert float(negative_proton.value) == pytest.approx(-1.0)
    _violated_constraint(
        negative_proton,
        "physical.ineq.lithography_source_proton_count_positive",
    )
    _violated_constraint(
        negative_proton,
        f"domain.{SOURCE_PROTON_COUNT}.nonnegative",
    )

    zero_proton = resolve(
        SOURCE_VALENCE_UP,
        assignments={
            SOURCE_PROTON_COUNT: 0,
            SOURCE_NEUTRON_COUNT: 1,
        },
    )
    assert float(zero_proton.value) == pytest.approx(1.0)
    _violated_constraint(
        zero_proton,
        "physical.ineq.lithography_source_proton_count_positive",
    )


def test_source_mass_number_alias_reports_positive_integer_diagnostics():
    direct_zero = resolve(
        SOURCE_MASS_NUMBER,
        assignments={
            SOURCE_MASS_NUMBER: 0,
        },
    )
    assert float(direct_zero.value) == pytest.approx(0.0)
    mass_violation = _violated_constraint(
        direct_zero,
        f"domain.{SOURCE_MASS_NUMBER}.positive",
    )
    assert mass_violation.variable == SOURCE_MASS_NUMBER
    assert float(mass_violation.inputs[SOURCE_MASS_NUMBER]) == pytest.approx(0.0)

    isotope_zero = resolve(
        SOURCE_ISOTOPE_MASS_NUMBER,
        assignments={
            SOURCE_PROTON_COUNT: 0,
            SOURCE_NEUTRON_COUNT: 0,
        },
    )
    assert float(isotope_zero.value) == pytest.approx(0.0)
    _violated_constraint(
        isotope_zero,
        f"domain.{SOURCE_ISOTOPE_MASS_NUMBER}.positive",
    )


@pytest.mark.parametrize(
    "variable_name",
    [
        SOURCE_BOUND_ELECTRON_COUNT,
        SOURCE_INNER_CLOSED_SHELL_ELECTRON_COUNT,
        SOURCE_TRANSITION_SHELL_OCCUPANCY,
    ],
)
def test_source_electron_inventory_count_assignments_report_domain_diagnostics(
    variable_name,
):
    negative = resolve(variable_name, assignments={variable_name: -1})
    assert float(negative.value) == pytest.approx(-1.0)
    _violated_constraint(negative, f"domain.{variable_name}.nonnegative")

    fractional = resolve(variable_name, assignments={variable_name: 1.5})
    assert float(fractional.value) == pytest.approx(1.5)
    _violated_constraint(fractional, f"domain.{variable_name}.integer")


def test_source_nucleon_valid_one_proton_boundary_satisfies_domains():
    result = resolve(
        SOURCE_VALENCE_UP,
        assignments={
            SOURCE_PROTON_COUNT: 1,
            SOURCE_NEUTRON_COUNT: 0,
        },
    )

    assert float(result.value) == pytest.approx(2.0)
    assert [step.equation for step in result.trace] == [
        "physical.eq.lithography_source_valence_up_quark_count_from_zn"
    ]
    checks = {check.equation: check for check in result.constraints}
    assert checks[f"domain.{SOURCE_PROTON_COUNT}.nonnegative"].satisfied is True
    assert checks[f"domain.{SOURCE_NEUTRON_COUNT}.nonnegative"].satisfied is True
    assert checks[f"domain.{SOURCE_VALENCE_UP}.positive"].satisfied is True
    assert (
        checks["physical.ineq.lithography_source_proton_count_positive"].satisfied
        is True
    )
