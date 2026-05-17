"""Physical scope export propagation import tests."""

from tests.helpers.import_physical_lithography_exports import (
    assert_absorption_edge_exports_propagate_through_physical_surface,
    assert_lithography_k1_exports_propagate_through_physical_surface,
    assert_medium_density_exports_and_composition_compat_surface,
    assert_medium_response_exports_propagate_through_physical_surface,
)
from tests.helpers.import_physical_plasma_state_exports import (
    assert_plasma_state_shim_preserves_public_surface,
)


def test_absorption_edge_exports_propagate_through_physical_surface():
    assert_absorption_edge_exports_propagate_through_physical_surface()


def test_medium_response_exports_propagate_through_physical_surface():
    assert_medium_response_exports_propagate_through_physical_surface()


def test_medium_density_exports_and_composition_compat_surface():
    assert_medium_density_exports_and_composition_compat_surface()


def test_lithography_k1_exports_propagate_through_physical_surface():
    assert_lithography_k1_exports_propagate_through_physical_surface()


def test_plasma_state_shim_preserves_public_surface():
    assert_plasma_state_shim_preserves_public_surface()
