"""Checks that lithography exports re-export cleanly up the physical scope chain.

Each lithography submodule (absorption edge, medium response, density, k1)
defines names that must also appear, as the very same objects, in the parent
``physical_lithography`` module and the top-level ``physical`` scope. If a
re-export shim drops or shadows a name, user code that imports from the
top-level scope silently gets the wrong object. These helpers walk each
export list and assert identity at every level.
"""


def assert_absorption_edge_exports_propagate_through_physical_surface():
    from gpu_stack.scopes import physical as physical_scope
    from gpu_stack.scopes import physical_lithography as lithography
    from gpu_stack.scopes import physical_lithography_absorption_edge as edge
    from gpu_stack.scopes import physical_lithography_electronic_structure as es
    from gpu_stack.scopes import physical_lithography_source as source

    export_name = "LITHOGRAPHY_SOURCE_ABSORPTION_EDGE_REF"
    expected_ref = edge.LITHOGRAPHY_SOURCE_ABSORPTION_EDGE_REF

    for module in (edge, es, source, lithography, physical_scope):
        assert export_name in module.__all__
        assert getattr(module, export_name) is expected_ref


def assert_medium_response_exports_propagate_through_physical_surface():
    from gpu_stack.scopes import physical as physical_scope
    from gpu_stack.scopes import physical_lithography as lithography
    from gpu_stack.scopes import physical_lithography_medium_response as response

    for name in response.__all__:
        assert name in lithography.__all__
        assert getattr(lithography, name) is getattr(response, name)
        assert name in physical_scope.__all__
        assert getattr(physical_scope, name) is getattr(response, name)

    assert set(response.LITHOGRAPHY_MEDIUM_RESPONSE_VARIABLES) <= set(
        lithography.LITHOGRAPHY_VARIABLES
    )
    assert set(response.LITHOGRAPHY_MEDIUM_RESPONSE_EQUATIONS) <= set(
        lithography.LITHOGRAPHY_EQUATIONS
    )


def assert_medium_density_exports_and_composition_compat_surface():
    from gpu_stack.scopes import physical as physical_scope
    from gpu_stack.scopes import physical_lithography as lithography
    from gpu_stack.scopes import physical_lithography_medium_composition as composition
    from gpu_stack.scopes import physical_lithography_medium_density as density

    for name in density.__all__:
        assert name in lithography.__all__
        assert getattr(lithography, name) is getattr(density, name)
        assert name in physical_scope.__all__
        assert getattr(physical_scope, name) is getattr(density, name)

    for name in density.__all__:
        assert name in composition.__all__
        assert getattr(composition, name) is getattr(density, name)

    assert set(density.LITHOGRAPHY_MEDIUM_DENSITY_VARIABLES) <= set(
        lithography.LITHOGRAPHY_VARIABLES
    )
    assert set(density.LITHOGRAPHY_MEDIUM_DENSITY_EQUATIONS) <= set(
        lithography.LITHOGRAPHY_EQUATIONS
    )


def assert_lithography_k1_exports_propagate_through_physical_surface():
    from gpu_stack.scopes import physical as physical_scope
    from gpu_stack.scopes import physical_lithography as lithography
    from gpu_stack.scopes import physical_lithography_k1 as k1

    for name in k1.__all__:
        assert name in lithography.__all__
        assert getattr(lithography, name) is getattr(k1, name)
        assert name in physical_scope.__all__
        assert getattr(physical_scope, name) is getattr(k1, name)

    assert set(k1.LITHOGRAPHY_K1_VARIABLES) <= set(lithography.LITHOGRAPHY_VARIABLES)
    assert set(k1.LITHOGRAPHY_K1_EQUATIONS) <= set(lithography.LITHOGRAPHY_EQUATIONS)
