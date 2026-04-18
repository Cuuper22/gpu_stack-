"""
Demo script for gpu_stack.

Run with:
    python -m gpu_stack.demo
"""

import sympy as sp

from gpu_stack import (
    Constant,
    Registry,
    SCOPE_DESCRIPTIONS,
    SCOPE_MODULES,
    find_cycles,
    topological_sort,
)


def print_section(title):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def show_dependency_tree(var, depth=0, seen=None, max_depth=6):
    if seen is None:
        seen = set()
    if var.name in seen or depth > max_depth:
        return
    seen.add(var.name)
    prefix = "  " * depth + ("+ " if depth > 0 else "")
    marker = " [CONST]" if isinstance(var, Constant) else ""
    print(f"{prefix}{var.name}  [{var.units}]{marker}")
    for child in sorted(var.direct_dependencies(), key=lambda v: v.name):
        show_dependency_tree(child, depth + 1, seen, max_depth)


def main():
    stats = Registry.stats()

    print_section("Registry summary")
    for key in ("systems", "variables", "constants", "equations", "root_inputs", "leaves"):
        print(f"{key:<12}: {stats[key]}")

    print_section("Loaded scopes")
    for name in SCOPE_MODULES:
        description = SCOPE_DESCRIPTIONS.get(name, "")
        sys_obj = Registry.systems.get(name)
        if sys_obj is None:
            print(f"  {name:<16} missing")
            continue
        print(
            f"  {name:<16} vars={len(sys_obj.variables):<4} "
            f"eqs={len(sys_obj.equations):<4} {description}"
        )

    print_section("Graph health")
    cycles = find_cycles()
    if cycles:
        print("Cycles found:")
        for cycle in cycles:
            print("  " + " -> ".join(v.name for v in cycle))
    else:
        print("No cycles found.")
        topo = topological_sort()
        print(f"Topological sort length: {len(topo)}")
        print("Last 10 variables in one valid topological order:")
        for v in topo[-10:]:
            print(f"  {v.name}")

    print_section("Universal physics constants")
    for v in Registry.variables.values():
        if isinstance(v, Constant):
            print(f"  {str(v.symbol):<10} = {v.value:<15g} {v.units:<15} {v.description}")

    print_section("Dependency tree: econ.cost.per_token")
    cost_per_token = Registry.variables["econ.cost.per_token"]
    show_dependency_tree(cost_per_token, max_depth=4)

    print_section("All equations defining gpu.peak_flops")
    peak_gpu = Registry.variables["gpu.peak_flops"]
    for e in peak_gpu.defining_equations:
        print(f"  {e.name}")
        print(f"    {e.as_sympy()}")
        print(f"    -> {e.description}")

    print_section("Chain: how cluster.rack.peak_flops reduces toward per-GPU peak")
    rack_peak = Registry.variables["cluster.rack.peak_flops"]

    def walk(v, depth=0, seen=None):
        if seen is None:
            seen = set()
        if v.name in seen or depth > 8:
            return
        seen.add(v.name)
        pad = "  " * depth
        print(f"{pad}{v.name}")
        for eq in v.defining_equations[:1]:
            print(f"{pad}  <= {eq.rhs}")
        for child in sorted(v.direct_dependencies(), key=lambda x: x.name):
            walk(child, depth + 1, seen)

    walk(rack_peak)

    print_section("Symbolic solve: one PUE equation, two solve directions")
    pue_eq = Registry.equations["thermal.eq.pue_definition"]
    dc_total_power = Registry.variables["thermal.dc.total_power"]
    pue = Registry.variables["thermal.dc.pue"]
    print(f"  {pue_eq.as_sympy()}")
    print(f"  solve for total power: {pue_eq.solve_for(dc_total_power.symbol)}")
    print(f"  solve for PUE:         {pue_eq.solve_for(pue.symbol)}")

    print_section("Example substitution: GB300-class NVL72 rack peak FLOPs")
    node_eq = Registry.equations["cluster.eq.node_peak_flops"]
    rack_eq = Registry.equations["cluster.eq.rack_peak_flops"]
    node_value = sp.N(
        node_eq.evaluate_rhs(
            {
                Registry.variables["cluster.node.n_gpus"].symbol: 8,
                Registry.variables["gpu.peak_flops"].symbol: sp.Float(15e15),
            }
        )
    )
    rack_value = sp.N(
        rack_eq.evaluate_rhs(
            {
                Registry.variables["cluster.rack.n_nodes"].symbol: 9,
                Registry.variables["cluster.node.peak_flops"].symbol: node_value,
            }
        )
    )
    print(f"  node equation: {node_eq.as_sympy()}")
    print(f"  rack equation: {rack_eq.as_sympy()}")
    print("  substitutions:")
    print("    N_node_rack = 9")
    print("    N_G_node    = 8")
    print("    F_GPU       = 1.5e16")
    print(f"  node peak = {node_value}")
    print(f"  rack peak = {rack_value}")
    print("  (= 1.08e18 FLOP/s, or 1.08 exaFLOP/s)")

    print_section("Example equation: total run cost")
    run_cost_eq = Registry.equations["econ.eq.run_total"]
    print(f"  {run_cost_eq.as_sympy()}")
    print(f"  LaTeX: {run_cost_eq.latex()}")

    print_section("A few root inputs")
    for v in sorted(Registry.roots(), key=lambda x: x.name)[:20]:
        print(f"  {v.name:<42} [{v.units}]")

    print_section("A few leaves")
    for v in sorted(Registry.leaves(), key=lambda x: x.name)[:20]:
        print(f"  {v.name:<42} [{v.units}]")


if __name__ == "__main__":
    main()
