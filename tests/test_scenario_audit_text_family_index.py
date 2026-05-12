"""Focused scenario-audit text-mode missing-family coverage."""

import contextlib
import io

from gpu_stack.cli import main


def _run_cli(args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = main(args)
    return rc, out.getvalue()


def test_scenario_audit_missing_families_text_indexes_missing_roots_by_family():
    rc, out = _run_cli(
        [
            "scenario-audit",
            "--preset",
            "scenarios.pythia_70m_dgx_h100_us_2024_industrial_power",
            "--target",
            "cost_per_token=econ.cost.per_token",
            "--missing-families",
        ]
    )

    assert rc == 0
    assert "Scenario audit:" in out
    assert (
        "pythia_70m_dgx_h100_us_2024_industrial_power: issues "
        "targets=1 issues=33 sourced=True"
    ) in out
    assert (
        "cost_per_token: issues target=econ.cost.per_token "
        "missing=33 violated_constraints=0"
    ) in out
    assert "unresolved inputs:" not in out
    assert "      missing families:" in out
    assert (
        "        family=cluster.node boundary_category=primitive-root "
        "primitive_boundary=True count=6 names="
    ) in out
    assert (
        "        family=econ.cluster boundary_category=symbolic-boundary "
        "primitive_boundary=False count=1 names=econ.cluster.facility_capex"
    ) in out
    assert (
        "        family=thermal.water boundary_category=primitive-root "
        "primitive_boundary=True count=4 names="
    ) in out
