"""
tests/test_lithography_medium_composition_formula_constraints.py
================================================================

A formula unit is the smallest repeating recipe of the imaging medium: so
many atoms of component a, so many of component b. Not every recipe is
physically possible, so the graph attaches inequality constraints to the
formula-unit variables. This module verifies that those constraints exist as
real Inequality objects with the right operator and right-hand side, and that
they actually fire: each stoichiometric count must be at least 1, the packing
fill factor at most 1, the packing length scale factor at least 1, and the
number of electrons transferred between components can never exceed either
component's total electron inventory (stoichiometric count times proton
count). For each rule we resolve once with a legal value and once with an
illegal one, and confirm the constraint check flips from satisfied to
violated.
"""

import sympy as sp

from gpu_stack import Inequality, Registry, RelationRole, resolve
from tests.helpers.lithography import medium_component_quark_assignments


def test_lithography_medium_formula_unit_feasibility_constraints():
    packing_length_scale_factor_constraint = Registry.equations[
        "physical.ineq.lithography_medium_formula_unit_packing_length_scale_factor_at_least_unity"
    ]
    packing_length_scale_factor = Registry.variables[
        "physical.lithography.medium_formula_unit_packing_length_scale_factor"
    ]

    assert isinstance(packing_length_scale_factor_constraint, Inequality)
    assert packing_length_scale_factor_constraint.role is RelationRole.CONSTRAINT
    assert packing_length_scale_factor_constraint in packing_length_scale_factor.constraints()
    assert packing_length_scale_factor_constraint.op == ">="
    assert packing_length_scale_factor_constraint.rhs == sp.Integer(1)
    assert packing_length_scale_factor_constraint.references
    assert getattr(packing_length_scale_factor_constraint, "_check_units_flag", False)
    assert isinstance(packing_length_scale_factor_constraint.as_sympy(), sp.Rel)
    assert not packing_length_scale_factor_constraint.is_trivially_true()

    constraint_cases = [
        (
            "physical.lithography.medium_component_a_stoichiometric_count",
            "physical.ineq.lithography_medium_component_a_stoichiometric_count_at_least_one",
            ">=",
            1,
            0,
        ),
        (
            "physical.lithography.medium_component_b_stoichiometric_count",
            "physical.ineq.lithography_medium_component_b_stoichiometric_count_at_least_one",
            ">=",
            1,
            0,
        ),
        (
            "physical.lithography.medium_formula_unit_packing_fill_factor",
            "physical.ineq.lithography_medium_formula_unit_packing_fill_factor_at_most_unity",
            "<=",
            1,
            1.25,
        ),
    ]

    for variable_name, equation_name, op, valid_value, invalid_value in constraint_cases:
        variable = Registry.variables[variable_name]
        relation = Registry.equations[equation_name]
        assert isinstance(relation, Inequality)
        assert relation.role is RelationRole.CONSTRAINT
        assert relation in variable.constraints()
        assert relation.op == op
        assert relation.rhs == sp.Integer(1)
        assert relation.references
        assert getattr(relation, "_check_units_flag", False)
        assert isinstance(relation.as_sympy(), sp.Rel)
        assert not relation.is_trivially_true()

        valid_result = resolve(variable_name, assignments={variable_name: valid_value})
        valid_check = next(
            c for c in valid_result.constraints if c.equation == equation_name
        )
        assert valid_check.satisfied is True

        invalid_result = resolve(
            variable_name,
            assignments={variable_name: invalid_value},
        )
        invalid_check = next(
            c for c in invalid_result.constraints if c.equation == equation_name
        )
        assert invalid_check.satisfied is False

    transfer_count = Registry.variables[
        "physical.lithography.medium_formula_unit_intercomponent_charge_transfer_electron_count"
    ]
    component_a_stoich = Registry.variables[
        "physical.lithography.medium_component_a_stoichiometric_count"
    ]
    component_b_stoich = Registry.variables[
        "physical.lithography.medium_component_b_stoichiometric_count"
    ]
    component_a_protons = Registry.variables[
        "physical.lithography.medium_component_a_proton_count"
    ]
    component_b_protons = Registry.variables[
        "physical.lithography.medium_component_b_proton_count"
    ]
    transfer_constraints = [
        (
            "physical.ineq.lithography_medium_formula_unit_intercomponent_charge_transfer_at_most_component_a_electron_inventory",
            component_a_stoich.symbol * component_a_protons.symbol,
        ),
        (
            "physical.ineq.lithography_medium_formula_unit_intercomponent_charge_transfer_at_most_component_b_electron_inventory",
            component_b_stoich.symbol * component_b_protons.symbol,
        ),
    ]
    assert [eq.name for eq in transfer_count.constraints()] == [
        name for name, _rhs in transfer_constraints
    ]
    for equation_name, rhs in transfer_constraints:
        relation = Registry.equations[equation_name]
        assert isinstance(relation, Inequality)
        assert relation.role is RelationRole.CONSTRAINT
        assert relation in transfer_count.constraints()
        assert relation.op == "<="
        assert relation.rhs == rhs
        assert relation.references
        assert getattr(relation, "_check_units_flag", False)
        assert isinstance(relation.as_sympy(), sp.Rel)
        assert not relation.is_trivially_true()

    valid_transfer_assignments = {
        "physical.lithography.medium_component_a_stoichiometric_count": 2,
        **medium_component_quark_assignments("a", 1, 0),
        "physical.lithography.medium_component_b_stoichiometric_count": 1,
        **medium_component_quark_assignments("b", 8, 9),
        "physical.lithography.medium_formula_unit_intercomponent_charge_transfer_electron_count": 2,
    }
    valid_transfer_result = resolve(
        transfer_count.name,
        assignments=valid_transfer_assignments,
    )
    for equation_name, _rhs in transfer_constraints:
        check = next(
            c for c in valid_transfer_result.constraints if c.equation == equation_name
        )
        assert check.satisfied is True

    invalid_transfer_assignments = dict(valid_transfer_assignments)
    invalid_transfer_assignments[transfer_count.name] = 3
    invalid_transfer_result = resolve(
        transfer_count.name,
        assignments=invalid_transfer_assignments,
    )
    component_a_inventory_check = next(
        c
        for c in invalid_transfer_result.constraints
        if c.equation == transfer_constraints[0][0]
    )
    component_b_inventory_check = next(
        c
        for c in invalid_transfer_result.constraints
        if c.equation == transfer_constraints[1][0]
    )
    assert component_a_inventory_check.satisfied is False
    assert component_b_inventory_check.satisfied is True

    invalid_component_a_formula_result = resolve(
        "physical.lithography.medium_formula_unit_proton_count",
        assignments={
            "physical.lithography.medium_component_a_stoichiometric_count": 0,
            **medium_component_quark_assignments("a", 1, 0),
            "physical.lithography.medium_component_b_stoichiometric_count": 1,
            **medium_component_quark_assignments("b", 8, 9),
        },
    )
    component_a_formula_check = next(
        c for c in invalid_component_a_formula_result.constraints
        if c.equation
        == "physical.ineq.lithography_medium_component_a_stoichiometric_count_at_least_one"
    )
    assert component_a_formula_check.satisfied is False

    invalid_component_b_formula_result = resolve(
        "physical.lithography.medium_formula_unit_proton_count",
        assignments={
            "physical.lithography.medium_component_a_stoichiometric_count": 1,
            **medium_component_quark_assignments("a", 1, 0),
            "physical.lithography.medium_component_b_stoichiometric_count": 0,
            **medium_component_quark_assignments("b", 8, 9),
        },
    )
    component_b_formula_check = next(
        c for c in invalid_component_b_formula_result.constraints
        if c.equation
        == "physical.ineq.lithography_medium_component_b_stoichiometric_count_at_least_one"
    )
    assert component_b_formula_check.satisfied is False
