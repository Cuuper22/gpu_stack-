"""Tests for the ``root-debt`` CLI command.

"Root debt" is the count of unassigned root inputs, ranked by how many
derived variables depend on each one — assigning the top-ranked roots pays
down the most uncertainty per value. The big test here pins, name by name,
which lithography variables are roots (they appear in the ranking) and
which are derived (they must not). That split is the model's real structure:
if a refactor turns a derived quantity back into a root, or vice versa,
this test names the exact variable that moved. The others cover the scope
filter and the ``--include-constraints`` toggle.
"""

from gpu_stack.cli import main
from tests.helpers.cli import captured_stdout


def test_root_debt_ranks_central_roots():
    with captured_stdout() as buf:
        rc = main(["root-debt", "--limit", "1000"])
    out = buf.getvalue()
    assert rc == 0
    assert "Root-debt ranking:" in out
    assert "include_constraints False" in out
    assert "dependents" in out
    ranked_variables = {
        parts[2]
        for line in out.splitlines()
        if (parts := line.split()) and parts[0].isdigit() and len(parts) >= 3
    }
    assert "physical.lithography.wavelength" in ranked_variables
    assert "physical.lithography.numerical_aperture" in ranked_variables
    assert "physical.lithography.gate_k1_aerial_image_contrast_factor" in ranked_variables
    assert "physical.lithography.gate_k1_resist_process_factor" in ranked_variables
    assert "physical.lithography.gate_k1_mask_error_factor" in ranked_variables
    assert "physical.lithography.gate_k1_resolution_enhancement_factor" in ranked_variables
    assert "physical.lithography.gate_k1" not in ranked_variables
    assert "physical.lithography.gate_resolution" not in ranked_variables


def test_root_debt_scope_filter():
    with captured_stdout() as buf:
        rc = main(["root-debt", "--scope", "gpu", "--limit", "3"])
    out = buf.getvalue()
    assert rc == 0
    assert "filtered_scope     gpu" in out
    assert "gpu.sm.tensor_core_area_per_unit" in out


def test_root_debt_can_include_constraint_edges():
    with captured_stdout() as buf:
        rc = main(["root-debt", "--scope", "thermal", "--limit", "5", "--include-constraints"])
    out = buf.getvalue()
    assert rc == 0
    assert "include_constraints True" in out
