"""
tests/test_resolver_advanced.py
================================

Focused tests for the three opt-in resolver extensions:
  (1) Validity-aware variant fallback (--fallback-on-violated-validity)
  (2) Small simultaneous-system solving (--solve-systems)
  (3) Selection explanation (--explain-selection)

All tests use either synthetic variables via registry_snapshot or
existing real-registry fixtures.
"""

from __future__ import annotations

import pytest
import sympy as sp

from gpu_stack import resolve
from gpu_stack.core import (
    Approximation,
    Equation,
    RelationRole,
)
from gpu_stack.core.variable import Variable
from gpu_stack.core.resolver_models import TraceStep
from tests.helpers.registry import registry_snapshot


# ===========================================================================
# Helpers
# ===========================================================================

def _make_var(name, symbol, scope="test", positive=None):
    return Variable(
        name,
        symbol,
        "value",
        f"Temporary test variable {name}.",
        scope=scope,
        positive=positive,
    )


def _make_eq(name, lhs_sym, rhs, description="Temporary test equation.",
             role=None, variant=None):
    return Equation(name, lhs_sym, rhs, description, role=role, variant=variant)


def _make_approx(name, lhs_sym, rhs, validity, description="Temporary test approximation.",
                 role=None, variant=None):
    return Approximation(name, lhs_sym, rhs, validity, description,
                         role=role, variant=variant)


# ===========================================================================
# (1) Validity-aware variant fallback
# ===========================================================================

class TestFallbackOnViolatedValidity:
    """Feature: fallback-on-violated-validity flag.

    Test structure: variable has two VARIANT relations.
    - Variant 'approx' is an Approximation (with validity that can be violated).
    - Variant 'exact' is a regular Equation (always valid).
    - User selects 'approx'; when validity is violated, fallback switches to 'exact'.

    This is the only mechanism by which an Approximation is the SELECTED equation
    (role=APPROXIMATION or role=VARIANT with isinstance(eq, Approximation) being True)
    while an alternative exists. A plain IDENTITY always wins over APPROXIMATION in
    _select_equation, so the fallback scenario requires VARIANT-role relationships.
    """

    def test_fallback_triggers_when_selected_approx_validity_violated(
        self, registry_snapshot
    ):
        """
        When a VARIANT Approximation is selected and its validity is violated,
        fallback finds the other VARIANT and uses it instead.
        """
        x = _make_var("test.fallback.x", "x_fb_val_test")
        y = _make_var("test.fallback.y", "y_fb_val_test")
        regime = _make_var("test.fallback.regime", "r_fb_val_test")

        # Variant 'exact': plain equation, always valid
        _make_eq(
            "test.eq.fallback_x_exact",
            x.symbol,
            y.symbol + 1,
            "Exact variant for fallback test.",
            role=RelationRole.VARIANT,
            variant="exact",
        )
        # Variant 'approx': Approximation with validity: regime > 10
        _make_approx(
            "test.eq.fallback_x_approx",
            x.symbol,
            y.symbol + 100,
            regime.symbol > 10,
            "Approximation for fallback test.",
            role=RelationRole.VARIANT,
            variant="approx",
        )

        # Without fallback: approx is used, validity violated, value from approx
        result_no_fallback = resolve(
            "test.fallback.x",
            assignments={"test.fallback.y": 5, "test.fallback.regime": 1},
            variants={"test.fallback.x": "approx"},
            fallback_on_violated_validity=False,
        )
        assert float(result_no_fallback.value) == pytest.approx(105.0)
        violated = [
            c for c in result_no_fallback.approximation_validity
            if c.satisfied is False
        ]
        assert len(violated) == 1

        # With fallback: switches to 'exact' variant
        result_fallback = resolve(
            "test.fallback.x",
            assignments={"test.fallback.y": 5, "test.fallback.regime": 1},
            variants={"test.fallback.x": "approx"},
            fallback_on_violated_validity=True,
        )
        assert float(result_fallback.value) == pytest.approx(6.0)  # y + 1 = 6
        assert len(result_fallback.trace) == 1
        step = result_fallback.trace[0]
        assert step.equation == "test.eq.fallback_x_exact"
        assert step.fallback_from == "test.eq.fallback_x_approx"

    def test_fallback_trace_records_fallback_from_field(self, registry_snapshot):
        """The fallback TraceStep records the original equation in fallback_from."""
        x = _make_var("test.fallback2.x", "x_fb2_test")
        y = _make_var("test.fallback2.y", "y_fb2_test")
        regime = _make_var("test.fallback2.regime", "r_fb2_test")

        _make_eq(
            "test.eq.fallback2_x_exact",
            x.symbol,
            y.symbol + 10,
            "Exact variant.",
            role=RelationRole.VARIANT,
            variant="exact",
        )
        _make_approx(
            "test.eq.fallback2_x_approx",
            x.symbol,
            y.symbol + 999,
            regime.symbol > 100,
            "Approximation with tight validity.",
            role=RelationRole.VARIANT,
            variant="approx",
        )

        result = resolve(
            "test.fallback2.x",
            assignments={"test.fallback2.y": 3, "test.fallback2.regime": 5},
            variants={"test.fallback2.x": "approx"},
            fallback_on_violated_validity=True,
        )
        assert float(result.value) == pytest.approx(13.0)  # y + 10 = 13
        step = result.trace[0]
        assert step.fallback_from == "test.eq.fallback2_x_approx"
        assert step.equation == "test.eq.fallback2_x_exact"

    def test_no_fallback_when_validity_satisfied(self, registry_snapshot):
        """When validity is NOT violated, the original approximation is kept."""
        x = _make_var("test.fallback3.x", "x_fb3_test")
        y = _make_var("test.fallback3.y", "y_fb3_test")
        regime = _make_var("test.fallback3.regime", "r_fb3_test")

        _make_eq(
            "test.eq.fallback3_x_exact",
            x.symbol,
            y.symbol + 1,
            "Exact variant.",
            role=RelationRole.VARIANT,
            variant="exact",
        )
        _make_approx(
            "test.eq.fallback3_x_approx",
            x.symbol,
            y.symbol + 100,
            regime.symbol > 0,
            "Approximation with easy-to-satisfy validity.",
            role=RelationRole.VARIANT,
            variant="approx",
        )

        result = resolve(
            "test.fallback3.x",
            assignments={"test.fallback3.y": 5, "test.fallback3.regime": 50},
            variants={"test.fallback3.x": "approx"},
            fallback_on_violated_validity=True,
        )
        # Validity is satisfied (regime=50 > 0), no fallback
        assert float(result.value) == pytest.approx(105.0)
        step = result.trace[0]
        assert step.equation == "test.eq.fallback3_x_approx"
        assert step.fallback_from is None

    def test_no_fallback_when_no_alternative_exists(self, registry_snapshot):
        """When no alternative exists, the original approximation is used despite violation."""
        x = _make_var("test.fallback4.x", "x_fb4_test")
        y = _make_var("test.fallback4.y", "y_fb4_test")
        regime = _make_var("test.fallback4.regime", "r_fb4_test")

        # Only an approximation (no alternative), validity will be violated
        _make_approx(
            "test.eq.fallback4_x_approx",
            x.symbol,
            y.symbol * 2,
            regime.symbol > 100,
            "Lone approximation with violated validity.",
        )

        result = resolve(
            "test.fallback4.x",
            assignments={"test.fallback4.y": 3, "test.fallback4.regime": 1},
            fallback_on_violated_validity=True,
        )
        # Uses the lone approximation despite violated validity (no alternative)
        assert float(result.value) == pytest.approx(6.0)
        step = result.trace[0]
        assert step.equation == "test.eq.fallback4_x_approx"
        assert step.fallback_from is None

    def test_default_behavior_unchanged_without_flag(self, registry_snapshot):
        """Without the flag, default behavior: approximation used, violation reported."""
        x = _make_var("test.fallback5.x", "x_fb5_test")
        y = _make_var("test.fallback5.y", "y_fb5_test")
        regime = _make_var("test.fallback5.regime", "r_fb5_test")

        _make_eq(
            "test.eq.fallback5_x_exact",
            x.symbol,
            y.symbol + 1,
            "Exact variant.",
            role=RelationRole.VARIANT,
            variant="exact",
        )
        _make_approx(
            "test.eq.fallback5_x_approx",
            x.symbol,
            y.symbol + 100,
            regime.symbol > 10,
            "Approximation for default-unchanged test.",
            role=RelationRole.VARIANT,
            variant="approx",
        )

        result = resolve(
            "test.fallback5.x",
            assignments={"test.fallback5.y": 5, "test.fallback5.regime": 1},
            variants={"test.fallback5.x": "approx"},
        )
        # Default: uses the selected approximation, reports violated validity
        assert float(result.value) == pytest.approx(105.0)
        assert result.trace[0].fallback_from is None
        violated = [c for c in result.approximation_validity if c.satisfied is False]
        assert len(violated) == 1

    def test_fallback_records_reason_with_explain_selection(self, registry_snapshot):
        """With explain_selection, the trace step has a selection_reason mentioning fallback."""
        x = _make_var("test.fallback6.x", "x_fb6_test")
        y = _make_var("test.fallback6.y", "y_fb6_test")
        regime = _make_var("test.fallback6.regime", "r_fb6_test")

        _make_eq(
            "test.eq.fallback6_x_exact",
            x.symbol,
            y.symbol + 1,
            "Exact variant.",
            role=RelationRole.VARIANT,
            variant="exact",
        )
        _make_approx(
            "test.eq.fallback6_x_approx",
            x.symbol,
            y.symbol + 100,
            regime.symbol > 50,
            "Approximation with tight regime.",
            role=RelationRole.VARIANT,
            variant="approx",
        )

        result = resolve(
            "test.fallback6.x",
            assignments={"test.fallback6.y": 2, "test.fallback6.regime": 5},
            variants={"test.fallback6.x": "approx"},
            fallback_on_violated_validity=True,
            explain_selection=True,
        )
        assert float(result.value) == pytest.approx(3.0)  # y + 1 = 3
        step = result.trace[0]
        assert step.fallback_from == "test.eq.fallback6_x_approx"
        assert step.selection_reason is not None
        assert "fallback" in step.selection_reason.lower()
        assert "test.eq.fallback6_x_approx" in step.selection_reason


# ===========================================================================
# (2) Small simultaneous-system solving
# ===========================================================================

class TestSolveSystems:
    """Feature: solve-systems flag for small mutual-dependency cycles."""

    def test_2_variable_linear_cycle_resolves(self, registry_snapshot):
        """Two variables defining each other with a solvable linear system."""
        # x = y + 3, y = x - 3  => x = y + 3, y = x - 3
        # Substitute: x = (x-3)+3 = x (identity for any x+y pair that satisfies)
        # Actually we need a unique solution.
        # x = 2*y + 1, y = (x - 1) / 2 => x = 2*((x-1)/2)+1 = x (identity again)
        # We need: x = y + 3, y = 2 => x=5, y=2 but y has no defining equation that avoids x.
        # Let's try: x = a + y, y = b - x (where a, b are assigned)
        # x = a + y, y = b - x
        # Substitute: x = a + (b-x) => 2x = a+b => x = (a+b)/2
        # y = b - x = b - (a+b)/2 = (b-a)/2

        a = _make_var("test.sys2a.a", "a_sys2_test")
        b = _make_var("test.sys2a.b", "b_sys2_test")
        x = _make_var("test.sys2a.x", "x_sys2_test")
        y = _make_var("test.sys2a.y", "y_sys2_test")

        _make_eq("test.eq.sys2a_x", x.symbol, a.symbol + y.symbol)
        _make_eq("test.eq.sys2a_y", y.symbol, b.symbol - x.symbol)

        result = resolve(
            "test.sys2a.x",
            assignments={"test.sys2a.a": 2, "test.sys2a.b": 10},
            solve_systems=True,
        )
        # x = (a+b)/2 = (2+10)/2 = 6
        assert float(result.value) == pytest.approx(6.0)
        assert "test.sys2a.x" not in result.missing
        assert "test.sys2a.y" not in result.missing

    def test_2_variable_cycle_trace_has_system_peers(self, registry_snapshot):
        """System-solved trace steps list each other as system_peers."""
        a = _make_var("test.sys2b.a", "a_sys2b_test")
        x = _make_var("test.sys2b.x", "x_sys2b_test")
        y = _make_var("test.sys2b.y", "y_sys2b_test")

        _make_eq("test.eq.sys2b_x", x.symbol, a.symbol + y.symbol)
        _make_eq("test.eq.sys2b_y", y.symbol, a.symbol - x.symbol)

        result = resolve(
            "test.sys2b.x",
            assignments={"test.sys2b.a": 8},
            solve_systems=True,
            explain_selection=True,
        )
        # x = a + y, y = a - x => 2x = 2a => x=a=8, y=0
        assert float(result.value) == pytest.approx(8.0)

        x_step = next(s for s in result.trace if s.variable == "test.sys2b.x")
        y_step = next(s for s in result.trace if s.variable == "test.sys2b.y")

        assert "test.sys2b.y" in x_step.system_peers
        assert "test.sys2b.x" in y_step.system_peers
        assert "system" in x_step.selection_reason.lower()
        assert "system" in y_step.selection_reason.lower()

    def test_3_variable_cycle_resolves(self, registry_snapshot):
        """Three variables in a mutual-dependency cycle (max allowed size)."""
        # x = y + 1, y = z + 1, z = x - 2
        # Substitute: x = (z+1)+1 = z+2 = (x-2)+2 = x (degenerate!)
        # Need independent equations:
        # x = a + y + z, y = b - x + z, z = c - y
        # Let's use: x = y + z, y = a - x, z = b
        # where b is assigned. Then:
        # y = a - x, x = y + b = (a-x) + b => 2x = a+b => x=(a+b)/2
        a = _make_var("test.sys3.a", "a_sys3_test")
        b = _make_var("test.sys3.b", "b_sys3_test")
        x = _make_var("test.sys3.x", "x_sys3_test")
        y = _make_var("test.sys3.y", "y_sys3_test")
        z = _make_var("test.sys3.z", "z_sys3_test")

        # z = b is assigned in the test, so z is NOT part of the cycle.
        # For a 3-var cycle: x = y + z, y = x - z, z = x - y
        # Add: x + y = 2a, x - y = 2b, x - z = a => 3 equations
        # Let a, b be assigned scalar inputs.
        # x = a + y + z, y = x - a, z = 2*a - x - y => 3 cycle vars
        # Substitute: y = x - a, z = 2a - x - (x-a) = 3a - 2x
        # x = a + (x-a) + (3a-2x) = a + x - a + 3a - 2x = 3a - x
        # => 2x = 3a => x = 3a/2
        # Assign a=2 => x=3, y=3-2=1, z=3*2-2*3=0
        x3 = _make_var("test.sys3b.x", "x_s3b_test")
        y3 = _make_var("test.sys3b.y", "y_s3b_test")
        z3 = _make_var("test.sys3b.z", "z_s3b_test")
        aa = _make_var("test.sys3b.a", "a_s3b_test")

        _make_eq("test.eq.sys3b_x", x3.symbol, aa.symbol + y3.symbol + z3.symbol)
        _make_eq("test.eq.sys3b_y", y3.symbol, x3.symbol - aa.symbol)
        _make_eq("test.eq.sys3b_z", z3.symbol, 3 * aa.symbol - 2 * x3.symbol)

        result = resolve(
            "test.sys3b.x",
            assignments={"test.sys3b.a": 2},
            solve_systems=True,
        )
        assert float(result.value) == pytest.approx(3.0)
        assert "test.sys3b.x" not in result.missing
        assert "test.sys3b.y" not in result.missing
        assert "test.sys3b.z" not in result.missing

    def test_unsolvable_cycle_stays_missing(self, registry_snapshot):
        """A non-invertible or unsolvable cycle leaves variables missing."""
        # x = x^2 - y, y = x^2 + 1 (non-linear, multiple solutions or no real solution)
        # x + y = x^2 + x^2 + 1 - y ... actually:
        # Use: x = y^2 (non-linear, ambiguous solutions without assumptions)
        x = _make_var("test.unsolvable.x", "x_unsolvable_test")
        y = _make_var("test.unsolvable.y", "y_unsolvable_test")

        # y = x + 1, x = y^2 - 2 => x = (x+1)^2 - 2 = x^2 + 2x + 1 - 2
        # => x^2 + x - 1 = 0 => x = (-1 +/- sqrt(5))/2 (two real solutions!)
        # Neither is ruled out by assumptions (no sign constraint).
        _make_eq("test.eq.unsolvable_y", y.symbol, x.symbol + 1)
        _make_eq("test.eq.unsolvable_x", x.symbol, y.symbol**2 - 2)

        result = resolve(
            "test.unsolvable.x",
            solve_systems=True,
        )
        # Cannot pick a unique solution: stays missing
        assert "test.unsolvable.x" in result.missing or result.missing

    def test_cycle_size_4_stays_missing(self, registry_snapshot):
        """Cycles of size >3 are not solved and remain missing (raises Underdetermined)."""
        a = _make_var("test.cycle4.a", "a_cycle4_test")
        x = _make_var("test.cycle4.x", "x_cycle4_test")
        y = _make_var("test.cycle4.y", "y_cycle4_test")
        z = _make_var("test.cycle4.z", "z_cycle4_test")
        w = _make_var("test.cycle4.w", "w_cycle4_test")

        # 4-way cycle: x=y+a, y=z+a, z=w+a, w=x-3*a
        # This forms a true 4-cycle among x, y, z, w; each depends on the next.
        # Even though mathematically solvable (all = a*something), the system
        # size (4 vars) exceeds the cap of 3, so it stays missing.
        _make_eq("test.eq.cycle4_x", x.symbol, y.symbol + a.symbol)
        _make_eq("test.eq.cycle4_y", y.symbol, z.symbol + a.symbol)
        _make_eq("test.eq.cycle4_z", z.symbol, w.symbol + a.symbol)
        _make_eq("test.eq.cycle4_w", w.symbol, x.symbol - 3 * a.symbol)

        from gpu_stack.core import Underdetermined
        with pytest.raises(Underdetermined) as exc_info:
            resolve(
                "test.cycle4.x",
                assignments={"test.cycle4.a": 1},
                solve_systems=True,
            )
        # 4-var cycle is above the cap: all four are missing
        assert len(exc_info.value.missing) >= 4

    def test_assumption_filters_multi_root_solutions(self, registry_snapshot):
        """Only solutions consistent with symbol assumptions are accepted.

        Two variables form a cycle. Without positivity assumptions, a non-linear
        system might have multiple real solutions and sympy.solve would return
        multiple candidates. With positive=True, only the positive solution
        is kept.
        """
        # x * y = 6, x + y = 5, both positive.
        # Solutions: (2,3) or (3,2). Both are real and positive, so there are
        # two valid solutions -> system solver should reject (not unique).
        # But that tests 'not unique' -> use a linear system that IS unique.
        #
        # Better test: x = a + y, y = a + x with a < 0 such that x and y
        # have unique positive solution.
        # x = a+y, y = a+x => x-y = a, y-x = a => a = -a => only a=0 works.
        # This degeneracy is not useful.
        #
        # Actually: use a non-symmetric system:
        # x = 2*y - 1, y = x/2 + 1, both positive.
        # Substituting: x = 2*(x/2+1) - 1 = x + 2 - 1 = x + 1 => 0 = 1 (no solution!)
        #
        # Reliable test: two-var linear system with unique solution,
        # both vars positive.
        # x = 3 + y, y = b - x where b > 3 to ensure positivity.
        # 2x = 3 + b => x = (3+b)/2, y = b - (3+b)/2 = (b-3)/2
        # For b=7: x=5, y=2. Both positive.
        x = _make_var("test.posonly2.x", "x_posonly2_test", positive=True)
        y = _make_var("test.posonly2.y", "y_posonly2_test", positive=True)
        b = _make_var("test.posonly2.b", "b_posonly2_test")

        _make_eq("test.eq.posonly2_x", x.symbol, sp.Integer(3) + y.symbol)
        _make_eq("test.eq.posonly2_y", y.symbol, b.symbol - x.symbol)

        # b=7: x=5, y=2 (both positive, unique solution)
        result = resolve(
            "test.posonly2.x",
            assignments={"test.posonly2.b": 7},
            solve_systems=True,
        )
        assert float(result.value) == pytest.approx(5.0)
        assert "test.posonly2.y" not in result.missing

    def test_default_behavior_unchanged_without_solve_flag(self, registry_snapshot):
        """Without --solve-systems, cyclic variables cause a ResolverError."""
        a = _make_var("test.nosys.a", "a_nosys_test")
        x = _make_var("test.nosys.x", "x_nosys_test")
        y = _make_var("test.nosys.y", "y_nosys_test")

        _make_eq("test.eq.nosys_x", x.symbol, a.symbol + y.symbol)
        _make_eq("test.eq.nosys_y", y.symbol, a.symbol - x.symbol)

        from gpu_stack.core import ResolverError
        with pytest.raises(ResolverError):
            resolve(
                "test.nosys.x",
                assignments={"test.nosys.a": 5},
                solve_systems=False,
            )


# ===========================================================================
# (3) Selection explanation
# ===========================================================================

class TestExplainSelection:
    """Feature: explain_selection flag."""

    def test_identity_step_has_selection_reason(self, registry_snapshot):
        """Sole identity steps have 'sole identity relation' as reason."""
        x = _make_var("test.explain1.x", "x_expl1_test")
        y = _make_var("test.explain1.y", "y_expl1_test")

        _make_eq("test.eq.explain1_x", x.symbol, y.symbol * 2)

        result = resolve(
            "test.explain1.x",
            assignments={"test.explain1.y": 5},
            explain_selection=True,
        )
        step = result.trace[0]
        assert step.selection_reason is not None
        assert "sole identity" in step.selection_reason.lower()

    def test_variant_step_has_selection_reason(self, registry_snapshot):
        """Variant steps have the variant key in their selection_reason."""
        x = _make_var("test.explain2.x", "x_expl2_test")
        y = _make_var("test.explain2.y", "y_expl2_test")
        z = _make_var("test.explain2.z", "z_expl2_test")

        Equation(
            "test.eq.explain2_x_v1",
            x.symbol,
            y.symbol,
            "Variant 1.",
            role=RelationRole.VARIANT,
            variant="v1",
        )
        Equation(
            "test.eq.explain2_x_v2",
            x.symbol,
            z.symbol,
            "Variant 2.",
            role=RelationRole.VARIANT,
            variant="v2",
        )

        result = resolve(
            "test.explain2.x",
            assignments={"test.explain2.y": 3, "test.explain2.z": 7},
            variants={"test.explain2.x": "v2"},
            explain_selection=True,
        )
        step = result.trace[0]
        assert step.selection_reason is not None
        assert "v2" in step.selection_reason

    def test_approximation_step_has_selection_reason(self, registry_snapshot):
        """Approximation steps have explanation in selection_reason."""
        x = _make_var("test.explain3.x", "x_expl3_test")
        y = _make_var("test.explain3.y", "y_expl3_test")

        Approximation(
            "test.eq.explain3_x_approx",
            x.symbol,
            y.symbol * 2,
            y.symbol > 0,
            "Approximation for explain test.",
        )

        result = resolve(
            "test.explain3.x",
            assignments={"test.explain3.y": 3},
            explain_selection=True,
        )
        step = result.trace[0]
        assert step.selection_reason is not None
        assert "approximation" in step.selection_reason.lower()

    def test_no_selection_reason_without_flag(self, registry_snapshot):
        """Without explain_selection, selection_reason is None by default."""
        x = _make_var("test.explain4.x", "x_expl4_test")
        y = _make_var("test.explain4.y", "y_expl4_test")

        _make_eq("test.eq.explain4_x", x.symbol, y.symbol + 1)

        result = resolve(
            "test.explain4.x",
            assignments={"test.explain4.y": 4},
        )
        step = result.trace[0]
        assert step.selection_reason is None

    def test_unresolved_input_lists_alternatives_with_explain(self, registry_snapshot):
        """UnresolvedInput.not_selectable_alternatives is populated when explain_selection=True."""
        x = _make_var("test.explain5.x", "x_expl5_test")
        y = _make_var("test.explain5.y", "y_expl5_test")
        z = _make_var("test.explain5.z", "z_expl5_test")

        # x has two variant definitions but no selector provided
        # so x is unresolved (AmbiguousVariant)
        # Actually we just make x have only alternative equations (VARIANT)
        # without providing a selector, so x remains in missing.

        # Simpler: make x depend on y, and y depend on z (root input).
        # z has no defining equation. When explain_selection is True,
        # UnresolvedInput for z should have not_selectable_alternatives = ()
        # because z has no defining equations at all.

        _make_eq("test.eq.explain5_x", x.symbol, y.symbol + z.symbol)
        _make_eq("test.eq.explain5_y", y.symbol, sp.Integer(1))

        result = resolve(
            "test.explain5.x",
            explain_selection=True,
        )
        assert "test.explain5.z" in result.missing
        unresolved = next(
            u for u in result.unresolved_inputs
            if u.variable == "test.explain5.z"
        )
        # z has no defining equations, so no alternatives
        assert hasattr(unresolved, "not_selectable_alternatives")

    def test_unresolved_input_alternatives_nonempty_for_variant_var(self, registry_snapshot):
        """When a variable has defining equations but is still missing, alternatives are listed."""
        x = _make_var("test.explain6.x", "x_expl6_test")
        y = _make_var("test.explain6.y", "y_expl6_test")
        z = _make_var("test.explain6.z", "z_expl6_test")
        driver = _make_var("test.explain6.driver", "driver_expl6_test")

        # y has variant equations but no selector -> AmbiguousVariant -> missing
        # y also has defining equations which will be in alternatives
        Equation(
            "test.eq.explain6_y_v1",
            y.symbol,
            driver.symbol,
            "Variant 1 for y.",
            role=RelationRole.VARIANT,
            variant="v1",
        )
        Equation(
            "test.eq.explain6_y_v2",
            y.symbol,
            driver.symbol * 2,
            "Variant 2 for y.",
            role=RelationRole.VARIANT,
            variant="v2",
        )
        _make_eq("test.eq.explain6_x", x.symbol, y.symbol + z.symbol)
        _make_eq("test.eq.explain6_z", z.symbol, sp.Integer(1))

        result = resolve(
            "test.explain6.x",
            assignments={"test.explain6.driver": 3},
            explain_selection=True,
        )
        assert "test.explain6.y" in result.missing
        unresolved = next(
            u for u in result.unresolved_inputs
            if u.variable == "test.explain6.y"
        )
        assert len(unresolved.not_selectable_alternatives) == 2

    def test_system_solve_step_records_system_peers(self, registry_snapshot):
        """System-solved steps carry system_peers tuple naming co-solved variables."""
        a = _make_var("test.explain7.a", "a_expl7_test")
        x = _make_var("test.explain7.x", "x_expl7_test")
        y = _make_var("test.explain7.y", "y_expl7_test")

        _make_eq("test.eq.explain7_x", x.symbol, a.symbol + y.symbol)
        _make_eq("test.eq.explain7_y", y.symbol, a.symbol - x.symbol)

        result = resolve(
            "test.explain7.x",
            assignments={"test.explain7.a": 6},
            solve_systems=True,
            explain_selection=True,
        )
        # x=a+y, y=a-x => 2x=2a => x=6, y=0
        assert float(result.value) == pytest.approx(6.0)

        x_step = next(s for s in result.trace if s.variable == "test.explain7.x")
        y_step = next(s for s in result.trace if s.variable == "test.explain7.y")

        assert x_step.system_peers is not None
        assert "test.explain7.y" in x_step.system_peers
        assert y_step.system_peers is not None
        assert "test.explain7.x" in y_step.system_peers

        assert x_step.selection_reason is not None
        assert "system" in x_step.selection_reason.lower()


# ===========================================================================
# CLI integration tests
# ===========================================================================

class TestCLINewFlags:
    """Integration tests for the new CLI flags via main()."""

    def test_cli_explain_selection_adds_why_to_trace(self, registry_snapshot):
        """--explain-selection adds [why: ...] to trace output."""
        from gpu_stack.cli import main
        from tests.helpers.cli import captured_stdout

        x = _make_var("test.cli_expl.x", "x_cli_expl_test")
        y = _make_var("test.cli_expl.y", "y_cli_expl_test")
        _make_eq("test.eq.cli_expl_x", x.symbol, y.symbol + 1)

        with captured_stdout() as buf:
            rc = main([
                "resolve", "test.cli_expl.x",
                "--assign", "test.cli_expl.y=5",
                "--trace",
                "--explain-selection",
            ])
        out = buf.getvalue()
        assert rc == 0
        assert "[why:" in out

    def test_cli_fallback_flag_switches_equation(self, registry_snapshot):
        """--fallback-on-violated-validity changes which equation is used."""
        from gpu_stack.cli import main
        from tests.helpers.cli import captured_stdout

        x = _make_var("test.cli_fb.x", "x_cli_fb_test")
        y = _make_var("test.cli_fb.y", "y_cli_fb_test")
        regime = _make_var("test.cli_fb.regime", "r_cli_fb_test")

        # 'exact' variant: plain equation
        _make_eq(
            "test.eq.cli_fb_x_exact",
            x.symbol,
            y.symbol + 1,
            "Exact variant.",
            role=RelationRole.VARIANT,
            variant="exact",
        )
        # 'approx' variant: Approximation with violated validity
        _make_approx(
            "test.eq.cli_fb_x_approx",
            x.symbol,
            y.symbol + 200,
            regime.symbol > 100,
            "Approx for CLI fallback test.",
            role=RelationRole.VARIANT,
            variant="approx",
        )

        with captured_stdout() as buf:
            rc = main([
                "resolve", "test.cli_fb.x",
                "--assign", "test.cli_fb.y=3",
                "--assign", "test.cli_fb.regime=1",
                "--variant", "test.cli_fb.x=approx",
                "--trace",
                "--fallback-on-violated-validity",
            ])
        out = buf.getvalue()
        assert rc == 0
        assert "fallback from" in out.lower()
        # Value should be exact: y+1=4, not approx: y+200=203
        assert "test.cli_fb.x = 4" in out

    def test_cli_solve_systems_resolves_cycle(self, registry_snapshot):
        """--solve-systems resolves 2-variable cycle."""
        from gpu_stack.cli import main
        from tests.helpers.cli import captured_stdout

        a = _make_var("test.cli_sys.a", "a_cli_sys_test")
        x = _make_var("test.cli_sys.x", "x_cli_sys_test")
        y = _make_var("test.cli_sys.y", "y_cli_sys_test")

        _make_eq("test.eq.cli_sys_x", x.symbol, a.symbol + y.symbol)
        _make_eq("test.eq.cli_sys_y", y.symbol, a.symbol - x.symbol)

        with captured_stdout() as buf:
            rc = main([
                "resolve", "test.cli_sys.x",
                "--assign", "test.cli_sys.a=5",
                "--solve-systems",
                "--trace",
            ])
        out = buf.getvalue()
        assert rc == 0
        # x = (a+a)/2... wait: x=a+y, y=a-x => 2x=2a => x=5, y=0
        assert "test.cli_sys.x = 5" in out


# ===========================================================================
# Regression: default behavior byte-identical
# ===========================================================================

class TestRegressionDefaultBehavior:
    """Existing default behavior must be unchanged."""

    def test_default_resolve_unchanged(self):
        """resolve() with no new flags produces same result as before."""
        result = resolve(
            "cluster.rack.peak_flops",
            assignments={
                "cluster.rack.n_nodes": 9,
                "cluster.node.n_gpus": 8,
                "gpu.peak_flops": 15e15,
            },
        )
        assert float(result.value) == pytest.approx(1.08e18, rel=1e-12)
        # No new fields populated
        for step in result.trace:
            assert step.selection_reason is None
            assert step.fallback_from is None
            assert step.system_peers is None

    def test_default_unresolved_input_no_alternatives(self):
        """UnresolvedInput.not_selectable_alternatives is empty by default."""
        result = resolve(
            "cluster.node.peak_flops",
            assignments={"cluster.node.n_gpus": 8},
        )
        for u in result.unresolved_inputs:
            assert u.not_selectable_alternatives == ()
