"""Core contracts for the scenario-preset framework."""

import pytest

from gpu_stack.core import Preset, combine_presets
from gpu_stack.presets import hardware, workload


def test_preset_rejects_unknown_variable_name():
    with pytest.raises(ValueError, match="unknown variables"):
        Preset(
            name="bad",
            description="typo in variable name",
            assignments={"cluster.rack.n_NODES": 9},  # wrong case
        )


def test_preset_rejects_unknown_variant_name():
    with pytest.raises(ValueError, match="unknown variables"):
        Preset(
            name="bad",
            description="typo in variant variable name",
            variants={"training.flopz_per_step": "dense"},
        )


def test_preset_rejects_non_variant_selector():
    with pytest.raises(ValueError, match="invalid variant selector"):
        Preset(
            name="bad",
            description="valid variable, but not a variant family",
            variants={"cluster.rack.n_nodes": "dense"},
        )


def test_preset_rejects_unknown_variant_key():
    with pytest.raises(ValueError, match="variant key"):
        Preset(
            name="bad",
            description="valid variant family with a typoed key",
            variants={"training.flops_per_step": "denze"},
        )


def test_demo_rack_resolves_to_canonical_number():
    result = hardware.demo_rack.resolve("cluster.rack.peak_flops")
    assert float(result.value) == pytest.approx(1.08e18, rel=1e-12)


def test_combine_presets_merges_assignments_and_variants():
    combined = combine_presets(
        hardware.demo_rack,
        workload.dense_variant_selector,
        name="demo_rack_dense",
    )
    assert combined.assignments["cluster.rack.n_nodes"] == 9
    assert combined.variants["training.flops_per_step"] == "dense"
    assert "demo_rack" in (combined.source or "")


def test_combine_presets_override_order():
    # Later preset wins on collisions.
    a = Preset(name="a", description="", assignments={"cluster.rack.n_nodes": 9})
    b = Preset(name="b", description="", assignments={"cluster.rack.n_nodes": 18})
    merged = combine_presets(a, b, name="ab")
    assert merged.assignments["cluster.rack.n_nodes"] == 18


def test_workload_presets_pin_variant_keys():
    assert workload.dense_variant_selector.variants["training.flops_per_step"] == "dense"
    assert workload.dense_variant_selector.variants["training.scaling_params"] == "dense"
    assert workload.moe_variant_selector.variants["training.flops_per_step"] == "moe"
    assert workload.moe_variant_selector.variants["training.scaling_params"] == "moe"
    assert workload.adamw_optimizer_selector.variants["opt.param_next"] == "adamw"
    assert workload.muon_optimizer_selector.variants["opt.param_next"] == "muon"


def test_preset_with_overrides_returns_new_instance():
    base = hardware.demo_rack
    updated = base.with_overrides(assignments={"cluster.rack.n_nodes": 72})
    assert base.assignments["cluster.rack.n_nodes"] == 9
    assert updated.assignments["cluster.rack.n_nodes"] == 72
    assert updated.name.startswith("demo_rack")


def test_preset_copies_and_freezes_inputs():
    assignments = {"cluster.rack.n_nodes": 9}
    variants = {"training.flops_per_step": "dense"}
    notes = ["temporary note"]

    preset = Preset(
        name="frozen_inputs",
        description="temporary preset with mutable constructor inputs",
        assignments=assignments,
        variants=variants,
        notes=notes,
    )

    assignments["cluster.rack.n_nodes"] = 72
    variants["training.flops_per_step"] = "moe"
    notes.append("mutated")

    assert preset.assignments["cluster.rack.n_nodes"] == 9
    assert preset.variants["training.flops_per_step"] == "dense"
    assert preset.notes == ("temporary note",)
    with pytest.raises(TypeError):
        preset.assignments["cluster.rack.n_nodes"] = 18
    with pytest.raises(TypeError):
        preset.variants["training.flops_per_step"] = "moe"


def test_preset_with_overrides_revalidates_variants():
    with pytest.raises(ValueError, match="invalid variant selector"):
        workload.dense_variant_selector.with_overrides(
            variants={"training.flops_per_step": "denze"},
        )


def test_preset_variants_unlock_mfu_resolution():
    # training.mfu has two variants; dense_variant_selector does not cover
    # it, so resolving via demo_rack alone is insufficient. Combining with
    # mfu_from_flops_selector resolves the variant ambiguity.
    combined = combine_presets(
        hardware.demo_rack,
        workload.mfu_from_flops_selector,
        name="demo_rack_mfu",
    )
    assert combined.variants["training.mfu"] == "from_flops"
