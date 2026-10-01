"""Unit SCALE checks: seconds are not milliseconds, kWh is not watt-seconds.

Variable values are numbers in their display unit, so `sp_units` must carry
the display unit's scale. The checker compares scale as well as dimension. A
numeric literal can bridge two scales (a conversion), but equal-dimension
quantities of different scale cannot be added or equated without one.
"""

import re

import pytest
import sympy as sp
from sympy.physics.units import (
    giga, liter, mega, micro, milli, nano, tonne,
)

from gpu_stack import Registry
from gpu_stack.core import Equation, UnitError, infer_expr_units, var
from gpu_stack.core import units as U
from gpu_stack.core.units import (
    GIGABYTE, KILOWATT, KWH, MONTH, SECOND, WATT, byte, bit,
    check_dimensional_consistency, undecided_unit_checks, unit_scale,
)
from tests.helpers.registry import registry_snapshot  # noqa: F401  (fixture)

MS = milli * SECOND
USD = sp.Symbol("USD_unit", positive=True)


def _mk(name, units, sp_units):
    return var(
        f"test.scale.{name}", f"test_scale_{name}", units,
        f"Temporary scale-check variable {name}.",
        scope="test", sp_units=sp_units,
    )


def test_unit_scale_of_common_display_units():
    assert unit_scale(MS) / unit_scale(SECOND) == sp.Rational(1, 1000)
    assert unit_scale(KWH) / unit_scale(WATT * SECOND) == 3_600_000
    assert unit_scale(KILOWATT) / unit_scale(WATT) == 1000
    assert unit_scale(MONTH) / unit_scale(SECOND) == 2_592_000
    assert unit_scale(GIGABYTE) / unit_scale(byte) == 10**9
    assert unit_scale(USD / KWH) == unit_scale(USD / (WATT * SECOND)) / 3_600_000


def test_adding_milliseconds_to_seconds_is_caught():
    t_s, t_ms = sp.symbols("t_s t_ms")
    with pytest.raises(UnitError, match="scale"):
        infer_expr_units(t_s + t_ms, {t_s: SECOND, t_ms: MS}, "test.add")


def test_milliseconds_converted_to_seconds_by_literal_passes():
    t_s, t_ms = sp.symbols("t_s t_ms")
    lookup = {t_s: SECOND, t_ms: MS}
    assert infer_expr_units(t_s + t_ms / 1000, lookup, "test.add") == SECOND


def test_equation_ms_vs_s_without_conversion_is_caught(registry_snapshot):
    t_s = _mk("ms_s.t_s", "s", SECOND)
    t_ms = _mk("ms_s.t_ms", "ms", MS)
    with pytest.raises(UnitError, match="scale"):
        Equation(
            "test.scale.eq.ms_as_s", t_s.symbol, t_ms.symbol,
            "Seconds set equal to milliseconds.", check_units=True,
        )
    assert "test.scale.eq.ms_as_s" not in Registry.equations


def test_equation_ms_vs_s_with_wrong_conversion_is_caught(registry_snapshot):
    t_s = _mk("ms_s2.t_s", "s", SECOND)
    t_ms = _mk("ms_s2.t_ms", "ms", MS)
    with pytest.raises(UnitError, match="scale"):
        Equation(
            "test.scale.eq.ms_times_1000", t_s.symbol, t_ms.symbol * 1000,
            "Conversion applied in the wrong direction.", check_units=True,
        )


def test_equation_ms_vs_s_with_correct_conversion_passes(registry_snapshot):
    t_s = _mk("ms_s3.t_s", "s", SECOND)
    t_ms = _mk("ms_s3.t_ms", "ms", MS)
    Equation(
        "test.scale.eq.ms_to_s", t_s.symbol, t_ms.symbol / 1000,
        "Milliseconds to seconds.", check_units=True,
    )


def test_equation_kwh_price_vs_watt_second_price(registry_snapshot):
    p_kwh = _mk("kwh.p_kwh", "USD/kWh", USD / KWH)
    p_ws = _mk("kwh.p_ws", "USD/(W*s)", USD / (WATT * SECOND))
    with pytest.raises(UnitError, match="scale"):
        Equation(
            "test.scale.eq.kwh_as_ws", p_ws.symbol, p_kwh.symbol,
            "Missing 3.6e6 conversion.", check_units=True,
        )
    with pytest.raises(UnitError, match="scale"):
        Equation(
            "test.scale.eq.kwh_as_ws_hours", p_ws.symbol, p_kwh.symbol / 3600,
            "Hours-per-second slip instead of 3.6e6.", check_units=True,
        )
    Equation(
        "test.scale.eq.kwh_to_ws", p_ws.symbol, p_kwh.symbol / 3_600_000,
        "Correct conversion.", check_units=True,
    )


def test_bit_byte_slip_is_caught(registry_snapshot):
    n_bit = _mk("bb.bits", "bit", bit)
    n_byte = _mk("bb.bytes", "byte", byte)
    with pytest.raises(UnitError, match="scale"):
        Equation("test.scale.eq.bytes_eq_bits", n_byte.symbol, n_bit.symbol,
                 "Missing divide by 8.", check_units=True)
    Equation("test.scale.eq.bytes_from_bits", n_byte.symbol, n_bit.symbol / 8,
             "Bits to bytes.", check_units=True)


def test_physical_coefficient_with_matching_scale_still_passes(registry_snapshot):
    c = _mk("coef.c", "F", sp.Symbol("F_unit"))
    half = _mk("coef.half", "F", sp.Symbol("F_unit"))
    Equation("test.scale.eq.half", half.symbol, c.symbol * sp.Rational(1, 2),
             "A physical coefficient on equal-scale units.", check_units=True)


def test_exponent_with_unconverted_scale_is_caught():
    t_ms, tau_s = sp.symbols("t_ms tau_s")
    with pytest.raises(UnitError, match="scale"):
        infer_expr_units(
            sp.exp(-t_ms / tau_s), {t_ms: MS, tau_s: SECOND}, "test.exp"
        )


def test_check_dimensional_consistency_compares_scale():
    with pytest.raises(UnitError, match="scale"):
        check_dimensional_consistency(SECOND, MS, "test.dim")
    check_dimensional_consistency(SECOND, SECOND, "test.dim")


def test_non_unit_errors_are_recorded_as_undecided_not_silent(monkeypatch):
    def boom(*_args, **_kwargs):
        raise RuntimeError("sympy gave up")

    monkeypatch.setattr(U, "_assert_equivalent_units", boom)
    U.UNDECIDED_UNIT_CHECKS.pop("test.scale.undecided", None)
    check_dimensional_consistency(SECOND, SECOND, "test.scale.undecided")
    try:
        assert "RuntimeError" in undecided_unit_checks()["test.scale.undecided"]
    finally:
        U.UNDECIDED_UNIT_CHECKS.pop("test.scale.undecided", None)


# ---------------------------------------------------------------------------
# Every variable's label scale must match its sp_units scale
# ---------------------------------------------------------------------------

_LABEL_TOKENS = {
    "m": U.METER, "s": SECOND, "kg": U.KILOGRAM, "A": U.AMPERE, "K": U.KELVIN,
    "Hz": U.HZ, "Pa": U.PASCAL, "J": U.JOULE, "W": WATT, "C": U.COULOMB,
    "V": U.VOLT, "F": U.FARAD, "kW": KILOWATT, "h": U.HOUR, "month": MONTH,
    "year": U.YEAR, "L": liter, "t": tonne, "GB": GIGABYTE, "kWh": KWH,
    "byte": byte, "bit": bit, "ms": MS, "us": micro * SECOND,
    "ns": nano * SECOND, "GHz": giga * U.HZ, "MHz": mega * U.HZ,
    "mm": milli * U.METER, "um": micro * U.METER, "nm": nano * U.METER,
    "USD": USD,
}


def _label_unit(label):
    text = label.replace("^", "**")
    names = set(re.findall(r"[A-Za-z_]+", text))
    if not names or not names <= set(_LABEL_TOKENS):
        return None  # counts, "dimensionless", free-form labels: no scale claim
    return sp.sympify(text, locals=_LABEL_TOKENS)


def test_variable_labels_and_sp_units_agree_in_scale():
    mismatched = []
    checked = 0
    for variable in Registry.variables.values():
        if variable.sp_units is None:
            continue
        expected = _label_unit(variable.units)
        if expected is None:
            continue
        checked += 1
        ratio = float(unit_scale(expected)) / float(unit_scale(variable.sp_units))
        if abs(ratio - 1.0) > 1e-9:
            mismatched.append((variable.name, variable.units, ratio))
    assert checked > 300, "label parser stopped recognizing most labels"
    assert mismatched == []
